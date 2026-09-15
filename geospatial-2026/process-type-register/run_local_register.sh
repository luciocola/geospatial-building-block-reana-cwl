#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

python3 -m uvicorn app:app --app-dir "$SCRIPT_DIR/service" --host 127.0.0.1 --port 8015
