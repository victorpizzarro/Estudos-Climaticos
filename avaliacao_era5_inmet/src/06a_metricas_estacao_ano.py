from pathlib import Path

import duckdb
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


ARQUIVO_MAPEAMENTO = (
    MATCHES_DIR
    / "inmet_era5_estacao_ano.csv"
)


ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


ANNUAL_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ARQUIVO_PARQUET = (
    ANNUAL_DIR
    / "metricas_era5_inmet_estacao_ano.parquet"
)


ARQUIVO_CSV = (
    TABLES_DIR
    / "metricas_era5_inmet_estacao_ano.csv"
)


ARQUIVO_RESUMO = (
    TABLES_DIR
    / "resumo_metricas_estacao_ano.csv"
)


# ==========================================================
# CAMINHO PARA SQL
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
print("MÉTRICAS ERA5 × INMET POR ESTAÇÃO E ANO")
print("=" * 90)

print(
    "\nDefinição:"
)

print(
    "erro = ERA5 - INMET"
)

print(
    "\nBias negativo = ERA5 subestima o INMET"
)

print(
    "Bias positivo = ERA5 superestima o INMET"
)


# ==========================================================
# 1. VERIFICAR MAPEAMENTO
# ==========================================================

if not ARQUIVO_MAPEAMENTO.exists():

    raise FileNotFoundError(
        f"Mapeamento não encontrado:\n"
        f"{ARQUIVO_MAPEAMENTO}"
    )


# ==========================================================
# 2. CARREGAR METADADOS
# ==========================================================

mapeamento = pd.read_csv(
    ARQUIVO_MAPEAMENTO
)


print(
    f"\nRegistros estação-ano no mapeamento: "
    f"{len(mapeamento):,}"
)


# ----------------------------------------------------------
# Tipos
# ----------------------------------------------------------

mapeamento[
    "ano"
] = pd.to_numeric(
    mapeamento[
        "ano"
    ],
    errors="raise",
).astype(int)


mapeamento[
    "grid_index"
] = pd.to_numeric(
    mapeamento[
        "grid_index"
    ],
    errors="raise",
).astype(int)


mapeamento[
    "observacoes_inmet"
] = pd.to_numeric(
    mapeamento[
        "observacoes_inmet"
    ],
    errors="coerce",
).fillna(0).astype(
    "int64"
)


# ==========================================================
# 3. DUCKDB
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


# ==========================================================
# 4. PROCESSAR ANO POR ANO
# ==========================================================

resultados = []


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    print("\n" + "=" * 90)

    print(
        f"ANO {ano}"
    )

    print("=" * 90)


    arquivo = (
        PARES_DIR
        / f"era5_inmet_pares_{ano}.parquet"
    )


    if not arquivo.exists():

        raise FileNotFoundError(
            f"Arquivo de pares ausente:\n"
            f"{arquivo}"
        )


    caminho_sql = sql_path(
        arquivo
    )


    # ======================================================
    # MÉTRICAS
    # ======================================================

    consulta = f"""
        SELECT

            CAST(ano AS INTEGER)
                AS ano,

            CAST(codigo AS VARCHAR)
                AS codigo,

            CAST(grid_index AS INTEGER)
                AS grid_index,

            COUNT(*)
                AS n_pares,


            -- =============================================
            -- TEMPERATURAS MÉDIAS
            -- =============================================

            AVG(
                CAST(
                    temp_inmet_c
                    AS DOUBLE
                )
            )
                AS media_inmet_c,

            AVG(
                CAST(
                    temp_era5_c
                    AS DOUBLE
                )
            )
                AS media_era5_c,


            -- =============================================
            -- BIAS
            -- =============================================

            AVG(
                CAST(
                    erro_c
                    AS DOUBLE
                )
            )
                AS bias_c,


            -- =============================================
            -- MAE
            -- =============================================

            AVG(
                ABS(
                    CAST(
                        erro_c
                        AS DOUBLE
                    )
                )
            )
                AS mae_c,


            -- =============================================
            -- RMSE
            -- =============================================

            SQRT(
                AVG(
                    POWER(
                        CAST(
                            erro_c
                            AS DOUBLE
                        ),
                        2
                    )
                )
            )
                AS rmse_c,


            -- =============================================
            -- CORRELAÇÃO
            -- =============================================

            CORR(
                CAST(
                    temp_era5_c
                    AS DOUBLE
                ),

                CAST(
                    temp_inmet_c
                    AS DOUBLE
                )
            )
                AS correlacao_pearson,


            -- =============================================
            -- DISPERSÃO DO ERRO
            -- =============================================

            STDDEV_SAMP(
                CAST(
                    erro_c
                    AS DOUBLE
                )
            )
                AS desvio_erro_c,


            -- =============================================
            -- EXTREMOS
            -- =============================================

            MIN(
                CAST(
                    erro_c
                    AS DOUBLE
                )
            )
                AS erro_min_c,

            MAX(
                CAST(
                    erro_c
                    AS DOUBLE
                )
            )
                AS erro_max_c,

            MAX(
                ABS(
                    CAST(
                        erro_c
                        AS DOUBLE
                    )
                )
            )
                AS erro_abs_max_c,


            -- =============================================
            -- PERCENTIS DO ERRO
            -- =============================================

            QUANTILE_CONT(
                CAST(
                    erro_c
                    AS DOUBLE
                ),
                0.05
            )
                AS erro_p05_c,

            QUANTILE_CONT(
                CAST(
                    erro_c
                    AS DOUBLE
                ),
                0.50
            )
                AS erro_mediana_c,

            QUANTILE_CONT(
                CAST(
                    erro_c
                    AS DOUBLE
                ),
                0.95
            )
                AS erro_p95_c,


            -- =============================================
            -- TEMPERATURAS OBSERVADAS
            -- =============================================

            MIN(
                CAST(
                    temp_inmet_c
                    AS DOUBLE
                )
            )
                AS temp_inmet_min_c,

            MAX(
                CAST(
                    temp_inmet_c
                    AS DOUBLE
                )
            )
                AS temp_inmet_max_c,

            MIN(
                CAST(
                    temp_era5_c
                    AS DOUBLE
                )
            )
                AS temp_era5_min_c,

            MAX(
                CAST(
                    temp_era5_c
                    AS DOUBLE
                )
            )
                AS temp_era5_max_c,


            -- =============================================
            -- ERROS GRANDES
            -- =============================================

            SUM(
                CASE
                    WHEN ABS(
                        CAST(
                            erro_c
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
                            erro_c
                            AS DOUBLE
                        )
                    ) > 20
                    THEN 1
                    ELSE 0
                END
            )
                AS n_abs_erro_gt20


        FROM read_parquet(
            '{caminho_sql}'
        )


        GROUP BY

            ano,
            codigo,
            grid_index


        ORDER BY

            codigo
    """


    df_ano = con.execute(
        consulta
    ).fetchdf()


    print(
        f"\nEstações calculadas: "
        f"{len(df_ano):,}"
    )


    print(
        f"Pares utilizados: "
        f"{df_ano['n_pares'].sum():,}"
    )


    resultados.append(
        df_ano
    )


