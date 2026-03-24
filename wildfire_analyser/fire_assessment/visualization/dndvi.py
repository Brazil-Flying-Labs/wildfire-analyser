# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# dNDVI classification and visualization renderer.


import ee


def dndvi_visual(image: ee.Image, roi: ee.Geometry) -> ee.Image:
    # Paper Table 5 thresholds normalized to contiguous intervals.
    classified = (
        ee.Image(0).updateMask(image.mask())  # Unburned (< 0.07)
        .where(image.gte(0.07).And(image.lt(0.20)), 1)   # Low
        .where(image.gte(0.20).And(image.lt(0.33)), 2)   # Moderate
        .where(image.gte(0.33).And(image.lt(0.45)), 3)   # High
        .where(image.gte(0.45), 4)                       # Very High
    )

    styled = classified.visualize(
        min=0,
        max=4,
        palette=[
            "36a402",  # Unburned
            "fbfb01",  # Low
            "feb012",  # Moderate
            "f50003",  # High
            "6a044d",  # Very High
        ],
    )

    return styled
