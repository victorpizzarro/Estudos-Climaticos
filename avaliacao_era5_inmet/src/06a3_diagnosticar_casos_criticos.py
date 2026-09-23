from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    PROJECT_DIR,
    TABLES_DIR,
)


# ==========================================================
# CAMINHOS
# ==========================================================

ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


MATCHES_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "matches"
)


METRICAS_FILE = (
    ANNUAL_DIR
    / "metricas_era5_inmet_estacao_ano_revisadas.parquet"
)


MATCH_FILE = (
    MATCHES_DIR
    / "inmet_era5_estacao_ano.csv"
)


MENSAL_FILE = (
    TABLES_DIR
    / "diagnostico_mensal_estacoes_suspeitas.csv"
)


SAIDA_CRITICOS = (
    TABLES_DIR
    / "casos_criticos_era5_inmet.csv"
)


SAIDA_ESTACOES = (
    TABLES_DIR
    / "resumo_estacoes_criticas_era5_inmet.csv"
)


SAIDA_CHAVE = (
    TABLES_DIR
    / "diagnostico_casos_chave_era5_inmet.csv"
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

MIN_PARES_ANALISE = 100


CASOS_CHAVE = {
    "A402",
    "A355",
    "A316",
    "A610",
}


# ==========================================================
# HAVERSINE
# ==========================================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2,
):

    if any(
        pd.isna(x)
        for x in [
            lat1,
            lon1,
            lat2,
            lon2,
        ]
    ):
        return np.nan


    raio = 6371.0088


    lat1 = np.radians(
        float(lat1)
    )

    lon1 = np.radians(
        float(lon1)
    )

    lat2 = np.radians(
        float(lat2)
    )

    lon2 = np.radians(
        float(lon2)
    )


    dlat = lat2 - lat1
    dlon = lon2 - lon1


    a = (
        np.sin(
            dlat / 2
        ) ** 2
        +
        np.cos(lat1)
        *
        np.cos(lat2)
        *
        np.sin(
            dlon / 2
        ) ** 2
    )


    return (
        raio
        *
        2
        *
        np.arctan2(
            np.sqrt(a),
            np.sqrt(1 - a),
        )
    )


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("DIAGNÓSTICO FINAL DOS CASOS CRÍTICOS ERA5 × INMET")
print("=" * 90)


# ==========================================================
# 1. CARREGAR
# ==========================================================

metricas = pd.read_parquet(
    METRICAS_FILE
)


matches = pd.read_csv(
    MATCH_FILE
)


print(
    f"\nMétricas estação-ano: "
    f"{len(metricas):,}"
)


print(
    f"Registros espaciais: "
    f"{len(matches):,}"
)


# ==========================================================
# 2. GARANTIR TIPOS
# ==========================================================

for coluna in [
    "ano",
    "grid_index",
]:

    metricas[coluna] = pd.to_numeric(
        metricas[coluna],
        errors="coerce",
    )


for coluna in [
    "latitude_inmet",
    "longitude_inmet",
    "altitude_inmet_m",
    "distancia_centro_km",
]:

    metricas[coluna] = pd.to_numeric(
        metricas[coluna],
        errors="coerce",
    )


# ==========================================================
# 3. DEFINIR FLAGS REALMENTE ANALÍTICAS
# ==========================================================

flags_desempenho = [
    "flag_bias_extremo",
    "flag_rmse_extremo",
    "flag_correlacao_baixa",
    "flag_salto_bias_historico",
    "flag_salto_rmse_historico",
]


for coluna in flags_desempenho:

    if metricas[coluna].dtype != bool:

        metricas[coluna] = (
            metricas[coluna]
            .astype(str)
            .str.lower()
            .map(
                {
                    "true": True,
                    "false": False,
                    "1": True,
                    "0": False,
                }
            )
            .fillna(False)
        )


metricas[
    "flag_desempenho"
] = (
    metricas[
        flags_desempenho
    ]
    .any(
        axis=1
    )
)


metricas[
    "amostra_suficiente"
] = (
    metricas[
        "n_pares"
    ]
    >=
    MIN_PARES_ANALISE
)


