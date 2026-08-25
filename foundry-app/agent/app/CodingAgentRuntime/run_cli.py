"""Interactive CLI for the deployed CodingAgentRuntime AgentCore runtime.

This talks to the live agent runtime directly, bypassing the web UI entirely.
It is useful for testing the agent's reasoning, traversal, and workspace
updates from a terminal.

Usage:
    python3 run_cli.py
    python3 run_cli.py --arn <runtime-arn>
    python3 run_cli.py --customer-id demo --session-id demo-1
"""
from __future__ import annotations

import argparse
import json
import uuid

import boto3

DEFAULT_ARN = (
    "arn:aws:bedrock-agentcore:us-east-1:616627284001:"
    "runtime/CodingAgentRuntime_CodingAgentRuntime-TOiVHpGwhu"
)


def _parse_sse(body: str) -> dict:
    chat_parts: list[str] = []
    workspace = None
    architecture = None
    events: list[dict] = []

    for line in body.splitlines():
        if not line.startswith("data: "):
            continue
        raw = line[len("data: ") :].strip()
        if not raw or raw == "[DONE]":
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        nested_lines = payload.splitlines() if isinstance(payload, str) else [None]
        if nested_lines[0] is not None:
            for nested in nested_lines:
                if not nested.startswith("data: "):
                    continue
                inner = nested[len("data: ") :].strip()
                if not inner or inner == "[DONE]":
                    continue
                try:
                    event = json.loads(inner)
                except json.JSONDecodeError:
                    continue
                events.append(event)
        elif isinstance(payload, dict):
            events.append(payload)

    for event in events:
        event_type = event.get("type")
        data = event.get("data", {})
        if event_type == "chat_stream":
            text = data.get("text", "")
            if isinstance(text, str):
                chat_parts.append(text)
        elif event_type == "workspace_update":
            workspace = data
        elif event_type == "architecture_update":
            architecture = data

    return {
        "chat_text": "".join(chat_parts).strip(),
        "workspace": workspace,
        "architecture": architecture,
    }


def _invoke_turn(
    client,
    *,
    arn: str,
    runtime_session_id: str,
    customer_id: str,
    session_id: str,
    actor_id: str,
    user_message: str,
) -> dict:
    payload = {
        "user_message": user_message,
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
    return _parse_sse(body)


def _print_workspace_summary(workspace: dict | None) -> None:
    if not isinstance(workspace, dict):
        return
    stage = workspace.get("stage") or "n/a"
    questions = workspace.get("open_questions") or []
    decisions = workspace.get("decisions") or []
    risks = workspace.get("risks") or []
    recommendation = (workspace.get("recommendation") or "").strip()

    print(f"\n[workspace] stage={stage}")
    if recommendation:
        compact = " ".join(recommendation.split())
        print(f"[workspace] recommendation={compact[:220]}{'...' if len(compact) > 220 else ''}")
    if questions:
        print(f"[workspace] open_questions={len(questions)}")
        for idx, question in enumerate(questions[:3], start=1):
            print(f"  {idx}. {' '.join(str(question).split())}")
    if decisions:
        print(f"[workspace] decisions={len(decisions)}")
    if risks:
        print(f"[workspace] risks={len(risks)}")


def _print_architecture_summary(architecture: dict | None) -> None:
    if not isinstance(architecture, dict):
        return
    stage = architecture.get("stage") or "n/a"
    nodes = architecture.get("nodes") or []
    edges = architecture.get("edges") or []
    baseline = architecture.get("baseline_node_ids") or []
    print(
        f"[architecture] stage={stage} nodes={len(nodes)} "
        f"edges={len(edges)} baseline_nodes={len(baseline)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arn", default=DEFAULT_ARN)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--customer-id", default="")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--actor-id", default="cli-user")
    args = parser.parse_args()

    client = boto3.client("bedrock-agentcore", region_name=args.region)
    runtime_session_id = f"cli-{uuid.uuid4().hex[:29]}".ljust(33, "0")
    customer_id = args.customer_id
    session_id = args.session_id

    print("CodingAgentRuntime CLI")
    print(f"runtime_arn={args.arn}")
    print(f"runtime_session_id={runtime_session_id}")
    print(f"persisted_customer_id={customer_id or '(disabled)'}")
    print(f"persisted_session_id={session_id or '(disabled)'}")
    print("Type /exit to quit.\n")

    while True:
        try:
            user_message = input("you> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break

        if not user_message:
            continue
        if user_message.lower() in {"/exit", "exit", "quit"}:
            break

        result = _invoke_turn(
            client,
            arn=args.arn,
            runtime_session_id=runtime_session_id,
            customer_id=customer_id,
            session_id=session_id,
            actor_id=args.actor_id,
            user_message=user_message,
        )

        print("\nagent>")
        print(result["chat_text"] or "(no chat text)")
        _print_workspace_summary(result.get("workspace"))
        _print_architecture_summary(result.get("architecture"))
        print()


if __name__ == "__main__":
    main()
