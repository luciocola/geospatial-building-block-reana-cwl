cwlVersion: v1.2
class: CommandLineTool
label: Package Workflow Provenance
baseCommand:
  - python3
  - scripts/package_provenance.py
requirements:
  - class: InlineJavascriptRequirement
inputs:
  ingest_manifest:
    type: File
    inputBinding:
      prefix: --ingest-manifest
  hsi_cube_manifest:
    type: File
    inputBinding:
      prefix: --hsi-cube-manifest
  classification_geojson:
    type: File
    inputBinding:
      prefix: --classification-geojson
  classification_summary:
    type: File
    inputBinding:
      prefix: --classification-summary
  stac_item:
    type: File
    inputBinding:
      prefix: --stac-item
  run_id:
    type: string
    inputBinding:
      prefix: --run-id
  layer_name:
    type: string?
    inputBinding:
      prefix: --layer-name
  image_path:
    type: string?
    inputBinding:
      prefix: --image-path
arguments:
  - prefix: --output-dir
    valueFrom: $(runtime.outdir)
outputs:
  provenance_bundle:
    type: File
    outputBinding:
      glob: provenance_bundle.json
  workflow_prov_profile:
    type: File
    outputBinding:
      glob: workflow_prov_profile.json
  provenance_verification:
    type: File
    outputBinding:
      glob: provenance_verification.json
