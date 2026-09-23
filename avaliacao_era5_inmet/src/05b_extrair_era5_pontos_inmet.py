from calendar import isleap
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_get_double_elements,
    codes_release,
)

from config import (
    PROJECT_DIR,
    ERA5_GRIB,
    ERA5_COMPLEMENTO_ANOS_DIR,
    TABLES_DIR,
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

ANO_INICIAL = 2000
ANO_FINAL = 2025

KELVIN_CELSIUS = 273.15


MATCHES_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "matches"
)


ARQUIVO_MATCHES = (
    MATCHES_DIR
    / "inmet_era5_estacao_ano.csv"
)


ERA5_PONTOS_DIR = (
    PROJECT_DIR
    / "data"
    / "interim"
    / "era5"
    / "pontos_inmet"
)


ERA5_PONTOS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ARQUIVO_RESUMO = (
    TABLES_DIR
    / "resumo_extracao_era5_pontos_inmet.csv"
)


# Quantidade aproximada de linhas acumuladas
# antes de escrever um novo bloco no Parquet.
LIMITE_BUFFER = 200_000


# ==========================================================
# SCHEMA
# ==========================================================

SCHEMA = pa.schema(
    [
        (
            "datetime_utc",
            pa.timestamp("ns"),
        ),
        (
            "grid_index",
            pa.int32(),
        ),
        (
            "temp_era5_c",
            pa.float32(),
        ),
    ]
)


# ==========================================================
# DATETIME DO GRIB
# ==========================================================

def montar_datetime(
    validity_date,
    validity_time,
):

    validity_date = int(
        validity_date
    )

    validity_time = int(
        validity_time
    )


    ano = (
        validity_date
        // 10000
    )

    mes = (
        validity_date
        // 100
    ) % 100

    dia = (
        validity_date
        % 100
    )

    hora = (
        validity_time
        // 100
    )

    minuto = (
        validity_time
        % 100
    )


    return datetime(
        ano,
        mes,
        dia,
        hora,
        minuto,
    )


# ==========================================================
# HORAS ESPERADAS NO ANO
# ==========================================================

def horas_esperadas(
    ano,
):

    return (
        8784
        if isleap(
            ano
        )
        else
        8760
    )


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("EXTRAÇÃO ERA5 NAS CÉLULAS DAS ESTAÇÕES INMET")
print("=" * 90)

print(
    "\nPeríodo:"
)

print(
    f"{ANO_INICIAL}-{ANO_FINAL}"
)


# ==========================================================
# 1. CARREGAR PAREAMENTO ESPACIAL
# ==========================================================

if not ARQUIVO_MATCHES.exists():

    raise FileNotFoundError(
        f"Arquivo de pareamento não encontrado:\n"
        f"{ARQUIVO_MATCHES}"
    )


matches = pd.read_csv(
    ARQUIVO_MATCHES
)


matches[
    "ano"
] = pd.to_numeric(
    matches[
        "ano"
    ],
    errors="raise",
).astype(int)


matches[
    "grid_index"
] = pd.to_numeric(
    matches[
        "grid_index"
    ],
    errors="raise",
).astype(int)


print(
    f"\nRegistros estação-ano: "
    f"{len(matches):,}"
)


print(
    f"Células únicas em todo período: "
    f"{matches['grid_index'].nunique():,}"
)


# ==========================================================
# 2. CÉLULAS NECESSÁRIAS POR ANO
# ==========================================================

indices_por_ano = {}


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    indices = (
        matches.loc[
            matches[
                "ano"
            ]
            ==
            ano,
            "grid_index",
        ]
        .drop_duplicates()
        .sort_values()
        .to_numpy(
            dtype=np.int32
        )
    )


    if len(indices) == 0:

        raise RuntimeError(
            f"Nenhuma célula ERA5 necessária "
            f"para {ano}."
        )


    indices_por_ano[
        ano
    ] = indices


print(
    "\nCélulas necessárias por ano:"
)


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    print(
        f"{ano}: "
        f"{len(indices_por_ano[ano]):,}"
    )


# ==========================================================
# 3. PREPARAR ARQUIVOS DE SAÍDA
# ==========================================================

caminhos_saida = {}


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    caminho = (
        ERA5_PONTOS_DIR
        / f"era5_pontos_inmet_{ano}.parquet"
    )


    caminhos_saida[
        ano
    ] = caminho


    if caminho.exists():

        print(
            f"\nRemovendo saída anterior: "
            f"{caminho.name}"
        )

        caminho.unlink()


# ==========================================================
# 4. WRITERS E BUFFERS
# ==========================================================

writers = {
    ano: None
    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    )
}


buffers_datetime = {
    ano: []
    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    )
}


buffers_grid = {
    ano: []
    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    )
}


buffers_temp = {
    ano: []
    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    )
}


linhas_buffer = {
    ano: 0
    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    )
}


mensagens_por_ano = {
    ano: 0
    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    )
}


linhas_por_ano = {
    ano: 0
    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    )
}


