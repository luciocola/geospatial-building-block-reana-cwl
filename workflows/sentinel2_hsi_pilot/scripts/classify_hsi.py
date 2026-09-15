#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone


CLASSIFICATION_FEATURES = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "class_id": 1,
                "class_name": "flood-water",
                "confidence": 0.92
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[14.30, 40.81], [14.32, 40.81], [14.32, 40.83], [14.30, 40.83], [14.30, 40.81]]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "class_id": 2,
                "class_name": "damaged-infrastructure",
                "confidence": 0.87
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[14.33, 40.80], [14.34, 40.80], [14.34, 40.82], [14.33, 40.82], [14.33, 40.80]]]
            }
        }
    ]
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HSI classification outputs")
    parser.add_argument("--hsi-cube-manifest", required=True)
    parser.add_argument("--classifier-model", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    with open(args.hsi_cube_manifest, "r", encoding="utf-8") as f:
        cube = json.load(f)

    summary = {
        "run_id": args.run_id,
        "step": "classify_hsi",
        "process_type_uri": "https://example.org/ospd/2026/process-types/image-classification",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "classifier_model": args.classifier_model,
        "input_cube": cube.get("hsi_cube", {}),
        "class_distribution": {
            "flood-water": 0.38,
            "damaged-infrastructure": 0.21,
            "background": 0.41
        },
        "software": {
            "tool": "classify_hsi.py",
            "version": "0.1.0"
        }
    }

    stac_item = {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": f"pilot-hsi-{args.run_id}",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[14.30, 40.80], [14.34, 40.80], [14.34, 40.83], [14.30, 40.83], [14.30, 40.80]]]
        },
        "bbox": [14.30, 40.80, 14.34, 40.83],
        "properties": {
            "datetime": datetime.now(timezone.utc).isoformat(),
            "processing:facility": "reana",
            "processing:software": "classify_hsi.py",
            "processing:version": "0.1.0",
            "processing:process_type": "https://example.org/ospd/2026/process-types/image-classification",
            "ml:model_name": args.classifier_model,
            "ml:task": "semantic-segmentation"
        },
        "assets": {
            "classification": {
                "href": "hsi_classification.geojson",
                "type": "application/geo+json",
                "roles": ["data"]
            },
            "summary": {
                "href": "classification_summary.json",
                "type": "application/json",
                "roles": ["metadata"]
            }
        }
    }

    out_geojson = os.path.join(args.output_dir, "hsi_classification.geojson")
    out_summary = os.path.join(args.output_dir, "classification_summary.json")
    out_stac = os.path.join(args.output_dir, "stac_item.json")

    with open(out_geojson, "w", encoding="utf-8") as f:
        json.dump(CLASSIFICATION_FEATURES, f, indent=2)
    with open(out_summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open(out_stac, "w", encoding="utf-8") as f:
        json.dump(stac_item, f, indent=2)


if __name__ == "__main__":
    main()
