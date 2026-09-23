import numpy as np
import pandas as pd
import xarray as xr

from config import (
    ERA5_GRIB,
    ERA5_INTERIM_DIR,
)


print("=" * 80)
print("VALIDAÇÃO DA COBERTURA HORÁRIA REAL DO ERA5")
print("=" * 80)


# ==========================================================
# ABRIR DATASET
# ==========================================================

index_path = (
    ERA5_INTERIM_DIR
    / "cfgrib_index"
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
# PEGAR SOMENTE UMA CÉLULA CONHECIDA NO BRASIL
# ==========================================================

lat = -21.25
lon = -53.00


temperatura = (
    ds["mx2t"]
    .sel(
        latitude=lat,
        longitude=lon,
    )
)


print("\nCélula analisada:")
print(f"Latitude:  {lat}")
print(f"Longitude: {lon}")


# ==========================================================
# TRANSFORMAR time × step EM UMA LISTA
# ==========================================================

valid_time = (
    ds["valid_time"]
    .values
    .reshape(-1)
)


valores = (
    temperatura
    .values
    .reshape(-1)
)


df = pd.DataFrame(
    {
        "valid_time": valid_time,
        "temperatura_k": valores,
    }
)


# ==========================================================
# LIMITAR A 1995–2025
# ==========================================================

inicio = pd.Timestamp(
    "1995-01-01 00:00:00"
)

fim = pd.Timestamp(
    "2026-01-01 00:00:00"
)


df = df[
    (df["valid_time"] >= inicio)
    &
    (df["valid_time"] < fim)
].copy()


df["hora_utc"] = (
    df["valid_time"]
    .dt
    .hour
)


df["disponivel"] = (
    df["temperatura_k"]
    .notna()
)


# ==========================================================
# CONTAGEM POR HORA
# ==========================================================

print("\n" + "=" * 80)
print("COBERTURA POR HORA UTC")
print("=" * 80)


resultado = (
    df.groupby("hora_utc")
    ["disponivel"]
    .agg(
        registros="size",
        disponiveis="sum",
    )
)


resultado["faltantes"] = (
    resultado["registros"]
    -
    resultado["disponiveis"]
)


resultado["cobertura_percentual"] = (
    resultado["disponiveis"]
    /
    resultado["registros"]
    *
    100
)


print(resultado)


# ==========================================================
# TOTAL
# ==========================================================

total = len(df)

disponiveis = int(
    df["disponivel"].sum()
)

faltantes = (
    total
    -
    disponiveis
)


print("\n" + "=" * 80)
print("RESUMO")
print("=" * 80)

print(
    f"\nPosições temporais: "
    f"{total:,}"
)

print(
    f"Com temperatura: "
    f"{disponiveis:,}"
)

print(
    f"Sem temperatura: "
    f"{faltantes:,}"
)

print(
    f"Cobertura: "
    f"{disponiveis / total * 100:.2f}%"
)


# ==========================================================
# EXEMPLO DE UM DIA
# ==========================================================

print("\n" + "=" * 80)
print("EXEMPLO: 03/10/2020")
print("=" * 80)


dia = df[
    (
        df["valid_time"]
        >= pd.Timestamp("2020-10-03")
    )
    &
    (
        df["valid_time"]
        < pd.Timestamp("2020-10-04")
    )
].copy()


# Como o cubo pode conter combinações inexistentes,
# agrupamos por valid_time.

dia = (
    dia
    .sort_values("valid_time")
    .groupby(
        "valid_time",
        as_index=False,
    )
    .agg(
        temperatura_k=(
            "temperatura_k",
            "max",
        )
    )
)


dia["temperatura_c"] = (
    dia["temperatura_k"]
    -
    273.15
)


for _, linha in dia.iterrows():

    horario = linha["valid_time"]

    temperatura_c = linha[
        "temperatura_c"
    ]

    if pd.isna(temperatura_c):

        print(
            f"{horario}: "
            "SEM DADO"
        )

    else:

        print(
            f"{horario}: "
            f"{temperatura_c:.2f} °C"
        )


ds.close()


print("\n" + "=" * 80)
print("VALIDAÇÃO CONCLUÍDA")
print("=" * 80)