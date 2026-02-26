# SPDX-License-Identifier: MIT
#
# Deliverable to dependency mapping for burn trend DAG.

from wildfire_analyser.burn_trend.deliverables import Deliverable
from wildfire_analyser.burn_trend.dependencies import Dependency

DELIVERABLE_DEPENDENCIES = {
    Deliverable.REPORT: {Dependency.REPORT_JSON},
}
