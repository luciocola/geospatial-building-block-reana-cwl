#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Sentinel-2 ingestion manifest")
    parser.add_argument("--aoi-geojson", required=True)
    parser.add_argument("--acquisition-date", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    with open(args.aoi_geojson, "r", encoding="utf-8") as f:
        aoi = json.load(f)

    output = {
        "run_id": args.run_id,
        "step": "ingest_sentinel2",
        "process_type_uri": "https://example.org/ospd/2026/process-types/data-ingestion",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "acquisition_date": args.acquisition_date,
        "source": "Sentinel-2 L2A (simulated pilot)",
        "selected_granules": [
            "S2A_MSIL2A_20260710T101031_N0510_R022_T32TPR",
            "S2B_MSIL2A_20260710T101029_N0510_R022_T32TPR"
        ],
        "aoi": aoi,
        "software": {
            "tool": "ingest_sentinel2.py",
            "version": "0.1.0"
        }
    }

    out_path = os.path.join(args.output_dir, "sentinel2_ingest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
