# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# RGB visualization renderers for pre- and post-fire imagery.


import ee


def _outline(roi):
    return ee.Image().byte().paint(
        featureCollection=ee.FeatureCollection(roi),
        color=1,
        width=4,
    )


def rgb_pre_fire_visual(image: ee.Image, roi: ee.Geometry) -> ee.Image:
    vis = image.visualize(
        bands=["red", "green", "blue"],
        min=0.02,
        max=0.30,
        gamma=1.2,
    )
    return vis.blend(_outline(roi).visualize(palette=["000000"]))


def rgb_post_fire_visual(image: ee.Image, roi: ee.Geometry) -> ee.Image:
    vis = image.visualize(
        bands=["red", "green", "blue"],
        min=0.02,
        max=0.30,
        gamma=1.2,
    )
    return vis.blend(_outline(roi).visualize(palette=["000000"]))
