cwlVersion: v1.2
class: CommandLineTool
label: Classify HSI Products
baseCommand:
  - python3
  - scripts/classify_hsi.py
requirements:
  - class: InlineJavascriptRequirement
inputs:
  hsi_cube_manifest:
    type: File
    inputBinding:
      prefix: --hsi-cube-manifest
  classifier_model:
    type: string
    inputBinding:
      prefix: --classifier-model
  run_id:
    type: string
    inputBinding:
      prefix: --run-id
arguments:
  - prefix: --output-dir
    valueFrom: $(runtime.outdir)
outputs:
  classification_geojson:
    type: File
    outputBinding:
      glob: hsi_classification.geojson
  classification_summary:
    type: File
    outputBinding:
      glob: classification_summary.json
  stac_item:
    type: File
    outputBinding:
      glob: stac_item.json
