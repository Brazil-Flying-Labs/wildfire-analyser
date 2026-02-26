# SPDX-License-Identifier: MIT
#
# Dependency resolution utilities for burn trend pipeline.

from typing import List, Set
from wildfire_analyser.burn_trend.dependency_graph import DEPENDENCY_GRAPH
from wildfire_analyser.burn_trend.dependencies import Dependency


def resolve_dependencies(requested: List[Dependency]) -> List[Dependency]:
    resolved: Set[Dependency] = set()
    visiting: Set[Dependency] = set()
    order: List[Dependency] = []

    def visit(dep: Dependency) -> None:
        if dep in resolved:
            return
        if dep in visiting:
            raise RuntimeError(f"Circular dependency detected: {dep}")

        visiting.add(dep)
        for parent in DEPENDENCY_GRAPH.get(dep, set()):
            visit(parent)
        visiting.remove(dep)
        resolved.add(dep)
        order.append(dep)

    for dep in requested:
        visit(dep)

    return order
