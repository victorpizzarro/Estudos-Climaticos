from pathlib import Path

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

TEMP_MIN_SUSPEITA = -20.0
TEMP_MAX_SUSPEITA = 55.0

DESLOCAMENTO_SUSPEITO_KM = 5.0


INMET_INTERIM_DIR = (
    PROJECT_DIR
    / "data"
    / "interim"
    / "inmet"
    / "automaticas"
)


CATALOGO_ANUAL = (
    TABLES_DIR
    / "catalogo_estacoes_inmet_por_ano.csv"
)


CATALOGO_ESTACOES = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "stations"
    / "catalogo_estacoes_inmet.csv"
)


SAIDA_EXTREMOS = (
    TABLES_DIR
    / "inmet_temperaturas_suspeitas.csv"
)


SAIDA_EXTREMOS_ESTACAO = (
    TABLES_DIR
    / "inmet_temperaturas_suspeitas_por_estacao.csv"
)


SAIDA_COORDENADAS = (
    TABLES_DIR
    / "inmet_coordenadas_suspeitas_detalhadas.csv"
)


# ==========================================================
# FUNÇÃO HAVERSINE
# ==========================================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2,
):

    raio = 6371.0088

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        +
        np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    c = (
        2
        *
        np.arctan2(
            np.sqrt(a),
            np.sqrt(1 - a),
        )
    )

    return raio * c


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("INVESTIGAÇÃO DAS ANOMALIAS INMET")
print("=" * 90)

print(
    "\nNenhum dado será removido."
)

print(
    "Objetivo: identificar a origem das flags do QC."
)


# ==========================================================
# 1. INVESTIGAR TEMPERATURAS SUSPEITAS
# ==========================================================

print("\n" + "=" * 90)
print("TEMPERATURAS SUSPEITAS")
print("=" * 90)


extremos_total = []


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    caminho = (
        INMET_INTERIM_DIR
        / f"inmet_{ano}.parquet"
    )


    df = pd.read_parquet(
        caminho,
        columns=[
            "codigo",
            "datetime_utc",
            "temp_max_hora_ant_c",
        ],
    )


    mascara = (
        (
            df[
                "temp_max_hora_ant_c"
            ]
            < TEMP_MIN_SUSPEITA
        )
        |
        (
            df[
                "temp_max_hora_ant_c"
            ]
            > TEMP_MAX_SUSPEITA
        )
    )


    suspeitos = (
        df.loc[
            mascara
        ]
        .copy()
    )


    if not suspeitos.empty:

        suspeitos[
            "ano"
        ] = ano

        extremos_total.append(
            suspeitos
        )


        print(
            f"\n{ano}: "
            f"{len(suspeitos):,} "
            "observações suspeitas"
        )


        print(
            "Mínimo:",
            suspeitos[
                "temp_max_hora_ant_c"
            ].min(),
        )


        print(
            "Máximo:",
            suspeitos[
                "temp_max_hora_ant_c"
            ].max(),
        )


        print(
            "Estações:",
            suspeitos[
                "codigo"
            ].nunique(),
        )


    del df


# ==========================================================
# CONSOLIDAR EXTREMOS
# ==========================================================

