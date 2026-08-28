#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_FILE = ROOT / "frontend" / "lib" / "review-scenarios.json"
DEFAULT_REPORT_DIR = ROOT / ".reports" / "review-judge"


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


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
    open_questions = workspace.get("open_questions") if isinstance(workspace.get("open_questions"), list) else []
    return len(open_questions)


def resolve_blueprint_mode(workspace: dict[str, Any], architecture_artifact: dict[str, Any] | None) -> str:
    architecture_case = workspace.get("architecture_case") if isinstance(workspace.get("architecture_case"), dict) else {}
    artifacts = architecture_case.get("artifacts") if isinstance(architecture_case.get("artifacts"), dict) else {}
    if str(artifacts.get("blueprint_markdown") or "").strip():
        return "published"
    if str(workspace.get("blueprint_markdown") or "").strip():
        return "published"
    advisory_case = workspace.get("advisory_case") if isinstance(workspace.get("advisory_case"), dict) else {}
    if has_output_pack_content(advisory_case.get("output_pack") if isinstance(advisory_case.get("output_pack"), dict) else None):
        return "published"
    if any([
        str(workspace.get("recommendation") or "").strip(),
        architecture_artifact and str(architecture_artifact.get("executive_summary") or "").strip(),
        workspace.get("decisions"),
        workspace.get("implementation_plan"),
    ]):
        return "derived"
    return "empty"


def collect_recommendation_corpus(workspace: dict[str, Any], architecture_artifact: dict[str, Any] | None) -> str:
    advisory_case = workspace.get("advisory_case") if isinstance(workspace.get("advisory_case"), dict) else {}
    recommendation = advisory_case.get("recommendation") if isinstance(advisory_case.get("recommendation"), dict) else {}
    readout = advisory_case.get("readout") if isinstance(advisory_case.get("readout"), dict) else {}
    output_pack = advisory_case.get("output_pack") if isinstance(advisory_case.get("output_pack"), dict) else {}
    architecture_case = workspace.get("architecture_case") if isinstance(workspace.get("architecture_case"), dict) else {}
    artifacts = architecture_case.get("artifacts") if isinstance(architecture_case.get("artifacts"), dict) else {}
    recommendation_state = workspace.get("recommendation_state") if isinstance(workspace.get("recommendation_state"), dict) else {}
    combined = "\n".join([
        str(workspace.get("recommendation") or ""),
        str(recommendation_state.get("primary_recommendation") or ""),
        str(recommendation.get("summary") or ""),
        str(recommendation.get("why_this") or ""),
        str(readout.get("current_recommendation") or ""),
        str(output_pack.get("executive_summary") or ""),
        str(output_pack.get("recommendation_memo") or ""),
        str((architecture_artifact or {}).get("executive_summary") or ""),
        str(workspace.get("blueprint_markdown") or ""),
        str(artifacts.get("blueprint_markdown") or ""),
    ])
    return normalize_text(combined)


def collect_recommended_option_corpus(workspace: dict[str, Any]) -> str:
    recommendation_state = workspace.get("recommendation_state") if isinstance(workspace.get("recommendation_state"), dict) else {}
    options = recommendation_state.get("candidate_options") if isinstance(recommendation_state.get("candidate_options"), list) else []
    recommended = [
        f"{item.get('title', '')} {item.get('summary', '')}"
        for item in options
        if isinstance(item, dict) and item.get("position") == "recommended"
    ]
    return normalize_text("\n".join(recommended))


