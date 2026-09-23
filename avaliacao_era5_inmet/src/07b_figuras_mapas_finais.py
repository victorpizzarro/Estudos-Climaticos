from pathlib import Path
import shutil
import urllib.request
import zipfile

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

from config import (
    PROJECT_DIR,
    TABLES_DIR,
    FIGURES_DIR,
    IBGE_SHAPEFILE,
)


# ==========================================================
# OBJETIVO
# ==========================================================
#
# Gerar as figuras finais do bloco de consolidação.
#
# Requisito cartográfico:
# - contorno nacional;
# - limites estaduais;
# - estações sobrepostas.
#
# A malha estadual 2024 é baixada automaticamente do
# repositório oficial do IBGE caso ainda não exista.
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


ARQUIVO_TENDENCIAS = (
    ANNUAL_DIR
    / "tendencias_extremos_estacoes.parquet"
)


ARQUIVO_COORDENADAS = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "matches"
    / "inmet_era5_estacao_ano.csv"
)


ARQUIVO_VALIDACAO_FINAL = (
    TABLES_DIR
    / "final_resumo_validacao_era5_inmet.csv"
)


SHAPES_DIR = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "shapes"
)


UF_DIR = (
    SHAPES_DIR
    / "BR_UF_2024"
)


UF_ZIP = (
    SHAPES_DIR
    / "BR_UF_2024.zip"
)


UF_SHP = (
    UF_DIR
    / "BR_UF_2024.shp"
)


URL_UF_IBGE = (
    "https://geoftp.ibge.gov.br/"
    "organizacao_do_territorio/"
    "malhas_territoriais/"
    "malhas_municipais/"
    "municipio_2024/"
    "Brasil/"
    "BR_UF_2024.zip"
)


SAIDA_DIR = (
    FIGURES_DIR
    / "finais"
)


SAIDA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

REDES = {
    "principal_15a":
        "Rede principal: >=15 anos válidos",

    "sensibilidade_10a":
        "Rede de sensibilidade: >=10 anos válidos",
}


VARIAVEIS = {
    "tmax_inmet":
        "Tmax anual INMET",

    "tmax_era5":
        "Tmax anual ERA5",

    "delta_tmax":
        "Diferença anual ERA5 - INMET",
}


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
        dpi=300,
        bbox_inches="tight",
    )


    plt.close()


    print(
        f"Salvo: {caminho}"
    )


def baixar_malha_ufs():

    if UF_SHP.exists():

        print(
            f"Malha estadual encontrada: "
            f"{UF_SHP}"
        )

        return


    print(
        "\nMalha estadual não encontrada."
    )


    print(
        "Baixando BR_UF_2024.zip do IBGE..."
    )


    SHAPES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    urllib.request.urlretrieve(
        URL_UF_IBGE,
        UF_ZIP,
    )


    if UF_DIR.exists():

        shutil.rmtree(
            UF_DIR
        )


    UF_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    with zipfile.ZipFile(
        UF_ZIP,
        "r",
    ) as arquivo_zip:

        arquivo_zip.extractall(
            UF_DIR
        )


    if not UF_SHP.exists():

        candidatos = list(
            UF_DIR.rglob(
                "*.shp"
            )
        )


        if len(
            candidatos
        ) == 1:

            candidato = candidatos[0]


            for extensao in [
                ".shp",
                ".shx",
                ".dbf",
                ".prj",
                ".cpg",
            ]:

                origem = (
                    candidato
                    .with_suffix(
                        extensao
                    )
                )


                if origem.exists():

                    destino = (
                        UF_DIR
                        /
                        (
                            "BR_UF_2024"
                            +
                            extensao
                        )
                    )


                    if origem != destino:

                        shutil.copy2(
                            origem,
                            destino,
                        )


    if not UF_SHP.exists():

        raise RuntimeError(
            "O ZIP do IBGE foi baixado, "
            "mas BR_UF_2024.shp não foi localizado."
        )


    print(
        f"Malha estadual pronta: "
        f"{UF_SHP}"
    )


def primeira_coluna(
    colunas,
    candidatos,
):

    for coluna in candidatos:

        if coluna in colunas:

            return coluna


    return None


