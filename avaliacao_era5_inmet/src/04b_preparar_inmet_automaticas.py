from pathlib import Path
import csv
import io
import re
import unicodedata
import zipfile

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from config import PROJECT_DIR, TABLES_DIR


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

ANO_INICIAL = 2000
ANO_FINAL = 2025


INMET_RAW_DIR = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "inmet"
    / "automaticas"
)


INMET_INTERIM_DIR = (
    PROJECT_DIR
    / "data"
    / "interim"
    / "inmet"
    / "automaticas"
)


INMET_INTERIM_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


TABLES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ARQUIVO_CATALOGO = (
    TABLES_DIR
    / "catalogo_estacoes_inmet_por_ano.csv"
)


ARQUIVO_RESUMO = (
    TABLES_DIR
    / "resumo_preparo_inmet.csv"
)


# ==========================================================
# SCHEMA DOS PARQUETS
# ==========================================================

SCHEMA = pa.schema(
    [
        (
            "codigo",
            pa.string(),
        ),
        (
            "datetime_utc",
            pa.timestamp("ns"),
        ),
        (
            "temp_max_hora_ant_c",
            pa.float64(),
        ),
    ]
)


# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def normalizar_texto(texto):

    texto = str(
        texto
    ).strip()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(
            caractere
        )
    )

    texto = texto.upper()

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def converter_numero(valor):

    if valor is None:
        return np.nan

    valor = str(
        valor
    ).strip()

    if not valor:
        return np.nan

    valor = valor.replace(
        ",",
        ".",
    )

    try:

        numero = float(
            valor
        )

    except ValueError:

        return np.nan


    # Sentinel histórico do INMET
    if numero <= -9990:

        return np.nan


    return numero


def localizar_cabecalho(linhas):

    for indice, linha in enumerate(
        linhas[:30]
    ):

        normalizada = normalizar_texto(
            linha
        )

        if (
            "TEMPERATURA MAXIMA NA HORA ANT"
            in normalizada
            and
            "HORA"
            in normalizada
        ):

            return indice


    raise RuntimeError(
        "Cabeçalho dos dados não encontrado."
    )


def ler_metadados(
    linhas,
    indice_cabecalho,
):

    metadados = {}


    for linha in linhas[
        :indice_cabecalho
    ]:

        partes = linha.split(
            ";",
            1,
        )


        if len(partes) != 2:

            continue


        chave = normalizar_texto(
            partes[0]
        )


        valor = (
            partes[1]
            .strip()
        )


        metadados[
            chave
        ] = valor


    def buscar(*termos):

        for chave, valor in (
            metadados.items()
        ):

            if all(
                termo in chave
                for termo in termos
            ):

                return valor

        return None


    return {

        "regiao":
            buscar(
                "REGIAO",
            ),

        "uf":
            buscar(
                "UF",
            ),

        "estacao":
            buscar(
                "ESTACAO",
            ),

        "codigo":
            buscar(
                "CODIGO",
                "WMO",
            ),

        "latitude":
            converter_numero(
                buscar(
                    "LATITUDE",
                )
            ),

        "longitude":
            converter_numero(
                buscar(
                    "LONGITUDE",
                )
            ),

        "altitude":
            converter_numero(
                buscar(
                    "ALTITUDE",
                )
            ),

        "data_fundacao":
            buscar(
                "DATA",
                "FUND",
            ),
    }


def identificar_colunas(
    colunas,
):

    mapa = {}


    for coluna in colunas:

        normalizada = normalizar_texto(
            coluna
        )


        if normalizada.startswith(
            "DATA"
        ):

            mapa[
                "data"
            ] = coluna


        elif (
            "HORA"
            in normalizada
            and
            "UTC"
            in normalizada
        ):

            mapa[
                "hora"
            ] = coluna


        elif (
            "TEMPERATURA MAXIMA "
            "NA HORA ANT"
            in normalizada
        ):

            mapa[
                "temperatura"
            ] = coluna


    obrigatorias = {
        "data",
        "hora",
        "temperatura",
    }


    faltantes = (
        obrigatorias
        -
        set(
            mapa.keys()
        )
    )


    if faltantes:

        raise RuntimeError(
            "Colunas obrigatórias "
            f"não encontradas: {faltantes}"
        )


    return mapa


