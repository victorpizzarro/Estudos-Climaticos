from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    PROJECT_DIR,
    TABLES_DIR,
)


# ==========================================================
# OBJETIVO
# ==========================================================
#
# Consolidar a robustez das tendências de extremos anuais
# comparando:
#
# 1. Rede principal do 06g:
#    >=15 anos válidos, com lacunas permitidas
#
# 2. Rede de sensibilidade do 06g:
#    >=10 anos válidos, com lacunas permitidas
#
# 3. Rede consecutiva principal do 06i:
#    >=15 anos consecutivos
#
# 4. Rede consecutiva de sensibilidade do 06i:
#    >=10 anos consecutivos
#
# Além disso, compara o Mann-Kendall clássico e o
# Hamed-Rao sobre EXATAMENTE as mesmas séries consecutivas.
#
# Importante:
# - diferenças entre 06g e 06i não devem ser atribuídas
#   automaticamente ao método Hamed-Rao;
# - as redes e os períodos analisados também mudam;
# - o efeito isolado da correção de autocorrelação é medido
#   comparando MK clássico vs Hamed-Rao dentro do próprio 06i.
#
# ==========================================================


# ==========================================================
# CAMINHOS
# ==========================================================

ANNUAL_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "annual"
)


ARQUIVO_06G = (
    ANNUAL_DIR
    / "tendencias_extremos_estacoes.parquet"
)


ARQUIVO_06I = (
    ANNUAL_DIR
    / "tendencias_extremos_mk_modificado.parquet"
)


SAIDA_RESUMO = (
    TABLES_DIR
    / "robustez_tendencias_resumo.csv"
)


SAIDA_CONCORDANCIA = (
    TABLES_DIR
    / "robustez_tendencias_concordancia_inmet_era5.csv"
)


SAIDA_METODOS = (
    TABLES_DIR
    / "robustez_mk_classico_vs_hamed_rao.csv"
)


SAIDA_ESTACOES_COMUNS = (
    TABLES_DIR
    / "robustez_tendencias_estacoes_comuns.csv"
)


