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
import re
import uuid
from pathlib import Path

import boto3

DEFAULT_ARN = (
    "arn:aws:bedrock-agentcore:us-east-1:616627284001:"
    "runtime/CodingAgentRuntime_CodingAgentRuntime-TOiVHpGwhu"
)

# Matches "**Speaker Name (Role):** text" or "**Speaker:** text" at line start.
SPEAKER_RE = re.compile(r"^\*\*([^*:]+?):\*\*\s*(.*)$")

# Speaker-label prefixes that represent the human customer side of the
# conversation (as opposed to "Advisor" or blueprint section headers).
CUSTOMER_LABELS = ("customer", "rachel", "marcus")


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

    client = boto3.client("bedrock-agentcore", region_name="us-east-1")

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

        print(f"\n[AGENT RESPONSE]\n{'-' * 70}")
        print(text.strip())
        for ev in arch_events:
            print(f"\n  >> architecture_update: stage={ev.get('stage')!r} "
                  f"nodes={len(ev.get('nodes', []))} edges={len(ev.get('edges', []))}")

    print(f"\n{'=' * 70}")
    print(f"Simulation complete. {len(messages)} turns, "
          f"{total_arch_updates} architecture_update event(s) emitted.")
    print(f"customer_id={customer_id}  session_id={session_id}")


if __name__ == "__main__":
    main()
