from pathlib import Path

import numpy as np
import pandas as pd

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_get_array,
    codes_release,
)

from config import (
    PROJECT_DIR,
    ERA5_GRIB,
    TABLES_DIR,
)


# ==========================================================
# CAMINHOS
# ==========================================================

STATIONS_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "stations"
)


MATCHES_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "matches"
)


MATCHES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ARQUIVO_ELEGIBILIDADE = (
    STATIONS_DIR
    / "estacoes_inmet_ano_elegibilidade.csv"
)


ARQUIVO_SAIDA = (
    MATCHES_DIR
    / "inmet_era5_estacao_ano.csv"
)


ARQUIVO_CELULAS = (
    MATCHES_DIR
    / "celulas_era5_com_estacoes_inmet.csv"
)


ARQUIVO_RESUMO = (
    TABLES_DIR
    / "resumo_pareamento_espacial_inmet_era5.csv"
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

# Não é critério automático de exclusão.
# Serve apenas para nos avisar caso alguma estação
# esteja inesperadamente distante do centro da célula.

DISTANCIA_ALERTA_KM = 25.0


# ==========================================================
# HAVERSINE
# ==========================================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2,
):

    raio_terra = 6371.0088

    lat1 = np.radians(
        lat1
    )

    lon1 = np.radians(
        lon1
    )

    lat2 = np.radians(
        lat2
    )

    lon2 = np.radians(
        lon2
    )


    dlat = (
        lat2
        -
        lat1
    )

    dlon = (
        lon2
        -
        lon1
    )


    a = (
        np.sin(
            dlat / 2
        ) ** 2
        +
        np.cos(
            lat1
        )
        *
        np.cos(
            lat2
        )
        *
        np.sin(
            dlon / 2
        ) ** 2
    )


    c = (
        2
        *
        np.arctan2(
            np.sqrt(a),
            np.sqrt(1 - a),
        )
    )


    return (
        raio_terra
        *
        c
    )


# ==========================================================
# LER GRADE ERA5
# ==========================================================

def ler_grade_era5():

    print("\n" + "=" * 90)
    print("LENDO GRADE ERA5")
    print("=" * 90)


    with open(
        ERA5_GRIB,
        "rb",
    ) as arquivo:

        while True:

            gid = codes_grib_new_from_file(
                arquivo
            )


            if gid is None:

                raise RuntimeError(
                    "Nenhuma mensagem mx2t "
                    "encontrada no GRIB ERA5."
                )


            try:

                short_name = codes_get(
                    gid,
                    "shortName",
                )


                if short_name != "mx2t":

                    continue


                nx = int(
                    codes_get(
                        gid,
                        "Nx",
                    )
                )


                ny = int(
                    codes_get(
                        gid,
                        "Ny",
                    )
                )


                latitudes = np.asarray(
                    codes_get_array(
                        gid,
                        "latitudes",
                    ),
                    dtype=float,
                )


                longitudes = np.asarray(
                    codes_get_array(
                        gid,
                        "longitudes",
                    ),
                    dtype=float,
                )


                break


            finally:

                codes_release(
                    gid
                )


    print(
        f"\nNx: {nx}"
    )

    print(
        f"Ny: {ny}"
    )

    print(
        f"Pontos: "
        f"{len(latitudes):,}"
    )


    if (
        len(latitudes)
        != nx * ny
    ):

        raise RuntimeError(
            "Quantidade de latitudes não corresponde "
            "a Nx × Ny."
        )


    if (
        len(longitudes)
        != nx * ny
    ):

        raise RuntimeError(
            "Quantidade de longitudes não corresponde "
            "a Nx × Ny."
        )


    # ======================================================
    # VALORES ÚNICOS
    # ======================================================

    latitudes_unicas = np.unique(
        latitudes
    )


    longitudes_unicas = np.unique(
        longitudes
    )


    print(
        f"\nLatitudes únicas: "
        f"{len(latitudes_unicas)}"
    )

    print(
        f"Longitudes únicas: "
        f"{len(longitudes_unicas)}"
    )


    print(
        f"\nLatitude mínima: "
        f"{latitudes.min():.2f}"
    )

    print(
        f"Latitude máxima: "
        f"{latitudes.max():.2f}"
    )

    print(
        f"Longitude mínima: "
        f"{longitudes.min():.2f}"
    )

    print(
        f"Longitude máxima: "
        f"{longitudes.max():.2f}"
    )


    # ======================================================
    # MAPA COORDENADA → ÍNDICE FLAT
    # ======================================================

    mapa_indice = {}


    for indice, (
        latitude,
        longitude,
    ) in enumerate(
        zip(
            latitudes,
            longitudes,
        )
    ):

        chave = (
            round(
                float(latitude),
                6,
            ),
            round(
                float(longitude),
                6,
            ),
        )


        mapa_indice[
            chave
        ] = indice


    return (
        latitudes,
        longitudes,
        latitudes_unicas,
        longitudes_unicas,
        mapa_indice,
        nx,
        ny,
    )


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("PAREAMENTO ESPACIAL INMET × ERA5")
print("=" * 90)


