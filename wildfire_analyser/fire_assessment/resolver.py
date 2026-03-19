# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# DAG execution engine for the fire assessment pipeline.


from typing import Dict, Iterable, Any, List

from wildfire_analyser.fire_assessment.deliverables import Deliverable
from wildfire_analyser.fire_assessment.deliverable_dependencies import (
    DELIVERABLE_DEPENDENCIES,
)
from wildfire_analyser.fire_assessment.dependencies import Dependency
from wildfire_analyser.fire_assessment.dependency_resolver import resolve_dependencies
from wildfire_analyser.fire_assessment.products import PRODUCT_REGISTRY

import logging

logger = logging.getLogger(__name__)


class DAGExecutionContext:
    """Store inputs and cached dependency results for DAG execution."""

    def __init__(self, **inputs: Any):
        self.inputs: Dict[str, Any] = inputs
        self.cache: Dict[Dependency, Any] = {}

    def get(self, dep: Dependency) -> Any:
        return self.cache.get(dep)

    def set(self, dep: Dependency, value: Any) -> None:
        self.cache[dep] = value


def execute_dag(
    deliverables: Iterable[Deliverable],
    context: DAGExecutionContext,
) -> Dict[Deliverable, Any]:
    """Execute the DAG for the requested deliverables and return their outputs."""

    # 1. Map deliverables to required dependencies
    requested_dependencies: List[Dependency] = []
    for deliverable in deliverables:
        deps = DELIVERABLE_DEPENDENCIES.get(deliverable)
        if deps is None:
            raise KeyError(
                f"No dependencies defined for deliverable {deliverable}")
        requested_dependencies.extend(deps)

    # 2. Resolve full dependency order
    execution_order = resolve_dependencies(requested_dependencies)

    # 3. Execute dependencies in order
    for dep in execution_order:
        if dep in context.cache:
            continue

        logger.info("[DAG] Executing dependency: %s", dep.name)

        executor = PRODUCT_REGISTRY.get(dep)
        if executor is None:
            raise KeyError(
                f"No product executor registered for dependency {dep}")

        result = executor(context)
        context.set(dep, result)

    # 4. Collect final deliverables
    outputs: Dict[Deliverable, Any] = {}
    for deliverable in deliverables:
        deps = DELIVERABLE_DEPENDENCIES[deliverable]
        if len(deps) != 1:
            raise RuntimeError(
                f"Deliverable {deliverable} must map to exactly one dependency"
            )
        dep = next(iter(deps))
        outputs[deliverable] = context.get(dep)

    return outputs
