"""CLI runner: replays a canned simulation transcript's customer lines against
the live CodingAgentRuntime AgentCore runtime and prints the agent's real
responses turn-by-turn, for comparison against the documented reference
transcript in simulations/*.md.

Usage:
    python3 run_simulation.py <simulation-file.md> [--arn <runtime-arn>]
"""
from __future__ import annotations
import argparse
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config

DEFAULT_ARN = (
    "arn:aws:bedrock-agentcore:us-east-1:616627284001:"
    "runtime/CodingAgentRuntime_CodingAgentRuntime-TOiVHpGwhu"
)

# Matches "**Speaker Name (Role):** text" or "**Speaker:** text" at line start.
SPEAKER_RE = re.compile(r"^\*\*([^*:]+?):\*\*\s*(.*)$")

# Speaker-label prefixes that represent the human customer side of the
# conversation (as opposed to "Advisor" or blueprint section headers).
CUSTOMER_LABELS = ("customer", "rachel", "marcus")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _simulation_title(slug: str) -> str:
    return f"Simulation: {slug.replace('-', ' ')}"


def _bootstrap_inventory_rows(
    table,
    *,
    customer_id: str,
    session_id: str,
    actor_id: str,
    slug: str,
    simulation_file: Path,
) -> None:
    now = _now()
    customer_key = {
        "PK": f"CUSTOMER#{customer_id}",
        "SK": f"CUSTOMER#{customer_id}",
    }
    if not table.get_item(Key=customer_key).get("Item"):
        table.put_item(
            Item={
                **customer_key,
                "customer_id": customer_id,
                "name": _simulation_title(slug),
                "created_by": actor_id,
                "created_at": now,
                "updated_at": now,
                "demo_data": True,
                "simulation_slug": slug,
            }
        )

    table.put_item(
        Item={
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"SESSION#{session_id}",
            "session_id": session_id,
            "customer_id": customer_id,
            "module_id": "coding-agent",
            "title": _simulation_title(slug),
            "description": f"Auto-generated from {simulation_file.name}",
            "status": "active",
            "current_step": 0,
            "created_by": actor_id,
            "created_at": now,
            "updated_at": now,
            "demo_data": True,
            "simulation_slug": slug,
        }
    )


def _update_session_row(
    table,
    *,
    customer_id: str,
    session_id: str,
    current_step: int,
    status: str,
) -> None:
    table.update_item(
        Key={
            "PK": f"CUSTOMER#{customer_id}",
            "SK": f"SESSION#{session_id}",
        },
        UpdateExpression="SET current_step = :current_step, #status = :status, updated_at = :updated_at",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":current_step": current_step,
            ":status": status,
            ":updated_at": _now(),
        },
    )


def extract_customer_turns(md_path: Path) -> list[str]:
    """Pull sequential customer utterances out of the Advisor Discovery /
    Discovery Conversation section, stopping once the transcript moves into
    the Platform Blueprint section."""
    lines = md_path.read_text(encoding="utf-8").splitlines()
    turns: list[str] = []
    in_blueprint = False
    buffer_speaker: str | None = None
    buffer_text: list[str] = []

    def flush():
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
        m = SPEAKER_RE.match(line.strip())
        if m:
            flush()
            buffer_speaker = m.group(1).strip()
            buffer_text = [m.group(2)]
        elif buffer_speaker:
            buffer_text.append(line)
    flush()
    return turns


def extract_opening_message(md_path: Path) -> str:
    """Build a synthetic opening user message from the Customer Profile table."""
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r"## Customer Profile\n+(.*?)\n\n##", text, re.S)
    profile = m.group(1).strip() if m else ""
    return (
        "Here is our company profile — help us design a coding agent platform.\n\n"
        + profile
    )


def parse_sse(body: str) -> tuple[str, list[dict]]:
    """Extract concatenated chat_stream text and any architecture_update events."""
    chat_text = []
    arch_events = []
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
            if inner is None:
                continue
            if not inner.startswith("data: "):
                continue
            payload = inner[len("data: "):]
            if payload == "[DONE]":
                continue
            try:
                ev = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "chat_stream":
                chat_text.append(ev["data"].get("text", ""))
            elif ev.get("type") == "architecture_update":
                arch_events.append(ev["data"])
    return "".join(chat_text), arch_events


