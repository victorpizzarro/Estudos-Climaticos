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

MIN_PARES_ESTACAO_ANO = 100


# ==========================================================
# REGIÕES
# ==========================================================

UF_REGIAO = {

    # Norte
    "AC": "Norte",
    "AP": "Norte",
    "AM": "Norte",
    "PA": "Norte",
    "RO": "Norte",
    "RR": "Norte",
    "TO": "Norte",

    # Nordeste
    "AL": "Nordeste",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "MA": "Nordeste",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RN": "Nordeste",
    "SE": "Nordeste",

    # Centro-Oeste
    "DF": "Centro-Oeste",
    "GO": "Centro-Oeste",
    "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",

    # Sudeste
    "ES": "Sudeste",
    "MG": "Sudeste",
    "RJ": "Sudeste",
    "SP": "Sudeste",

    # Sul
    "PR": "Sul",
    "RS": "Sul",
    "SC": "Sul",
}


ORDEM_AREAS = [
    "Brasil",
    "Norte",
    "Nordeste",
    "Centro-Oeste",
    "Sudeste",
    "Sul",
]


# ==========================================================
# CAMINHOS
# ==========================================================

ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


PARES_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "matches"
    / "horarios"
)


AMOSTRA_FILE = (
    ANNUAL_DIR
    / "amostra_analitica_estacao_ano.parquet"
)


SAIDA_PARQUET = (
    ANNUAL_DIR
    / "metricas_anuais_regionais_era5_inmet.parquet"
)


SAIDA_CSV = (
    TABLES_DIR
    / "metricas_anuais_regionais_era5_inmet.csv"
)


SAIDA_IMPACTO_QC = (
    TABLES_DIR
    / "impacto_qc_metricas_anuais_regionais.csv"
)


SAIDA_RESUMO = (
    TABLES_DIR
    / "resumo_metricas_anuais_regionais.csv"
)


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
print("MÉTRICAS ANUAIS E REGIONAIS ERA5 × INMET")
print("=" * 90)


print(
    "\nSerão calculadas duas formas de agregação:"
)


print(
    "1. por pares horários"
)


print(
    "2. equilibrada entre estações"
)


print(
    "\nE duas amostras:"
)


print(
    "principal = QC aplicado"
)


print(
    "completa  = todos os pares espacialmente válidos"
)


# ==========================================================
# 1. CARREGAR AMOSTRA ANALÍTICA
# ==========================================================

if not AMOSTRA_FILE.exists():

    raise FileNotFoundError(
        f"Amostra analítica não encontrada:\n"
        f"{AMOSTRA_FILE}"
    )


amostra = pd.read_parquet(
    AMOSTRA_FILE
)


print(
    f"\nRegistros estação-ano carregados: "
    f"{len(amostra):,}"
)


print(
    f"Pares registrados: "
    f"{amostra['n_pares'].sum():,}"
)


# ==========================================================
# 2. NORMALIZAR UF
# ==========================================================

amostra[
    "uf"
] = (
    amostra[
        "uf"
    ]
    .astype(str)
    .str.strip()
    .str.upper()
)


amostra[
    "regiao_padrao"
] = (
    amostra[
        "uf"
    ]
    .map(
        UF_REGIAO
    )
)


uf_sem_regiao = (
    amostra.loc[
        amostra[
            "regiao_padrao"
        ]
        .isna(),
        "uf",
    ]
    .drop_duplicates()
    .tolist()
)


if uf_sem_regiao:

    raise RuntimeError(
        "Existem UFs sem região definida: "
        f"{uf_sem_regiao}"
    )


# ==========================================================
# 3. NORMALIZAR BOOLEANO
# ==========================================================

for coluna in [
    "usar_validacao_principal",
]:

    if (
        amostra[
            coluna
        ].dtype
        != bool
    ):

        amostra[
            coluna
        ] = (
            amostra[
                coluna
            ]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(
                {
                    "true": True,
                    "false": False,
                    "1": True,
                    "0": False,
                }
            )
        )


# ==========================================================
# 4. DUCKDB
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
# 5. AGREGAÇÃO DOS PARES HORÁRIOS
# ==========================================================

print("\n" + "=" * 90)
print("AGREGAÇÃO DOS PARES HORÁRIOS")
print("=" * 90)


