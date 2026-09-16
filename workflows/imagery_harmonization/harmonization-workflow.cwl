cwlVersion: v1.2
class: Workflow
label: Sentinel-2 and DJI Imagery Harmonization
doc: Create a Sentinel-2 reference, harmonize an orthorectified DJI mosaic to it, and apply the comparability gate.
inputs:
  source_rgb: File
  orthomosaic: File
  target_crs: string
  target_resolution: float
  sentinel_input_scale:
    type: float
    default: 10000.0
  dji_input_scale:
    type: float
    default: 10000.0
  method:
    type: string
    default: bicubic-demo
  model: File?
  model_card: File?
  expected_model_sha256: string?
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
  prepare_reference:
    run: steps/process-sentinel2.cwl
    in:
      source_rgb: source_rgb
      target_crs: target_crs
      target_resolution: target_resolution
      input_scale: sentinel_input_scale
      method: method
      model: model
      model_card: model_card
      expected_model_sha256: expected_model_sha256
      run_id: run_id
    out: [sentinel2_harmonized, reference_histogram, target_grid, sentinel2_quality, sentinel2_stac_item, sentinel2_provenance]
  harmonize_dji:
    run: steps/process-dji.cwl
    in:
      orthomosaic: orthomosaic
      target_grid: prepare_reference/target_grid
      reference_histogram: prepare_reference/reference_histogram
      input_scale: dji_input_scale
      checkpoint_rmse_pixels: checkpoint_rmse_pixels
      cloud_shadow_fraction: cloud_shadow_fraction
      run_id: run_id
    out: [dji_harmonized, dji_histograms, dji_quality, dji_stac_item, dji_provenance]
  assess_pair:
    run: steps/assess-comparability.cwl
    in:
      reference_image: prepare_reference/sentinel2_harmonized
      comparison_image: harmonize_dji/dji_harmonized
      dji_quality: harmonize_dji/dji_quality
      min_overlap_pixels: min_overlap_pixels
      max_js_distance: max_js_distance
      max_clipping_fraction: max_clipping_fraction
      max_registration_rmse_pixels: max_registration_rmse_pixels
      max_cloud_shadow_fraction: max_cloud_shadow_fraction
    out: [comparability_report]
outputs:
  sentinel2_harmonized: {type: File, outputSource: prepare_reference/sentinel2_harmonized}
  reference_histogram: {type: File, outputSource: prepare_reference/reference_histogram}
  target_grid: {type: File, outputSource: prepare_reference/target_grid}
  sentinel2_quality: {type: File, outputSource: prepare_reference/sentinel2_quality}
  sentinel2_stac_item: {type: File, outputSource: prepare_reference/sentinel2_stac_item}
  sentinel2_provenance: {type: File, outputSource: prepare_reference/sentinel2_provenance}
  dji_harmonized: {type: File, outputSource: harmonize_dji/dji_harmonized}
  dji_histograms: {type: File, outputSource: harmonize_dji/dji_histograms}
  dji_quality: {type: File, outputSource: harmonize_dji/dji_quality}
  dji_stac_item: {type: File, outputSource: harmonize_dji/dji_stac_item}
  dji_provenance: {type: File, outputSource: harmonize_dji/dji_provenance}
  comparability_report: {type: File, outputSource: assess_pair/comparability_report}
