# Geospatial Building Block (GBB) Package

This package implements the minimum Geospatial Building Block artefacts on top of the shared REANA/CWL approach.

## Capability Coverage

- Generic Provenance Building Block:
  - `provenance-profile/` with schema, JSON-LD context, examples, and building-block metadata.
- Workflow Profiling:
  - `workflows/sentinel2_hsi_pilot` emits provenance with controlled process-type references.
- Process-Type Register Setup:
  - `process-type-register/` includes register model, governance, OGC API Records-like payload, and DCAT catalog.
- Register Population:
  - Initial process-type entries + federation mappings (`exactMatch`, `closeMatch`, `broader`, `narrower`).
- Documentation and publication readiness:
  - This README plus per-package metadata and examples.
- OGC API Processes profiling:
  - `ogc-api-processes-profile/examples/` with input provenance references and registered process types.
- Geospatial Processes facade kernel:
  - `geospatial-processes-kernel/` exposing `/processes` and `/jobs` plus `/kernel/building-blocks` to bind execution, provenance profile, and process-type register semantics.
- Operational trust-enabled BB model:
  - `operational-trust-bbs/` defining executable Building Blocks for data certificates, process contracts, execution validation, and result certificates.
- GBB core conformance class:
  - `gbb-core/` defines `https://luciocola.github.io/geospatial-building-block/1.0/conf/core`.
  - The class builds on (`dependsOn`) only the OGC building blocks that the services actually satisfy: `ogc.ogc-utils.json-link`, `ogc.api.common.landingPage` and `ogc.api.common.confClasses`.
  - Requirements, schema and example are in that directory. The executable abstract tests are in `geospatial-processes-kernel/service/test_gbb_conformance.py`.

## GBB Core Conformance

Both services return the JSON landing page at `GET /`, including `service-desc` and `service-doc` links. Browsers (`Accept: text/html`) are still redirected to Swagger.

STAC workflow outputs include a relative `self` link. When an Item is retrieved
through the kernel, its `self` and `root` links point to the served Item and the
authenticated STAC Catalog at `/jobs/{jobId}/catalog`. Stored artifacts are not
rewritten, and non-STAC downloads retain their existing behavior.

The [provenance conformance class](gbb-provenance/description.md) is a separate
draft. It is listed as a draft in the QGIS building-block catalog, not advertised
as implemented by `/conformance`. Existing provenance summaries still need
normalization and execution-linked validation. Liability remains optional.

The kernel `/conformance` lists Processes core, json and oas30, plus GBB core;
these declarations are not independent OGC certification. Run the local suites
in a test environment:

```bash
cd geospatial-processes-kernel/service
python -m pip install -r requirements-test.txt
python -m unittest test_gbb_conformance test_stac_outputs test_security
```

The [implementation matrix](GBB_IMPLEMENTATION_MATRIX.md) describes capability
coverage and remaining publication work.

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
