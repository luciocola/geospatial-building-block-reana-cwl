#!/usr/bin/env python3
"""Local OGC API Processes facade defined as an OGC Building Blocks kernel."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request, Response
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BASE_DIR.parents[1]
WORKFLOW_DIR = WORKSPACE_ROOT / "workflows" / "sentinel2_hsi_pilot"
WORKFLOW_FILE = WORKFLOW_DIR / "workflow.cwl"
HARMONIZATION_WORKFLOW_DIR = WORKSPACE_ROOT / "workflows" / "imagery_harmonization"
RUNNER_SCRIPT = WORKSPACE_ROOT / "scripts" / "run_workflow.py"
KERNEL_FILE = BASE_DIR / "kernel" / "bblock-kernel.json"
DEFAULT_AOI = WORKFLOW_DIR / "examples" / "aoi.geojson"
JOB_ROOT = WORKFLOW_DIR / ".tmp_oapip_jobs"
REGISTER_API_BASE = os.getenv("OSPD_REGISTER_API_BASE", "http://127.0.0.1:8015")
PROVENANCE_ROOT = BASE_DIR / "kernel" / "provenance_ingest"
API_TOKEN = os.getenv("OSPD_API_TOKEN", "")
MAX_PROVENANCE_BYTES = int(os.getenv("OSPD_MAX_PROVENANCE_BYTES", "1048576"))
MAX_JOB_LOG_CHARS = int(os.getenv("OSPD_MAX_JOB_LOG_CHARS", "65536"))
MAX_EXECUTION_BYTES = int(os.getenv("OSPD_MAX_EXECUTION_BYTES", "262144"))
MAX_PROVENANCE_RECORDS = int(os.getenv("OSPD_MAX_PROVENANCE_RECORDS", "1000"))
RESULT_MEDIA_TYPES = {
    "hsi_classification.geojson": "application/geo+json",
    "classification_summary.json": "application/json",
    "stac_item.json": "application/geo+json",
    "provenance_bundle.json": "application/json",
    "workflow_prov_profile.json": "application/json",
    "provenance_verification.json": "application/json",
}
PROCESS_OUTPUTS = {
    "sentinel2-hsi-pilot": (
        "hsi_classification.geojson",
        "classification_summary.json",
        "stac_item.json",
        "provenance_bundle.json",
        "workflow_prov_profile.json",
        "provenance_verification.json",
    ),
    "sentinel2-dji-imagery-harmonization": (
        "sentinel2_harmonized.tif",
        "reference_histogram.json",
        "target_grid.json",
        "sentinel2_quality.json",
        "sentinel2_stac_item.json",
        "sentinel2_provenance.json",
        "dji_harmonized.tif",
        "dji_histograms.json",
        "dji_quality.json",
        "dji_stac_item.json",
        "dji_provenance.json",
        "comparability_report.json",
    ),
}
PROCESS_MEDIA_TYPES = {
    **RESULT_MEDIA_TYPES,
    "sentinel2_harmonized.tif": "image/tiff; application=geotiff",
    "dji_harmonized.tif": "image/tiff; application=geotiff",
    "reference_histogram.json": "application/json",
    "target_grid.json": "application/json",
    "sentinel2_quality.json": "application/json",
    "sentinel2_stac_item.json": "application/geo+json",
    "sentinel2_provenance.json": "application/json",
    "dji_histograms.json": "application/json",
    "dji_quality.json": "application/json",
    "dji_stac_item.json": "application/geo+json",
    "dji_provenance.json": "application/json",
    "comparability_report.json": "application/json",
}


class ProcessExecutionRequest(BaseModel):
    backend: str = Field(default="cwltool", pattern="^(cwltool|reana)$")
    inputs: dict[str, Any] = Field(default_factory=dict)
    layer_name: str | None = Field(default=None, max_length=256)
    image_path: str | None = Field(default=None, max_length=2048)
    run_id: str | None = Field(default=None, max_length=128)
    reana_name_prefix: str | None = Field(default=None, max_length=128)


class ProvenanceIngestRequest(BaseModel):
    bundle: dict[str, Any] | None = None
    source: str | None = Field(default=None, max_length=2048)
    tags: list[str] = Field(default_factory=list, max_length=50)


# --- openEO interoperability binding -----------------------------------------------------
# Same execution/process-type/provenance kernel exposed via the openEO API shape, so a
# workflow step can pick whichever interface (REST / OGC API Processes / OpenAPI / openEO)
# matches the data or service it actually needs to talk to.
OPENEO_API_VERSION = "1.2.0"
OPENEO_PROCESS_ID = "ospd_sentinel2_hsi_pilot"
_OPENEO_STATUS_MAP = {
    "accepted": "created",
    "running": "running",
    "successful": "finished",
    "failed": "error",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _extract_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    bundle = payload.get("bundle")
    if isinstance(bundle, dict):
        return bundle
    return payload


def _resolve_workspace_file(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(status_code=422, detail="File href/path must be a non-empty string")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = WORKSPACE_ROOT / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(WORKSPACE_ROOT.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="File inputs must remain inside the workspace") from exc
    if not resolved.is_file():
        raise HTTPException(status_code=422, detail="Input file does not exist inside the workspace")
    return str(resolved)


def _normalize_input_value(value: Any) -> Any:
    if isinstance(value, dict):
        if "href" in value:
            return {"class": "File", "path": _resolve_workspace_file(value["href"])}
        if "path" in value and value.get("class") == "File":
            return {**value, "path": _resolve_workspace_file(value["path"])}
        if "value" in value:
            return value["value"]
    return value


def _build_workflow_inputs(
    payload: dict[str, Any], run_id: str, process_id: str = "sentinel2-hsi-pilot"
) -> dict[str, Any]:
    user_inputs = payload.get("inputs") or {}

    normalized: dict[str, Any] = {}
    for key, value in user_inputs.items():
        normalized[key] = _normalize_input_value(value)

    if process_id == "sentinel2-hsi-pilot":
        normalized.setdefault("aoi_geojson", {"class": "File", "path": str(DEFAULT_AOI)})
        normalized.setdefault("acquisition_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        normalized.setdefault("classifier_model", "hsi-baseline-v1")
    normalized.setdefault("run_id", run_id)

    if payload.get("layer_name"):
        normalized["layer_name"] = payload["layer_name"]
    if payload.get("image_path"):
        normalized["image_path"] = payload["image_path"]

    return normalized


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, process_id: str, backend: str, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        record = {
            "jobID": job_id,
            "processID": process_id,
            "backend": backend,
            "status": "accepted",
            "created": now_iso(),
            "updated": now_iso(),
            "payload": payload,
            "returnCode": None,
            "stdout": "",
            "stderr": "",
            "results": {},
        }
        with self._lock:
            self._jobs[job_id] = record
        return record

    def update(self, job_id: str, **fields: Any) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            self._jobs[job_id].update(fields)
            self._jobs[job_id]["updated"] = now_iso()
            return dict(self._jobs[job_id])

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return dict(self._jobs[job_id])

    def list_all(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(j) for j in self._jobs.values()]


JOB_STORE = JobStore()


def _collect_local_results(job_id: str, job_dir: Path) -> dict[str, Any]:
    outputs = {}
    output_dir = job_dir / "outputs"
    try:
        process_id = JOB_STORE.get(job_id)["processID"]
    except KeyError:
        process_id = "sentinel2-hsi-pilot"
    for name in PROCESS_OUTPUTS.get(process_id, RESULT_MEDIA_TYPES):
        if (output_dir / name).is_file():
            outputs[name] = {
                "href": f"/jobs/{job_id}/artifacts/{name}",
                "type": PROCESS_MEDIA_TYPES[name],
            }
    return outputs


def _run_local_pipeline(job_dir: Path, inputs_file: Path) -> subprocess.CompletedProcess[str]:
    inputs = load_json(inputs_file)
    script_dir = WORKFLOW_DIR / "scripts"
    tmp_dir = job_dir / "outputs"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    aoi_href = inputs["aoi_geojson"]["path"] if isinstance(inputs.get("aoi_geojson"), dict) else inputs["aoi_geojson"]
    acquisition_date = inputs["acquisition_date"]
    run_id = inputs["run_id"]
    classifier_model = inputs["classifier_model"]
    layer_name = inputs.get("layer_name")
    image_path = inputs.get("image_path")

    commands = [
        [
            "python3",
            str(script_dir / "ingest_sentinel2.py"),
            "--aoi-geojson",
            aoi_href,
            "--acquisition-date",
            acquisition_date,
            "--run-id",
            run_id,
            "--output-dir",
            str(tmp_dir),
        ],
        [
            "python3",
            str(script_dir / "preprocess_hsi.py"),
            "--ingest-manifest",
            str(tmp_dir / "sentinel2_ingest.json"),
            "--run-id",
            run_id,
            "--output-dir",
            str(tmp_dir),
        ],
        [
            "python3",
            str(script_dir / "classify_hsi.py"),
            "--hsi-cube-manifest",
            str(tmp_dir / "hsi_cube_manifest.json"),
            "--classifier-model",
            classifier_model,
            "--run-id",
            run_id,
            "--output-dir",
            str(tmp_dir),
        ],
        [
            "python3",
            str(script_dir / "package_provenance.py"),
            "--ingest-manifest",
            str(tmp_dir / "sentinel2_ingest.json"),
            "--hsi-cube-manifest",
            str(tmp_dir / "hsi_cube_manifest.json"),
            "--classification-geojson",
            str(tmp_dir / "hsi_classification.geojson"),
            "--classification-summary",
            str(tmp_dir / "classification_summary.json"),
            "--stac-item",
            str(tmp_dir / "stac_item.json"),
            "--run-id",
            run_id,
            "--output-dir",
            str(tmp_dir),
        ],
    ]
    if layer_name:
        commands[-1].extend(["--layer-name", str(layer_name)])
    if image_path:
        commands[-1].extend(["--image-path", str(image_path)])

    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    return_code = 0
    for cmd in commands:
        proc = subprocess.run(cmd, cwd=str(workflow_dir), capture_output=True, text=True, check=False)
        stdout_parts.append(proc.stdout)
        stderr_parts.append(proc.stderr)
        if proc.returncode != 0:
            return_code = proc.returncode
            break

    return subprocess.CompletedProcess(
        args=["python3", "local-pipeline-fallback"],
        returncode=return_code,
        stdout="".join(stdout_parts),
        stderr="".join(stderr_parts),
    )


def _run_job(job: dict[str, Any]) -> None:
    job_id = job["jobID"]
    payload = job["payload"]
    backend = job["backend"]
    process = PROCESSES[job["processID"]]
    workflow_dir = Path(process["workflow_dir"])
    workflow_file = workflow_dir / process["workflow_file"]

    job_dir = JOB_ROOT / job_id
    output_dir = job_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = payload.get("run_id") or f"oapip-{job_id[:8]}"
    inputs = _build_workflow_inputs(payload, run_id=run_id, process_id=job["processID"])
    inputs_file = job_dir / "workflow-inputs.json"
    with inputs_file.open("w", encoding="utf-8") as f:
        json.dump(inputs, f, indent=2)

    cwltool_bin = shutil.which("cwltool")

    if backend == "reana":
        cmd = [
            "python3",
            str(RUNNER_SCRIPT),
            "--backend",
            "reana",
            "--workflow-dir",
            str(workflow_dir),
            "--workflow-file",
            process["workflow_file"],
            "--reana-name-prefix",
            payload.get("reana_name_prefix", "oapip-kernel"),
            "--no-follow-logs",
        ]
    else:
        if cwltool_bin:
            cmd = [
                cwltool_bin,
                "--outdir",
                str(output_dir),
                str(workflow_file),
                str(inputs_file),
            ]
        else:
            cmd = ["python3", "local-pipeline-fallback"]

    JOB_STORE.update(job_id, status="running", command=cmd)
    if backend == "cwltool" and not cwltool_bin:
        if job["processID"] != "sentinel2-hsi-pilot":
            proc = subprocess.CompletedProcess(
                args=["cwltool"],
                returncode=2,
                stdout="",
                stderr="cwltool is required for this workflow when the process-specific fallback is unavailable",
            )
        else:
            proc = _run_local_pipeline(job_dir=job_dir, inputs_file=inputs_file)
    else:
        proc = subprocess.run(cmd, cwd=str(workflow_dir), capture_output=True, text=True, check=False)

    status = "successful" if proc.returncode == 0 else "failed"
    results = (
        _collect_local_results(job_id, job_dir)
        if status == "successful" and backend == "cwltool"
        else {}
    )
    JOB_STORE.update(
        job_id,
        status=status,
        returnCode=proc.returncode,
        stdout=proc.stdout[-MAX_JOB_LOG_CHARS:],
        stderr=proc.stderr[-MAX_JOB_LOG_CHARS:],
        results=results,
    )


PROCESSES = {
    "sentinel2-hsi-pilot": {
        "id": "sentinel2-hsi-pilot",
        "title": "Sentinel-2 to HSI Classification (Pilot)",
        "description": "Shared CWL workflow with OSPD provenance outputs and process-type semantics.",
        "version": "0.1.0",
        "workflow_dir": str(WORKFLOW_DIR),
        "workflow_file": "workflow.cwl",
        "input_schema": {
            "aoi_geojson": {"type": "File", "required": False, "default": str(DEFAULT_AOI)},
            "acquisition_date": {"type": "string", "required": False},
            "classifier_model": {"type": "string", "required": False, "default": "hsi-baseline-v1"},
            "run_id": {"type": "string", "required": False},
            "layer_name": {"type": "string", "required": False},
            "image_path": {"type": "string", "required": False},
        },
        "output_schema": {
            name: "File" for name in PROCESS_OUTPUTS["sentinel2-hsi-pilot"]
        },
        "jobControlOptions": ["async-execute"],
        "outputTransmission": ["value", "reference"],
        "keywords": ["cwl", "provenance", "stac", "ospd", "hsi"],
        "kernel": {
            "buildingBlocks": [
                "provenance-profile",
                "process-type-register",
                "geospatial-processes-profile",
            ]
        },
    },
    "sentinel2-dji-imagery-harmonization": {
        "id": "sentinel2-dji-imagery-harmonization",
        "title": "Sentinel-2 and DJI Imagery Harmonization",
        "description": "Executable two-workflow sample for common-grid reprojection, Sentinel-2 enhancement, DJI area downsampling, histogram matching, and quality gates.",
        "version": "0.1.0",
        "workflow_dir": str(HARMONIZATION_WORKFLOW_DIR),
        "workflow_file": "harmonization-workflow.cwl",
        "jobControlOptions": ["async-execute"],
        "outputTransmission": ["reference"],
        "keywords": ["cwl", "reana", "sentinel-2", "dji", "harmonization", "quality"],
        "kernel": {
            "buildingBlocks": [
                "sentinel2-dji-imagery-harmonization",
                "provenance-profile",
                "process-type-register",
            ]
        },
        "input_schema": {
            "source_rgb": {"type": "File", "required": True},
            "orthomosaic": {"type": "File", "required": True},
            "target_crs": {"type": "string", "required": True},
            "target_resolution": {"type": "float", "required": True},
            "sentinel_input_scale": {"type": "float", "required": False, "default": 10000.0},
            "dji_input_scale": {"type": "float", "required": False, "default": 10000.0},
            "method": {"type": "string", "required": False, "default": "bicubic-demo"},
            "model": {"type": "File", "required": False},
            "model_card": {"type": "File", "required": False},
            "expected_model_sha256": {"type": "string", "required": False},
            "checkpoint_rmse_pixels": {"type": "float", "required": False, "default": 0.0},
            "cloud_shadow_fraction": {"type": "float", "required": False, "default": 0.0},
            "min_overlap_pixels": {"type": "int", "required": False, "default": 10000},
            "max_js_distance": {"type": "float", "required": False, "default": 0.10},
            "max_clipping_fraction": {"type": "float", "required": False, "default": 0.01},
            "max_registration_rmse_pixels": {"type": "float", "required": False, "default": 1.0},
            "max_cloud_shadow_fraction": {"type": "float", "required": False, "default": 0.05},
            "run_id": {"type": "string", "required": True},
        },
        "output_schema": {
            name: "File" for name in PROCESS_OUTPUTS["sentinel2-dji-imagery-harmonization"]
        },
    },
}


app = FastAPI(
    title="OSPD Geospatial Processes Facade",
    description="Geospatial processes facade backed by shared CWL workflows and a Geospatial Building Blocks kernel.",
    version="0.1.0",
    summary="Geospatial processes facade + Geospatial Building Blocks kernel",
    openapi_tags=[
        {
            "name": "processes",
            "description": "OGC API Processes facade for executing the shared CWL pilot workflow.",
        },
        {
            "name": "jobs",
            "description": "Process execution jobs and results.",
        },
        {
            "name": "kernel",
            "description": "Geospatial Building Blocks kernel resources linking provenance and register semantics.",
        },
        {
            "name": "openeo",
            "description": "openEO-compatible binding for the same execution kernel, for interoperability with openEO Platform/ESA back-ends.",
        },
    ],
)


def _is_protected_route(request: Request) -> bool:
    path = request.url.path.rstrip("/")
    return (
        path.startswith("/jobs")
        or path.startswith("/kernel/provenance")
        or path.startswith("/openeo/jobs")
        or path.endswith("/execution")
    )


@app.middleware("http")
async def protect_operational_routes(request: Request, call_next):
    if not _is_protected_route(request):
        return await call_next(request)
    content_length = request.headers.get("Content-Length")
    maximum_length = (
        MAX_PROVENANCE_BYTES
        if request.url.path.rstrip("/") == "/kernel/provenance"
        else MAX_EXECUTION_BYTES
    )
    if content_length:
        try:
            if int(content_length) > maximum_length:
                return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header"})
    if not API_TOKEN:
        return JSONResponse(
            status_code=503,
            content={"detail": "Operational API disabled: configure OSPD_API_TOKEN"},
        )
    authorization = request.headers.get("Authorization", "")
    scheme, _, supplied_token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(supplied_token, API_TOKEN):
        return JSONResponse(
            status_code=401,
            content={"detail": "Valid bearer token required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await call_next(request)


def build_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        summary=app.summary,
        description=app.description,
        routes=app.routes,
    )
    kernel = load_json(KERNEL_FILE)
    schema["info"]["x-kernel"] = {
        "id": "ospd-geospatial-bblocks-kernel",
        "buildingBlocks": [
            "geospatial-processes-facade",
            "provenance-profile",
            "process-type-register",
            "geospatial-processes-profile",
            "sentinel2-dji-imagery-harmonization",
            "qgis-edi-plugin-portfolio",
        ],
        "interfaceBindings": list(kernel.get("interfaceBindings", {}).keys()),
        "functionalContract": kernel.get("functionalContract", {}),
        "standards": [
            {
                "id": standard.get("id"),
                "title": standard.get("title"),
                "version": standard.get("version"),
                "conformanceClasses": standard.get("conformanceClasses", []),
            }
            for block in kernel.get("buildingBlocks", [])
            for standard in block.get("standards", [])
        ],
    }
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
    }
    for path, operations in schema.get("paths", {}).items():
        if (
            path.startswith("/jobs")
            or path.startswith("/kernel/provenance")
            or path.startswith("/openeo/jobs")
            or path.endswith("/execution")
        ):
            for operation in operations.values():
                if isinstance(operation, dict):
                    operation["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema


app.openapi = build_openapi


@app.get("/")
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/swagger", status_code=307)


@app.get("/landing")
def landing_page() -> dict[str, Any]:
    return {
        "title": "OSPD Geospatial Processes Facade",
        "description": "Local facade exposing CWL workflows through geospatial interfaces and linking Geospatial Building Blocks.",
        "links": [
            {"rel": "self", "type": "application/json", "href": "/landing"},
            {"rel": "ui", "type": "text/html", "href": "/swagger"},
            {"rel": "conformance", "type": "application/json", "href": "/conformance"},
            {"rel": "processes", "type": "application/json", "href": "/processes"},
            {"rel": "kernel", "type": "application/json", "href": "/kernel"},
            {"rel": "register", "type": "application/json", "href": f"{REGISTER_API_BASE}/collections/process-types/items"},
            {"rel": "openeo", "type": "application/json", "href": "/openeo/"},
        ],
    }


@app.get("/conformance")
def conformance() -> dict[str, Any]:
    return {
        "conformsTo": [
            "http://www.opengis.net/spec/ogcapi-processes-1/1.0/conf/core",
            "http://www.opengis.net/spec/ogcapi-processes-1/1.0/conf/json",
            "http://www.opengis.net/spec/ogcapi-processes-1/1.0/conf/oas30",
            "http://www.opengis.net/spec/ogcapi-processes-1/1.0/conf/job-list",
            "http://www.opengis.net/spec/ogcapi-processes-1/1.0/conf/callback",
        ]
    }


@app.get("/swagger.json", include_in_schema=False)
def swagger_json() -> dict[str, Any]:
    return build_openapi()


@app.get("/swagger", include_in_schema=False)
def swagger_ui() -> Any:
    return get_swagger_ui_html(
        openapi_url="/swagger.json",
        title="OSPD OGC API Processes Facade Kernel Swagger UI",
    )


@app.get("/processes", tags=["processes"])
def list_processes() -> dict[str, Any]:
    return {
        "processes": [
            {
                **proc,
                "links": [
                    {"rel": "self", "type": "application/json", "href": f"/processes/{proc['id']}"},
                    {"rel": "execute", "type": "application/json", "href": f"/processes/{proc['id']}/execution"},
                ],
            }
            for proc in PROCESSES.values()
        ],
        "links": [{"rel": "self", "type": "application/json", "href": "/processes"}],
    }


@app.get("/processes/{process_id}", tags=["processes"])
def describe_process(process_id: str) -> dict[str, Any]:
    proc = PROCESSES.get(process_id)
    if not proc:
        raise HTTPException(status_code=404, detail=f"Process not found: {process_id}")

    return {
        **proc,
        "inputs": proc.get("input_schema", {}),
        "outputs": proc.get("output_schema", {}),
        "links": [
            {"rel": "execute", "type": "application/json", "href": f"/processes/{process_id}/execution"},
            {"rel": "kernel", "type": "application/json", "href": "/kernel/building-blocks"},
        ],
    }


@app.post("/processes/{process_id}/execution", status_code=201, tags=["processes"])
def execute_process(
    process_id: str,
    request: ProcessExecutionRequest = Body(
        ...,
        examples={
            "pilot": {
                "summary": "Pilot execution request",
                "value": {
                    "backend": "cwltool",
                    "layer_name": "roads_main",
                    "image_path": "/data/sentinel2/B04.tif",
                    "inputs": {
                        "aoi_geojson": {"href": "workflows/sentinel2_hsi_pilot/examples/aoi.geojson"},
                        "acquisition_date": "2026-07-10",
                        "classifier_model": "hsi-baseline-v1",
                    },
                },
            }
        },
    ),
) -> dict[str, Any]:
    if process_id not in PROCESSES:
        raise HTTPException(status_code=404, detail=f"Process not found: {process_id}")

    payload = request.model_dump(exclude_none=True)
    backend = str(request.backend).lower().strip()
    if backend not in ("cwltool", "reana"):
        raise HTTPException(status_code=400, detail="backend must be 'cwltool' or 'reana'")

    process = PROCESSES[process_id]
    workflow_file = Path(process["workflow_dir"]) / process["workflow_file"]
    if not workflow_file.exists():
        raise HTTPException(status_code=500, detail=f"Workflow file missing: {workflow_file}")

    _build_workflow_inputs(payload, run_id=request.run_id or "validation")

    job = JOB_STORE.create(process_id=process_id, backend=backend, payload=payload)
    thread = threading.Thread(target=_run_job, args=(job,), daemon=True)
    thread.start()

    job_id = job["jobID"]
    return {
        "jobID": job_id,
        "status": "accepted",
        "location": f"/jobs/{job_id}",
        "links": [
            {"rel": "monitor", "type": "application/json", "href": f"/jobs/{job_id}"},
            {"rel": "results", "type": "application/json", "href": f"/jobs/{job_id}/results"},
        ],
    }


@app.get("/jobs/{job_id}", tags=["jobs"])
def get_job(job_id: str) -> dict[str, Any]:
    try:
        job = JOB_STORE.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}") from exc

    return {
        "jobID": job["jobID"],
        "processID": job["processID"],
        "status": job["status"],
        "backend": job["backend"],
        "created": job["created"],
        "updated": job["updated"],
        "returnCode": job["returnCode"],
        "links": [
            {"rel": "self", "type": "application/json", "href": f"/jobs/{job_id}"},
            {"rel": "results", "type": "application/json", "href": f"/jobs/{job_id}/results"},
        ],
    }


@app.get("/jobs/{job_id}/results", tags=["jobs"])
def get_job_results(job_id: str) -> dict[str, Any]:
    try:
        job = JOB_STORE.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}") from exc

    if job["status"] not in ("successful", "failed"):
        raise HTTPException(status_code=409, detail=f"Job is still {job['status']}")

    return {
        "jobID": job["jobID"],
        "status": job["status"],
        "returnCode": job["returnCode"],
        "results": job.get("results", {}),
        "logsAvailable": bool(job.get("stdout") or job.get("stderr")),
    }


@app.get("/jobs/{job_id}/artifacts/{filename}", tags=["jobs"])
def get_job_artifact(job_id: str, filename: str) -> FileResponse:
    try:
        job = JOB_STORE.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}") from exc
    if job["status"] != "successful":
        raise HTTPException(status_code=409, detail="Artifacts are available only for successful jobs")
    if filename not in PROCESS_MEDIA_TYPES:
        raise HTTPException(status_code=404, detail="Artifact not found")
    path = JOB_ROOT / job_id / "outputs" / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path, media_type=PROCESS_MEDIA_TYPES[filename], filename=filename)


@app.get("/kernel", tags=["kernel"])
def kernel_landing() -> dict[str, Any]:
    kernel = load_json(KERNEL_FILE)
    return {
        "id": kernel.get("id"),
        "title": kernel.get("title"),
        "description": kernel.get("description"),
        "version": kernel.get("version"),
        "functionalContract": kernel.get("functionalContract", {}),
        "interfaceBindings": kernel.get("interfaceBindings", {}),
        "bindingSelectionNotes": kernel.get("bindingSelectionNotes"),
        "links": [
            {"rel": "self", "type": "application/json", "href": "/kernel"},
            {"rel": "building-blocks", "type": "application/json", "href": "/kernel/building-blocks"},
            {"rel": "register", "type": "application/json", "href": f"{REGISTER_API_BASE}/collections/process-types/items"},
            {"rel": "openeo", "type": "application/json", "href": "/openeo/"},
        ],
    }


@app.get("/kernel/building-blocks", tags=["kernel"])
def list_building_blocks() -> dict[str, Any]:
    kernel = load_json(KERNEL_FILE)
    blocks = kernel.get("buildingBlocks", [])
    return {
        "type": "BuildingBlockCollection",
        "count": len(blocks),
        "buildingBlocks": blocks,
        "links": [{"rel": "self", "type": "application/json", "href": "/kernel/building-blocks"}],
    }


@app.get("/kernel/building-blocks/{block_id}", tags=["kernel"])
def get_building_block(block_id: str) -> dict[str, Any]:
    kernel = load_json(KERNEL_FILE)
    for block in kernel.get("buildingBlocks", []):
        if block.get("id") == block_id:
            return block
    raise HTTPException(status_code=404, detail=f"Building block not found: {block_id}")


@app.post("/kernel/provenance", status_code=202, tags=["kernel"])
def ingest_provenance(payload: ProvenanceIngestRequest | dict[str, Any] = Body(...)) -> dict[str, Any]:
    if isinstance(payload, ProvenanceIngestRequest):
        payload_data = payload.model_dump(exclude_none=True)
    else:
        payload_data = payload

    if not isinstance(payload_data, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")

    bundle = _extract_bundle(payload_data)
    if not isinstance(bundle, dict):
        raise HTTPException(status_code=400, detail="Provenance bundle must be a JSON object")
    if not any(key in bundle for key in ("entity", "activity", "agent")):
        raise HTTPException(status_code=422, detail="Provenance bundle must contain entity, activity, or agent")
    encoded_payload = json.dumps(payload_data, separators=(",", ":")).encode("utf-8")
    if len(encoded_payload) > MAX_PROVENANCE_BYTES:
        raise HTTPException(status_code=413, detail="Provenance payload exceeds configured size limit")

    ingest_id = str(uuid.uuid4())
    received_at = now_iso()
    PROVENANCE_ROOT.mkdir(parents=True, exist_ok=True)
    out_file = PROVENANCE_ROOT / f"{ingest_id}.json"

    envelope = {
        "ingestID": ingest_id,
        "receivedAt": received_at,
        "source": payload_data.get("source"),
        "tags": payload_data.get("tags", []),
        "bundle": bundle,
    }
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(envelope, f, indent=2)
    out_file.chmod(0o600)
    retained = sorted(
        (path for path in PROVENANCE_ROOT.glob("*.json") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for expired in retained[MAX_PROVENANCE_RECORDS:]:
        expired.unlink()

    return {
        "status": "accepted",
        "ingestID": ingest_id,
        "receivedAt": received_at,
        "links": [
            {"rel": "self", "type": "application/json", "href": f"/kernel/provenance/{ingest_id}"},
            {"rel": "collection", "type": "application/json", "href": "/kernel/provenance"},
        ],
    }


@app.get("/kernel/provenance", tags=["kernel"])
def list_provenance(limit: int = 20) -> dict[str, Any]:
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be >= 1")
    if limit > 200:
        limit = 200

    PROVENANCE_ROOT.mkdir(parents=True, exist_ok=True)
    files = sorted(
        [p for p in PROVENANCE_ROOT.glob("*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]

    entries = []
    for p in files:
        try:
            record = load_json(p)
        except Exception:
            continue
        ingest_id = record.get("ingestID") or p.stem
        entries.append(
            {
                "ingestID": ingest_id,
                "receivedAt": record.get("receivedAt"),
                "source": record.get("source"),
                "tags": record.get("tags", []),
                "href": f"/kernel/provenance/{ingest_id}",
            }
        )

    return {
        "type": "ProvenanceIngestCollection",
        "count": len(entries),
        "items": entries,
        "links": [{"rel": "self", "type": "application/json", "href": "/kernel/provenance"}],
    }


@app.get("/kernel/provenance/{ingest_id}", tags=["kernel"])
def get_provenance(ingest_id: str) -> dict[str, Any]:
    try:
        normalized_id = str(uuid.UUID(ingest_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid provenance ingest identifier") from exc
    path = PROVENANCE_ROOT / f"{normalized_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Provenance ingest not found: {ingest_id}")
    return load_json(path)


def _openeo_process_description() -> dict[str, Any]:
    proc = PROCESSES["sentinel2-hsi-pilot"]
    return {
        "id": OPENEO_PROCESS_ID,
        "summary": proc["title"],
        "description": proc["description"],
        "categories": ["cubes", "earth-observation"],
        "parameters": [
            {
                "name": "aoi_geojson",
                "description": "Area of interest, as a GeoJSON geometry/href.",
                "schema": {"type": "object", "subtype": "geojson"},
                "optional": True,
            },
            {
                "name": "acquisition_date",
                "description": "Sentinel-2 acquisition date.",
                "schema": {"type": "string", "format": "date"},
                "optional": True,
            },
            {
                "name": "classifier_model",
                "description": "HSI classifier model identifier.",
                "schema": {"type": "string"},
                "optional": True,
                "default": "hsi-baseline-v1",
            },
            {
                "name": "layer_name",
                "description": "Optional vector layer name to record in provenance.",
                "schema": {"type": "string"},
                "optional": True,
            },
            {
                "name": "image_path",
                "description": "Optional source image path to record in provenance.",
                "schema": {"type": "string"},
                "optional": True,
            },
        ],
        "returns": {
            "description": "STAC item, classification GeoJSON and PROV-JSON provenance bundle.",
            "schema": {"type": "object", "subtype": "stac-item"},
        },
        "links": [{"rel": "about", "type": "application/json", "href": "/kernel/building-blocks/geospatial-processes-facade"}],
    }


def _openeo_arguments_to_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        key: arguments[key]
        for key in ("aoi_geojson", "acquisition_date", "classifier_model")
        if key in arguments
    }
    payload: dict[str, Any] = {"backend": arguments.get("backend", "cwltool"), "inputs": inputs}
    for key in ("layer_name", "image_path", "run_id", "reana_name_prefix"):
        if key in arguments:
            payload[key] = arguments[key]
    return payload


def _extract_openeo_result_node(process_graph: dict[str, Any]) -> dict[str, Any]:
    result_nodes = [n for n in process_graph.values() if isinstance(n, dict) and n.get("result")]
    if len(result_nodes) == 1:
        return result_nodes[0]
    if len(process_graph) == 1:
        return next(iter(process_graph.values()))
    raise HTTPException(
        status_code=400,
        detail="process_graph must contain exactly one node with 'result': true",
    )


def _job_to_openeo(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job["jobID"],
        "process": {"id": OPENEO_PROCESS_ID},
        "status": _OPENEO_STATUS_MAP.get(job["status"], job["status"]),
        "created": job["created"],
        "updated": job["updated"],
        "links": [
            {"rel": "self", "type": "application/json", "href": f"/openeo/jobs/{job['jobID']}"},
            {"rel": "results", "type": "application/json", "href": f"/openeo/jobs/{job['jobID']}/results"},
        ],
    }


@app.get("/openeo/", tags=["openeo"])
def openeo_capabilities() -> dict[str, Any]:
    return {
        "api_version": OPENEO_API_VERSION,
        "backend_version": PROCESSES["sentinel2-hsi-pilot"]["version"],
        "id": "ospd-openeo-facade",
        "title": "OSPD Geospatial Building Blocks Kernel - openEO binding",
        "description": (
            "openEO-compatible binding for the same REANA/CWL execution kernel exposed under "
            "/processes (OGC API Processes) and /kernel (Building Blocks), so this workflow can "
            "be driven from any openEO client/back-end (e.g. openEO Platform, Copernicus Data "
            "Space Ecosystem) alongside REST/OGC API Processes/OpenAPI."
        ),
        "endpoints": [
            {"path": "/openeo/", "methods": ["GET"]},
            {"path": "/openeo/processes", "methods": ["GET"]},
            {"path": "/openeo/jobs", "methods": ["GET", "POST"]},
            {"path": "/openeo/jobs/{job_id}", "methods": ["GET"]},
            {"path": "/openeo/jobs/{job_id}/results", "methods": ["GET", "POST"]},
        ],
        "links": [
            {"rel": "self", "type": "application/json", "href": "/openeo/"},
            {"rel": "conformance", "type": "application/json", "href": "/conformance"},
            {"rel": "kernel", "type": "application/json", "href": "/kernel"},
        ],
    }


@app.get("/openeo/processes", tags=["openeo"])
def openeo_processes() -> dict[str, Any]:
    return {
        "processes": [_openeo_process_description()],
        "links": [{"rel": "self", "type": "application/json", "href": "/openeo/processes"}],
    }


@app.post("/openeo/jobs", status_code=201, tags=["openeo"])
def openeo_create_job(payload: dict[str, Any] = Body(...), response: Response = None) -> dict[str, Any]:
    process = payload.get("process") or {}
    process_graph = process.get("process_graph")
    if not isinstance(process_graph, dict) or not process_graph:
        raise HTTPException(status_code=400, detail="process.process_graph is required")

    node = _extract_openeo_result_node(process_graph)
    if node.get("process_id") not in (OPENEO_PROCESS_ID, None):
        raise HTTPException(status_code=400, detail=f"Unsupported openEO process_id: {node.get('process_id')}")

    job_payload = _openeo_arguments_to_payload(node.get("arguments") or {})
    job = JOB_STORE.create(process_id="sentinel2-hsi-pilot", backend=job_payload["backend"], payload=job_payload)

    if response is not None:
        response.headers["OpenEO-Identifier"] = job["jobID"]
        response.headers["Location"] = f"/openeo/jobs/{job['jobID']}"
    return _job_to_openeo(job)


@app.get("/openeo/jobs", tags=["openeo"])
def openeo_list_jobs() -> dict[str, Any]:
    return {
        "jobs": [_job_to_openeo(j) for j in JOB_STORE.list_all()],
        "links": [{"rel": "self", "type": "application/json", "href": "/openeo/jobs"}],
    }


@app.get("/openeo/jobs/{job_id}", tags=["openeo"])
def openeo_get_job(job_id: str) -> dict[str, Any]:
    try:
        job = JOB_STORE.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}") from exc
    return _job_to_openeo(job)


@app.post("/openeo/jobs/{job_id}/results", status_code=202, tags=["openeo"])
def openeo_start_job(job_id: str) -> dict[str, Any]:
    try:
        job = JOB_STORE.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}") from exc

    if job["status"] == "accepted":
        thread = threading.Thread(target=_run_job, args=(job,), daemon=True)
        thread.start()

    return _job_to_openeo(JOB_STORE.get(job_id))


@app.get("/openeo/jobs/{job_id}/results", tags=["openeo"])
def openeo_get_job_results(job_id: str) -> dict[str, Any]:
    try:
        job = JOB_STORE.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}") from exc

    if job["status"] not in ("successful", "failed"):
        raise HTTPException(status_code=400, detail={"code": "JobNotFinished", "message": f"Job is still {_OPENEO_STATUS_MAP.get(job['status'], job['status'])}"})

    return {
        "type": "Collection",
        "id": job_id,
        "assets": {name: {"href": href, "type": "application/octet-stream"} for name, href in job.get("results", {}).items()},
        "links": [{"rel": "self", "type": "application/json", "href": f"/openeo/jobs/{job_id}/results"}],
    }
