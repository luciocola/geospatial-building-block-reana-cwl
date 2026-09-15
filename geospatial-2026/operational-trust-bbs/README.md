# Operational Trust Building Blocks (OTBB)

This document defines an operational interpretation of OGC Building Blocks for automated workflow execution in shared environments.

## Why a New BB Interpretation

Current BBs are often documentation and schema artifacts only. For operational use, BBs must be executable trust units that can drive discovery, policy checks, workflow execution, and validation.

The OTBB model enables this by combining:

- machine-checkable certificates for data and outputs
- executable process contracts
- policy-driven pre-flight validation
- runtime provenance and result attestation

## Core OTBB Types

### BB-Data-Certificate

Purpose: advertise datasets (not only linked data) with trust, security, and releasability metadata.

Required content:

- dataset identity: id, issuer, timestamps, signatures
- integrity: hashes, optional transparency references
- provenance: lineage references and previous evidence
- security: classification and handling caveats
- releasability: audience, jurisdiction, sharing constraints
- access descriptors: STAC/OGC API/file endpoints
- policy claims: allowed purpose, retention obligations

### BB-Process-Contract

Purpose: declare what a process needs and what it must guarantee.

Required content:

- input requirements: schemas and certificate predicates
- execution constraints: allowed runtime, model versions, image digests
- policy gates: security/releasability/trust checks
- output obligations: mandatory provenance and output certificate fields
- quality gates: domain checks for result acceptance

### BB-Execution-Validation

Purpose: record pre-flight and in-flight compliance decisions for a specific run.

Required content:

- selected data certificates and process contract version
- policy decision trace (allow/deny + reasons)
- runtime evidence: environment, commands, software hashes
- validation outcomes: passed/failed checks with timestamps

### BB-Result-Certificate

Purpose: publish outputs with verifiable trust metadata and full traceability.

Required content:

- output identity and integrity
- back-link to execution validation and input certificates
- output security/releasability profile
- quality metrics and acceptance verdict
- provenance references for all generated artifacts

## Automated Execution Lifecycle

1. Data is published with BB-Data-Certificate.
2. Discovery indexes metadata and certificate claims.
3. Process selection loads BB-Process-Contract.
4. Policy engine evaluates compatibility in a shared common space.
5. REANA/CWL executes only if contract predicates pass.
6. BB-Execution-Validation is emitted during execution.
7. Output checks run against quality and contract obligations.
8. BB-Result-Certificate is generated and published.

## Mapping to This Repository

- Process orchestration: `scripts/run_workflow.py` + `workflows/sentinel2_hsi_pilot/`
- Process-type governance: `geospatial-2026/process-type-register/`
- Execution facade: `geospatial-2026/geospatial-processes-kernel/`
- Provenance profile baseline: `geospatial-2026/provenance-profile/`

Planned extension points:

- add OTBB schemas under `geospatial-2026/operational-trust-bbs/schemas/`
- add contract/certificate examples under `geospatial-2026/operational-trust-bbs/examples/`
- add conformance test cases under `geospatial-2026/operational-trust-bbs/tests/`

## Minimal API Surface (Recommended)

- `POST /kernel/validate-contract`:
  evaluate BB-Process-Contract against candidate BB-Data-Certificate payloads.
- `POST /kernel/execute-with-contract`:
  run process only when pre-flight validation succeeds.
- `POST /kernel/result-certificate`:
  register BB-Result-Certificate after successful run validation.

## Conformance Levels

- Level 1 (Descriptive): static schema compliance only.
- Level 2 (Policy-aware): pre-flight contract checks enabled.
- Level 3 (Operational): execution gating + runtime evidence + result certificate required.

## Notes on OGC BB Structure Alignment

The OTBB model remains compatible with OGC BB structure by keeping:

- schema as normative artifact
- examples as informative artifact
- API bindings as implementation artifact
- conformance tests as executable artifact

The key enhancement is that the BB is treated as an executable control object, not just a description.

## Interface Interoperability Requirement

Each OTBB (`BB-Data-Certificate`, `BB-Process-Contract`, `BB-Execution-Validation`, `BB-Result-Certificate`) must be
reachable through more than one interface style, so a workflow can bind to whichever interface the available data or
service actually exposes rather than requiring a single fixed API end-to-end:

- **REST** — plain HTTP/JSON for generic clients and simple polling.
- **OGC API (Processes/Records)** — for STAC/OGC-native catalogs and process execution.
- **OpenAPI** — a machine-readable contract for every REST/OGC API operation, enabling generated clients.
- **openEO** — for interoperability with ESA's [openEO Platform](https://openeo.cloud) and other openEO back-ends,
where a process contract or certificate needs to travel alongside an openEO process graph/batch job.

A `BB-Process-Contract` should therefore declare an `interfaceBindings` list (mirroring
`geospatial-processes-kernel/kernel/bblock-kernel.json`) and, where relevant, an `openeo` mapping (process id and/or
federation-mapping reference in `process-type-register/mappings/federation-mappings.json`) so policy/discovery logic
can select the right binding automatically based on workflow needs and data availability.
