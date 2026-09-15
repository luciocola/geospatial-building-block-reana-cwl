#!/usr/bin/env python3
"""Generate small georeferenced RGB fixtures for local workflow execution."""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin


HERE = Path(__file__).resolve().parent
CRS = "EPSG:32632"
ORIGIN_X = 500000.0
ORIGIN_Y = 4510000.0


def scene(height: int, width: int, color_shift: tuple[float, float, float]) -> np.ndarray:
    y, x = np.mgrid[0:height, 0:width]
    x_norm = x / max(width - 1, 1)
    y_norm = y / max(height - 1, 1)
    road = np.exp(-((y_norm - 0.55 - 0.08 * np.sin(x_norm * 8)) ** 2) / 0.0015)
    field = ((x_norm > 0.15) & (x_norm < 0.48) & (y_norm > 0.12) & (y_norm < 0.42)).astype(float)
    water = ((x_norm - 0.76) ** 2 + (y_norm - 0.28) ** 2 < 0.06).astype(float)
    red = 0.12 + 0.34 * x_norm + 0.16 * field + 0.25 * road - 0.08 * water
    green = 0.16 + 0.30 * y_norm + 0.22 * field + 0.18 * road - 0.05 * water
    blue = 0.10 + 0.20 * (1 - x_norm) + 0.12 * road + 0.22 * water
    result = np.stack((red, green, blue))
    result = result * np.asarray(color_shift)[:, None, None]
    return np.clip(result, 0.0, 1.0)


def write_fixture(path: Path, size: int, resolution: float, shift: tuple[float, float, float]) -> None:
    data = (scene(size, size, shift) * 10000).astype("uint16")
    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "count": 3,
        "dtype": "uint16",
        "crs": CRS,
        "transform": from_origin(ORIGIN_X, ORIGIN_Y, resolution, resolution),
        "nodata": 0,
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(data)
        for index, name in enumerate(("red", "green", "blue"), start=1):
            dataset.set_band_description(index, name)


def main() -> None:
    write_fixture(HERE / "sentinel2_rgb_demo.tif", 64, 10.0, (1.0, 1.0, 1.0))
    write_fixture(HERE / "dji_orthomosaic_demo.tif", 640, 1.0, (1.22, 0.88, 1.12))
    print("Generated Sentinel-2 and DJI demo GeoTIFFs")


if __name__ == "__main__":
    main()