def run_turn(client, arn: str, runtime_session_id: str, customer_id: str,
             session_id: str, actor_id: str, message: str) -> tuple[str, list[dict]]:
    payload = {
        "user_message": message,
        "session_id": session_id,
        "customer_id": customer_id,
        "module_id": "coding-agent",
        "actor_id": actor_id,
    }
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=runtime_session_id,
        payload=json.dumps(payload).encode(),
        qualifier="DEFAULT",
    )
    body = resp["response"].read().decode(errors="replace")
    return parse_sse(body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("simulation_file", type=Path)
    parser.add_argument("--arn", default=DEFAULT_ARN)
    parser.add_argument("--max-turns", type=int, default=None)
    parser.add_argument("--profile", default="")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--connect-timeout", type=int, default=20)
    parser.add_argument("--read-timeout", type=int, default=300)
    parser.add_argument("--table-name", default=os.environ.get("DYNAMODB_TABLE", "foundry-app-main"))
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args()

    turns = extract_customer_turns(args.simulation_file)
    if args.max_turns:
        turns = turns[: args.max_turns]

    opening = extract_opening_message(args.simulation_file)
    messages = [opening] + turns

    slug = args.simulation_file.stem
    run_id = uuid.uuid4().hex[:10]
    runtime_session_id = f"sim-{slug}-{run_id}".ljust(33, "0")
    customer_id = f"sim-{slug}-cust"
    session_id = f"sim-{slug}-sess-{run_id}"
    actor_id = f"sim-{slug}-user"

    session = boto3.Session(profile_name=args.profile or None, region_name=args.region)
    client = session.client(
        "bedrock-agentcore",
        config=Config(
            connect_timeout=args.connect_timeout,
            read_timeout=args.read_timeout,
            retries={"max_attempts": 3, "mode": "adaptive"},
        ),
    )
    table = None
    if not args.no_persist:
        table = session.resource("dynamodb", region_name=args.region).Table(args.table_name)
        _bootstrap_inventory_rows(
            table,
            customer_id=customer_id,
            session_id=session_id,
            actor_id=actor_id,
            slug=slug,
            simulation_file=args.simulation_file,
        )

    print(f"=== Simulation: {slug} ===")
    print(f"session_id={session_id}  actor_id={actor_id}")
    print(f"turns to replay: {len(messages)}\n")

    total_arch_updates = 0
    for i, msg in enumerate(messages):
        label = "OPENING (synthetic, from profile)" if i == 0 else f"CUSTOMER TURN {i}"
        print(f"\n{'=' * 70}\n[{label}]\n{'-' * 70}")
        print(msg[:600] + ("..." if len(msg) > 600 else ""))

        text, arch_events = run_turn(
            client, args.arn, runtime_session_id, customer_id, session_id, actor_id, msg
        )
        total_arch_updates += len(arch_events)
        if table is not None:
            _update_session_row(
                table,
                customer_id=customer_id,
                session_id=session_id,
                current_step=i + 1,
                status="active",
            )

        print(f"\n[AGENT RESPONSE]\n{'-' * 70}")
        print(text.strip())
        for ev in arch_events:
            print(f"\n  >> architecture_update: stage={ev.get('stage')!r} "
                  f"nodes={len(ev.get('nodes', []))} edges={len(ev.get('edges', []))}")

    if table is not None:
        _update_session_row(
            table,
            customer_id=customer_id,
            session_id=session_id,
            current_step=len(messages),
            status="completed",
        )

    print(f"\n{'=' * 70}")
    print(f"Simulation complete. {len(messages)} turns, "
          f"{total_arch_updates} architecture_update event(s) emitted.")
    print(f"customer_id={customer_id}  session_id={session_id}")


if __name__ == "__main__":
    main()
