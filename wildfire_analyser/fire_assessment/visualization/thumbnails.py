# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# Earth Engine thumbnail generation helpers.


import ee


def get_visual_thumbnail_url(
    image: ee.Image,
    roi: ee.Geometry,
    roi_only: bool = False,
) -> str:
    if roi_only:
        image = image.clip(roi)
    else:
        image = image.clip(roi.bounds())

    return image.getThumbURL({
        "dimensions": 1024,
        "format": "jpg",
    })
