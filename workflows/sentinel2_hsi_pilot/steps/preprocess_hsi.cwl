cwlVersion: v1.2
class: CommandLineTool
label: Build HSI Cube Manifest
baseCommand:
  - python3
  - scripts/preprocess_hsi.py
requirements:
  - class: InlineJavascriptRequirement
inputs:
  ingest_manifest:
    type: File
    inputBinding:
      prefix: --ingest-manifest
  run_id:
    type: string
    inputBinding:
      prefix: --run-id
arguments:
  - prefix: --output-dir
    valueFrom: $(runtime.outdir)
outputs:
  hsi_cube_manifest:
    type: File
    outputBinding:
      glob: hsi_cube_manifest.json
