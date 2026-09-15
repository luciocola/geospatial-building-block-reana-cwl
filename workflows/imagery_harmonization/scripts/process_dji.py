#!/usr/bin/env python3
"""Warp an orthorectified DJI mosaic to a reference grid and match its RGB histograms."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.enums import Resampling
from rasterio.warp import reproject

from raster_contracts import (
    NODATA,
    histogram_profile,
    sha256,
    stac_item,
    utc_now,
    valid_mask,
    write_cog,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orthomosaic", required=True)
    parser.add_argument("--target-grid", required=True)
    parser.add_argument("--reference-histogram", required=True)
    parser.add_argument("--input-scale", type=float, default=10000.0)
    parser.add_argument("--checkpoint-rmse-pixels", type=float, default=0.0)
    parser.add_argument("--cloud-shadow-fraction", type=float, default=0.0)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def distribution_distance(left: list[int], right: list[int]) -> float:
    left_values = np.asarray(left, dtype="float64")
    right_values = np.asarray(right, dtype="float64")
    left_values /= max(left_values.sum(), 1.0)
    right_values /= max(right_values.sum(), 1.0)
    midpoint = 0.5 * (left_values + right_values)

    def divergence(values: np.ndarray) -> float:
        selected = values > 0
        return float(np.sum(values[selected] * np.log2(values[selected] / midpoint[selected])))

    return 0.5 * divergence(left_values) + 0.5 * divergence(right_values)


def match_band(values: np.ndarray, target: dict) -> np.ndarray:
    source_counts, source_edges = np.histogram(values, bins=256, range=(0.0, 1.0))
    source_cdf = np.cumsum(source_counts, dtype="float64")
    source_cdf /= max(source_cdf[-1], 1.0)
    source_centers = (source_edges[:-1] + source_edges[1:]) / 2.0

    target_counts = np.asarray(target["counts"], dtype="float64")
    target_edges = np.asarray(target["bin_edges"], dtype="float64")
    if target_counts.size != 256 or target_edges.size != 257:
        raise ValueError("reference histogram must contain 256 counts and 257 bin edges per band")
    target_cdf = np.cumsum(target_counts)
    target_cdf /= max(target_cdf[-1], 1.0)
    target_centers = (target_edges[:-1] + target_edges[1:]) / 2.0

    probabilities = np.interp(values, source_centers, source_cdf, left=0.0, right=1.0)
    return np.interp(probabilities, target_cdf, target_centers).astype("float32")


def main() -> int:
    args = parse_args()
    if args.input_scale <= 0:
        raise ValueError("input-scale must be greater than zero")
    if args.checkpoint_rmse_pixels < 0 or not 0 <= args.cloud_shadow_fraction <= 1:
        raise ValueError("quality fractions and errors must be within their valid ranges")

    target_grid = read_json(args.target_grid)
    reference = read_json(args.reference_histogram)
    required_grid = {"crs", "transform", "width", "height", "band_order", "nodata"}
    missing = sorted(required_grid - target_grid.keys())
    if missing:
        raise ValueError("target grid is missing: " + ", ".join(missing))
    if target_grid["band_order"] != ["red", "green", "blue"]:
        raise ValueError("target grid band order must be red, green, blue")

    target_crs = rasterio.crs.CRS.from_user_input(target_grid["crs"])
    target_transform = Affine(*target_grid["transform"])
    width = int(target_grid["width"])
    height = int(target_grid["height"])
    warped = np.full((3, height, width), NODATA, dtype="float32")
    warped_mask = np.zeros((height, width), dtype="uint8")

    with rasterio.open(args.orthomosaic) as source:
        if source.count < 3 or source.crs is None:
            raise ValueError("orthomosaic must contain at least three bands and a CRS")
        for band in range(3):
            reproject(
                rasterio.band(source, band + 1),
                warped[band],
                src_transform=source.transform,
                src_crs=source.crs,
                src_nodata=source.nodata,
                dst_transform=target_transform,
                dst_crs=target_crs,
                dst_nodata=NODATA,
                resampling=Resampling.average,
            )
        reproject(
            source.dataset_mask(),
            warped_mask,
            src_transform=source.transform,
            src_crs=source.crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=Resampling.nearest,
        )
    warped = np.where(warped == NODATA, NODATA, warped / args.input_scale)
    mask = valid_mask(warped, warped_mask > 0)
    if not mask.any():
        raise ValueError("orthomosaic has no valid pixels on the target grid")

    before = histogram_profile(warped, mask)
    matched = warped.copy()
    for index, name in enumerate(("red", "green", "blue")):
        matched[index][mask] = match_band(warped[index][mask], reference["bands"][name])
    matched = np.clip(matched, 0.0, 1.0)
    after = histogram_profile(matched, mask)

    distances_before = {
        name: distribution_distance(before["bands"][name]["counts"], reference["bands"][name]["counts"])
        for name in ("red", "green", "blue")
    }
    distances_after = {
        name: distribution_distance(after["bands"][name]["counts"], reference["bands"][name]["counts"])
        for name in ("red", "green", "blue")
    }
    valid_values = matched[:, mask]
    clipping_fraction = float(np.mean((valid_values <= 0.0) | (valid_values >= 1.0)))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raster_path = output_dir / "dji_harmonized.tif"
    histograms_path = output_dir / "dji_histograms.json"
    quality_path = output_dir / "dji_quality.json"
    stac_path = output_dir / "dji_stac_item.json"
    provenance_path = output_dir / "dji_provenance.json"
    write_cog(raster_path, matched, mask, target_crs, target_transform)
    write_json(histograms_path, {"source_downsampled": before, "matched": after})
    quality = {
        "run_id": args.run_id,
        "valid_pixel_count": int(mask.sum()),
        "checkpoint_rmse_pixels": args.checkpoint_rmse_pixels,
        "cloud_shadow_fraction": args.cloud_shadow_fraction,
        "clipping_fraction": clipping_fraction,
        "jensen_shannon_distance_before": distances_before,
        "jensen_shannon_distance_after": distances_after,
        "resampling": "average",
        "histogram_matching": "masked-empirical-cdf",
    }
    write_json(quality_path, quality)
    item = stac_item(
        f"dji-comparison-{args.run_id}",
        raster_path,
        quality_path,
        target_crs,
        target_transform,
        width,
        height,
        {
            "platform": "dji",
            "processing:level": "orthomosaic-harmonized",
            "processing:software": {"process_dji.py": "1.0.0"},
            "processing:resampling": "average",
            "processing:radiometric_adjustment": "masked-empirical-cdf",
            "gsd": abs(target_transform.a),
        },
    )
    item["assets"]["histograms"] = {
        "href": histograms_path.name,
        "type": "application/json",
        "roles": ["metadata"],
    }
    write_json(stac_path, item)
    write_json(
        provenance_path,
        {
            "run_id": args.run_id,
            "timestamp_utc": utc_now(),
            "activity": "dji-grid-and-radiometric-harmonization",
            "process_type_uris": [
                "https://example.org/ospd/2026/process-types/geometric-correction",
                "https://example.org/ospd/2026/process-types/radiometric-preprocessing",
            ],
            "inputs": {
                "orthomosaic": {"path": args.orthomosaic, "sha256": sha256(args.orthomosaic)},
                "target_grid": {"path": args.target_grid, "sha256": sha256(args.target_grid)},
                "reference_histogram": {
                    "path": args.reference_histogram,
                    "sha256": sha256(args.reference_histogram),
                },
            },
            "outputs": {
                path.name: sha256(path)
                for path in (raster_path, histograms_path, quality_path, stac_path)
            },
        },
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, ValueError, rasterio.errors.RasterioError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2) from error