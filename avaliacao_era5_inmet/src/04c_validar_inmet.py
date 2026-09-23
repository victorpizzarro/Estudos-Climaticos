from pathlib import Path
import math

import numpy as np
import pandas as pd

from config import (
    PROJECT_DIR,
    TABLES_DIR,
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

ANO_INICIAL = 2000
ANO_FINAL = 2025


INMET_INTERIM_DIR = (
    PROJECT_DIR
    / "data"
    / "interim"
    / "inmet"
    / "automaticas"
)


PROCESSED_STATIONS_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "stations"
)


PROCESSED_STATIONS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


CATALOGO_ANUAL = (
    TABLES_DIR
    / "catalogo_estacoes_inmet_por_ano.csv"
)


ARQUIVO_QC_ANUAL = (
    TABLES_DIR
    / "qc_inmet_por_ano.csv"
)


ARQUIVO_QC_ESTACAO_ANO = (
    TABLES_DIR
    / "qc_inmet_estacoes_por_ano.csv"
)


ARQUIVO_ESTACOES = (
    PROCESSED_STATIONS_DIR
    / "catalogo_estacoes_inmet.csv"
)


ARQUIVO_COORDENADAS_SUSPEITAS = (
    TABLES_DIR
    / "estacoes_inmet_coordenadas_suspeitas.csv"
)


# ==========================================================
# LIMITES PARA FLAG, NÃO PARA EXCLUSÃO
# ==========================================================

# Esses limites apenas sinalizam observações suspeitas.
# Nada será removido neste script.

TEMP_MIN_FLAG = -20.0
TEMP_MAX_FLAG = 55.0


# Domínio espacial do nosso ERA5
ERA5_LAT_MIN = -34.0
ERA5_LAT_MAX = 6.0

ERA5_LON_MIN = -74.0
ERA5_LON_MAX = -34.0


# Mudança de coordenada a partir da qual
# queremos investigar a estação.
DESLOCAMENTO_COORD_KM_FLAG = 5.0


# ==========================================================
# FUNÇÕES
# ==========================================================

def moda_ou_primeiro(serie):

    serie = (
        serie
        .dropna()
        .astype(str)
        .str.strip()
    )

    serie = serie[
        serie != ""
    ]

    if serie.empty:
        return None

    moda = serie.mode()

    if not moda.empty:
        return moda.iloc[0]

    return serie.iloc[0]


def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2,
):

    raio_terra = 6371.0088

    lat1 = np.radians(
        lat1
    )

    lon1 = np.radians(
        lon1
    )

    lat2 = np.radians(
        lat2
    )

    lon2 = np.radians(
        lon2
    )


    dlat = (
        lat2
        -
        lat1
    )

    dlon = (
        lon2
        -
        lon1
    )


    a = (
        np.sin(
            dlat / 2
        ) ** 2
        +
        np.cos(
            lat1
        )
        *
        np.cos(
            lat2
        )
        *
        np.sin(
            dlon / 2
        ) ** 2
    )


    c = (
        2
        *
        np.arctan2(
            np.sqrt(a),
            np.sqrt(1 - a),
        )
    )


    return (
        raio_terra
        *
        c
    )


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)

print(
    "CONTROLE DE QUALIDADE DAS ESTAÇÕES AUTOMÁTICAS DO INMET"
)

print("=" * 90)


print(
    "\nIMPORTANTE:"
)

print(
    "Este script apenas identifica problemas."
)

print(
    "Nenhuma observação será removida."
)


# ==========================================================
# 1. CARREGAR CATÁLOGO
# ==========================================================

if not CATALOGO_ANUAL.exists():

    raise FileNotFoundError(
        f"Catálogo não encontrado:\n"
        f"{CATALOGO_ANUAL}"
    )


catalogo = pd.read_csv(
    CATALOGO_ANUAL
)


print(
    f"\nRegistros estação-ano no catálogo: "
    f"{len(catalogo):,}"
)


# ==========================================================
# CONVERTER CAMPOS NUMÉRICOS
# ==========================================================

