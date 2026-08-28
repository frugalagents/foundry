#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config

DEFAULT_RUNTIME_ARN = (
    "arn:aws:bedrock-agentcore:us-east-1:616627284001:"
    "runtime/CodingAgentRuntime_CodingAgentRuntime-TOiVHpGwhu"
)

SPEAKER_RE = re.compile(r"^\*\*([^*:]+?):\*\*\s*(.*)$")
CUSTOMER_LABELS = ("customer", "rachel", "marcus")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_customer_turns(md_path: Path) -> list[str]:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    turns: list[str] = []
    in_blueprint = False
    buffer_speaker: str | None = None
    buffer_text: list[str] = []

    def flush() -> None:
        nonlocal buffer_speaker, buffer_text
        if buffer_speaker and buffer_speaker.lower().startswith(CUSTOMER_LABELS):
            text = " ".join(t.strip() for t in buffer_text if t.strip())
            if text:
                turns.append(text)
        buffer_speaker, buffer_text = None, []

    for line in lines:
        if line.startswith("## Platform Blueprint"):
            flush()
            in_blueprint = True
        if in_blueprint:
            continue
        match = SPEAKER_RE.match(line.strip())
        if match:
            flush()
            buffer_speaker = match.group(1).strip()
            buffer_text = [match.group(2)]
        elif buffer_speaker:
            buffer_text.append(line)

    flush()
    return turns


def extract_opening_message(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    match = re.search(r"## Customer Profile\n+(.*?)\n\n##", text, re.S)
    profile = match.group(1).strip() if match else ""
    return (
        "Here is our company profile — help us design a coding agent platform.\n\n"
        + profile
    )


def parse_sse(body: str) -> tuple[str, list[dict], dict | None, dict | None]:
    chat_text: list[str] = []
    architecture_events: list[dict] = []
    latest_workspace = None
    latest_architecture = None

    for line in body.split("\n"):
        if not line.startswith("data: "):
            continue
        raw = line[len("data: "):]
        try:
            outer = json.loads(raw)
        except json.JSONDecodeError:
            continue
        inner_lines = outer.split("\n") if isinstance(outer, str) else [None]
        for inner in inner_lines:
            if inner is None or not inner.startswith("data: "):
                continue
            payload = inner[len("data: "):]
            if payload == "[DONE]":
                continue
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "chat_stream":
                chat_text.append(event.get("data", {}).get("text", ""))
            elif event.get("type") == "architecture_update":
                data = event.get("data", {})
                architecture_events.append(data)
                latest_architecture = data
            elif event.get("type") == "workspace_update":
                latest_workspace = event.get("data", {})

    return "".join(chat_text), architecture_events, latest_workspace, latest_architecture


def invoke_turn(
    client,
    *,
    arn: str,
    runtime_session_id: str,
    customer_id: str,
    session_id: str,
    actor_id: str,
    message: str,
) -> tuple[str, list[dict], dict | None, dict | None]:
    payload = {
        "user_message": message,
        "session_id": session_id,
        "customer_id": customer_id,
        "module_id": "coding-agent",
        "actor_id": actor_id,
    }
    response = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=runtime_session_id,
        payload=json.dumps(payload).encode(),
        qualifier="DEFAULT",
    )
    body = response["response"].read().decode(errors="replace")
    return parse_sse(body)


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


