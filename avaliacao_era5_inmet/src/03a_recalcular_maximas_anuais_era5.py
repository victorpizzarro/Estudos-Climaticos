from calendar import isleap
from copy import deepcopy
from datetime import datetime
import csv

import geopandas as gpd
import numpy as np

from shapely.geometry import Point

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_get_array,
    codes_get_values,
    codes_release,
)

from config import (
    ERA5_GRIB,
    ERA5_COMPLEMENTO_ANOS_DIR,
    IBGE_SHAPEFILE,
    TABLES_DIR,
)


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

ANO_INICIAL = 1995
ANO_FINAL = 2025

KELVIN_CELSIUS = 273.15


TABLES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ARQUIVO_SAIDA = (
    TABLES_DIR
    / "maximas_anuais_era5_completo_1995_2025.csv"
)


# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def montar_datetime(
    validity_date,
    validity_time,
):

    validity_date = int(
        validity_date
    )

    validity_time = int(
        validity_time
    )

    ano = (
        validity_date
        // 10000
    )

    mes = (
        validity_date
        // 100
    ) % 100

    dia = (
        validity_date
        % 100
    )

    hora = (
        validity_time
        // 100
    )

    minuto = (
        validity_time
        % 100
    )

    return datetime(
        ano,
        mes,
        dia,
        hora,
        minuto,
    )


def horas_esperadas(ano):

    return (
        8784
        if isleap(ano)
        else 8760
    )


def resultado_vazio():

    return {
        ano: {
            "max_k": -np.inf,
            "datetime": None,
            "latitude": None,
            "longitude": None,
            "fonte": None,
        }
        for ano in range(
            ANO_INICIAL,
            ANO_FINAL + 1,
        )
    }


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("RECÁLCULO DAS TEMPERATURAS MÁXIMAS ANUAIS - ERA5")
print("=" * 90)

print(
    "\nSerá feita a comparação entre:"
)

print(
    "1. GRIB original (75% da cobertura)"
)

print(
    "2. GRIB original + complementos (100%)"
)


# ==========================================================
# 1. CARREGAR MALHA DO BRASIL
# ==========================================================

print("\n" + "=" * 90)
print("CARREGANDO MALHA DO BRASIL")
print("=" * 90)

print(
    "\nShapefile:"
)

print(
    IBGE_SHAPEFILE
)


if not IBGE_SHAPEFILE.exists():

    raise FileNotFoundError(
        f"Shapefile não encontrado:\n"
        f"{IBGE_SHAPEFILE}"
    )


if IBGE_SHAPEFILE.stat().st_size == 0:

    raise RuntimeError(
        "O shapefile do Brasil possui tamanho zero."
    )


brasil_gdf = gpd.read_file(
    IBGE_SHAPEFILE
)


if brasil_gdf.empty:

    raise RuntimeError(
        "O shapefile foi aberto, "
        "mas não contém geometrias."
    )


print(
    f"\nCRS original: "
    f"{brasil_gdf.crs}"
)


# Garantir latitude/longitude
if brasil_gdf.crs is None:

    raise RuntimeError(
        "O shapefile não possui CRS definido."
    )


brasil_gdf = brasil_gdf.to_crs(
    epsg=4326
)


# GeoPandas moderno
try:

    brasil_geom = (
        brasil_gdf
        .geometry
        .union_all()
    )

except AttributeError:

    brasil_geom = (
        brasil_gdf
        .geometry
        .unary_union
    )


print(
    "Malha do Brasil carregada."
)


# ==========================================================
# 2. CONSTRUIR MÁSCARA DA GRADE ERA5
# ==========================================================

print("\n" + "=" * 90)
print("CONSTRUINDO MÁSCARA ESPACIAL")
print("=" * 90)


latitudes_grade = None
longitudes_grade = None
mascara_brasil = None


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
                "encontrada no GRIB."
            )


        try:

            short_name = codes_get(
                gid,
                "shortName",
            )


            if short_name != "mx2t":
                continue


            latitudes_grade = np.asarray(
                codes_get_array(
                    gid,
                    "latitudes",
                ),
                dtype=float,
            )


            longitudes_grade = np.asarray(
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
    f"\nPontos totais da grade: "
    f"{len(latitudes_grade):,}"
)


print(
    "\nTestando quais centros de célula "
    "estão dentro do território brasileiro..."
)


mascara_brasil = np.zeros(
    len(latitudes_grade),
    dtype=bool,
)


for indice, (
    latitude,
    longitude,
) in enumerate(
    zip(
        latitudes_grade,
        longitudes_grade,
    )
):

    ponto = Point(
        longitude,
        latitude,
    )


    # covers inclui pontos exatamente na fronteira
    if brasil_geom.covers(
        ponto
    ):

        mascara_brasil[
            indice
        ] = True


    if (
        indice > 0
        and indice % 5000 == 0
    ):

        print(
            f"{indice:,} pontos analisados..."
        )


numero_celulas_brasil = int(
    mascara_brasil.sum()
)


