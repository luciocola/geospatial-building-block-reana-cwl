# REANA CWL Shared Workspace

This workspace centralizes reusable REANA/CWL workflows for multiple plugins.

> **Pilot status:** This is not a hardened multi-tenant service. Read [SECURITY.md](SECURITY.md) before deployment. Source and documentation are licensed under [Apache License 2.0](LICENSE); see [NOTICE](NOTICE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Implemented Geospatial Building Block

This repository implements a REANA/CWL-based **Geospatial Building Block** for reusable, provenance-ready geospatial processing. It combines executable CWL workflows, process contracts, interface bindings, quality validation, STAC outputs, and W3C PROV evidence so QGIS plugins and other clients can use the same processing capability.

The Building Block evolves the role of metadata for dynamic environments. Metadata remains context-dependent and is not forced into one universal fixed schema. Instead, each execution dynamically creates a machine-readable contract that logically represents the selected data, process, parameters, outputs, and context-specific metadata. The kernel harmonizes that evolving contract through stable minimum semantics, typed outputs, validation behavior, and evidence requirements.

In short:

```text
context-dependent metadata
	-> dynamically created data/process contract
	-> harmonized kernel semantics and evidence
	-> executable REANA/CWL result
```

The implemented Sentinel-2/DJI example demonstrates this model with common-grid reprojection, optional AI super-resolution, DJI downsampling, histogram harmonization, comparability gates, STAC Items, and provenance artifacts. See [the imagery harmonization workflow](workflows/imagery_harmonization/README.md) and [the contract architecture](docs/sentinel2-dji-harmonization-example.md).

## Goals

- Keep workflow definitions independent from any single plugin.
- Reuse common CWL pipelines across geospatial processing plugins.
- Standardize provenance-ready execution with REANA.

## Structure

- `workflows/`: reusable workflow packages
- `docs/`: guidance for contributors and plugin integrators

Current workflow package:

- `workflows/sentinel2_hsi_pilot`
- `workflows/imagery_harmonization` (executable Sentinel-2/DJI COG and comparability example)

Geospatial 2026 alignment package:

- `geospatial-2026/`

## Quick Start

Run with cwltool:

```bash
python3 scripts/run_workflow.py --backend cwltool
```

Run with REANA:

```bash
python3 scripts/run_workflow.py --backend reana --reana-name-prefix s2-hsi-pilot
```

To run a different shared workflow package:

```bash
python3 scripts/run_workflow.py \
	--backend cwltool \
	--workflow-dir workflows/sentinel2_hsi_pilot \
	--inputs examples/workflow-inputs.yml
```

Optional dry-run mode (prints commands only):

```bash
python3 scripts/run_workflow.py --backend reana --dry-run
```

## Reusing in Other Plugins

1. Keep plugin-specific adapters in each plugin.
2. Keep workflow specs and step contracts in this shared workspace.
3. Pass plugin outputs as CWL inputs, and consume workflow outputs back in plugin logic.

See `docs/integration-guide.md`.

QGIS EDI integration boundary:

- `integrations/qgis_edi/` — dynamic contract adapter and service-mode design for QGIS Processing.

## Geospatial 2026 Artefacts

- Provenance profile package: `geospatial-2026/provenance-profile/`
- Process-type register prototype: `geospatial-2026/process-type-register/`
- OGC API Processes profiling example: `geospatial-2026/ogc-api-processes-profile/`
- Operational trust-enabled Building Blocks: `geospatial-2026/operational-trust-bbs/`
- Sentinel-2/DJI harmonization Building Block example: `docs/sentinel2-dji-harmonization-example.md`
- Sentinel-2/DJI architecture slides: `docs/sentinel2-dji-harmonization-architecture.pptx`
- Refreshed Building Block explanation deck: `docs/geospatial-building-block-harmonization-v2.pptx`

Regenerate the presentation with:

```bash
python3 scripts/generate_harmonization_slides.py
```

Workflow outputs now include:

- `provenance_bundle.json`
- `workflow_prov_profile.json`
