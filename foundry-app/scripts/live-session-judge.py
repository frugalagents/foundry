#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TABLE = "foundry-app-main"
DEFAULT_REGION = "us-east-1"
DEFAULT_REPORT_DIR = ROOT / ".reports" / "live-session-judge"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_section(markdown: str, title: str) -> str:
    pattern = rf"^## {re.escape(title)}\n+(.*?)(?=^## |\Z)"
    match = re.search(pattern, markdown, re.S | re.M)
    return match.group(1).strip() if match else ""


def extract_judge_expectations(markdown: str) -> dict[str, Any]:
    section = extract_section(markdown, "Judge Expectations")
    if not section:
        return {}
    match = re.search(r"```json\s*(\{.*?\})\s*```", section, re.S)
    if not match:
        return {}
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def has_output_pack_content(pack: dict[str, Any] | None) -> bool:
    if not isinstance(pack, dict):
        return False
    return any([
        bool(pack.get("executive_summary")),
        bool(pack.get("recommendation_memo")),
        bool(pack.get("architecture_narrative")),
        bool(pack.get("key_decisions")),
        bool(pack.get("risks_and_mitigations")),
        bool(pack.get("rollout_30_90_180")),
        bool(pack.get("operating_principles")),
        bool(pack.get("control_checklist")),
    ])


def stage_of(workspace: dict[str, Any]) -> str:
    value = str(workspace.get("stage") or "").strip().lower()
    if value in {"solutioning", "blueprint"}:
        return value
    return "discovery"


def count_blocking_questions(workspace: dict[str, Any]) -> int:
    question_state = workspace.get("question_state") if isinstance(workspace.get("question_state"), list) else []
    structured = [
        item for item in question_state
        if isinstance(item, dict) and item.get("status") == "open" and item.get("blocking") is True
    ]
    if structured:
        return len(structured)
    return len(workspace.get("open_questions") or [])


def resolve_blueprint_mode(workspace: dict[str, Any], architecture_artifact: dict[str, Any] | None) -> str:
    architecture_case = workspace.get("architecture_case") if isinstance(workspace.get("architecture_case"), dict) else {}
    artifacts = architecture_case.get("artifacts") if isinstance(architecture_case.get("artifacts"), dict) else {}
    if str(artifacts.get("blueprint_markdown") or "").strip():
        return "published"
    if str(workspace.get("blueprint_markdown") or "").strip():
        return "published"
    advisory_case = workspace.get("advisory_case") if isinstance(workspace.get("advisory_case"), dict) else {}
    output_pack = advisory_case.get("output_pack") if isinstance(advisory_case.get("output_pack"), dict) else None
    if has_output_pack_content(output_pack):
        return "published"
    if any([
        str(workspace.get("recommendation") or "").strip(),
        str((architecture_artifact or {}).get("executive_summary") or "").strip(),
        len(workspace.get("decisions") or []),
        len(workspace.get("implementation_plan") or []),
    ]):
        return "derived"
    return "empty"


def recommendation_corpus(workspace: dict[str, Any], architecture_artifact: dict[str, Any] | None) -> str:
    advisory_case = workspace.get("advisory_case") if isinstance(workspace.get("advisory_case"), dict) else {}
    recommendation = advisory_case.get("recommendation") if isinstance(advisory_case.get("recommendation"), dict) else {}
    recommendation_state = workspace.get("recommendation_state") if isinstance(workspace.get("recommendation_state"), dict) else {}
    output_pack = advisory_case.get("output_pack") if isinstance(advisory_case.get("output_pack"), dict) else {}
    architecture_case = workspace.get("architecture_case") if isinstance(workspace.get("architecture_case"), dict) else {}
    artifacts = architecture_case.get("artifacts") if isinstance(architecture_case.get("artifacts"), dict) else {}
    combined = "\n".join([
        str(workspace.get("recommendation") or ""),
        str(recommendation.get("summary") or ""),
        str(recommendation.get("why_this") or ""),
        str(recommendation_state.get("primary_recommendation") or ""),
        str(output_pack.get("executive_summary") or ""),
        str(output_pack.get("recommendation_memo") or ""),
        str((architecture_artifact or {}).get("executive_summary") or ""),
        str(workspace.get("blueprint_markdown") or ""),
        str(artifacts.get("blueprint_markdown") or ""),
    ])
    return normalize_text(combined)


