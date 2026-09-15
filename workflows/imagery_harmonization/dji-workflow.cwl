cwlVersion: v1.2
class: Workflow
label: DJI Orthomosaic Harmonization and Comparison
doc: Downsample an orthorectified DJI mosaic to the reference grid, match RGB distributions, and enforce quality gates.
inputs:
  orthomosaic: File
  reference_image: File
  target_grid: File
  reference_histogram: File
  input_scale:
    type: float
    default: 10000.0
  checkpoint_rmse_pixels:
    type: float
    default: 0.0
  cloud_shadow_fraction:
    type: float
    default: 0.0
  min_overlap_pixels:
    type: int
    default: 10000
  max_js_distance:
    type: float
    default: 0.10
  max_clipping_fraction:
    type: float
    default: 0.01
  max_registration_rmse_pixels:
    type: float
    default: 1.0
  max_cloud_shadow_fraction:
    type: float
    default: 0.05
  run_id: string
steps:
  harmonize_dji:
    run: steps/process-dji.cwl
    in:
      orthomosaic: orthomosaic
      target_grid: target_grid
      reference_histogram: reference_histogram
      input_scale: input_scale
      checkpoint_rmse_pixels: checkpoint_rmse_pixels
      cloud_shadow_fraction: cloud_shadow_fraction
      run_id: run_id
    out:
      - dji_harmonized
      - dji_histograms
      - dji_quality
      - dji_stac_item
      - dji_provenance
  assess_pair:
    run: steps/assess-comparability.cwl
    in:
      reference_image: reference_image
      comparison_image: harmonize_dji/dji_harmonized
      dji_quality: harmonize_dji/dji_quality
      min_overlap_pixels: min_overlap_pixels
      max_js_distance: max_js_distance
      max_clipping_fraction: max_clipping_fraction
      max_registration_rmse_pixels: max_registration_rmse_pixels
      max_cloud_shadow_fraction: max_cloud_shadow_fraction
    out:
      - comparability_report
outputs:
  dji_harmonized:
    type: File
    outputSource: harmonize_dji/dji_harmonized
  dji_histograms:
    type: File
    outputSource: harmonize_dji/dji_histograms
  dji_quality:
    type: File
    outputSource: harmonize_dji/dji_quality
  dji_stac_item:
    type: File
    outputSource: harmonize_dji/dji_stac_item
  dji_provenance:
    type: File
    outputSource: harmonize_dji/dji_provenance
  comparability_report:
    type: File
    outputSource: assess_pair/comparability_report