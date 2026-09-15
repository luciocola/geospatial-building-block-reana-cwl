cwlVersion: v1.2
class: CommandLineTool
label: Assess Harmonized Image Pair
baseCommand: [python3]
requirements:
  InlineJavascriptRequirement: {}
  InitialWorkDirRequirement:
    listing:
      - $(inputs.script)
      - $(inputs.helper)
      - $(inputs.dji_module)
inputs:
  script:
    type: File
    default:
      class: File
      location: ../scripts/assess_comparability.py
  helper:
    type: File
    default:
      class: File
      location: ../scripts/raster_contracts.py
  dji_module:
    type: File
    default:
      class: File
      location: ../scripts/process_dji.py
  reference_image:
    type: File
    inputBinding:
      prefix: --reference-image
  comparison_image:
    type: File
    inputBinding:
      prefix: --comparison-image
  dji_quality:
    type: File
    inputBinding:
      prefix: --dji-quality
  min_overlap_pixels:
    type: int
    default: 10000
    inputBinding:
      prefix: --min-overlap-pixels
  max_js_distance:
    type: float
    default: 0.10
    inputBinding:
      prefix: --max-js-distance
  max_clipping_fraction:
    type: float
    default: 0.01
    inputBinding:
      prefix: --max-clipping-fraction
  max_registration_rmse_pixels:
    type: float
    default: 1.0
    inputBinding:
      prefix: --max-registration-rmse-pixels
  max_cloud_shadow_fraction:
    type: float
    default: 0.05
    inputBinding:
      prefix: --max-cloud-shadow-fraction
arguments:
  - position: -100
    valueFrom: $(inputs.script.basename)
  - prefix: --output-dir
    valueFrom: $(runtime.outdir)
outputs:
  comparability_report:
    type: File
    outputBinding:
      glob: comparability_report.json