# Local Process-Type Register API

This folder includes a local running OGC API - Records-like service for the OSPD process-type register prototype.

## Run

```bash
cd reana_cwl_workflows/geospatial-2026/process-type-register
bash run_local_register.sh
```

Server endpoint:

- `http://127.0.0.1:8015`

## Key Endpoints

- Landing page: `/`
- Conformance: `/conformance`
- Collections: `/collections`
- Process-type records: `/collections/process-types/items`
- Single record: `/collections/process-types/items/{record_id}`
- Federation mappings: `/mappings`
- DCAT catalog: `/dcat`
- Governance: `/governance`

## Example Checks

```bash
curl -s http://127.0.0.1:8015/collections | jq .
curl -s 'http://127.0.0.1:8015/collections/process-types/items?q=classification' | jq .
```

## Full OSPD Smoke Test

From the OSPD package root:

```bash
cd reana_cwl_workflows/geospatial-2026
bash run_full_test.sh
```

The script validates the workflow outputs, the provenance schema, the register records, the federation mappings, and the local API endpoints.
