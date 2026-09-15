#!/usr/bin/env python3
import argparse
import json
import sys


REQUIRED_PROFILE_KEYS = [
    "entity",
    "activity",
    "agent",
    "wasGeneratedBy",
    "used",
    "wasAssociatedWith",
    "wasInformedBy",
]


def read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fail(message: str) -> int:
    print(f"[FAIL] {message}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify W3C PROV fields and applied-to summary")
    parser.add_argument("--workflow-prov-profile", required=True)
    parser.add_argument("--provenance-verification", required=True)
    parser.add_argument("--classification-summary", required=True)
    parser.add_argument("--layer-name", help="Optional layer name to report in the provenance summary")
    parser.add_argument("--image-path", help="Optional image path to report in the provenance summary")
    args = parser.parse_args()

    profile = read_json(args.workflow_prov_profile)
    verification = read_json(args.provenance_verification)
    classification_summary = read_json(args.classification_summary)

    missing = [key for key in REQUIRED_PROFILE_KEYS if key not in profile]
    if missing:
        return fail("Missing PROV profile keys: " + ", ".join(missing))

    if not verification.get("w3c_prov_parameters_present"):
        return fail("Verification JSON does not confirm W3C PROV parameters")

    process_types = verification.get("applied_to", {}).get("process_type_uris", {})
    if not all(process_types.get(name) for name in ("ingest", "preprocess", "classify")):
        return fail("One or more process type URIs are missing from the provenance verification file")

    print("[OK] W3C PROV profile keys present")
    print("[OK] W3C PROV parameters confirmed in provenance_verification.json")
    print("[OK] Process types:")
    print(f"  ingest: {process_types.get('ingest')}")
    print(f"  preprocess: {process_types.get('preprocess')}")
    print(f"  classify: {process_types.get('classify')}")

    applied_to = verification.get("applied_to", {})
    granules = applied_to.get("source_granules", [])
    hsi_cube = applied_to.get("hsi_cube", {})
    outputs = applied_to.get("outputs", {})
    layer_name = args.layer_name or applied_to.get("layer_name")
    image_path = args.image_path or applied_to.get("image_path")

    print("[OK] Applied-to summary:")
    if layer_name:
        print(f"  layer name: {layer_name}")
    if image_path:
        print(f"  image path: {image_path}")
    print(f"  source granules: {', '.join(granules) if granules else 'none'}")
    print(f"  hsi cube id: {hsi_cube.get('id', 'unknown')}")
    print(f"  hsi cube bands: {hsi_cube.get('bands', 'unknown')}")
    print(f"  classifier model: {applied_to.get('classifier_model', 'unknown')}")
    print(f"  classification summary process type: {classification_summary.get('process_type_uri', 'unknown')}")
    print(f"  outputs: {', '.join(outputs.values()) if outputs else 'none'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
