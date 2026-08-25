from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from architecture_case import build_architecture_case


def test_build_architecture_case_maps_workspace_and_canvas_into_one_contract():
    case = build_architecture_case(
        case_id="cust1/sess1",
        revision=3,
        okf_release_id="okf-slice-v1",
        workspace={
            "stage": "solutioning",
            "recommendation": "Use one default harness with formal exception governance.",
            "facts": [
                "Current tools in scope: GitHub Copilot, Cursor.",
                "ITAR repositories are isolated in a separate enclave.",
            ],
            "assumptions": [
                {
                    "id": "default-surface",
                    "title": "Default developer surface",
                    "assumed": "IDE-first entry point for the main population.",
                    "why": "Most teams already work from IDE-based flows.",
                    "impact": "CLI-only teams become exception populations.",
                    "confidence": "medium",
                    "options": [{"id": "cli", "label": "CLI-first", "prompt": "Do some teams need CLI as the default surface?"}],
                }
            ],
            "operating_model": "default_plus_exceptions",
            "question_state": [
                {
                    "id": "q-exceptions",
                    "text": "Which teams need formal exception lanes?",
                    "why_it_matters": "This determines population policy and approval flow.",
                    "blocking": True,
                    "decision_domain": "population_policy",
                    "status": "open",
                    "source": "okf",
                },
                {
                    "id": "q-answered",
                    "text": "Are regulated repositories isolated already?",
                    "status": "answered",
                    "answer": "Yes, they are in a separate enclave.",
                    "blocking": True,
                    "decision_domain": "execution_boundary",
                },
            ],
            "open_questions": ["Stale question that should not win"],
            "decisions": ["Adopt one default harness with formal exception paths."],
            "risks": ["Repo classification must stay accurate."],
            "blueprint_markdown": "## Blueprint\n<p>Controlled baseline.</p>",
            "advisory_case": {
                "recommendation": {
                    "summary": "Use one default harness with formal exception governance.",
                    "why_this": "It keeps the main path simple while preserving control over outliers.",
                    "why_not": "A fully open multi-tool posture would create unmanaged sprawl.",
                    "confidence": "high",
                },
                "decisions": [
                    {
                        "statement": "Use one default harness with formal exception governance.",
                        "why": "The customer wants one default path rather than a free-form portfolio.",
                        "options_considered": ["Governed multi-harness portfolio"],
                        "owner": "platform-architecture",
                    }
                ],
                "risks": [
                    {
                        "risk": "Repo classification must stay accurate.",
                        "mitigation": "Tie local-lane eligibility to repo tags and review gates.",
                        "severity": "high",
                        "category": "governance",
                    }
                ],
                "output_pack": {
                    "executive_summary": "Default path plus governed exceptions.",
                    "recommendation_memo": "Keep one mainline and force exceptions through policy.",
                    "architecture_narrative": "The platform keeps the default path simple and isolates exceptions.",
                    "rollout_30_90_180": [{"horizon": "30 days", "outcome": "Pilot the default lane."}],
                },
            },
            "artifact_status": {"recommendation": "ready", "blueprint": "ready"},
            "traversal_state": {
                "active_decision": {
                    "path": "decision/operating-model/default-plus-exceptions",
                    "title": "Default plus exceptions",
                },
                "decision_focus": "operating_model",
                "candidate_options": [
                    {
                        "path": "decision/operating-model/default-plus-exceptions",
                        "title": "Default plus exceptions",
                        "position": "recommended",
                    }
                ],
                "missing_evidence": [
                    {"question": "Which teams need formal exception lanes?"}
                ],
                "structured_facts": [
                    {
                        "key": "export_control",
                        "value": True,
                        "status": "confirmed",
                        "fact_text": "Export-controlled repositories are in scope.",
                    },
                    {
                        "key": "local_execution_scope",
                        "value": "non_regulated_only",
                        "status": "confirmed",
                        "fact_text": "Local execution is limited to non-regulated workflows.",
                    },
                ],
            },
            "updated_at": "2026-08-25T12:00:00Z",
        },
        canvas_snapshot={
            "nodes": [
                {"id": "surface-entry", "label": "Developer surfaces", "layer": "surface", "kind": "developer_surface"},
                {"id": "execution-main", "label": "Primary controlled execution", "layer": "execution", "kind": "execution"},
                {"id": "access-policy", "label": "Guardrails / policy", "layer": "access", "kind": "policy_control", "path_role": "overlay"},
            ],
            "edges": [
                {"id": "surface-entry->execution-main", "source": "surface-entry", "target": "execution-main"},
                {"id": "access-policy->execution-main", "source": "access-policy", "target": "execution-main", "dashed": True, "color": "#ef4444"},
            ],
            "architecture_artifact": {
                "executive_summary": "Layered baseline with a cross-cutting control plane.",
                "decisions": [
                    {
                        "decision": "Keep regulated workloads off the general local lane.",
                        "why": "Local execution is scoped to non-regulated work only.",
                    }
                ],
                "risks": [
                    {
                        "risk": "Local-lane scope could drift without population governance.",
                        "mitigation": "Review repo and population mapping quarterly.",
                    }
                ],
                "rollout": [{"phase": "Baseline", "outcome": "Establish the default lane first."}],
            },
            "updated_at": "2026-08-25T12:01:00Z",
        },
    )

    assert case.case_id == "cust1/sess1"
    assert case.revision == 3
    assert case.okf_release_id == "okf-slice-v1"
    assert case.stage == "blueprint"
    assert case.operating_model == "default_plus_exceptions"
    assert [item.text for item in case.open_questions] == ["Which teams need formal exception lanes?"]
    assert case.artifacts.executive_summary == "Default path plus governed exceptions."
    assert case.artifacts.rollout[0].phase == "30 days"
    assert [item.statement for item in case.decisions] == ["Adopt one default harness with formal exception paths."]
    assert all(item.source == "workspace" for item in case.decisions)
    assert any(item.layer == "execution" for item in case.architecture_components)
    assert any(item.relationship_type == "control_overlay" for item in case.relationships)
    assert "okf:active:decision/operating-model/default-plus-exceptions" in {item.id for item in case.evidence_refs}
    assert case.observability.active_decision_path == "decision/operating-model/default-plus-exceptions"
    assert case.observability.candidate_option_paths == ["decision/operating-model/default-plus-exceptions"]
    assert case.observability.missing_evidence == ["Which teams need formal exception lanes?"]
    assert [item.risk for item in case.risks] == ["Repo classification must stay accurate."]
    assert case.evaluation.has_blueprint is True
    assert case.evaluation.has_architecture_snapshot is True


