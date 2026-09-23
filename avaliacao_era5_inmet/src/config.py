from pathlib import Path


# ==========================================================
# PROJETO NOVO
# ==========================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]


# ==========================================================
# PROJETO BRASIL_ERA5 ORIGINAL
# ==========================================================

BRASIL_ERA5_DIR = PROJECT_DIR.parents[1]


# ==========================================================
# DADOS ERA5 JÁ EXISTENTES
# ==========================================================

LEGACY_DATA_DIR = BRASIL_ERA5_DIR / "codigos" / "data_set"

ERA5_GRIB = (
    LEGACY_DATA_DIR
    / "era5_1995_2025_completo.grib"
)

ERA5_INDEX = (
    LEGACY_DATA_DIR
    / "era5_1995_2025_completo.grib.mx2t.idx"
)

ERA5_NETCDF = (
    LEGACY_DATA_DIR
    / "dados.nc"
)
# ==========================================================
# COMPLEMENTO ERA5
# ==========================================================

ERA5_COMPLEMENTO_DIR = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "era5"
    / "complemento"
)

ERA5_COMPLEMENTO_TESTE = (
    ERA5_COMPLEMENTO_DIR
    / "teste_mx2t_2020-10-03_horas_faltantes.grib"
)
ERA5_COMPLEMENTO_ANOS_DIR = (
    ERA5_COMPLEMENTO_DIR
    / "anos"
)

ERA5_COMPLEMENTO_TESTES_DIR = (
    ERA5_COMPLEMENTO_DIR
    / "testes"
)

# ==========================================================
# MALHA DO IBGE JÁ EXISTENTE
# ==========================================================

IBGE_SHAPEFILE = (
    LEGACY_DATA_DIR
    / "malha_ibge"
    / "BR_Pais_2024"
    / "BR_Pais_2024.shp"
)

ARQUIVO_UFS = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "shapes"
    / "BR_UF_2024"
    / "BR_UF_2024.shp"
)


# ==========================================================
# DADOS DO NOVO PROJETO
# ==========================================================

DATA_DIR = PROJECT_DIR / "data"

RAW_DIR = DATA_DIR / "raw"

INMET_RAW_DIR = RAW_DIR / "inmet"

INMET_AUTOMATICAS_DIR = (
    INMET_RAW_DIR
    / "automaticas"
)

INMET_CONVENCIONAIS_DIR = (
    INMET_RAW_DIR
    / "convencionais"
)


INTERIM_DIR = DATA_DIR / "interim"

ERA5_INTERIM_DIR = INTERIM_DIR / "era5"
INMET_INTERIM_DIR = INTERIM_DIR / "inmet"


PROCESSED_DIR = DATA_DIR / "processed"

STATIONS_DIR = PROCESSED_DIR / "stations"
MATCHES_DIR = PROCESSED_DIR / "matches"
ANNUAL_DIR = PROCESSED_DIR / "annual"


# ==========================================================
# RESULTADOS
# ==========================================================

OUTPUT_DIR = PROJECT_DIR / "outputs"

FIGURES_DIR = OUTPUT_DIR / "figures"
MAPS_DIR = OUTPUT_DIR / "maps"
TABLES_DIR = OUTPUT_DIR / "tables"
LOGS_DIR = OUTPUT_DIR / "logs"


# ==========================================================
# CONFIGURAÇÕES DA PESQUISA
# ==========================================================

ERA5_START_YEAR = 1995
ERA5_END_YEAR = 2025

INMET_START_YEAR = 2000
INMET_END_YEAR = 2025

ERA5_VARIABLE = "mx2t"

ERA5_RESOLUTION = 0.25

ERROR_DEFINITION = "ERA5 - INMET"