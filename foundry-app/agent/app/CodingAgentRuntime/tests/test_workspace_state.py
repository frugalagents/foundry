from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workspace_state import build_workspace_state, reconcile_workspace_state


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


def test_blueprint_stage_remains_blueprint_when_questions_remain_but_artifact_exists():
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
        recommendation=existing["recommendation"],
        blueprint_markdown=existing["blueprint_markdown"],
        open_questions=["Which populations require HIPAA isolation?"],
        stage="blueprint",
    )

    assert reasoning_changes == ["question_state", "open_questions"]
    assert invalidated_fields
    assert workspace["stage"] == "blueprint"


def test_blueprint_stage_only_requires_recommendation_and_blueprint_artifact():
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
        "implementation_plan": [],
        "advisory_case": {"recommendation": {"summary": "Governed multi-harness target state."}},
    }

    workspace, _, _ = build_workspace_state(
        existing,
        stage="blueprint",
    )

    assert workspace["stage"] == "blueprint"


def test_question_state_becomes_authoritative_and_derives_open_questions():
    existing = {
        "question_state": [
            {
                "id": "q-harness",
                "text": "Which harness is default?",
                "status": "open",
                "blocking": True,
            },
            {
                "id": "q-compliance",
                "text": "Which compliance framework applies?",
                "status": "answered",
                "answer": "HIPAA",
                "blocking": True,
            },
        ],
        "open_questions": ["Which harness is default?"],
    }

    workspace, invalidated_fields, reasoning_changes = build_workspace_state(
        existing,
        question_state=[
            {
                "id": "q-harness",
                "text": "Which harness is default?",
                "why_it_matters": "It determines the target operating model.",
                "status": "answered",
                "answer": "Claude Code Enterprise for the default population.",
                "decision_domain": "operating_model",
                "blocking": True,
            },
            {
                "id": "q-exceptions",
                "text": "Which teams need formal exception paths?",
                "status": "open",
                "blocking": True,
                "decision_domain": "population_policy",
            },
        ],
        stage="solutioning",
    )

    assert reasoning_changes == ["question_state"]
    assert "open_questions" in invalidated_fields
    assert workspace["open_questions"] == ["Which teams need formal exception paths?"]
    assert any(item["status"] == "answered" and item["answer"] for item in workspace["question_state"])


def test_reconcile_workspace_builds_recommendation_state_and_advisory_case_defaults():
    workspace = reconcile_workspace_state(
        {
            "stage": "solutioning",
            "recommendation": "Use a governed multi-harness portfolio with one default and formal exception lanes.",
            "facts": ["Current tools: Claude Code, Copilot, Cursor"],
            "question_state": [
                {
                    "id": "q1",
                    "text": "Which teams need exception lanes?",
                    "status": "open",
                    "blocking": True,
                    "decision_domain": "population_policy",
                    "why_it_matters": "This determines the default-plus-exceptions target state.",
                }
            ],
            "traversal_state": {
                "next_best_question": "Which teams need exception lanes?",
                "candidate_options": [
                    {"path": "harness-selection/multi-harness-governance", "title": "Governed Multi-Harness Governance", "description": "Shared control plane."},
                    {"path": "harness-selection/saas-products", "title": "SaaS Coding Agent Products", "description": "One vendor default."},
                    {"path": "harness-selection/managed-runtime", "title": "Managed Runtime", "description": "Custom managed lane."},
                ],
                "missing_evidence": [
                    {"question": "Which teams need exception lanes?", "why_it_matters": "Defines the operating model."}
                ],
            },
        },
        reasoning_changes=["facts"],
    )

    assert workspace["recommendation_state"]["primary_recommendation"]
    assert workspace["recommendation_state"]["candidate_options"]
    assert workspace["recommendation_state"]["missing_evidence"] == ["Which teams need exception lanes?"]
    assert workspace["advisory_case"] is not None
    assert workspace["advisory_case"]["recommendation"]["summary"] == workspace["recommendation"]
    assert len(workspace["advisory_case"]["alternatives"]) >= 2
    assert workspace["recommendation_state"]["confidence"] == "medium"
    assert workspace["advisory_case"]["recommendation"]["confidence"] == "medium"
    assert "blocking question" in workspace["advisory_case"]["recommendation"]["confidence_reason"]
    assert workspace["artifact_status"]["recommendation"] == "ready"


