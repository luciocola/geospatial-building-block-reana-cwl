# OSPD 2026 Alignment Package

This package implements the minimum artefacts required to align the shared REANA/CWL approach with OSPD 2026 CFP activities.

## Coverage by CFP Activity

- Activity 1 (Generic Provenance Building Block):
  - `provenance-profile/` with schema, JSON-LD context, examples, and building-block metadata.
- Activity 2 (Workflow Profiling):
  - `workflows/sentinel2_hsi_pilot` emits provenance with controlled process-type references.
- Activity 3 (Process-Type Register Setup):
  - `process-type-register/` includes register model, governance, OGC API Records-like payload, and DCAT catalog.
- Activity 4 (Register Population):
  - Initial process-type entries + federation mappings (`exactMatch`, `closeMatch`, `broader`, `narrower`).
- Activity 5/6 (Documentation and publication readiness):
  - This README plus per-package metadata and examples.
- D120 support (OGC API Processes profiler):
  - `ogc-api-processes-profile/examples/` with input provenance references and registered process types.
- Geospatial Processes facade kernel:
  - `geospatial-processes-kernel/` exposing `/processes` and `/jobs` plus `/kernel/building-blocks` to bind execution, provenance profile, and process-type register semantics.
- Operational trust-enabled BB model:
  - `operational-trust-bbs/` defining executable Building Blocks for data certificates, process contracts, execution validation, and result certificates.

## Liability/Claims Reuse

This package reuses the same provenance style used in the STAC liability/claims extension:

- PROV-JSON structures (`entity`, `activity`, `agent`, relations)
- JSON-LD context and W3C PROV namespaces
- OGC Building Block metadata style (`bblock.json`)

## Quick Validation

```bash
cd workflows/sentinel2_hsi_pilot
python3 ../../scripts/run_workflow.py --backend cwltool
```

Then inspect:

- `provenance_bundle.json`
- `workflow_prov_profile.json`
- `provenance_verification.json`

To verify the W3C PROV fields and the applied-to summary explicitly, run:

```bash
cd workflows/sentinel2_hsi_pilot
python3 scripts/verify_provenance.py \
  --workflow-prov-profile .tmp_run/workflow_prov_profile.json \
  --provenance-verification .tmp_run/provenance_verification.json \
  --classification-summary .tmp_run/classification_summary.json

If you want the workflow itself to store a layer or image identifier in `provenance_verification.json`, pass the optional inputs `layer_name` and `image_path` when running the CWL workflow.

You can also pass a specific layer name or image path to have the checker print them in the summary:

```bash
python3 scripts/verify_provenance.py \
  --workflow-prov-profile .tmp_run/workflow_prov_profile.json \
  --provenance-verification .tmp_run/provenance_verification.json \
  --classification-summary .tmp_run/classification_summary.json \
  --layer-name roads_main \
  --image-path /data/sentinel2/B04.tif
```
```

## Full End-to-End Test

Run the complete smoke test from the OSPD package root:

```bash
cd reana_cwl_workflows/geospatial-2026
bash run_full_test.sh
```

This performs:

1. Python syntax compilation for workflow and register service helpers.
2. Workflow step execution into a temporary directory.
3. JSON Schema validation of the generated provenance profile.
4. Controlled-term and federation mapping checks.
5. Local OGC API register startup and endpoint smoke tests.

## Running Registry and OGC API Facade in Separate Docker Containers

From `reana_cwl_workflows/geospatial-2026`:

```bash
docker compose up --build
```

This starts two separate services:

- Process-type register API on `http://localhost:8015`
- OGC API Processes facade kernel (Swagger + execution facade) on `http://localhost:8016`

Swagger/OpenAPI endpoints:

- `http://localhost:8015/docs`
- `http://localhost:8015/swagger`
- `http://localhost:8015/swagger.json`
- `http://localhost:8016/docs`
- `http://localhost:8016/swagger`
- `http://localhost:8016/swagger.json`

## Operational Trust BB Documentation

For the revised BB concept enabling automatic workflow execution in a common space, see:

- `operational-trust-bbs/README.md`
