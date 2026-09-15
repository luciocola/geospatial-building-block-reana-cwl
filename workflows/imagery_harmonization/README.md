# Executable Sentinel-2 and DJI Imagery Harmonization

This package implements the two workflow contracts described in `docs/sentinel2-dji-harmonization-example.md`.

## Implemented Processing

### Sentinel-2 reference workflow

1. Reads a georeferenced, three-band Sentinel-2 L2A RGB GeoTIFF.
2. Reprojects it to the requested CRS and resolution.
3. Uses either:
   - `bicubic-demo`: deterministic cubic-spline enhancement for testing; not AI.
   - `torchscript`: inference with a supplied, versioned TorchScript super-resolution model.
4. Writes a COG, exact grid contract, masked histogram profile, quality report, STAC Item, and checksummed provenance.

### DJI comparison workflow

1. Reads an already orthorectified DJI RGB mosaic produced by ODM/WebODM or equivalent photogrammetry software.
2. Warps it to the exact Sentinel-2 grid with area averaging.
3. Matches each band to the reference distribution with masked empirical-CDF mapping.
4. Writes a COG, before/after histograms, quality report, STAC Item, and checksummed provenance.
5. Fails the CWL job if the pair violates configured spatial, overlap, histogram, clipping, registration, or cloud/shadow gates.

Raw DJI frame bundle adjustment is intentionally not reimplemented here. Use the existing `dji_drone_processor` NodeODM/Docker ODM path, then pass its orthophoto GeoTIFF as `orthomosaic`.

## Install

From this directory:

```bash
python3 -m pip install -r requirements.txt
```

The local workflow also requires `cwltool`.

## Run the Complete Demo

```bash
python3 run_demo.py
```

The script creates two deterministic georeferenced fixtures and writes results to `.demo/sentinel/` and `.demo/dji/`.

Measured fixture result:

- common overlap: 65,536 pixels;
- worst Jensen-Shannon distance before matching: approximately 0.138;
- worst Jensen-Shannon distance after matching: approximately 0.0043;
- clipping fraction: 0;
- all configured acceptance checks pass.

## Run Separately

```bash
python3 examples/generate_demo_inputs.py

cwltool --outdir .demo/sentinel \
  sentinel2-workflow.cwl examples/sentinel2-inputs.yml

cwltool --outdir .demo/dji \
  dji-workflow.cwl examples/dji-inputs.yml
```

For production Sentinel-2 AI inference, change `method` to `torchscript` and add:

```yaml
model:
  class: File
  path: /absolute/path/model.pt
model_card:
  class: File
  path: /absolute/path/model-card.json
```

The model must accept a normalized tensor shaped `[1, 3, height, width]`, return `[1, 3, scaled_height, scaled_width]`, and produce the requested target resolution within 2%. Start from `examples/model-card-template.json`.

## REANA

The two descriptors are `reana-sentinel2.yaml` and `reana-dji.yaml`. A remote deployment must provide a worker image containing the packages in `requirements.txt`. Run Sentinel-2 first, then upload its reference COG, histogram, and target-grid outputs with the DJI inputs and adjust their paths in the DJI job file.

The bundled descriptors demonstrate the file manifests and output contracts. They do not provision an ODM service or a trained model.