#!/usr/bin/env python3
"""Generate fixtures and execute both CWL workflows with cwltool."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEMO = ROOT / ".demo"


def run(command: list[str]) -> None:
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    if DEMO.exists():
        shutil.rmtree(DEMO)
    (DEMO / "sentinel").mkdir(parents=True)
    (DEMO / "dji").mkdir(parents=True)
    run([sys.executable, "examples/generate_demo_inputs.py"])
    run([
        "cwltool", "--outdir", str(DEMO / "sentinel"),
        "sentinel2-workflow.cwl", "examples/sentinel2-inputs.yml",
    ])
    run([
        "cwltool", "--outdir", str(DEMO / "dji"),
        "dji-workflow.cwl", "examples/dji-inputs.yml",
    ])
    print(f"Demo passed. Results: {DEMO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())