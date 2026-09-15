#!/usr/bin/env python3
"""Apply measurable spatial and radiometric acceptance gates to a harmonized pair."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

from raster_contracts import histogram_profile, valid_mask, write_json
from process_dji import distribution_distance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-image", required=True)
    parser.add_argument("--comparison-image", required=True)
    parser.add_argument("--dji-quality", required=True)
    parser.add_argument("--min-overlap-pixels", type=int, default=10000)
    parser.add_argument("--max-js-distance", type=float, default=0.10)
    parser.add_argument("--max-clipping-fraction", type=float, default=0.01)
    parser.add_argument("--max-registration-rmse-pixels", type=float, default=1.0)
    parser.add_argument("--max-cloud-shadow-fraction", type=float, default=0.05)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def same_grid(left: rasterio.DatasetReader, right: rasterio.DatasetReader) -> bool:
    return (
        left.crs == right.crs
        and left.width == right.width
        and left.height == right.height
        and left.transform.almost_equals(right.transform)
        and left.count >= 3
        and right.count >= 3
    )


def main() -> int:
    args = parse_args()
    with open(args.dji_quality, "r", encoding="utf-8") as stream:
        dji_quality = json.load(stream)

    with rasterio.open(args.reference_image) as reference, rasterio.open(args.comparison_image) as comparison:
        grid_equal = same_grid(reference, comparison)
        if not grid_equal:
            report = {"passed": False, "checks": {"grid_equal": False}}
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            write_json(output_dir / "comparability_report.json", report)
            return 2
        reference_data = reference.read((1, 2, 3), out_dtype="float32")
        comparison_data = comparison.read((1, 2, 3), out_dtype="float32")
        overlap = valid_mask(reference_data, reference.dataset_mask() > 0)
        overlap &= valid_mask(comparison_data, comparison.dataset_mask() > 0)

    reference_profile = histogram_profile(reference_data, overlap)
    comparison_profile = histogram_profile(comparison_data, overlap)
    distances = {
        name: distribution_distance(
            reference_profile["bands"][name]["counts"],
            comparison_profile["bands"][name]["counts"],
        )
        for name in ("red", "green", "blue")
    }
    checks = {
        "grid_equal": grid_equal,
        "minimum_overlap": int(overlap.sum()) >= args.min_overlap_pixels,
        "histogram_distance": max(distances.values()) <= args.max_js_distance,
        "clipping_fraction": dji_quality["clipping_fraction"] <= args.max_clipping_fraction,
        "registration_rmse": dji_quality["checkpoint_rmse_pixels"] < args.max_registration_rmse_pixels,
        "cloud_shadow_fraction": dji_quality["cloud_shadow_fraction"] <= args.max_cloud_shadow_fraction,
    }
    report = {
        "passed": all(checks.values()),
        "checks": checks,
        "measurements": {
            "common_overlap_pixels": int(overlap.sum()),
            "jensen_shannon_distance": distances,
            "clipping_fraction": dji_quality["clipping_fraction"],
            "checkpoint_rmse_pixels": dji_quality["checkpoint_rmse_pixels"],
            "cloud_shadow_fraction": dji_quality["cloud_shadow_fraction"],
        },
        "thresholds": {
            "min_overlap_pixels": args.min_overlap_pixels,
            "max_js_distance": args.max_js_distance,
            "max_clipping_fraction": args.max_clipping_fraction,
            "max_registration_rmse_pixels": args.max_registration_rmse_pixels,
            "max_cloud_shadow_fraction": args.max_cloud_shadow_fraction,
        },
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "comparability_report.json", report)
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, ValueError, rasterio.errors.RasterioError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2) from error