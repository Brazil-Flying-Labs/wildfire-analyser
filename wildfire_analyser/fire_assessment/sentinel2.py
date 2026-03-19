# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# Sentinel-2 data access and preprocessing utilities.


import ee

COLLECTION_ID = "COPERNICUS/S2_SR_HARMONIZED"


def _add_reflectance_bands(image: ee.Image) -> ee.Image:
    bands = ["B2", "B3", "B4", "B8", "B12"]
    refl = image.select(bands).multiply(0.0001)
    refl_names = refl.bandNames().map(lambda b: ee.String(b).cat("_refl"))
    return image.addBands(refl.rename(refl_names))


def gather_collection(
    roi: ee.Geometry,
) -> ee.ImageCollection:
    """Load the Sentinel-2 SR collection for the ROI and add scaled bands."""
    return (
        ee.ImageCollection(COLLECTION_ID)
        .filterBounds(roi)
        .map(_add_reflectance_bands)
    )
