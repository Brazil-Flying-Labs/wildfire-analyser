# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# Dependency resolution utilities for the fire assessment DAG.


from typing import List, Set
from wildfire_analyser.fire_assessment.dependency_graph import DEPENDENCY_GRAPH
from wildfire_analyser.fire_assessment.dependencies import Dependency


def resolve_dependencies(requested: List[Dependency]) -> List[Dependency]:
    """Return all required dependencies in a valid execution order."""

    resolved: Set[Dependency] = set()
    temporary: Set[Dependency] = set()
    result: List[Dependency] = []

    def visit(dep: Dependency):
        if dep in resolved:
            return
        if dep in temporary:
            raise RuntimeError(f"Circular dependency detected: {dep}")

        temporary.add(dep)

        for parent in DEPENDENCY_GRAPH.get(dep, set()):
            visit(parent)

        temporary.remove(dep)
        resolved.add(dep)
        result.append(dep)

    for dependency in requested:
        visit(dependency)

    return result