def construir_datetime(
    datas,
    horas,
):

    # ------------------------------------------------------
    # DATA
    # ------------------------------------------------------

    datas = (
        datas.astype(str)
        .str.strip()
        .str.replace(
            "/",
            "-",
            regex=False,
        )
    )


    datas_convertidas = pd.to_datetime(
        datas,
        errors="coerce",
        format="mixed",
    )


    # ------------------------------------------------------
    # HORA
    # ------------------------------------------------------

    horas = (
        horas.astype(str)
        .str.upper()
        .str.replace(
            "UTC",
            "",
            regex=False,
        )
        .str.strip()
    )


    somente_digitos = (
        horas
        .str.replace(
            r"\D",
            "",
            regex=True,
        )
    )


    somente_digitos = (
        somente_digitos
        .str.zfill(4)
    )


    hh = pd.to_numeric(
        somente_digitos.str[
            :2
        ],
        errors="coerce",
    )


    mm = pd.to_numeric(
        somente_digitos.str[
            2:4
        ],
        errors="coerce",
    )


    # ------------------------------------------------------
    # TRATAR 24:00, CASO EXISTA
    # ------------------------------------------------------

    mascara_2400 = (
        (hh == 24)
        &
        (mm == 0)
    )


    hh_corrigida = hh.copy()

    hh_corrigida.loc[
        mascara_2400
    ] = 0


    datetime_utc = (
        datas_convertidas
        +
        pd.to_timedelta(
            hh_corrigida,
            unit="h",
        )
        +
        pd.to_timedelta(
            mm,
            unit="m",
        )
    )


    datetime_utc.loc[
        mascara_2400
    ] = (
        datetime_utc.loc[
            mascara_2400
        ]
        +
        pd.Timedelta(
            days=1
        )
    )


    return datetime_utc


def ler_csv_do_zip(
    zf,
    nome_arquivo,
    ano,
):

    with zf.open(
        nome_arquivo
    ) as arquivo:

        dados = arquivo.read()


    texto = dados.decode(
        "latin-1"
    )


    linhas = texto.splitlines()


    indice_cabecalho = (
        localizar_cabecalho(
            linhas
        )
    )


    metadados = ler_metadados(
        linhas,
        indice_cabecalho,
    )


    codigo = metadados[
        "codigo"
    ]


    if not codigo:

        raise RuntimeError(
            f"Código WMO ausente: "
            f"{nome_arquivo}"
        )


    # ======================================================
    # LER TABELA
    # ======================================================

    df = pd.read_csv(
        io.StringIO(
            texto
        ),
        sep=";",
        skiprows=indice_cabecalho,
        dtype=str,
        encoding_errors="replace",
        low_memory=False,
    )


    # Coluna vazia causada pelo ; final
    df = df.loc[
        :,
        ~df.columns.astype(str)
        .str.startswith(
            "Unnamed"
        )
    ]


    colunas = identificar_colunas(
        df.columns
    )


    # ======================================================
    # DATETIME UTC
    # ======================================================

    datetime_utc = (
        construir_datetime(
            df[
                colunas[
                    "data"
                ]
            ],
            df[
                colunas[
                    "hora"
                ]
            ],
        )
    )


    # ======================================================
    # TEMPERATURA
    # ======================================================

    temperatura_texto = (
        df[
            colunas[
                "temperatura"
            ]
        ]
        .astype(str)
        .str.strip()
        .str.replace(
            ",",
            ".",
            regex=False,
        )
    )


    temperatura = pd.to_numeric(
        temperatura_texto,
        errors="coerce",
    )


    temperatura = temperatura.mask(
        temperatura <= -9990
    )


    # ======================================================
    # ESTATÍSTICAS DO ARQUIVO
    # ======================================================

    total_linhas = len(
        df
    )


    datas_validas = int(
        datetime_utc.notna().sum()
    )


    temperaturas_validas = int(
        temperatura.notna().sum()
    )


    duplicados_datetime = int(
        datetime_utc[
            datetime_utc.notna()
        ].duplicated().sum()
    )


    if datetime_utc.notna().any():

        inicio = (
            datetime_utc.min()
        )

        fim = (
            datetime_utc.max()
        )

    else:

        inicio = pd.NaT
        fim = pd.NaT


    # ======================================================
    # OBSERVAÇÕES QUE REALMENTE USAREMOS
    # ======================================================

    observacoes = pd.DataFrame(
        {
            "codigo":
                codigo,

            "datetime_utc":
                datetime_utc,

            "temp_max_hora_ant_c":
                temperatura,
        }
    )


    # Para comparação ERA5 × INMET precisamos
    # de tempo e temperatura válidos.
    observacoes = (
        observacoes
        .dropna(
            subset=[
                "datetime_utc",
                "temp_max_hora_ant_c",
            ]
        )
        .reset_index(
            drop=True
        )
    )


    # Não aplicamos ainda filtro climatológico.
    # Valores suspeitos serão avaliados no QC.


    catalogo = {

        "ano":
            ano,

        "codigo":
            codigo,

        "estacao":
            metadados[
                "estacao"
            ],

        "regiao":
            metadados[
                "regiao"
            ],

        "uf":
            metadados[
                "uf"
            ],

        "latitude":
            metadados[
                "latitude"
            ],

        "longitude":
            metadados[
                "longitude"
            ],

        "altitude_m":
            metadados[
                "altitude"
            ],

        "data_fundacao":
            metadados[
                "data_fundacao"
            ],

        "arquivo_origem":
            nome_arquivo,

        "linhas_total":
            total_linhas,

        "datetime_validos":
            datas_validas,

        "temperaturas_validas":
            temperaturas_validas,

        "duplicados_datetime":
            duplicados_datetime,

        "primeiro_datetime_utc":
            (
                inicio.isoformat()
                if pd.notna(
                    inicio
                )
                else ""
            ),

        "ultimo_datetime_utc":
            (
                fim.isoformat()
                if pd.notna(
                    fim
                )
                else ""
            ),
    }


    return (
        observacoes,
        catalogo,
    )


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)

