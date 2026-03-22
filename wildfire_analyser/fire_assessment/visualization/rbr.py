# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# RBR classification and visualization renderer.


import ee


def rbr_visual(image: ee.Image, roi: ee.Geometry) -> ee.Image:
    # Paper-style threshold classification.
    classified = (
        ee.Image(0).updateMask(image.mask())  # Unburned
        .where(image.gte(0.10).And(image.lt(0.27)), 1)   # Low
        .where(image.gte(0.27).And(image.lt(0.44)), 2)  # Moderate
        .where(image.gte(0.44).And(image.lt(0.66)), 3)  # High
        .where(image.gte(0.66), 4)                      # Very High
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

    outline = ee.Image().byte().paint(
        ee.FeatureCollection(roi),
        color=1,
        width=4,
    )

    return styled.blend(outline.visualize(palette=["000000"]))
