#!/usr/bin/env python3
"""Local OGC API - Records-like service for OSPD process-type register."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import PlainTextResponse, RedirectResponse

BASE_DIR = Path(__file__).resolve().parents[1]
RECORDS_FILE = BASE_DIR / "records" / "process-types-records.json"
MAPPINGS_FILE = BASE_DIR / "mappings" / "federation-mappings.json"
DCAT_FILE = BASE_DIR / "dcat" / "process-types-catalog.json"
GOVERNANCE_FILE = BASE_DIR / "governance" / "register-governance.md"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_records() -> dict[str, Any]:
    return load_json(RECORDS_FILE)


app = FastAPI(
    title="OSPD 2026 Process-Type Register API",
    description="Local OGC API - Records-like endpoint for process-type register prototyping.",
    version="0.1.0",
)


@app.get("/swagger.json", include_in_schema=False)
def swagger_json() -> dict[str, Any]:
    return app.openapi()


@app.get("/swagger", include_in_schema=False)
def swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/swagger.json",
        title="OSPD 2026 Process-Type Register Swagger UI",
    )


@app.get("/")
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/swagger", status_code=307)


@app.get("/landing")
def landing_page() -> dict[str, Any]:
    return {
        "title": "OSPD 2026 Process-Type Register API",
        "description": "Local register endpoint exposing OGC API - Records-like resources.",
        "links": [
            {"rel": "self", "type": "application/json", "href": "/landing"},
            {"rel": "ui", "type": "text/html", "href": "/swagger"},
            {"rel": "conformance", "type": "application/json", "href": "/conformance"},
            {"rel": "data", "type": "application/json", "href": "/collections"},
            {"rel": "records", "type": "application/geo+json", "href": "/collections/process-types/items"},
            {"rel": "dcat", "type": "application/ld+json", "href": "/dcat"},
        ],
    }


@app.get("/conformance")
def conformance() -> dict[str, Any]:
    return {
        "conformsTo": [
            "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core",
            "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/record-core",
            "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/json",
        ]
    }


@app.get("/collections")
def collections() -> dict[str, Any]:
    return {
        "collections": [
            {
                "id": "process-types",
                "title": "OSPD Process Types",
                "description": "Controlled vocabulary of process types for provenance activity classification.",
                "itemType": "feature",
                "links": [
                    {"rel": "items", "type": "application/geo+json", "href": "/collections/process-types/items"},
                    {"rel": "describedby", "type": "application/json", "href": "/collections/process-types/schema"},
                    {"rel": "related", "type": "application/json", "href": "/mappings"},
                ],
            }
        ],
        "links": [{"rel": "self", "type": "application/json", "href": "/collections"}],
    }


@app.get("/collections/process-types")
def collection_by_id() -> dict[str, Any]:
    return collections()["collections"][0]


@app.get("/collections/process-types/schema")
def process_type_schema() -> dict[str, Any]:
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Process Type Record",
        "type": "object",
        "required": ["id", "properties"],
        "properties": {
            "id": {"type": "string", "format": "uri"},
            "properties": {
                "type": "object",
                "required": ["recordType", "prefLabel", "definition", "status"],
                "properties": {
                    "recordType": {"type": "string"},
                    "prefLabel": {"type": "string"},
                    "definition": {"type": "string"},
                    "status": {"type": "string"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
                "additionalProperties": True,
            },
        },
        "additionalProperties": True,
    }


@app.get("/collections/process-types/items")
def items(limit: int = Query(default=100, ge=1, le=1000), q: str | None = None) -> dict[str, Any]:
    records = load_records()
    features = records.get("features", [])

    if q:
        query = q.lower().strip()
        features = [
            f
            for f in features
            if query in f.get("id", "").lower()
            or query in f.get("properties", {}).get("prefLabel", "").lower()
            or query in f.get("properties", {}).get("definition", "").lower()
            or any(query in kw.lower() for kw in f.get("properties", {}).get("keywords", []))
        ]

    sliced = features[:limit]
    return {
        "type": "FeatureCollection",
        "timeStamp": records.get("timeStamp"),
        "numberMatched": len(features),
        "numberReturned": len(sliced),
        "features": sliced,
        "links": [{"rel": "self", "type": "application/geo+json", "href": "/collections/process-types/items"}],
    }


@app.get("/collections/process-types/items/{record_id}")
def item_by_id(record_id: str) -> dict[str, Any]:
    records = load_records().get("features", [])
    for feature in records:
        if feature.get("id", "").rstrip("/").endswith(record_id):
            return feature
    raise HTTPException(status_code=404, detail=f"Record not found: {record_id}")


@app.get("/mappings")
def mappings() -> dict[str, Any]:
    return load_json(MAPPINGS_FILE)


@app.get("/dcat")
def dcat_catalog() -> dict[str, Any]:
    return load_json(DCAT_FILE)


@app.get("/governance", response_class=PlainTextResponse)
def governance() -> str:
    return GOVERNANCE_FILE.read_text(encoding="utf-8")
