"""Dependency-derived implementation roadmap builder."""
from __future__ import annotations

from ..models import CatalogRelease, WorkspaceRevision
from .models import (
    AssuranceCatalog,
    ImplementationRoadmap,
    NumericRange,
    RoadmapPhase,
    SecurityAssurancePlan,
    SelectedBundleContext,
    WorkPackage,
)


def _package_id(kind: str, record_id: str) -> str:
    return f"work-package:{kind}-{record_id.split(':', 1)[1]}"


def _sum_ranges(ranges: list[NumericRange]) -> NumericRange:
    return NumericRange(
        low=round(sum(item.low for item in ranges), 2),
        high=round(sum(item.high for item in ranges), 2),
    )


def _topological_waves(
    packages: dict[str, WorkPackage],
) -> tuple[tuple[str, ...], ...]:
    remaining = set(packages)
    completed: set[str] = set()
    waves: list[tuple[str, ...]] = []
    while remaining:
        ready = tuple(
            sorted(
                package_id
                for package_id in remaining
                if set(packages[package_id].dependency_package_ids) <= completed
            )
        )
        if not ready:
            raise ValueError("roadmap work-package dependency cycle")
        waves.append(ready)
        completed.update(ready)
        remaining.difference_update(ready)
    return tuple(waves)


def build_implementation_roadmap(
    architecture_catalog: CatalogRelease,
    revision: WorkspaceRevision,
    assurance_catalog: AssuranceCatalog,
    security: SecurityAssurancePlan,
    *,
    selected_bundle: SelectedBundleContext | None,
) -> ImplementationRoadmap:
    active_component_ids = {
        node.component_id for node in revision.architecture.nodes
    }
    components = {
        item.id: item
        for item in architecture_catalog.components
        if item.id in active_component_ids
    }
    implementations = {
        item.component_id: item
        for item in (selected_bundle.implementations if selected_bundle else ())
    }

    packages: dict[str, WorkPackage] = {}
    for component_id, component in sorted(components.items()):
        package_id = _package_id("component", component_id)
        implementation = implementations.get(component_id)
        base_effort = assurance_catalog.roadmap.effort_days_by_plane[
            component.plane.value
        ]
        dependency_count = len(
            active_component_ids.intersection(component.dependency_ids)
        )
        dependency_effort = assurance_catalog.roadmap.dependency_effort_days
        effort = NumericRange(
            low=base_effort.low + dependency_count * dependency_effort.low,
            high=base_effort.high + dependency_count * dependency_effort.high,
        )
        title = f"Implement {component.name}"
        if implementation is not None:
            title = (
                f"Implement {component.name} with "
                f"{implementation.provider} {implementation.product}"
            )
        packages[package_id] = WorkPackage(
            package_id=package_id,
            title=title,
            kind="component",
            component_id=component_id,
            offering_id=(
                implementation.offering_id if implementation is not None else None
            ),
            owner=assurance_catalog.roadmap.owner_by_plane[
                component.plane.value
            ],
            effort_person_days=effort,
            dependency_package_ids=tuple(
                sorted(
                    _package_id("component", dependency_id)
                    for dependency_id in component.dependency_ids
                    if dependency_id in active_component_ids
                )
            ),
            exit_criteria=(
                f"{component.name} is configured and version controlled.",
                "Declared dependencies pass integration checks.",
                "Operational owner accepts runbook and support boundary.",
            ),
        )

    control_definitions = {
        item.id: item for item in assurance_catalog.controls
    }
    for control_item in security.controls:
        control = control_definitions[control_item.control_id]
        package_id = _package_id("control", control.id)
        packages[package_id] = WorkPackage(
            package_id=package_id,
            title=f"Verify control: {control.title}",
            kind="control_verification",
            control_id=control.id,
            owner="Security Engineering",
            effort_person_days=(
                assurance_catalog.roadmap.control_verification_effort_days
            ),
            dependency_package_ids=tuple(
                sorted(
                    _package_id("component", component_id)
                    for component_id in control_item.applicable_component_ids
                )
            ),
            exit_criteria=(
                control.verification.acceptance_criteria,
                "Evidence is immutable, attributable, and not expired.",
                "Failure or exception has an owner and remediation date.",
            ),
        )

    waves = _topological_waves(packages)
    phases = tuple(
        RoadmapPhase(
            phase_id=f"phase:wave-{sequence:02d}",
            sequence=sequence,
            name=(
                "Foundation"
                if sequence == 1
                else "Control verification"
                if all(
                    packages[package_id].kind == "control_verification"
                    for package_id in wave
                )
                else f"Dependency wave {sequence}"
            ),
            work_packages=tuple(packages[package_id] for package_id in wave),
            exit_criteria=(
                "Every work package in this wave meets its exit criteria.",
                "No unresolved dependency blocks the next wave.",
            ),
        )
        for sequence, wave in enumerate(waves, start=1)
    )

    depths: dict[str, int] = {}
    for wave_number, wave in enumerate(waves, start=1):
        for package_id in wave:
            depths[package_id] = wave_number
    critical_path: list[str] = []
    if packages:
        current_id = max(
            packages,
            key=lambda package_id: (depths[package_id], package_id),
        )
        while True:
            critical_path.append(current_id)
            dependencies = packages[current_id].dependency_package_ids
            if not dependencies:
                break
            current_id = max(
                dependencies,
                key=lambda package_id: (depths[package_id], package_id),
            )
        critical_path.reverse()

    return ImplementationRoadmap(
        phases=phases,
        total_effort_person_days=_sum_ranges(
            [item.effort_person_days for item in packages.values()]
        ),
        critical_path_package_ids=tuple(critical_path),
    )