# ==========================================================
# 5. CONSOLIDAR
# ==========================================================

metricas = pd.concat(
    resultados,
    ignore_index=True,
)


print("\n" + "=" * 90)

print(
    "CONSOLIDANDO RESULTADOS"
)

print("=" * 90)


print(
    f"\nRegistros estação-ano: "
    f"{len(metricas):,}"
)


print(
    f"Pares totais: "
    f"{metricas['n_pares'].sum():,}"
)


# ==========================================================
# 6. PERCENTUAIS DE ERROS GRANDES
# ==========================================================

metricas[
    "pct_abs_erro_gt10"
] = (
    metricas[
        "n_abs_erro_gt10"
    ]
    /
    metricas[
        "n_pares"
    ]
    *
    100
)


metricas[
    "pct_abs_erro_gt20"
] = (
    metricas[
        "n_abs_erro_gt20"
    ]
    /
    metricas[
        "n_pares"
    ]
    *
    100
)


metricas[
    "dias_equivalentes"
] = (
    metricas[
        "n_pares"
    ]
    /
    24
)


# ==========================================================
# 7. METADADOS
# ==========================================================

metadata_cols = [
    "ano",
    "codigo",
    "estacao",
    "uf",
    "regiao",
    "latitude_inmet",
    "longitude_inmet",
    "altitude_inmet_m",
    "latitude_era5",
    "longitude_era5",
    "grid_index",
    "distancia_centro_km",
    "observacoes_inmet",
    "cobertura_temp",
]


metadata = (
    mapeamento[
        metadata_cols
    ]
    .copy()
)


metricas = metricas.merge(
    metadata,
    on=[
        "ano",
        "codigo",
        "grid_index",
    ],
    how="left",
    validate="one_to_one",
)


# ==========================================================
# 8. VALIDAR QUANTIDADE DE PARES
# ==========================================================

metricas[
    "pareamento_completo"
] = (
    metricas[
        "n_pares"
    ].astype(
        "int64"
    )
    ==
    metricas[
        "observacoes_inmet"
    ].astype(
        "int64"
    )
)


incompletos = int(
    (
        ~metricas[
            "pareamento_completo"
        ]
    ).sum()
)


metadata_ausente = int(
    metricas[
        "estacao"
    ]
    .isna()
    .sum()
)


# ==========================================================
# 9. REORGANIZAR COLUNAS
# ==========================================================