resultados_pares = []


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    print(
        f"\n{ano}"
    )


    arquivo_pares = (
        PARES_DIR
        / f"era5_inmet_pares_{ano}.parquet"
    )


    if not arquivo_pares.exists():

        raise FileNotFoundError(
            f"Arquivo não encontrado:\n"
            f"{arquivo_pares}"
        )


    meta_ano = (
        amostra[
            amostra[
                "ano"
            ]
            ==
            ano
        ][
            [
                "ano",
                "codigo",
                "uf",
                "regiao_padrao",
                "usar_validacao_principal",
            ]
        ]
        .copy()
    )


    con.register(
        "meta_ano",
        meta_ano,
    )


    caminho_sql = sql_path(
        arquivo_pares
    )


    # ------------------------------------------------------
    # Criamos duas versões:
    #
    # completa  → todos os pares
    # principal → remove os 4 estação-ano do QC
    #
    # Depois calculamos regiões + Brasil.
    # ------------------------------------------------------

    consulta = f"""
        WITH base AS (

            SELECT

                CAST(
                    p.ano
                    AS INTEGER
                ) AS ano,

                CAST(
                    p.codigo
                    AS VARCHAR
                ) AS codigo,

                m.regiao_padrao,

                CAST(
                    m.usar_validacao_principal
                    AS BOOLEAN
                ) AS usar_validacao_principal,

                CAST(
                    p.temp_inmet_c
                    AS DOUBLE
                ) AS temp_inmet_c,

                CAST(
                    p.temp_era5_c
                    AS DOUBLE
                ) AS temp_era5_c,

                CAST(
                    p.erro_c
                    AS DOUBLE
                ) AS erro_c


            FROM read_parquet(
                '{caminho_sql}'
            ) AS p


            INNER JOIN meta_ano AS m

                ON p.codigo
                    =
                   m.codigo

                AND p.ano
                    =
                   m.ano
        ),


        expandida AS (

            SELECT

                *,
                'completa'
                    AS amostra

            FROM base


            UNION ALL


            SELECT

                *,
                'principal'
                    AS amostra

            FROM base

            WHERE
                usar_validacao_principal
                =
                TRUE
        ),


        regional AS (

            SELECT

                ano,

                amostra,

                regiao_padrao
                    AS area,

                COUNT(*)
                    AS n_pares,

                COUNT(
                    DISTINCT codigo
                )
                    AS n_estacoes,

                AVG(
                    temp_inmet_c
                )
                    AS media_inmet_c_pares,

                AVG(
                    temp_era5_c
                )
                    AS media_era5_c_pares,

                AVG(
                    erro_c
                )
                    AS bias_pares_c,

                AVG(
                    ABS(
                        erro_c
                    )
                )
                    AS mae_pares_c,

                SQRT(
                    AVG(
                        POWER(
                            erro_c,
                            2
                        )
                    )
                )
                    AS rmse_pares_c,

                CORR(
                    temp_era5_c,
                    temp_inmet_c
                )
                    AS correlacao_pares,

                QUANTILE_CONT(
                    erro_c,
                    0.05
                )
                    AS erro_p05_pares_c,

                QUANTILE_CONT(
                    erro_c,
                    0.50
                )
                    AS erro_mediana_pares_c,

                QUANTILE_CONT(
                    erro_c,
                    0.95
                )
                    AS erro_p95_pares_c,

                SUM(
                    CASE

                        WHEN ABS(
                            erro_c
                        ) > 5

                        THEN 1

                        ELSE 0

                    END
                )
                    AS n_abs_erro_gt5,

                SUM(
                    CASE

                        WHEN ABS(
                            erro_c
                        ) > 10

                        THEN 1

                        ELSE 0

                    END
                )
                    AS n_abs_erro_gt10


            FROM expandida


            GROUP BY

                ano,
                amostra,
                regiao_padrao
        ),


        brasil AS (

            SELECT

                ano,

                amostra,

                'Brasil'
                    AS area,

                COUNT(*)
                    AS n_pares,

                COUNT(
                    DISTINCT codigo
                )
                    AS n_estacoes,

                AVG(
                    temp_inmet_c
                )
                    AS media_inmet_c_pares,

                AVG(
                    temp_era5_c
                )
                    AS media_era5_c_pares,

                AVG(
                    erro_c
                )
                    AS bias_pares_c,

                AVG(
                    ABS(
                        erro_c
                    )
                )
                    AS mae_pares_c,

                SQRT(
                    AVG(
                        POWER(
                            erro_c,
                            2
                        )
                    )
                )
                    AS rmse_pares_c,

                CORR(
                    temp_era5_c,
                    temp_inmet_c
                )
                    AS correlacao_pares,

                QUANTILE_CONT(
                    erro_c,
                    0.05
                )
                    AS erro_p05_pares_c,

                QUANTILE_CONT(
                    erro_c,
                    0.50
                )
                    AS erro_mediana_pares_c,

                QUANTILE_CONT(
                    erro_c,
                    0.95
                )
                    AS erro_p95_pares_c,

                SUM(
                    CASE

                        WHEN ABS(
                            erro_c
                        ) > 5

                        THEN 1

                        ELSE 0

                    END
                )
                    AS n_abs_erro_gt5,

                SUM(
                    CASE

                        WHEN ABS(
                            erro_c
                        ) > 10

                        THEN 1

                        ELSE 0

                    END
                )
                    AS n_abs_erro_gt10


            FROM expandida


            GROUP BY

                ano,
                amostra
        )


        SELECT *
        FROM regional


        UNION ALL


        SELECT *
        FROM brasil


        ORDER BY

            amostra,
            area
    """


    df_ano = con.execute(
        consulta
    ).fetchdf()


    # ------------------------------------------------------
    # Percentuais
    # ------------------------------------------------------

    df_ano[
        "pct_abs_erro_gt5"
    ] = (
        df_ano[
            "n_abs_erro_gt5"
        ]
        /
        df_ano[
            "n_pares"
        ]
        *
        100
    )


    df_ano[
        "pct_abs_erro_gt10"
    ] = (
        df_ano[
            "n_abs_erro_gt10"
        ]
        /
        df_ano[
            "n_pares"
        ]
        *
        100
    )


    resultados_pares.append(
        df_ano
    )


    brasil_principal = (
        df_ano[
            (
                df_ano[
                    "amostra"
                ]
                ==
                "principal"
            )
            &
            (
                df_ano[
                    "area"
                ]
                ==
                "Brasil"
            )
        ]
    )


    if not brasil_principal.empty:

        linha = (
            brasil_principal
            .iloc[0]
        )


        print(
            f"  pares principal: "
            f"{int(linha['n_pares']):,}"
        )


        print(
            f"  Bias: "
            f"{linha['bias_pares_c']:+.3f} °C | "
            f"MAE: {linha['mae_pares_c']:.3f} °C | "
            f"RMSE: {linha['rmse_pares_c']:.3f} °C | "
            f"r: {linha['correlacao_pares']:.3f}"
        )


    con.unregister(
        "meta_ano"
    )


