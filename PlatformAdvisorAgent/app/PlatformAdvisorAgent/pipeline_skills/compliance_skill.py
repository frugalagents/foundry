"""Step 5 — Compliance: deterministic rule evaluation, no LLM required."""
from __future__ import annotations
from typing import AsyncIterator

from agent_core_engine.graph_loader import get_graph
from .base import (
    PipelineContext,
    make_chat_message,
    make_panel_update,
    make_panel_complete,
    make_step_transition,
)

COMPLIANCE_REGIMES: dict[str, list[dict]] = {
    "HIPAA": [
        {"id": "hipaa_phi", "name": "PHI Encryption at Rest",     "status": "required", "aws_control": "Amazon Macie + KMS"},
        {"id": "hipaa_baa", "name": "Business Associate Agreement","status": "required", "aws_control": "AWS HIPAA BAA"},
        {"id": "hipaa_audit","name": "Audit Log Retention 6yr",   "status": "required", "aws_control": "CloudTrail + S3 Lifecycle"},
        {"id": "hipaa_access","name":"Minimum Necessary Access",   "status": "required", "aws_control": "IAM + Lake Formation"},
    ],
    "SOC2": [
        {"id": "soc2_cc6",  "name": "Logical & Physical Access",  "status": "required", "aws_control": "IAM Identity Center + SCPs"},
        {"id": "soc2_cc7",  "name": "System Operations Monitoring","status": "required", "aws_control": "CloudWatch + Security Hub"},
        {"id": "soc2_cc9",  "name": "Risk Mitigation",            "status": "required", "aws_control": "AWS Config + Trusted Advisor"},
        {"id": "soc2_avail","name": "Availability SLAs",          "status": "advisory", "aws_control": "Multi-AZ deployments"},
    ],
    "GDPR": [
        {"id": "gdpr_art5",  "name": "Data Minimization",         "status": "required", "aws_control": "Lake Formation column masking"},
        {"id": "gdpr_art17", "name": "Right to Erasure",          "status": "required", "aws_control": "Custom deletion workflows"},
        {"id": "gdpr_art25", "name": "Privacy by Design",         "status": "required", "aws_control": "Macie + KMS + VPC"},
        {"id": "gdpr_dpa",   "name": "DPA with sub-processors",   "status": "required", "aws_control": "AWS DPA + SCCs"},
    ],
    "PCI-DSS": [
        {"id": "pci_req1", "name": "Network Segmentation",        "status": "required", "aws_control": "VPC + Security Groups"},
        {"id": "pci_req3", "name": "Cardholder Data Encryption",  "status": "required", "aws_control": "KMS + CloudHSM"},
        {"id": "pci_req10","name": "Audit Trail",                  "status": "required", "aws_control": "CloudTrail + SIEM"},
        {"id": "pci_req11","name": "Vulnerability Scanning",       "status": "required", "aws_control": "Amazon Inspector"},
    ],
    "FedRAMP": [
        {"id": "fedramp_ato", "name": "ATO Documentation",        "status": "required", "aws_control": "GovCloud ATO package"},
        {"id": "fedramp_cm",  "name": "Configuration Management", "status": "required", "aws_control": "AWS Config + SSM"},
        {"id": "fedramp_ia",  "name": "Identification & Auth",    "status": "required", "aws_control": "IAM + PIV/CAC"},
        {"id": "fedramp_sc",  "name": "System & Comms Protection", "status": "required", "aws_control": "PrivateLink + WAF"},
    ],
}

UNIVERSAL_CONTROLS = [
    {"id": "ctrl_iam",  "name": "Least-Privilege IAM",            "status": "best_practice", "aws_control": "IAM Analyzer"},
    {"id": "ctrl_enc",  "name": "Encryption in Transit (TLS 1.2+)","status": "best_practice", "aws_control": "ACM + ALB"},
    {"id": "ctrl_trail","name": "CloudTrail Enabled",              "status": "best_practice", "aws_control": "AWS CloudTrail"},
    {"id": "ctrl_guard","name": "Threat Detection",                "status": "best_practice", "aws_control": "Amazon GuardDuty"},
]


async def run_compliance(ctx: PipelineContext) -> AsyncIterator[str]:
    """
    Evaluate compliance controls based on answers.compliance_regime.

    Yields SSE events.
    """
    ctx.current_step = 5
    graph = get_graph()

    yield make_panel_update(5, "compliance", {"status": "evaluating", "progress": 10})

    regime = ctx.answers.get("compliance_regime", "")
    if isinstance(regime, list):
        regime = regime[0] if regime else ""

    yield make_panel_update(5, "compliance", {"status": "evaluating", "progress": 40})

    controls: list[dict] = list(UNIVERSAL_CONTROLS)
    if regime:
        regime_key = regime.upper().replace(" ", "-")
        for key, ctrl_list in COMPLIANCE_REGIMES.items():
            if key in regime_key or regime_key in key:
                controls.extend(ctrl_list)
                break

    # Also check graph for Law nodes that affect the selected components
    law_notes: list[str] = []
    for node in graph.get_nodes_by_type("Law"):
        props = graph.get_props(node["id"])
        trigger = props.get("trigger_condition", {})
        if isinstance(trigger, dict):
            if all(str(ctx.answers.get(k, "")).lower() == str(v).lower() for k, v in trigger.items()):
                law_notes.append(props.get("description", node["id"]))

    ctx.compliance_notes = law_notes

    yield make_panel_update(5, "compliance", {"status": "complete", "progress": 100})

    required_count = sum(1 for c in controls if c["status"] == "required")
    advisory_count = sum(1 for c in controls if c["status"] == "advisory")
    bp_count = sum(1 for c in controls if c["status"] == "best_practice")

    yield make_panel_complete(5, "compliance", {
        "regime": regime or "General Best Practices",
        "controls": controls,
        "counts": {
            "required": required_count,
            "advisory": advisory_count,
            "best_practice": bp_count,
        },
        "law_notes": law_notes,
    })

    yield make_chat_message("assistant",
        f"Compliance checked for **{regime or 'General Best Practices'}** "
        f"({required_count} required, {advisory_count} advisory). See Compliance panel →"
    )

    yield make_step_transition(5, 6, "Mapping AWS services...")