print(
    f"\nCélulas ERA5 consideradas "
    f"dentro do Brasil: "
    f"{numero_celulas_brasil:,}"
)


if numero_celulas_brasil == 0:

    raise RuntimeError(
        "Nenhuma célula foi classificada "
        "como pertencente ao Brasil."
    )


# ==========================================================
# 3. FUNÇÃO PARA PROCESSAR UM GRIB
# ==========================================================

def processar_grib(
    caminho,
    origem,
    resultados,
    contagem,
):
    """
    Percorre um GRIB e atualiza as máximas anuais.

    Otimização importante:
    primeiro consulta o máximo global do campo usando
    o ecCodes.

    O vetor completo de 25.921 células só é transferido
    para o Python se esse máximo puder superar o recorde
    anual atual.
    """

    print("\n" + "=" * 90)

    print(
        f"PROCESSANDO: {origem}"
    )

    print("=" * 90)

    print(
        caminho
    )


    mensagens = 0

    campos_decodificados = 0


    with open(
        caminho,
        "rb",
    ) as arquivo:

        while True:

            gid = codes_grib_new_from_file(
                arquivo
            )


            if gid is None:
                break


            try:

                short_name = codes_get(
                    gid,
                    "shortName",
                )


                if short_name != "mx2t":
                    continue


                validity_date = int(
                    codes_get(
                        gid,
                        "validityDate",
                    )
                )


                validity_time = int(
                    codes_get(
                        gid,
                        "validityTime",
                    )
                )


                data_hora = montar_datetime(
                    validity_date,
                    validity_time,
                )


                ano = data_hora.year


                if (
                    ano < ANO_INICIAL
                    or ano > ANO_FINAL
                ):

                    continue


                mensagens += 1


                contagem[
                    ano
                ] += 1


                # ==========================================
                # OTIMIZAÇÃO
                # ==========================================

                try:

                    max_global_k = float(
                        codes_get(
                            gid,
                            "max",
                        )
                    )

                except Exception:

                    max_global_k = np.inf


                # Se nem o máximo da grade inteira supera
                # o recorde brasileiro atual daquele ano,
                # não precisamos trazer 25.921 valores
                # para o Python.

                if (
                    max_global_k
                    <= resultados[ano]["max_k"]
                ):

                    continue


                # ==========================================
                # DECODIFICAR CAMPO
                # ==========================================

                valores = np.asarray(
                    codes_get_values(
                        gid
                    ),
                    dtype=float,
                )


                campos_decodificados += 1


                if (
                    len(valores)
                    != len(mascara_brasil)
                ):

                    raise RuntimeError(
                        "Quantidade de pontos do campo "
                        "não corresponde à grade usada "
                        "na máscara."
                    )


                valores_brasil = valores[
                    mascara_brasil
                ]


                indice_local = int(
                    np.nanargmax(
                        valores_brasil
                    )
                )


                max_brasil_k = float(
                    valores_brasil[
                        indice_local
                    ]
                )


                # ==========================================
                # NOVO RECORDE ANUAL
                # ==========================================

                if (
                    max_brasil_k
                    >
                    resultados[ano]["max_k"]
                ):

                    indices_grade = np.flatnonzero(
                        mascara_brasil
                    )


                    indice_grade = int(
                        indices_grade[
                            indice_local
                        ]
                    )


                    latitude = float(
                        latitudes_grade[
                            indice_grade
                        ]
                    )


                    longitude = float(
                        longitudes_grade[
                            indice_grade
                        ]
                    )


                    resultados[
                        ano
                    ] = {

                        "max_k":
                            max_brasil_k,

                        "datetime":
                            data_hora,

                        "latitude":
                            latitude,

                        "longitude":
                            longitude,

                        "fonte":
                            origem,
                    }


            finally:

                codes_release(
                    gid
                )


            if (
                mensagens > 0
                and mensagens % 25000 == 0
            ):

                print(
                    f"{mensagens:,} mensagens "
                    "processadas..."
                )


    print(
        f"\nMensagens utilizadas: "
        f"{mensagens:,}"
    )


    print(
        f"Campos completamente "
        f"decodificados: "
        f"{campos_decodificados:,}"
    )


# ==========================================================
# 4. PROCESSAR GRIB ORIGINAL
# ==========================================================

resultados = resultado_vazio()


contagem_original = {
    ano: 0
    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    )
}


processar_grib(
    ERA5_GRIB,
    "original",
    resultados,
    contagem_original,
)


# Guardar uma cópia ANTES de adicionar
# as seis horas complementares.
resultados_original = deepcopy(
    resultados
)


# ==========================================================
# 5. PROCESSAR COMPLEMENTOS
# ==========================================================

contagem_complemento = {
    ano: 0
    for ano in range(
        ANO_INICIAL,
        ANO_FINAL + 1,
    )
}


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    arquivo = (
        ERA5_COMPLEMENTO_ANOS_DIR
        / f"mx2t_faltantes_{ano}.grib"
    )


    if not arquivo.exists():

        raise FileNotFoundError(
            f"Complemento ausente:\n"
            f"{arquivo}"
        )


    processar_grib(
        arquivo,
        "complemento",
        resultados,
        contagem_complemento,
    )


