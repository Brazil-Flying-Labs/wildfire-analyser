# SPDX-License-Identifier: MIT
#
# Sentinel-2 data access and preprocessing utilities (burn trend).

import ee

COLLECTION_ID = "COPERNICUS/S2_SR_HARMONIZED"


def _scale_reflectance(image: ee.Image) -> ee.Image:
    bands = ["B2", "B3", "B4", "B8", "B11", "B12"]
    refl = image.select(bands).multiply(0.0001)
    refl_names = [f"{b}_refl" for b in bands]
    return image.addBands(refl.rename(refl_names), overwrite=True)


def _mask_clouds(image: ee.Image) -> ee.Image:
    scl = image.select("SCL")
    invalid = (
        scl.eq(1)
        .Or(scl.eq(3))
        .Or(scl.eq(9))
        .Or(scl.eq(10))
    )
    return image.updateMask(invalid.Not())


def gather_collection(roi: ee.Geometry, start_date: str, end_date: str,
                      cloud_threshold: int | None) -> ee.ImageCollection:
    collection = ee.ImageCollection(COLLECTION_ID).filterBounds(roi)

    if start_date and end_date:
        collection = collection.filterDate(start_date, end_date)

    if cloud_threshold is not None:
        collection = collection.filter(
            ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", cloud_threshold)
        )

    return collection.map(_mask_clouds).map(_scale_reflectance)
