from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import yaml

from advisor_core.knowledge import (
    PERMISSIONS,
    ClaimContradiction,
    ContradictionReport,
    KnowledgeReviewRecord,
    PublicationAuthorizationError,
    PublicationPrincipal,
    authorize_publication,
    require_publication_authorization,
)


NOW = datetime(2026, 8, 11, 22, tzinfo=timezone.utc)
HASH_A = f"sha256:{'a' * 64}"
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
POLICY_PATH = (
    REPOSITORY_ROOT
    / "knowledge"
    / "policies"
    / "publication-policy.yaml"
)


def record(state: str = "approved") -> KnowledgeReviewRecord:
    return KnowledgeReviewRecord(
        candidate_id="candidate:example-claim",
        state=state,
        created_at=NOW,
        updated_at=NOW,
        decisions=(),
        record_hash=HASH_A,
    )


def report(*, blocking: bool = False) -> ContradictionReport:
    contradictions = (
        ClaimContradiction(
            contradiction_type="direct_value_conflict",
            severity="blocking",
            claim_ids=("claim:a", "claim:b"),
            subject_id="offering:example",
            predicates=("availability_status", "availability_status"),
            rationale="Conflicting availability facts.",
        ),
    ) if blocking else ()
    return ContradictionReport(
        as_of=date(2026, 8, 11),
        evaluated_claim_ids=("claim:a", "claim:b"),
        contradictions=contradictions,
        report_hash=HASH_A,
    )


def test_research_agent_cannot_approve_or_publish():
    principal = PublicationPrincipal(
        principal_id="agent:research-collector",
        principal_type="research_agent",
    )

    assert authorize_publication(
        principal,
        "write_candidate",
    ).authorized
    assert not authorize_publication(
        principal,
        "record_review_decision",
    ).authorized
    with pytest.raises(
        PublicationAuthorizationError,
        match="not permitted to publish_catalog",
    ):
        require_publication_authorization(
            principal,
            "publish_catalog",
        )


def test_release_pipeline_requires_approved_records_and_clean_report():
    principal = PublicationPrincipal(
        principal_id="pipeline:knowledge-release",
        principal_type="release_pipeline",
    )

    assert not authorize_publication(
        principal,
        "publish_catalog",
        review_records=(record("disputed"),),
        contradiction_report=report(),
    ).authorized
    assert not authorize_publication(
        principal,
        "publish_catalog",
        review_records=(record(),),
        contradiction_report=report(blocking=True),
    ).authorized
    assert authorize_publication(
        principal,
        "publish_catalog",
        review_records=(record(),),
        contradiction_report=report(),
    ).authorized


def test_human_reviewer_cannot_publish_catalog():
    principal = PublicationPrincipal(
        principal_id="person:knowledge-reviewer",
        principal_type="human_reviewer",
    )

    assert authorize_publication(
        principal,
        "record_review_decision",
    ).authorized
    assert not authorize_publication(
        principal,
        "publish_catalog",
        review_records=(record(),),
        contradiction_report=report(),
    ).authorized


def test_checked_in_policy_matches_code_permission_matrix():
    document = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    expected = {
        principal.value: sorted(action.value for action in actions)
        for principal, actions in PERMISSIONS.items()
    }
    actual = {
        principal: sorted(actions)
        for principal, actions in document["principals"].items()
    }

    assert actual == expected
