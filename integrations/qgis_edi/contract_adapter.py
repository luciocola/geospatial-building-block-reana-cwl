#!/usr/bin/env python3
"""Build a context-specific QGIS EDI contract for the Geospatial Building Block."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ServiceEndpoints:
    umm_stac: str = "http://127.0.0.1:18000"
    process_register: str = "http://127.0.0.1:8015"
    kernel: str = "http://127.0.0.1:8016"


@dataclass(frozen=True)
class QGISLayerContext:
    layer_id: str
    source_href: str
    profile: str
    crs: str
    extent: tuple[float, float, float, float]
    acquisition_datetime: str | None = None
    resolution_m: float | None = None
    bands: tuple[str, ...] = ()
    masks: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


def build_contract(
    context: QGISLayerContext,
    process_id: str,
    parameters: dict[str, Any],
    endpoints: ServiceEndpoints | None = None,
) -> dict[str, Any]:
    """Create the logical contract sent to a Building Block.

    ``metadata`` is intentionally nested under ``context``. It can vary by
    source and process without changing the kernel-wide minimum semantics.
    """
    if context.profile not in {"raster", "stac", "geojson"}:
        raise ValueError(f"Unsupported QGIS input profile: {context.profile}")
    if not context.layer_id.strip() or not context.source_href.strip():
        raise ValueError("layer_id and source_href are required")
    if len(context.extent) != 4 or context.extent[0] > context.extent[2] or context.extent[1] > context.extent[3]:
        raise ValueError("extent must be [minx, miny, maxx, maxy]")
    if context.resolution_m is not None and context.resolution_m <= 0:
        raise ValueError("resolution_m must be greater than zero")

    services = endpoints or ServiceEndpoints()
    created = datetime.now(timezone.utc).isoformat()
    return {
        "contractVersion": "0.1.0",
        "created": created,
        "input": {
            "id": context.layer_id,
            "href": context.source_href,
            "profile": context.profile,
            "crs": context.crs,
            "extent": list(context.extent),
            "datetime": context.acquisition_datetime,
            "resolution_m": context.resolution_m,
            "bands": list(context.bands),
            "masks": list(context.masks),
            "contextMetadata": context.metadata,
        },
        "process": {
            "id": process_id,
            "parameters": parameters,
        },
        "outputs": {
            "profile": "raster",
            "mediaTypes": ["image/tiff; application=geotiff", "application/json"],
            "requiredEvidence": ["execution identifier", "input references", "output references", "validation result"],
        },
        "services": {
            "ummStac": services.umm_stac,
            "processRegister": services.process_register,
            "kernel": services.kernel,
        },
    }