def carregar_coordenadas():

    if not ARQUIVO_COORDENADAS.exists():

        raise FileNotFoundError(
            f"Arquivo de associação espacial não encontrado:\n"
            f"{ARQUIVO_COORDENADAS}"
        )


    df = pd.read_csv(
        ARQUIVO_COORDENADAS
    )


    codigo = primeira_coluna(
        df.columns,
        [
            "codigo",
            "codigo_estacao",
            "cod_estacao",
        ],
    )


    latitude = primeira_coluna(
        df.columns,
        [
            "latitude_inmet",
            "latitude",
            "latitude_estacao",
            "lat_estacao",
            "lat",
        ],
    )


    longitude = primeira_coluna(
        df.columns,
        [
            "longitude_inmet",
            "longitude",
            "longitude_estacao",
            "lon_estacao",
            "lon",
        ],
    )


    if (
        codigo is None
        or
        latitude is None
        or
        longitude is None
    ):

        raise RuntimeError(
            "Não consegui identificar as colunas de "
            "código/latitude/longitude em "
            f"{ARQUIVO_COORDENADAS.name}.\n"
            f"Colunas disponíveis: {list(df.columns)}"
        )


    print(
        f"Colunas de coordenadas usadas: "
        f"{latitude}, {longitude}"
    )


    coords = (
        df[
            [
                codigo,
                latitude,
                longitude,
            ]
        ]
        .rename(
            columns={
                codigo:
                    "codigo",

                latitude:
                    "latitude",

                longitude:
                    "longitude",
            }
        )
        .copy()
    )


    coords[
        "codigo"
    ] = (
        coords[
            "codigo"
        ]
        .astype(str)
        .str.strip()
    )


    coords[
        "latitude"
    ] = pd.to_numeric(
        coords[
            "latitude"
        ],
        errors="coerce",
    )


    coords[
        "longitude"
    ] = pd.to_numeric(
        coords[
            "longitude"
        ],
        errors="coerce",
    )


    coords = (
        coords
        .dropna(
            subset=[
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
                "median",
            ),

            longitude=(
                "longitude",
                "median",
            ),
        )
    )


    return coords


def preparar_mapa(
    ax,
    brasil,
    ufs,
):

    # Linhas estaduais
    ufs.boundary.plot(
        ax=ax,
        linewidth=0.45,
    )


    # Contorno nacional mais espesso
    brasil.boundary.plot(
        ax=ax,
        linewidth=1.0,
    )


    limites = ufs.total_bounds


    margem_x = (
        limites[2]
        -
        limites[0]
    ) * 0.025


    margem_y = (
        limites[3]
        -
        limites[1]
    ) * 0.025


    ax.set_xlim(
        limites[0] - margem_x,
        limites[2] + margem_x,
    )


    ax.set_ylim(
        limites[1] - margem_y,
        limites[3] + margem_y,
    )


    ax.set_xlabel(
        "Longitude"
    )


    ax.set_ylabel(
        "Latitude"
    )


    ax.grid(
        alpha=0.15,
    )


# ==========================================================
# INÍCIO
# ==========================================================

print("=" * 90)
print("FIGURAS FINAIS DA AVALIAÇÃO ERA5 × INMET")
print("=" * 90)


if not ARQUIVO_TENDENCIAS.exists():

    raise FileNotFoundError(
        f"Arquivo não encontrado:\n"
        f"{ARQUIVO_TENDENCIAS}"
    )


if not IBGE_SHAPEFILE.exists():

    raise FileNotFoundError(
        f"Malha nacional não encontrada:\n"
        f"{IBGE_SHAPEFILE}"
    )


baixar_malha_ufs()


# ==========================================================
# 1. MALHAS
# ==========================================================

brasil = gpd.read_file(
    IBGE_SHAPEFILE
)


ufs = gpd.read_file(
    UF_SHP
)


if brasil.crs is None:

    raise RuntimeError(
        "Malha do Brasil sem CRS."
    )


if ufs.crs is None:

    raise RuntimeError(
        "Malha das UFs sem CRS."
    )


brasil = brasil.to_crs(
    "EPSG:4326"
)


ufs = ufs.to_crs(
    "EPSG:4326"
)


print(
    f"\nUFs carregadas: "
    f"{len(ufs)}"
)


# ==========================================================
# 2. TENDÊNCIAS + COORDENADAS
# ==========================================================

tendencias = pd.read_parquet(
    ARQUIVO_TENDENCIAS
)


coords = carregar_coordenadas()


tendencias[
    "codigo"
] = (
    tendencias[
        "codigo"
    ]
    .astype(str)
    .str.strip()
)


tendencias = tendencias.merge(
    coords,
    on="codigo",
    how="left",
    validate="many_to_one",
)


