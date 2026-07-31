"""Deterministic proposal guard: veto violated constraints, fake integrations,
and unbacked capabilities. Everything else is left to the agents."""
from __future__ import annotations

from .checks import (
    check_capabilities,
    check_constraints,
    check_integrations,
    run_guard,
)
from .models import (
    GUARD_VERSION,
    AssertedConstraint,
    GuardVerdict,
    ProposedComponent,
    Proposal,
    Violation,
)
from .record import Citation, DecisionRecord, ModelStamp, revalidate

__all__ = [
    "GUARD_VERSION",
    "AssertedConstraint",
    "Citation",
    "DecisionRecord",
    "GuardVerdict",
    "ModelStamp",
    "Proposal",
    "ProposedComponent",
    "Violation",
    "check_capabilities",
    "check_constraints",
    "check_integrations",
    "revalidate",
    "run_guard",
]


def load_bindings(catalog_root) -> dict:
    """Load component interface bindings from the deployable r0.2 catalog.

    These power the integration check — the set of interfaces each component
    provides/requires. Returns {component_id: ComponentInterfaceBinding}.
    """
    import json
    from pathlib import Path

    from ..deployable.models import ComponentInterfaceBinding

    root = Path(catalog_root)
    interfaces_file = root / "10-interfaces.json"
    data = json.loads(interfaces_file.read_text(encoding="utf-8"))
    bindings: dict[str, ComponentInterfaceBinding] = {}
    for raw in data.get("component_bindings", []):
        binding = ComponentInterfaceBinding.model_validate(raw)
        bindings[binding.component_id] = binding
    return bindings