def audit_scenario(scenario: dict[str, Any]) -> list[dict[str, str]]:
    workspace = scenario.get("workspace") if isinstance(scenario.get("workspace"), dict) else {}
    architecture_artifact = scenario.get("architectureArtifact") if isinstance(scenario.get("architectureArtifact"), dict) else None
    stage = stage_of(workspace)
    blueprint_mode = resolve_blueprint_mode(workspace, architecture_artifact)
    blocking_questions = count_blocking_questions(workspace)
    confidence = (
        ((workspace.get("advisory_case") or {}).get("recommendation") or {}).get("confidence")
        or ((workspace.get("recommendation_state") or {}).get("confidence") or "")
    )
    has_architecture = bool((scenario.get("canvas") or {}).get("nodes")) or architecture_artifact is not None
    findings: list[dict[str, str]] = []

    def push(component: str, severity: str, title: str, detail: str) -> None:
      findings.append({
          "component": component,
          "severity": severity,
          "title": title,
          "detail": detail,
      })

    transcript = scenario.get("transcript") if isinstance(scenario.get("transcript"), list) else []
    if not any(isinstance(message, dict) and message.get("role") == "agent" for message in transcript):
        push("transcript", "critical", "No advisor output in transcript", "No agent turn explains the state shown in the workspace.")
    if not str(workspace.get("recommendation") or "").strip():
        push("brief", "critical", "Recommendation missing", "The brief has no primary recommendation.")
    if stage != "discovery" and not has_architecture:
        push("architecture", "critical", "Solutioning without architecture", "The session advanced but the architecture board has no real content.")
    if stage == "blueprint" and blueprint_mode != "published":
        push("blueprint", "critical", "Blueprint is not canonical", f"The session is in blueprint stage but the blueprint mode is `{blueprint_mode}`.")
    if stage == "blueprint" and blocking_questions > 0:
        push("questions", "warning", "Blueprint still has blocking questions", f"{blocking_questions} blocking question(s) remain.")
    if stage != "discovery" and confidence == "":
        push("brief", "note", "Confidence signal missing", "The brief does not show recommendation confidence.")
    if confidence == "high" and blocking_questions > 0:
        push("brief", "warning", "Confidence overstates readiness", "The brief says high confidence while blockers remain.")

    expectations = scenario.get("expectations") if isinstance(scenario.get("expectations"), dict) else {}
    recommendation_corpus = collect_recommendation_corpus(workspace, architecture_artifact)
    recommended_option_corpus = collect_recommended_option_corpus(workspace)
    if expectations.get("required_stage") and stage != expectations["required_stage"]:
        push("workspace", "critical", "Scenario ended in the wrong stage", f"Expected `{expectations['required_stage']}`, got `{stage}`.")
    if expectations.get("required_confidence") and confidence != expectations["required_confidence"]:
        push("brief", "critical", "Scenario confidence target not met", f"Expected `{expectations['required_confidence']}`, got `{confidence or 'unset'}`.")
    if expectations.get("require_architecture") and not has_architecture:
        push("architecture", "critical", "Scenario requires an architecture view", "Expected an architecture snapshot.")
    if expectations.get("require_published_blueprint") and blueprint_mode != "published":
        push("blueprint", "critical", "Scenario requires a published blueprint", f"Got `{blueprint_mode}`.")
    if isinstance(expectations.get("max_open_questions"), int) and blocking_questions > expectations["max_open_questions"]:
        push("questions", "critical", "Scenario has too many open questions", f"Allowed {expectations['max_open_questions']}, got {blocking_questions}.")

    for term in expectations.get("recommendation_must_include") or []:
        if normalize_text(term) not in recommendation_corpus:
            push("brief", "critical", "Required recommendation signal missing", f'Missing "{term}" in recommendation path.')
    for term in expectations.get("recommendation_must_exclude") or []:
        if normalize_text(term) in recommendation_corpus:
            push("brief", "critical", "Disallowed recommendation signal present", f'Found "{term}" in recommendation path.')
    for term in expectations.get("recommended_option_must_include") or []:
        if normalize_text(term) not in recommended_option_corpus:
            push("brief", "critical", "Recommended option is not explicit enough", f'Missing "{term}" in recommended options.')
    for term in expectations.get("recommended_option_must_exclude") or []:
        if normalize_text(term) in recommended_option_corpus:
            push("brief", "critical", "Recommended option includes a forbidden choice", f'Found "{term}" in recommended options.')
    return findings


def build_packet(scenario: dict[str, Any]) -> dict[str, Any]:
    workspace = scenario.get("workspace") if isinstance(scenario.get("workspace"), dict) else {}
    architecture_artifact = scenario.get("architectureArtifact") if isinstance(scenario.get("architectureArtifact"), dict) else None
    advisory_case = workspace.get("advisory_case") if isinstance(workspace.get("advisory_case"), dict) else {}
    recommendation = advisory_case.get("recommendation") if isinstance(advisory_case.get("recommendation"), dict) else {}
    canvas = scenario.get("canvas") if isinstance(scenario.get("canvas"), dict) else {}
    transcript = scenario.get("transcript") if isinstance(scenario.get("transcript"), list) else []
    blueprint_mode = resolve_blueprint_mode(workspace, architecture_artifact)
    blocking_questions = count_blocking_questions(workspace)
    findings = audit_scenario(scenario)

    return {
        "scenario": {
            "id": scenario.get("id"),
            "name": scenario.get("name"),
            "summary": scenario.get("summary"),
        },
        "product_vision": scenario.get("vision"),
        "success_criteria": scenario.get("success_criteria") or [],
        "expectations": scenario.get("expectations") or {},
        "outcome": {
            "stage": stage_of(workspace),
            "confidence": recommendation.get("confidence") or ((workspace.get("recommendation_state") or {}).get("confidence") or ""),
            "recommendation": workspace.get("recommendation") or recommendation.get("summary") or "",
            "blocking_question_count": blocking_questions,
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
                "blocking_count": blocking_questions,
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
                "node_count": len(canvas.get("nodes") or []),
                "edge_count": len(canvas.get("edges") or []),
                "baseline_node_count": len(canvas.get("baselineNodeIds") or []),
                "artifact_summary": (architecture_artifact or {}).get("executive_summary") or "",
            },
            "transcript": {
                "message_count": len(transcript),
                "agent_turn_count": len([m for m in transcript if isinstance(m, dict) and m.get("role") == "agent"]),
                "user_turn_count": len([m for m in transcript if isinstance(m, dict) and m.get("role") == "user"]),
                "messages": transcript,
            },
        },
        "deterministic_findings": findings,
    }