mensagens_original = {
    ano: 0
    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    )
}


mensagens_complemento = {
    ano: 0
    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    )
}


# ==========================================================
# 5. ESCREVER BUFFER
# ==========================================================

def flush_ano(
    ano,
):

    if linhas_buffer[
        ano
    ] == 0:

        return


    datetimes = np.concatenate(
        buffers_datetime[
            ano
        ]
    )


    grids = np.concatenate(
        buffers_grid[
            ano
        ]
    )


    temperaturas = np.concatenate(
        buffers_temp[
            ano
        ]
    )


    tabela = pa.Table.from_arrays(
        [
            pa.array(
                datetimes,
                type=pa.timestamp(
                    "ns"
                ),
            ),

            pa.array(
                grids,
                type=pa.int32(),
            ),

            pa.array(
                temperaturas,
                type=pa.float32(),
            ),
        ],
        schema=SCHEMA,
    )


    if writers[
        ano
    ] is None:

        writers[
            ano
        ] = pq.ParquetWriter(
            caminhos_saida[
                ano
            ],
            SCHEMA,
            compression="snappy",
        )


    writers[
        ano
    ].write_table(
        tabela
    )


    buffers_datetime[
        ano
    ].clear()

    buffers_grid[
        ano
    ].clear()

    buffers_temp[
        ano
    ].clear()


    linhas_buffer[
        ano
    ] = 0


# ==========================================================
# 6. ADICIONAR UMA MENSAGEM AO BUFFER
# ==========================================================

def adicionar_mensagem(
    ano,
    data_hora,
    valores_c,
):

    indices = (
        indices_por_ano[
            ano
        ]
    )


    quantidade = len(
        indices
    )


    vetor_datetime = np.full(
        quantidade,
        np.datetime64(
            data_hora,
            "ns",
        ),
        dtype="datetime64[ns]",
    )


    buffers_datetime[
        ano
    ].append(
        vetor_datetime
    )


    buffers_grid[
        ano
    ].append(
        indices
    )


    buffers_temp[
        ano
    ].append(
        valores_c
    )


    linhas_buffer[
        ano
    ] += quantidade


    linhas_por_ano[
        ano
    ] += quantidade


    mensagens_por_ano[
        ano
    ] += 1


    if (
        linhas_buffer[
            ano
        ]
        >= LIMITE_BUFFER
    ):

        flush_ano(
            ano
        )


# ==========================================================
# 7. PROCESSAR GRIB
# ==========================================================

def processar_grib(
    caminho,
    fonte,
):

    print("\n" + "=" * 90)

    print(
        f"PROCESSANDO: {fonte}"
    )

    print("=" * 90)

    print(
        caminho
    )


    total_mx2t = 0

    total_periodo = 0


    with open(
        caminho,
        "rb",
    ) as arquivo:

        while True:

            gid = (
                codes_grib_new_from_file(
                    arquivo
                )
            )


            if gid is None:

                break


            try:

                short_name = codes_get(
                    gid,
                    "shortName",
                )


                if short_name != "mx2t":

                    continue


                total_mx2t += 1


                validity_date = int(
                    codes_get(
                        gid,
                        "validityDate",
                    )
                )


                validity_time = int(
                    codes_get(
                        gid,
                        "validityTime",
                    )
                )


                data_hora = montar_datetime(
                    validity_date,
                    validity_time,
                )


                ano = data_hora.year


                if (
                    ano < ANO_INICIAL
                    or
                    ano > ANO_FINAL
                ):

                    continue


                total_periodo += 1


                indices = (
                    indices_por_ano[
                        ano
                    ]
                )


                # ==========================================
                # EXTRAIR SOMENTE AS CÉLULAS NECESSÁRIAS
                # ==========================================

                valores_k = np.asarray(
                    codes_get_double_elements(
                        gid,
                        "values",
                        indices.tolist(),
                    ),
                    dtype=np.float64,
                )


                if (
                    len(valores_k)
                    != len(indices)
                ):

                    raise RuntimeError(
                        "Número de valores ERA5 "
                        "extraídos diferente do número "
                        "de células solicitadas."
                    )


                valores_c = (
                    valores_k
                    -
                    KELVIN_CELSIUS
                ).astype(
                    np.float32
                )


                adicionar_mensagem(
                    ano,
                    data_hora,
                    valores_c,
                )


                if fonte == "original":

                    mensagens_original[
                        ano
                    ] += 1

                else:

                    mensagens_complemento[
                        ano
                    ] += 1


            finally:

                codes_release(
                    gid
                )


            if (
                total_mx2t > 0
                and
                total_mx2t % 25000 == 0
            ):

                print(
                    f"{total_mx2t:,} mensagens "
                    "mx2t examinadas..."
                )


    print(
        f"\nMensagens mx2t examinadas: "
        f"{total_mx2t:,}"
    )


    print(
        f"Mensagens dentro de "
        f"{ANO_INICIAL}-{ANO_FINAL}: "
        f"{total_periodo:,}"
    )


