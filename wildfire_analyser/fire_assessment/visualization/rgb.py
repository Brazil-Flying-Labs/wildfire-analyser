# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# RGB visualization renderers for pre- and post-fire imagery.


import ee

def rgb_pre_fire_visual(image: ee.Image, roi: ee.Geometry) -> ee.Image:
    return image.visualize(
        bands=["RED_refl", "GREEN_refl", "BLUE_refl"],
        min=0.02,
        max=0.30,
        gamma=1.2,
    )


def rgb_post_fire_visual(image: ee.Image, roi: ee.Geometry) -> ee.Image:
    return image.visualize(
        bands=["RED_refl", "GREEN_refl", "BLUE_refl"],
        min=0.02,
        max=0.30,
        gamma=1.2,
    )
