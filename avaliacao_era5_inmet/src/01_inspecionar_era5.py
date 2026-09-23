from pathlib import Path
import sys

import numpy as np
import xarray as xr
import cfgrib

from config import (
    ERA5_GRIB,
    ERA5_INTERIM_DIR,
)


# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def tamanho_legivel(numero_bytes):
    """
    Converte bytes para uma representação mais fácil de ler.
    """

    tamanho = float(numero_bytes)

    for unidade in ["B", "KB", "MB", "GB", "TB"]:
        if tamanho < 1024:
            return f"{tamanho:.2f} {unidade}"

        tamanho /= 1024

    return f"{tamanho:.2f} PB"


def encontrar_coordenada(dataset, nomes):
    """
    Procura uma coordenada entre vários nomes possíveis.
    """

    for nome in nomes:
        if nome in dataset.coords:
            return nome

    return None


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 80)
print("INSPEÇÃO DO ARQUIVO ERA5")
print("=" * 80)

print("\nPython:")
print(sys.version)

print("\nXarray:")
print(xr.__version__)

print("\ncfgrib:")
print(cfgrib.__version__)


# ==========================================================
# VERIFICAÇÃO DO ARQUIVO
# ==========================================================

print("\n" + "=" * 80)
print("1. ARQUIVO")
print("=" * 80)

print(f"\nCaminho:\n{ERA5_GRIB}")

if not ERA5_GRIB.exists():
    raise FileNotFoundError(
        f"\nArquivo ERA5 não encontrado:\n{ERA5_GRIB}"
    )

print("\nArquivo encontrado: SIM")

tamanho = ERA5_GRIB.stat().st_size

print(f"Tamanho: {tamanho_legivel(tamanho)}")


# ==========================================================
# ÍNDICE LOCAL DO NOVO PROJETO
# ==========================================================

INDEX_DIR = ERA5_INTERIM_DIR / "cfgrib_index"

INDEX_DIR.mkdir(
    parents=True,
    exist_ok=True
)

index_path = INDEX_DIR / "era5_{short_hash}.idx"

print("\nÍndice cfgrib será armazenado em:")
print(index_path)

print(
    "\nO arquivo GRIB original NÃO será modificado."
)


# ==========================================================
# TENTATIVA DE ABERTURA DA VARIÁVEL MX2T
# ==========================================================

print("\n" + "=" * 80)
print("2. ABRINDO mx2t")
print("=" * 80)

try:

    ds = xr.open_dataset(
        ERA5_GRIB,
        engine="cfgrib",
        backend_kwargs={
            "filter_by_keys": {
                "shortName": "mx2t"
            },
            "indexpath": str(index_path),
        },
    )

    print("\nmx2t aberta com sucesso.")

except Exception as erro:

    print("\nNão foi possível abrir diretamente mx2t.")

    print("\nErro:")
    print(erro)

    print(
        "\nTentando descobrir automaticamente "
        "os grupos existentes no GRIB..."
    )

    datasets = cfgrib.open_datasets(
        str(ERA5_GRIB),
        backend_kwargs={
            "indexpath": str(index_path),
        },
    )

    print(
        f"\nQuantidade de grupos encontrados: "
        f"{len(datasets)}"
    )

    for numero, dataset in enumerate(datasets):

        print("\n" + "-" * 80)
        print(f"GRUPO {numero}")
        print("-" * 80)

        print(dataset)

        print("\nVariáveis:")

        for variavel in dataset.data_vars:
            print(f"  - {variavel}")

    raise SystemExit(
        "\nAbertura automática concluída. "
        "Analise os grupos mostrados acima."
    )


# ==========================================================
# ESTRUTURA DO DATASET
# ==========================================================

print("\n" + "=" * 80)
print("3. ESTRUTURA DO DATASET")
print("=" * 80)

print(ds)


# ==========================================================
# DIMENSÕES
# ==========================================================

print("\n" + "=" * 80)
print("4. DIMENSÕES")
print("=" * 80)

for nome, tamanho_dim in ds.sizes.items():

    print(
        f"{nome:<20} "
        f"{tamanho_dim:,}"
    )


# ==========================================================
# COORDENADAS
# ==========================================================

print("\n" + "=" * 80)
print("5. COORDENADAS")
print("=" * 80)

for coordenada in ds.coords:

    objeto = ds[coordenada]

    print(f"\n{coordenada}")

    print(f"  dimensões: {objeto.dims}")
    print(f"  shape:     {objeto.shape}")
    print(f"  dtype:     {objeto.dtype}")


# ==========================================================
# LATITUDE E LONGITUDE
# ==========================================================

latitude_nome = encontrar_coordenada(
    ds,
    [
        "latitude",
        "lat",
    ],
)

longitude_nome = encontrar_coordenada(
    ds,
    [
        "longitude",
        "lon",
    ],
)


print("\n" + "=" * 80)
print("6. GRADE ESPACIAL")
print("=" * 80)


