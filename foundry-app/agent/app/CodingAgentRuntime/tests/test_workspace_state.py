from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workspace_state import build_workspace_state


def test_material_fact_change_clears_omitted_dependent_artifacts():
    existing = {
        "stage": "blueprint",
        "recommendation": "Use Claude Code Enterprise as the single standard harness.",
        "blueprint_markdown": "# Blueprint\nold",
        "assumptions": [],
        "facts": ["Current tools unknown"],
        "operating_model": "single_standard",
        "open_questions": ["Which harness is default?"],
        "decisions": ["Standardize on Claude Code Enterprise"],
        "risks": ["Azure BUs not yet understood"],
        "implementation_plan": ["Run pilot"],
        "advisory_case": {"recommendation": {"summary": "Claude Code Enterprise for everyone"}},
    }

    workspace, invalidated_fields, reasoning_changes = build_workspace_state(
        existing,
        facts=["Current tools: Claude Code, Copilot, Cursor, Codex CLI"],
        stage="solutioning",
    )

    assert reasoning_changes == ["facts"]
    assert "recommendation" in invalidated_fields
    assert "open_questions" in invalidated_fields
    assert "decisions" in invalidated_fields
    assert "risks" in invalidated_fields
    assert "implementation_plan" in invalidated_fields
    assert "blueprint_markdown" in invalidated_fields
    assert "advisory_case" in invalidated_fields
    assert workspace["facts"] == ["Current tools: Claude Code, Copilot, Cursor, Codex CLI"]
    assert workspace["recommendation"] == ""
    assert workspace["open_questions"] == []
    assert workspace["decisions"] == []
    assert workspace["risks"] == []
    assert workspace["implementation_plan"] == []
    assert workspace["blueprint_markdown"] == ""
    assert workspace["advisory_case"] is None
    assert workspace["stage"] == "solutioning"


def test_recommendation_change_clears_only_heavy_artifacts_when_not_regenerated():
    existing = {
        "stage": "solutioning",
        "recommendation": "Use one standard harness.",
        "blueprint_markdown": "# Blueprint\nold",
        "assumptions": [],
        "facts": ["Brownfield rollout"],
        "operating_model": "single_standard",
        "open_questions": [],
        "decisions": ["One standard harness"],
        "risks": [],
        "implementation_plan": ["Pilot"],
        "advisory_case": {"recommendation": {"summary": "One standard harness"}},
    }

    workspace, invalidated_fields, reasoning_changes = build_workspace_state(
        existing,
        recommendation="Use a governed multi-harness portfolio.",
        stage="solutioning",
    )

    assert reasoning_changes == []
    assert invalidated_fields == ["blueprint_markdown", "advisory_case"]
    assert workspace["recommendation"] == "Use a governed multi-harness portfolio."
    assert workspace["blueprint_markdown"] == ""
    assert workspace["advisory_case"] is None
    assert workspace["decisions"] == ["One standard harness"]


def test_blueprint_stage_downgrades_when_blockers_or_artifacts_are_missing():
    existing = {
        "stage": "blueprint",
        "recommendation": "Governed multi-harness target state.",
        "blueprint_markdown": "# Blueprint\nready",
        "assumptions": [],
        "facts": ["Enterprise brownfield"],
        "operating_model": "multi_harness_governed",
        "open_questions": [],
        "decisions": ["Use a shared control plane"],
        "risks": [],
        "implementation_plan": ["Pilot", "Expand"],
        "advisory_case": {"recommendation": {"summary": "Governed multi-harness target state."}},
    }

    workspace, invalidated_fields, reasoning_changes = build_workspace_state(
        existing,
        open_questions=["Which populations require HIPAA isolation?"],
        stage="blueprint",
    )

    assert reasoning_changes == ["open_questions"]
    assert invalidated_fields
    assert workspace["stage"] == "solutioning"
