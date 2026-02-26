# SPDX-License-Identifier: MIT
#
# Dependency graph definition for burn trend pipeline.

from wildfire_analyser.burn_trend.dependencies import Dependency

DEPENDENCY_GRAPH = {
    Dependency.COLLECTION_GATHERING: set(),
    Dependency.MONTH_WINDOWS: set(),
    Dependency.MONTHLY_COMPOSITES: {
        Dependency.COLLECTION_GATHERING,
        Dependency.MONTH_WINDOWS,
    },
    Dependency.NDVI_MONTHLY: {Dependency.MONTHLY_COMPOSITES},
    Dependency.NBR_MONTHLY: {Dependency.MONTHLY_COMPOSITES},
    Dependency.NDFI_MONTHLY: {Dependency.MONTHLY_COMPOSITES},
    Dependency.EVI_MONTHLY: {Dependency.MONTHLY_COMPOSITES},

    Dependency.NDVI_STATS: {Dependency.NDVI_MONTHLY},
    Dependency.NBR_STATS: {Dependency.NBR_MONTHLY},
    Dependency.NDFI_STATS: {Dependency.NDFI_MONTHLY},
    Dependency.EVI_STATS: {Dependency.EVI_MONTHLY},

    Dependency.REPORT_JSON: {
        Dependency.MONTHLY_COMPOSITES,
    },
}
