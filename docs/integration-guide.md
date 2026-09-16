# Integration Guide for Plugin Teams

This guide explains how to consume shared workflows from multiple plugins.

## Recommended Pattern

- Plugin owns UI, local validation, and datasource adapters.
- Shared workspace owns CWL definitions and REANA descriptors.
- Data exchange uses stable file contracts (`geojson`, `json`, `tif`, etc.).

## Interface Contract Example

For `workflows/sentinel2_hsi_pilot`:

Inputs:

- `aoi_geojson` (File)
- `acquisition_date` (string)
- `classifier_model` (string)
- `run_id` (string)

Outputs:

- `hsi_classification.geojson`
- `stac_item.json`
- `provenance_bundle.json`

## Plugin Invocation Options

1. Local run with `cwltool` for development and offline testing.
2. Remote execution on REANA for operational provenance capture.

Recommended launcher commands from shared workspace root:

```bash
python3 scripts/run_workflow.py --backend cwltool
python3 scripts/run_workflow.py --backend reana --reana-name-prefix plugin-run
```

To invoke with plugin-generated inputs:

```bash
python3 scripts/run_workflow.py \
	--backend cwltool \
	--workflow-dir workflows/sentinel2_hsi_pilot \
	--inputs /absolute/path/from/plugin/runtime-inputs.yml
```

## Provenance Alignment

- CWL step artifacts provide deterministic, machine-readable evidence.
- REANA provides runtime provenance (jobs, logs, environments, outputs).
- Combined outputs can be mapped to OGC/OSPD provenance profile requirements.

## Geospatial Imagery Harmonization Example

See [Sentinel-2 and DJI Harmonization Example](sentinel2-dji-harmonization-example.md) for a two-workflow design covering orthorectification, Sentinel-2 AI super-resolution, DJI downsampling, robust histogram matching, common-grid validation, and provenance.

## QGIS EDI Integration Boundary

The QGIS EDI source tree is a QGIS fork and currently has no distinct EDI workflow/provider implementation. The recommended adapter is documented in [integrations/qgis_edi](../integrations/qgis_edi/README.md). It creates a context-specific logical contract from a QGIS layer and selected Processing parameters, then selects among:

- local `cwltool` for offline execution;
- the protected Geospatial Building Block kernel on port `8016`;
- the Process-Type Register on port `8015`;
- the UMM STAC API on port `18000` for health/catalog integration only;
- REANA and ODM/NodeODM for operational remote execution and raw DJI photogrammetry.

The current Docker inspection found no running containers because Docker Desktop was unavailable. The adapter therefore performs service preflight and supports offline fallback instead of assuming these endpoints are live.
