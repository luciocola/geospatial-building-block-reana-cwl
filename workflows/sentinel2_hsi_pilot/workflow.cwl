cwlVersion: v1.2
class: Workflow
label: Sentinel-2 to HSI Classification (Pilot)
doc: |
  Pilot multi-step workflow designed for REANA execution and provenance capture.

inputs:
  aoi_geojson:
    type: File
  acquisition_date:
    type: string
  classifier_model:
    type: string
    default: hsi-baseline-v1
  run_id:
    type: string
  layer_name:
    type: string?
  image_path:
    type: string?

steps:
  ingest_sentinel2:
    run: steps/ingest_sentinel2.cwl
    in:
      aoi_geojson: aoi_geojson
      acquisition_date: acquisition_date
      run_id: run_id
    out:
      - ingest_manifest

  preprocess_hsi:
    run: steps/preprocess_hsi.cwl
    in:
      ingest_manifest: ingest_sentinel2/ingest_manifest
      run_id: run_id
    out:
      - hsi_cube_manifest

  classify_hsi:
    run: steps/classify_hsi.cwl
    in:
      hsi_cube_manifest: preprocess_hsi/hsi_cube_manifest
      classifier_model: classifier_model
      run_id: run_id
    out:
      - classification_geojson
      - classification_summary
      - stac_item

  package_provenance:
    run: steps/package_provenance.cwl
    in:
      ingest_manifest: ingest_sentinel2/ingest_manifest
      hsi_cube_manifest: preprocess_hsi/hsi_cube_manifest
      classification_geojson: classify_hsi/classification_geojson
      classification_summary: classify_hsi/classification_summary
      stac_item: classify_hsi/stac_item
      run_id: run_id
      layer_name: layer_name
      image_path: image_path
    out:
      - provenance_bundle
      - workflow_prov_profile

outputs:
  classification_geojson:
    type: File
    outputSource: classify_hsi/classification_geojson
  classification_summary:
    type: File
    outputSource: classify_hsi/classification_summary
  stac_item:
    type: File
    outputSource: classify_hsi/stac_item
  provenance_bundle:
    type: File
    outputSource: package_provenance/provenance_bundle
  workflow_prov_profile:
    type: File
    outputSource: package_provenance/workflow_prov_profile
  provenance_verification:
    type: File
    outputSource: package_provenance/provenance_verification