# ==========================================================
# 1. CARREGAR ESTAÇÕES ELEGÍVEIS
# ==========================================================

if not ARQUIVO_ELEGIBILIDADE.exists():

    raise FileNotFoundError(
        f"Arquivo não encontrado:\n"
        f"{ARQUIVO_ELEGIBILIDADE}"
    )


estacoes = pd.read_csv(
    ARQUIVO_ELEGIBILIDADE
)


print(
    f"\nRegistros estação-ano carregados: "
    f"{len(estacoes):,}"
)


# ==========================================================
# NORMALIZAR BOOLEANO
# ==========================================================

if (
    estacoes[
        "elegivel_pareamento"
    ].dtype
    != bool
):

    estacoes[
        "elegivel_pareamento"
    ] = (
        estacoes[
            "elegivel_pareamento"
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


elegiveis = (
    estacoes[
        estacoes[
            "elegivel_pareamento"
        ]
        ==
        True
    ]
    .copy()
)


print(
    f"Elegíveis: "
    f"{len(elegiveis):,}"
)


# ==========================================================
# CONVERTER COORDENADAS
# ==========================================================

for coluna in [
    "latitude",
    "longitude",
]:

    elegiveis[
        coluna
    ] = pd.to_numeric(
        elegiveis[
            coluna
        ],
        errors="coerce",
    )


if (
    elegiveis[
        [
            "latitude",
            "longitude",
        ]
    ]
    .isna()
    .any()
    .any()
):

    raise RuntimeError(
        "Há estação elegível com "
        "latitude/longitude ausente."
    )


# ==========================================================
# 2. LER GRADE
# ==========================================================

(
    latitudes_grade,
    longitudes_grade,
    latitudes_unicas,
    longitudes_unicas,
    mapa_indice,
    nx,
    ny,
) = ler_grade_era5()


# ==========================================================
# 3. ASSOCIAR ESTAÇÃO → CÉLULA
# ==========================================================

print("\n" + "=" * 90)
print("ASSOCIANDO ESTAÇÕES À GRADE")
print("=" * 90)


resultados = []


for numero, (_, linha) in enumerate(
    elegiveis.iterrows(),
    start=1,
):

    lat_estacao = float(
        linha[
            "latitude"
        ]
    )


    lon_estacao = float(
        linha[
            "longitude"
        ]
    )


    # ======================================================
    # LATITUDE MAIS PRÓXIMA
    # ======================================================

    indice_lat = int(
        np.argmin(
            np.abs(
                latitudes_unicas
                -
                lat_estacao
            )
        )
    )


    lat_era5 = float(
        latitudes_unicas[
            indice_lat
        ]
    )


    # ======================================================
    # LONGITUDE MAIS PRÓXIMA
    # ======================================================

    indice_lon = int(
        np.argmin(
            np.abs(
                longitudes_unicas
                -
                lon_estacao
            )
        )
    )


    lon_era5 = float(
        longitudes_unicas[
            indice_lon
        ]
    )


    # ======================================================
    # ÍNDICE FLAT REAL DO GRIB
    # ======================================================

    chave = (
        round(
            lat_era5,
            6,
        ),
        round(
            lon_era5,
            6,
        ),
    )


    if chave not in mapa_indice:

        raise RuntimeError(
            "Célula calculada não encontrada "
            "na grade ERA5:\n"
            f"{chave}"
        )


    grid_index = int(
        mapa_indice[
            chave
        ]
    )


    # Conferência adicional.
    lat_check = float(
        latitudes_grade[
            grid_index
        ]
    )


    lon_check = float(
        longitudes_grade[
            grid_index
        ]
    )


    if (
        not np.isclose(
            lat_check,
            lat_era5,
        )
        or
        not np.isclose(
            lon_check,
            lon_era5,
        )
    ):

        raise RuntimeError(
            "Falha na validação do índice ERA5."
        )


    # ======================================================
    # DISTÂNCIA
    # ======================================================

    distancia = float(
        haversine_km(
            lat_estacao,
            lon_estacao,
            lat_era5,
            lon_era5,
        )
    )


    alerta_distancia = bool(
        distancia
        >
        DISTANCIA_ALERTA_KM
    )


    resultados.append(
        {
            "ano":
                int(
                    linha[
                        "ano"
                    ]
                ),

            "codigo":
                linha[
                    "codigo"
                ],

            "estacao":
                linha[
                    "estacao"
                ],

            "uf":
                linha[
                    "uf"
                ],

            "regiao":
                linha[
                    "regiao"
                ],

            "latitude_inmet":
                lat_estacao,

            "longitude_inmet":
                lon_estacao,

            "altitude_inmet_m":
                linha[
                    "altitude_m"
                ],

            "latitude_era5":
                lat_era5,

            "longitude_era5":
                lon_era5,

            "grid_index":
                grid_index,

            "distancia_centro_km":
                distancia,

            "alerta_distancia":
                alerta_distancia,

            "observacoes_inmet":
                linha[
                    "observacoes"
                ],

            "cobertura_temp":
                linha[
                    "cobertura_temp"
                ],
        }
    )


    if (
        numero % 1000 == 0
        or
        numero == len(
            elegiveis
        )
    ):

        print(
            f"{numero:,} / "
            f"{len(elegiveis):,} "
            "registros associados"
        )


# ==========================================================
# 4. DATAFRAME FINAL
# ==========================================================

matches = pd.DataFrame(
    resultados
)


matches = matches.sort_values(
    [
        "ano",
        "codigo",
    ]
).reset_index(
    drop=True
)


# ==========================================================
# 5. VALIDAÇÕES
# ==========================================================

print("\n" + "=" * 90)
print("VALIDAÇÃO DO PAREAMENTO")
print("=" * 90)


duplicados = int(
    matches
    .duplicated(
        subset=[
            "ano",
            "codigo",
        ]
    )
    .sum()
)


indices_invalidos = int(
    (
        (
            matches[
                "grid_index"
            ]
            < 0
        )
        |
        (
            matches[
                "grid_index"
            ]
            >= nx * ny
        )
    )
    .sum()
)


distancia_min = float(
    matches[
        "distancia_centro_km"
    ].min()
)


distancia_media = float(
    matches[
        "distancia_centro_km"
    ].mean()
)


distancia_mediana = float(
    matches[
        "distancia_centro_km"
    ].median()
)


distancia_p95 = float(
    matches[
        "distancia_centro_km"
    ].quantile(
        0.95
    )
)


distancia_max = float(
    matches[
        "distancia_centro_km"
    ].max()
)


alertas = int(
    matches[
        "alerta_distancia"
    ].sum()
)


celulas_unicas = int(
    matches[
        "grid_index"
    ].nunique()
)


estacoes_unicas = int(
    matches[
        "codigo"
    ].nunique()
)


print(
    f"\nRegistros pareados: "
    f"{len(matches):,}"
)


print(
    f"Estações únicas: "
    f"{estacoes_unicas:,}"
)


print(
    f"Células ERA5 únicas utilizadas: "
    f"{celulas_unicas:,}"
)


print(
    f"\nDuplicados estação-ano: "
    f"{duplicados:,}"
)


print(
    f"Índices ERA5 inválidos: "
    f"{indices_invalidos:,}"
)


print(
    "\nDistância estação → centro ERA5:"
)


print(
    f"  mínima: "
    f"{distancia_min:.3f} km"
)


print(
    f"  média: "
    f"{distancia_media:.3f} km"
)


print(
    f"  mediana: "
    f"{distancia_mediana:.3f} km"
)


print(
    f"  p95: "
    f"{distancia_p95:.3f} km"
)


print(
    f"  máxima: "
    f"{distancia_max:.3f} km"
)


print(
    f"\nAcima de "
    f"{DISTANCIA_ALERTA_KM:.0f} km: "
    f"{alertas:,}"
)


# ==========================================================
# 6. VERIFICAR ESTAÇÕES QUE MUDARAM DE CÉLULA
# ==========================================================

celulas_por_estacao = (
    matches
    .groupby(
        "codigo"
    )[
        "grid_index"
    ]
    .nunique()
)


mudaram_celula = (
    celulas_por_estacao
    [
        celulas_por_estacao
        >
        1
    ]
)


print(
    f"\nEstações que utilizaram "
    f"mais de uma célula ERA5 "
    f"ao longo dos anos: "
    f"{len(mudaram_celula):,}"
)


if len(
    mudaram_celula
) > 0:

    print(
        "\nMaiores quantidades de células "
        "por estação:"
    )


    print(
        mudaram_celula
        .sort_values(
            ascending=False
        )
        .head(20)
        .to_string()
    )


# ==========================================================
# 7. TABELA DE CÉLULAS UTILIZADAS
# ==========================================================

celulas = (
    matches[
        [
            "grid_index",
            "latitude_era5",
            "longitude_era5",
        ]
    ]
    .drop_duplicates()
    .sort_values(
        "grid_index"
    )
    .reset_index(
        drop=True
    )
)


# Número de registros estação-ano por célula
contagem_estacao_ano = (
    matches
    .groupby(
        "grid_index"
    )
    .size()
    .rename(
        "registros_estacao_ano"
    )
)


# Número de códigos distintos que passaram
# pela célula em algum momento
contagem_estacoes = (
    matches
    .groupby(
        "grid_index"
    )[
        "codigo"
    ]
    .nunique()
    .rename(
        "estacoes_unicas"
    )
)


celulas = (
    celulas
    .merge(
        contagem_estacao_ano,
        on="grid_index",
        how="left",
    )
    .merge(
        contagem_estacoes,
        on="grid_index",
        how="left",
    )
)


# ==========================================================
# 8. SALVAR
# ==========================================================

matches.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    encoding="utf-8",
)


celulas.to_csv(
    ARQUIVO_CELULAS,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 9. RESUMO EM CSV
# ==========================================================

resumo = pd.DataFrame(
    [
        {
            "registros_estacao_ano":
                len(matches),

            "estacoes_unicas":
                estacoes_unicas,

            "celulas_era5_unicas":
                celulas_unicas,

            "duplicados_estacao_ano":
                duplicados,

            "indices_invalidos":
                indices_invalidos,

            "distancia_min_km":
                distancia_min,

            "distancia_media_km":
                distancia_media,

            "distancia_mediana_km":
                distancia_mediana,

            "distancia_p95_km":
                distancia_p95,

            "distancia_max_km":
                distancia_max,

            "alertas_distancia":
                alertas,

            "estacoes_multiplas_celulas":
                len(
                    mudaram_celula
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
# 10. RESULTADO
# ==========================================================

aprovado = (
    len(matches)
    ==
    len(elegiveis)
    and
    duplicados
    ==
    0
    and
    indices_invalidos
    ==
    0
)


print("\n" + "=" * 90)


if aprovado:

    print(
        "RESULTADO: PAREAMENTO ESPACIAL APROVADO"
    )

else:

    print(
        "RESULTADO: PAREAMENTO ESPACIAL "
        "REQUER INVESTIGAÇÃO"
    )


print(
    "\nTabela estação-ano × ERA5:"
)

print(
    ARQUIVO_SAIDA
)


print(
    "\nCélulas ERA5 utilizadas:"
)

print(
    ARQUIVO_CELULAS
)


print(
    "\nResumo:"
)

print(
    ARQUIVO_RESUMO
)


print("\n" + "=" * 90)
print("PROCESSAMENTO CONCLUÍDO")
print("=" * 90)