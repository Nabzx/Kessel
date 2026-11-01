"""Build the credited Rutongo satellite and elevation crops from public COGs."""

from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling, transform


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "rutongo"
LOCATION = (30.059167, -1.8175)
SIZE_METRES = 4096
SOURCE_RESOLUTION_METRES = 4
SENTINEL_COG = (
    "https://sentinel-cogs.s3.us-west-2.amazonaws.com/"
    "sentinel-s2-l2a-cogs/35/M/RU/2026/8/"
    "S2B_35MRU_20260814_0_L2A/TCI.tif"
)
COPERNICUS_DEM_COG = (
    "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/"
    "Copernicus_DSM_COG_10_S02_00_E030_00_DEM/"
    "Copernicus_DSM_COG_10_S02_00_E030_00_DEM.tif"
)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    x, y = transform("EPSG:4326", "EPSG:32735", [LOCATION[0]], [LOCATION[1]])
    centre_x, centre_y = x[0], y[0]
    width = height = SIZE_METRES // SOURCE_RESOLUTION_METRES
    left = centre_x - SIZE_METRES / 2
    top = centre_y + SIZE_METRES / 2
    destination_transform = from_origin(left, top, SOURCE_RESOLUTION_METRES, SOURCE_RESOLUTION_METRES)

    rgb = np.zeros((3, height, width), dtype=np.uint8)
    with rasterio.open(SENTINEL_COG) as source:
        for band in range(1, 4):
            reproject(
                rasterio.band(source, band),
                rgb[band - 1],
                src_transform=source.transform,
                src_crs=source.crs,
                src_nodata=source.nodata,
                dst_transform=destination_transform,
                dst_crs="EPSG:32735",
                dst_nodata=0,
                resampling=Resampling.bilinear,
            )
    satellite = Image.fromarray(np.moveaxis(rgb, 0, -1)).resize((1024, 1024), Image.Resampling.LANCZOS)
    satellite.save(OUTPUT / "satellite-2026-08-14.webp", "WEBP", quality=86, method=6)

    elevation = np.full((height, width), np.nan, dtype=np.float32)
    with rasterio.open(COPERNICUS_DEM_COG) as source:
        reproject(
            rasterio.band(source, 1),
            elevation,
            src_transform=source.transform,
            src_crs=source.crs,
            src_nodata=source.nodata,
            dst_transform=destination_transform,
            dst_crs="EPSG:32735",
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    valid = np.isfinite(elevation)
    minimum, maximum = np.percentile(elevation[valid], [1, 99])
    heightfield = np.clip((np.nan_to_num(elevation, nan=minimum) - minimum) / (maximum - minimum), 0, 1)
    height_image = Image.fromarray(np.rint(heightfield * 255).astype(np.uint8))
    height_image.resize((256, 256), Image.Resampling.LANCZOS).save(
        OUTPUT / "elevation-30m-4km.png", optimize=True
    )
    print(f"Heightfield metres: {minimum:.2f} to {maximum:.2f}")
    print(f"Outputs: {[(path.name, path.stat().st_size) for path in OUTPUT.iterdir()]}")


if __name__ == "__main__":
    main()