con.close()


pares = pd.concat(
    resultados_pares,
    ignore_index=True,
)


# ==========================================================
# 6. AGREGAÇÃO EQUILIBRADA ENTRE ESTAÇÕES
# ==========================================================

print("\n" + "=" * 90)
print("AGREGAÇÃO EQUILIBRADA ENTRE ESTAÇÕES")
print("=" * 90)


resultados_estacoes = []


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    dados_ano = (
        amostra[
            amostra[
                "ano"
            ]
            ==
            ano
        ]
        .copy()
    )


    for nome_amostra in [
        "completa",
        "principal",
    ]:

        if (
            nome_amostra
            ==
            "principal"
        ):

            dados_amostra = (
                dados_ano[
                    dados_ano[
                        "usar_validacao_principal"
                    ]
                ]
                .copy()
            )

        else:

            dados_amostra = (
                dados_ano
                .copy()
            )


        # --------------------------------------------------
        # Equal-weight só faz sentido com uma quantidade
        # mínima de observações por estação.
        # --------------------------------------------------

        dados_amostra = (
            dados_amostra[
                dados_amostra[
                    "n_pares"
                ]
                >=
                MIN_PARES_ESTACAO_ANO
            ]
            .copy()
        )


        for area in ORDEM_AREAS:

            if area == "Brasil":

                subset = (
                    dados_amostra
                    .copy()
                )

            else:

                subset = (
                    dados_amostra[
                        dados_amostra[
                            "regiao_padrao"
                        ]
                        ==
                        area
                    ]
                    .copy()
                )


            if subset.empty:

                resultados_estacoes.append(
                    {
                        "ano":
                            ano,

                        "amostra":
                            nome_amostra,

                        "area":
                            area,

                        "n_estacoes_equilibradas":
                            0,

                        "n_pares_mediana_estacao":
                            np.nan,

                        "bias_media_estacoes_c":
                            np.nan,

                        "bias_mediana_estacoes_c":
                            np.nan,

                        "mae_media_estacoes_c":
                            np.nan,

                        "mae_mediana_estacoes_c":
                            np.nan,

                        "rmse_equilibrado_estacoes_c":
                            np.nan,

                        "rmse_mediana_estacoes_c":
                            np.nan,

                        "correlacao_mediana_estacoes":
                            np.nan,
                    }
                )

                continue


            # --------------------------------------------------
            # RMSE equilibrado:
            #
            # cada estação recebe o mesmo peso.
            #
            # Como RMSE_i² = MSE_i:
            #
            # sqrt(mean(RMSE_i²))
            #
            # equivale à raiz do MSE médio entre estações.
            # --------------------------------------------------

            rmse_equilibrado = float(
                np.sqrt(
                    np.mean(
                        np.square(
                            subset[
                                "rmse_c"
                            ]
                        )
                    )
                )
            )


            resultados_estacoes.append(
                {
                    "ano":
                        ano,

                    "amostra":
                        nome_amostra,

                    "area":
                        area,

                    "n_estacoes_equilibradas":
                        len(
                            subset
                        ),

                    "n_pares_mediana_estacao":
                        float(
                            subset[
                                "n_pares"
                            ]
                            .median()
                        ),

                    "bias_media_estacoes_c":
                        float(
                            subset[
                                "bias_c"
                            ]
                            .mean()
                        ),

                    "bias_mediana_estacoes_c":
                        float(
                            subset[
                                "bias_c"
                            ]
                            .median()
                        ),

                    "mae_media_estacoes_c":
                        float(
                            subset[
                                "mae_c"
                            ]
                            .mean()
                        ),

                    "mae_mediana_estacoes_c":
                        float(
                            subset[
                                "mae_c"
                            ]
                            .median()
                        ),

                    "rmse_equilibrado_estacoes_c":
                        rmse_equilibrado,

                    "rmse_mediana_estacoes_c":
                        float(
                            subset[
                                "rmse_c"
                            ]
                            .median()
                        ),

                    "correlacao_mediana_estacoes":
                        float(
                            subset[
                                "correlacao_pearson"
                            ]
                            .median()
                        ),
                }
            )


