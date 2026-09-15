#!/usr/bin/env python3
"""Shared raster, histogram, STAC, and provenance helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.shutil import copy as rio_copy
from rasterio.transform import Affine
from rasterio.warp import transform_bounds


BAND_NAMES = ("red", "green", "blue")
NODATA = -9999.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)


def valid_mask(data: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    valid = np.all(np.isfinite(data), axis=0)
    valid &= np.all(data != NODATA, axis=0)
    if mask is not None:
        valid &= mask.astype(bool)
    return valid


def histogram_profile(data: np.ndarray, mask: np.ndarray, bins: int = 256) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "method": "masked-histogram",
        "bins": bins,
        "valid_range": [0.0, 1.0],
        "sample_count": int(mask.sum()),
        "bands": {},
    }
    edges = np.linspace(0.0, 1.0, bins + 1)
    for index, name in enumerate(BAND_NAMES):
        values = np.clip(data[index][mask], 0.0, 1.0)
        counts, _ = np.histogram(values, bins=edges)
        quantiles = np.quantile(values, [0.02, 0.50, 0.98]) if values.size else [0, 0, 0]
        profile["bands"][name] = {
            "counts": counts.astype(int).tolist(),
            "bin_edges": edges.tolist(),
            "quantiles": {
                "p02": float(quantiles[0]),
                "p50": float(quantiles[1]),
                "p98": float(quantiles[2]),
            },
        }
    return profile


def grid_contract(crs: CRS, transform: Affine, width: int, height: int) -> dict[str, Any]:
    left, top = transform * (0, 0)
    right, bottom = transform * (width, height)
    return {
        "crs": crs.to_string(),
        "transform": list(transform)[:6],
        "resolution": [transform.a, transform.e],
        "extent": [min(left, right), min(bottom, top), max(left, right), max(bottom, top)],
        "width": width,
        "height": height,
        "band_order": list(BAND_NAMES),
        "dtype": "float32",
        "nodata": NODATA,
    }


def write_cog(path: str | Path, data: np.ndarray, mask: np.ndarray, crs: CRS, transform: Affine) -> None:
    path = Path(path)
    temporary = path.with_suffix(".working.tif")
    profile = {
        "driver": "GTiff",
        "width": data.shape[2],
        "height": data.shape[1],
        "count": 3,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "nodata": NODATA,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": min(256, max(16, (data.shape[2] // 16) * 16)),
        "blockysize": min(256, max(16, (data.shape[1] // 16) * 16)),
    }
    output = np.where(mask[np.newaxis, :, :], data, NODATA).astype("float32")
    with rasterio.open(temporary, "w", **profile) as dataset:
        dataset.write(output)
        dataset.write_mask(mask.astype("uint8") * 255)
        for index, name in enumerate(BAND_NAMES, start=1):
            dataset.set_band_description(index, name)
    rio_copy(
        temporary,
        path,
        driver="COG",
        compress="DEFLATE",
        overview_resampling="average",
        overview_level=2,
    )
    temporary.unlink()


def stac_item(
    item_id: str,
    raster_path: str | Path,
    quality_path: str | Path,
    crs: CRS,
    transform: Affine,
    width: int,
    height: int,
    properties: dict[str, Any],
) -> dict[str, Any]:
    grid = grid_contract(crs, transform, width, height)
    west, south, east, north = transform_bounds(crs, "EPSG:4326", *grid["extent"])
    geometry = {
        "type": "Polygon",
        "coordinates": [[
            [west, south], [east, south], [east, north], [west, north], [west, south]
        ]],
    }
    return {
        "type": "Feature",
        "stac_version": "1.0.0",
        "stac_extensions": [
            "https://stac-extensions.github.io/processing/v1.2.0/schema.json",
            "https://stac-extensions.github.io/projection/v2.0.0/schema.json",
            "https://stac-extensions.github.io/checksum/v1.0.0/schema.json",
        ],
        "id": item_id,
        "bbox": [west, south, east, north],
        "geometry": geometry,
        "properties": {
            "datetime": utc_now(),
            "proj:code": crs.to_string(),
            "proj:shape": [height, width],
            "proj:transform": list(transform)[:6],
            **properties,
        },
        "links": [],
        "assets": {
            "data": {
                "href": Path(raster_path).name,
                "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                "roles": ["data", "derived"],
                "checksum:multihash": "1220" + sha256(raster_path),
            },
            "quality": {
                "href": Path(quality_path).name,
                "type": "application/json",
                "roles": ["quality", "metadata"],
            },
        },
    }