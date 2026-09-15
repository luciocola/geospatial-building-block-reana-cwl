#!/usr/bin/env python3
"""Unified launcher for shared CWL workflows via cwltool or REANA."""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _candidate_gdal_data_dirs() -> list[str]:
    candidates: list[str] = []
    for env_key in ("GDAL_DATA", "QGIS_GDAL_DATA"):
        env_value = os.environ.get(env_key)
        if env_value:
            candidates.append(env_value)

    candidates.extend([
        "/Applications/QGIS.app/Contents/Resources/share/gdal",
        "/Applications/QGIS-LTR.app/Contents/Resources/share/gdal",
        "/opt/homebrew/share/gdal",
        "/usr/local/share/gdal",
        "/usr/share/gdal",
    ])
    candidates.extend(sorted(glob.glob("/opt/homebrew/Cellar/gdal/*/share/gdal"), reverse=True))
    candidates.extend(sorted(glob.glob("/usr/local/Cellar/gdal/*/share/gdal"), reverse=True))

    unique: list[str] = []
    for path in candidates:
        if path and path not in unique:
            unique.append(path)
    return unique


def _resolve_gdal_data_dir() -> str:
    for path in _candidate_gdal_data_dirs():
        if os.path.isfile(os.path.join(path, "gcs.csv")):
            return path
    return ""


def _build_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    if env.get("GDAL_DATA") and os.path.isfile(os.path.join(env["GDAL_DATA"], "gcs.csv")):
        return env

    gdal_data = _resolve_gdal_data_dir()
    if gdal_data:
        env["GDAL_DATA"] = gdal_data
        os.environ["GDAL_DATA"] = gdal_data
        print(f"[run_workflow] GDAL_DATA={gdal_data}")
    else:
        print("[run_workflow] WARNING: GDAL_DATA not resolved; EPSG lookups may fail.")
    return env


def run_cmd(cmd: list[str], cwd: Path, dry_run: bool = False) -> int:
    print("$", " ".join(cmd))
    if dry_run:
        return 0
    result = subprocess.run(cmd, cwd=str(cwd), env=_build_subprocess_env(), check=False)
    return result.returncode


def ensure_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")


def run_cwltool(workflow_dir: Path, workflow_file: str, inputs_file: Path, dry_run: bool) -> int:
    ensure_exists(workflow_dir / workflow_file, "Workflow file")
    ensure_exists(inputs_file, "Inputs file")

    cwltool_bin = shutil.which("cwltool")
    if cwltool_bin:
        cmd = [cwltool_bin, workflow_file, str(inputs_file)]
    else:
        cmd = [sys.executable, "-m", "cwltool", workflow_file, str(inputs_file)]

    return run_cmd(cmd, cwd=workflow_dir, dry_run=dry_run)


def infer_reana_name(base: str) -> str:
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{base}-{timestamp}"


def run_reana(
    workflow_dir: Path,
    reana_name: str,
    follow_logs: bool,
    dry_run: bool,
) -> int:
    reana_bin = shutil.which("reana-client")
    if not reana_bin:
        print("ERROR: reana-client is not installed or not on PATH.")
        print("Install: python3 -m pip install reana-client")
        return 2

    commands = [
        [reana_bin, "create", "-n", reana_name],
        [reana_bin, "upload", "-n", reana_name],
        [reana_bin, "start", "-n", reana_name],
    ]

    for cmd in commands:
        code = run_cmd(cmd, cwd=workflow_dir, dry_run=dry_run)
        if code != 0:
            return code

    if follow_logs:
        return run_cmd([reana_bin, "logs", "-n", reana_name, "-f"], cwd=workflow_dir, dry_run=dry_run)

    print(f"Workflow submitted to REANA as: {reana_name}")
    print(f"Inspect logs with: reana-client logs -n {reana_name} -f")
    return 0


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    default_workflow_dir = repo_root / "workflows" / "sentinel2_hsi_pilot"

    parser = argparse.ArgumentParser(
        description="Run shared CWL workflows with cwltool or REANA."
    )
    parser.add_argument(
        "--backend",
        choices=["cwltool", "reana"],
        default="cwltool",
        help="Execution backend.",
    )
    parser.add_argument(
        "--workflow-dir",
        default=str(default_workflow_dir),
        help="Directory containing workflow.cwl and reana.yaml.",
    )
    parser.add_argument(
        "--workflow-file",
        default="workflow.cwl",
        help="Workflow CWL filename relative to workflow dir.",
    )
    parser.add_argument(
        "--inputs",
        default="examples/workflow-inputs.yml",
        help="Inputs YAML path (relative to workflow dir or absolute).",
    )
    parser.add_argument(
        "--reana-name",
        default="",
        help="REANA workflow name. If omitted, generated automatically.",
    )
    parser.add_argument(
        "--reana-name-prefix",
        default="shared-cwl",
        help="Name prefix used when --reana-name is omitted.",
    )
    parser.add_argument(
        "--no-follow-logs",
        action="store_true",
        help="For REANA backend, do not stream logs after start.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    workflow_dir = Path(args.workflow_dir).resolve()
    if not workflow_dir.exists():
        print(f"ERROR: workflow directory not found: {workflow_dir}")
        return 2

    inputs_path = Path(args.inputs)
    if not inputs_path.is_absolute():
        inputs_path = (workflow_dir / inputs_path).resolve()

    try:
        if args.backend == "cwltool":
            return run_cwltool(
                workflow_dir=workflow_dir,
                workflow_file=args.workflow_file,
                inputs_file=inputs_path,
                dry_run=args.dry_run,
            )

        ensure_exists(workflow_dir / "reana.yaml", "REANA descriptor")
        reana_name = args.reana_name or infer_reana_name(args.reana_name_prefix)
        return run_reana(
            workflow_dir=workflow_dir,
            reana_name=reana_name,
            follow_logs=not args.no_follow_logs,
            dry_run=args.dry_run,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
