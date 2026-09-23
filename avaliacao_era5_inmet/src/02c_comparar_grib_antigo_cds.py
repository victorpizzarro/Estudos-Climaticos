from pathlib import Path

import cdsapi
import numpy as np
import xarray as xr

from config import (
    ERA5_GRIB,
    ERA5_COMPLEMENTO_DIR,
    ERA5_INTERIM_DIR,
)


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

DATA_TESTE = np.datetime64(
    "2020-10-03T18:00:00"
)

LAT_TESTE = -21.25
LON_TESTE = -53.00


arquivo_controle = (
    ERA5_COMPLEMENTO_DIR
    / "controle_mx2t_2020-10-03_18UTC.grib"
)


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("COMPARAÇÃO ENTRE GRIB ORIGINAL E CDS ATUAL")
print("=" * 90)

print("\nData de controle:")
print(DATA_TESTE)

print("\nGRIB original:")
print(ERA5_GRIB)

print("\nArquivo CDS:")
print(arquivo_controle)


# ==========================================================
# 1. BAIXAR CAMPO DE CONTROLE SE AINDA NÃO EXISTIR
# ==========================================================

if not arquivo_controle.exists():

    print("\nArquivo de controle ainda não existe.")
    print("Baixando do CDS...")

    dataset = "reanalysis-era5-single-levels"

    request = {

        "product_type": [
            "reanalysis"
        ],

        "variable": [
            "maximum_2m_temperature_since_previous_post_processing"
        ],

        "year": [
            "2020"
        ],

        "month": [
            "10"
        ],

        "day": [
            "03"
        ],

        "time": [
            "18:00"
        ],

        "data_format": "grib",

        "download_format": "unarchived",

        "area": [
            6,
            -74,
            -34,
            -34,
        ],

        "grid": [
            0.25,
            0.25,
        ],
    }


    cliente = cdsapi.Client()

    cliente.retrieve(
        dataset,
        request,
    ).download(
        str(arquivo_controle)
    )

    print("\nDownload concluído.")

else:

    print(
        "\nArquivo de controle já existe. "
        "Download não será repetido."
    )


print(
    f"\nTamanho do arquivo de controle: "
    f"{arquivo_controle.stat().st_size:,} bytes"
)


# ==========================================================
# 2. ABRIR O GRIB ORIGINAL
# ==========================================================

print("\n" + "=" * 90)
print("ABRINDO GRIB ORIGINAL")
print("=" * 90)


index_original = (
    ERA5_INTERIM_DIR
    / "cfgrib_index"
    / "era5_{short_hash}.idx"
)


ds_original = xr.open_dataset(
    ERA5_GRIB,
    engine="cfgrib",
    backend_kwargs={
        "filter_by_keys": {
            "shortName": "mx2t"
        },
        "indexpath": str(
            index_original
        ),
    },
)


# ==========================================================
# LOCALIZAR valid_time DE 18 UTC
# ==========================================================

valid_time = (
    ds_original["valid_time"].values
)


indices = np.where(
    valid_time == DATA_TESTE
)


if len(indices[0]) == 0:

    raise RuntimeError(
        "Horário de controle não encontrado "
        "no GRIB original."
    )


indice_time = int(
    indices[0][0]
)

indice_step = int(
    indices[1][0]
)


print(
    f"\ntime index: {indice_time}"
)

print(
    f"step index: {indice_step}"
)


campo_original = (
    ds_original["mx2t"]
    .isel(
        time=indice_time,
        step=indice_step,
    )
    .values
    .astype(float)
)


# ==========================================================
# 3. ABRIR CAMPO BAIXADO DO CDS
# ==========================================================

print("\n" + "=" * 90)
print("ABRINDO CAMPO DO CDS")
print("=" * 90)


ds_cds = xr.open_dataset(
    arquivo_controle,
    engine="cfgrib",
    backend_kwargs={
        "filter_by_keys": {
            "shortName": "mx2t"
        },

        # Não precisamos manter índice
        # permanente para um arquivo tão pequeno.
        "indexpath": "",
    },
)


campo_cds = (
    ds_cds["mx2t"]
    .values
    .astype(float)
)


# Remove dimensões escalares extras, caso existam.
campo_cds = np.squeeze(
    campo_cds
)