def test_reconcile_workspace_prefers_current_traversal_question_after_reasoning_change():
    workspace = reconcile_workspace_state(
        {
            "stage": "solutioning",
            "recommendation": "Resolve the operating model next.",
            "question_state": [
                {
                    "id": "q1",
                    "text": "Is the target state one standard tool, a governed multi-harness portfolio, or one default tool with formal exception paths?",
                    "status": "open",
                    "blocking": True,
                    "decision_domain": "operating_model",
                }
            ],
            "recommendation_state": {
                "next_best_question": "Old stale question?",
                "candidate_options": [{"path": "old", "title": "Old"}],
                "missing_evidence": ["Old stale question?"],
            },
            "traversal_state": {
                "next_best_question": "Is the target state one standard tool, a governed multi-harness portfolio, or one default tool with formal exception paths?",
                "candidate_options": [
                    {"path": "decision/operating-model/multi-harness-governed", "title": "Governed multi-harness portfolio", "description": "Shared controls."}
                ],
                "missing_evidence": [
                    {"question": "Is the target state one standard tool, a governed multi-harness portfolio, or one default tool with formal exception paths?"}
                ],
            },
        },
        reasoning_changes=["facts"],
    )

    assert workspace["recommendation_state"]["next_best_question"].startswith("Is the target state one standard tool")
    assert workspace["recommendation_state"]["candidate_options"][0]["path"] == "decision/operating-model/multi-harness-governed"


def test_reconcile_workspace_prefers_confirmed_structured_facts_over_raw_workspace_fact_strings():
    workspace = reconcile_workspace_state(
        {
            "stage": "solutioning",
            "facts": ["Stale workspace fact that should not remain visible."],
            "traversal_state": {
                "customer_confirmed_facts": [
                    {
                        "key": "current_tools",
                        "value": ["GitHub Copilot", "Cursor"],
                        "status": "confirmed",
                        "source": "customer",
                        "fact_text": "Current tools in scope: GitHub Copilot, Cursor.",
                    }
                ]
            },
        }
    )

    assert workspace["facts"] == ["Current tools in scope: GitHub Copilot, Cursor."]


def test_reconcile_workspace_derives_high_confidence_when_blueprint_and_blockers_are_resolved():
    workspace = reconcile_workspace_state(
        {
            "stage": "blueprint",
            "recommendation": "Use a governed multi-harness platform with one default lane and controlled exceptions.",
            "blueprint_markdown": "## Technical Blueprint\n\n### Identity\nOkta to Cognito federation.\n\n### Controls\nShared policy plane.",
            "decisions": [
                "Use a shared control plane.",
                "Gate exception lanes through policy tiers.",
            ],
            "implementation_plan": [
                "Pilot the default lane with one BU.",
                "Expand to regulated teams after control validation.",
            ],
            "question_state": [
                {
                    "id": "q1",
                    "text": "Which teams need exception lanes?",
                    "status": "answered",
                    "answer": "Payments and ML platform.",
                    "blocking": True,
                }
            ],
            "traversal_state": {
                "candidate_options": [
                    {"path": "decision/default-plus-exceptions", "title": "Default Plus Exceptions", "description": "One standard with formal carve-outs."},
                    {"path": "decision/multi-harness", "title": "Governed Multi-Harness", "description": "Shared policy plane."},
                ],
                "missing_evidence": [],
            },
        }
    )

    assert workspace["recommendation_state"]["confidence"] == "high"
    assert workspace["advisory_case"]["recommendation"]["confidence"] == "high"
    assert "blueprint stage" in workspace["advisory_case"]["recommendation"]["confidence_reason"]
    assert "no blocking questions remain" in workspace["advisory_case"]["recommendation"]["confidence_reason"]


