from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from config import (
    PROJECT_DIR,
    TABLES_DIR,
)


# ==========================================================
# CAMINHOS
# ==========================================================

MATCHES_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "matches"
)


PARES_DIR = (
    MATCHES_DIR
    / "horarios"
)


ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


STATIONS_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "stations"
)


AMOSTRA_FILE = (
    ANNUAL_DIR
    / "amostra_analitica_estacao_ano.parquet"
)


CATALOGO_ESTACOES = (
    STATIONS_DIR
    / "catalogo_estacoes_inmet.csv"
)


SAIDA_PARQUET = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "stations"
    / "metricas_era5_inmet_por_estacao.parquet"
)


SAIDA_CSV = (
    TABLES_DIR
    / "metricas_era5_inmet_por_estacao.csv"
)


SAIDA_RANKING = (
    TABLES_DIR
    / "ranking_diagnostico_estacoes_era5_inmet.csv"
)


SAIDA_RESUMO = (
    TABLES_DIR
    / "resumo_metricas_por_estacao.csv"
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

MIN_PARES_INTERPRETACAO = 100


# ==========================================================
# AUXILIAR SQL
# ==========================================================

def sql_path(caminho):

    return str(
        caminho.resolve()
    ).replace(
        "'",
        "''",
    )


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("MÉTRICAS ERA5 × INMET POR ESTAÇÃO")
print("=" * 90)

print(
    "\nAs métricas serão recalculadas "
    "diretamente dos pares horários."
)

print(
    "\nerro = ERA5 - INMET"
)

print(
    "Bias < 0 → ERA5 subestima"
)

print(
    "Bias > 0 → ERA5 superestima"
)


# ==========================================================
# 1. VERIFICAR ARQUIVOS
# ==========================================================

if not AMOSTRA_FILE.exists():

    raise FileNotFoundError(
        f"Amostra analítica não encontrada:\n"
        f"{AMOSTRA_FILE}"
    )


if not CATALOGO_ESTACOES.exists():

    raise FileNotFoundError(
        f"Catálogo de estações não encontrado:\n"
        f"{CATALOGO_ESTACOES}"
    )


arquivos_pares = sorted(
    PARES_DIR.glob(
        "era5_inmet_pares_*.parquet"
    )
)


if len(arquivos_pares) != 26:

    raise RuntimeError(
        "Esperávamos 26 Parquets horários "
        f"e encontramos {len(arquivos_pares)}."
    )


# ==========================================================
# 2. DUCKDB
# ==========================================================

con = duckdb.connect(
    database=":memory:"
)


con.execute(
    "SET memory_limit = '4GB'"
)


con.execute(
    "SET threads = 4"
)


amostra_sql = sql_path(
    AMOSTRA_FILE
)


glob_pares = sql_path(
    PARES_DIR
    / "era5_inmet_pares_*.parquet"
)


# ==========================================================
# 3. CARREGAR MÁSCARA ESTAÇÃO-ANO
# ==========================================================

print("\n" + "=" * 90)
print("CARREGANDO AMOSTRA ANALÍTICA")
print("=" * 90)


con.execute(
    f"""
    CREATE TABLE amostra AS

    SELECT

        CAST(
            ano
            AS INTEGER
        ) AS ano,

        CAST(
            codigo
            AS VARCHAR
        ) AS codigo,

        CAST(
            usar_validacao_principal
            AS BOOLEAN
        ) AS usar_validacao_principal,

        CAST(
            usar_tendencia_10a
            AS BOOLEAN
        ) AS usar_tendencia_10a,

        CAST(
            usar_tendencia_15a
            AS BOOLEAN
        ) AS usar_tendencia_15a

    FROM read_parquet(
        '{amostra_sql}'
    )
    """
)


n_amostra = con.execute(
    """
    SELECT COUNT(*)
    FROM amostra
    """
).fetchone()[0]


print(
    f"\nRegistros estação-ano: "
    f"{n_amostra:,}"
)


# ==========================================================
# 4. FUNÇÃO DE AGREGAÇÃO
# ==========================================================

def calcular_metricas(
    nome_amostra,
    filtro_sql,
):

    print("\n" + "=" * 90)

    print(
        f"CALCULANDO: {nome_amostra}"
    )

    print("=" * 90)


    consulta = f"""
        SELECT

            CAST(
                p.codigo
                AS VARCHAR
            ) AS codigo,


            COUNT(*)
                AS n_pares,


            COUNT(
                DISTINCT p.ano
            )
                AS anos_com_dados,


            MIN(
                p.ano
            )
                AS primeiro_ano,


            MAX(
                p.ano
            )
                AS ultimo_ano,


            AVG(
                CAST(
                    p.temp_inmet_c
                    AS DOUBLE
                )
            )
                AS media_inmet_c,


            AVG(
                CAST(
                    p.temp_era5_c
                    AS DOUBLE
                )
            )
                AS media_era5_c,


            AVG(
                CAST(
                    p.erro_c
                    AS DOUBLE
                )
            )
                AS bias_c,


            AVG(
                ABS(
                    CAST(
                        p.erro_c
                        AS DOUBLE
                    )
                )
            )
                AS mae_c,


            SQRT(
                AVG(
                    POWER(
                        CAST(
                            p.erro_c
                            AS DOUBLE
                        ),
                        2
                    )
                )
            )
                AS rmse_c,


            CORR(
                CAST(
                    p.temp_era5_c
                    AS DOUBLE
                ),

                CAST(
                    p.temp_inmet_c
                    AS DOUBLE
                )
            )
                AS correlacao_pearson,


            STDDEV_SAMP(
                CAST(
                    p.erro_c
                    AS DOUBLE
                )
            )
                AS desvio_erro_c,


            MIN(
                CAST(
                    p.erro_c
                    AS DOUBLE
                )
            )
                AS erro_min_c,


            QUANTILE_CONT(
                CAST(
                    p.erro_c
                    AS DOUBLE
                ),
                0.05
            )
                AS erro_p05_c,


            QUANTILE_CONT(
                CAST(
                    p.erro_c
                    AS DOUBLE
                ),
                0.50
            )
                AS erro_mediana_c,


            QUANTILE_CONT(
                CAST(
                    p.erro_c
                    AS DOUBLE
                ),
                0.95
            )
                AS erro_p95_c,


            MAX(
                CAST(
                    p.erro_c
                    AS DOUBLE
                )
            )
                AS erro_max_c,


            MAX(
                ABS(
                    CAST(
                        p.erro_c
                        AS DOUBLE
                    )
                )
            )
                AS erro_abs_max_c,


            SUM(
                CASE

                    WHEN ABS(
                        CAST(
                            p.erro_c
                            AS DOUBLE
                        )
                    ) > 5

                    THEN 1

                    ELSE 0

                END
            )
                AS n_abs_erro_gt5,


            SUM(
                CASE

                    WHEN ABS(
                        CAST(
                            p.erro_c
                            AS DOUBLE
                        )
                    ) > 10

                    THEN 1

                    ELSE 0

                END
            )
                AS n_abs_erro_gt10,


            SUM(
                CASE

                    WHEN ABS(
                        CAST(
                            p.erro_c
                            AS DOUBLE
                        )
                    ) > 20

                    THEN 1

                    ELSE 0

                END
            )
                AS n_abs_erro_gt20


        FROM read_parquet(
            '{glob_pares}'
        ) AS p


        INNER JOIN amostra AS a

            ON p.codigo
                =
               a.codigo

            AND p.ano
                =
               a.ano


        WHERE
            {filtro_sql}


        GROUP BY
            p.codigo


        ORDER BY
            p.codigo
    """


    df = con.execute(
        consulta
    ).fetchdf()


    # ======================================================
    # PERCENTUAIS
    # ======================================================

    for limite in [
        5,
        10,
        20,
    ]:

        df[
            f"pct_abs_erro_gt{limite}"
        ] = (
            df[
                f"n_abs_erro_gt{limite}"
            ]
            /
            df[
                "n_pares"
            ]
            *
            100
        )


    print(
        f"\nEstações: "
        f"{len(df):,}"
    )


    print(
        f"Pares utilizados: "
        f"{df['n_pares'].sum():,}"
    )


    return df


# ==========================================================
# 5. AMOSTRA COMPLETA
# ==========================================================

completa = calcular_metricas(
    "AMOSTRA COMPLETA",
    "TRUE",
)


# ==========================================================
# 6. AMOSTRA PRINCIPAL
# ==========================================================

principal = calcular_metricas(
    "VALIDAÇÃO PRINCIPAL",
    "a.usar_validacao_principal = TRUE",
)


con.close()


# ==========================================================
# 7. RENOMEAR COLUNAS DA COMPLETA
# ==========================================================

chaves = [
    "codigo"
]


colunas_completa = {
    coluna:
        f"{coluna}_completa"

    for coluna in completa.columns

    if coluna not in chaves
}


completa = completa.rename(
    columns=colunas_completa
)


# ==========================================================
# 8. JUNTAR PRINCIPAL + COMPLETA
# ==========================================================

resultado = principal.merge(
    completa,
    on="codigo",
    how="outer",
    validate="one_to_one",
)


# ==========================================================
# 9. METADADOS DAS ESTAÇÕES
# ==========================================================

catalogo = pd.read_csv(
    CATALOGO_ESTACOES
)


catalogo = (
    catalogo
    .sort_values(
        "codigo"
    )
    .drop_duplicates(
        subset=[
            "codigo"
        ]
    )
)


metadata_cols = [
    "codigo",
    "estacao",
    "uf",
    "regiao",
    "latitude",
    "longitude",
    "altitude_m",
    "anos_presentes",
    "anos_cobertura_80",
    "anos_cobertura_90",
    "cobertura_mediana",
    "deslocamento_max_coord_km",
    "coordenada_suspeita",
    "dentro_dominio_era5",
]


metadata_cols = [
    coluna
    for coluna in metadata_cols
    if coluna in catalogo.columns
]


resultado = resultado.merge(
    catalogo[
        metadata_cols
    ],
    on="codigo",
    how="left",
    validate="one_to_one",
)


# ==========================================================
# 10. DIFERENÇA PRINCIPAL × COMPLETA
# ==========================================================

resultado[
    "pares_removidos_qc"
] = (
    resultado[
        "n_pares_completa"
    ]
    -
    resultado[
        "n_pares"
    ]
)


resultado[
    "pct_pares_removidos_qc"
] = (
    resultado[
        "pares_removidos_qc"
    ]
    /
    resultado[
        "n_pares_completa"
    ]
    *
    100
)


resultado[
    "delta_bias_qc_c"
] = (
    resultado[
        "bias_c"
    ]
    -
    resultado[
        "bias_c_completa"
    ]
)


resultado[
    "delta_mae_qc_c"
] = (
    resultado[
        "mae_c"
    ]
    -
    resultado[
        "mae_c_completa"
    ]
)


resultado[
    "delta_rmse_qc_c"
] = (
    resultado[
        "rmse_c"
    ]
    -
    resultado[
        "rmse_c_completa"
    ]
)


resultado[
    "delta_correlacao_qc"
] = (
    resultado[
        "correlacao_pearson"
    ]
    -
    resultado[
        "correlacao_pearson_completa"
    ]
)


# ==========================================================
# 11. FLAGS DE INTERPRETAÇÃO
# ==========================================================

resultado[
    "amostra_interpretavel"
] = (
    resultado[
        "n_pares"
    ]
    >=
    MIN_PARES_INTERPRETACAO
)


# Número de células ERA5 usadas ao longo
# da história de cada código.

mapa_file = (
    MATCHES_DIR
    / "inmet_era5_estacao_ano.csv"
)


mapa = pd.read_csv(
    mapa_file
)


n_celulas = (
    mapa
    .groupby(
        "codigo"
    )[
        "grid_index"
    ]
    .nunique()
    .rename(
        "n_celulas_era5_historico"
    )
    .reset_index()
)


resultado = resultado.merge(
    n_celulas,
    on="codigo",
    how="left",
    validate="one_to_one",
)


resultado[
    "mudou_celula_era5"
] = (
    resultado[
        "n_celulas_era5_historico"
    ]
    >
    1
)


# ==========================================================
# 12. ORDENAR COLUNAS PRINCIPAIS
# ==========================================================

colunas_inicio = [
    "codigo",
    "estacao",
    "uf",
    "regiao",

    "latitude",
    "longitude",
    "altitude_m",

    "n_pares",
    "anos_com_dados",
    "primeiro_ano",
    "ultimo_ano",

    "media_inmet_c",
    "media_era5_c",

    "bias_c",
    "mae_c",
    "rmse_c",
    "correlacao_pearson",
    "desvio_erro_c",

    "erro_min_c",
    "erro_p05_c",
    "erro_mediana_c",
    "erro_p95_c",
    "erro_max_c",
    "erro_abs_max_c",

    "pct_abs_erro_gt5",
    "pct_abs_erro_gt10",
    "pct_abs_erro_gt20",

    "n_celulas_era5_historico",
    "mudou_celula_era5",
    "deslocamento_max_coord_km",

    "amostra_interpretavel",

    "pares_removidos_qc",
    "pct_pares_removidos_qc",

    "delta_bias_qc_c",
    "delta_mae_qc_c",
    "delta_rmse_qc_c",
    "delta_correlacao_qc",
]


colunas_inicio = [
    coluna
    for coluna in colunas_inicio
    if coluna in resultado.columns
]


restantes = [
    coluna
    for coluna in resultado.columns
    if coluna not in colunas_inicio
]


resultado = resultado[
    colunas_inicio
    +
    restantes
]


resultado = resultado.sort_values(
    "codigo"
).reset_index(
    drop=True
)


# ==========================================================
# 13. VALIDAR CONTAGENS
# ==========================================================

pares_principal = int(
    resultado[
        "n_pares"
    ].sum()
)


pares_completa = int(
    resultado[
        "n_pares_completa"
    ].sum()
)


pares_removidos = int(
    resultado[
        "pares_removidos_qc"
    ].sum()
)


if pares_principal != 71_901_988:

    raise RuntimeError(
        "Total principal inesperado: "
        f"{pares_principal:,}"
    )


if pares_completa != 71_927_348:

    raise RuntimeError(
        "Total completo inesperado: "
        f"{pares_completa:,}"
    )


if pares_removidos != 25_360:

    raise RuntimeError(
        "Quantidade removida pelo QC inesperada: "
        f"{pares_removidos:,}"
    )


# ==========================================================
# 14. SALVAR
# ==========================================================

resultado.to_parquet(
    SAIDA_PARQUET,
    index=False,
)


resultado.to_csv(
    SAIDA_CSV,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 15. RANKING DIAGNÓSTICO
# ==========================================================

# Não é ranking de "melhor/pior estação".
# É apenas uma ordenação para inspeção dos
# maiores RMSE na validação principal.

ranking = (
    resultado[
        resultado[
            "amostra_interpretavel"
        ]
    ]
    .sort_values(
        "rmse_c",
        ascending=False,
    )
    .copy()
)


ranking.to_csv(
    SAIDA_RANKING,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 16. DISTRIBUIÇÃO ENTRE ESTAÇÕES
# ==========================================================

print("\n" + "=" * 90)
print("DISTRIBUIÇÃO ENTRE ESTAÇÕES")
print("=" * 90)


interpretaveis = resultado[
    resultado[
        "amostra_interpretavel"
    ]
].copy()


for coluna in [
    "bias_c",
    "mae_c",
    "rmse_c",
    "correlacao_pearson",
]:

    serie = (
        interpretaveis[
            coluna
        ]
        .dropna()
    )


    print(
        f"\n{coluna}:"
    )


    print(
        f"  mínimo:  "
        f"{serie.min():.4f}"
    )


    print(
        f"  p05:     "
        f"{serie.quantile(0.05):.4f}"
    )


    print(
        f"  mediana: "
        f"{serie.median():.4f}"
    )


    print(
        f"  média:   "
        f"{serie.mean():.4f}"
    )


    print(
        f"  p95:     "
        f"{serie.quantile(0.95):.4f}"
    )


    print(
        f"  máximo:  "
        f"{serie.max():.4f}"
    )


# ==========================================================
# 17. CASOS DE MAIOR RMSE
# ==========================================================

print("\n" + "=" * 90)
print("20 ESTAÇÕES COM MAIOR RMSE")
print("=" * 90)


colunas_ranking = [
    "codigo",
    "estacao",
    "uf",
    "n_pares",
    "anos_com_dados",
    "bias_c",
    "mae_c",
    "rmse_c",
    "correlacao_pearson",
    "altitude_m",
    "n_celulas_era5_historico",
]


print(
    ranking[
        colunas_ranking
    ]
    .head(20)
    .to_string(
        index=False
    )
)


# ==========================================================
# 18. IMPACTO DO QC
# ==========================================================

print("\n" + "=" * 90)
print("IMPACTO DO QC")
print("=" * 90)


afetadas = (
    resultado[
        resultado[
            "pares_removidos_qc"
        ]
        >
        0
    ]
    .copy()
)


print(
    f"\nEstações afetadas pelo QC: "
    f"{len(afetadas):,}"
)


if not afetadas.empty:

    print(
        afetadas[
            [
                "codigo",
                "estacao",
                "uf",

                "pares_removidos_qc",

                "bias_c_completa",
                "bias_c",
                "delta_bias_qc_c",

                "rmse_c_completa",
                "rmse_c",
                "delta_rmse_qc_c",

                "correlacao_pearson_completa",
                "correlacao_pearson",
                "delta_correlacao_qc",
            ]
        ]
        .sort_values(
            "pares_removidos_qc",
            ascending=False,
        )
        .to_string(
            index=False
        )
    )


# ==========================================================
# 19. RESUMO PARA ARQUIVO
# ==========================================================

resumo = pd.DataFrame(
    [
        {
            "estacoes_total":
                len(
                    resultado
                ),

            "estacoes_interpretaveis_min100":
                int(
                    resultado[
                        "amostra_interpretavel"
                    ].sum()
                ),

            "pares_validacao_principal":
                pares_principal,

            "pares_amostra_completa":
                pares_completa,

            "pares_removidos_qc":
                pares_removidos,

            "estacoes_afetadas_qc":
                len(
                    afetadas
                ),

            "bias_mediano_estacoes":
                float(
                    interpretaveis[
                        "bias_c"
                    ].median()
                ),

            "mae_mediano_estacoes":
                float(
                    interpretaveis[
                        "mae_c"
                    ].median()
                ),

            "rmse_mediano_estacoes":
                float(
                    interpretaveis[
                        "rmse_c"
                    ].median()
                ),

            "correlacao_mediana_estacoes":
                float(
                    interpretaveis[
                        "correlacao_pearson"
                    ].median()
                ),
        }
    ]
)


resumo.to_csv(
    SAIDA_RESUMO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 20. RESULTADO
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO GLOBAL")
print("=" * 90)


print(
    f"\nEstações totais: "
    f"{len(resultado):,}"
)


print(
    f"Estações com >=100 pares: "
    f"{resultado['amostra_interpretavel'].sum():,}"
)


print(
    f"\nPares da validação principal: "
    f"{pares_principal:,}"
)


print(
    f"Pares da amostra completa: "
    f"{pares_completa:,}"
)


print(
    f"Pares removidos pelo QC: "
    f"{pares_removidos:,}"
)


print(
    f"Estações afetadas pelo QC: "
    f"{len(afetadas):,}"
)


print(
    "\nArquivo principal:"
)

print(
    SAIDA_PARQUET
)


print(
    "\nCSV:"
)

print(
    SAIDA_CSV
)


print(
    "\nResumo:"
)

print(
    SAIDA_RESUMO
)


print("\n" + "=" * 90)
print("MÉTRICAS POR ESTAÇÃO CONCLUÍDAS")
print("=" * 90)