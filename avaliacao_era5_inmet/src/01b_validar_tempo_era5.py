import numpy as np
import xarray as xr

from config import (
    ERA5_GRIB,
    ERA5_INTERIM_DIR,
)


print("=" * 80)
print("VALIDAÇÃO TEMPORAL DO ERA5")
print("=" * 80)


# ==========================================================
# ABERTURA DO ERA5
# ==========================================================

index_dir = ERA5_INTERIM_DIR / "cfgrib_index"

index_dir.mkdir(
    parents=True,
    exist_ok=True,
)

index_path = (
    index_dir
    / "era5_{short_hash}.idx"
)


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


# ==========================================================
# VALID_TIME
# ==========================================================

valid_time = ds["valid_time"].values.reshape(-1)


inicio = np.datetime64(
    "1995-01-01T00:00:00"
)

fim = np.datetime64(
    "2026-01-01T00:00:00"
)


mascara = (
    (valid_time >= inicio)
    &
    (valid_time < fim)
)


valid_periodo = valid_time[mascara]


print("\nPeríodo desejado:")

print(
    "Início:",
    valid_periodo[0]
)

print(
    "Fim:",
    valid_periodo[-1]
)


print(
    "\nQuantidade de horas:",
    len(valid_periodo)
)


# ==========================================================
# HORAS ESPERADAS
# ==========================================================

esperado = 271752


print(
    "Quantidade esperada:",
    esperado
)


print(
    "Quantidade correta:",
    len(valid_periodo) == esperado
)


# ==========================================================
# DUPLICATAS
# ==========================================================

unicos = np.unique(
    valid_periodo
)


duplicados = (
    len(valid_periodo)
    -
    len(unicos)
)


print(
    "\nDatas/horas duplicadas:",
    duplicados
)


# ==========================================================
# CONTINUIDADE HORÁRIA
# ==========================================================

diferencas = np.diff(
    valid_periodo
)


uma_hora = np.timedelta64(
    1,
    "h",
)


irregulares = np.sum(
    diferencas != uma_hora
)


print(
    "Intervalos diferentes de 1 hora:",
    irregulares
)


# ==========================================================
# TESTE COM O MÁXIMO DE 2020
# ==========================================================

print("\n" + "=" * 80)
print("TESTE DO EVENTO DE 2020")
print("=" * 80)


data_teste = np.datetime64(
    "2020-10-03T18:00:00"
)


indices = np.where(
    ds["valid_time"].values
    ==
    data_teste
)


if len(indices[0]) == 0:

    print(
        "\nHorário de teste não encontrado."
    )

else:

    indice_time = indices[0][0]
    indice_step = indices[1][0]


    time_base = ds["time"].isel(
        time=indice_time
    ).values


    step = ds["step"].isel(
        step=indice_step
    ).values


    print(
        "\nvalid_time:",
        data_teste,
    )

    print(
        "time:",
        time_base,
    )

    print(
        "step:",
        step,
    )


    valor_k = (
        ds["mx2t"]
        .isel(
            time=indice_time,
            step=indice_step,
        )
        .sel(
            latitude=-21.25,
            longitude=-53.00,
        )
        .values
        .item()
    )


    valor_c = (
        valor_k
        -
        273.15
    )


    print(
        "\nLatitude:",
        -21.25
    )

    print(
        "Longitude:",
        -53.00
    )


    print(
        f"\nTemperatura Kelvin: "
        f"{valor_k:.4f} K"
    )

    print(
        f"Temperatura Celsius: "
        f"{valor_c:.4f} °C"
    )


    print(
        "\nValor esperado "
        "aproximadamente:"
    )

    print(
        "42.94 °C"
    )


    diferenca = (
        valor_c
        -
        42.94
    )


    print(
        f"\nDiferença: "
        f"{diferenca:.6f} °C"
    )


# ==========================================================
# FINAL
# ==========================================================

ds.close()


print("\n" + "=" * 80)
print("VALIDAÇÃO CONCLUÍDA")
print("=" * 80)