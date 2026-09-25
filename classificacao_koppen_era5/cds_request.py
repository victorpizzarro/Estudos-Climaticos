import cdsapi

client = cdsapi.Client()

dataset = "reanalysis-era5-single-levels-monthly-means"
request = {
    "product_type": ["monthly_averaged_reanalysis"],
    "variable": [
        "2m_temperature",
        "total_precipitation",
    ],
    "year": [str(y) for y in range(1995, 2026)],
    "month": [f"{m:02d}" for m in range(1, 13)],
    "time": ["00:00"],
    # North, West, South, East -- bounding box covering all of Brazil
    "area": [6, -74, -34, -34],
    "data_format": "grib",
    "download_format": "unarchived",
}

client.retrieve(dataset, request).download("era5_brazil_1995_2025.grib")
