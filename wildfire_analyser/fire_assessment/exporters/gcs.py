# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# Google Cloud Storage export helpers for Earth Engine products.


import ee


def export_geotiff_to_gcs(
    image: ee.Image,
    roi: ee.Geometry,
    bucket: str,
    object_name: str,
    scale: int
) -> dict:
    task = ee.batch.Export.image.toCloudStorage(
        image=image,
        description=object_name,
        bucket=bucket,
        fileNamePrefix=object_name,
        region=roi,
        scale=scale,
        maxPixels=1e13,
        fileFormat="GeoTIFF",
    )
    task.start()

    return {
        "url": f"https://storage.googleapis.com/{bucket}/{object_name}.tif",
        "gee_task_id": task.id,
    }