# ==========================================================
# 8. PROCESSAR GRIB ORIGINAL UMA ÚNICA VEZ
# ==========================================================

print("\n" + "=" * 90)
print("ETAPA 1/2 - GRIB ORIGINAL")
print("=" * 90)


processar_grib(
    ERA5_GRIB,
    "original",
)


# ==========================================================
# 9. PROCESSAR COMPLEMENTOS 2000–2025
# ==========================================================

print("\n" + "=" * 90)
print("ETAPA 2/2 - COMPLEMENTOS")
print("=" * 90)


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    caminho = (
        ERA5_COMPLEMENTO_ANOS_DIR
        / f"mx2t_faltantes_{ano}.grib"
    )


    if not caminho.exists():

        raise FileNotFoundError(
            f"Complemento não encontrado:\n"
            f"{caminho}"
        )


    processar_grib(
        caminho,
        "complemento",
    )


# ==========================================================
# 10. DESCARREGAR BUFFERS E FECHAR WRITERS
# ==========================================================

print("\n" + "=" * 90)
print("FINALIZANDO PARQUETS")
print("=" * 90)


try:

    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    ):

        flush_ano(
            ano
        )

finally:

    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    ):

        if writers[
            ano
        ] is not None:

            writers[
                ano
            ].close()


# ==========================================================
# 11. VALIDAR RESULTADOS
# ==========================================================

print("\n" + "=" * 90)
print("VALIDAÇÃO DA EXTRAÇÃO")
print("=" * 90)


resumo = []

tudo_ok = True


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    esperado_horas = horas_esperadas(
        ano
    )


    celulas = len(
        indices_por_ano[
            ano
        ]
    )


    esperado_linhas = (
        esperado_horas
        *
        celulas
    )


    encontrado_horas = (
        mensagens_por_ano[
            ano
        ]
    )


    arquivo = (
        caminhos_saida[
            ano
        ]
    )


    if arquivo.exists():

        parquet = pq.ParquetFile(
            arquivo
        )


        encontrado_linhas = int(
            parquet.metadata.num_rows
        )


        tamanho_mb = (
            arquivo.stat().st_size
            /
            1024**2
        )

    else:

        encontrado_linhas = 0
        tamanho_mb = 0.0


    original = (
        mensagens_original[
            ano
        ]
    )


    complemento = (
        mensagens_complemento[
            ano
        ]
    )


    status = (
        "OK"
        if (
            encontrado_horas
            ==
            esperado_horas
            and
            encontrado_linhas
            ==
            esperado_linhas
            and
            original
            +
            complemento
            ==
            esperado_horas
        )
        else
        "ERRO"
    )


    if status != "OK":

        tudo_ok = False


    print(
        f"{ano} | "
        f"células={celulas:3d} | "
        f"horas={encontrado_horas:,}/"
        f"{esperado_horas:,} | "
        f"original={original:,} | "
        f"compl={complemento:,} | "
        f"linhas={encontrado_linhas:,}/"
        f"{esperado_linhas:,} | "
        f"{tamanho_mb:7.2f} MB | "
        f"{status}"
    )


    resumo.append(
        {
            "ano":
                ano,

            "celulas_era5":
                celulas,

            "horas_esperadas":
                esperado_horas,

            "mensagens_original":
                original,

            "mensagens_complemento":
                complemento,

            "horas_encontradas":
                encontrado_horas,

            "linhas_esperadas":
                esperado_linhas,

            "linhas_encontradas":
                encontrado_linhas,

            "arquivo_mb":
                round(
                    tamanho_mb,
                    2,
                ),

            "status":
                status,
        }
    )


# ==========================================================
# 12. SALVAR RESUMO
# ==========================================================

df_resumo = pd.DataFrame(
    resumo
)


df_resumo.to_csv(
    ARQUIVO_RESUMO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 13. RESUMO GLOBAL
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO GLOBAL")
print("=" * 90)


print(
    f"\nAnos processados: "
    f"{len(df_resumo)}"
)


print(
    f"Total de horas ERA5: "
    f"{df_resumo['horas_encontradas'].sum():,}"
)


print(
    f"Total de linhas extraídas: "
    f"{df_resumo['linhas_encontradas'].sum():,}"
)


print(
    f"Tamanho total dos Parquets: "
    f"{df_resumo['arquivo_mb'].sum():,.2f} MB"
)


print(
    f"\nArquivos com erro: "
    f"{(df_resumo['status'] != 'OK').sum():,}"
)


print(
    "\nResumo salvo em:"
)

print(
    ARQUIVO_RESUMO
)


print(
    "\nParquets ERA5:"
)

print(
    ERA5_PONTOS_DIR
)


print("\n" + "=" * 90)


if tudo_ok:

    print(
        "RESULTADO: EXTRAÇÃO ERA5 APROVADA"
    )

else:

    print(
        "RESULTADO: EXTRAÇÃO ERA5 "
        "REQUER INVESTIGAÇÃO"
    )


print("=" * 90)