ordem = [

    "ano",
    "codigo",
    "estacao",
    "uf",
    "regiao",

    "latitude_inmet",
    "longitude_inmet",
    "altitude_inmet_m",

    "latitude_era5",
    "longitude_era5",
    "grid_index",

    "distancia_centro_km",
    "cobertura_temp",

    "n_pares",
    "dias_equivalentes",

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

    "n_abs_erro_gt10",
    "pct_abs_erro_gt10",

    "n_abs_erro_gt20",
    "pct_abs_erro_gt20",

    "temp_inmet_min_c",
    "temp_inmet_max_c",

    "temp_era5_min_c",
    "temp_era5_max_c",

    "observacoes_inmet",
    "pareamento_completo",
]


metricas = metricas[
    ordem
]


metricas = metricas.sort_values(
    [
        "ano",
        "codigo",
    ]
).reset_index(
    drop=True
)


# ==========================================================
# 10. SALVAR
# ==========================================================

metricas.to_parquet(
    ARQUIVO_PARQUET,
    index=False,
)


metricas.to_csv(
    ARQUIVO_CSV,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 11. RESUMO DE QC
# ==========================================================

resumo = pd.DataFrame(
    [
        {
            "registros_estacao_ano":
                len(
                    metricas
                ),

            "pares_totais":
                int(
                    metricas[
                        "n_pares"
                    ].sum()
                ),

            "pareamentos_incompletos":
                incompletos,

            "metadata_ausente":
                metadata_ausente,

            "bias_mediano_estacao_ano":
                float(
                    metricas[
                        "bias_c"
                    ].median()
                ),

            "mae_mediano_estacao_ano":
                float(
                    metricas[
                        "mae_c"
                    ].median()
                ),

            "rmse_mediano_estacao_ano":
                float(
                    metricas[
                        "rmse_c"
                    ].median()
                ),

            "correlacao_mediana_estacao_ano":
                float(
                    metricas[
                        "correlacao_pearson"
                    ].median()
                ),
        }
    ]
)


resumo.to_csv(
    ARQUIVO_RESUMO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 12. IMPRESSÃO DOS RESULTADOS
# ==========================================================

print("\n" + "=" * 90)

print(
    "VALIDAÇÃO"
)

print("=" * 90)


print(
    f"\nRegistros estação-ano: "
    f"{len(metricas):,}"
)


print(
    f"Pares utilizados: "
    f"{metricas['n_pares'].sum():,}"
)


print(
    f"Pareamentos incompletos: "
    f"{incompletos:,}"
)


print(
    f"Metadados ausentes: "
    f"{metadata_ausente:,}"
)


# ==========================================================
# 13. ESTATÍSTICAS DESCRITIVAS
# ==========================================================

print("\n" + "=" * 90)

print(
    "DISTRIBUIÇÃO DAS MÉTRICAS ESTAÇÃO-ANO"
)

print("=" * 90)


for coluna in [
    "bias_c",
    "mae_c",
    "rmse_c",
    "correlacao_pearson",
]:

    serie = (
        metricas[
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
# 14. MAIORES RMSE
# ==========================================================

print("\n" + "=" * 90)

print(
    "20 MAIORES RMSE ESTAÇÃO-ANO"
)

print("=" * 90)


colunas_ranking = [
    "ano",
    "codigo",
    "estacao",
    "uf",
    "n_pares",
    "bias_c",
    "mae_c",
    "rmse_c",
    "correlacao_pearson",
    "erro_abs_max_c",
]


print(
    metricas[
        colunas_ranking
    ]
    .sort_values(
        "rmse_c",
        ascending=False,
    )
    .head(20)
    .to_string(
        index=False
    )
)


# ==========================================================
# 15. MAIORES BIAS ABSOLUTOS
# ==========================================================

print("\n" + "=" * 90)

print(
    "20 MAIORES |BIAS| ESTAÇÃO-ANO"
)

print("=" * 90)


ranking_bias = (
    metricas[
        colunas_ranking
    ]
    .copy()
)


ranking_bias[
    "bias_abs"
] = (
    ranking_bias[
        "bias_c"
    ].abs()
)


print(
    ranking_bias
    .sort_values(
        "bias_abs",
        ascending=False,
    )
    .head(20)
    .drop(
        columns=[
            "bias_abs"
        ]
    )
    .to_string(
        index=False
    )
)


# ==========================================================
# 16. RESULTADO
# ==========================================================

aprovado = (
    len(metricas)
    ==
    len(mapeamento)
    and
    incompletos
    ==
    0
    and
    metadata_ausente
    ==
    0
)


print("\n" + "=" * 90)


if aprovado:

    print(
        "RESULTADO: MÉTRICAS ESTAÇÃO-ANO APROVADAS"
    )

else:

    print(
        "RESULTADO: MÉTRICAS ESTAÇÃO-ANO "
        "REQUEREM INVESTIGAÇÃO"
    )


print(
    "\nParquet:"
)

print(
    ARQUIVO_PARQUET
)


print(
    "\nCSV:"
)

print(
    ARQUIVO_CSV
)


print(
    "\nResumo:"
)

print(
    ARQUIVO_RESUMO
)


print("\n" + "=" * 90)


con.close()