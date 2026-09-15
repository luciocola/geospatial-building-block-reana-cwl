#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HSI preprocessing manifest")
    parser.add_argument("--ingest-manifest", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    with open(args.ingest_manifest, "r", encoding="utf-8") as f:
        ingest = json.load(f)

    output = {
        "run_id": args.run_id,
        "step": "preprocess_hsi",
        "process_type_uri": "https://example.org/ospd/2026/process-types/radiometric-preprocessing",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_granules": ingest.get("selected_granules", []),
        "processing_chain": [
            "toa_reflectance_normalization",
            "atmospheric_correction",
            "band_alignment"
        ],
        "hsi_cube": {
            "id": f"hsi-cube-{args.run_id}",
            "bands": 180,
            "dtype": "float32"
        },
        "software": {
            "tool": "preprocess_hsi.py",
            "version": "0.1.0"
        }
    }

    out_path = os.path.join(args.output_dir, "hsi_cube_manifest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