def touch_session(table, *, customer_id: str, session_id: str) -> None:
    table.update_item(
        Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"SESSION#{session_id}"},
        UpdateExpression="SET updated_at = :updated_at",
        ExpressionAttributeValues={":updated_at": now_iso()},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a UI-visible demo session by replaying a simulation into the live runtime.")
    parser.add_argument("simulation_file", type=Path)
    parser.add_argument("--profile", default="")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--runtime-arn", default=DEFAULT_RUNTIME_ARN)
    parser.add_argument("--table", default="foundry-app-main")
    parser.add_argument("--customer-name", default="")
    parser.add_argument("--session-title", default="")
    parser.add_argument("--session-description", default="Seeded from a simulation replay for UI review.")
    parser.add_argument("--created-by", default="review-agent")
    parser.add_argument("--actor-id", default="review-agent")
    parser.add_argument("--app-url", default="")
    parser.add_argument("--max-turns", type=int, default=None)
    parser.add_argument("--connect-timeout", type=int, default=20)
    parser.add_argument("--read-timeout", type=int, default=300)
    args = parser.parse_args()

    simulation_file = args.simulation_file
    if not simulation_file.exists():
        raise SystemExit(f"Simulation file not found: {simulation_file}")

    slug = simulation_file.stem
    customer_id = f"demo-{uuid.uuid4().hex[:10]}"
    session_id = f"demo-sess-{uuid.uuid4().hex[:10]}"
    runtime_session_id = f"seed-{slug}-{uuid.uuid4().hex[:20]}".ljust(33, "0")
    customer_name = args.customer_name or f"Demo {slug.replace('-', ' ').title()}"
    session_title = args.session_title or f"Simulation: {slug.replace('-', ' ')}"

    turns = extract_customer_turns(simulation_file)
    if args.max_turns:
      turns = turns[:args.max_turns]
    messages = [extract_opening_message(simulation_file), *turns]

    session = boto3.Session(profile_name=args.profile or None, region_name=args.region)
    dynamodb = session.resource("dynamodb")
    table = dynamodb.Table(args.table)
    put_customer_and_session(
        table,
        customer_id=customer_id,
        customer_name=customer_name,
        session_id=session_id,
        session_title=session_title,
        session_description=args.session_description,
        created_by=args.created_by,
    )

    print(f"customer_id={customer_id}", flush=True)
    print(f"session_id={session_id}", flush=True)
    print(f"simulation_file={simulation_file}", flush=True)

    client = session.client(
        "bedrock-agentcore",
        config=Config(
            connect_timeout=args.connect_timeout,
            read_timeout=args.read_timeout,
            retries={"max_attempts": 3, "mode": "adaptive"},
        ),
    )

    last_workspace = None
    last_architecture = None
    for index, message in enumerate(messages, start=1):
        chat_text, architecture_events, workspace, architecture = invoke_turn(
            client,
            arn=args.runtime_arn,
            runtime_session_id=runtime_session_id,
            customer_id=customer_id,
            session_id=session_id,
            actor_id=args.actor_id,
            message=message,
        )
        if workspace:
            last_workspace = workspace
        if architecture:
            last_architecture = architecture
        try:
            touch_session(table, customer_id=customer_id, session_id=session_id)
        except Exception as exc:
            print(f"warning=failed_to_touch_session:{exc}", flush=True)
        print(f"turn {index}/{len(messages)} complete", flush=True)
        if chat_text.strip():
            compact = " ".join(chat_text.split())
            print(f"  agent: {compact[:220]}{'...' if len(compact) > 220 else ''}", flush=True)
        if architecture_events:
            latest = architecture_events[-1]
            print(
                "  architecture:"
                f" stage={latest.get('stage', '')}"
                f" nodes={len(latest.get('nodes', []))}"
                f" edges={len(latest.get('edges', []))}",
                flush=True,
            )

    print("", flush=True)
    print("Seeded review session created.", flush=True)
    print(f"customer_id={customer_id}", flush=True)
    print(f"session_id={session_id}", flush=True)
    print(f"simulation_file={simulation_file}", flush=True)
    if isinstance(last_workspace, dict):
        print(f"workspace_stage={last_workspace.get('stage', '')}", flush=True)
        print(f"open_questions={len(last_workspace.get('open_questions', []) or [])}", flush=True)
    if isinstance(last_architecture, dict):
        print(f"architecture_nodes={len(last_architecture.get('nodes', []) or [])}", flush=True)
        print(f"architecture_edges={len(last_architecture.get('edges', []) or [])}", flush=True)
    if args.app_url:
        print(f"app_url={args.app_url.rstrip('/')}", flush=True)
        print(f"session_path=/sessions/{session_id}", flush=True)
        print("Open the app, log in, and load the demo session from the sidebar.", flush=True)


if __name__ == "__main__":
    main()
