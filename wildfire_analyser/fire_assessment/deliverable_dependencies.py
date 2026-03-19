# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# Deliverable-to-dependency mapping for the fire assessment DAG.


from wildfire_analyser.fire_assessment.deliverables import Deliverable
from wildfire_analyser.fire_assessment.dependencies import Dependency

DELIVERABLE_DEPENDENCIES = {
    # Scientific deliverables (raw analytical products)
    #
    # These deliverables represent scientific outputs derived directly
    # from Earth Engine processing. They are intended for quantitative
    # analysis, export, and downstream reuse.
    Deliverable.RGB_PRE_FIRE: {Dependency.RGB_PRE_FIRE},
    Deliverable.RGB_POST_FIRE: {Dependency.RGB_POST_FIRE},

    Deliverable.NDVI_PRE_FIRE: {Dependency.NDVI_PRE_FIRE},
    Deliverable.NDVI_POST_FIRE: {Dependency.NDVI_POST_FIRE},
    Deliverable.DNDVI: {Dependency.DNDVI},

    Deliverable.NBR_PRE_FIRE: {Dependency.NBR_PRE_FIRE},
    Deliverable.NBR_POST_FIRE: {Dependency.NBR_POST_FIRE},
    Deliverable.DNBR: {Dependency.DNBR},
    Deliverable.RBR: {Dependency.RBR},

    # Statistical deliverables (derived summaries)
    #
    # These deliverables perform statistical aggregation over scientific
    # products (e.g. area by severity class). They typically trigger
    # immediate Earth Engine execution via getInfo().
    Deliverable.DNBR_AREA_STATISTICS: {Dependency.DNBR_AREA_STATISTICS},
    Deliverable.DNDVI_AREA_STATISTICS: {Dependency.DNDVI_AREA_STATISTICS},
    Deliverable.RBR_AREA_STATISTICS: {Dependency.RBR_AREA_STATISTICS},

    # Visual deliverables (qualitative representations)
    #
    # Visual deliverables reuse the same scientific dependencies as their
    # analytical counterparts but differ only in representation. They are
    # intended for preview, reporting, and qualitative inspection.
    Deliverable.RGB_PRE_FIRE_VISUAL: {Dependency.RGB_PRE_FIRE},
    Deliverable.RGB_POST_FIRE_VISUAL: {Dependency.RGB_POST_FIRE},
    Deliverable.DNDVI_VISUAL: {Dependency.DNDVI},
    Deliverable.RBR_VISUAL: {Dependency.RBR},
    Deliverable.DNBR_VISUAL: {Dependency.DNBR},
}
