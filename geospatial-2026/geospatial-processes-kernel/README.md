# Geospatial Processes Facade Kernel

This package exposes the shared REANA/CWL workflow as a **geospatial processes facade** and defines that facade as a lightweight **Geospatial Building Blocks kernel**.

## Why this kernel

The facade binds together:

- process execution interface (`/processes`, `/jobs/*`)
- provenance contract (W3C PROV profile artifacts)
- process-type semantics (register mappings)
- OGC API Processes profiling artifacts

Kernel metadata is published in:

- `kernel/bblock-kernel.json`

## Interface bindings

A Building Block should be usable from whichever interface style a given workflow step actually needs, depending on the
data/service available, rather than assuming a single fixed API. This kernel declares its supported bindings in
`kernel/bblock-kernel.json` (`interfaceBindings`) and backs them with running endpoints:

- **REST** — plain HTTP/JSON (`/jobs/*`, `/kernel/*`) for generic polling/integration.
- **OGC API - Processes** — `/processes`, `/jobs/*` execution model.
- **OGC API - Records-like** — process-type register lookups (`process-type-register` service).
- **OpenAPI** — `/swagger.json` machine-readable description of every operation above, for client generation.
- **openEO** — `/openeo/*`, exposing the same execution kernel as an openEO-compatible process/batch job, so it can be
  driven from ESA's [openEO Platform](https://openeo.cloud) or any other openEO back-end/client (e.g. Copernicus Data
  Space Ecosystem). See `GET /openeo/processes` for the process description and `POST /openeo/jobs` +
  `POST /openeo/jobs/{job_id}/results` to create and start a batch job.

Each entry in `buildingBlocks[]` lists its own `interfaceBindings`, so orchestrators can select bindings per Building
Block rather than per whole kernel. Each entry also declares a `standards` list, and every standard can carry its own
`conformanceClasses` with machine-readable URIs. This lets one geospatial building block use several standards without
flattening their conformance requirements into one list.

## Run locally

From `reana_cwl_workflows` root:

```bash
python3 -m uvicorn app:app \
  --app-dir geospatial-2026/geospatial-processes-kernel/service \
  --host 127.0.0.1 --port 8016
```

## Key endpoints

- `GET /` landing page
- `GET /conformance`
- `GET /processes`
- `GET /processes/sentinel2-hsi-pilot`
- `POST /processes/sentinel2-hsi-pilot/execution`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/results`
- `GET /kernel`
- `GET /kernel/building-blocks`
- `GET /kernel/building-blocks/{block_id}`
- `GET /swagger.json` exported OpenAPI document
- `GET /docs` Swagger UI
- `GET /redoc` ReDoc UI

## Execute example

```bash
curl -sS -X POST http://127.0.0.1:8016/processes/sentinel2-hsi-pilot/execution \
  -H 'Content-Type: application/json' \
  -d '{
    "backend": "cwltool",
    "layer_name": "roads_main",
    "image_path": "/data/sentinel2/B04.tif",
    "inputs": {
      "aoi_geojson": {"href": "workflows/sentinel2_hsi_pilot/examples/aoi.geojson"},
      "acquisition_date": "2026-07-10",
      "classifier_model": "hsi-baseline-v1"
    }
  }'
```

Then poll:

```bash
curl -sS http://127.0.0.1:8016/jobs/<job_id> | jq
curl -sS http://127.0.0.1:8016/jobs/<job_id>/results | jq
```

## Notes

- `backend=cwltool` executes locally and returns output file paths.
- `backend=reana` submits through `scripts/run_workflow.py` with `--backend reana`; results are not pulled back automatically by this facade.