print(
    "PREPARAÇÃO DAS ESTAÇÕES AUTOMÁTICAS DO INMET"
)

print("=" * 90)


print(
    f"\nPeríodo: "
    f"{ANO_INICIAL}-{ANO_FINAL}"
)


print(
    "\nEntrada:"
)

print(
    INMET_RAW_DIR
)


print(
    "\nSaída:"
)

print(
    INMET_INTERIM_DIR
)


# ==========================================================
# LISTAS DE RESULTADOS
# ==========================================================

catalogo_total = []

resumo_total = []


# ==========================================================
# PROCESSAR ANO POR ANO
# ==========================================================

for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    print("\n" + "=" * 90)

    print(
        f"ANO {ano}"
    )

    print("=" * 90)


    arquivo_zip = (
        INMET_RAW_DIR
        / f"{ano}.zip"
    )


    arquivo_parquet = (
        INMET_INTERIM_DIR
        / f"inmet_{ano}.parquet"
    )


    if not arquivo_zip.exists():

        raise FileNotFoundError(
            f"ZIP ausente:\n"
            f"{arquivo_zip}"
        )


    # ------------------------------------------------------
    # REFAZER PARQUET SE EXISTIR
    # ------------------------------------------------------

    if arquivo_parquet.exists():

        print(
            "\nRemovendo saída anterior:"
        )

        print(
            arquivo_parquet
        )

        arquivo_parquet.unlink()


    writer = None


    estacoes = 0

    linhas_totais = 0

    observacoes_validas = 0

    erros = []


    try:

        with zipfile.ZipFile(
            arquivo_zip,
            "r",
        ) as zf:

            nomes = sorted(
                nome
                for nome in zf.namelist()
                if (
                    not nome.endswith("/")
                    and
                    nome.lower().endswith(
                        ".csv"
                    )
                )
            )


            print(
                f"\nArquivos CSV: "
                f"{len(nomes)}"
            )


            for indice, nome in enumerate(
                nomes,
                start=1,
            ):

                try:

                    observacoes, catalogo = (
                        ler_csv_do_zip(
                            zf,
                            nome,
                            ano,
                        )
                    )


                    catalogo_total.append(
                        catalogo
                    )


                    estacoes += 1

                    linhas_totais += int(
                        catalogo[
                            "linhas_total"
                        ]
                    )


                    observacoes_validas += len(
                        observacoes
                    )


                    # ======================================
                    # ESCREVER PARQUET INCREMENTALMENTE
                    # ======================================

                    if not observacoes.empty:

                        tabela_arrow = (
                            pa.Table.from_pandas(
                                observacoes,
                                schema=SCHEMA,
                                preserve_index=False,
                            )
                        )


                        if writer is None:

                            writer = (
                                pq.ParquetWriter(
                                    arquivo_parquet,
                                    SCHEMA,
                                    compression="snappy",
                                )
                            )


                        writer.write_table(
                            tabela_arrow
                        )


                except Exception as erro:

                    erros.append(
                        (
                            nome,
                            str(
                                erro
                            ),
                        )
                    )


                if (
                    indice % 50 == 0
                    or indice == len(
                        nomes
                    )
                ):

                    print(
                        f"{indice:4d} / "
                        f"{len(nomes):4d} "
                        "arquivos processados"
                    )


    finally:

        if writer is not None:

            writer.close()


    # ======================================================
    # RESUMO DO ANO
    # ======================================================

    print(
        f"\nEstações processadas: "
        f"{estacoes:,}"
    )


    print(
        f"Linhas horárias originais: "
        f"{linhas_totais:,}"
    )


    print(
        f"Temperaturas válidas: "
        f"{observacoes_validas:,}"
    )


    print(
        f"Erros de arquivos: "
        f"{len(erros):,}"
    )


    if erros:

        print(
            "\nPrimeiros erros:"
        )

        for nome, erro in erros[
            :10
        ]:

            print(
                f"  {nome}"
            )

            print(
                f"    {erro}"
            )


    tamanho_mb = (
        arquivo_parquet.stat().st_size
        /
        1024**2
        if arquivo_parquet.exists()
        else 0
    )


    print(
        f"\nParquet: "
        f"{arquivo_parquet.name}"
    )


    print(
        f"Tamanho: "
        f"{tamanho_mb:.2f} MB"
    )


    resumo_total.append(
        {
            "ano":
                ano,

            "arquivos_csv":
                len(
                    nomes
                ),

            "estacoes_processadas":
                estacoes,

            "linhas_horarias":
                linhas_totais,

            "temperaturas_validas":
                observacoes_validas,

            "arquivos_com_erro":
                len(
                    erros
                ),

            "parquet_mb":
                round(
                    tamanho_mb,
                    2,
                ),
        }
    )


