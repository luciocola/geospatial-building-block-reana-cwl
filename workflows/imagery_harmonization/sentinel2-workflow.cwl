cwlVersion: v1.2
class: Workflow
label: Sentinel-2 Harmonization Reference
doc: Create a common grid, enhanced RGB reference COG, histogram profile, STAC Item, and provenance.
inputs:
  source_rgb: File
  target_crs: string
  target_resolution: float
  input_scale:
    type: float
    default: 10000.0
  method:
    type: string
    default: bicubic-demo
  model: File?
  model_card: File?
  expected_model_sha256: string?
  run_id: string
steps:
  prepare_reference:
    run: steps/process-sentinel2.cwl
    in:
      source_rgb: source_rgb
      target_crs: target_crs
      target_resolution: target_resolution
      input_scale: input_scale
      method: method
      model: model
      model_card: model_card
      expected_model_sha256: expected_model_sha256
      run_id: run_id
    out:
      - sentinel2_harmonized
      - reference_histogram
      - target_grid
      - sentinel2_quality
      - sentinel2_stac_item
      - sentinel2_provenance
outputs:
  sentinel2_harmonized:
    type: File
    outputSource: prepare_reference/sentinel2_harmonized
  reference_histogram:
    type: File
    outputSource: prepare_reference/reference_histogram
  target_grid:
    type: File
    outputSource: prepare_reference/target_grid
  sentinel2_quality:
    type: File
    outputSource: prepare_reference/sentinel2_quality
  sentinel2_stac_item:
    type: File
    outputSource: prepare_reference/sentinel2_stac_item
  sentinel2_provenance:
    type: File
    outputSource: prepare_reference/sentinel2_provenance