estacoes = pd.DataFrame(
    resultados_estacoes
)


# ==========================================================
# 7. JUNTAR AS DUAS FORMAS DE AGREGAÇÃO
# ==========================================================

resultado = pares.merge(
    estacoes,
    on=[
        "ano",
        "amostra",
        "area",
    ],
    how="outer",
    validate="one_to_one",
)


# ==========================================================
# 8. COMPLETAR COMBINAÇÕES AUSENTES
# ==========================================================

grade = pd.MultiIndex.from_product(
    [
        range(
            ANO_INICIAL,
            ANO_FINAL + 1,
        ),

        [
            "principal",
            "completa",
        ],

        ORDEM_AREAS,
    ],

    names=[
        "ano",
        "amostra",
        "area",
    ],
).to_frame(
    index=False
)


resultado = grade.merge(
    resultado,
    on=[
        "ano",
        "amostra",
        "area",
    ],
    how="left",
)


# Contagens ausentes significam ausência
# de estações naquela região/ano.

for coluna in [
    "n_pares",
    "n_estacoes",
    "n_abs_erro_gt5",
    "n_abs_erro_gt10",
    "n_estacoes_equilibradas",
]:

    resultado[
        coluna
    ] = (
        resultado[
            coluna
        ]
        .fillna(0)
        .astype(
            "int64"
        )
    )


