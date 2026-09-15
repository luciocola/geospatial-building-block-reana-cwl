cwlVersion: v1.2
class: CommandLineTool
label: Harmonize DJI Orthomosaic
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
      location: ../scripts/process_dji.py
  helper:
    type: File
    default:
      class: File
      location: ../scripts/raster_contracts.py
  orthomosaic:
    type: File
    inputBinding:
      prefix: --orthomosaic
  target_grid:
    type: File
    inputBinding:
      prefix: --target-grid
  reference_histogram:
    type: File
    inputBinding:
      prefix: --reference-histogram
  input_scale:
    type: float
    default: 10000.0
    inputBinding:
      prefix: --input-scale
  checkpoint_rmse_pixels:
    type: float
    default: 0.0
    inputBinding:
      prefix: --checkpoint-rmse-pixels
  cloud_shadow_fraction:
    type: float
    default: 0.0
    inputBinding:
      prefix: --cloud-shadow-fraction
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
  dji_harmonized:
    type: File
    outputBinding:
      glob: dji_harmonized.tif
  dji_histograms:
    type: File
    outputBinding:
      glob: dji_histograms.json
  dji_quality:
    type: File
    outputBinding:
      glob: dji_quality.json
  dji_stac_item:
    type: File
    outputBinding:
      glob: dji_stac_item.json
  dji_provenance:
    type: File
    outputBinding:
      glob: dji_provenance.json