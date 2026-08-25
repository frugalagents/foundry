from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_loader import load_knowledge_base
from decision_spine import build_turn_guidance

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


def test_multi_tool_signal_prefers_operating_model_question():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"facts": []},
        "We already use GitHub Copilot and Cursor across engineering teams.",
    )

    assert guidance["decision_focus"] == "operating_model"
    assert guidance["next_best_question"].startswith("Is the target state one standard tool")
    assert guidance["candidate_options"][0]["path"] == "decision/operating-model/multi-harness-governed"


def test_export_control_with_local_execution_challenges_execution_boundary_first():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"facts": []},
        "Some repos are ITAR-controlled and one BU wants local execution on developer laptops.",
    )

    assert guidance["decision_focus"] == "execution_boundary"
    assert "local execution" in guidance["recommendation"].lower()
    assert guidance["question_state"][0]["decision_domain"] == "execution_boundary"
    assert any("export-controlled workloads" in risk for risk in guidance["risks"])


def test_explicit_operating_model_answer_is_carried_as_a_decision():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"facts": ["Current tools in scope: GitHub Copilot, Cursor."]},
        "The target state is one default tool with formal exception paths.",
    )

    assert guidance["operating_model"] == "default_plus_exceptions"
    assert any("default harness with formal exception lanes" in item for item in guidance["decisions"])
    assert guidance["decision_focus"] == "exception_governance"
    assert guidance["next_best_question"].startswith("Which developer populations actually need formal exception lanes")


def test_default_plus_exceptions_pushes_exception_governance_before_product_comparison():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"facts": ["Current tools in scope: GitHub Copilot, Cursor."]},
        "The target state is one default tool with formal exception paths.",
    )

    assert guidance["decision_focus"] == "exception_governance"
    assert guidance["candidate_options"][0]["path"] == "decision/exception-governance/named-population-lanes"
    assert "personal carve-outs" in guidance["recommendation"].lower()


def test_named_time_bounded_exceptions_resolve_into_a_governed_lane_decision():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"operating_model": "default_plus_exceptions"},
        "Exceptions are only for named teams, and they are time-bounded with quarterly review.",
    )

    assert any("time-bounded lanes" in item for item in guidance["decisions"])


def test_multiple_identity_sources_trigger_broker_boundary_question():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"facts": []},
        "We have Okta for corporate, Entra in an acquired BU, and a legacy AD forest that all need platform access.",
    )

    assert guidance["decision_focus"] == "identity_boundary"
    assert guidance["next_best_question"].startswith("Will the platform trust one central identity broker")
    assert guidance["candidate_options"][0]["path"] == "decision/identity-boundary/central-broker"


def test_brokered_identity_answer_is_carried_as_a_decision():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"facts": []},
        "We have multiple IDPs, and the target state is IAM Identity Center as one broker with normalized claims.",
    )

    assert any("brokered identity boundary" in item for item in guidance["decisions"])


def test_shared_control_plane_question_activates_after_exception_lanes_are_defined():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {
            "operating_model": "default_plus_exceptions",
            "traversal_state": {
                "customer_confirmed_facts": [
                    {"key": "exception_scope", "value": "named_populations", "status": "confirmed", "source": "customer", "fact_text": ""},
                    {"key": "exception_review", "value": "time_bounded", "status": "confirmed", "source": "customer", "fact_text": ""},
                ]
            },
        },
        "Platform engineers may keep an exception lane, but some teams want direct API keys to call providers without the gateway.",
    )

    assert guidance["decision_focus"] == "control_plane"
    assert guidance["next_best_question"].startswith("Will every approved harness and exception lane still use the same identity")
    assert guidance["candidate_options"][0]["path"] == "decision/control-plane/shared-governance"
    assert any("outside the shared control plane" in risk.lower() for risk in guidance["risks"])


def test_prior_recommendation_text_does_not_self_confirm_shared_control_plane():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {
            "operating_model": "default_plus_exceptions",
            "recommendation": "Keep every approved lane on one shared control plane even when execution differs.",
            "decisions": [
                "Draft recommendation: shared control plane for all lanes."
            ],
            "traversal_state": {
                "customer_confirmed_facts": [
                    {
                        "key": "operating_model",
                        "value": "default_plus_exceptions",
                        "status": "confirmed",
                        "source": "operating_model",
                        "fact_text": "",
                    }
                ]
            },
        },
        "Continue.",
    )

    assert not any(
        "all approved harnesses and exception lanes stay on one shared control plane" in item.lower()
        for item in guidance["decisions"]
    )
    assert all(item["key"] != "shared_control_plane" for item in guidance["customer_confirmed_facts"])