def test_reconcile_workspace_builds_blueprint_markdown_from_output_pack_when_missing():
    workspace = reconcile_workspace_state(
        {
            "stage": "blueprint",
            "recommendation": "Adopt a governed platform with a standard lane and a regulated lane.",
            "decisions": ["Use AgentCore Runtime for managed execution."],
            "implementation_plan": ["30 days: pilot standard lane."],
            "question_state": [],
            "advisory_case": {
                "recommendation": {
                    "summary": "Adopt a governed platform with a standard lane and a regulated lane.",
                    "why_this": "It matches the control model.",
                    "why_not": "Single-lane would violate controls.",
                    "confidence": "high",
                },
                "alternatives": [
                    {"id": "a", "title": "Single standard"},
                    {"id": "b", "title": "Governed multi-lane"},
                ],
                "output_pack": {
                    "executive_summary": "Northstar should use a managed runtime and a restricted regulated lane.",
                    "recommendation_memo": "The design keeps control points centralized.",
                    "architecture_narrative": "Shared identity and audit feed distinct lanes.",
                    "key_decisions": ["Use AgentCore Runtime.", "Route regulated repos to the restricted lane."],
                    "rollout_30_90_180": [{"horizon": "30 days", "outcome": "Pilot standard lane."}],
                    "open_questions": [],
                },
            },
        }
    )

    assert workspace["blueprint_markdown"].startswith("## Technical Blueprint")
    assert "Rollout Phases" in workspace["blueprint_markdown"]
    assert workspace["stage"] == "blueprint"


def test_reconcile_workspace_invalidates_open_questions_when_output_pack_declares_none():
    workspace = reconcile_workspace_state(
        {
            "stage": "blueprint",
            "recommendation": "Finalize the platform design.",
            "blueprint_markdown": "## Technical Blueprint\n\n### Rollout\nDone.",
            "implementation_plan": ["Launch the governed platform."],
            "question_state": [
                {
                    "id": "q1",
                    "text": "Will every lane stay on the shared control plane?",
                    "status": "open",
                    "blocking": True,
                }
            ],
            "recommendation_state": {
                "next_best_question": "Will every lane stay on the shared control plane?",
                "missing_evidence": ["Will every lane stay on the shared control plane?"],
            },
            "advisory_case": {
                "recommendation": {
                    "summary": "Finalize the platform design.",
                    "why_this": "Shared governance is already confirmed.",
                    "why_not": "Bypass lanes break audit controls.",
                    "confidence": "high",
                },
                "alternatives": [
                    {"id": "a", "title": "Bypass lanes"},
                    {"id": "b", "title": "Shared control plane"},
                ],
                "output_pack": {
                    "executive_summary": "All lanes stay on the shared control plane.",
                    "open_questions": [],
                },
            },
        }
    )

    assert workspace["open_questions"] == []
    assert workspace["recommendation_state"]["next_best_question"] == ""
    assert workspace["recommendation_state"]["missing_evidence"] == []
    assert workspace["question_state"][0]["status"] == "invalidated"


def test_reconcile_workspace_synthesizes_missing_rollout_and_blueprint_for_blueprint_stage():
    workspace = reconcile_workspace_state(
        {
            "stage": "blueprint",
            "recommendation": "Use a managed runtime with a regulated lane.",
            "decisions": ["Use a managed runtime."],
            "implementation_plan": [],
            "question_state": [],
            "advisory_case": {
                "recommendation": {
                    "summary": "Use a managed runtime with a regulated lane.",
                    "why_this": "Matches the controls.",
                    "why_not": "Single lane is insufficient.",
                    "confidence": "high",
                },
                "alternatives": [
                    {"id": "a", "title": "Single lane"},
                    {"id": "b", "title": "Regulated lane"},
                ],
            },
        }
    )

    assert workspace["stage"] == "blueprint"
    assert workspace["implementation_plan"]
    assert workspace["blueprint_markdown"].startswith("## Technical Blueprint")
    assert "Rollout Phases" in workspace["blueprint_markdown"]


