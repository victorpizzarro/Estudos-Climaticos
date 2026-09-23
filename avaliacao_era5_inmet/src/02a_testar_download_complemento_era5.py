from pathlib import Path

import cdsapi


# ==========================================================
# DIRETÓRIOS
# ==========================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

OUTPUT_DIR = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "era5"
    / "complemento"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


arquivo_saida = (
    OUTPUT_DIR
    / "teste_mx2t_2020-10-03_horas_faltantes.grib"
)


# ==========================================================
# HORAS QUE FALTAM NO GRIB ORIGINAL
# ==========================================================

horas_faltantes = [
    "00:00",
    "01:00",
    "02:00",
    "03:00",
    "22:00",
    "23:00",
]


# ==========================================================
# REQUISIÇÃO CDS
# ==========================================================

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

    "time": horas_faltantes,

    "data_format": "grib",

    "download_format": "unarchived",

    # Norte, Oeste, Sul, Leste
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


# ==========================================================
# DOWNLOAD
# ==========================================================

print("=" * 80)
print("TESTE DE DOWNLOAD DO COMPLEMENTO ERA5")
print("=" * 80)

print("\nDataset:")
print(dataset)

print("\nHorários solicitados:")

for hora in horas_faltantes:
    print(" ", hora)

print("\nArquivo de saída:")
print(arquivo_saida)


cliente = cdsapi.Client()


cliente.retrieve(
    dataset,
    request,
).download(
    str(arquivo_saida)
)


print("\n" + "=" * 80)
print("DOWNLOAD CONCLUÍDO")
print("=" * 80)

print("\nArquivo:")
print(arquivo_saida)

print(
    "\nTamanho:",
    arquivo_saida.stat().st_size,
    "bytes",
)