def test_prior_recommendation_text_does_not_pollute_current_tools_fact():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {
            "recommendation": "Use Claude Code Enterprise as the single standard harness.",
            "decisions": ["Standardize on Claude Code Enterprise."],
        },
        "What observability controls should we expect?",
    )

    assert all(item["key"] != "current_tools" for item in guidance["customer_confirmed_facts"])
    assert guidance["facts"] == []


def test_population_policy_question_activates_after_shared_control_plane_is_confirmed():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {
            "operating_model": "default_plus_exceptions",
            "traversal_state": {
                "customer_confirmed_facts": [
                    {"key": "exception_scope", "value": "named_populations", "status": "confirmed", "source": "customer", "fact_text": ""},
                    {"key": "exception_review", "value": "time_bounded", "status": "confirmed", "source": "customer", "fact_text": ""},
                    {"key": "shared_control_plane", "value": True, "status": "confirmed", "source": "customer", "fact_text": ""},
                ]
            },
        },
        "Contractors and platform engineers need different guardrails and quota limits.",
    )

    assert guidance["decision_focus"] == "population_policy"
    assert guidance["next_best_question"].startswith("Which named developer populations need differentiated quota")
    assert guidance["candidate_options"][0]["path"] == "decision/population-policy/named-policy-tiers"


def test_named_time_bounded_policy_tiers_resolve_into_a_population_policy_decision():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {
            "traversal_state": {
                "customer_confirmed_facts": [
                    {"key": "shared_control_plane", "value": True, "status": "confirmed", "source": "customer", "fact_text": ""},
                ]
            },
        },
        "Platform engineers and contractors will sit in named policy tiers with 90-day renewal.",
    )

    assert any("named, time-bounded policy tiers" in item for item in guidance["decisions"])


def test_model_routing_question_activates_when_multiple_providers_are_in_scope():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {
            "traversal_state": {
                "customer_confirmed_facts": [
                    {"key": "shared_control_plane", "value": True, "status": "confirmed", "source": "customer", "fact_text": ""},
                ]
            },
        },
        "We need Bedrock and OpenAI in play, with frontier models for architecture work and cheaper models for simple tasks.",
    )

    assert guidance["decision_focus"] == "model_routing"
    assert guidance["next_best_question"].startswith("Will all approved harnesses route models through one shared gateway")
    assert guidance["candidate_options"][0]["path"] == "decision/model-routing/shared-gateway-tiered"


def test_shared_gateway_and_tiering_answer_is_carried_as_a_model_routing_decision():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"facts": []},
        "We will use Bedrock and OpenAI behind one central model gateway with tiered routing so cheaper models handle simple tasks and frontier models handle architecture work.",
    )

    assert any("shared gateway with explicit provider and tiering policy" in item for item in guidance["decisions"])


def test_multi_cloud_question_activates_for_azure_and_gcp_without_forced_migration():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"facts": []},
        "An acquired BU is on Azure, another team is on GCP, and they need the same platform policy without AWS migration.",
    )

    assert guidance["decision_focus"] == "multi_cloud"
    assert guidance["next_best_question"].startswith("Do the Azure or GCP populations need governed cloud-resident lanes")
    assert guidance["candidate_options"][0]["path"] == "decision/multi-cloud/federated-governed-lanes"


def test_federated_multi_cloud_answer_is_carried_as_a_decision():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"facts": []},
        "Azure and GCP will stay cloud-resident with no AWS migration, but they will run as one platform across clouds with the same policy and audit model.",
    )

    assert any("governed as federated lanes" in item for item in guidance["decisions"])


def test_regional_compliance_question_activates_for_works_council_signal():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"facts": []},
        "Our Germany engineering org needs works council approval before rollout.",
    )

    assert guidance["decision_focus"] == "compliance_overlay"
    assert guidance["next_best_question"].startswith("For EU populations subject to works-council")
    assert guidance["candidate_options"][0]["path"] == "decision/regional-compliance/aggregate-team-telemetry"


def test_aggregate_team_telemetry_answer_is_carried_as_a_regional_compliance_decision():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"facts": []},
        "For Germany we will keep telemetry aggregate by team and avoid individual developer dashboards.",
    )

    assert any("aggregate-by-team telemetry" in item for item in guidance["decisions"])


def test_no_compliance_signal_closes_compliance_domain_without_promoting_regulatory_facts():
    kb = load_knowledge_base(KNOWLEDGE_DIR)
    guidance = build_turn_guidance(
        kb,
        {"facts": []},
        "This is a simple enterprise rollout with no compliance requirements and no HIPAA, ITAR, PCI, or SOX scope.",
    )

    assert guidance["closed_domains"] == ["compliance_overlay"]
    assert all(item["key"] != "export_control" for item in guidance["customer_confirmed_facts"])
