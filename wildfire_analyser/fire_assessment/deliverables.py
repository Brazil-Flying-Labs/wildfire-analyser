# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# Deliverable definitions for the fire assessment pipeline.


from enum import Enum, auto


class Deliverable(Enum):
    # Scientific deliverables (GeoTIFF)
    #
    # Quantitative analytical products derived directly from Earth Engine
    # processing. These deliverables represent scientific data intended for
    # export, archival, and downstream quantitative analysis.
    #
    # They are typically materialized as GeoTIFF files and preserve the
    # original numerical values of the computed indices or composites.
    RGB_PRE_FIRE = auto()
    RGB_POST_FIRE = auto()

    NDVI_PRE_FIRE = auto()
    NDVI_POST_FIRE = auto()
    DNDVI = auto()

    NBR_PRE_FIRE = auto()
    NBR_POST_FIRE = auto()
    DNBR = auto()

    RBR = auto()

    # Statistical deliverables
    #
    # Aggregated summaries computed from scientific deliverables, such as
    # burned area by severity class. These deliverables usually trigger
    # immediate Earth Engine execution via getInfo() and return structured
    # numerical results rather than raster data.
    DNBR_AREA_STATISTICS = auto()
    DNDVI_AREA_STATISTICS = auto()
    RBR_AREA_STATISTICS = auto()

    # Visual deliverables (JPEG / Thumbnail)
    #
    # Qualitative representations derived from scientific deliverables.
    # Visual deliverables reuse the same underlying data but differ only in
    # presentation, using color palettes and styling for preview and
    # reporting purposes.
    #
    # These deliverables are not intended for quantitative analysis.
    RGB_PRE_FIRE_VISUAL = auto()
    RGB_POST_FIRE_VISUAL = auto()
    DNDVI_VISUAL = auto()
    DNBR_VISUAL = auto()
    RBR_VISUAL = auto()