# ==========================================================
# 4. CATEGORIZAR
# ==========================================================

def categoria(
    linha,
):

    if (
        linha[
            "n_pares"
        ]
        <
        MIN_PARES_ANALISE
    ):

        return (
            "amostra_insuficiente"
        )


    if (
        linha[
            "flag_salto_bias_historico"
        ]
        or
        linha[
            "flag_salto_rmse_historico"
        ]
    ):

        return (
            "anomalia_temporal"
        )


    if (
        linha[
            "flag_bias_extremo"
        ]
        or
        linha[
            "flag_rmse_extremo"
        ]
        or
        linha[
            "flag_correlacao_baixa"
        ]
    ):

        return (
            "desempenho_extremo"
        )


    return (
        "sem_anomalia_desempenho"
    )


metricas[
    "categoria_diagnostico"
] = metricas.apply(
    categoria,
    axis=1,
)


# ==========================================================
# 5. HISTÓRICO ANO ANTERIOR / POSTERIOR
# ==========================================================

metricas = metricas.sort_values(
    [
        "codigo",
        "ano",
    ]
).reset_index(
    drop=True
)


grupo = metricas.groupby(
    "codigo",
    sort=False,
)


colunas_historicas = [
    "ano",
    "grid_index",
    "latitude_inmet",
    "longitude_inmet",
    "altitude_inmet_m",
    "bias_c",
    "rmse_c",
    "correlacao_pearson",
]


for coluna in colunas_historicas:

    metricas[
        f"{coluna}_anterior"
    ] = grupo[
        coluna
    ].shift(1)


    metricas[
        f"{coluna}_posterior"
    ] = grupo[
        coluna
    ].shift(-1)


# ==========================================================
# 6. VERIFICAR SE ANOS SÃO CONSECUTIVOS
# ==========================================================

metricas[
    "anterior_consecutivo"
] = (
    metricas[
        "ano"
    ]
    -
    metricas[
        "ano_anterior"
    ]
    ==
    1
)


metricas[
    "posterior_consecutivo"
] = (
    metricas[
        "ano_posterior"
    ]
    -
    metricas[
        "ano"
    ]
    ==
    1
)


# ==========================================================
# 7. MUDANÇA DE CÉLULA
# ==========================================================

metricas[
    "mudou_celula_vs_anterior"
] = (
    metricas[
        "anterior_consecutivo"
    ]
    &
    (
        metricas[
            "grid_index"
        ]
        !=
        metricas[
            "grid_index_anterior"
        ]
    )
)


metricas[
    "mudou_celula_vs_posterior"
] = (
    metricas[
        "posterior_consecutivo"
    ]
    &
    (
        metricas[
            "grid_index"
        ]
        !=
        metricas[
            "grid_index_posterior"
        ]
    )
)


# ==========================================================
# 8. DISTÂNCIA DA MUDANÇA DE COORDENADA
# ==========================================================

def calcular_dist_anterior(
    linha,
):

    if not linha[
        "anterior_consecutivo"
    ]:

        return np.nan


    return haversine_km(
        linha[
            "latitude_inmet"
        ],
        linha[
            "longitude_inmet"
        ],
        linha[
            "latitude_inmet_anterior"
        ],
        linha[
            "longitude_inmet_anterior"
        ],
    )


metricas[
    "mudanca_coord_vs_anterior_km"
] = metricas.apply(
    calcular_dist_anterior,
    axis=1,
)


# ==========================================================
# 9. MUDANÇA DE ALTITUDE
# ==========================================================

metricas[
    "mudanca_altitude_vs_anterior_m"
] = np.where(
    metricas[
        "anterior_consecutivo"
    ],

    metricas[
        "altitude_inmet_m"
    ]
    -
    metricas[
        "altitude_inmet_m_anterior"
    ],

    np.nan,
)


# ==========================================================
# 10. MUDANÇAS DAS MÉTRICAS
# ==========================================================

metricas[
    "delta_bias_vs_anterior"
] = np.where(
    metricas[
        "anterior_consecutivo"
    ],

    metricas[
        "bias_c"
    ]
    -
    metricas[
        "bias_c_anterior"
    ],

    np.nan,
)