colunas_numericas = [
    "ano",
    "latitude",
    "longitude",
    "altitude_m",
    "linhas_total",
    "datetime_validos",
    "temperaturas_validas",
    "duplicados_datetime",
]


for coluna in colunas_numericas:

    if coluna in catalogo.columns:

        catalogo[coluna] = (
            pd.to_numeric(
                catalogo[coluna],
                errors="coerce",
            )
        )


# ==========================================================
# 2. COBERTURA ESTAÇÃO-ANO
# ==========================================================

catalogo[
    "cobertura_temp"
] = np.where(
    catalogo[
        "datetime_validos"
    ] > 0,

    catalogo[
        "temperaturas_validas"
    ]
    /
    catalogo[
        "datetime_validos"
    ],

    np.nan,
)


catalogo[
    "cobertura_temp_pct"
] = (
    catalogo[
        "cobertura_temp"
    ]
    *
    100
)


catalogo[
    "cobertura_80_pct"
] = (
    catalogo[
        "cobertura_temp"
    ]
    >= 0.80
)


catalogo[
    "cobertura_90_pct"
] = (
    catalogo[
        "cobertura_temp"
    ]
    >= 0.90
)


# ==========================================================
# 3. DUPLICIDADE NO CATÁLOGO
# ==========================================================

duplicados_estacao_ano = (
    catalogo
    .duplicated(
        subset=[
            "ano",
            "codigo",
        ],
        keep=False,
    )
)


print(
    f"\nRegistros com código repetido "
    f"dentro do mesmo ano: "
    f"{duplicados_estacao_ano.sum():,}"
)


# ==========================================================
# 4. QC DOS PARQUETS ANO A ANO
# ==========================================================

resumo_anos = []

