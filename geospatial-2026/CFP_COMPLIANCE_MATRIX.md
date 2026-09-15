# OSPD 2026 CFP Compliance Matrix (Current Workspace)

## Scope

This matrix maps implemented artefacts to OSPD 2026 activities and roles.

## Activity Coverage

### Activity 1: Generic Provenance Building Block

Implemented:

- `provenance-profile/schema/provenance-profile.schema.json`
- `provenance-profile/context/osdp-prov-context.jsonld`
- `provenance-profile/examples/workflow-provenance-example.json`
- `provenance-profile/bblock.json`

Status: Implemented (pilot-grade).

### Activity 2: Workflow Profiling

Implemented:

- Workflow emits profile-compatible provenance with process-type references:
  - `workflows/sentinel2_hsi_pilot/scripts/package_provenance.py`
  - output `workflow_prov_profile.json`

Status: Implemented.

### Activity 3: Process-Type Register Setup

Implemented:

- Register records payload:
  - `process-type-register/records/process-types-records.json`
- Governance model:
  - `process-type-register/governance/register-governance.md`
- DCAT catalog representation:
  - `process-type-register/dcat/process-types-catalog.json`

Status: Implemented (prototype, file-based).

### Activity 4: Register Population

Implemented:

- Initial process-type entries (5 entries)
- Federation mappings with required relation types:
  - `process-type-register/mappings/federation-mappings.json`

Status: Implemented.

### Activity 5: Documentation

Implemented:

- `geospatial-2026/README.md`
- `CFP_COMPLIANCE_MATRIX.md`
- Updated shared workflow README files

Status: Implemented.

### Activity 6: Building Blocks to Profile Documentation (optional)

Partially implemented:

- Building-block metadata and profile documentation included.
- No automated static doc generation pipeline yet.

Status: Partial.

## Role Readiness

### D100 Workflow Profiler

Status: Ready (pilot-grade)

Evidence:

- Independent workflow profiling artefacts under `workflows/sentinel2_hsi_pilot` and `geospatial-2026/provenance-profile`.

### D110 Register Implementer

Status: Partially ready

Evidence:

- Register model/governance/mappings implemented as prototype files.
- Remaining gap: deploy as running OGC API - Records profile endpoint and handover-ready runtime.

### D120 OGC API Processes Profiler

Status: Ready for demonstration

Evidence:

- OGC API Processes profiling example:
  - `ogc-api-processes-profile/examples/execution-metadata-example.json`
  - `ogc-api-processes-profile/schema/ogc-process-execution-metadata.schema.json`

## Remaining Work for Full Bid Strength

1. Deploy process-type register as a running OGC API - Records service.
2. Add automated validation scripts for profile schema and example conformance.
3. Add publication-ready report snippets in AsciiDoc/Metanorma format.