if extremos_total:

    extremos = pd.concat(
        extremos_total,
        ignore_index=True,
    )


    extremos = extremos[
        [
            "ano",
            "codigo",
            "datetime_utc",
            "temp_max_hora_ant_c",
        ]
    ]


    extremos = extremos.sort_values(
        [
            "codigo",
            "datetime_utc",
        ]
    )


    extremos.to_csv(
        SAIDA_EXTREMOS,
        index=False,
        encoding="utf-8",
    )


    # ======================================================
    # RESUMO POR ESTAÇÃO
    # ======================================================

    extremos_estacao = (
        extremos
        .groupby(
            [
                "ano",
                "codigo",
            ]
        )
        .agg(
            observacoes_suspeitas=(
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

            primeiro_evento=(
                "datetime_utc",
                "min",
            ),

            ultimo_evento=(
                "datetime_utc",
                "max",
            ),
        )
        .reset_index()
    )


    extremos_estacao.to_csv(
        SAIDA_EXTREMOS_ESTACAO,
        index=False,
        encoding="utf-8",
    )


    print("\n" + "=" * 90)
    print("RESUMO DOS EXTREMOS")
    print("=" * 90)


    print(
        f"\nObservações suspeitas: "
        f"{len(extremos):,}"
    )


    print(
        f"Estações envolvidas: "
        f"{extremos['codigo'].nunique():,}"
    )


    print(
        "\nEstações com mais ocorrências:"
    )


    ranking = (
        extremos_estacao
        .sort_values(
            "observacoes_suspeitas",
            ascending=False,
        )
        .head(20)
    )


    print(
        ranking.to_string(
            index=False
        )
    )


    print(
        "\nValores mais baixos:"
    )


    print(
        extremos
        .nsmallest(
            30,
            "temp_max_hora_ant_c",
        )
        .to_string(
            index=False
        )
    )


else:

    extremos = pd.DataFrame()

    print(
        "\nNenhuma temperatura suspeita encontrada."
    )


# ==========================================================
# 2. INVESTIGAR COORDENADAS
# ==========================================================

print("\n" + "=" * 90)
print("MUDANÇAS DE COORDENADAS")
print("=" * 90)


catalogo_anual = pd.read_csv(
    CATALOGO_ANUAL
)


catalogo_estacoes = pd.read_csv(
    CATALOGO_ESTACOES
)


for coluna in [
    "latitude",
    "longitude",
]:

    catalogo_anual[
        coluna
    ] = pd.to_numeric(
        catalogo_anual[
            coluna
        ],
        errors="coerce",
    )


suspeitas = catalogo_estacoes[
    (
        catalogo_estacoes[
            "coordenada_suspeita"
        ]
        ==
        True
    )
    |
    (
        catalogo_estacoes[
            "dentro_dominio_era5"
        ]
        ==
        False
    )
].copy()


detalhes_coord = []


for _, estacao in suspeitas.iterrows():

    codigo = estacao[
        "codigo"
    ]


    historico = (
        catalogo_anual[
            catalogo_anual[
                "codigo"
            ]
            ==
            codigo
        ]
        .copy()
    )


    lat_ref = estacao[
        "latitude"
    ]

    lon_ref = estacao[
        "longitude"
    ]


    historico[
        "distancia_ref_km"
    ] = haversine_km(
        historico[
            "latitude"
        ].to_numpy(
            dtype=float
        ),

        historico[
            "longitude"
        ].to_numpy(
            dtype=float
        ),

        lat_ref,
        lon_ref,
    )


    historico[
        "latitude_referencia"
    ] = lat_ref


    historico[
        "longitude_referencia"
    ] = lon_ref


    detalhes_coord.append(
        historico
    )


if detalhes_coord:

    coordenadas = pd.concat(
        detalhes_coord,
        ignore_index=True,
    )


    coordenadas = coordenadas.sort_values(
        [
            "codigo",
            "ano",
        ]
    )


    coordenadas.to_csv(
        SAIDA_COORDENADAS,
        index=False,
        encoding="utf-8",
    )


    print(
        f"\nEstações com coordenadas "
        f"a investigar: "
        f"{suspeitas['codigo'].nunique():,}"
    )


    print(
        "\nMaiores deslocamentos:"
    )


    resumo_coord = (
        coordenadas
        .groupby(
            "codigo"
        )
        .agg(
            estacao=(
                "estacao",
                "first",
            ),

            uf=(
                "uf",
                "first",
            ),

            distancia_max_km=(
                "distancia_ref_km",
                "max",
            ),

            primeiro_ano=(
                "ano",
                "min",
            ),

            ultimo_ano=(
                "ano",
                "max",
            ),
        )
        .reset_index()
        .sort_values(
            "distancia_max_km",
            ascending=False,
        )
    )


    print(
        resumo_coord
        .head(30)
        .to_string(
            index=False
        )
    )


# ==========================================================
# 3. ESTAÇÕES FORA DO DOMÍNIO
# ==========================================================

print("\n" + "=" * 90)
print("ESTAÇÕES FORA DO DOMÍNIO ERA5")
print("=" * 90)


fora = (
    catalogo_estacoes[
        catalogo_estacoes[
            "dentro_dominio_era5"
        ]
        ==
        False
    ]
)


if fora.empty:

    print(
        "\nNenhuma."
    )

else:

    colunas = [
        "codigo",
        "estacao",
        "uf",
        "latitude",
        "longitude",
        "ano_inicio",
        "ano_fim",
    ]


    print(
        "\n",
        fora[
            colunas
        ].to_string(
            index=False
        ),
    )


# ==========================================================
# 4. RESUMO FINAL
# ==========================================================

print("\n" + "=" * 90)
print("ARQUIVOS GERADOS")
print("=" * 90)


if not extremos.empty:

    print(
        "\nTemperaturas suspeitas:"
    )

    print(
        SAIDA_EXTREMOS
    )


    print(
        "\nResumo por estação:"
    )

    print(
        SAIDA_EXTREMOS_ESTACAO
    )


if detalhes_coord:

    print(
        "\nHistórico das coordenadas suspeitas:"
    )

    print(
        SAIDA_COORDENADAS
    )


print("\n" + "=" * 90)
print("INVESTIGAÇÃO CONCLUÍDA")
print("=" * 90)