qc_estacao_ano = []


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    print("\n" + "=" * 90)

    print(
        f"ANO {ano}"
    )

    print("=" * 90)


    caminho = (
        INMET_INTERIM_DIR
        / f"inmet_{ano}.parquet"
    )


    if not caminho.exists():

        raise FileNotFoundError(
            f"Parquet ausente:\n"
            f"{caminho}"
        )


    # Só as três colunas necessárias.
    df = pd.read_parquet(
        caminho,
        columns=[
            "codigo",
            "datetime_utc",
            "temp_max_hora_ant_c",
        ],
    )


    total = len(
        df
    )


    # ======================================================
    # NULOS
    # ======================================================

    datetime_nulos = int(
        df[
            "datetime_utc"
        ]
        .isna()
        .sum()
    )


    temperatura_nulos = int(
        df[
            "temp_max_hora_ant_c"
        ]
        .isna()
        .sum()
    )


    codigo_nulos = int(
        df[
            "codigo"
        ]
        .isna()
        .sum()
    )


    # ======================================================
    # ANO INCORRETO
    # ======================================================

    ano_incorreto = int(
        (
            df[
                "datetime_utc"
            ]
            .dt.year
            != ano
        )
        .sum()
    )


    # ======================================================
    # DUPLICADOS
    # ======================================================

    mascara_dup = (
        df
        .duplicated(
            subset=[
                "codigo",
                "datetime_utc",
            ],
            keep=False,
        )
    )


    linhas_duplicadas = int(
        mascara_dup.sum()
    )


    if linhas_duplicadas > 0:

        duplicados = (
            df.loc[
                mascara_dup,
                [
                    "codigo",
                    "datetime_utc",
                    "temp_max_hora_ant_c",
                ],
            ]
        )


        chaves_duplicadas = int(
            duplicados[
                [
                    "codigo",
                    "datetime_utc",
                ]
            ]
            .drop_duplicates()
            .shape[0]
        )


        conflitos = (
            duplicados
            .groupby(
                [
                    "codigo",
                    "datetime_utc",
                ]
            )[
                "temp_max_hora_ant_c"
            ]
            .nunique()
        )


        duplicados_conflitantes = int(
            (
                conflitos
                > 1
            )
            .sum()
        )

    else:

        chaves_duplicadas = 0

        duplicados_conflitantes = 0


    # ======================================================
    # EXTREMOS
    # ======================================================

    temperaturas = (
        df[
            "temp_max_hora_ant_c"
        ]
    )


    abaixo_limite = int(
        (
            temperaturas
            < TEMP_MIN_FLAG
        )
        .sum()
    )


    acima_limite = int(
        (
            temperaturas
            > TEMP_MAX_FLAG
        )
        .sum()
    )


    temp_min = float(
        temperaturas.min()
    )


    temp_max = float(
        temperaturas.max()
    )


    # ======================================================
    # ESTAÇÕES DO ANO
    # ======================================================

    numero_estacoes = int(
        df[
            "codigo"
        ]
        .nunique()
    )


    # ======================================================
    # COMPARAR COM CATÁLOGO
    # ======================================================

    catalogo_ano = (
        catalogo[
            catalogo[
                "ano"
            ]
            == ano
        ]
    )


    esperado_catalogo = int(
        catalogo_ano[
            "temperaturas_validas"
        ]
        .sum()
    )


    contagem_bate = (
        total
        ==
        esperado_catalogo
    )


    # ======================================================
    # QC POR ESTAÇÃO
    # ======================================================

    agrupado = (
        df
        .groupby(
            "codigo",
            sort=False,
        )
        .agg(
            observacoes=(
                "temp_max_hora_ant_c",
                "size",
            ),

            temperatura_min_c=(
                "temp_max_hora_ant_c",
                "min",
            ),

            temperatura_max_c=(
                "temp_max_hora_ant_c",
                "max",
            ),

            primeiro_datetime=(
                "datetime_utc",
                "min",
            ),

            ultimo_datetime=(
                "datetime_utc",
                "max",
            ),
        )
        .reset_index()
    )


    agrupado[
        "ano"
    ] = ano


    qc_estacao_ano.append(
        agrupado
    )


    # ======================================================
    # STATUS E IMPRESSÃO
    # ======================================================

    estrutura_ok = (
        datetime_nulos == 0
        and temperatura_nulos == 0
        and codigo_nulos == 0
        and ano_incorreto == 0
        and duplicados_conflitantes == 0
        and contagem_bate
    )


    status = (
        "OK"
        if estrutura_ok
        else "INVESTIGAR"
    )


    print(
        f"\nObservações: "
        f"{total:,}"
    )


    print(
        f"Estações únicas: "
        f"{numero_estacoes:,}"
    )


    print(
        f"Esperado pelo catálogo: "
        f"{esperado_catalogo:,}"
    )


    print(
        f"Contagem confere: "
        f"{contagem_bate}"
    )


    print(
        f"\nDatetime nulos: "
        f"{datetime_nulos:,}"
    )


    print(
        f"Temperaturas nulas: "
        f"{temperatura_nulos:,}"
    )


    print(
        f"Datas fora do ano: "
        f"{ano_incorreto:,}"
    )


    print(
        f"\nLinhas em horários duplicados: "
        f"{linhas_duplicadas:,}"
    )


    print(
        f"Chaves estação/hora duplicadas: "
        f"{chaves_duplicadas:,}"
    )


    print(
        f"Duplicados com valores conflitantes: "
        f"{duplicados_conflitantes:,}"
    )


    print(
        f"\nTemperatura mínima: "
        f"{temp_min:.2f} °C"
    )


    print(
        f"Temperatura máxima: "
        f"{temp_max:.2f} °C"
    )


    print(
        f"Abaixo de {TEMP_MIN_FLAG:.0f} °C: "
        f"{abaixo_limite:,}"
    )


    print(
        f"Acima de {TEMP_MAX_FLAG:.0f} °C: "
        f"{acima_limite:,}"
    )


    print(
        f"\nSTATUS: "
        f"{status}"
    )


    resumo_anos.append(
        {
            "ano":
                ano,

            "observacoes":
                total,

            "estacoes":
                numero_estacoes,

            "esperado_catalogo":
                esperado_catalogo,

            "contagem_confere":
                contagem_bate,

            "datetime_nulos":
                datetime_nulos,

            "temperatura_nulos":
                temperatura_nulos,

            "codigo_nulos":
                codigo_nulos,

            "datas_fora_ano":
                ano_incorreto,

            "linhas_duplicadas":
                linhas_duplicadas,

            "chaves_duplicadas":
                chaves_duplicadas,

            "duplicados_conflitantes":
                duplicados_conflitantes,

            "temp_min_c":
                temp_min,

            "temp_max_c":
                temp_max,

            "abaixo_flag":
                abaixo_limite,

            "acima_flag":
                acima_limite,

            "status":
                status,
        }
    )


    # Liberar memória antes do próximo ano.
    del df
    del agrupado


