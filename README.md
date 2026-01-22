# wildfire-analyser

Python project for **post-fire assessment and burned area analysis** using **Sentinel-2 imagery** and **Google Earth Engine (GEE)**.

This project supports multiple spectral indices (**dNBR, dNDVI, RBR**), visual products, and paper-ready burned area statistics.

---

## Scientific Background

This project is **based on the peer-reviewed study**:

> **Spatial and statistical analysis of burned areas with Landsat-8/9 and Sentinel-2 satellites: 2023 Çanakkale forest fires**
> **Authors:** Deniz Bitek, Fusun Balik Sanli, Ramazan Cuneyt Erenoglu
> **Study area:** Çanakkale Province, Turkey

The methodology implemented in `wildfire-analyser` follows the **same analytical framework and burn severity thresholds** described in the paper, particularly for the **Sentinel-2–based analysis**, including:

* dNBR, dNDVI and RBR indices
* Burn severity classification tables
* Area statistics in hectares and percentage

Minor numerical differences may occur due to cloud masking, spatial sampling, and Google Earth Engine implementation details.

---

## Installation and Usage

Follow the steps below to install and test `wildfire-analyser` inside an isolated environment:

```bash
mkdir test
cd test

python3 -m venv venv
source venv/bin/activate

pip install wildfire-analyser
```

---

## Required Files Before Running the Client

Before running the client, you **must** prepare the following items:

---

### 1. Add a GeoJSON polygon (ROI)

Create a folder named `polygons` in the project root and place your ROI polygon file inside it:

```
/tmp/test/
├── polygons/
│   └── your_polygon.geojson
└── venv/
```

Example GeoJSON files are available in the repository (e.g. `canakkale_aoi_1.geojson`).

---

### 2. Create the `.env` file with GEE credentials

In the project root, add a `.env` file containing your Google Earth Engine authentication variables.

A `.env.template` file is available in the repository.

```
/tmp/test/
├── .env
├── polygons/
└── venv/
```

---

## Running the Client (Standard Mode)

After adding the `.env` file and your GeoJSON polygon:

```bash
python3 -m wildfire_analyser.client \
  --roi polygons/canakkale_aoi_1.geojson \
  --start-date 2023-07-01 \
  --end-date 2023-07-21 \
  --deliverables \
    DNBR_VISUAL \
    DNDVI_VISUAL \
    RBR_VISUAL \
    DNBR_AREA_STATISTICS \
    DNDVI_AREA_STATISTICS \
    RBR_AREA_STATISTICS \
  --days-before-after 1

```

This will:

* Run the post-fire assessment pipeline
* Generate **visual thumbnail URLs**
* Generate **scientific GeoTIFF outputs** (when applicable)
* Compute **burned area statistics**
* Print all results to the terminal

---

## Deliverables

You may explicitly select deliverables using `--deliverables`.

### Scientific products

* `RGB_PRE_FIRE`
* `RGB_POST_FIRE`
* `NDVI_PRE_FIRE`
* `NDVI_POST_FIRE`
* `NBR_PRE_FIRE`
* `NBR_POST_FIRE`
* `DNDVI`
* `DNBR`
* `RBR`

### Visual products

* `RGB_PRE_FIRE_VISUAL`
* `RGB_POST_FIRE_VISUAL`
* `DNDVI_VISUAL`
* `DNBR_VISUAL`
* `RBR_VISUAL`

### Severity maps and statistics

* `DNBR_AREA_STATISTICS`
* `DNDVI_AREA_STATISTICS`
* `RBR_AREA_STATISTICS`

Example:

```bash
python3 -m wildfire_analyser.client \
   --roi polygons/canakkale_aoi_1.geojson \
   --start-date 2023-07-01 \
   --end-date 2023-07-21 \
   --deliverables DNBR_VISUAL DNBR_AREA_STATISTICS \
   --days-before-after 1
```

If `--deliverables` is **not provided**, **all available deliverables** are generated.

---

## Paper Preset Mode (Reproducibility)

The client also supports **paper presets**, which are predefined experimental configurations designed to reproduce published results.

### Example preset: `PAPER_DENIZ_FUSUN_RAMAZAN`

Run:

```bash
python3 -m wildfire_analyser.client \
  --deliverables PAPER_DENIZ_FUSUN_RAMAZAN
```

This preset:

* Executes the analysis for **two distinct burned areas**
* Uses **paper-aligned temporal windows**
* Generates **only visual outputs and statistics**
* Does **not export scientific GeoTIFFs**
* Prints results **grouped by area**

Internally, it runs:

| Area   | ROI                       | Pre-fire   | Post-fire  |
| ------ | ------------------------- | ---------- | ---------- |
| Area 1 | `canakkale_aoi_1.geojson` | 2023-07-01 | 2023-07-21 |
| Area 2 | `canakkale_aoi_2.geojson` | 2023-07-31 | 2023-08-30 |

---

## Help

For help and full usage information:

```bash
python3 -m wildfire_analyser.client --help
```

---

## Setup Instructions for Developers

1. **Clone the repository**

```bash
git clone git@github.com:camargo-advanced/wildfire-analyser.git
cd wildfire-analyser
```

2. **Create a virtual environment**

```bash
python3 -m venv venv
```

3. **Activate the virtual environment**

```bash
source venv/bin/activate
```

4. **Install dependencies**

```bash
pip install -r requirements.txt
```

5. **Configure environment variables**

Copy your `.env` file to the project root.
A `.env.template` file is provided.

6. **Run the sample client**

```bash
python3 -m wildfire_analyser.client \
   --roi polygons/canakkale_aoi_1.geojson \
   --start-date 2023-07-01 \
   --end-date 2023-07-21 \
   --days-before-after 1
```

---

## Useful Commands

### Deactivate the virtual environment

```bash
deactivate
```

### Build and publish a new PyPI release

```bash
rm -rf dist/*
python -m build
twine upload dist/*
```

---

## Citation

If you use this software for scientific work, please cite:

> *Spatial and statistical analysis of burned areas with Landsat-8/9 and Sentinel-2 satellites: 2023 Çanakkale forest fires*
> Deniz Bitek, Fusun Balik Sanli, Ramazan Cuneyt Erenoglu.

And cite this repository as the reference implementation.