from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.db.models import SessionCreate
from api.routers.sessions import _to_session


def base_item(**overrides):
    item = {
        "session_id": "sess_123",
        "customer_id": "cust_123",
        "title": "Platform blueprint",
        "description": "Architecture assessment",
        "status": "active",
        "current_step": 0,
        "created_by": "user_123",
        "created_at": "2026-07-28T10:00:00+00:00",
        "updated_at": "2026-07-28T10:00:00+00:00",
    }
    item.update(overrides)
    return item


def test_session_response_uses_canonical_blueprint_fields():
    session = _to_session(base_item())

    assert session.title == "Platform blueprint"
    assert session.description == "Architecture assessment"
    assert session.evidence_state == "not_started"
    assert session.status == "active"


def test_session_response_reads_legacy_name_and_notes():
    item = base_item(name="Legacy blueprint", notes="Legacy description")
    item.pop("title")
    item.pop("description")

    session = _to_session(item)

    assert session.title == "Legacy blueprint"
    assert session.description == "Legacy description"


def test_session_response_derives_pipeline_summary():
    session = _to_session(base_item(
        pipeline_ctx={
            "current_step": 10,
            "pattern_id": "federated",
            "assessment_input": {"primary_workload": "internal_copilot"},
            "assessment_result": {
                "status": "complete",
                "operating_model": "federated",
            },
        },
    ))

    assert session.current_step == 10
    assert session.status == "complete"
    assert session.primary_workload == "internal_copilot"
    assert session.recommendation == "federated"
    assert session.evidence_state == "decision_ready"


def test_session_response_marks_missing_evidence_as_provisional():
    session = _to_session(base_item(
        pipeline_ctx={
            "current_step": 2,
            "assessment_result": {"status": "needs_information"},
        },
    ))

    assert session.status == "active"
    assert session.evidence_state == "provisional"


def test_session_create_limits_title_and_description_lengths():
    with pytest.raises(ValidationError):
        SessionCreate(title="x" * 121)

    with pytest.raises(ValidationError):
        SessionCreate(title="Valid", description="x" * 501)