def test_build_architecture_case_falls_back_to_workspace_when_executive_artifacts_are_missing():
    case = build_architecture_case(
        case_id="cust2/sess2",
        workspace={
            "stage": "discovery",
            "recommendation": "Resolve the execution boundary before locking the platform shape.",
            "facts": ["The business unit wants local execution on laptops."],
            "question_state": [
                {
                    "id": "q-boundary",
                    "text": "Does local execution include export-controlled repositories?",
                    "status": "open",
                    "blocking": True,
                    "decision_domain": "execution_boundary",
                }
            ],
            "decisions": ["Do not assume local execution is safe for regulated work."],
            "traversal_state": {
                "structured_facts": [
                    {
                        "key": "local_execution_requested",
                        "value": True,
                        "status": "confirmed",
                        "fact_text": "At least one population wants local execution.",
                    }
                ]
            },
        },
    )

    assert case.stage == "solutioning"
    assert case.current_recommendation == "Resolve the execution boundary before locking the platform shape."
    assert [item.statement for item in case.decisions] == ["Do not assume local execution is safe for regulated work."]
    assert [item.text for item in case.open_questions] == ["Does local execution include export-controlled repositories?"]
    assert {item.id for item in case.evidence_refs} == {"fact:local_execution_requested"}
    assert case.evaluation.has_blueprint is False
    assert case.evaluation.has_architecture_snapshot is False
    assert case.evaluation.missing_artifacts == ["blueprint", "architecture_snapshot"]


def test_build_architecture_case_excludes_engine_inferred_facts_from_canonical_facts():
    case = build_architecture_case(
        case_id="cust3/sess3",
        workspace={
            "stage": "solutioning",
            "traversal_state": {
                "customer_confirmed_facts": [
                    {
                        "key": "current_tools",
                        "value": ["GitHub Copilot", "Cursor"],
                        "status": "confirmed",
                        "source": "customer",
                        "fact_text": "Current tools in scope: GitHub Copilot, Cursor.",
                    }
                ],
                "engine_inferred_facts": [
                    {
                        "key": "shared_control_plane",
                        "value": True,
                        "status": "confirmed",
                        "source": "engine_inferred",
                        "fact_text": "The target state appears to keep approved lanes on one shared control plane.",
                    }
                ],
            },
        },
    )

    assert [item.statement for item in case.facts] == ["Current tools in scope: GitHub Copilot, Cursor."]
