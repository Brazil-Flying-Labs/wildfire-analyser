""" 
SPDX-License-Identifier: MIT

Mosaic strategy implementations.

This module defines alternative compositing strategies for combining
multiple satellite acquisitions into a single analysis-ready image.

Each strategy represents a distinct compositing decision policy.

The processing pipeline delegates all compositing decisions to this
module, keeping higher-level code policy-agnostic.

Copyright (C) 2025
Marcelo Camargo.
"""

import ee


def apply_mosaic_strategy(
    collection: ee.ImageCollection,
    strategy: str,
    context,
) -> ee.Image:
    """
    Apply a named mosaic strategy to an ImageCollection.
    """

    strategies = {
        "best_available_scene_raw": best_available_scene_raw,
        "cloud_masked_light_mosaic": cloud_masked_light_mosaic,
        "best_available_scene": best_available_scene,
    }

    func = strategies.get(strategy)
    if func is None:
        raise ValueError(f"Unknown mosaic strategy: '{strategy}'")

    return func(collection, context)


def best_available_scene_raw(
    collection: ee.ImageCollection,
    context,
) -> ee.Image:
    """
    Selects the least cloudy acquisition and mosaics only its tiles.

    - Single acquisition (no temporal mixing)
    - Mosaic is used only to merge spatial tiles
    """

    cloud_threshold = context.inputs.get("cloud_threshold")

    # Select the least cloudy acquisition in the period
    best_scene = (
        collection
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", cloud_threshold))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
        .first()
    )

    # Assumes system:index uniquely identifies an acquisition (Sentinel-2)
    scene_id = best_scene.get("system:index")

    # Rebuild the collection using only images from this acquisition
    same_acquisition = collection.filter(
        ee.Filter.eq("system:index", scene_id)
    )

    # Mosaic is used only to merge spatial tiles
    unified = same_acquisition.mosaic()

    return unified


def cloud_masked_light_mosaic(
    collection: ee.ImageCollection,
    context,
) -> ee.Image:    
    """
    Pixel-based mosaic using cloud probability as a quality weight.

    - Applies a light SCL cloud mask
    - Selects pixels with lower cloud probability across dates
    """
       
    def _mask_scl_light(image: ee.Image) -> ee.Image:
        scl = image.select("SCL")

        # Mask only clearly invalid observations
        invalid = (
            scl.eq(1)
            .Or(scl.eq(3))   # Cloud shadow
            .Or(scl.eq(9))   # High probability cloud
            .Or(scl.eq(10))  # Cirrus
        )
        return image.updateMask(invalid.Not())

    def _pixel_mosaic_by_cloud_prob(
        collection: ee.ImageCollection,
    ) -> ee.Image:

        def add_quality(image: ee.Image) -> ee.Image:
            prob = image.select("MSK_CLDPRB")
            scl = image.select("SCL")

            # Higher quality = lower cloud probability
            quality = ee.Image(100).subtract(prob)

            # Penalize cloud edges without fully masking them
            quality = quality.where(
                scl.eq(8),
                quality.subtract(5)
            )

            return image.addBands(quality.rename("quality"))

        return (
            collection
            .map(add_quality)
            .qualityMosaic("quality")
        )
    
    masked = collection.map(_mask_scl_light)
    mosaic = _pixel_mosaic_by_cloud_prob(masked)

    # Remove auxiliary quality band from output
    return mosaic.select(
        mosaic.bandNames().remove("quality")
    )

def best_available_scene(
    collection: ee.ImageCollection,
    context,
) -> ee.Image:
    """
    Scene-based strategy with physical cloud masking.

    - Single acquisition
    - Applies SCL-based cloud mask
    - Accepts data gaps
    """

    def _mask_scl(image: ee.Image) -> ee.Image:
        """
        Removes physically invalid pixels using the SCL band.
        """

        scl = image.select("SCL")

        invalid = (
            scl.eq(1)        # Saturated / defective
            .Or(scl.eq(3))   # Cloud shadow
            .Or(scl.eq(9))   # Cloud high probability
            .Or(scl.eq(10))  # Cirrus
        )

        return image.updateMask(invalid.Not())

    return _mask_scl(best_available_scene_raw(collection, context))