def build_prompt(packet: dict[str, Any]) -> str:
    packet_json = json.dumps(packet, indent=2)
    return f"""You are a product review judge for an enterprise advisory app.

Evaluate whether the session outcome and UI surfaces match the product vision.
Your job is not just to check completeness. Judge whether the app is making the right recommendation, representing uncertainty honestly, exposing the right artifacts at the right time, and revealing obvious product gaps.

Review dimensions:
1. Vision alignment: Did the outcome actually deliver against the product vision and success criteria?
2. Recommendation quality: Is the recommendation defensible from the available evidence?
3. UI component accuracy: Review the brief, questions, assumptions, blueprint, architecture, and transcript surfaces for accuracy and clarity.
4. Readiness: Is the confidence level honest? Is the blueprint truly complete? Are blockers still present?
5. Feature opportunities: Suggest additional product features that would materially improve the app for real users.

Return strict JSON with this shape:
{{
  "overall_verdict": "pass" | "mixed" | "fail",
  "judge_confidence": "low" | "medium" | "high",
  "summary": "short paragraph",
  "vision_alignment": {{
    "score": 1-5,
    "assessment": "..."
  }},
  "recommendation_review": {{
    "score": 1-5,
    "assessment": "...",
    "right_recommendation": true,
    "why": ["..."]
  }},
  "ui_component_reviews": [
    {{
      "component": "brief|questions|assumptions|blueprint|architecture|transcript",
      "score": 1-5,
      "status": "accurate|partially_accurate|misleading|missing",
      "what_is_working": ["..."],
      "issues": ["..."],
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
      "user_value": "...",
      "implementation_hint": "..."
    }}
  ]
}}

Judge this packet:
{packet_json}
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
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ],
        inferenceConfig={
            "maxTokens": max_tokens,
            "temperature": temperature,
        },
    )
    content = (((response.get("output") or {}).get("message") or {}).get("content") or [])
    text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
    return "\n".join(part for part in text_parts if part).strip()


def render_summary(packet: dict[str, Any], response_text: str | None) -> str:
    findings = packet["deterministic_findings"]
    lines = [
        "# Review Judge",
        "",
        f"- Scenario: `{packet['scenario']['name']}`",
        f"- Stage: `{packet['outcome']['stage']}`",
        f"- Confidence: `{packet['outcome']['confidence'] or 'unset'}`",
        f"- Blocking questions: `{packet['outcome']['blocking_question_count']}`",
        f"- Deterministic findings: `{len(findings)}`",
        "",
        "## Deterministic Findings",
        "",
    ]
    if not findings:
        lines.append("- No deterministic findings.")
    else:
        for finding in findings:
            lines.append(f"- `{finding['severity']}` [{finding['component']}] {finding['title']}: {finding['detail']}")
    if response_text is not None:
        lines.extend([
            "",
            "## Judge Response",
            "",
            "```json",
            response_text.strip() or "{}",
            "```",
        ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and optionally run an LLM-as-judge review from a seeded review scenario.")
    parser.add_argument("--scenario-id", default="", help="Scenario id from frontend/lib/review-scenarios.json. Defaults to the first scenario.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--profile", default="")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--bedrock-model-id", default="", help="Optional Bedrock model id. If omitted, only the judge packet and prompt are written.")
    parser.add_argument("--max-tokens", type=int, default=2200)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--connect-timeout", type=int, default=20)
    parser.add_argument("--read-timeout", type=int, default=180)
    parser.add_argument("--stdout-prompt", action="store_true")
    args = parser.parse_args()

    scenarios = json.loads(SCENARIO_FILE.read_text(encoding="utf-8"))
    scenario = next((item for item in scenarios if item.get("id") == args.scenario_id), scenarios[0] if scenarios else None)
    if scenario is None:
        raise SystemExit("No review scenarios found.")

    stamp = f"{now_stamp()}-{scenario.get('id', 'scenario')}"
    run_dir = Path(args.report_dir) / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    packet = build_packet(scenario)
    prompt = build_prompt(packet)

    packet_file = run_dir / "packet.json"
    prompt_file = run_dir / "prompt.txt"
    packet_file.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    prompt_file.write_text(prompt, encoding="utf-8")

    response_text: str | None = None
    if args.stdout_prompt:
        print(prompt)

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

    summary = render_summary(packet, response_text)
    summary_file = run_dir / "summary.md"
    summary_file.write_text(summary, encoding="utf-8")

    print(f"scenario_id={scenario.get('id')}")
    print(f"packet={packet_file}")
    print(f"prompt={prompt_file}")
    print(f"summary={summary_file}")
    if args.bedrock_model_id:
        print(f"response={run_dir / 'response.txt'}")


if __name__ == "__main__":
    main()
