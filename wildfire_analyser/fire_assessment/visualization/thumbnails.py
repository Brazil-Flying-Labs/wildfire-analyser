# SPDX-License-Identifier: MIT
#
# Earth Engine thumbnail generation helpers.
#
# This module provides a lightweight helper for generating visualization
# thumbnails from Earth Engine Images. Thumbnails are intended for preview
# and reporting purposes only and are generated using the Earth Engine
# thumbnail service.
#
# Design notes:
# - Earth Engine objects are evaluated lazily until getThumbURL() is called.
# - Thumbnail generation triggers server-side execution but returns
#   immediately with a signed URL.
# - Thumbnails can either be clipped strictly to the ROI or rendered over the
#   full ROI bounding box while preserving pixels outside the ROI.
# - Fixed dimensions are used instead of scale to avoid Earth Engine pixel
#   grid and request size limitations.
#
# Responsibilities of this module:
# - Generate stable thumbnail URLs for visual deliverables.
# - Apply ROI masking and white background outside the ROI.
# - Define thumbnail rendering parameters (dimensions, format).
#
# Copyright (C) 2025
# Marcelo Camargo.
#
# This file is part of wildfire-analyser and is distributed under the terms
# of the MIT license. See the LICENSE file for details.


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
