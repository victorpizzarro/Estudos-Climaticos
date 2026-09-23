from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import (
    PROJECT_DIR,
    TABLES_DIR,
    FIGURES_DIR,
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


ARQUIVO_METRICAS = (
    ANNUAL_DIR
    / "metricas_anuais_regionais_era5_inmet.parquet"
)


ARQUIVO_IMPACTO = (
    TABLES_DIR
    / "impacto_qc_metricas_anuais_regionais.csv"
)


SAIDA_DIR = (
    FIGURES_DIR
    / "desempenho_era5_inmet"
)


SAIDA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ==========================================================
# CONFIGURAÇÃO VISUAL
# ==========================================================

plt.rcParams.update(
    {
        "figure.figsize": (11, 6),
        "figure.dpi": 120,
        "savefig.dpi": 300,

        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 12,

        "xtick.labelsize": 10,
        "ytick.labelsize": 10,

        "legend.fontsize": 10,

        "axes.grid": True,
        "grid.alpha": 0.25,

        "figure.autolayout": True,
    }
)


# ==========================================================
# AUXILIARES
# ==========================================================

def salvar(
    nome,
):

    caminho = (
        SAIDA_DIR
        / nome
    )

    plt.savefig(
        caminho,
        bbox_inches="tight",
    )

    print(
        f"Salvo: {caminho.name}"
    )

    plt.close()


def preparar_eixo_anos():

    plt.xticks(
        range(
            2000,
            2026,
            2,
        ),
        rotation=45,
    )


# ==========================================================
# CARREGAR
# ==========================================================

if not ARQUIVO_METRICAS.exists():

    raise FileNotFoundError(
        ARQUIVO_METRICAS
    )


dados = pd.read_parquet(
    ARQUIVO_METRICAS
)


principal = (
    dados[
        dados[
            "amostra"
        ]
        ==
        "principal"
    ]
    .copy()
)


brasil = (
    principal[
        principal[
            "area"
        ]
        ==
        "Brasil"
    ]
    .sort_values(
        "ano"
    )
)


print("=" * 90)
print("GRÁFICOS DE DESEMPENHO ERA5 × INMET")
print("=" * 90)


# ==========================================================
# 1. BIAS BRASIL
# ==========================================================

plt.figure()


plt.plot(
    brasil["ano"],
    brasil["bias_pares_c"],
    marker="o",
    linewidth=2,
    label="Todos os pares horários",
)


plt.plot(
    brasil["ano"],
    brasil["bias_media_estacoes_c"],
    marker="s",
    linewidth=2,
    label="Peso igual por estação",
)


plt.axhline(
    0,
    linewidth=1,
)


plt.xlabel(
    "Ano"
)


plt.ylabel(
    "Bias (°C)"
)


plt.title(
    "Bias anual ERA5 − INMET no Brasil"
)


plt.legend()


preparar_eixo_anos()


salvar(
    "01_bias_anual_brasil.png"
)


# ==========================================================
# 2. RMSE BRASIL
# ==========================================================

plt.figure()


plt.plot(
    brasil["ano"],
    brasil["rmse_pares_c"],
    marker="o",
    linewidth=2,
    label="Todos os pares horários",
)


plt.plot(
    brasil["ano"],
    brasil["rmse_equilibrado_estacoes_c"],
    marker="s",
    linewidth=2,
    label="Peso igual por estação",
)


plt.xlabel(
    "Ano"
)


plt.ylabel(
    "RMSE (°C)"
)


plt.title(
    "RMSE anual ERA5 × INMET no Brasil"
)


plt.legend()


preparar_eixo_anos()


salvar(
    "02_rmse_anual_brasil.png"
)


# ==========================================================
# 3. CORRELAÇÃO BRASIL
# ==========================================================

plt.figure()


plt.plot(
    brasil["ano"],
    brasil["correlacao_pares"],
    marker="o",
    linewidth=2,
    label="Correlação com todos os pares",
)


plt.plot(
    brasil["ano"],
    brasil["correlacao_mediana_estacoes"],
    marker="s",
    linewidth=2,
    label="Mediana das correlações por estação",
)


plt.xlabel(
    "Ano"
)


plt.ylabel(
    "Correlação de Pearson"
)


plt.title(
    "Correlação anual ERA5 × INMET no Brasil"
)


plt.ylim(
    0.80,
    1.00,
)


plt.legend()


preparar_eixo_anos()


salvar(
    "03_correlacao_anual_brasil.png"
)


# ==========================================================
# 4. REDE DE ESTAÇÕES
# ==========================================================

plt.figure()


plt.plot(
    brasil["ano"],
    brasil["n_estacoes"],
    marker="o",
    linewidth=2,
    label="Estações com pares",
)


plt.plot(
    brasil["ano"],
    brasil[
        "n_estacoes_equilibradas"
    ],
    marker="s",
    linewidth=2,
    label="Estações com ≥100 pares",
)


plt.xlabel(
    "Ano"
)


plt.ylabel(
    "Número de estações"
)


plt.title(
    "Evolução da rede INMET utilizada na validação"
)


plt.legend()


preparar_eixo_anos()


salvar(
    "04_numero_estacoes_por_ano.png"
)


# ==========================================================
# 5. BIAS REGIONAL
# ==========================================================

regioes = [
    "Norte",
    "Nordeste",
    "Centro-Oeste",
    "Sudeste",
    "Sul",
]


plt.figure(
    figsize=(
        12,
        7,
    )
)


for regiao in regioes:

    subset = (
        principal[
            principal[
                "area"
            ]
            ==
            regiao
        ]
        .sort_values(
            "ano"
        )
    )


    plt.plot(
        subset["ano"],
        subset[
            "bias_media_estacoes_c"
        ],
        marker="o",
        linewidth=1.8,
        label=regiao,
    )


plt.axhline(
    0,
    linewidth=1,
)


plt.xlabel(
    "Ano"
)


plt.ylabel(
    "Bias médio entre estações (°C)"
)


plt.title(
    "Bias anual ERA5 − INMET por região"
)


plt.legend(
    ncol=2
)


preparar_eixo_anos()


salvar(
    "05_bias_anual_regioes.png"
)


# ==========================================================
# 6. RMSE REGIONAL
# ==========================================================

plt.figure(
    figsize=(
        12,
        7,
    )
)


for regiao in regioes:

    subset = (
        principal[
            principal[
                "area"
            ]
            ==
            regiao
        ]
        .sort_values(
            "ano"
        )
    )


    plt.plot(
        subset["ano"],
        subset[
            "rmse_equilibrado_estacoes_c"
        ],
        marker="o",
        linewidth=1.8,
        label=regiao,
    )


plt.xlabel(
    "Ano"
)


plt.ylabel(
    "RMSE equilibrado entre estações (°C)"
)


plt.title(
    "RMSE anual ERA5 × INMET por região"
)


plt.legend(
    ncol=2
)


preparar_eixo_anos()


salvar(
    "06_rmse_anual_regioes.png"
)


# ==========================================================
# 7. BIAS: PARES × ESTAÇÕES
# ==========================================================

plt.figure()


x = brasil[
    "bias_pares_c"
]


y = brasil[
    "bias_media_estacoes_c"
]


plt.scatter(
    x,
    y,
    s=55,
)


minimo = min(
    x.min(),
    y.min(),
)


maximo = max(
    x.max(),
    y.max(),
)


plt.plot(
    [
        minimo,
        maximo,
    ],
    [
        minimo,
        maximo,
    ],
    linewidth=1,
)


for _, linha in brasil.iterrows():

    plt.annotate(
        str(
            int(
                linha[
                    "ano"
                ]
            )
        ),
        (
            linha[
                "bias_pares_c"
            ],
            linha[
                "bias_media_estacoes_c"
            ],
        ),
        fontsize=7,
        alpha=0.7,
    )


plt.xlabel(
    "Bias ponderado pelos pares (°C)"
)


plt.ylabel(
    "Bias com peso igual por estação (°C)"
)


plt.title(
    "Sensibilidade do Bias ao método de agregação"
)


salvar(
    "07_bias_pares_vs_estacoes.png"
)


# ==========================================================
# 8. RMSE: PARES × ESTAÇÕES
# ==========================================================

plt.figure()


x = brasil[
    "rmse_pares_c"
]


y = brasil[
    "rmse_equilibrado_estacoes_c"
]


plt.scatter(
    x,
    y,
    s=55,
)


minimo = min(
    x.min(),
    y.min(),
)


maximo = max(
    x.max(),
    y.max(),
)


plt.plot(
    [
        minimo,
        maximo,
    ],
    [
        minimo,
        maximo,
    ],
    linewidth=1,
)


for _, linha in brasil.iterrows():

    plt.annotate(
        str(
            int(
                linha[
                    "ano"
                ]
            )
        ),
        (
            linha[
                "rmse_pares_c"
            ],
            linha[
                "rmse_equilibrado_estacoes_c"
            ],
        ),
        fontsize=7,
        alpha=0.7,
    )


plt.xlabel(
    "RMSE ponderado pelos pares (°C)"
)


plt.ylabel(
    "RMSE equilibrado entre estações (°C)"
)


plt.title(
    "Sensibilidade do RMSE ao método de agregação"
)


salvar(
    "08_rmse_pares_vs_estacoes.png"
)


# ==========================================================
# 9. IMPACTO DO QC
# ==========================================================

if ARQUIVO_IMPACTO.exists():

    impacto = pd.read_csv(
        ARQUIVO_IMPACTO
    )


    impacto_brasil = (
        impacto[
            (
                impacto[
                    "area"
                ]
                ==
                "Brasil"
            )
            &
            (
                impacto[
                    "pares_removidos_qc"
                ]
                >
                0
            )
        ]
        .copy()
    )


    if not impacto_brasil.empty:

        plt.figure()


        largura = 0.35


        x = np.arange(
            len(
                impacto_brasil
            )
        )


        plt.bar(
            x - largura / 2,
            impacto_brasil[
                "delta_bias_qc_c"
            ],
            width=largura,
            label="Δ Bias",
        )


        plt.bar(
            x + largura / 2,
            impacto_brasil[
                "delta_rmse_qc_c"
            ],
            width=largura,
            label="Δ RMSE",
        )


        plt.axhline(
            0,
            linewidth=1,
        )


        plt.xticks(
            x,
            impacto_brasil[
                "ano"
            ].astype(str),
        )


        plt.xlabel(
            "Ano"
        )


        plt.ylabel(
            "Principal − completa (°C)"
        )


        plt.title(
            "Impacto do QC nas métricas anuais do Brasil"
        )


        plt.legend()


        salvar(
            "09_impacto_qc_brasil.png"
        )


# ==========================================================
# 10. PAINEL NUMÉRICO NO TERMINAL
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO NUMÉRICO - BRASIL")
print("=" * 90)


for coluna, nome in [
    (
        "bias_pares_c",
        "Bias por pares",
    ),
    (
        "bias_media_estacoes_c",
        "Bias equilibrado",
    ),
    (
        "mae_pares_c",
        "MAE por pares",
    ),
    (
        "rmse_pares_c",
        "RMSE por pares",
    ),
    (
        "rmse_equilibrado_estacoes_c",
        "RMSE equilibrado",
    ),
    (
        "correlacao_pares",
        "Correlação por pares",
    ),
    (
        "correlacao_mediana_estacoes",
        "Correlação mediana estações",
    ),
]:

    serie = (
        brasil[
            coluna
        ]
        .dropna()
    )


    print(
        f"\n{nome}:"
    )


    print(
        f"  mínimo anual: "
        f"{serie.min():.4f}"
    )


    print(
        f"  mediana anual: "
        f"{serie.median():.4f}"
    )


    print(
        f"  média anual: "
        f"{serie.mean():.4f}"
    )


    print(
        f"  máximo anual: "
        f"{serie.max():.4f}"
    )


print("\n" + "=" * 90)
print("FIGURAS GERADAS")
print("=" * 90)


for caminho in sorted(
    SAIDA_DIR.glob(
        "*.png"
    )
):

    print(
        caminho
    )


print("\n" + "=" * 90)
print("GRÁFICOS CONCLUÍDOS")
print("=" * 90)