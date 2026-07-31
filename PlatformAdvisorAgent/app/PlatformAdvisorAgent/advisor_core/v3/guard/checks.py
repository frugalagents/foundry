"""The three deterministic guard checks.

Each check is a pure function: (proposal, catalog facts) -> list[Violation].
The guard runs all three and returns a combined verdict. It never mutates the
proposal and never decides — it only reports what must not ship.
"""
from __future__ import annotations

from ..deployable.models import ComponentInterfaceBinding
from .models import GUARD_VERSION, GuardVerdict, Proposal, Violation


def check_constraints(proposal: Proposal) -> list[Violation]:
    """Veto any proposed component/capability an asserted constraint forbids.

    This is the disqualifying failure the whole guard exists for: a customer
    said "no self-hosting" and the proposal quietly includes a self-hosted
    component. Constraints are matched exactly against component ids and
    capability tokens — no similarity, no interpretation.
    """
    violations: list[Violation] = []
    for constraint in proposal.constraints:
        forbidden_components = set(constraint.forbids_component_ids)
        forbidden_caps = set(constraint.forbids_capabilities)
        for component in proposal.components:
            if component.component_id in forbidden_components:
                violations.append(Violation(
                    check="constraint",
                    component_id=component.component_id,
                    detail=(
                        f"{component.component_id} violates asserted constraint "
                        f"'{constraint.id}': {constraint.description}"
                    ),
                    remedy=f"Choose an option that satisfies '{constraint.id}'.",
                ))
            offending = forbidden_caps.intersection(component.claimed_capabilities)
            for cap in sorted(offending):
                violations.append(Violation(
                    check="constraint",
                    component_id=component.component_id,
                    detail=(
                        f"{component.component_id} claims capability '{cap}' "
                        f"forbidden by constraint '{constraint.id}'."
                    ),
                    remedy=f"Remove capability '{cap}' or pick a compliant option.",
                ))
    return violations


def check_integrations(
    proposal: Proposal,
    bindings: dict[str, ComponentInterfaceBinding],
    *,
    baseline_provided: frozenset[str] = frozenset(),
) -> list[Violation]:
    """Veto a selected component whose required interfaces nothing provides.

    A proposal is integration-complete only if every required interface of
    every selected component is provided either by another selected component
    or by the fixed platform baseline. This catches an agent stitching together
    components that cannot actually talk to each other.
    """
    selected_ids = {c.component_id for c in proposal.components}
    provided: set[str] = set(baseline_provided)
    for cid in selected_ids:
        binding = bindings.get(cid)
        if binding is not None:
            provided.update(binding.provides_interface_ids)

    violations: list[Violation] = []
    for component in proposal.components:
        binding = bindings.get(component.component_id)
        if binding is None:
            # A component the catalog has never heard of is itself a fake.
            violations.append(Violation(
                check="integration",
                component_id=component.component_id,
                detail=f"{component.component_id} is not in the service catalog.",
                remedy="Select a catalogued component.",
            ))
            continue
        missing = [
            iface for iface in binding.requires_interface_ids
            if iface not in provided
        ]
        for iface in missing:
            violations.append(Violation(
                check="integration",
                component_id=component.component_id,
                detail=(
                    f"{component.component_id} requires interface '{iface}', "
                    f"which no selected component or the baseline provides."
                ),
                remedy=(
                    f"Add a component that provides '{iface}' "
                    f"(or remove {component.component_id})."
                ),
            ))
    return violations


def check_capabilities(
    proposal: Proposal,
    known_capabilities: frozenset[str],
) -> list[Violation]:
    """Veto a claimed capability with no catalog/knowledge basis.

    The agent may only claim capabilities that exist in the curated catalog or
    knowledge base. An empty `known_capabilities` set disables the check (used
    before the capability vocabulary is authored).
    """
    if not known_capabilities:
        return []
    violations: list[Violation] = []
    for component in proposal.components:
        for cap in component.claimed_capabilities:
            if cap not in known_capabilities:
                violations.append(Violation(
                    check="capability",
                    component_id=component.component_id,
                    detail=(
                        f"{component.component_id} claims capability '{cap}' "
                        f"not backed by the catalog or knowledge base."
                    ),
                    remedy=f"Drop the unbacked claim '{cap}'.",
                ))
    return violations


def run_guard(
    proposal: Proposal,
    *,
    bindings: dict[str, ComponentInterfaceBinding],
    baseline_provided: frozenset[str] = frozenset(),
    known_capabilities: frozenset[str] = frozenset(),
) -> GuardVerdict:
    """Run all three checks and return a single verdict."""
    violations: list[Violation] = []
    violations += check_constraints(proposal)
    violations += check_integrations(
        proposal, bindings, baseline_provided=baseline_provided
    )
    violations += check_capabilities(proposal, known_capabilities)
    return GuardVerdict(
        guard_version=GUARD_VERSION,
        passed=len(violations) == 0,
        violations=tuple(violations),
    )