def fetch_messages(table, customer_id: str, session_id: str) -> list[dict[str, Any]]:
    response = table.query(
        KeyConditionExpression=(
            Key("PK").eq(f"CUSTOMER#{customer_id}") &
            Key("SK").begins_with(f"MSG#{session_id}#")
        ),
    )
    items = response.get("Items", [])
    items.sort(key=lambda item: item.get("created_at", ""))
    return items


def fetch_latest_canvas(table, customer_id: str, session_id: str) -> dict[str, Any] | None:
    response = table.query(
        KeyConditionExpression=(
            Key("PK").eq(f"CUSTOMER#{customer_id}") &
            Key("SK").begins_with(f"CANVAS#{session_id}#")
        ),
        ScanIndexForward=False,
        Limit=1,
    )
    items = response.get("Items", [])
    if not items:
        return None
    item = items[0]
    return {
        "nodes": json.loads(item.get("nodes_json") or "[]"),
        "edges": json.loads(item.get("edges_json") or "[]"),
        "stage": item.get("stage") or "",
        "baseline_node_ids": json.loads(item.get("baseline_node_ids_json") or "[]"),
        "architecture_artifact": json.loads(item.get("architecture_artifact_json") or "{}") or None,
        "updated_at": item.get("updated_at") or item.get("created_at") or "",
    }


def fetch_workspace(table, customer_id: str, session_id: str) -> dict[str, Any] | None:
    response = table.get_item(Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"WORKSPACE#{session_id}"})
    item = response.get("Item")
    if not item:
        return None
    return {
        "stage": item.get("stage") or "",
        "recommendation": item.get("recommendation") or "",
        "blueprint_markdown": item.get("blueprint_markdown") or "",
        "assumptions": json.loads(item.get("assumptions_json") or "[]"),
        "facts": item.get("facts") or [],
        "operating_model": item.get("operating_model") or "",
        "question_state": json.loads(item.get("question_state_json") or "[]"),
        "open_questions": item.get("open_questions") or [],
        "decisions": item.get("decisions") or [],
        "risks": item.get("risks") or [],
        "implementation_plan": item.get("implementation_plan") or [],
        "advisory_case": json.loads(item.get("advisory_case_json") or "{}") or {},
        "recommendation_state": json.loads(item.get("recommendation_state_json") or "{}") or {},
        "artifact_status": json.loads(item.get("artifact_status_json") or "{}") or {},
        "updated_at": item.get("updated_at") or "",
    }


def fetch_latest_architecture_case(table, customer_id: str, session_id: str) -> dict[str, Any] | None:
    response = table.query(
        KeyConditionExpression=(
            Key("PK").eq(f"CUSTOMER#{customer_id}") &
            Key("SK").begins_with(f"CASE#{session_id}#")
        ),
        ScanIndexForward=False,
        Limit=1,
    )
    items = response.get("Items", [])
    if not items:
        return None
    return json.loads(items[0].get("architecture_case_json") or "{}") or None


