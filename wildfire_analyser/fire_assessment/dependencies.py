# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# Internal dependency definitions for the fire assessment DAG.


from enum import Enum, auto


class Dependency(Enum):
    # Data ingestion and scene selection
    #
    # Initial gathering of satellite imagery and
    # filtering by date, cloud coverage, and ROI.
    COLLECTION_GATHERING = auto()

    # Temporal image collections
    #
    # Pre- and post-fire image collections built
    # from the ingestion step.
    PRE_FIRE_COLLECTION = auto()
    POST_FIRE_COLLECTION = auto()

    # Temporal mosaics
    #
    # Cloud-filtered mosaics generated from the
    # pre- and post-fire collections.
    PRE_FIRE_MOSAIC = auto()
    POST_FIRE_MOSAIC = auto()

    # RGB composites
    #
    # True-color composites derived from mosaics,
    # primarily for visual inspection.
    RGB_PRE_FIRE = auto()
    RGB_POST_FIRE = auto()

    # Spectral indices (continuous values)
    #
    # Burn and vegetation indices computed from
    # pre- and post-fire mosaics.
    NBR_PRE_FIRE = auto()
    NBR_POST_FIRE = auto()
    DNBR = auto()

    NDVI_PRE_FIRE = auto()
    NDVI_POST_FIRE = auto()
    DNDVI = auto()

    RBR = auto()

    # Fire severity metrics (aggregated statistics)
    #
    # Area-based summaries derived from classified
    # burn severity indices.
    DNBR_AREA_STATISTICS = auto()
    DNDVI_AREA_STATISTICS = auto()
    RBR_AREA_STATISTICS = auto()