# ==========================================================
# 5. SALVAR QC ANUAL
# ==========================================================

df_resumo = pd.DataFrame(
    resumo_anos
)


df_resumo.to_csv(
    ARQUIVO_QC_ANUAL,
    index=False,
    encoding="utf-8",
)


df_qc_estacao_ano = pd.concat(
    qc_estacao_ano,
    ignore_index=True,
)


df_qc_estacao_ano.to_csv(
    ARQUIVO_QC_ESTACAO_ANO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 6. CONSOLIDAR METADADOS POR ESTAÇÃO
# ==========================================================

print("\n" + "=" * 90)

print(
    "CONSOLIDANDO ESTAÇÕES"
)

print("=" * 90)


estacoes = []


for codigo, grupo in catalogo.groupby(
    "codigo"
):

    latitudes = (
        grupo[
            "latitude"
        ]
        .dropna()
        .to_numpy(
            dtype=float
        )
    )


    longitudes = (
        grupo[
            "longitude"
        ]
        .dropna()
        .to_numpy(
            dtype=float
        )
    )


    lat_canonica = float(
        np.nanmedian(
            latitudes
        )
    ) if len(
        latitudes
    ) else np.nan


    lon_canonica = float(
        np.nanmedian(
            longitudes
        )
    ) if len(
        longitudes
    ) else np.nan


    # ======================================================
    # DISTÂNCIA DAS COORDENADAS HISTÓRICAS
    # ATÉ A POSIÇÃO CANÔNICA
    # ======================================================

    grupo_coord = (
        grupo[
            [
                "latitude",
                "longitude",
            ]
        ]
        .dropna()
    )


    if (
        not grupo_coord.empty
        and
        np.isfinite(
            lat_canonica
        )
        and
        np.isfinite(
            lon_canonica
        )
    ):

        distancias = (
            haversine_km(
                grupo_coord[
                    "latitude"
                ].to_numpy(
                    dtype=float
                ),

                grupo_coord[
                    "longitude"
                ].to_numpy(
                    dtype=float
                ),

                lat_canonica,

                lon_canonica,
            )
        )


        deslocamento_max = float(
            np.max(
                distancias
            )
        )

    else:

        deslocamento_max = np.nan


    # ======================================================
    # COBERTURA
    # ======================================================

    coberturas = (
        grupo[
            "cobertura_temp"
        ]
        .dropna()
    )


    cobertura_mediana = (
        float(
            coberturas.median()
        )
        if not coberturas.empty
        else np.nan
    )


    anos_80 = int(
        grupo[
            "cobertura_80_pct"
        ]
        .sum()
    )


    anos_90 = int(
        grupo[
            "cobertura_90_pct"
        ]
        .sum()
    )


    # ======================================================
    # DOMÍNIO ERA5
    # ======================================================

    dentro_era5 = bool(
        np.isfinite(
            lat_canonica
        )
        and
        np.isfinite(
            lon_canonica
        )
        and
        ERA5_LAT_MIN
        <= lat_canonica
        <= ERA5_LAT_MAX
        and
        ERA5_LON_MIN
        <= lon_canonica
        <= ERA5_LON_MAX
    )


    coordenada_suspeita = bool(
        np.isfinite(
            deslocamento_max
        )
        and
        deslocamento_max
        >
        DESLOCAMENTO_COORD_KM_FLAG
    )


    estacoes.append(
        {
            "codigo":
                codigo,

            "estacao":
                moda_ou_primeiro(
                    grupo[
                        "estacao"
                    ]
                ),

            "uf":
                moda_ou_primeiro(
                    grupo[
                        "uf"
                    ]
                ),

            "regiao":
                moda_ou_primeiro(
                    grupo[
                        "regiao"
                    ]
                ),

            "latitude":
                lat_canonica,

            "longitude":
                lon_canonica,

            "altitude_m":
                float(
                    grupo[
                        "altitude_m"
                    ]
                    .median()
                )
                if grupo[
                    "altitude_m" 
                ]
                .notna()
                .any()
                else np.nan,

            "ano_inicio":
                int(
                    grupo[
                        "ano"
                    ].min()
                ),

            "ano_fim":
                int(
                    grupo[
                        "ano"
                    ].max()
                ),

            "anos_presentes":
                int(
                    grupo[
                        "ano"
                    ].nunique()
                ),

            "anos_cobertura_80":
                anos_80,

            "anos_cobertura_90":
                anos_90,

            "cobertura_mediana":
                cobertura_mediana,

            "observacoes_validas":
                int(
                    grupo[
                        "temperaturas_validas"
                    ]
                    .sum()
                ),

            "deslocamento_max_coord_km":
                deslocamento_max,

            "coordenada_suspeita":
                coordenada_suspeita,

            "dentro_dominio_era5":
                dentro_era5,
        }
    )


df_estacoes = pd.DataFrame(
    estacoes
)


df_estacoes = (
    df_estacoes
    .sort_values(
        "codigo"
    )
    .reset_index(
        drop=True
    )
)


df_estacoes.to_csv(
    ARQUIVO_ESTACOES,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 7. COORDENADAS SUSPEITAS
# ==========================================================

df_coord_suspeitas = (
    df_estacoes[
        (
            df_estacoes[
                "coordenada_suspeita"
            ]
        )
        |
        (
            ~df_estacoes[
                "dentro_dominio_era5"
            ]
        )
    ]
    .copy()
)


df_coord_suspeitas.to_csv(
    ARQUIVO_COORDENADAS_SUSPEITAS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 8. RESUMO GLOBAL
# ==========================================================

print("\n" + "=" * 90)

print(
    "RESUMO GLOBAL DO QC"
)

print("=" * 90)


print(
    f"\nEstações únicas: "
    f"{len(df_estacoes):,}"
)


print(
    f"Estações dentro do domínio ERA5: "
    f"{df_estacoes['dentro_dominio_era5'].sum():,}"
)


print(
    f"Estações fora do domínio ERA5: "
    f"{(~df_estacoes['dentro_dominio_era5']).sum():,}"
)


print(
    f"\nEstações com mudança de coordenada "
    f"> {DESLOCAMENTO_COORD_KM_FLAG:.0f} km: "
    f"{df_estacoes['coordenada_suspeita'].sum():,}"
)


print(
    f"\nEstações com pelo menos "
    f"10 anos presentes: "
    f"{(df_estacoes['anos_presentes'] >= 10).sum():,}"
)


print(
    f"Estações com pelo menos "
    f"15 anos presentes: "
    f"{(df_estacoes['anos_presentes'] >= 15).sum():,}"
)


print(
    f"Estações com pelo menos "
    f"20 anos presentes: "
    f"{(df_estacoes['anos_presentes'] >= 20).sum():,}"
)


print(
    f"\nEstações com pelo menos "
    f"10 anos e cobertura >=80%: "
    f"{(df_estacoes['anos_cobertura_80'] >= 10).sum():,}"
)


print(
    f"Estações com pelo menos "
    f"15 anos e cobertura >=80%: "
    f"{(df_estacoes['anos_cobertura_80'] >= 15).sum():,}"
)


print(
    "\nArquivos gerados:"
)


print(
    ARQUIVO_QC_ANUAL
)


print(
    ARQUIVO_QC_ESTACAO_ANO
)


print(
    ARQUIVO_ESTACOES
)


print(
    ARQUIVO_COORDENADAS_SUSPEITAS
)


print("\n" + "=" * 90)

print(
    "CONTROLE DE QUALIDADE CONCLUÍDO"
)

print("=" * 90)