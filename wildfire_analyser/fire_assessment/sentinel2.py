# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# Sentinel-2 data access and preprocessing utilities.


import ee

from wildfire_analyser.fire_assessment.bands import (
    SENTINEL2_REFLECTANCE_BAND_MAP,
    reflectance_band_name,
)

COLLECTION_ID = "COPERNICUS/S2_SR_HARMONIZED"


def native_scale_meters() -> int:
    return 10


def _add_reflectance_bands(image: ee.Image) -> ee.Image:
    source_bands = list(SENTINEL2_REFLECTANCE_BAND_MAP.keys())
    reflectance_bands = [
        reflectance_band_name(acronym)
        for acronym in SENTINEL2_REFLECTANCE_BAND_MAP.values()
    ]
    refl = image.select(source_bands).multiply(0.0001)
    return (
        image.addBands(refl.rename(reflectance_bands))
        .set("CLOUD_PERCENTAGE", image.get("CLOUDY_PIXEL_PERCENTAGE"))
        .set("SPATIAL_TILE_ID", image.get("MGRS_TILE"))
    )


def gather_collection(
    roi: ee.Geometry,
) -> ee.ImageCollection:
    """Load the Sentinel-2 SR collection for the ROI and add scaled bands."""
    return (
        ee.ImageCollection(COLLECTION_ID)
        .filterBounds(roi)
        .map(_add_reflectance_bands)
    )


def mask_invalid_pixels(image: ee.Image) -> ee.Image:
    scl = image.select("SCL")

    invalid = (
        scl.eq(1)
        .Or(scl.eq(3))
        .Or(scl.eq(9))
        .Or(scl.eq(10))
    )

    return image.updateMask(invalid.Not())


def add_quality_band(image: ee.Image) -> ee.Image:
    prob = image.select("MSK_CLDPRB")
    scl = image.select("SCL")

    quality = ee.Image(100).subtract(prob)
    quality = quality.where(
        scl.eq(8),
        quality.subtract(5),
    )

    return image.addBands(quality.rename("quality"))
