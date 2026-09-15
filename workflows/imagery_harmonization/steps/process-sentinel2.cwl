cwlVersion: v1.2
class: CommandLineTool
label: Prepare Sentinel-2 Reference Image
baseCommand: [python3]
requirements:
  InlineJavascriptRequirement: {}
  InitialWorkDirRequirement:
    listing:
      - $(inputs.script)
      - $(inputs.helper)
inputs:
  script:
    type: File
    default:
      class: File
      location: ../scripts/process_sentinel2.py
  helper:
    type: File
    default:
      class: File
      location: ../scripts/raster_contracts.py
  source_rgb:
    type: File
    inputBinding:
      prefix: --source-rgb
  target_crs:
    type: string
    inputBinding:
      prefix: --target-crs
  target_resolution:
    type: float
    inputBinding:
      prefix: --target-resolution
  input_scale:
    type: float
    default: 10000.0
    inputBinding:
      prefix: --input-scale
  method:
    type: string
    default: bicubic-demo
    inputBinding:
      prefix: --method
  model:
    type: File?
    inputBinding:
      prefix: --model
  model_card:
    type: File?
    inputBinding:
      prefix: --model-card
  run_id:
    type: string
    inputBinding:
      prefix: --run-id
arguments:
  - position: -100
    valueFrom: $(inputs.script.basename)
  - prefix: --output-dir
    valueFrom: $(runtime.outdir)
outputs:
  sentinel2_harmonized:
    type: File
    outputBinding:
      glob: sentinel2_harmonized.tif
  reference_histogram:
    type: File
    outputBinding:
      glob: reference_histogram.json
  target_grid:
    type: File
    outputBinding:
      glob: target_grid.json
  sentinel2_quality:
    type: File
    outputBinding:
      glob: sentinel2_quality.json
  sentinel2_stac_item:
    type: File
    outputBinding:
      glob: sentinel2_stac_item.json
  sentinel2_provenance:
    type: File
    outputBinding:
      glob: sentinel2_provenance.json