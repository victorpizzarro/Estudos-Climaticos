from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize

from config import (
    PROJECT_DIR,
    TABLES_DIR,
    FIGURES_DIR,
    IBGE_SHAPEFILE,
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


ARQUIVO_TENDENCIAS = (
    ANNUAL_DIR
    / "tendencias_extremos_estacoes.parquet"
)


# Fonte preferencial das coordenadas:
# associação estação-ano com a grade ERA5.
ARQUIVO_COORDENADAS_MATCHES = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "matches"
    / "inmet_era5_estacao_ano.csv"
)


# Fontes alternativas caso a primeira não esteja disponível
# ou use outra estrutura.
ARQUIVO_CATALOGO_ESTACOES = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "stations"
    / "catalogo_estacoes_inmet.csv"
)


ARQUIVO_METRICAS_ESTACAO = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "stations"
    / "metricas_era5_inmet_por_estacao.parquet"
)


SAIDA_DIR = (
    FIGURES_DIR
    / "tendencias_extremos"
)


SAIDA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


SAIDA_RESUMO = (
    TABLES_DIR
    / "resumo_figuras_tendencias_extremos.csv"
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

REDES = {
    "principal_15a": {
        "nome": "Rede principal (>=15 anos válidos)",
        "esperado": 45,
        "tamanho_ponto": 55,
    },

    "sensibilidade_10a": {
        "nome": "Rede de sensibilidade (>=10 anos válidos)",
        "esperado": 214,
        "tamanho_ponto": 28,
    },
}


VARIAVEIS = {
    "tmax_inmet": {
        "nome": "Tmax INMET",
        "arquivo": "tmax_inmet",
    },

    "tmax_era5": {
        "nome": "Tmax ERA5",
        "arquivo": "tmax_era5",
    },

    "delta_tmax": {
        "nome": "Delta Tmax (ERA5 - INMET)",
        "arquivo": "delta_tmax",
    },
}


# ==========================================================
# CONFIGURAÇÃO VISUAL
# ==========================================================

plt.rcParams.update(
    {
        "figure.figsize": (10, 9),
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "figure.autolayout": True,
    }
)


# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def salvar_figura(nome):

    caminho = (
        SAIDA_DIR
        / nome
    )

    plt.savefig(
        caminho,
        bbox_inches="tight",
    )

    plt.close()

    print(
        f"Salvo: {caminho.name}"
    )


def primeira_coluna_existente(
    colunas,
    candidatos,
):

    for candidato in candidatos:

        if candidato in colunas:

            return candidato

    return None


def mediana_numerica(serie):

    serie = pd.to_numeric(
        serie,
        errors="coerce",
    ).dropna()

    if serie.empty:

        return np.nan

    return float(
        serie.median()
    )


def ler_arquivo_metadata(
    caminho,
):

    if caminho.suffix.lower() == ".parquet":

        return pd.read_parquet(
            caminho
        )

    return pd.read_csv(
        caminho
    )


def extrair_coordenadas_de_arquivo(
    caminho,
):

    if not caminho.exists():

        return None


    try:

        df = ler_arquivo_metadata(
            caminho
        )

    except Exception as erro:

        print(
            f"AVISO: não foi possível ler "
            f"{caminho.name}: {erro}"
        )

        return None


    coluna_codigo = primeira_coluna_existente(
        df.columns,
        [
            "codigo",
            "codigo_estacao",
            "cod_estacao",
        ],
    )


    coluna_lat = primeira_coluna_existente(
        df.columns,
        [
            "latitude",
            "latitude_estacao",
            "lat_estacao",
            "lat",
        ],
    )


    coluna_lon = primeira_coluna_existente(
        df.columns,
        [
            "longitude",
            "longitude_estacao",
            "lon_estacao",
            "lon",
        ],
    )


    if (
        coluna_codigo is None
        or
        coluna_lat is None
        or
        coluna_lon is None
    ):

        print(
            f"AVISO: {caminho.name} existe, "
            f"mas não possui colunas reconhecidas "
            f"de código/latitude/longitude."
        )

        print(
            "  Colunas disponíveis: "
            + ", ".join(
                map(
                    str,
                    df.columns,
                )
            )
        )

        return None


    aux = df[
        [
            coluna_codigo,
            coluna_lat,
            coluna_lon,
        ]
    ].copy()


    aux = aux.rename(
        columns={
            coluna_codigo:
                "codigo",

            coluna_lat:
                "latitude",

            coluna_lon:
                "longitude",
        }
    )


    aux[
        "codigo"
    ] = (
        aux[
            "codigo"
        ]
        .astype(str)
        .str.strip()
    )


    aux[
        "latitude"
    ] = pd.to_numeric(
        aux[
            "latitude"
        ],
        errors="coerce",
    )


    aux[
        "longitude"
    ] = pd.to_numeric(
        aux[
            "longitude"
        ],
        errors="coerce",
    )


    aux = (
        aux
        .dropna(
            subset=[
                "codigo",
                "latitude",
                "longitude",
            ]
        )
        .groupby(
            "codigo",
            as_index=False,
        )
        .agg(
            latitude=(
                "latitude",
                mediana_numerica,
            ),

            longitude=(
                "longitude",
                mediana_numerica,
            ),
        )
    )


    aux = aux[
        aux[
            "latitude"
        ].between(
            -35,
            7,
        )
        &
        aux[
            "longitude"
        ].between(
            -75,
            -30,
        )
    ].copy()


    if aux.empty:

        print(
            f"AVISO: {caminho.name} não produziu "
            f"coordenadas válidas para o domínio brasileiro."
        )

        return None


    print(
        f"Coordenadas carregadas de "
        f"{caminho.name}: "
        f"{aux['codigo'].nunique():,} estações"
    )


    return aux


def carregar_coordenadas():

    candidatos = [
        ARQUIVO_COORDENADAS_MATCHES,
        ARQUIVO_CATALOGO_ESTACOES,
        ARQUIVO_METRICAS_ESTACAO,
    ]


    for caminho in candidatos:

        coordenadas = (
            extrair_coordenadas_de_arquivo(
                caminho
            )
        )


        if coordenadas is not None:

            return (
                coordenadas,
                caminho,
            )


    raise RuntimeError(
        "Não foi possível obter latitude/longitude "
        "de nenhuma fonte conhecida.\n"
        "Arquivos tentados:\n"
        +
        "\n".join(
            str(caminho)
            for caminho in candidatos
        )
    )


def validar_coordenadas(
    df,
):

    df = df.copy()


    df[
        "latitude"
    ] = pd.to_numeric(
        df[
            "latitude"
        ],
        errors="coerce",
    )


    df[
        "longitude"
    ] = pd.to_numeric(
        df[
            "longitude"
        ],
        errors="coerce",
    )


    return df[
        df[
            "latitude"
        ].between(
            -35,
            7,
        )
        &
        df[
            "longitude"
        ].between(
            -75,
            -30,
        )
    ].copy()


# ==========================================================
# INÍCIO
# ==========================================================

print("=" * 90)
print("MAPAS E GRÁFICOS DAS TENDÊNCIAS DE EXTREMOS")
print("=" * 90)


if not ARQUIVO_TENDENCIAS.exists():

    raise FileNotFoundError(
        f"Arquivo de tendências não encontrado:\n"
        f"{ARQUIVO_TENDENCIAS}"
    )


if not IBGE_SHAPEFILE.exists():

    raise FileNotFoundError(
        f"Shapefile do Brasil não encontrado:\n"
        f"{IBGE_SHAPEFILE}"
    )


# ==========================================================
# 1. CARREGAR TENDÊNCIAS
# ==========================================================

dados = pd.read_parquet(
    ARQUIVO_TENDENCIAS
)


print(
    f"\nRegistros de tendência carregados: "
    f"{len(dados):,}"
)


print(
    f"Estações presentes nas tendências: "
    f"{dados['codigo'].nunique():,}"
)


# ==========================================================
# 2. VALIDAR COLUNAS DAS TENDÊNCIAS
# ==========================================================

colunas_obrigatorias = [
    "rede",
    "variavel",
    "codigo",
    "estacao",
    "uf",
    "regiao",
    "sen_slope_c_decada",
    "mk_p",
    "mk_p_fdr",
    "significativo_fdr05",
]


faltantes = [
    coluna
    for coluna in colunas_obrigatorias
    if coluna not in dados.columns
]


if faltantes:

    raise RuntimeError(
        "Colunas ausentes em "
        "tendencias_extremos_estacoes.parquet: "
        f"{faltantes}"
    )


dados[
    "codigo"
] = (
    dados[
        "codigo"
    ]
    .astype(str)
    .str.strip()
)


# ==========================================================
# 3. COORDENADAS
#
# O 06g não gravou latitude/longitude porque o arquivo de
# máximas anuais não possuía essas colunas. Para os mapas,
# recuperamos as coordenadas diretamente do cadastro/match
# das estações.
# ==========================================================

if (
    "latitude"
    in dados.columns
    and
    "longitude"
    in dados.columns
):

    print(
        "\nLatitude/longitude já existem "
        "no arquivo de tendências."
    )


else:

    print(
        "\nLatitude/longitude não existem "
        "no arquivo de tendências."
    )

    print(
        "Buscando coordenadas nos arquivos "
        "de metadados da estação..."
    )


    coordenadas, fonte_coordenadas = (
        carregar_coordenadas()
    )


    dados = dados.merge(
        coordenadas,
        on="codigo",
        how="left",
        validate="many_to_one",
    )


    print(
        f"Fonte utilizada: "
        f"{fonte_coordenadas}"
    )


sem_coordenada = (
    dados[
        dados[
            "latitude"
        ].isna()
        |
        dados[
            "longitude"
        ].isna()
    ][
        [
            "codigo",
            "estacao",
            "uf",
        ]
    ]
    .drop_duplicates()
)


if not sem_coordenada.empty:

    print(
        "\nEstações sem coordenadas:"
    )

    print(
        sem_coordenada.to_string(
            index=False
        )
    )

    raise RuntimeError(
        f"{len(sem_coordenada):,} estação(ões) "
        f"da análise ficaram sem coordenadas."
    )


dados = validar_coordenadas(
    dados
)


print(
    f"\nRegistros com coordenadas válidas: "
    f"{len(dados):,}"
)


# ==========================================================
# 4. CARREGAR MAPA DO BRASIL
# ==========================================================

brasil = gpd.read_file(
    IBGE_SHAPEFILE
)


if brasil.crs is None:

    raise RuntimeError(
        "O shapefile não possui CRS definido."
    )


brasil = brasil.to_crs(
    "EPSG:4326"
)


# ==========================================================
# 5. VALIDAR REDES
# ==========================================================

for rede, config in REDES.items():

    subset = (
        dados[
            dados[
                "rede"
            ]
            ==
            rede
        ]
    )


    n_estacoes = (
        subset[
            "codigo"
        ]
        .nunique()
    )


    print(
        f"{rede}: "
        f"{n_estacoes:,} estações com coordenadas"
    )


    if n_estacoes != config[
        "esperado"
    ]:

        raise RuntimeError(
            f"A rede {rede} deveria possuir "
            f"{config['esperado']} estações, "
            f"mas encontramos {n_estacoes}."
        )


# ==========================================================
# 6. ESCALAS COMUNS DOS MAPAS
#
# A mesma variável usa a mesma escala na rede de 15 anos
# e na rede de 10 anos, facilitando a comparação visual.
# ==========================================================

limites = {}


for variavel in VARIAVEIS:

    valores = (
        dados.loc[
            dados[
                "variavel"
            ]
            ==
            variavel,
            "sen_slope_c_decada",
        ]
        .dropna()
        .astype(float)
    )


    limite = float(
        np.nanmax(
            np.abs(
                valores
            )
        )
    )


    if (
        not np.isfinite(
            limite
        )
        or
        limite == 0
    ):

        limite = 1.0


    limites[
        variavel
    ] = limite


# ==========================================================
# 7. MAPAS DE SEN'S SLOPE
# ==========================================================

resumo_figuras = []


for rede, config_rede in REDES.items():

    for variavel, config_var in VARIAVEIS.items():

        subset = (
            dados[
                (
                    dados[
                        "rede"
                    ]
                    ==
                    rede
                )
                &
                (
                    dados[
                        "variavel"
                    ]
                    ==
                    variavel
                )
            ]
            .copy()
        )


        if subset.empty:

            continue


        limite = limites[
            variavel
        ]


        norm = Normalize(
            vmin=-limite,
            vmax=limite,
        )


        fig, ax = plt.subplots(
            figsize=(
                10,
                9,
            )
        )


        brasil.plot(
            ax=ax,
            facecolor="none",
            edgecolor="black",
            linewidth=0.7,
        )


        pontos = ax.scatter(
            subset[
                "longitude"
            ],
            subset[
                "latitude"
            ],
            c=subset[
                "sen_slope_c_decada"
            ],
            cmap="coolwarm",
            norm=norm,
            s=config_rede[
                "tamanho_ponto"
            ],
            alpha=0.90,
            linewidths=0.25,
            edgecolors="black",
        )


        cbar = fig.colorbar(
            pontos,
            ax=ax,
            shrink=0.78,
            pad=0.02,
        )


        cbar.set_label(
            "Sen's Slope (°C/década)"
        )


        ax.set_title(
            f"{config_var['nome']} - "
            f"{config_rede['nome']}\n"
            f"n = "
            f"{subset['codigo'].nunique()} "
            f"estações"
        )


        ax.set_xlabel(
            "Longitude"
        )


        ax.set_ylabel(
            "Latitude"
        )


        ax.set_xlim(
            -75,
            -30,
        )


        ax.set_ylim(
            -35,
            7,
        )


        ax.grid(
            alpha=0.20
        )


        nome_arquivo = (
            f"mapa_"
            f"{config_var['arquivo']}_"
            f"{rede}.png"
        )


        salvar_figura(
            nome_arquivo
        )


        resumo_figuras.append(
            {
                "tipo":
                    "mapa",

                "rede":
                    rede,

                "variavel":
                    variavel,

                "n_estacoes":
                    subset[
                        "codigo"
                    ]
                    .nunique(),

                "sen_mediana_c_decada":
                    subset[
                        "sen_slope_c_decada"
                    ]
                    .median(),

                "sen_media_c_decada":
                    subset[
                        "sen_slope_c_decada"
                    ]
                    .mean(),

                "n_slope_positivo":
                    int(
                        (
                            subset[
                                "sen_slope_c_decada"
                            ]
                            >
                            0
                        )
                        .sum()
                    ),

                "n_slope_negativo":
                    int(
                        (
                            subset[
                                "sen_slope_c_decada"
                            ]
                            <
                            0
                        )
                        .sum()
                    ),

                "n_significativo_fdr":
                    int(
                        subset[
                            "significativo_fdr05"
                        ]
                        .fillna(False)
                        .sum()
                    ),
            }
        )


# ==========================================================
# 8. COMPARAÇÃO SEN INMET × ERA5
# ==========================================================

for rede, config_rede in REDES.items():

    subset = (
        dados[
            (
                dados[
                    "rede"
                ]
                ==
                rede
            )
            &
            (
                dados[
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
        .reset_index()
    )


    x = subset[
        "tmax_inmet"
    ].astype(float)


    y = subset[
        "tmax_era5"
    ].astype(float)


    minimo = float(
        min(
            x.min(),
            y.min(),
        )
    )


    maximo = float(
        max(
            x.max(),
            y.max(),
        )
    )


    margem = (
        maximo
        -
        minimo
    ) * 0.08


    if margem == 0:

        margem = 0.1


    minimo_plot = (
        minimo
        -
        margem
    )


    maximo_plot = (
        maximo
        +
        margem
    )


    correlacao = float(
        np.corrcoef(
            x,
            y,
        )[0, 1]
    )


    mae_slopes = float(
        np.mean(
            np.abs(
                y
                -
                x
            )
        )
    )


    mesmo_sinal = int(
        (
            np.sign(
                x
            )
            ==
            np.sign(
                y
            )
        )
        .sum()
    )


    plt.figure(
        figsize=(
            8,
            8,
        )
    )


    plt.scatter(
        x,
        y,
        s=45,
        alpha=0.8,
    )


    plt.plot(
        [
            minimo_plot,
            maximo_plot,
        ],
        [
            minimo_plot,
            maximo_plot,
        ],
        linewidth=1,
    )


    plt.axhline(
        0,
        linewidth=0.8,
    )


    plt.axvline(
        0,
        linewidth=0.8,
    )


    plt.xlim(
        minimo_plot,
        maximo_plot,
    )


    plt.ylim(
        minimo_plot,
        maximo_plot,
    )


    plt.xlabel(
        "Sen's Slope INMET (°C/década)"
    )


    plt.ylabel(
        "Sen's Slope ERA5 (°C/década)"
    )


    plt.title(
        f"Tendência das máximas: "
        f"INMET × ERA5\n"
        f"{config_rede['nome']}"
    )


    texto = (
        f"n = {len(subset)}\n"
        f"r entre slopes = "
        f"{correlacao:.3f}\n"
        f"MAE entre slopes = "
        f"{mae_slopes:.3f} °C/década\n"
        f"mesmo sinal = "
        f"{mesmo_sinal}/{len(subset)}"
    )


    plt.text(
        0.03,
        0.97,
        texto,
        transform=plt.gca().transAxes,
        va="top",
        bbox={
            "boxstyle": "round",
            "facecolor": "white",
            "alpha": 0.85,
        },
    )


    plt.grid(
        alpha=0.20
    )


    salvar_figura(
        f"scatter_sen_inmet_era5_"
        f"{rede}.png"
    )


# ==========================================================
# 9. DISTRIBUIÇÃO DAS SLOPES NA REDE PRINCIPAL
# ==========================================================

principal = (
    dados[
        dados[
            "rede"
        ]
        ==
        "principal_15a"
    ]
)


for variavel, config_var in VARIAVEIS.items():

    subset = (
        principal[
            principal[
                "variavel"
            ]
            ==
            variavel
        ][
            "sen_slope_c_decada"
        ]
        .dropna()
        .astype(float)
    )


    plt.figure(
        figsize=(
            9,
            6,
        )
    )


    plt.hist(
        subset,
        bins=12,
        edgecolor="black",
    )


    plt.axvline(
        0,
        linewidth=1,
    )


    plt.axvline(
        subset.median(),
        linewidth=1.5,
        linestyle="--",
        label=(
            f"Mediana = "
            f"{subset.median():.3f} "
            f"°C/década"
        ),
    )


    plt.xlabel(
        "Sen's Slope (°C/década)"
    )


    plt.ylabel(
        "Número de estações"
    )


    plt.title(
        f"Distribuição das tendências - "
        f"{config_var['nome']}\n"
        f"Rede principal "
        f"(>=15 anos válidos)"
    )


    plt.legend()


    plt.grid(
        alpha=0.20
    )


    salvar_figura(
        f"histograma_"
        f"{config_var['arquivo']}_"
        f"principal_15a.png"
    )


# ==========================================================
# 10. MEDIANAS REGIONAIS NA REDE PRINCIPAL
# ==========================================================

ordem_regioes = [
    "Norte",
    "Nordeste",
    "Centro-Oeste",
    "Sudeste",
    "Sul",
]


for variavel, config_var in VARIAVEIS.items():

    subset = (
        principal[
            principal[
                "variavel"
            ]
            ==
            variavel
        ]
        .copy()
    )


    regional = (
        subset
        .groupby(
            "regiao",
            as_index=False,
        )
        .agg(
            sen_mediana_c_decada=(
                "sen_slope_c_decada",
                "median",
            ),

            n_estacoes=(
                "codigo",
                "nunique",
            ),
        )
    )


    regional[
        "regiao"
    ] = pd.Categorical(
        regional[
            "regiao"
        ],
        categories=ordem_regioes,
        ordered=True,
    )


    regional = (
        regional
        .sort_values(
            "regiao"
        )
    )


    plt.figure(
        figsize=(
            10,
            6,
        )
    )


    plt.bar(
        regional[
            "regiao"
        ].astype(str),
        regional[
            "sen_mediana_c_decada"
        ],
    )


    plt.axhline(
        0,
        linewidth=1,
    )


    for indice, linha in regional.reset_index(
        drop=True
    ).iterrows():

        plt.text(
            indice,
            linha[
                "sen_mediana_c_decada"
            ],
            (
                f"n="
                f"{int(linha['n_estacoes'])}"
            ),
            ha="center",
            va=(
                "bottom"
                if linha[
                    "sen_mediana_c_decada"
                ]
                >=
                0
                else
                "top"
            ),
            fontsize=9,
        )


    plt.xlabel(
        "Região"
    )


    plt.ylabel(
        "Mediana de Sen's Slope "
        "(°C/década)"
    )


    plt.title(
        f"Tendência mediana por região - "
        f"{config_var['nome']}\n"
        f"Rede principal "
        f"(>=15 anos válidos)"
    )


    plt.grid(
        axis="y",
        alpha=0.20,
    )


    salvar_figura(
        f"regional_"
        f"{config_var['arquivo']}_"
        f"principal_15a.png"
    )


# ==========================================================
# 11. SALVAR RESUMO
# ==========================================================

pd.DataFrame(
    resumo_figuras
).to_csv(
    SAIDA_RESUMO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 12. LISTAR FIGURAS
# ==========================================================

print("\n" + "=" * 90)
print("FIGURAS GERADAS")
print("=" * 90)


arquivos = sorted(
    SAIDA_DIR.glob(
        "*.png"
    )
)


for arquivo in arquivos:

    print(
        arquivo
    )


print(
    f"\nTotal de figuras: "
    f"{len(arquivos)}"
)


print("\n" + "=" * 90)
print("MAPAS E GRÁFICOS CONCLUÍDOS")
print("=" * 90)
