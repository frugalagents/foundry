from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from architecture_spine import build_architecture_snapshot


def test_architecture_snapshot_waits_for_minimum_detail():
    snapshot = build_architecture_snapshot(
        {
            "stage": "discovery",
            "recommendation": "",
            "facts": ["Customer uses GitHub Copilot."],
            "question_state": [],
            "decisions": [],
            "risks": [],
            "traversal_state": {"structured_facts": []},
        }
    )

    assert snapshot is None


def test_architecture_snapshot_builds_a_clean_baseline_for_regulated_local_split():
    snapshot = build_architecture_snapshot(
        {
            "stage": "discovery",
            "recommendation": (
                "Do not assume a shared local execution pattern for export-controlled "
                "workloads. Treat this as a controlled split-boundary decision before "
                "locking the platform shape."
            ),
            "facts": [
                "Export-controlled / ITAR-sensitive repositories appear to be in scope.",
                "Current tools in scope: GitHub Copilot, Cursor.",
                "At least one population or business unit is asking for local execution.",
            ],
            "question_state": [
                {
                    "id": "execution-boundary-regulated-local",
                    "text": (
                        "Are the export-controlled repositories isolated to a separate "
                        "developer population and execution lane, or does the business "
                        "unit expect local execution for those same workloads?"
                    ),
                    "why_it_matters": (
                        "This answer determines whether local execution can stay in "
                        "scope at all for regulated workloads."
                    ),
                    "blocking": True,
                    "decision_domain": "execution_boundary",
                    "status": "open",
                    "answer": "",
                    "source": "okf",
                }
            ],
            "decisions": [
                "Do not assume a shared local execution path for export-controlled workloads."
            ],
            "risks": [
                "If the same regulated repositories are expected to use local execution, the platform will need a materially different execution and policy boundary."
            ],
            "operating_model": "undecided",
            "traversal_state": {
                "structured_facts": [
                    {"key": "current_tools", "value": ["GitHub Copilot", "Cursor"]},
                    {"key": "export_control", "value": True},
                    {"key": "local_execution_requested", "value": True},
                ],
                "candidate_options": [],
            },
        }
    )

    assert snapshot is not None
    assert snapshot["stage"] == "baseline"
    assert "surface-entry" in snapshot["baseline_node_ids"]
    node_ids = {node["id"] for node in snapshot["nodes"]}
    baseline_labels = {node["label"] for node in snapshot["nodes"] if node["id"] in snapshot["baseline_node_ids"]}
    assert "harness-cursor" in node_ids
    assert "harness-github-copilot" in node_ids
    assert "Cursor" not in baseline_labels
    assert "GitHub Copilot" not in baseline_labels
    assert any(label.startswith("Container runtime") for label in baseline_labels)
    assert "execution-regulated" in {node["id"] for node in snapshot["nodes"]}
    assert "access-export-control" in {node["id"] for node in snapshot["nodes"]}
    assert any(lane["id"] == "current-estate-harnesses" for lane in snapshot["architecture_artifact"]["supporting_lanes"])
    assert any(lane["id"] == "regulated-supporting-lane" for lane in snapshot["architecture_artifact"]["supporting_lanes"])
    assert "cross-cutting" in snapshot["architecture_artifact"]["executive_summary"].lower()