# ==========================================================
# 6. VALIDAR CONTAGEM
# ==========================================================

print("\n" + "=" * 90)
print("VALIDANDO COBERTURA")
print("=" * 90)


cobertura_aprovada = True


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    original = (
        contagem_original[
            ano
        ]
    )

    complemento = (
        contagem_complemento[
            ano
        ]
    )

    total = (
        original
        +
        complemento
    )

    esperado = horas_esperadas(
        ano
    )


    status = (
        "OK"
        if total == esperado
        else "ERRO"
    )


    print(
        f"{ano}: "
        f"{original:,} + "
        f"{complemento:,} = "
        f"{total:,} / "
        f"{esperado:,} "
        f"[{status}]"
    )


    if total != esperado:

        cobertura_aprovada = False


if not cobertura_aprovada:

    raise RuntimeError(
        "A cobertura anual não corresponde "
        "ao número esperado de horas."
    )


# ==========================================================
# 7. GERAR TABELA COMPARATIVA
# ==========================================================

print("\n" + "=" * 90)
print("RESULTADOS")
print("=" * 90)


linhas = []

anos_alterados = []


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    antigo = (
        resultados_original[
            ano
        ]
    )

    completo = (
        resultados[
            ano
        ]
    )


    antigo_c = (
        antigo["max_k"]
        -
        KELVIN_CELSIUS
    )


    completo_c = (
        completo["max_k"]
        -
        KELVIN_CELSIUS
    )


    diferenca = (
        completo_c
        -
        antigo_c
    )


    mudou = (
        abs(diferenca)
        >
        0.000001
    )


    if mudou:

        anos_alterados.append(
            ano
        )


    registro = {

        "ano":
            ano,

        "maxima_original_c":
            round(
                antigo_c,
                4,
            ),

        "data_hora_original_utc":
            antigo["datetime"].strftime(
                "%Y-%m-%d %H:%M"
            ),

        "latitude_original":
            antigo["latitude"],

        "longitude_original":
            antigo["longitude"],

        "maxima_completa_c":
            round(
                completo_c,
                4,
            ),

        "data_hora_completa_utc":
            completo["datetime"].strftime(
                "%Y-%m-%d %H:%M"
            ),

        "latitude_completa":
            completo["latitude"],

        "longitude_completa":
            completo["longitude"],

        "fonte_maxima":
            completo["fonte"],

        "diferenca_c":
            round(
                diferenca,
                4,
            ),

        "maxima_alterada":
            mudou,

        "registros_original":
            contagem_original[
                ano
            ],

        "registros_complemento":
            contagem_complemento[
                ano
            ],

        "registros_total":
            (
                contagem_original[
                    ano
                ]
                +
                contagem_complemento[
                    ano
                ]
            ),
    }


    linhas.append(
        registro
    )


    indicador = (
        "ALTEROU"
        if mudou
        else ""
    )


    print(
        f"{ano} | "
        f"antiga: "
        f"{antigo_c:6.2f} °C | "
        f"completa: "
        f"{completo_c:6.2f} °C | "
        f"Δ {diferenca:+.2f} °C | "
        f"{completo['fonte']:<11} "
        f"{indicador}"
    )


# ==========================================================
# 8. SALVAR CSV
# ==========================================================

with open(
    ARQUIVO_SAIDA,
    "w",
    newline="",
    encoding="utf-8",
) as arquivo:

    campos = list(
        linhas[0].keys()
    )


    writer = csv.DictWriter(
        arquivo,
        fieldnames=campos,
    )


    writer.writeheader()

    writer.writerows(
        linhas
    )


# ==========================================================
# 9. RESUMO
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO")
print("=" * 90)


print(
    f"\nAnos analisados: "
    f"{len(linhas)}"
)


print(
    f"Anos cuja máxima mudou: "
    f"{len(anos_alterados)}"
)


if anos_alterados:

    print(
        "\nAnos alterados:"
    )

    print(
        anos_alterados
    )

else:

    print(
        "\nNenhum máximo anual foi "
        "alterado pelos complementos."
    )


# ==========================================================
# MAIOR VALOR DA SÉRIE COMPLETA
# ==========================================================

maior = max(
    linhas,
    key=lambda linha:
        linha["maxima_completa_c"],
)


print("\nMaior valor 1995-2025:")

print(
    f"{maior['maxima_completa_c']:.4f} °C"
)

print(
    f"Ano: "
    f"{maior['ano']}"
)

print(
    f"Data/hora UTC: "
    f"{maior['data_hora_completa_utc']}"
)

print(
    f"Latitude: "
    f"{maior['latitude_completa']}"
)

print(
    f"Longitude: "
    f"{maior['longitude_completa']}"
)

print(
    f"Fonte: "
    f"{maior['fonte_maxima']}"
)


print(
    "\nTabela salva em:"
)

print(
    ARQUIVO_SAIDA
)


print("\n" + "=" * 90)
print("RECÁLCULO CONCLUÍDO")
print("=" * 90)