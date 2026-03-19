# wildfire-analyser

`wildfire-analyser` is a Python library for post-fire assessment with Sentinel-2 imagery in Google Earth Engine. It generates three kinds of outputs from a region of interest (ROI): scientific rasters, visual previews, and burned-area statistics.

The project is organized around a dependency-driven workflow, so the CLI only computes what is required for the deliverables you request.

## What It Produces

- Scientific products exported as GeoTIFFs to Google Cloud Storage
- Visual products returned as Google Earth Engine thumbnail URLs
- Burned-area statistics for dNBR, dNDVI, and RBR

## Requirements

Before running the CLI, prepare:

- A GeoJSON polygon file for the ROI
- A Google Earth Engine service account credential in `GEE_PRIVATE_KEY_JSON`
- A Google Cloud Storage bucket name in `GCS_BUCKET_NAME` if you request scientific deliverables

`GCS_BUCKET_NAME` is only required for scientific deliverables exported to Google Cloud Storage. Visual outputs and statistics do not require a bucket.

## Quickstart (Repository)

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp wildfire_analyser/.env.template .env
```

Then edit `.env` with your real Earth Engine credentials and, if needed, your bucket name. Place your ROI GeoJSON under `polygons/`.

Example layout:

```text
.
├── .env
├── polygons/
│   └── ccanakkale01.geojson
└── venv/
```

## Run the CLI

Minimal example:

```bash
./venv/bin/python -m wildfire_analyser.cli \
  --roi polygons/ccanakkale01.geojson \
  --start-date 2023-07-01 \
  --end-date 2023-07-21 \
  --deliverables DNBR_VISUAL DNBR_AREA_STATISTICS
```

Example with more outputs:

```bash
./venv/bin/python -m wildfire_analyser.cli \
  --roi polygons/eejatai.geojson \
  --start-date 2024-09-26 \
  --end-date 2024-10-05 \
  --deliverables RGB_PRE_FIRE_VISUAL RGB_POST_FIRE_VISUAL DNBR_VISUAL DNBR_AREA_STATISTICS
```

If `--deliverables` is omitted, the CLI requests every deliverable defined in [`wildfire_analyser/fire_assessment/deliverables.py`](/home/marcelo/code/wildfire-analyser/wildfire_analyser/fire_assessment/deliverables.py).

## Deliverables

Scientific:
`RGB_PRE_FIRE`, `RGB_POST_FIRE`, `NDVI_PRE_FIRE`, `NDVI_POST_FIRE`, `NBR_PRE_FIRE`, `NBR_POST_FIRE`, `DNDVI`, `DNBR`, `RBR`

Visual:
`RGB_PRE_FIRE_VISUAL`, `RGB_POST_FIRE_VISUAL`, `DNDVI_VISUAL`, `DNBR_VISUAL`, `RBR_VISUAL`

Statistics:
`DNBR_AREA_STATISTICS`, `DNDVI_AREA_STATISTICS`, `RBR_AREA_STATISTICS`

## Useful Flags

- `--days-before-after`: temporal buffer around the event window. Default: `30`
- `--cloud-threshold`: maximum `CLOUDY_PIXEL_PERCENTAGE`. Default: `100`
- `--fire-mosaic-strategy`: one of `best_date_mosaic`, `best_date_masked_mosaic`, `best_available_per_tile_mosaic`, `cloud_masked_light_mosaic`
- `--roi-only`: clips visual thumbnails to the ROI footprint instead of its bounding box

Full CLI help:

```bash
./venv/bin/python -m wildfire_analyser.cli --help
```

## Paper Preset

The CLI includes one preset for the Canakkale case study:

```bash
./venv/bin/python -m wildfire_analyser.cli \
  --deliverables PAPER_DENIZ_FUSUN_RAMAZAN
```

This preset runs two predefined ROIs, produces visual outputs and statistics, and compares the computed statistics against the reference values embedded in the CLI implementation.

The preset uses its own fixed internal configuration for scene selection. 

## Notes on Methodology

The implementation follows the same general analytical structure used in the Canakkale wildfire case study: Sentinel-2 composites, dNBR, dNDVI, RBR, severity-class statistics, and reproducible execution through a fixed workflow. For the paper preset, the intent is reproducible selection under preset-defined conditions rather than a user-adjustable temporal window. Numerical differences can still occur because of cloud filtering, mosaic strategy, and Earth Engine execution details.

## Additional Docs

- Environment setup: [`docs/environment-setup.md`](/home/marcelo/code/wildfire-analyser/docs/environment-setup.md)
- GEE task monitoring: [`docs/gee_task_monitoring.md`](/home/marcelo/code/wildfire-analyser/docs/gee_task_monitoring.md)
- Development notes: [`docs/development.md`](/home/marcelo/code/wildfire-analyser/docs/development.md)
