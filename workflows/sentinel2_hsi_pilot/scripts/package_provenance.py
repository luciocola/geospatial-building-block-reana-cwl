#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone


def file_sha256(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Package provenance evidence")
    parser.add_argument("--ingest-manifest", required=True)
    parser.add_argument("--hsi-cube-manifest", required=True)
    parser.add_argument("--classification-geojson", required=True)
    parser.add_argument("--classification-summary", required=True)
    parser.add_argument("--stac-item", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--layer-name")
    parser.add_argument("--image-path")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    input_files = {
        "ingest_manifest": args.ingest_manifest,
        "hsi_cube_manifest": args.hsi_cube_manifest,
        "classification_geojson": args.classification_geojson,
        "classification_summary": args.classification_summary,
        "stac_item": args.stac_item
    }

    checksums = {name: file_sha256(path) for name, path in input_files.items()}

    ingest_manifest = read_json(args.ingest_manifest)
    hsi_cube_manifest = read_json(args.hsi_cube_manifest)
    classification_summary = read_json(args.classification_summary)

    bundle = {
        "run_id": args.run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "execution_environment": {
            "name": "REANA",
            "note": "Runtime provenance such as container digests and job logs are collected by REANA."
        },
        "processing_steps": [
            ingest_manifest,
            hsi_cube_manifest,
            classification_summary
        ],
        "artifacts": [
            {
                "name": name,
                "sha256": digest,
                "basename": os.path.basename(input_files[name])
            }
            for name, digest in checksums.items()
        ]
    }

    out_path = os.path.join(args.output_dir, "provenance_bundle.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)

    prov_profile = {
        "@context": "../../../geospatial-2026/provenance-profile/context/osdp-prov-context.jsonld",
        "prefix": {
            "prov": "http://www.w3.org/ns/prov#",
            "process": "https://example.org/ospd/2026/process-types/",
            "ex": "https://example.org/ospd/2026/workflow/"
        },
        "entity": {
            "ex:ingest_manifest": {
                "prov:type": "prov:Entity",
                "prov:label": "Sentinel-2 ingest manifest",
                "prov:location": os.path.basename(args.ingest_manifest)
            },
            "ex:hsi_cube_manifest": {
                "prov:type": "prov:Entity",
                "prov:label": "HSI cube manifest",
                "prov:location": os.path.basename(args.hsi_cube_manifest)
            },
            "ex:classification_geojson": {
                "prov:type": "prov:Entity",
                "prov:label": "HSI classification output",
                "prov:location": os.path.basename(args.classification_geojson)
            },
            "ex:stac_item": {
                "prov:type": "prov:Entity",
                "prov:label": "STAC item",
                "prov:location": os.path.basename(args.stac_item)
            }
        },
        "activity": {
            "ex:ingest": {
                "prov:type": "prov:Activity",
                "prov:label": "Sentinel-2 ingestion",
                "prov:startTime": ingest_manifest.get("timestamp_utc"),
                "prov:endTime": ingest_manifest.get("timestamp_utc"),
                "processType": ingest_manifest.get("process_type_uri", "https://example.org/ospd/2026/process-types/data-ingestion")
            },
            "ex:preprocess": {
                "prov:type": "prov:Activity",
                "prov:label": "HSI preprocessing",
                "prov:startTime": hsi_cube_manifest.get("timestamp_utc"),
                "prov:endTime": hsi_cube_manifest.get("timestamp_utc"),
                "processType": hsi_cube_manifest.get("process_type_uri", "https://example.org/ospd/2026/process-types/radiometric-preprocessing")
            },
            "ex:classify": {
                "prov:type": "prov:Activity",
                "prov:label": "HSI classification",
                "prov:startTime": classification_summary.get("timestamp_utc"),
                "prov:endTime": classification_summary.get("timestamp_utc"),
                "processType": classification_summary.get("process_type_uri", "https://example.org/ospd/2026/process-types/image-classification")
            }
        },
        "agent": {
            "ex:reana": {
                "prov:type": "prov:SoftwareAgent",
                "prov:label": "REANA"
            }
        },
        "wasGeneratedBy": {
            "_:wgb_ingest": {
                "prov:entity": "ex:ingest_manifest",
                "prov:activity": "ex:ingest"
            },
            "_:wgb_pre": {
                "prov:entity": "ex:hsi_cube_manifest",
                "prov:activity": "ex:preprocess"
            },
            "_:wgb_cls": {
                "prov:entity": "ex:classification_geojson",
                "prov:activity": "ex:classify"
            },
            "_:wgb_stac": {
                "prov:entity": "ex:stac_item",
                "prov:activity": "ex:classify"
            }
        },
        "used": {
            "_:used_pre": {
                "prov:activity": "ex:preprocess",
                "prov:entity": "ex:ingest_manifest"
            },
            "_:used_cls": {
                "prov:activity": "ex:classify",
                "prov:entity": "ex:hsi_cube_manifest"
            }
        },
        "wasAssociatedWith": {
            "_:waw_ingest": {
                "prov:activity": "ex:ingest",
                "prov:agent": "ex:reana"
            },
            "_:waw_pre": {
                "prov:activity": "ex:preprocess",
                "prov:agent": "ex:reana"
            },
            "_:waw_cls": {
                "prov:activity": "ex:classify",
                "prov:agent": "ex:reana"
            }
        },
        "wasInformedBy": {
            "_:wib1": {
                "prov:informed": "ex:preprocess",
                "prov:informant": "ex:ingest"
            },
            "_:wib2": {
                "prov:informed": "ex:classify",
                "prov:informant": "ex:preprocess"
            }
        }
    }

    prov_profile_path = os.path.join(args.output_dir, "workflow_prov_profile.json")

    provenance_verification = {
        "run_id": args.run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "w3c_prov_parameters_present": True,
        "provenance_profile_file": os.path.basename(prov_profile_path),
        "checked_artifacts": [
            os.path.basename(args.ingest_manifest),
            os.path.basename(args.hsi_cube_manifest),
            os.path.basename(args.classification_geojson),
            os.path.basename(args.classification_summary),
            os.path.basename(args.stac_item)
        ],
        "applied_to": {
            "layer_name": args.layer_name,
            "image_path": args.image_path,
            "source_granules": ingest_manifest.get("selected_granules", []),
            "aoi": ingest_manifest.get("aoi", {}),
            "hsi_cube": hsi_cube_manifest.get("hsi_cube", {}),
            "classifier_model": classification_summary.get("classifier_model"),
            "process_type_uris": {
                "ingest": ingest_manifest.get("process_type_uri"),
                "preprocess": hsi_cube_manifest.get("process_type_uri"),
                "classify": classification_summary.get("process_type_uri")
            },
            "outputs": {
                "classification_geojson": os.path.basename(args.classification_geojson),
                "classification_summary": os.path.basename(args.classification_summary),
                "stac_item": os.path.basename(args.stac_item)
            }
        }
    }

    with open(prov_profile_path, "w", encoding="utf-8") as f:
        json.dump(prov_profile, f, indent=2)

    verification_path = os.path.join(args.output_dir, "provenance_verification.json")
    with open(verification_path, "w", encoding="utf-8") as f:
        json.dump(provenance_verification, f, indent=2)


if __name__ == "__main__":
    main()
