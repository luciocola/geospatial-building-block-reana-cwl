cwlVersion: v1.2
class: CommandLineTool
label: Ingest Sentinel-2 Metadata
baseCommand:
  - python3
  - scripts/ingest_sentinel2.py
requirements:
  - class: InlineJavascriptRequirement
inputs:
  aoi_geojson:
    type: File
    inputBinding:
      prefix: --aoi-geojson
  acquisition_date:
    type: string
    inputBinding:
      prefix: --acquisition-date
  run_id:
    type: string
    inputBinding:
      prefix: --run-id
arguments:
  - prefix: --output-dir
    valueFrom: $(runtime.outdir)
outputs:
  ingest_manifest:
    type: File
    outputBinding:
      glob: sentinel2_ingest.json
