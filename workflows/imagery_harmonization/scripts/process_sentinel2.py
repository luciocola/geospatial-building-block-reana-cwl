#!/usr/bin/env python3
"""Create the reference grid and histogram from a georeferenced Sentinel-2 RGB raster."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.warp import calculate_default_transform, reproject

from raster_contracts import (
    NODATA,
    grid_contract,
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
    parser.add_argument("--source-rgb", required=True)
    parser.add_argument("--target-crs", required=True)
    parser.add_argument("--target-resolution", required=True, type=float)
    parser.add_argument("--input-scale", type=float, default=10000.0)
    parser.add_argument("--method", choices=("bicubic-demo", "torchscript"), default="bicubic-demo")
    parser.add_argument("--model")
    parser.add_argument("--model-card")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def read_source(path: str, scale: float) -> tuple[np.ndarray, np.ndarray, dict]:
    if scale <= 0:
        raise ValueError("input-scale must be greater than zero")
    with rasterio.open(path) as source:
        if source.count < 3 or source.crs is None:
            raise ValueError("source-rgb must contain at least three bands and a CRS")
        data = source.read((1, 2, 3), out_dtype="float32") / scale
        mask = source.dataset_mask() > 0
        metadata = {
            "crs": source.crs,
            "transform": source.transform,
            "width": source.width,
            "height": source.height,
            "bounds": source.bounds,
        }
    return data, mask, metadata


def reproject_array(
    data: np.ndarray,
    mask: np.ndarray,
    source: dict,
    target_crs: str,
    resolution: float | None,
    resampling: Resampling,
) -> tuple[np.ndarray, np.ndarray, Affine]:
    transform, width, height = calculate_default_transform(
        source["crs"],
        target_crs,
        source["width"],
        source["height"],
        *source["bounds"],
        resolution=resolution,
    )
    destination = np.full((3, height, width), NODATA, dtype="float32")
    for band in range(3):
        reproject(
            data[band],
            destination[band],
            src_transform=source["transform"],
            src_crs=source["crs"],
            src_nodata=NODATA,
            dst_transform=transform,
            dst_crs=target_crs,
            dst_nodata=NODATA,
            resampling=resampling,
        )
    destination_mask = np.zeros((height, width), dtype="uint8")
    reproject(
        mask.astype("uint8"),
        destination_mask,
        src_transform=source["transform"],
        src_crs=source["crs"],
        dst_transform=transform,
        dst_crs=target_crs,
        resampling=Resampling.nearest,
    )
    return destination, destination_mask > 0, transform


def torchscript_super_resolve(
    data: np.ndarray,
    mask: np.ndarray,
    model_path: str,
    target_resolution: float,
    base_transform: Affine,
) -> tuple[np.ndarray, np.ndarray, Affine]:
    import torch
    import torch.nn.functional as functional

    model = torch.jit.load(model_path, map_location="cpu")
    model.eval()
    tensor = torch.from_numpy(np.where(mask[np.newaxis, :, :], data, 0.0)).unsqueeze(0)
    with torch.inference_mode():
        output = model(tensor)
    if isinstance(output, (tuple, list)):
        output = output[0]
    if output.ndim != 4 or output.shape[0] != 1 or output.shape[1] != 3:
        raise ValueError("TorchScript model must return a [1, 3, height, width] tensor")
    result = output.squeeze(0).detach().cpu().numpy().astype("float32")
    scale_y = result.shape[1] / data.shape[1]
    scale_x = result.shape[2] / data.shape[2]
    if scale_x <= 1 or scale_y <= 1:
        raise ValueError("TorchScript model output must be larger than its input")
    output_transform = base_transform * Affine.scale(1.0 / scale_x, 1.0 / scale_y)
    if abs(abs(output_transform.a) - target_resolution) > target_resolution * 0.02:
        raise ValueError("Model scale does not produce the requested target resolution")
    resized_mask = functional.interpolate(
        torch.from_numpy(mask.astype("float32"))[None, None],
        size=result.shape[1:],
        mode="nearest",
    )[0, 0].numpy() > 0.5
    return np.clip(result, 0.0, 1.0), resized_mask, output_transform


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data, mask, source = read_source(args.source_rgb, args.input_scale)

    model_sha = None
    if args.method == "torchscript":
        if not args.model or not args.model_card:
            raise ValueError("torchscript method requires --model and --model-card")
        base_data, base_mask, base_transform = reproject_array(
            data, mask, source, args.target_crs, None, Resampling.bilinear
        )
        result, result_mask, transform = torchscript_super_resolve(
            base_data, base_mask, args.model, args.target_resolution, base_transform
        )
        model_sha = sha256(args.model)
    else:
        result, result_mask, transform = reproject_array(
            data, mask, source, args.target_crs, args.target_resolution, Resampling.cubic_spline
        )

    result_mask &= valid_mask(result)
    crs = rasterio.crs.CRS.from_user_input(args.target_crs)
    raster_path = output_dir / "sentinel2_harmonized.tif"
    histogram_path = output_dir / "reference_histogram.json"
    grid_path = output_dir / "target_grid.json"
    quality_path = output_dir / "sentinel2_quality.json"
    stac_path = output_dir / "sentinel2_stac_item.json"
    provenance_path = output_dir / "sentinel2_provenance.json"

    write_cog(raster_path, result, result_mask, crs, transform)
    write_json(histogram_path, histogram_profile(result, result_mask))
    write_json(grid_path, grid_contract(crs, transform, result.shape[2], result.shape[1]))
    quality = {
        "run_id": args.run_id,
        "valid_pixel_count": int(result_mask.sum()),
        "nodata_fraction": float(1.0 - result_mask.mean()),
        "method": args.method,
        "passed": bool(result_mask.any()),
        "limitations": [
            "The output is a derived interpretation product and does not acquire true optical resolution."
        ],
    }
    write_json(quality_path, quality)
    item = stac_item(
        f"sentinel2-reference-{args.run_id}",
        raster_path,
        quality_path,
        crs,
        transform,
        result.shape[2],
        result.shape[1],
        {
            "platform": "sentinel-2",
            "processing:level": "L2A-derived",
            "processing:software": {"process_sentinel2.py": "1.0.0"},
            "processing:method": args.method,
            "gsd": args.target_resolution,
        },
    )
    item["assets"]["histogram"] = {
        "href": histogram_path.name,
        "type": "application/json",
        "roles": ["metadata"],
    }
    item["assets"]["target_grid"] = {
        "href": grid_path.name,
        "type": "application/json",
        "roles": ["metadata"],
    }
    write_json(stac_path, item)
    write_json(
        provenance_path,
        {
            "run_id": args.run_id,
            "timestamp_utc": utc_now(),
            "activity": "sentinel2-reference-preparation",
            "process_type_uri": "https://example.org/ospd/2026/process-types/geometric-correction",
            "inputs": {"source_rgb": args.source_rgb, "sha256": sha256(args.source_rgb)},
            "algorithm": {
                "method": args.method,
                "target_crs": args.target_crs,
                "target_resolution": args.target_resolution,
                "model": args.model,
                "model_sha256": model_sha,
                "model_card": args.model_card,
            },
            "outputs": {
                path.name: sha256(path)
                for path in (raster_path, histogram_path, grid_path, quality_path, stac_path)
            },
        },
    )
    return 0 if quality["passed"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, rasterio.errors.RasterioError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2) from error