metricas[
    "delta_rmse_vs_anterior"
] = np.where(
    metricas[
        "anterior_consecutivo"
    ],

    metricas[
        "rmse_c"
    ]
    -
    metricas[
        "rmse_c_anterior"
    ],

    np.nan,
)


metricas[
    "delta_correlacao_vs_anterior"
] = np.where(
    metricas[
        "anterior_consecutivo"
    ],

    metricas[
        "correlacao_pearson"
    ]
    -
    metricas[
        "correlacao_pearson_anterior"
    ],

    np.nan,
)


# ==========================================================
# 11. CASOS CRÍTICOS
# ==========================================================

criticos = metricas[
    (
        metricas[
            "flag_desempenho"
        ]
    )
    |
    (
        ~metricas[
            "amostra_suficiente"
        ]
    )
].copy()


criticos = criticos.sort_values(
    [
        "categoria_diagnostico",
        "codigo",
        "ano",
    ]
)


criticos.to_csv(
    SAIDA_CRITICOS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 12. RESUMO POR ESTAÇÃO
# ==========================================================

resumo_estacoes = (
    metricas
    .groupby(
        [
            "codigo",
            "estacao",
            "uf",
        ],
        dropna=False,
    )
    .agg(
        anos_total=(
            "ano",
            "nunique",
        ),

        anos_desempenho_extremo=(
            "flag_desempenho",
            "sum",
        ),

        bias_mediano_c=(
            "bias_c",
            "median",
        ),

        rmse_mediano_c=(
            "rmse_c",
            "median",
        ),

        correlacao_mediana=(
            "correlacao_pearson",
            "median",
        ),

        bias_min_c=(
            "bias_c",
            "min",
        ),

        bias_max_c=(
            "bias_c",
            "max",
        ),

        rmse_max_c=(
            "rmse_c",
            "max",
        ),
    )
    .reset_index()
)


resumo_estacoes[
    "pct_anos_desempenho_extremo"
] = (
    resumo_estacoes[
        "anos_desempenho_extremo"
    ]
    /
    resumo_estacoes[
        "anos_total"
    ]
    *
    100
)


resumo_estacoes[
    "comportamento_persistente"
] = (
    (
        resumo_estacoes[
            "anos_desempenho_extremo"
        ]
        >= 3
    )
    &
    (
        resumo_estacoes[
            "pct_anos_desempenho_extremo"
        ]
        >= 50
    )
)


resumo_estacoes.to_csv(
    SAIDA_ESTACOES,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 13. CASOS CHAVE
# ==========================================================

casos_chave = (
    metricas[
        metricas[
            "codigo"
        ]
        .isin(
            CASOS_CHAVE
        )
    ]
    .copy()
)


casos_chave.to_csv(
    SAIDA_CHAVE,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 14. IMPRESSÃO GERAL
# ==========================================================

print("\n" + "=" * 90)
print("CLASSIFICAÇÃO DOS CASOS")
print("=" * 90)


print(
    metricas[
        "categoria_diagnostico"
    ]
    .value_counts()
    .to_string()
)


print(
    f"\nCasos com problema de desempenho: "
    f"{metricas['flag_desempenho'].sum():,}"
)


print(
    f"Casos com menos de "
    f"{MIN_PARES_ANALISE} pares: "
    f"{(~metricas['amostra_suficiente']).sum():,}"
)


print(
    f"\nEstações com comportamento extremo "
    f"persistente: "
    f"{resumo_estacoes['comportamento_persistente'].sum():,}"
)


print(
    "\nEstações persistentes:"
)


persistentes = (
    resumo_estacoes[
        resumo_estacoes[
            "comportamento_persistente"
        ]
    ]
    .sort_values(
        "anos_desempenho_extremo",
        ascending=False,
    )
)


if persistentes.empty:

    print(
        "Nenhuma."
    )

else:

    print(
        persistentes[
            [
                "codigo",
                "estacao",
                "uf",
                "anos_total",
                "anos_desempenho_extremo",
                "pct_anos_desempenho_extremo",
                "bias_mediano_c",
                "rmse_mediano_c",
                "correlacao_mediana",
            ]
        ]
        .head(30)
        .to_string(
            index=False
        )
    )


# ==========================================================
# 15. CASOS CHAVE DETALHADOS
# ==========================================================

print("\n" + "=" * 90)
print("CASOS CHAVE")
print("=" * 90)


colunas_print = [
    "ano",
    "codigo",
    "estacao",
    "uf",
    "n_pares",
    "cobertura_temp",

    "grid_index",
    "mudou_celula_vs_anterior",

    "altitude_inmet_m",
    "mudanca_altitude_vs_anterior_m",

    "mudanca_coord_vs_anterior_km",

    "bias_c",
    "bias_c_anterior",
    "delta_bias_vs_anterior",

    "rmse_c",
    "rmse_c_anterior",
    "delta_rmse_vs_anterior",

    "correlacao_pearson",
    "correlacao_pearson_anterior",

    "categoria_diagnostico",
]


for codigo in sorted(
    CASOS_CHAVE
):

    print("\n" + "-" * 90)

    print(
        codigo
    )

    print("-" * 90)


    dados = (
        casos_chave[
            casos_chave[
                "codigo"
            ]
            ==
            codigo
        ]
    )


    print(
        dados[
            colunas_print
        ]
        .to_string(
            index=False
        )
    )


# ==========================================================
# 16. DIAGNÓSTICO MENSAL DOS CASOS CHAVE
# ==========================================================

print("\n" + "=" * 90)
print("DIAGNÓSTICO MENSAL DOS CASOS CHAVE")
print("=" * 90)


if MENSAL_FILE.exists():

    mensal = pd.read_csv(
        MENSAL_FILE
    )


    mensal_chave = (
        mensal[
            mensal[
                "codigo"
            ]
            .isin(
                CASOS_CHAVE
            )
        ]
        .copy()
    )


    # Só imprimir anos de interesse para não
    # transformar o terminal num romance russo.

    mascara_interesse = (
        (
            (
                mensal_chave[
                    "codigo"
                ]
                ==
                "A402"
            )
            &
            (
                mensal_chave[
                    "ano"
                ]
                ==
                2005
            )
        )
        |
        (
            (
                mensal_chave[
                    "codigo"
                ]
                ==
                "A355"
            )
            &
            (
                mensal_chave[
                    "ano"
                ]
                ==
                2015
            )
        )
        |
        (
            (
                mensal_chave[
                    "codigo"
                ]
                ==
                "A316"
            )
            &
            (
                mensal_chave[
                    "ano"
                ]
                .isin(
                    [
                        2014,
                        2015,
                    ]
                )
            )
        )
        |
        (
            (
                mensal_chave[
                    "codigo"
                ]
                ==
                "A610"
            )
            &
            (
                mensal_chave[
                    "ano"
                ]
                .isin(
                    [
                        2012,
                        2018,
                        2024,
                        2025,
                    ]
                )
            )
        )
    )


    mensal_interesse = mensal_chave[
        mascara_interesse
    ]


    print(
        mensal_interesse[
            [
                "ano",
                "codigo",
                "mes",
                "n_pares",
                "media_inmet_c",
                "media_era5_c",
                "bias_c",
                "mae_c",
                "rmse_c",
                "correlacao",
            ]
        ]
        .sort_values(
            [
                "codigo",
                "ano",
                "mes",
            ]
        )
        .to_string(
            index=False
        )
    )


else:

    print(
        "\nArquivo mensal não encontrado:"
    )

    print(
        MENSAL_FILE
    )


# ==========================================================
# 17. RESUMO FINAL
# ==========================================================

print("\n" + "=" * 90)
print("ARQUIVOS GERADOS")
print("=" * 90)


print(
    "\nCasos críticos:"
)

print(
    SAIDA_CRITICOS
)


print(
    "\nResumo por estação:"
)

print(
    SAIDA_ESTACOES
)


print(
    "\nCasos chave:"
)

print(
    SAIDA_CHAVE
)


print("\n" + "=" * 90)
print("DIAGNÓSTICO CONCLUÍDO")
print("=" * 90)