# ==========================================================
# 9. ORDENAR
# ==========================================================

resultado[
    "ordem_area"
] = (
    resultado[
        "area"
    ]
    .map(
        {
            nome:
                indice

            for indice, nome in enumerate(
                ORDEM_AREAS
            )
        }
    )
)


resultado[
    "ordem_amostra"
] = (
    resultado[
        "amostra"
    ]
    .map(
        {
            "principal": 0,
            "completa": 1,
        }
    )
)


resultado = (
    resultado
    .sort_values(
        [
            "ano",
            "ordem_amostra",
            "ordem_area",
        ]
    )
    .drop(
        columns=[
            "ordem_area",
            "ordem_amostra",
        ]
    )
    .reset_index(
        drop=True
    )
)


# ==========================================================
# 10. VALIDAÇÃO DOS TOTAIS BRASIL
# ==========================================================

brasil = (
    resultado[
        resultado[
            "area"
        ]
        ==
        "Brasil"
    ]
)


principal_total = int(
    brasil.loc[
        brasil[
            "amostra"
        ]
        ==
        "principal",
        "n_pares",
    ]
    .sum()
)


completa_total = int(
    brasil.loc[
        brasil[
            "amostra"
        ]
        ==
        "completa",
        "n_pares",
    ]
    .sum()
)


print("\n" + "=" * 90)
print("VALIDAÇÃO DOS TOTAIS")
print("=" * 90)


print(
    f"\nPrincipal: "
    f"{principal_total:,}"
)


print(
    f"Completa:  "
    f"{completa_total:,}"
)


if (
    principal_total
    !=
    71_901_988
):

    raise RuntimeError(
        "Total da amostra principal inesperado."
    )


if (
    completa_total
    !=
    71_927_348
):

    raise RuntimeError(
        "Total da amostra completa inesperado."
    )


# ==========================================================
# 11. SALVAR
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
# 12. IMPACTO DO QC
# ==========================================================

principal = (
    resultado[
        resultado[
            "amostra"
        ]
        ==
        "principal"
    ]
    .copy()
)


completa = (
    resultado[
        resultado[
            "amostra"
        ]
        ==
        "completa"
    ]
    .copy()
)


colunas_comparar = [
    "n_pares",
    "bias_pares_c",
    "mae_pares_c",
    "rmse_pares_c",
    "correlacao_pares",
]


completa_qc = completa[
    [
        "ano",
        "area",
    ]
    +
    colunas_comparar
].rename(
    columns={
        coluna:
            f"{coluna}_completa"

        for coluna in colunas_comparar
    }
)


impacto = principal.merge(
    completa_qc,
    on=[
        "ano",
        "area",
    ],
    how="left",
    validate="one_to_one",
)


impacto[
    "pares_removidos_qc"
] = (
    impacto[
        "n_pares_completa"
    ]
    -
    impacto[
        "n_pares"
    ]
)


impacto[
    "delta_bias_qc_c"
] = (
    impacto[
        "bias_pares_c"
    ]
    -
    impacto[
        "bias_pares_c_completa"
    ]
)


impacto[
    "delta_mae_qc_c"
] = (
    impacto[
        "mae_pares_c"
    ]
    -
    impacto[
        "mae_pares_c_completa"
    ]
)


impacto[
    "delta_rmse_qc_c"
] = (
    impacto[
        "rmse_pares_c"
    ]
    -
    impacto[
        "rmse_pares_c_completa"
    ]
)


impacto[
    "delta_correlacao_qc"
] = (
    impacto[
        "correlacao_pares"
    ]
    -
    impacto[
        "correlacao_pares_completa"
    ]
)


