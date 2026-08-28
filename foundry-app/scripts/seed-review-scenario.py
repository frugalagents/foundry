#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_FILE = ROOT / "frontend" / "lib" / "review-scenarios.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def put_customer_and_session(
    table,
    *,
    customer_id: str,
    customer_name: str,
    session_id: str,
    session_title: str,
    session_description: str,
    created_by: str,
) -> None:
    now = now_iso()
    table.put_item(
        Item={
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"CUSTOMER#{customer_id}",
            "customer_id": customer_id,
            "name": customer_name,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
            "demo_data": True,
        }
    )
    table.put_item(
        Item={
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"SESSION#{session_id}",
            "session_id": session_id,
            "customer_id": customer_id,
            "module_id": "coding-agent",
            "title": session_title,
            "description": session_description,
            "status": "active",
            "current_step": 0,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }
    )


def put_messages(table, *, customer_id: str, session_id: str, transcript: list[dict]) -> None:
    for index, message in enumerate(transcript, start=1):
        created_at = message.get("created_at") or now_iso()
        table.put_item(
            Item={
                "PK": f"CUSTOMER#{customer_id}",
                "SK": f"MSG#{session_id}#{created_at}#{index:04d}",
                "session_id": session_id,
                "customer_id": customer_id,
                "role": message.get("role", ""),
                "content": message.get("content", ""),
                "created_at": created_at,
            }
        )


def put_workspace(table, *, customer_id: str, session_id: str, workspace: dict) -> None:
    now = now_iso()
    table.put_item(
        Item={
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"WORKSPACE#{session_id}",
            "session_id": session_id,
            "customer_id": customer_id,
            "stage": workspace.get("stage", ""),
            "recommendation": workspace.get("recommendation", ""),
            "blueprint_markdown": workspace.get("blueprint_markdown", ""),
            "assumptions_json": json.dumps(workspace.get("assumptions", []) or []),
            "facts": workspace.get("facts", []) or [],
            "operating_model": workspace.get("operating_model", ""),
            "question_state_json": json.dumps(workspace.get("question_state", []) or []),
            "open_questions": workspace.get("open_questions", []) or [],
            "decisions": workspace.get("decisions", []) or [],
            "risks": workspace.get("risks", []) or [],
            "implementation_plan": workspace.get("implementation_plan", []) or [],
            "advisory_case_json": json.dumps(workspace.get("advisory_case", {}) or {}),
            "recommendation_state_json": json.dumps(workspace.get("recommendation_state", {}) or {}),
            "artifact_status_json": json.dumps(workspace.get("artifact_status", {}) or {}),
            "traversal_state_json": json.dumps(workspace.get("traversal_state", {}) or {}),
            "updated_at": now,
        }
    )


def put_architecture_case(table, *, customer_id: str, session_id: str, architecture_case: dict) -> None:
    if not architecture_case:
        return
    now = now_iso()
    table.put_item(
        Item={
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"CASE#{session_id}#{now}",
            "session_id": session_id,
            "customer_id": customer_id,
            "revision": int(architecture_case.get("revision") or 1),
            "case_id": architecture_case.get("case_id", ""),
            "okf_release_id": architecture_case.get("okf_release_id", ""),
            "architecture_case_json": json.dumps(architecture_case or {}),
            "created_at": now,
            "updated_at": now,
        }
    )


def put_canvas(
    table,
    *,
    customer_id: str,
    session_id: str,
    canvas: dict,
    architecture_artifact: dict | None,
    stage: str,
) -> None:
    now = now_iso()
    table.put_item(
        Item={
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"CANVAS#{session_id}#{now}",
            "session_id": session_id,
            "customer_id": customer_id,
            "nodes_json": json.dumps(canvas.get("nodes", []) or []),
            "edges_json": json.dumps(canvas.get("edges", []) or []),
            "stage": stage,
            "baseline_node_ids_json": json.dumps(canvas.get("baselineNodeIds", []) or []),
            "architecture_artifact_json": json.dumps(architecture_artifact or {}),
            "created_at": now,
            "updated_at": now,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a deterministic review scenario into DynamoDB so it can be opened in the normal app UI.")
    parser.add_argument("--scenario-id", default="", help="Scenario id from frontend/lib/review-scenarios.json. Defaults to the first scenario.")
    parser.add_argument("--profile", default="")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--table", default="foundry-app-main")
    parser.add_argument("--created-by", default="review-agent")
    parser.add_argument("--customer-name", default="")
    parser.add_argument("--session-title", default="")
    parser.add_argument("--session-description", default="")
    parser.add_argument("--app-url", default="")
    args = parser.parse_args()

    scenarios = json.loads(SCENARIO_FILE.read_text(encoding="utf-8"))
    scenario = next((item for item in scenarios if item.get("id") == args.scenario_id), scenarios[0] if scenarios else None)
    if scenario is None:
      raise SystemExit("No review scenarios found.")

    base_customer = scenario.get("customer") if isinstance(scenario.get("customer"), dict) else {}
    base_session = scenario.get("session") if isinstance(scenario.get("session"), dict) else {}
    workspace = scenario.get("workspace") if isinstance(scenario.get("workspace"), dict) else {}
    canvas = scenario.get("canvas") if isinstance(scenario.get("canvas"), dict) else {}
    architecture_artifact = scenario.get("architectureArtifact") if isinstance(scenario.get("architectureArtifact"), dict) else None

    customer_id = f"review-{scenario.get('id', 'scenario')}-{uuid.uuid4().hex[:8]}"
    session_id = f"review-sess-{uuid.uuid4().hex[:10]}"
    customer_name = args.customer_name or f"{base_customer.get('name', 'Review Scenario')} ({scenario.get('name', 'review')})"
    session_title = args.session_title or f"{base_session.get('title', 'Review Session')} [{scenario.get('name', 'review')}]"
    session_description = args.session_description or base_session.get("description") or scenario.get("summary") or "Seeded review scenario."

    session = boto3.Session(profile_name=args.profile or None, region_name=args.region)
    table = session.resource("dynamodb").Table(args.table)

    put_customer_and_session(
        table,
        customer_id=customer_id,
        customer_name=customer_name,
        session_id=session_id,
        session_title=session_title,
        session_description=session_description,
        created_by=args.created_by,
    )
    put_messages(
        table,
        customer_id=customer_id,
        session_id=session_id,
        transcript=scenario.get("transcript", []) or [],
    )
    put_workspace(
        table,
        customer_id=customer_id,
        session_id=session_id,
        workspace=workspace,
    )
    put_architecture_case(
        table,
        customer_id=customer_id,
        session_id=session_id,
        architecture_case=workspace.get("architecture_case", {}) if isinstance(workspace.get("architecture_case"), dict) else {},
    )
    put_canvas(
        table,
        customer_id=customer_id,
        session_id=session_id,
        canvas=canvas,
        architecture_artifact=architecture_artifact,
        stage=workspace.get("stage", ""),
    )

    print("Seeded review scenario created.")
    print(f"scenario_id={scenario.get('id')}")
    print(f"customer_id={customer_id}")
    print(f"session_id={session_id}")
    if args.app_url:
        print(f"app_url={args.app_url.rstrip('/')}")
        print(f"session_path=/sessions/{session_id}")
        print("Open the app, log in, and load the demo session from the sidebar.")


if __name__ == "__main__":
    main()