# ==========================================================
# 4. VERIFICAR SHAPES
# ==========================================================

print("\nShape original:")
print(campo_original.shape)

print("\nShape CDS:")
print(campo_cds.shape)


if campo_original.shape != campo_cds.shape:

    raise RuntimeError(
        "As grades possuem shapes diferentes."
    )


# ==========================================================
# 5. COMPARAÇÃO CÉLULA POR CÉLULA
# ==========================================================

print("\n" + "=" * 90)
print("COMPARAÇÃO DAS 25.921 CÉLULAS")
print("=" * 90)


mascara = (
    np.isfinite(campo_original)
    &
    np.isfinite(campo_cds)
)


original_validos = (
    campo_original[mascara]
)

cds_validos = (
    campo_cds[mascara]
)


diferenca = (
    cds_validos
    -
    original_validos
)


abs_diferenca = np.abs(
    diferenca
)


mae = float(
    np.mean(abs_diferenca)
)

rmse = float(
    np.sqrt(
        np.mean(
            diferenca ** 2
        )
    )
)

bias = float(
    np.mean(
        diferenca
    )
)

max_abs = float(
    np.max(
        abs_diferenca
    )
)


print(
    f"\nCélulas comparadas: "
    f"{len(diferenca):,}"
)

print(
    f"Bias CDS - original: "
    f"{bias:.8f} K"
)

print(
    f"MAE: "
    f"{mae:.8f} K"
)

print(
    f"RMSE: "
    f"{rmse:.8f} K"
)

print(
    f"Maior diferença absoluta: "
    f"{max_abs:.8f} K"
)


# ==========================================================
# 6. CONTAGEM POR TOLERÂNCIA
# ==========================================================

tolerancias = [
    0.001,
    0.01,
    0.05,
    0.1,
]


print("\nDiferenças acima das tolerâncias:")


for tolerancia in tolerancias:

    quantidade = int(
        np.sum(
            abs_diferenca
            >
            tolerancia
        )
    )

    percentual = (
        quantidade
        /
        len(abs_diferenca)
        *
        100
    )

    print(
        f"  > {tolerancia:.3f} K: "
        f"{quantidade:,} "
        f"({percentual:.4f}%)"
    )


# ==========================================================
# 7. PONTO DE CONTROLE -21.25 / -53.00
# ==========================================================

print("\n" + "=" * 90)
print("CÉLULA DE CONTROLE")
print("=" * 90)


valor_original = (
    ds_original["mx2t"]
    .isel(
        time=indice_time,
        step=indice_step,
    )
    .sel(
        latitude=LAT_TESTE,
        longitude=LON_TESTE,
    )
    .values
    .item()
)


valor_cds = (
    ds_cds["mx2t"]
    .sel(
        latitude=LAT_TESTE,
        longitude=LON_TESTE,
    )
    .values
)


valor_cds = float(
    np.squeeze(
        valor_cds
    )
)


print(
    f"\nLatitude:  "
    f"{LAT_TESTE}"
)

print(
    f"Longitude: "
    f"{LON_TESTE}"
)


print(
    f"\nOriginal: "
    f"{valor_original:.6f} K "
    f"= {valor_original - 273.15:.6f} °C"
)


print(
    f"CDS atual: "
    f"{valor_cds:.6f} K "
    f"= {valor_cds - 273.15:.6f} °C"
)


print(
    f"Diferença: "
    f"{valor_cds - valor_original:.8f} K"
)


# ==========================================================
# 8. RESULTADO
# ==========================================================

print("\n" + "=" * 90)
print("RESULTADO")
print("=" * 90)


if max_abs <= 0.05:

    print(
        "\nCONTROLE APROVADO"
    )

    print(
        "O campo baixado atualmente pelo CDS "
        "é compatível com o GRIB original."
    )

else:

    print(
        "\nCONTROLE REQUER INVESTIGAÇÃO"
    )

    print(
        "Foram encontradas diferenças maiores "
        "que o esperado."
    )


# ==========================================================
# FECHAR
# ==========================================================

ds_original.close()
ds_cds.close()


print("\n" + "=" * 90)
print("COMPARAÇÃO CONCLUÍDA")
print("=" * 90)