SAIDA_SINTESE = (
    TABLES_DIR
    / "robustez_tendencias_sintese.csv"
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

ALPHA = 0.05


ORDEM_REDES = [
    "principal_15a",
    "sensibilidade_10a",
    "principal_consecutiva_15a",
    "sensibilidade_consecutiva_10a",
]


NOMES_REDES = {
    "principal_15a":
        ">=15 anos válidos",

    "sensibilidade_10a":
        ">=10 anos válidos",

    "principal_consecutiva_15a":
        ">=15 anos consecutivos",

    "sensibilidade_consecutiva_10a":
        ">=10 anos consecutivos",
}


VARIAVEIS = [
    "tmax_inmet",
    "tmax_era5",
    "delta_tmax",
]


# ==========================================================
# AUXILIARES
# ==========================================================

def percentual(
    numerador,
    denominador,
):

    if denominador == 0:

        return np.nan

    return (
        numerador
        /
        denominador
        *
        100.0
    )


def resumo_slopes(
    df,
    rede,
    variavel,
    coluna_p,
    coluna_p_fdr=None,
    metodo=None,
):

    subset = (
        df[
            (
                df[
                    "rede"
                ]
                ==
                rede
            )
            &
            (
                df[
                    "variavel"
                ]
                ==
                variavel
            )
        ]
        .copy()
    )


    if subset.empty:

        return None


    n = (
        subset[
            "codigo"
        ]
        .nunique()
    )


    slopes = (
        subset[
            "sen_slope_c_decada"
        ]
        .astype(float)
    )


    positivos = int(
        (
            slopes
            >
            0
        )
        .sum()
    )


    negativos = int(
        (
            slopes
            <
            0
        )
        .sum()
    )


    zeros = int(
        (
            slopes
            ==
            0
        )
        .sum()
    )


    p = pd.to_numeric(
        subset[
            coluna_p
        ],
        errors="coerce",
    )


    n_p05 = int(
        (
            p
            <
            ALPHA
        )
        .sum()
    )


    if (
        coluna_p_fdr is not None
        and
        coluna_p_fdr in subset.columns
    ):

        p_fdr = pd.to_numeric(
            subset[
                coluna_p_fdr
            ],
            errors="coerce",
        )


        n_fdr = int(
            (
                p_fdr
                <
                ALPHA
            )
            .sum()
        )

    else:

        n_fdr = np.nan


    return {
        "rede":
            rede,

        "nome_rede":
            NOMES_REDES[
                rede
            ],

        "metodo":
            metodo,

        "variavel":
            variavel,

        "n_estacoes":
            n,

        "sen_mediana_c_decada":
            float(
                slopes.median()
            ),

        "sen_media_c_decada":
            float(
                slopes.mean()
            ),

        "sen_p25_c_decada":
            float(
                slopes.quantile(
                    0.25
                )
            ),

        "sen_p75_c_decada":
            float(
                slopes.quantile(
                    0.75
                )
            ),

        "n_slope_positivo":
            positivos,

        "n_slope_negativo":
            negativos,

        "n_slope_zero":
            zeros,

        "pct_slope_positivo":
            percentual(
                positivos,
                n,
            ),

        "n_p05":
            n_p05,

        "pct_p05":
            percentual(
                n_p05,
                n,
            ),

        "n_fdr05":
            n_fdr,

        "pct_fdr05":
            (
                percentual(
                    n_fdr,
                    n,
                )
                if np.isfinite(
                    n_fdr
                )
                else np.nan
            ),
    }


def mesmo_sinal(
    a,
    b,
):

    a = pd.to_numeric(
        a,
        errors="coerce",
    )


    b = pd.to_numeric(
        b,
        errors="coerce",
    )


    validos = (
        a.notna()
        &
        b.notna()
    )


    a = a[
        validos
    ]


    b = b[
        validos
    ]


    if len(
        a
    ) == 0:

        return (
            0,
            0,
            np.nan,
        )


    iguais = int(
        (
            np.sign(
                a
            )
            ==
            np.sign(
                b
            )
        )
        .sum()
    )


    total = len(
        a
    )


    return (
        iguais,
        total,
        percentual(
            iguais,
            total,
        ),
    )


# ==========================================================
# INÍCIO
# ==========================================================

print("=" * 90)
print("ROBUSTEZ DAS TENDÊNCIAS DE EXTREMOS")
print("=" * 90)


for arquivo in [
    ARQUIVO_06G,
    ARQUIVO_06I,
]:

    if not arquivo.exists():

        raise FileNotFoundError(
            f"Arquivo não encontrado:\n"
            f"{arquivo}"
        )


# ==========================================================
# 1. CARREGAR RESULTADOS
# ==========================================================

g = pd.read_parquet(
    ARQUIVO_06G
)


i = pd.read_parquet(
    ARQUIVO_06I
)


print(
    f"\n06g: {len(g):,} registros"
)


print(
    f"06i: {len(i):,} registros"
)


# ==========================================================
# 2. VALIDAR COLUNAS
# ==========================================================

colunas_g = [
    "rede",
    "variavel",
    "codigo",
    "sen_slope_c_decada",
    "mk_p",
    "mk_p_fdr",
]


colunas_i = [
    "rede",
    "variavel",
    "codigo",
    "sen_slope_c_decada",
    "mk_p_classico",
    "mk_p_modificado",
    "mk_p_modificado_fdr",
    "ano_inicio",
    "ano_fim",
    "n_anos",
]


faltantes_g = [
    coluna
    for coluna in colunas_g
    if coluna not in g.columns
]


faltantes_i = [
    coluna
    for coluna in colunas_i
    if coluna not in i.columns
]


if faltantes_g:

    raise RuntimeError(
        f"Colunas ausentes no 06g: "
        f"{faltantes_g}"
    )


if faltantes_i:

    raise RuntimeError(
        f"Colunas ausentes no 06i: "
        f"{faltantes_i}"
    )


# ==========================================================
# 3. RESUMO DAS QUATRO REDES
# ==========================================================

linhas_resumo = []


for rede in [
    "principal_15a",
    "sensibilidade_10a",
]:

    for variavel in VARIAVEIS:

        linha = resumo_slopes(
            g,
            rede,
            variavel,
            coluna_p="mk_p",
            coluna_p_fdr="mk_p_fdr",
            metodo="MK clássico",
        )


        if linha is not None:

            linhas_resumo.append(
                linha
            )


for rede in [
    "principal_consecutiva_15a",
    "sensibilidade_consecutiva_10a",
]:

    for variavel in VARIAVEIS:

        linha = resumo_slopes(
            i,
            rede,
            variavel,
            coluna_p="mk_p_modificado",
            coluna_p_fdr="mk_p_modificado_fdr",
            metodo="Hamed-Rao",
        )


        if linha is not None:

            linhas_resumo.append(
                linha
            )


resumo = pd.DataFrame(
    linhas_resumo
)


resumo[
    "ordem_rede"
] = (
    resumo[
        "rede"
    ]
    .map(
        {
            rede:
                indice

            for indice, rede
            in enumerate(
                ORDEM_REDES
            )
        }
    )
)


resumo = (
    resumo
    .sort_values(
        [
            "ordem_rede",
            "variavel",
        ]
    )
    .drop(
        columns=[
            "ordem_rede",
        ]
    )
    .reset_index(
        drop=True
    )
)


resumo.to_csv(
    SAIDA_RESUMO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 4. CONCORDÂNCIA DE SINAL INMET × ERA5
# ==========================================================

linhas_concordancia = []


for rede in [
    "principal_15a",
    "sensibilidade_10a",
]:

    subset = (
        g[
            (
                g[
                    "rede"
                ]
                ==
                rede
            )
            &
            (
                g[
                    "variavel"
                ]
                .isin(
                    [
                        "tmax_inmet",
                        "tmax_era5",
                    ]
                )
            )
        ][
            [
                "codigo",
                "variavel",
                "sen_slope_c_decada",
            ]
        ]
        .pivot(
            index="codigo",
            columns="variavel",
            values="sen_slope_c_decada",
        )
        .dropna()
    )


    iguais, total, pct = mesmo_sinal(
        subset[
            "tmax_inmet"
        ],
        subset[
            "tmax_era5"
        ],
    )


    linhas_concordancia.append(
        {
            "rede":
                rede,

            "nome_rede":
                NOMES_REDES[
                    rede
                ],

            "metodo":
                "MK clássico",

            "n_estacoes":
                total,

            "n_mesmo_sinal":
                iguais,

            "pct_mesmo_sinal":
                pct,
        }
    )


for rede in [
    "principal_consecutiva_15a",
    "sensibilidade_consecutiva_10a",
]:

    subset = (
        i[
            (
                i[
                    "rede"
                ]
                ==
                rede
            )
            &
            (
                i[
                    "variavel"
                ]
                .isin(
                    [
                        "tmax_inmet",
                        "tmax_era5",
                    ]
                )
            )
        ][
            [
                "codigo",
                "variavel",
                "sen_slope_c_decada",
            ]
        ]
        .pivot(
            index="codigo",
            columns="variavel",
            values="sen_slope_c_decada",
        )
        .dropna()
    )


    iguais, total, pct = mesmo_sinal(
        subset[
            "tmax_inmet"
        ],
        subset[
            "tmax_era5"
        ],
    )


    linhas_concordancia.append(
        {
            "rede":
                rede,

            "nome_rede":
                NOMES_REDES[
                    rede
                ],

            "metodo":
                "Hamed-Rao",

            "n_estacoes":
                total,

            "n_mesmo_sinal":
                iguais,

            "pct_mesmo_sinal":
                pct,
        }
    )


concordancia = pd.DataFrame(
    linhas_concordancia
)


concordancia.to_csv(
    SAIDA_CONCORDANCIA,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 5. EFEITO ISOLADO DO HAMED-RAO
#
# Compara p clássico e p modificado na MESMA série.
# ==========================================================

metodos = (
    i[
        [
            "rede",
            "variavel",
            "codigo",
            "estacao",
            "uf",
            "regiao",
            "n_anos",
            "ano_inicio",
            "ano_fim",
            "sen_slope_c_decada",
            "rho1_rank_detrendido",
            "fator_correcao_hamed_rao",
            "mk_p_classico",
            "mk_p_modificado",
            "mk_p_modificado_fdr",
        ]
    ]
    .copy()
)


metodos[
    "classico_p05"
] = (
    metodos[
        "mk_p_classico"
    ]
    <
    ALPHA
)


metodos[
    "modificado_p05"
] = (
    metodos[
        "mk_p_modificado"
    ]
    <
    ALPHA
)


metodos[
    "modificado_fdr05"
] = (
    metodos[
        "mk_p_modificado_fdr"
    ]
    <
    ALPHA
)


metodos[
    "mudou_p05"
] = (
    metodos[
        "classico_p05"
    ]
    !=
    metodos[
        "modificado_p05"
    ]
)


metodos[
    "delta_p_modificado_menos_classico"
] = (
    metodos[
        "mk_p_modificado"
    ]
    -
    metodos[
        "mk_p_classico"
    ]
)


metodos.to_csv(
    SAIDA_METODOS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 6. COMPARAR SLOPES 06g × 06i NAS ESTAÇÕES COMUNS
#
# Atenção:
# slopes podem mudar porque o 06i usa somente o maior
# segmento consecutivo, não porque o Hamed-Rao altera
# Sen's Slope. O Hamed-Rao atua na inferência do MK.
# ==========================================================

pares_redes = [
    (
        "principal_15a",
        "principal_consecutiva_15a",
    ),

    (
        "sensibilidade_10a",
        "sensibilidade_consecutiva_10a",
    ),
]


linhas_comuns = []


for rede_g, rede_i in pares_redes:

    parte_g = (
        g[
            g[
                "rede"
            ]
            ==
            rede_g
        ][
            [
                "codigo",
                "variavel",
                "sen_slope_c_decada",
            ]
        ]
        .rename(
            columns={
                "sen_slope_c_decada":
                    "sen_06g_c_decada",
            }
        )
    )


    parte_i = (
        i[
            i[
                "rede"
            ]
            ==
            rede_i
        ][
            [
                "codigo",
                "variavel",
                "estacao",
                "uf",
                "regiao",
                "n_anos",
                "ano_inicio",
                "ano_fim",
                "sen_slope_c_decada",
            ]
        ]
        .rename(
            columns={
                "sen_slope_c_decada":
                    "sen_06i_segmento_c_decada",
            }
        )
    )


    comum = parte_i.merge(
        parte_g,
        on=[
            "codigo",
            "variavel",
        ],
        how="inner",
        validate="one_to_one",
    )


    comum[
        "rede_06g"
    ] = rede_g


    comum[
        "rede_06i"
    ] = rede_i


    comum[
        "delta_sen_06i_menos_06g"
    ] = (
        comum[
            "sen_06i_segmento_c_decada"
        ]
        -
        comum[
            "sen_06g_c_decada"
        ]
    )


    comum[
        "abs_delta_sen"
    ] = (
        comum[
            "delta_sen_06i_menos_06g"
        ]
        .abs()
    )


    comum[
        "mesmo_sinal_sen"
    ] = (
        np.sign(
            comum[
                "sen_06i_segmento_c_decada"
            ]
        )
        ==
        np.sign(
            comum[
                "sen_06g_c_decada"
            ]
        )
    )


    linhas_comuns.append(
        comum
    )


estacoes_comuns = pd.concat(
    linhas_comuns,
    ignore_index=True,
)


estacoes_comuns.to_csv(
    SAIDA_ESTACOES_COMUNS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 7. SÍNTESE DE ROBUSTEZ
# ==========================================================

linhas_sintese = []


for rede in ORDEM_REDES:

    fonte = (
        g
        if rede
        in [
            "principal_15a",
            "sensibilidade_10a",
        ]
        else
        i
    )


    subset = (
        fonte[
            fonte[
                "rede"
            ]
            ==
            rede
        ]
    )


    if subset.empty:

        continue


    pivot = (
        subset[
            subset[
                "variavel"
            ]
            .isin(
                [
                    "tmax_inmet",
                    "tmax_era5",
                ]
            )
        ][
            [
                "codigo",
                "variavel",
                "sen_slope_c_decada",
            ]
        ]
        .pivot(
            index="codigo",
            columns="variavel",
            values="sen_slope_c_decada",
        )
        .dropna()
    )


    iguais, total, pct = mesmo_sinal(
        pivot[
            "tmax_inmet"
        ],
        pivot[
            "tmax_era5"
        ],
    )


    inmet = resumo[
        (
            resumo[
                "rede"
            ]
            ==
            rede
        )
        &
        (
            resumo[
                "variavel"
            ]
            ==
            "tmax_inmet"
        )
    ].iloc[0]


    era5 = resumo[
        (
            resumo[
                "rede"
            ]
            ==
            rede
        )
        &
        (
            resumo[
                "variavel"
            ]
            ==
            "tmax_era5"
        )
    ].iloc[0]


    delta = resumo[
        (
            resumo[
                "rede"
            ]
            ==
            rede
        )
        &
        (
            resumo[
                "variavel"
            ]
            ==
            "delta_tmax"
        )
    ].iloc[0]


    linhas_sintese.append(
        {
            "rede":
                rede,

            "nome_rede":
                NOMES_REDES[
                    rede
                ],

            "n_estacoes":
                int(
                    inmet[
                        "n_estacoes"
                    ]
                ),

            "sen_inmet_mediana_c_decada":
                inmet[
                    "sen_mediana_c_decada"
                ],

            "sen_era5_mediana_c_decada":
                era5[
                    "sen_mediana_c_decada"
                ],

            "sen_delta_mediana_c_decada":
                delta[
                    "sen_mediana_c_decada"
                ],

            "pct_inmet_slope_positivo":
                inmet[
                    "pct_slope_positivo"
                ],

            "pct_era5_slope_positivo":
                era5[
                    "pct_slope_positivo"
                ],

            "pct_mesmo_sinal_inmet_era5":
                pct,

            "n_inmet_fdr05":
                inmet[
                    "n_fdr05"
                ],

            "n_era5_fdr05":
                era5[
                    "n_fdr05"
                ],

            "n_delta_fdr05":
                delta[
                    "n_fdr05"
                ],
        }
    )


sintese = pd.DataFrame(
    linhas_sintese
)


sintese.to_csv(
    SAIDA_SINTESE,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 8. IMPRESSÃO
# ==========================================================

print("\n" + "=" * 90)
print("SÍNTESE DAS QUATRO REDES")
print("=" * 90)


print(
    sintese.to_string(
        index=False,
        float_format=lambda x:
            f"{x:.4f}"
    )
)


print("\n" + "=" * 90)
print("EFEITO ISOLADO DO HAMED-RAO")
print("=" * 90)


resumo_metodos = (
    metodos
    .groupby(
        [
            "rede",
            "variavel",
        ],
        as_index=False,
    )
    .agg(
        n_estacoes=(
            "codigo",
            "nunique",
        ),

        fator_correcao_mediano=(
            "fator_correcao_hamed_rao",
            "median",
        ),

        n_classico_p05=(
            "classico_p05",
            "sum",
        ),

        n_modificado_p05=(
            "modificado_p05",
            "sum",
        ),

        n_mudou_p05=(
            "mudou_p05",
            "sum",
        ),

        mediana_delta_p=(
            "delta_p_modificado_menos_classico",
            "median",
        ),
    )
)


print(
    resumo_metodos.to_string(
        index=False,
        float_format=lambda x:
            f"{x:.5f}"
    )
)


print("\n" + "=" * 90)
print("ROBUSTEZ DO SINAL DAS SLOPES 06g × SEGMENTOS CONSECUTIVOS")
print("=" * 90)


resumo_comuns = (
    estacoes_comuns
    .groupby(
        [
            "rede_06g",
            "rede_06i",
            "variavel",
        ],
        as_index=False,
    )
    .agg(
        n_estacoes=(
            "codigo",
            "nunique",
        ),

        pct_mesmo_sinal=(
            "mesmo_sinal_sen",
            lambda x:
                float(
                    x.mean()
                    *
                    100
                ),
        ),

        mediana_abs_delta_sen=(
            "abs_delta_sen",
            "median",
        ),
    )
)


print(
    resumo_comuns.to_string(
        index=False,
        float_format=lambda x:
            f"{x:.4f}"
    )
)


print("\n" + "=" * 90)
print("ARQUIVOS GERADOS")
print("=" * 90)


for caminho in [
    SAIDA_RESUMO,
    SAIDA_CONCORDANCIA,
    SAIDA_METODOS,
    SAIDA_ESTACOES_COMUNS,
    SAIDA_SINTESE,
]:

    print(
        caminho
    )


print("\n" + "=" * 90)
print("ANÁLISE DE ROBUSTEZ CONCLUÍDA")
print("=" * 90)
