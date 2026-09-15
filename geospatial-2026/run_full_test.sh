#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REGISTER_DIR="$SCRIPT_DIR/process-type-register"
WORKFLOW_DIR="$WORKSPACE_ROOT/workflows/sentinel2_hsi_pilot"
TMP_WORKFLOW_DIR="$WORKFLOW_DIR/.tmp_full_test"
TMP_REGISTER_DIR="$REGISTER_DIR/.tmp_full_test"
SERVER_PID=""

cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_WORKFLOW_DIR" "$TMP_REGISTER_DIR"
}

trap cleanup EXIT

echo "[1/5] Compiling Python helpers"
cd "$WORKSPACE_ROOT"
python3 -m py_compile \
  scripts/run_workflow.py \
  workflows/sentinel2_hsi_pilot/scripts/ingest_sentinel2.py \
  workflows/sentinel2_hsi_pilot/scripts/preprocess_hsi.py \
  workflows/sentinel2_hsi_pilot/scripts/classify_hsi.py \
  workflows/sentinel2_hsi_pilot/scripts/package_provenance.py \
  "$REGISTER_DIR/service/app.py"

echo "[2/5] Running workflow steps and validating provenance profile"
mkdir -p "$TMP_WORKFLOW_DIR"
python3 "$WORKFLOW_DIR/scripts/ingest_sentinel2.py" \
  --aoi-geojson "$WORKFLOW_DIR/examples/aoi.geojson" \
  --acquisition-date "2026-07-10" \
  --run-id "full-test-001" \
  --output-dir "$TMP_WORKFLOW_DIR"
python3 "$WORKFLOW_DIR/scripts/preprocess_hsi.py" \
  --ingest-manifest "$TMP_WORKFLOW_DIR/sentinel2_ingest.json" \
  --run-id "full-test-001" \
  --output-dir "$TMP_WORKFLOW_DIR"
python3 "$WORKFLOW_DIR/scripts/classify_hsi.py" \
  --hsi-cube-manifest "$TMP_WORKFLOW_DIR/hsi_cube_manifest.json" \
  --classifier-model "hsi-baseline-v1" \
  --run-id "full-test-001" \
  --output-dir "$TMP_WORKFLOW_DIR"
python3 "$WORKFLOW_DIR/scripts/package_provenance.py" \
  --ingest-manifest "$TMP_WORKFLOW_DIR/sentinel2_ingest.json" \
  --hsi-cube-manifest "$TMP_WORKFLOW_DIR/hsi_cube_manifest.json" \
  --classification-geojson "$TMP_WORKFLOW_DIR/hsi_classification.geojson" \
  --classification-summary "$TMP_WORKFLOW_DIR/classification_summary.json" \
  --stac-item "$TMP_WORKFLOW_DIR/stac_item.json" \
  --run-id "full-test-001" \
  --output-dir "$TMP_WORKFLOW_DIR"

python3 - <<'PY'
import json
from pathlib import Path
import jsonschema

schema = json.loads(Path('geospatial-2026/provenance-profile/schema/provenance-profile.schema.json').read_text())
prov = json.loads(Path('workflows/sentinel2_hsi_pilot/.tmp_full_test/workflow_prov_profile.json').read_text())
jsonschema.validate(instance=prov, schema=schema)
print('[OK] provenance profile validation passed')
PY

echo "[3/5] Checking process-type register content"
python3 - <<'PY'
import json
from pathlib import Path

records = json.loads(Path('geospatial-2026/process-type-register/records/process-types-records.json').read_text())
features = records.get('features', [])
assert features, 'no register records found'
for feature in features:
    assert feature.get('id', '').startswith('https://example.org/ospd/2026/process-types/'), feature.get('id')
    props = feature.get('properties', {})
    for key in ('prefLabel', 'definition', 'status'):
        assert props.get(key), (feature.get('id'), key)
print('[OK] register records validated:', len(features))

mappings = json.loads(Path('geospatial-2026/process-type-register/mappings/federation-mappings.json').read_text())
relations = {item.get('relation') for item in mappings.get('mappings', [])}
assert {'exactMatch', 'closeMatch', 'broader', 'narrower'}.issubset(relations), relations
print('[OK] federation relations validated:', sorted(relations))
PY

echo "[4/5] Starting local register API"
cd "$REGISTER_DIR"
python3 -m uvicorn app:app --app-dir "$REGISTER_DIR/service" --host 127.0.0.1 --port 8015 >/tmp/ospd_register_test.log 2>&1 &
SERVER_PID=$!

python3 - <<'PY'
import time
import urllib.request
import json

base = 'http://127.0.0.1:8015'
for _ in range(30):
    try:
        with urllib.request.urlopen(base + '/conformance', timeout=1) as resp:
            if resp.status == 200:
                break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit('register API did not become ready')

for path in ['/conformance', '/collections', '/collections/process-types/items?q=classification', '/mappings', '/dcat']:
    with urllib.request.urlopen(base + path, timeout=3) as resp:
        assert resp.status == 200, (path, resp.status)
        body = resp.read().decode('utf-8')
        assert body, path
print('[OK] local register API endpoints responded successfully')
PY

echo "[5/5] Done"
echo "Workflow outputs: $TMP_WORKFLOW_DIR"
echo "Register API: http://127.0.0.1:8015"
