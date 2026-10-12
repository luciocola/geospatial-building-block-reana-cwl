# Geospatial Building Block (GBB) — Core conformance class

| | |
|---|---|
| Conformance class | `https://luciocola.github.io/geospatial-building-block/1.0/conf/core` |
| Requirements class | `https://luciocola.github.io/geospatial-building-block/1.0/req/core` |
| Target | A web service that exposes one or more geospatial processes |
| Depends on (OGC Building Blocks) | `ogc.ogc-utils.json-link`, `ogc.api.common.landingPage`, `ogc.api.common.confClasses` |
| Status | under development |

The core class captures the minimum *observable* behaviour that makes a capability a GBB. It is deliberately smaller than the full GBB kernel contract ([bblock-kernel.json](../geospatial-processes-kernel/kernel/bblock-kernel.json)). It builds on (`dependsOn`) only the OGC building blocks the reference implementation actually satisfies. It does not depend on OGC API — Processes job listing, callbacks or the OGC exception schema.

## Requirements

All paths are relative to the service root. Requirement identifiers are relative to the requirements-class URI.

### `/req/core/landing`

1. `GET /` with `Accept: application/json` SHALL return `200` and a JSON object valid against `ogc.api.common.landingPage`.
2. Its `links` SHALL include `self`, `conformance`, `service-desc` (the OpenAPI document) and `service-doc` (human-readable documentation).
3. Every link SHALL be valid against `ogc.ogc-utils.json-link`.

A browser request (`Accept: text/html` without JSON) MAY be redirected to the human-readable documentation.

### `/req/core/conformance`

1. `GET /conformance` SHALL return a JSON object valid against `ogc.api.common.confClasses`.
2. `conformsTo` SHALL include the URI of this conformance class.
3. `conformsTo` SHALL NOT list a conformance class whose resources are not implemented.

### `/req/core/process-declaration`

This requirement corresponds to `algorithmContract` in the kernel.

1. Each entry in `GET /processes` SHALL have `id`, `title` and `version`.
2. `GET /processes/{id}` SHALL declare `inputs` (accepted input semantics) and `outputs` (declared output semantics).

### `/req/core/structured-failure`

1. A request for an unknown process or job SHALL return `404` with a JSON object body.
2. Invalid or unsupported input SHALL return a `4xx` status with a JSON object body. It SHALL NOT be silently accepted or ignored.

### `/req/core/evidence`

This requirement corresponds to `minimumSemantics` and `evidenceContract.required` in the kernel.

1. Executing a process SHALL return a job identifier and a `monitor` link.
2. `GET /jobs/{jobId}/results` for a job in a terminal state SHALL be valid against [schema/job-evidence.schema.json](schema/job-evidence.schema.json). It therefore reports:
   - the execution identifier (`jobID`)
   - the process identity (`processID`)
   - the execution status
   - the input references (`inputs`)
   - the output references (`results.*.href`)
   - a validation result (`validation.passed`)
3. Operational resources (`/jobs`, execution) MAY require authentication. Discovery resources (`/`, `/conformance`, `/processes`) SHALL NOT require it.

### `/req/core/stac-links`

1. When a process produces STAC Items, each Item SHALL contain a `links` array.
2. An Item served by the kernel SHALL include an absolute `self` link to that Item
   and a `root` link to a real STAC Catalog. A service landing page is not a STAC
   Catalog and SHALL NOT be used as the root.
3. The root Catalog SHALL link back to the published Items. Catalogs and Items
   SHALL retain the operational-resource authentication policy.

The reference kernel serves the Catalog at `/jobs/{jobId}/catalog`. Workflow
writers use relative `self` links; the kernel replaces `self` and `root` links
in the HTTP representation without modifying the saved files. Standalone
outputs need not invent a root when no Catalog has been published. STAC requires
`links`, but the additional `self`/`root` requirements here are GBB requirements,
not a claim that every GeoJSON Feature must have them.

## Optional conformance classes

- [Provenance](../gbb-provenance/description.md) is a separate draft class. It is
  not advertised by the kernel until the relevant producers pass its tests.
- Liability remains the optional kernel class `liability-claims-evidence`.
  Where claims are supplied, they must validate against the declared extension;
  core does not require producing liability evidence.

## Abstract test suite

The executable tests are in [test_gbb_conformance.py](../geospatial-processes-kernel/service/test_gbb_conformance.py). There is one test per requirement, and the OGC dependency schemas are checked structurally.