if latitude_nome is not None:

    latitude = ds[latitude_nome].values

    print("\nLatitude:")

    print(
        f"  mínimo: {np.nanmin(latitude):.4f}"
    )

    print(
        f"  máximo: {np.nanmax(latitude):.4f}"
    )

    print(
        f"  pontos: {len(latitude):,}"
    )

    if len(latitude) > 1:

        diferencas = np.abs(
            np.diff(latitude.astype(float))
        )

        resolucao_lat = np.median(diferencas)

        print(
            f"  resolução aproximada: "
            f"{resolucao_lat:.4f}°"
        )

else:

    print("\nLatitude não encontrada.")


if longitude_nome is not None:

    longitude = ds[longitude_nome].values

    print("\nLongitude:")

    print(
        f"  mínimo: {np.nanmin(longitude):.4f}"
    )

    print(
        f"  máximo: {np.nanmax(longitude):.4f}"
    )

    print(
        f"  pontos: {len(longitude):,}"
    )

    if len(longitude) > 1:

        diferencas = np.abs(
            np.diff(longitude.astype(float))
        )

        resolucao_lon = np.median(diferencas)

        print(
            f"  resolução aproximada: "
            f"{resolucao_lon:.4f}°"
        )


if (
    latitude_nome is not None
    and longitude_nome is not None
):

    numero_celulas = (
        len(latitude)
        * len(longitude)
    )

    print(
        f"\nTotal da grade retangular: "
        f"{numero_celulas:,} células"
    )


# ==========================================================
# TEMPO
# ==========================================================

print("\n" + "=" * 80)
print("7. TEMPO")
print("=" * 80)


for nome_tempo in [
    "time",
    "valid_time",
    "forecast_reference_time",
]:

    if nome_tempo not in ds.coords:
        continue

    tempo = ds[nome_tempo]

    print(f"\nCoordenada: {nome_tempo}")

    print(
        f"  dimensões: {tempo.dims}"
    )

    print(
        f"  shape: {tempo.shape}"
    )

    try:

        valores = tempo.values

        print(
            f"  primeiro: "
            f"{np.asarray(valores).flat[0]}"
        )

        print(
            f"  último:   "
            f"{np.asarray(valores).flat[-1]}"
        )

    except Exception as erro:

        print(
            f"  Não foi possível "
            f"ler início/fim: {erro}"
        )


# ==========================================================
# STEP
# ==========================================================

if "step" in ds.coords:

    print("\n" + "=" * 80)
    print("8. STEP")
    print("=" * 80)

    step = ds["step"]

    print(f"\nDimensões: {step.dims}")

    print(f"Quantidade: {step.size}")

    valores_step = step.values

    print(
        f"Primeiro: "
        f"{np.asarray(valores_step).flat[0]}"
    )

    print(
        f"Último: "
        f"{np.asarray(valores_step).flat[-1]}"
    )


# ==========================================================
# VARIÁVEIS
# ==========================================================

print("\n" + "=" * 80)
print("9. VARIÁVEIS")
print("=" * 80)


for nome_variavel in ds.data_vars:

    variavel = ds[nome_variavel]

    print(f"\nVariável: {nome_variavel}")

    print(
        f"  dimensões: "
        f"{variavel.dims}"
    )

    print(
        f"  shape: "
        f"{variavel.shape}"
    )

    print(
        f"  dtype: "
        f"{variavel.dtype}"
    )

    print(
        f"  unidades: "
        f"{variavel.attrs.get('units')}"
    )

    print(
        f"  long_name: "
        f"{variavel.attrs.get('long_name')}"
    )

    print(
        f"  standard_name: "
        f"{variavel.attrs.get('standard_name')}"
    )


# ==========================================================
# INSPEÇÃO ESPECÍFICA DA mx2t
# ==========================================================

if "mx2t" in ds.data_vars:

    variavel = ds["mx2t"]

    print("\n" + "=" * 80)
    print("10. DETALHES DA mx2t")
    print("=" * 80)

    print("\nAtributos:")

    for chave, valor in variavel.attrs.items():

        print(
            f"  {chave}: {valor}"
        )


    # Seleciona apenas um único valor.
    # NÃO carrega todo o conjunto de 31 anos.

    selecao = {}

    for dimensao in variavel.dims:
        selecao[dimensao] = 0

    try:

        valor = variavel.isel(
            selecao
        ).values.item()

        print(
            f"\nPrimeiro valor encontrado: "
            f"{valor}"
        )

        unidade = variavel.attrs.get(
            "units",
            "",
        )

        if unidade in ["K", "kelvin"]:

            valor_celsius = valor - 273.15

            print(
                f"Primeiro valor em °C: "
                f"{valor_celsius:.2f}"
            )

    except Exception as erro:

        print(
            "\nNão foi possível "
            "ler o primeiro valor:"
        )

        print(erro)


# ==========================================================
# ATRIBUTOS GLOBAIS
# ==========================================================

print("\n" + "=" * 80)
print("11. ATRIBUTOS DO GRIB")
print("=" * 80)

for chave, valor in ds.attrs.items():

    print(
        f"{chave}: {valor}"
    )


# ==========================================================
# FIM
# ==========================================================

print("\n" + "=" * 80)
print("INSPEÇÃO CONCLUÍDA")
print("=" * 80)

print(
    "\nNenhuma transformação foi realizada "
    "no arquivo ERA5 original."
)

ds.close()