def test_architecture_snapshot_adds_scoped_local_and_exception_governance_lanes():
    snapshot = build_architecture_snapshot(
        {
            "stage": "solutioning",
            "recommendation": (
                "Use one default harness with explicit exception governance, keep "
                "regulated workloads on a separate controlled lane, and allow local "
                "execution only for non-regulated workflows."
            ),
            "facts": [
                "Current tools in scope: GitHub Copilot, Cursor.",
                "Export-controlled repositories are isolated in a separate enclave.",
                "Local execution is only requested for non-regulated general engineering repos.",
            ],
            "question_state": [
                {
                    "id": "operating-model",
                    "text": "Is the target state one standard tool, a governed multi-harness portfolio, or one default tool with formal exception paths?",
                    "why_it_matters": "This determines how exceptions and tool sprawl are governed.",
                    "blocking": True,
                    "decision_domain": "operating_model",
                    "status": "answered",
                    "answer": "One default tool with formal exception paths.",
                    "source": "okf",
                }
            ],
            "decisions": [
                "Adopt one default harness with formal exception paths.",
                "Keep export-controlled workloads on a separate regulated execution lane.",
                "Allow local execution only for non-regulated workflows.",
            ],
            "risks": [
                "Repo classification must stay accurate or local execution scope will drift into regulated populations."
            ],
            "operating_model": "default_plus_exceptions",
            "traversal_state": {
                "structured_facts": [
                    {"key": "current_tools", "value": ["GitHub Copilot", "Cursor"]},
                    {"key": "export_control", "value": True},
                    {"key": "regulated_population_isolated", "value": True},
                    {"key": "local_execution_requested", "value": True},
                    {"key": "local_execution_scope", "value": "non_regulated_only"},
                ],
                "candidate_options": [],
            },
        }
    )

    assert snapshot is not None
    node_ids = {node["id"] for node in snapshot["nodes"]}
    customization_ids = {
        item["id"] for item in snapshot["architecture_artifact"]["customizations"]
    }

    assert "execution-local-general" in node_ids
    assert "access-exception-governance" in node_ids
    assert "harness-cursor" in node_ids
    assert "harness-github-copilot" in node_ids
    baseline_labels = {node["label"] for node in snapshot["nodes"] if node["id"] in snapshot["baseline_node_ids"]}
    assert "Cursor" not in baseline_labels
    assert "GitHub Copilot" not in baseline_labels
    assert any(lane["id"] == "current-estate-harnesses" for lane in snapshot["architecture_artifact"]["supporting_lanes"])
    assert {"regulated-lane", "local-general-lane", "exception-governance"} <= customization_ids
    assert "one default harness with formal exception lanes" in snapshot["architecture_artifact"]["executive_summary"].lower()
    assert "still being finalized" not in snapshot["architecture_artifact"]["executive_summary"].lower()
    execution_layer = next(layer for layer in snapshot["architecture_artifact"]["baseline"]["layers"] if layer["id"] == "execution")
    assert "Container runtime" in execution_layer["component_labels"]


def test_architecture_snapshot_explicitly_calls_out_control_and_regional_lanes():
    snapshot = build_architecture_snapshot(
        {
            "stage": "blueprint",
            "recommendation": (
                "Use a default governed harness on Bedrock, keep PCI scope on a tag-gated policy tier, "
                "route SOX repos through approval-backed workflows, federate identity from Okta, and keep "
                "data science users on a governed notebook lane."
            ),
            "facts": [
                "Okta is the enterprise identity provider.",
                "SOX-scoped financial repos are in scope.",
                "PCI-scoped services stay on shared infrastructure but require session-tag gating.",
                "GitHub Actions runs the pull-request automation path.",
                "Session evidence flows into the SIEM.",
                "Data science uses notebooks today.",
                "Primary regions: us-east-1, eu-west-1, ap-southeast-2.",
            ],
            "decisions": [
                "Use a shared model and tool gateway.",
                "Keep notebook-heavy data science users on a governed notebook lane.",
            ],
            "risks": ["Region-specific evidence retention must stay aligned with the control model."],
            "operating_model": "default_plus_exceptions",
            "traversal_state": {
                "structured_facts": [
                    {"key": "current_tools", "value": ["GitHub Copilot", "Codex CLI"]},
                    {"key": "regions", "value": ["us-east-1", "eu-west-1", "ap-southeast-2"]},
                ],
                "candidate_options": [],
            },
        }
    )

    assert snapshot is not None
    node_ids = {node["id"] for node in snapshot["nodes"]}
    assert {
        "access-okta-federation",
        "access-sox-lane",
        "access-pci-tier",
        "ops-siem-export",
        "gateway-github-delivery",
        "surface-notebook",
        "ops-regional-residency",
    } <= node_ids
    supporting_lane_ids = {item["id"] for item in snapshot["architecture_artifact"]["supporting_lanes"]}
    assert {
        "okta-federation-lane",
        "sox-control-lane",
        "pci-policy-tier",
        "siem-export-lane",
        "github-delivery-lane",
        "notebook-surface-lane",
        "regional-residency-lane",
    } <= supporting_lane_ids
    summary = snapshot["architecture_artifact"]["executive_summary"].lower()
    assert "okta" in summary
    assert "sox" in summary
    assert "pci" in summary
    assert "siem" in summary
    assert "github" in summary
    assert "data science" in summary
    assert "eu-west-1" in summary