impacto.to_csv(
    SAIDA_IMPACTO_QC,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 13. RESUMO TEMPORAL POR ÁREA
# ==========================================================

principal_resumo = (
    resultado[
        resultado[
            "amostra"
        ]
        ==
        "principal"
    ]
)


resumos = []


for area in ORDEM_AREAS:

    dados = (
        principal_resumo[
            principal_resumo[
                "area"
            ]
            ==
            area
        ]
    )


    dados_validos = (
        dados[
            dados[
                "n_pares"
            ]
            >
            0
        ]
    )


    if dados_validos.empty:

        continue


    resumos.append(
        {
            "area":
                area,

            "anos_com_dados":
                len(
                    dados_validos
                ),

            "primeiro_ano":
                int(
                    dados_validos[
                        "ano"
                    ]
                    .min()
                ),

            "ultimo_ano":
                int(
                    dados_validos[
                        "ano"
                    ]
                    .max()
                ),

            "bias_anual_mediano_pares_c":
                float(
                    dados_validos[
                        "bias_pares_c"
                    ]
                    .median()
                ),

            "mae_anual_mediano_pares_c":
                float(
                    dados_validos[
                        "mae_pares_c"
                    ]
                    .median()
                ),

            "rmse_anual_mediano_pares_c":
                float(
                    dados_validos[
                        "rmse_pares_c"
                    ]
                    .median()
                ),

            "correlacao_anual_mediana_pares":
                float(
                    dados_validos[
                        "correlacao_pares"
                    ]
                    .median()
                ),

            "bias_anual_mediano_equilibrado_c":
                float(
                    dados_validos[
                        "bias_media_estacoes_c"
                    ]
                    .median()
                ),

            "rmse_anual_mediano_equilibrado_c":
                float(
                    dados_validos[
                        "rmse_equilibrado_estacoes_c"
                    ]
                    .median()
                ),

            "correlacao_mediana_estacoes":
                float(
                    dados_validos[
                        "correlacao_mediana_estacoes"
                    ]
                    .median()
                ),
        }
    )


df_resumo = pd.DataFrame(
    resumos
)


df_resumo.to_csv(
    SAIDA_RESUMO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 14. IMPRIMIR BRASIL PRINCIPAL
# ==========================================================

print("\n" + "=" * 90)
print("BRASIL - VALIDAÇÃO PRINCIPAL")
print("=" * 90)


brasil_principal = (
    resultado[
        (
            resultado[
                "area"
            ]
            ==
            "Brasil"
        )
        &
        (
            resultado[
                "amostra"
            ]
            ==
            "principal"
        )
    ]
)


colunas_print = [
    "ano",
    "n_estacoes",
    "n_pares",
    "bias_pares_c",
    "mae_pares_c",
    "rmse_pares_c",
    "correlacao_pares",
    "n_estacoes_equilibradas",
    "bias_media_estacoes_c",
    "rmse_equilibrado_estacoes_c",
    "correlacao_mediana_estacoes",
]


print(
    brasil_principal[
        colunas_print
    ]
    .to_string(
        index=False,
        float_format=lambda x:
            f"{x:.4f}"
    )
)


# ==========================================================
# 15. RESUMO DAS REGIÕES
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO REGIONAL")
print("=" * 90)


print(
    df_resumo.to_string(
        index=False,
        float_format=lambda x:
            f"{x:.4f}"
    )
)


# ==========================================================
# 16. ANOS AFETADOS PELO QC
# ==========================================================

print("\n" + "=" * 90)
print("IMPACTO DO QC")
print("=" * 90)


impactados = (
    impacto[
        impacto[
            "pares_removidos_qc"
        ]
        >
        0
    ]
)


print(
    f"\nCombinações ano/região afetadas: "
    f"{len(impactados):,}"
)


if not impactados.empty:

    print(
        impactados[
            [
                "ano",
                "area",
                "pares_removidos_qc",
                "delta_bias_qc_c",
                "delta_mae_qc_c",
                "delta_rmse_qc_c",
                "delta_correlacao_qc",
            ]
        ]
        .to_string(
            index=False,
            float_format=lambda x:
                f"{x:.6f}"
        )
    )


# ==========================================================
# 17. ARQUIVOS
# ==========================================================

print("\n" + "=" * 90)
print("ARQUIVOS GERADOS")
print("=" * 90)


print(
    "\nMétricas:"
)

print(
    SAIDA_PARQUET
)


print(
    SAIDA_CSV
)


print(
    "\nImpacto do QC:"
)

print(
    SAIDA_IMPACTO_QC
)


print(
    "\nResumo:"
)

print(
    SAIDA_RESUMO
)


print("\n" + "=" * 90)
print("MÉTRICAS ANUAIS E REGIONAIS CONCLUÍDAS")
print("=" * 90)