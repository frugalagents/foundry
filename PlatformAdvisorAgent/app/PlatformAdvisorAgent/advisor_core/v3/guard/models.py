"""Contracts for the deterministic proposal guard.

The guard sits between an agent's *proposal* and showing it to a customer. It
does not decide the architecture — it only VETOES a proposal that violates one
of a small, bounded set of facts that must never be invented:

  1. a violated hard constraint (e.g. self-hosting under a managed-only mandate)
  2. a non-existent integration (a selected component whose required interfaces
     nothing in the proposal provides)
  3. an unbacked capability (a claimed capability with no catalog/evidence basis)

Everything here is a pure, typed contract so the guard is testable and its
verdict is a durable part of the Decision Record.
"""
from __future__ import annotations

from ..models import FrozenModel, StableId


GUARD_VERSION = "1.0.0"


class ProposedComponent(FrozenModel):
    """One box's decision as proposed by the agent."""

    box_id: str
    component_id: StableId
    # human-facing, agent-authored — narration only, never authority
    chosen_label: str = ""
    alternatives: tuple[str, ...] = ()
    reasoning: str = ""
    claimed_capabilities: tuple[str, ...] = ()


class AssertedConstraint(FrozenModel):
    """A hard constraint the customer stated that must not be weakened."""

    id: str
    description: str
    # component ids explicitly forbidden by this constraint
    forbids_component_ids: tuple[StableId, ...] = ()
    # capability tokens explicitly forbidden
    forbids_capabilities: tuple[str, ...] = ()


class Proposal(FrozenModel):
    """The full agent proposal handed to the guard."""

    components: tuple[ProposedComponent, ...]
    constraints: tuple[AssertedConstraint, ...] = ()


class Violation(FrozenModel):
    check: str          # "constraint" | "integration" | "capability"
    component_id: StableId
    detail: str
    # for a re-propose: what the agent must fix
    remedy: str = ""


class GuardVerdict(FrozenModel):
    guard_version: str
    passed: bool
    violations: tuple[Violation, ...] = ()

    @property
    def vetoed(self) -> bool:
        return not self.passed
