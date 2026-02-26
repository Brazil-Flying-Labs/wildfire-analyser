# SPDX-License-Identifier: MIT
#
# DAG execution engine for burn trend pipeline.

from typing import Dict, Iterable, Any, List
import logging

from wildfire_analyser.burn_trend.deliverables import Deliverable
from wildfire_analyser.burn_trend.deliverable_dependencies import (
    DELIVERABLE_DEPENDENCIES,
)
from wildfire_analyser.burn_trend.dependencies import Dependency
from wildfire_analyser.burn_trend.dependency_resolver import resolve_dependencies
from wildfire_analyser.burn_trend.products import PRODUCT_REGISTRY

logger = logging.getLogger(__name__)


class DAGExecutionContext:
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
    requested_dependencies: List[Dependency] = []
    for deliverable in deliverables:
        deps = DELIVERABLE_DEPENDENCIES.get(deliverable)
        if deps is None:
            raise KeyError(f"No dependencies defined for deliverable {deliverable}")
        requested_dependencies.extend(deps)

    execution_order = resolve_dependencies(requested_dependencies)

    for dep in execution_order:
        if dep in context.cache:
            continue
        logger.info("[DAG] Executing dependency: %s", dep.name)
        executor = PRODUCT_REGISTRY.get(dep)
        if executor is None:
            raise KeyError(f"No product executor registered for dependency {dep}")
        result = executor(context)
        context.set(dep, result)

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
