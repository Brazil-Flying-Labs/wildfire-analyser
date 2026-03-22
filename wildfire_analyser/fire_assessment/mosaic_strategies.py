"""Alternative mosaic strategies for fire assessment workflows.

SPDX-License-Identifier: MIT
Copyright (C) 2025 Marcelo Camargo.
"""

import ee

from enum import Enum

from wildfire_analyser.fire_assessment.sentinel2 import (
    add_quality_band,
    mask_invalid_pixels,
)


class MosaicStrategy(str, Enum):
    """Public-facing mosaic strategy identifiers."""

    # Date-based strategies
    BEST_DATE_MOSAIC = "best_date_mosaic"
    BEST_DATE_MASKED_MOSAIC = "best_date_masked_mosaic"

    # Tile-based strategies (default)
    BEST_AVAILABLE_PER_TILE_MOSAIC = "best_available_per_tile_mosaic"

    # Pixel-based strategies
    CLOUD_MASKED_LIGHT_MOSAIC = "cloud_masked_light_mosaic"


def apply_mosaic_strategy(
    collection: ee.ImageCollection,
    strategy,
    context,
) -> ee.Image:
    """Apply a named mosaic strategy to an ImageCollection."""

    # Accept either an enum value or a raw string.
    if isinstance(strategy, MosaicStrategy):
        strategy = strategy.value

    strategies = {
        MosaicStrategy.BEST_DATE_MOSAIC.value: best_date_mosaic,
        MosaicStrategy.BEST_DATE_MASKED_MOSAIC.value: best_date_masked_mosaic,
        MosaicStrategy.BEST_AVAILABLE_PER_TILE_MOSAIC.value: best_available_per_tile_mosaic,
        MosaicStrategy.CLOUD_MASKED_LIGHT_MOSAIC.value: cloud_masked_light_mosaic,
    }

    func = strategies.get(strategy)
    if func is None:
        raise ValueError(f"Unknown mosaic strategy: '{strategy}'")

    return func(collection, context)


def best_date_mosaic(
    collection: ee.ImageCollection,
    context,
) -> ee.Image:
    """Select the least cloudy sensing date and mosaic all tiles from that date."""

    cloud_threshold = context.inputs.get("cloud_threshold")

    filtered = collection
    if cloud_threshold is not None:
        filtered = filtered.filter(
            ee.Filter.lte("CLOUD_PERCENTAGE", cloud_threshold)
        )

    # Derive the sensing date (YYYY-MM-dd).
    def add_date(image):
        date = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd")
        return image.set("sensing_date", date)

    dated = filtered.map(add_date)

    # Pick the best image to identify the target date.
    best_image = dated.sort("CLOUD_PERCENTAGE").first()
    best_date = best_image.get("sensing_date")

    # Rebuild the collection using all tiles from that date.
    same_date = dated.filter(
        ee.Filter.eq("sensing_date", best_date)
    )

    return same_date.mosaic()


def cloud_masked_light_mosaic(
    collection: ee.ImageCollection,
    context,
) -> ee.Image:
    """Build a pixel-based mosaic using cloud probability as a quality weight."""

    def _pixel_mosaic_by_cloud_prob(
        collection: ee.ImageCollection,
    ) -> ee.Image:
        return (
            collection
            .map(add_quality_band)
            .qualityMosaic("quality")
        )

    masked = collection.map(mask_invalid_pixels)
    mosaic = _pixel_mosaic_by_cloud_prob(masked)

    # Remove the auxiliary quality band from the output.
    return mosaic.select(
        mosaic.bandNames().remove("quality")
    )


def best_date_masked_mosaic(
    collection: ee.ImageCollection,
    context,
) -> ee.Image:
    """Apply invalid-pixel masking to the best-date mosaic."""
    return mask_invalid_pixels(best_date_mosaic(collection, context))


def best_available_per_tile_mosaic(
    collection: ee.ImageCollection,
    context,
) -> ee.Image:
    """Select the best available scene independently for each spatial tile."""

    cloud_threshold = context.inputs.get("cloud_threshold")

    filtered = collection
    if cloud_threshold is not None:
        filtered = filtered.filter(
            ee.Filter.lte("CLOUD_PERCENTAGE", cloud_threshold)
        )

    tiles = ee.List(filtered.aggregate_array("SPATIAL_TILE_ID")).distinct()

    def select_best_for_tile(tile_id):
        tile_collection = (
            filtered
            .filter(ee.Filter.eq("SPATIAL_TILE_ID", tile_id))
            .sort("CLOUD_PERCENTAGE")
        )
        return ee.Image(tile_collection.first())

    per_tile_best = ee.ImageCollection(
        tiles.map(select_best_for_tile)
    )

    return per_tile_best.mosaic()
