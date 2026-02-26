# SPDX-License-Identifier: MIT
#
# Processing dependency definitions for burn trend DAG.

from enum import Enum, auto


class Dependency(Enum):
    COLLECTION_GATHERING = auto()
    MONTH_WINDOWS = auto()
    MONTHLY_COMPOSITES = auto()

    NDVI_MONTHLY = auto()
    NBR_MONTHLY = auto()
    NDFI_MONTHLY = auto()
    EVI_MONTHLY = auto()

    NDVI_STATS = auto()
    NBR_STATS = auto()
    NDFI_STATS = auto()
    EVI_STATS = auto()

    REPORT_JSON = auto()