def deterministic_findings(
    expectations: dict[str, Any],
    messages: list[dict[str, Any]],
    workspace: dict[str, Any],
    canvas: dict[str, Any] | None,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    architecture_artifact = (canvas or {}).get("architecture_artifact") if isinstance(canvas, dict) else None
    stage = stage_of(workspace)
    blueprint_mode = resolve_blueprint_mode(workspace, architecture_artifact)
    blocking_questions = count_blocking_questions(workspace)
    confidence = (
        ((workspace.get("advisory_case") or {}).get("recommendation") or {}).get("confidence")
        or ((workspace.get("recommendation_state") or {}).get("confidence") or "")
    )
    has_architecture = bool((canvas or {}).get("nodes")) or architecture_artifact is not None
    corpus = recommendation_corpus(workspace, architecture_artifact)

    def push(component: str, severity: str, title: str, detail: str) -> None:
        findings.append({
            "component": component,
            "severity": severity,
            "title": title,
            "detail": detail,
        })

    if not any(message.get("role") == "agent" for message in messages):
        push("transcript", "critical", "No advisor output in transcript", "The persisted session has no agent message to explain the result.")
    if not str(workspace.get("recommendation") or "").strip():
        push("brief", "critical", "Recommendation missing", "The workspace has no current recommendation.")
    if stage != "discovery" and not has_architecture:
        push("architecture", "critical", "Architecture missing", "The session advanced beyond discovery without a canvas or architecture artifact.")
    if stage != "blueprint":
        push("workspace", "critical", "Session did not finalize", f"The session ended in `{stage}` instead of a finalized `blueprint` state.")
    if confidence != "high":
        push("brief", "critical", "Brief confidence is not final", f"Expected a final recommendation at `high` confidence, got `{confidence or 'unset'}`.")
    if blocking_questions > 0:
        push("questions", "critical", "Blocking questions remain open", f"The session still has {blocking_questions} blocking question(s).")
    implementation_count = len(workspace.get("implementation_plan") or [])
    if implementation_count == 0:
        push("blueprint", "critical", "Implementation plan missing", "The published blueprint has no implementation steps or rollout actions.")
    if expectations.get("required_stage") and stage != expectations["required_stage"]:
        push("workspace", "critical", "Scenario ended in the wrong stage", f"Expected `{expectations['required_stage']}`, got `{stage}`.")
    if expectations.get("required_confidence") and confidence != expectations["required_confidence"]:
        push("brief", "critical", "Confidence target not met", f"Expected `{expectations['required_confidence']}`, got `{confidence or 'unset'}`.")
    if expectations.get("require_architecture") and not has_architecture:
        push("architecture", "critical", "Architecture required", "Judge expectations require a visible architecture.")
    if expectations.get("require_blueprint") and blueprint_mode != "published":
        push("blueprint", "critical", "Blueprint not canonical", f"Expected a published blueprint, got `{blueprint_mode}`.")
    if isinstance(expectations.get("max_open_questions"), int) and blocking_questions > expectations["max_open_questions"]:
        push("questions", "critical", "Too many open questions", f"Expected at most {expectations['max_open_questions']}, got {blocking_questions}.")
    for term in expectations.get("must_address") or []:
        if normalize_text(term) not in corpus:
            push("brief", "warning", "Expected topic missing", f'The recommendation path does not clearly address "{term}".')
    for term in expectations.get("must_not") or []:
        if normalize_text(term) in corpus:
            push("brief", "warning", "Disallowed topic present", f'The recommendation path still includes "{term}".')
    return findings


def build_packet(
    *,
    simulation_file: Path,
    customer_id: str,
    session_id: str,
    session: dict[str, Any] | None,
    messages: list[dict[str, Any]],
    workspace: dict[str, Any],
    canvas: dict[str, Any] | None,
    architecture_case: dict[str, Any] | None,
) -> dict[str, Any]:
    markdown = read_text(simulation_file)
    customer_profile = extract_section(markdown, "Customer Profile")
    expectations = extract_judge_expectations(markdown)
    if architecture_case:
        workspace = dict(workspace)
        workspace["architecture_case"] = architecture_case
    architecture_artifact = (canvas or {}).get("architecture_artifact") if isinstance(canvas, dict) else None
    advisory_case = workspace.get("advisory_case") if isinstance(workspace.get("advisory_case"), dict) else {}
    recommendation = advisory_case.get("recommendation") if isinstance(advisory_case.get("recommendation"), dict) else {}
    blueprint_mode = resolve_blueprint_mode(workspace, architecture_artifact)
    findings = deterministic_findings(expectations, messages, workspace, canvas)

    return {
        "simulation_file": str(simulation_file),
        "customer_id": customer_id,
        "session_id": session_id,
        "session_title": (session or {}).get("title") or "",
        "customer_profile": customer_profile,
        "judge_expectations": expectations,
        "outcome": {
            "stage": stage_of(workspace),
            "confidence": recommendation.get("confidence") or ((workspace.get("recommendation_state") or {}).get("confidence") or ""),
            "recommendation": workspace.get("recommendation") or recommendation.get("summary") or "",
            "blocking_question_count": count_blocking_questions(workspace),
            "blueprint_mode": blueprint_mode,
            "facts_count": len(workspace.get("facts") or []),
            "decision_count": len(workspace.get("decisions") or []),
            "risk_count": len(workspace.get("risks") or []),
            "implementation_count": len(workspace.get("implementation_plan") or []),
        },
        "ui_surfaces": {
            "brief": {
                "recommendation": workspace.get("recommendation") or recommendation.get("summary") or "",
                "confidence": recommendation.get("confidence") or ((workspace.get("recommendation_state") or {}).get("confidence") or ""),
                "facts": workspace.get("facts") or [],
                "decisions": workspace.get("decisions") or [],
                "risks": workspace.get("risks") or [],
            },
            "questions": {
                "blocking_count": count_blocking_questions(workspace),
                "open_questions": workspace.get("open_questions") or [],
                "question_state": workspace.get("question_state") or [],
                "next_best_question": ((workspace.get("recommendation_state") or {}).get("next_best_question") or ""),
            },
            "assumptions": {
                "assumption_count": len(workspace.get("assumptions") or []),
                "assumptions": workspace.get("assumptions") or [],
            },
            "blueprint": {
                "mode": blueprint_mode,
                "blueprint_markdown": workspace.get("blueprint_markdown") or ((workspace.get("architecture_case") or {}).get("artifacts") or {}).get("blueprint_markdown") or "",
                "output_pack_present": has_output_pack_content((advisory_case.get("output_pack") if isinstance(advisory_case.get("output_pack"), dict) else None)),
            },
            "architecture": {
                "node_count": len((canvas or {}).get("nodes") or []),
                "edge_count": len((canvas or {}).get("edges") or []),
                "baseline_node_count": len((canvas or {}).get("baseline_node_ids") or []),
                "artifact_summary": (architecture_artifact or {}).get("executive_summary") or "",
            },
            "transcript": {
                "message_count": len(messages),
                "agent_turn_count": len([m for m in messages if m.get("role") == "agent"]),
                "user_turn_count": len([m for m in messages if m.get("role") == "user"]),
                "messages": messages,
            },
        },
        "deterministic_findings": findings,
    }


def build_prompt(packet: dict[str, Any]) -> str:
    return f"""You are an enterprise product review judge.

You are reviewing the output of an advisory app after a real simulated enterprise customer session.
Judge whether the app behaved correctly for the customer scenario and whether it produced the right recommendation, architecture, and blueprint.

Focus on:
1. Whether the recommendation fits the customer profile and constraints.
2. Whether the architecture actually addresses the hard requirements.
3. Whether the blueprint is complete and implementation-ready.
4. Whether the visible UI surfaces tell the truth about readiness and remaining uncertainty.
5. What product features would make this review workflow more useful.

Use the simulation's judge expectations as the intended outcome, but do not blindly accept them if the output does not justify them.

Return strict JSON with this shape:
{{
  "overall_verdict": "pass" | "mixed" | "fail",
  "judge_confidence": "low" | "medium" | "high",
  "summary": "short paragraph",
  "recommendation_review": {{
    "score": 1,
    "is_correct_for_customer": true,
    "assessment": "...",
    "evidence": ["..."]
  }},
  "architecture_review": {{
    "score": 1,
    "is_complete_enough": true,
    "assessment": "...",
    "strengths": ["..."],
    "gaps": ["..."]
  }},
  "blueprint_review": {{
    "score": 1,
    "is_complete_enough": true,
    "assessment": "...",
    "missing_elements": ["..."]
  }},
  "ui_accuracy_review": [
    {{
      "component": "brief|questions|assumptions|blueprint|architecture|transcript",
      "status": "accurate|partially_accurate|misleading|missing",
      "score": 1,
      "assessment": "...",
      "suggested_improvements": ["..."]
    }}
  ],
  "open_items": [
    {{
      "severity": "critical|warning|note",
      "title": "...",
      "reason": "...",
      "suggested_fix": "..."
    }}
  ],
  "suggested_features": [
    {{
      "name": "...",
      "priority": "high|medium|low",
      "why_it_matters": "...",
      "implementation_hint": "..."
    }}
  ]
}}

Judge this packet:
{json.dumps(packet, indent=2)}
"""


def invoke_bedrock(
    prompt: str,
    *,
    profile: str,
    region: str,
    model_id: str,
    max_tokens: int,
    temperature: float,
    connect_timeout: int,
    read_timeout: int,
) -> str:
    session = boto3.Session(profile_name=profile or None, region_name=region)
    client = session.client(
        "bedrock-runtime",
        config=Config(
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            retries={"max_attempts": 3, "mode": "adaptive"},
        ),
    )
    response = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    content = (((response.get("output") or {}).get("message") or {}).get("content") or [])
    return "\n".join(item.get("text", "") for item in content if isinstance(item, dict)).strip()


def extract_json_object(text: str) -> dict[str, Any] | None:
    if not text.strip():
        return None
    fenced = re.search(r"```json\s*(\{.*\})\s*```", text, re.S)
    candidates = [fenced.group(1)] if fenced else []
    candidates.append(text.strip())
    balanced = extract_balanced_json_object(text)
    if balanced:
        candidates.append(balanced)
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def extract_balanced_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return None


def extract_review_payload(text: str) -> dict[str, Any]:
    parsed = extract_json_object(text)
    if parsed:
        return parsed

    fallback: dict[str, Any] = {}
    verdict = _extract_string_field(text, "overall_verdict")
    confidence = _extract_string_field(text, "judge_confidence")
    summary = _extract_string_field(text, "summary")
    if verdict:
        fallback["overall_verdict"] = verdict
    if confidence:
        fallback["judge_confidence"] = confidence
    if summary:
        fallback["summary"] = summary
    return fallback


def normalize_review_payload(parsed: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(parsed or {})
    verdict = str(normalized.get("overall_verdict") or "unknown").strip().lower()
    if verdict not in {"pass", "mixed", "fail"}:
        verdict = "unknown"
    critical_findings = [
        finding for finding in packet.get("deterministic_findings", [])
        if isinstance(finding, dict) and str(finding.get("severity") or "").strip().lower() == "critical"
    ]
    outcome = packet.get("outcome") if isinstance(packet.get("outcome"), dict) else {}
    stage = str(outcome.get("stage") or "").strip().lower()
    confidence = str(outcome.get("confidence") or "").strip().lower()
    blocking_count = int(outcome.get("blocking_question_count") or 0)
    implementation_count = int(outcome.get("implementation_count") or 0)
    has_outcome = any(
        key in outcome
        for key in ("stage", "confidence", "blocking_question_count", "implementation_count")
    )

    target_verdict = verdict
    if critical_findings or (
        has_outcome
        and (stage != "blueprint" or confidence != "high" or blocking_count > 0 or implementation_count == 0)
    ):
        if critical_findings or stage != "blueprint" or blocking_count > 0 or implementation_count == 0 or len(critical_findings) >= 2:
            target_verdict = "fail"
        else:
            target_verdict = "mixed"

    severity_rank = {"unknown": 0, "pass": 1, "mixed": 2, "fail": 3}
    if severity_rank.get(target_verdict, 0) > severity_rank.get(verdict, 0):
        normalized["overall_verdict"] = target_verdict
        reasons: list[str] = []
        if has_outcome and stage != "blueprint":
            reasons.append(f"stage is `{stage or 'unset'}`")
        if has_outcome and confidence != "high":
            reasons.append(f"brief confidence is `{confidence or 'unset'}`")
        if has_outcome and blocking_count > 0:
            reasons.append(f"{blocking_count} blocking question(s) remain")
        if has_outcome and implementation_count == 0:
            reasons.append("no implementation steps are published")
        note = "Deterministic completion guardrails downgraded the verdict because " + ", ".join(reasons) + "."
        summary = str(normalized.get("summary") or "").strip()
        normalized["summary"] = f"{summary} {note}".strip() if summary else note
    elif verdict != "unknown":
        normalized["overall_verdict"] = verdict

    confidence_value = str(normalized.get("judge_confidence") or "unknown").strip().lower()
    if confidence_value not in {"low", "medium", "high"}:
        normalized["judge_confidence"] = "unknown"
    else:
        normalized["judge_confidence"] = confidence_value
    return normalized


def _extract_string_field(text: str, field: str) -> str:
    pattern = rf'"{re.escape(field)}"\s*:\s*"((?:[^"\\]|\\.)*)"'
    match = re.search(pattern, text, re.S)
    if not match:
        return ""
    try:
        return json.loads(f'"{match.group(1)}"')
    except json.JSONDecodeError:
        return match.group(1).strip()


def render_summary(packet: dict[str, Any], response_text: str | None) -> str:
    findings = packet["deterministic_findings"]
    lines = [
        "# Live Session Judge",
        "",
        f"- Session title: `{packet['session_title'] or packet['session_id']}`",
        f"- Session id: `{packet['session_id']}`",
        f"- Stage: `{packet['outcome']['stage']}`",
        f"- Confidence: `{packet['outcome']['confidence'] or 'unset'}`",
        f"- Blueprint mode: `{packet['outcome']['blueprint_mode']}`",
        f"- Blocking questions: `{packet['outcome']['blocking_question_count']}`",
        f"- Deterministic findings: `{len(findings)}`",
        "",
        "## Deterministic Findings",
        "",
    ]
    if findings:
        for finding in findings:
            lines.append(f"- `{finding['severity']}` [{finding['component']}] {finding['title']}: {finding['detail']}")
    else:
        lines.append("- No deterministic findings.")

    if response_text is not None:
        lines.extend(["", "## Judge Response", "", "```json", response_text.strip() or "{}", "```"])
    return "\n".join(lines) + "\n"


def build_transcript_summary_message(response_text: str, packet: dict[str, Any]) -> str:
    parsed = normalize_review_payload(extract_review_payload(response_text), packet)
    verdict = parsed.get("overall_verdict", "unknown")
    confidence = parsed.get("judge_confidence", "unknown")
    summary = parsed.get("summary", "").strip()
    open_items = parsed.get("open_items") if isinstance(parsed.get("open_items"), list) else []
    features = parsed.get("suggested_features") if isinstance(parsed.get("suggested_features"), list) else []

    lines = [
        "## Review Judge Summary",
        "",
        f"- Verdict: `{verdict}`",
        f"- Judge confidence: `{confidence}`",
    ]
    if summary:
        lines.extend(["", summary])
    if open_items:
        lines.extend(["", "### Top Open Items"])
        for item in open_items[:3]:
            if not isinstance(item, dict):
                continue
            lines.append(f"- **{item.get('title', 'Untitled')}**: {item.get('reason', '')}")
    if features:
        lines.extend(["", "### Suggested Features"])
        for feature in features[:3]:
            if not isinstance(feature, dict):
                continue
            lines.append(f"- **{feature.get('name', 'Untitled')}** ({feature.get('priority', 'unknown')}): {feature.get('why_it_matters', '')}")
    if packet["deterministic_findings"]:
        lines.extend(["", "### Deterministic Findings"])
        for finding in packet["deterministic_findings"][:3]:
            lines.append(f"- **{finding['title']}**: {finding['detail']}")
    return "\n".join(lines).strip()


def append_message_and_touch_session(table, *, customer_id: str, session_id: str, content: str) -> None:
    now = now_iso()
    table.put_item(
        Item={
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"MSG#{session_id}#{now}#{uuid.uuid4().hex[:8]}",
            "session_id": session_id,
            "customer_id": customer_id,
            "role": "agent",
            "content": content,
            "created_at": now,
        }
    )
    table.update_item(
        Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"SESSION#{session_id}"},
        UpdateExpression="SET updated_at = :updated_at",
        ExpressionAttributeValues={":updated_at": now},
    )


def persist_judge_report(
    table,
    *,
    customer_id: str,
    session_id: str,
    packet: dict[str, Any],
    response_text: str,
    run_dir: Path,
) -> str:
    parsed = normalize_review_payload(extract_review_payload(response_text), packet)
    created_at = now_iso()
    report_id = f"judge_{uuid.uuid4().hex}"
    item = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": f"JUDGE#{session_id}#{created_at}",
        "judge_report_id": report_id,
        "customer_id": customer_id,
        "session_id": session_id,
        "session_title": packet.get("session_title", ""),
        "simulation_file": packet.get("simulation_file", ""),
        "overall_verdict": str(parsed.get("overall_verdict") or "unknown"),
        "judge_confidence": str(parsed.get("judge_confidence") or "unknown"),
        "summary": str(parsed.get("summary") or ""),
        "recommendation_review_json": json.dumps(parsed.get("recommendation_review") or {}),
        "architecture_review_json": json.dumps(parsed.get("architecture_review") or {}),
        "blueprint_review_json": json.dumps(parsed.get("blueprint_review") or {}),
        "ui_accuracy_review_json": json.dumps(parsed.get("ui_accuracy_review") or []),
        "deterministic_findings_json": json.dumps(packet.get("deterministic_findings") or []),
        "open_items_json": json.dumps(parsed.get("open_items") or []),
        "suggested_features_json": json.dumps(parsed.get("suggested_features") or []),
        "response_text": response_text,
        "report_dir": str(run_dir),
        "created_at": created_at,
        "updated_at": created_at,
    }
    table.put_item(Item=item)
    return report_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Judge a real persisted advisory session against the originating simulation's expectations.")
    parser.add_argument("simulation_file", type=Path)
    parser.add_argument("--customer-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--profile", default="")
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--bedrock-model-id", default="")
    parser.add_argument("--max-tokens", type=int, default=2200)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--connect-timeout", type=int, default=20)
    parser.add_argument("--read-timeout", type=int, default=180)
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--append-summary-message", action="store_true")
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile or None, region_name=args.region)
    table = session.resource("dynamodb").Table(args.table)

    session_item = table.get_item(
        Key={"PK": f"CUSTOMER#{args.customer_id}", "SK": f"SESSION#{args.session_id}"}
    ).get("Item")
    if not session_item:
        raise SystemExit(f"Session not found: customer_id={args.customer_id} session_id={args.session_id}")

    messages = fetch_messages(table, args.customer_id, args.session_id)
    workspace = fetch_workspace(table, args.customer_id, args.session_id)
    if not workspace:
        raise SystemExit("Workspace snapshot not found for session.")
    canvas = fetch_latest_canvas(table, args.customer_id, args.session_id)
    architecture_case = fetch_latest_architecture_case(table, args.customer_id, args.session_id)

    packet = build_packet(
        simulation_file=args.simulation_file,
        customer_id=args.customer_id,
        session_id=args.session_id,
        session=session_item,
        messages=messages,
        workspace=workspace,
        canvas=canvas,
        architecture_case=architecture_case,
    )
    prompt = build_prompt(packet)

    run_dir = Path(args.report_dir) / f"{now_stamp()}-{args.session_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "packet.json").write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    response_text: str | None = None
    report_id: str | None = None
    if args.bedrock_model_id:
        response_text = invoke_bedrock(
            prompt,
            profile=args.profile,
            region=args.region,
            model_id=args.bedrock_model_id,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            connect_timeout=args.connect_timeout,
            read_timeout=args.read_timeout,
        )
        (run_dir / "response.txt").write_text(response_text + "\n", encoding="utf-8")
        if response_text.strip():
            report_id = persist_judge_report(
                table,
                customer_id=args.customer_id,
                session_id=args.session_id,
                packet=packet,
                response_text=response_text,
                run_dir=run_dir,
            )
        if args.append_summary_message and extract_review_payload(response_text):
            append_message_and_touch_session(
                table,
                customer_id=args.customer_id,
                session_id=args.session_id,
                content=build_transcript_summary_message(response_text, packet),
            )

    summary = render_summary(packet, response_text)
    (run_dir / "summary.md").write_text(summary, encoding="utf-8")

    print(f"packet={run_dir / 'packet.json'}")
    print(f"prompt={run_dir / 'prompt.txt'}")
    print(f"summary={run_dir / 'summary.md'}")
    if args.bedrock_model_id:
        print(f"response={run_dir / 'response.txt'}")
        if report_id:
            print(f"judge_report_id={report_id}")
        if args.append_summary_message:
            print("appended_summary_message=true")


if __name__ == "__main__":
    main()
