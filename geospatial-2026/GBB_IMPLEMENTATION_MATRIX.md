# GBB Implementation Matrix (Current Workspace)

## Scope

This matrix maps implemented artefacts to GBB capabilities and implementation readiness.

## Capability Coverage

### Core Conformance and STAC Navigation

Implemented:

- [Core requirements](gbb-core/description.md), evidence schema and example.
- Kernel job Catalogs with Item backlinks and authenticated navigation.
- Relative writer `self` links and canonical `self`/`root` links in served Items.
- STAC navigation and producer regression tests in
  `geospatial-processes-kernel/service/test_stac_outputs.py`.

Status: Implemented locally; not independent standards certification.

### Optional Provenance Conformance

- [Provenance conformance draft](gbb-provenance/description.md).
- Existing profile example validated with date-time format checking.
- Producer normalization, execution identity and semantic validation remain.

Status: Draft; not advertised by the kernel.

### Generic Provenance Building Block

Implemented:

- `provenance-profile/schema/provenance-profile.schema.json`
- `provenance-profile/context/osdp-prov-context.jsonld`
- `provenance-profile/examples/workflow-provenance-example.json`
- `provenance-profile/bblock.json`

Status: Implemented (pilot-grade).

### Workflow Profiling

Implemented:

- Workflow emits profile-compatible provenance with process-type references:
  - `workflows/sentinel2_hsi_pilot/scripts/package_provenance.py`
  - output `workflow_prov_profile.json`

Status: Implemented.

### Process-Type Register Setup

Implemented:

- Register records payload:
  - `process-type-register/records/process-types-records.json`
- Governance model:
  - `process-type-register/governance/register-governance.md`
- DCAT catalog representation:
  - `process-type-register/dcat/process-types-catalog.json`

Status: Implemented (prototype, file-based).

### Register Population

Implemented:

- Initial process-type entries (5 entries)
- Federation mappings with required relation types:
  - `process-type-register/mappings/federation-mappings.json`

Status: Implemented.

### Documentation

Implemented:

- `geospatial-2026/README.md`
- [GBB_IMPLEMENTATION_MATRIX.md](GBB_IMPLEMENTATION_MATRIX.md)
- Updated shared workflow README files

Status: Implemented.

### Building Blocks to Profile Documentation (optional)

Partially implemented:

- Building-block metadata and profile documentation included.
- No automated static doc generation pipeline yet.

Status: Partial.

## Implementation Readiness

### Workflow Profiling

Status: Ready (pilot-grade)

Evidence:

- Independent workflow profiling artefacts under `workflows/sentinel2_hsi_pilot` and `geospatial-2026/provenance-profile`.

### Register Implementation

Status: Partially ready

Evidence:

- Register model/governance/mappings implemented as prototype files.
- Remaining gap: deploy as running OGC API - Records profile endpoint and handover-ready runtime.

### OGC API Processes Profiling

Status: Ready for demonstration

Evidence:

- OGC API Processes profiling example:
  - `ogc-api-processes-profile/examples/execution-metadata-example.json`
  - `ogc-api-processes-profile/schema/ogc-process-execution-metadata.schema.json`

## Remaining Work for Publication Readiness

1. Deploy process-type register as a running OGC API - Records service.
2. Add automated validation scripts for profile schema and example conformance.
3. Add publication-ready report snippets in AsciiDoc/Metanorma format.