def test_reconcile_workspace_builds_conditional_blueprint_when_blocker_remains():
    workspace = reconcile_workspace_state(
        {
            "stage": "solutioning",
            "recommendation": "Use one default harness with a shared control plane and a regulated exception lane for SOX-scoped repos.",
            "facts": [
                "Okta is the enterprise identity provider.",
                "SOX-controlled repos are likely in scope.",
                "GitHub Actions drives pull-request automation.",
            ],
            "question_state": [
                {
                    "id": "q1",
                    "text": "Are the finance-platform repos in SOX scope for this rollout?",
                    "why_it_matters": "This determines whether the default lane needs approval-backed write controls on day one.",
                    "status": "open",
                    "blocking": True,
                    "decision_domain": "compliance_overlay",
                }
            ],
            "risks": ["If SOX scope is broader than expected, rollout sequencing changes."],
        }
    )

    assert workspace["stage"] == "blueprint"
    assert len(workspace["implementation_plan"]) == 3
    assert "Conditional Paths For Unresolved Boundaries" in workspace["blueprint_markdown"]
    assert "Are the finance-platform repos in SOX scope for this rollout?" in workspace["blueprint_markdown"]
    assert workspace["recommendation_state"]["confidence"] == "medium"
    assert workspace["advisory_case"]["output_pack"]["rollout_30_90_180"][0]["horizon"] == "30 days"


def test_reconcile_workspace_preserves_explicit_confidence():
    workspace = reconcile_workspace_state(
        {
            "stage": "solutioning",
            "recommendation": "Use one standard harness with exceptions only for regulated teams.",
            "question_state": [
                {
                    "id": "q1",
                    "text": "Do regulated teams require a separate execution boundary?",
                    "status": "open",
                    "blocking": True,
                }
            ],
            "recommendation_state": {
                "confidence": "low",
                "candidate_options": [
                    {"path": "decision/default-plus-exceptions", "title": "Default Plus Exceptions", "description": "One standard with carve-outs."},
                    {"path": "decision/single-standard", "title": "Single Standard", "description": "Lowest variance."},
                ],
            },
            "advisory_case": {
                "recommendation": {
                    "summary": "Use one standard harness with exceptions only for regulated teams.",
                    "confidence": "low",
                    "confidence_reason": "Model-authored confidence should win.",
                }
            },
        }
    )

    assert workspace["recommendation_state"]["confidence"] == "low"
    assert workspace["advisory_case"]["recommendation"]["confidence"] == "low"
    assert workspace["advisory_case"]["recommendation"]["confidence_reason"] == "Model-authored confidence should win."


def test_stage_auto_promotes_to_blueprint_when_recommendation_and_blueprint_exist():
    workspace, _, _ = build_workspace_state(
        {
            "stage": "solutioning",
            "recommendation": "Use a governed multi-harness portfolio.",
            "blueprint_markdown": "",
            "facts": ["Brownfield environment"],
            "decisions": ["Keep a shared control plane."],
        },
        blueprint_markdown="## Architecture\nReady to build",
        stage="solutioning",
    )

    assert workspace["stage"] == "blueprint"


def test_reconcile_workspace_clears_raw_fact_strings_when_structured_fact_contract_is_empty():
    workspace = reconcile_workspace_state(
        {
            "stage": "solutioning",
            "facts": ["Stale fact that should be cleared."],
            "traversal_state": {
                "customer_confirmed_facts": [],
            },
        }
    )

    assert workspace["facts"] == []