sem_coords = (
    tendencias[
        tendencias[
            "latitude"
        ]
        .isna()
        |
        tendencias[
            "longitude"
        ]
        .isna()
    ][
        "codigo"
    ]
    .drop_duplicates()
    .tolist()
)


if sem_coords:

    raise RuntimeError(
        "Estações das tendências sem coordenadas: "
        f"{sem_coords}"
    )


# ==========================================================
# 3. VALIDAR REDES
# ==========================================================

esperados = {
    "principal_15a":
        45,

    "sensibilidade_10a":
        214,
}


for rede, esperado in esperados.items():

    n = (
        tendencias.loc[
            tendencias[
                "rede"
            ]
            ==
            rede,
            "codigo",
        ]
        .nunique()
    )


    print(
        f"{rede}: "
        f"{n} estações"
    )


    if n != esperado:

        raise RuntimeError(
            f"{rede}: esperado {esperado}, "
            f"encontrado {n}."
        )


# ==========================================================
# 4. MAPAS DE SEN'S SLOPE
# ==========================================================

for rede, nome_rede in REDES.items():

    for variavel, nome_variavel in VARIAVEIS.items():

        subset = (
            tendencias[
                (
                    tendencias[
                        "rede"
                    ]
                    ==
                    rede
                )
                &
                (
                    tendencias[
                        "variavel"
                    ]
                    ==
                    variavel
                )
            ]
            .copy()
        )


        valores = (
            subset[
                "sen_slope_c_decada"
            ]
            .astype(float)
            .to_numpy()
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


        norm = TwoSlopeNorm(
            vmin=-limite,
            vcenter=0,
            vmax=limite,
        )


        fig, ax = plt.subplots(
            figsize=(
                9,
                9,
            )
        )


        preparar_mapa(
            ax,
            brasil,
            ufs,
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
            norm=norm,
            s=(
                48
                if rede
                ==
                "principal_15a"
                else
                24
            ),
            alpha=0.88,
        )


        barra = fig.colorbar(
            pontos,
            ax=ax,
            shrink=0.78,
            pad=0.02,
        )


        barra.set_label(
            "Sen's Slope (°C/década)"
        )


        ax.set_title(
            f"{nome_variavel}\n"
            f"{nome_rede} | "
            f"n={subset['codigo'].nunique()}"
        )


        salvar(
            f"mapa_sen_"
            f"{variavel}_"
            f"{rede}.png"
        )


# ==========================================================
# 5. MAPAS DE CONCORDÂNCIA DE SINAL
# ==========================================================

for rede, nome_rede in REDES.items():

    subset = (
        tendencias[
            (
                tendencias[
                    "rede"
                ]
                ==
                rede
            )
            &
            (
                tendencias[
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
                "estacao",
                "uf",
                "latitude",
                "longitude",
                "variavel",
                "sen_slope_c_decada",
            ]
        ]
        .copy()
    )


    pivot = (
        subset
        .pivot_table(
            index=[
                "codigo",
                "estacao",
                "uf",
                "latitude",
                "longitude",
            ],
            columns="variavel",
            values="sen_slope_c_decada",
            aggfunc="first",
        )
        .reset_index()
        .dropna(
            subset=[
                "tmax_inmet",
                "tmax_era5",
            ]
        )
    )


    pivot[
        "mesmo_sinal"
    ] = (
        np.sign(
            pivot[
                "tmax_inmet"
            ]
        )
        ==
        np.sign(
            pivot[
                "tmax_era5"
            ]
        )
    )


    fig, ax = plt.subplots(
        figsize=(
            9,
            9,
        )
    )


    preparar_mapa(
        ax,
        brasil,
        ufs,
    )


    iguais = (
        pivot[
            pivot[
                "mesmo_sinal"
            ]
        ]
    )


    diferentes = (
        pivot[
            ~pivot[
                "mesmo_sinal"
            ]
        ]
    )


    ax.scatter(
        iguais[
            "longitude"
        ],
        iguais[
            "latitude"
        ],
        marker="o",
        s=(
            46
            if rede
            ==
            "principal_15a"
            else
            24
        ),
        alpha=0.85,
        label="Mesmo sinal INMET/ERA5",
    )


    ax.scatter(
        diferentes[
            "longitude"
        ],
        diferentes[
            "latitude"
        ],
        marker="x",
        s=(
            62
            if rede
            ==
            "principal_15a"
            else
            34
        ),
        label="Sinais opostos",
    )


    percentual_igual = (
        pivot[
            "mesmo_sinal"
        ]
        .mean()
        *
        100
    )


    ax.set_title(
        "Concordância do sinal da tendência anual\n"
        f"{nome_rede} | "
        f"{percentual_igual:.1f}% com mesmo sinal"
    )


    ax.legend()


    salvar(
        f"mapa_concordancia_"
        f"{rede}.png"
    )


# ==========================================================
# 6. SCATTER SEN INMET × ERA5
# ==========================================================

for rede, nome_rede in REDES.items():

    subset = (
        tendencias[
            (
                tendencias[
                    "rede"
                ]
                ==
                rede
            )
            &
            (
                tendencias[
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


    x = subset[
        "tmax_inmet"
    ]


    y = subset[
        "tmax_era5"
    ]


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


    inicio = (
        minimo
        -
        margem
    )


    fim = (
        maximo
        +
        margem
    )


    mesmo_sinal = (
        np.sign(
            x
        )
        ==
        np.sign(
            y
        )
    )


    correlacao = float(
        x.corr(
            y
        )
    )


    mae_slopes = float(
        (
            y
            -
            x
        )
        .abs()
        .mean()
    )


    fig, ax = plt.subplots(
        figsize=(
            7.5,
            7.5,
        )
    )


    ax.scatter(
        x,
        y,
        s=42,
        alpha=0.80,
    )


    ax.plot(
        [
            inicio,
            fim,
        ],
        [
            inicio,
            fim,
        ],
        linewidth=1,
        label="Linha 1:1",
    )


    ax.axhline(
        0,
        linewidth=0.8,
    )


    ax.axvline(
        0,
        linewidth=0.8,
    )


    ax.set_xlim(
        inicio,
        fim,
    )


    ax.set_ylim(
        inicio,
        fim,
    )


    ax.set_xlabel(
        "Sen's Slope INMET (°C/década)"
    )


    ax.set_ylabel(
        "Sen's Slope ERA5 (°C/década)"
    )


    ax.set_title(
        "Tendências das máximas anuais\n"
        f"{nome_rede}"
    )


    ax.text(
        0.03,
        0.97,
        (
            f"n = {len(subset)}\n"
            f"r entre slopes = {correlacao:.3f}\n"
            f"MAE entre slopes = {mae_slopes:.3f} °C/década\n"
            f"mesmo sinal = {mesmo_sinal.mean() * 100:.1f}%"
        ),
        transform=ax.transAxes,
        va="top",
    )


    ax.grid(
        alpha=0.15,
    )


    ax.legend()


    salvar(
        f"scatter_sen_inmet_era5_"
        f"{rede}.png"
    )


# ==========================================================
# 7. FIGURA FINAL DAS MÉTRICAS REGIONAIS
# ==========================================================

if ARQUIVO_VALIDACAO_FINAL.exists():

    validacao = pd.read_csv(
        ARQUIVO_VALIDACAO_FINAL
    )


    regional = (
        validacao[
            (
                validacao[
                    "escala"
                ]
                ==
                "Anual - todos os pares"
            )
            &
            (
                validacao[
                    "area"
                ]
                !=
                "Brasil"
            )
        ]
        .copy()
    )


    ordem = [
        "Norte",
        "Nordeste",
        "Centro-Oeste",
        "Sudeste",
        "Sul",
    ]


    regional[
        "area"
    ] = pd.Categorical(
        regional[
            "area"
        ],
        categories=ordem,
        ordered=True,
    )


    regional = regional.sort_values(
        "area"
    )


    fig, ax = plt.subplots(
        figsize=(
            9,
            5.5,
        )
    )


    ax.bar(
        regional[
            "area"
        ].astype(str),
        regional[
            "rmse_c"
        ],
    )


    ax.set_ylabel(
        "RMSE mediano anual (°C)"
    )


    ax.set_xlabel(
        "Região"
    )


    ax.set_title(
        "Desempenho regional ERA5 × INMET"
    )


    ax.grid(
        axis="y",
        alpha=0.15,
    )


    salvar(
        "rmse_regional_final.png"
    )


# ==========================================================
# 8. LISTA FINAL
# ==========================================================

arquivos = sorted(
    SAIDA_DIR.glob(
        "*.png"
    )
)


print("\n" + "=" * 90)
print("FIGURAS GERADAS")
print("=" * 90)


for arquivo in arquivos:

    print(
        arquivo
    )


print(
    f"\nTotal: "
    f"{len(arquivos)} figuras"
)


print("\n" + "=" * 90)
print("BLOCO DE FIGURAS FINAIS CONCLUÍDO")
print("=" * 90)
