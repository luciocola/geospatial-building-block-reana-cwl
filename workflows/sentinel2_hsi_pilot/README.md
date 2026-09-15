# REANA + CWL Pilot Workflow

This pilot demonstrates an operational multi-step processing chain:

1. Sentinel-2 ingestion metadata capture
2. HSI preprocessing manifest generation
3. HSI semantic classification output generation
4. Provenance packaging with SHA-256 evidence

The workflow is intentionally lightweight for proposal and integration testing. It focuses on:

- Portability: workflow and steps are defined in CWL.
- Provenance: each step emits structured metadata, while REANA records runtime evidence.
- Operational maturity: deterministic outputs and explicit step interfaces support reproducibility.

The workflow also emits an OSPD-aligned PROV profile JSON that references registered process-type URIs.

## Files

- `workflow.cwl`: Main CWL workflow.
- `steps/*.cwl`: Step-level command tools.
- `scripts/*.py`: Executable Python implementations used by CWL steps.
- `examples/workflow-inputs.yml`: Example inputs.
- `reana.yaml`: REANA workflow descriptor.

## Run with cwltool

From this folder:

```bash
python3 -m pip install cwltool
cwltool workflow.cwl examples/workflow-inputs.yml
```

Expected artifacts:

- `hsi_classification.geojson`
- `stac_item.json`
- `provenance_bundle.json`
- `workflow_prov_profile.json`

## Run on REANA

Prerequisites:

- REANA cluster access
- `reana-client` configured (`reana-client ping` succeeds)

From this folder:

```bash
reana-client create -n dqcv-reana-pilot
reana-client upload -n dqcv-reana-pilot
reana-client start -n dqcv-reana-pilot
reana-client logs -n dqcv-reana-pilot -f
reana-client list-files -n dqcv-reana-pilot
reana-client download -n dqcv-reana-pilot provenance_bundle.json
```

## Provenance Mapping Notes

- Workflow-level provenance is emitted in `provenance_bundle.json`.
- OSPD profile-compatible provenance is emitted in `workflow_prov_profile.json`.
- REANA augments this with execution provenance such as runtime logs, job metadata, and environment details.
- Together these artifacts support mapping processing activities to provenance profile requirements.

Registered process-type URIs used by this workflow:

- `https://example.org/ospd/2026/process-types/data-ingestion`
- `https://example.org/ospd/2026/process-types/radiometric-preprocessing`
- `https://example.org/ospd/2026/process-types/image-classification`
