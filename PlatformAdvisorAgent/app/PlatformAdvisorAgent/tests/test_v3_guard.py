from __future__ import annotations

from pathlib import Path

from advisor_core.v3.guard import (
    AssertedConstraint,
    Citation,
    DecisionRecord,
    GuardVerdict,
    ModelStamp,
    Proposal,
    ProposedComponent,
    load_bindings,
    revalidate,
    run_guard,
)

CATALOG_R02 = (
    Path(__file__).resolve().parents[1]
    / "advisor_core" / "v3" / "catalogs" / "coding-platform-r0.2"
)
# model-gateway requires these interfaces; the baseline platform provides them.
BASELINE = frozenset({
    "interface:audit-write", "interface:identity-assertion",
    "interface:model-catalog", "interface:policy-decision",
    "interface:quota-decision",
})


def _bindings():
    return load_bindings(CATALOG_R02)


def test_clean_managed_gateway_proposal_passes():
    bindings = _bindings()
    proposal = Proposal(components=(
        ProposedComponent(
            box_id="model-gateway",
            component_id="component:model-gateway",
            chosen_label="Managed model gateway",
        ),
    ))
    verdict = run_guard(proposal, bindings=bindings, baseline_provided=BASELINE)
    assert verdict.passed
    assert verdict.violations == ()


def test_constraint_veto_blocks_forbidden_component():
    bindings = _bindings()
    proposal = Proposal(
        components=(
            ProposedComponent(
                box_id="model-gateway",
                component_id="component:self-hosted-inference",
                chosen_label="Self-hosted inference",
            ),
        ),
        constraints=(
            AssertedConstraint(
                id="no-self-hosting",
                description="Managed-only mandate; no customer-operated inference.",
                forbids_component_ids=("component:self-hosted-inference",),
            ),
        ),
    )
    verdict = run_guard(proposal, bindings=bindings, baseline_provided=BASELINE)
    assert verdict.vetoed
    assert any(v.check == "constraint" for v in verdict.violations)


def test_integration_veto_when_required_interface_unprovided():
    bindings = _bindings()
    # model-gateway requires interface:model-catalog etc. With NO baseline and
    # no model-catalog component selected, the integration check must veto.
    proposal = Proposal(components=(
        ProposedComponent(
            box_id="model-gateway",
            component_id="component:model-gateway",
        ),
    ))
    verdict = run_guard(proposal, bindings=bindings, baseline_provided=frozenset())
    assert verdict.vetoed
    assert any(v.check == "integration" for v in verdict.violations)
    # ...but adding the model-catalog provider (plus baseline) satisfies it.
    proposal2 = Proposal(components=(
        ProposedComponent(box_id="model-gateway", component_id="component:model-gateway"),
        ProposedComponent(box_id="model-catalog", component_id="component:model-catalog"),
    ))
    ok = run_guard(
        proposal2, bindings=bindings,
        baseline_provided=BASELINE - {"interface:model-catalog"},
    )
    assert ok.passed, ok.violations


def test_unknown_component_is_vetoed_as_fake_integration():
    bindings = _bindings()
    proposal = Proposal(components=(
        ProposedComponent(box_id="x", component_id="component:make-believe-gateway"),
    ))
    verdict = run_guard(proposal, bindings=bindings, baseline_provided=BASELINE)
    assert verdict.vetoed
    assert any("not in the service catalog" in v.detail for v in verdict.violations)


def test_capability_veto_only_when_vocabulary_provided():
    bindings = _bindings()
    proposal = Proposal(components=(
        ProposedComponent(
            box_id="model-gateway",
            component_id="component:model-gateway",
            claimed_capabilities=("teleportation",),
        ),
    ))
    # no vocabulary → capability check disabled → passes integration/constraint
    lenient = run_guard(proposal, bindings=bindings, baseline_provided=BASELINE)
    assert lenient.passed
    # with a vocabulary that excludes the claim → vetoed
    strict = run_guard(
        proposal, bindings=bindings, baseline_provided=BASELINE,
        known_capabilities=frozenset({"prompt-caching", "fallback"}),
    )
    assert strict.vetoed
    assert any(v.check == "capability" for v in strict.violations)


def test_decision_record_round_trips_and_revalidates():
    bindings = _bindings()
    proposal = Proposal(components=(
        ProposedComponent(box_id="model-gateway", component_id="component:model-gateway"),
    ))
    verdict = run_guard(proposal, bindings=bindings, baseline_provided=BASELINE)
    record = DecisionRecord(
        record_id="rec-1",
        workspace_id="ws-1",
        created_at="2026-07-31T00:00:00Z",
        answers={"requirement:provider-hosting": "managed"},
        proposal=proposal,
        guard_verdict=verdict,
        citations=(Citation(claim_or_source_id="claim:bedrock-managed-inference"),),
        catalog_hash="sha256:deadbeef",
        guard_version=verdict.guard_version,
        model_stamp=ModelStamp(model_id="claude-sonnet-5", temperature=0.3),
    )
    # JSON round-trip is stable (durable persistence).
    again = DecisionRecord.model_validate_json(record.model_dump_json())
    assert again == record

    # Reopen under the SAME guard version → no review needed.
    same = revalidate(record, verdict)
    assert same["needs_review"] is False

    # Reopen under a NEWER guard that now vetoes → flagged for review.
    newer = GuardVerdict(
        guard_version="2.0.0",
        passed=False,
        violations=verdict.violations or (),
    )
    # force a violation to simulate a new check catching it
    from advisor_core.v3.guard import Violation
    newer = GuardVerdict(
        guard_version="2.0.0", passed=False,
        violations=(Violation(check="constraint", component_id="component:model-gateway", detail="new check"),),
    )
    flagged = revalidate(record, newer)
    assert flagged["stale_guard"] is True
    assert flagged["needs_review"] is True
