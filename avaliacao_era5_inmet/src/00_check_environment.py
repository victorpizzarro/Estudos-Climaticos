from config import (
    PROJECT_DIR,
    BRASIL_ERA5_DIR,
    ERA5_GRIB,
    ERA5_NETCDF,
    IBGE_SHAPEFILE,
    INMET_AUTOMATICAS_DIR,
)


print("=" * 70)
print("VERIFICAÇÃO DOS CAMINHOS")
print("=" * 70)

print("\nProjeto novo:")
print(PROJECT_DIR)

print("\nProjeto antigo:")
print(BRASIL_ERA5_DIR)

print("\nERA5 GRIB:")
print(ERA5_GRIB)
print("Existe:", ERA5_GRIB.exists())

print("\nERA5 NetCDF:")
print(ERA5_NETCDF)
print("Existe:", ERA5_NETCDF.exists())

print("\nShapefile IBGE:")
print(IBGE_SHAPEFILE)
print("Existe:", IBGE_SHAPEFILE.exists())

print("\nPasta INMET nova:")
print(INMET_AUTOMATICAS_DIR)
print("Existe:", INMET_AUTOMATICAS_DIR.exists())