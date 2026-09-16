# QGIS EDI Building Block Integration

This is the proposed integration boundary for QGIS EDI. The EDI source tree is a QGIS fork and currently contains no distinct EDI workflow/provider implementation, so the adapter belongs outside QGIS core as a Python Processing provider.

The complete workspace inventory is [building-block-catalog.json](building-block-catalog.json). It contains 21 QGIS plugins and 6 supporting services/processes/applications, each with a logical input/output contract and service bindings.

The catalog is exposed by the shared kernel as `qgis-edi-plugin-portfolio`, while the combined Sentinel-2/DJI sample is exposed as the `sentinel2-dji-imagery-harmonization` process. Both are discoverable from `GET /kernel/building-blocks` and `GET /processes` when the kernel is running. The process dispatches to `workflows/imagery_harmonization/harmonization-workflow.cwl`.

## Architecture

```text
QGIS EDI Processing algorithm
        |
        | creates a context-specific logical contract
        v
Service catalog and contract adapter
        |--------------------|
        v                    v
UMM STAC API            Geospatial BB kernel
localhost:18000        localhost:8016
                         |  OGC API Processes / REST
                         v
                   cwltool or REANA
                         |
                         v
             COG, STAC, QC, provenance outputs
```

The Process-Type Register at `localhost:8015` supplies controlled process semantics. The UMM service currently available in the Docker installation exposes only `/health` and `/`; it is therefore a health/catalog adapter, not an imagery-processing engine. ODM/NodeODM is not currently available and must be added separately for raw DJI frame reconstruction.

## Dynamic contract

The provider should create a contract from the selected QGIS layer, Processing parameters, and available service capabilities. Metadata remains context-dependent and is retained inside the contract; the kernel validates the stable minimum semantics:

- input identity and profile (`raster`, `STAC`, or `GeoJSON`);
- spatial, temporal, and coverage scope;
- process identity and parameters;
- typed output semantics;
- execution identifier, validation result, and evidence references.

The adapter must not invent one universal metadata schema. It should reject an unmapped or unsupported context before dispatch.

## Service modes

| Mode | Services | Behavior |
|---|---|---|
| Offline | QGIS + local `cwltool` | Default development path; no Docker service required. |
| Local services | UMM `18000`, register `8015`, kernel `8016` | Health-check services, discover contracts, execute through the protected kernel. |
| Operational | REANA + ODM/NodeODM + gateway | Use authenticated REANA execution, photogrammetric DJI preparation, TLS, quotas, and audit controls. |

The kernel requires `OSPD_API_TOKEN` for execution, job, artifact, openEO job, and provenance routes. Discovery routes remain readable without a token.

## QGIS provider responsibilities

1. Select a raster or STAC item from the current project.
2. Gather only context needed by the selected process: source URI, CRS, extent, resolution, bands, masks, acquisition time, and Processing parameters.
3. Build and persist the contract as an audit input.
4. Preflight UMM/register/kernel capabilities and report unavailable services clearly.
5. Dispatch the contract through the kernel or run the local CWL entry point.
6. Load typed raster outputs back into QGIS and expose QC/provenance sidecars.

The provider must never pass unrestricted user paths to a remote service. For kernel execution, files must be staged into an approved workspace and referenced by an allowed file contract.

## Current Docker inventory

At the time of this design check, Docker Desktop was unavailable and no containers were running. The repository contains a UMM STAC Compose service on port `18000`; the shared kernel Compose stack defines ports `8015` and `8016` but must be started separately. The adapter therefore uses health checks and offline fallback rather than assuming any service is live.

## Implementation sequence

1. Add a QGIS Processing provider using the `QgsProcessingProvider`/`QgsProcessingAlgorithm` extension point.
2. Implement contract creation and service preflight as pure Python, with tests outside the QGIS runtime.
3. Add a kernel process description for the imagery harmonization workflow and authenticated execution route.
4. Add a worker image with locked Rasterio/Torch dependencies and a versioned model release.
5. Add ODM/NodeODM integration for raw DJI inputs, independent checkpoint metrics, and orthomosaic handoff.

This package deliberately does not modify the QGIS fork or claim that UMM provides processing capabilities it does not currently expose.