# ==========================================================
# SALVAR CATÁLOGO
# ==========================================================

df_catalogo = pd.DataFrame(
    catalogo_total
)


df_catalogo.to_csv(
    ARQUIVO_CATALOGO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# SALVAR RESUMO
# ==========================================================

df_resumo = pd.DataFrame(
    resumo_total
)


df_resumo.to_csv(
    ARQUIVO_RESUMO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# RESUMO GLOBAL
# ==========================================================

print("\n" + "=" * 90)

print(
    "RESUMO GLOBAL"
)

print("=" * 90)


print(
    f"\nAnos processados: "
    f"{len(df_resumo)}"
)


print(
    f"Arquivos/estações processados: "
    f"{df_resumo['estacoes_processadas'].sum():,}"
)


print(
    f"Linhas horárias originais: "
    f"{df_resumo['linhas_horarias'].sum():,}"
)


print(
    f"Temperaturas máximas válidas: "
    f"{df_resumo['temperaturas_validas'].sum():,}"
)


print(
    f"Arquivos com erro: "
    f"{df_resumo['arquivos_com_erro'].sum():,}"
)


print(
    "\nCatálogo:"
)

print(
    ARQUIVO_CATALOGO
)


print(
    "\nResumo:"
)

print(
    ARQUIVO_RESUMO
)


print(
    "\nParquets:"
)

print(
    INMET_INTERIM_DIR
)


print("\n" + "=" * 90)

print(
    "PREPARAÇÃO CONCLUÍDA"
)

print("=" * 90)