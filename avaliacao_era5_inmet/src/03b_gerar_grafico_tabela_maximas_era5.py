from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.stats import (
    linregress,
    theilslopes,
    norm,
)

from config import (
    TABLES_DIR,
    FIGURES_DIR,
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

ARQUIVO_ENTRADA = (
    TABLES_DIR
    / "maximas_anuais_era5_completo_1995_2025.csv"
)

ARQUIVO_TABELA_FINAL = (
    TABLES_DIR
    / "tabela_maximas_anuais_era5_final.csv"
)

ARQUIVO_TENDENCIA = (
    TABLES_DIR
    / "resumo_tendencia_maximas_era5.csv"
)

ARQUIVO_GRAFICO = (
    FIGURES_DIR
    / "maximas_anuais_era5_1995_2025.png"
)

ARQUIVO_TABELA_PNG = (
    FIGURES_DIR
    / "tabela_maximas_anuais_era5_1995_2025.png"
)


FIGURES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

TABLES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ==========================================================
# FUNÇÃO: MANN-KENDALL
# ==========================================================

def mann_kendall(valores):
    """
    Teste de Mann-Kendall com correção para empates.

    Retorna:
    S
    variância
    Z
    p-value
    tau
    tendência
    """

    valores = np.asarray(
        valores,
        dtype=float,
    )

    n = len(valores)

    S = 0


    for i in range(n - 1):

        for j in range(
            i + 1,
            n,
        ):

            S += np.sign(
                valores[j]
                -
                valores[i]
            )


    # ======================================================
    # CORREÇÃO DE EMPATES
    # ======================================================

    _, contagens = np.unique(
        valores,
        return_counts=True,
    )


    termo_empates = np.sum(
        contagens
        *
        (contagens - 1)
        *
        (2 * contagens + 5)
    )


    variancia = (
        n
        *
        (n - 1)
        *
        (2 * n + 5)
        -
        termo_empates
    ) / 18


    # ======================================================
    # ESTATÍSTICA Z
    # ======================================================

    if S > 0:

        Z = (
            S - 1
        ) / np.sqrt(
            variancia
        )

    elif S < 0:

        Z = (
            S + 1
        ) / np.sqrt(
            variancia
        )

    else:

        Z = 0.0


    p_value = (
        2
        *
        (
            1
            -
            norm.cdf(
                abs(Z)
            )
        )
    )


    tau = (
        S
        /
        (
            0.5
            *
            n
            *
            (n - 1)
        )
    )


    if p_value < 0.05:

        if Z > 0:

            tendencia = (
                "crescente significativa"
            )

        else:

            tendencia = (
                "decrescente significativa"
            )

    else:

        tendencia = (
            "sem tendência significativa"
        )


    return {
        "S": int(S),
        "variancia": float(
            variancia
        ),
        "Z": float(Z),
        "p_value": float(
            p_value
        ),
        "tau": float(tau),
        "tendencia": tendencia,
    }


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("TABELA E GRÁFICO DAS MÁXIMAS ANUAIS ERA5")
print("=" * 90)


# ==========================================================
# 1. CARREGAR RESULTADOS
# ==========================================================

if not ARQUIVO_ENTRADA.exists():

    raise FileNotFoundError(
        f"Arquivo não encontrado:\n"
        f"{ARQUIVO_ENTRADA}"
    )


df = pd.read_csv(
    ARQUIVO_ENTRADA
)


print(
    f"\nRegistros carregados: "
    f"{len(df)}"
)


if len(df) != 31:

    raise RuntimeError(
        "Esperávamos exatamente "
        "31 anos entre 1995 e 2025."
    )


# ==========================================================
# 2. PREPARAR TABELA FINAL
# ==========================================================

tabela = pd.DataFrame({

    "Ano":
        df["ano"],

    "Temperatura máxima (°C)":
        df[
            "maxima_completa_c"
        ].round(2),

    "Data/hora UTC":
        df[
            "data_hora_completa_utc"
        ],

    "Latitude":
        df[
            "latitude_completa"
        ],

    "Longitude":
        df[
            "longitude_completa"
        ],

    "Fonte":
        df[
            "fonte_maxima"
        ],
})


tabela.to_csv(
    ARQUIVO_TABELA_FINAL,
    index=False,
    encoding="utf-8",
)


print(
    "\nTabela final salva em:"
)

print(
    ARQUIVO_TABELA_FINAL
)


# ==========================================================
# 3. VETORES DA SÉRIE
# ==========================================================

anos = (
    df["ano"]
    .to_numpy(
        dtype=float
    )
)


temperaturas = (
    df[
        "maxima_completa_c"
    ]
    .to_numpy(
        dtype=float
    )
)


# ==========================================================
# 4. TENDÊNCIA LINEAR
# ==========================================================

linear = linregress(
    anos,
    temperaturas,
)


inclinacao_linear = float(
    linear.slope
)

intercepto_linear = float(
    linear.intercept
)

r_linear = float(
    linear.rvalue
)

r2_linear = (
    r_linear ** 2
)

p_linear = float(
    linear.pvalue
)


linha_linear = (
    inclinacao_linear
    *
    anos
    +
    intercepto_linear
)


# ==========================================================
# 5. SEN'S SLOPE
# ==========================================================

sen = theilslopes(
    temperaturas,
    anos,
    alpha=0.95,
)


sen_slope = float(
    sen.slope
)

sen_intercept = float(
    sen.intercept
)

sen_low = float(
    sen.low_slope
)

sen_high = float(
    sen.high_slope
)


linha_sen = (
    sen_slope
    *
    anos
    +
    sen_intercept
)


# ==========================================================
# 6. MANN-KENDALL
# ==========================================================

mk = mann_kendall(
    temperaturas
)


# ==========================================================
# 7. MAIOR VALOR
# ==========================================================

indice_maximo = int(
    np.argmax(
        temperaturas
    )
)


ano_maximo = int(
    anos[
        indice_maximo
    ]
)


temp_maxima = float(
    temperaturas[
        indice_maximo
    ]
)


registro_maximo = (
    df.iloc[
        indice_maximo
    ]
)


# ==========================================================
# 8. SALVAR RESULTADOS ESTATÍSTICOS
# ==========================================================

resumo = pd.DataFrame(
    [
        {
            "periodo":
                "1995-2025",

            "n_anos":
                len(df),

            "tendencia_linear_c_por_ano":
                inclinacao_linear,

            "tendencia_linear_c_por_decada":
                inclinacao_linear
                * 10,

            "r":
                r_linear,

            "r2":
                r2_linear,

            "p_tendencia_linear":
                p_linear,

            "mann_kendall_S":
                mk["S"],

            "mann_kendall_tau":
                mk["tau"],

            "mann_kendall_Z":
                mk["Z"],

            "mann_kendall_p":
                mk["p_value"],

            "mann_kendall_resultado":
                mk["tendencia"],

            "sen_slope_c_por_ano":
                sen_slope,

            "sen_slope_c_por_decada":
                sen_slope
                * 10,

            "sen_ic95_inferior":
                sen_low,

            "sen_ic95_superior":
                sen_high,

            "maior_temperatura_c":
                temp_maxima,

            "ano_maior_temperatura":
                ano_maximo,

            "data_hora_maior_utc":
                registro_maximo[
                    "data_hora_completa_utc"
                ],

            "latitude_maior":
                registro_maximo[
                    "latitude_completa"
                ],

            "longitude_maior":
                registro_maximo[
                    "longitude_completa"
                ],
        }
    ]
)


resumo.to_csv(
    ARQUIVO_TENDENCIA,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 9. MOSTRAR RESULTADOS
# ==========================================================

print("\n" + "=" * 90)
print("ANÁLISE DE TENDÊNCIA")
print("=" * 90)


print(
    f"\nTendência linear: "
    f"{inclinacao_linear:+.4f} °C/ano"
)


print(
    f"Equivalente por década: "
    f"{inclinacao_linear * 10:+.3f} °C/década"
)


print(
    f"R²: "
    f"{r2_linear:.4f}"
)


print(
    f"p linear: "
    f"{p_linear:.6f}"
)


print(
    "\nMann-Kendall:"
)


print(
    f"  S: "
    f"{mk['S']}"
)


print(
    f"  Tau: "
    f"{mk['tau']:.4f}"
)


print(
    f"  Z: "
    f"{mk['Z']:.4f}"
)


print(
    f"  p: "
    f"{mk['p_value']:.6f}"
)


print(
    f"  Resultado: "
    f"{mk['tendencia']}"
)


print(
    "\nSen's Slope:"
)


print(
    f"  {sen_slope:+.4f} °C/ano"
)


print(
    f"  {sen_slope * 10:+.3f} °C/década"
)


print(
    f"  IC95%: "
    f"{sen_low:+.4f} a "
    f"{sen_high:+.4f} °C/ano"
)


# ==========================================================
# 10. GRÁFICO
# ==========================================================

fig, ax = plt.subplots(
    figsize=(
        14,
        7,
    )
)


# Série anual
ax.plot(
    anos,
    temperaturas,
    marker="o",
    linewidth=1.8,
    label="Máxima anual ERA5",
)


# Tendência linear
ax.plot(
    anos,
    linha_linear,
    linestyle="--",
    linewidth=2,
    label=(
        "Tendência linear "
        f"({inclinacao_linear:+.3f} °C/ano)"
    ),
)


# Sen
ax.plot(
    anos,
    linha_sen,
    linestyle=":",
    linewidth=2,
    label=(
        "Sen's Slope "
        f"({sen_slope:+.3f} °C/ano)"
    ),
)


# Destacar recorde
ax.scatter(
    ano_maximo,
    temp_maxima,
    s=100,
    zorder=5,
)


ax.annotate(
    (
        f"{temp_maxima:.2f} °C\n"
        f"{ano_maximo}"
    ),
    xy=(
        ano_maximo,
        temp_maxima,
    ),
    xytext=(
        ano_maximo - 4,
        temp_maxima + 0.45,
    ),
    arrowprops={
        "arrowstyle": "->",
    },
)


# ==========================================================
# FORMATAÇÃO
# ==========================================================

ax.set_title(
    (
        "Maior temperatura registrada no ERA5 "
        "em cada ano — Brasil\n"
        "Cobertura horária completa, 1995–2025"
    ),
    fontsize=15,
)


ax.set_xlabel(
    "Ano"
)


ax.set_ylabel(
    "Temperatura máxima (°C)"
)


ax.set_xticks(
    np.arange(
        1995,
        2026,
        2,
    )
)


ax.grid(
    True,
    alpha=0.25,
)


ax.legend()


texto_estatistico = (
    f"Mann-Kendall: "
    f"{mk['tendencia']}\n"
    f"p = {mk['p_value']:.4f}\n"
    f"Sen = "
    f"{sen_slope:+.3f} °C/ano"
)


ax.text(
    0.02,
    0.97,
    texto_estatistico,
    transform=ax.transAxes,
    verticalalignment="top",
    bbox={
        "boxstyle":
            "round",

        "alpha":
            0.15,
    },
)


fig.tight_layout()


fig.savefig(
    ARQUIVO_GRAFICO,
    dpi=300,
    bbox_inches="tight",
)


plt.close(
    fig
)


print(
    "\nGráfico salvo em:"
)

print(
    ARQUIVO_GRAFICO
)


# ==========================================================
# 11. IMAGEM DA TABELA
# ==========================================================

tabela_png = tabela.copy()


tabela_png[
    "Temperatura máxima (°C)"
] = tabela_png[
    "Temperatura máxima (°C)"
].map(
    lambda x:
        f"{x:.2f}"
)


tabela_png[
    "Latitude"
] = tabela_png[
    "Latitude"
].map(
    lambda x:
        f"{x:.2f}"
)


tabela_png[
    "Longitude"
] = tabela_png[
    "Longitude"
].map(
    lambda x:
        f"{x:.2f}"
)


fig_tabela, ax_tabela = plt.subplots(
    figsize=(
        12,
        17,
    )
)


ax_tabela.axis(
    "off"
)


tabela_artist = ax_tabela.table(
    cellText=tabela_png.values,
    colLabels=tabela_png.columns,
    cellLoc="center",
    loc="center",
)


tabela_artist.auto_set_font_size(
    False
)


tabela_artist.set_fontsize(
    8
)


tabela_artist.scale(
    1,
    1.35,
)


ax_tabela.set_title(
    (
        "Temperaturas máximas anuais ERA5 — Brasil\n"
        "1995–2025 | Cobertura horária: 100%"
    ),
    fontsize=14,
    pad=20,
)


fig_tabela.tight_layout()


fig_tabela.savefig(
    ARQUIVO_TABELA_PNG,
    dpi=300,
    bbox_inches="tight",
)


plt.close(
    fig_tabela
)


print(
    "\nImagem da tabela salva em:"
)

print(
    ARQUIVO_TABELA_PNG
)


print(
    "\nResumo estatístico salvo em:"
)

print(
    ARQUIVO_TENDENCIA
)


print("\n" + "=" * 90)
print("PROCESSAMENTO CONCLUÍDO")
print("=" * 90)