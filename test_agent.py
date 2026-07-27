#!/usr/bin/env python3
"""
AgentCore pipeline end-to-end test for Platform Advisor.
Tests the full 8-step advisory pipeline through AWS BedrockAgentCore.

Usage:
  python test_agent.py                      # run with default AWS profile
  python test_agent.py --profile myprofile  # use a different AWS profile
  python test_agent.py --verbose            # show all raw events
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import http.client
from collections import Counter

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

# ── Config ────────────────────────────────────────────────────────────────────

AGENTCORE_ARN = (
    "arn:aws:bedrock-agentcore:us-east-1:616627284001:runtime/"
    "PlatformAdvisorAgent_PlatformAdvisorAgent-3U71dVBprI"
)
REGION = "us-east-1"
SERVICE = "bedrock-agentcore"
AGENTCORE_HOST = f"bedrock-agentcore.{REGION}.amazonaws.com"
API_BASE = "https://5kr7vlzkfj.execute-api.us-east-1.amazonaws.com/api/v1"

# Dev token — matches backend DevMode=true format
DEV_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiJ0ZXN0LXVzZXIiLCJlbWFpbCI6InRlc3RAcGxhdGZvcm0tYWR2aXNvci5kZW1vIiwiY29nbml0bzpncm91cHMiOlsiYWRtaW4iXX0"
    ".test-signature"
)

INTAKE_ANSWERS = {
    "autonomy_model":   "hitl",
    "lob_count":        "4-10",
    "governance_model": "centralized",
    "cloud_posture":    "single_aws",
    "stack_preference": "managed",
    "auth_identity":    "oauth_oidc",
    "data_gravity":     "single_region",
    "observability":    "existing_stack",
    "intake_maturity":  "emerging",
    "agent_purpose":    "internal",
    "team_expertise":   "medium",
    "cost_sensitivity": "secondary",
}

VERBOSE = False

# ── Helpers ───────────────────────────────────────────────────────────────────

def ok(label: str, value: str = "") -> None:
    suffix = f"  \033[2m({value})\033[0m" if value else ""
    print(f"  \033[32m✓\033[0m  {label}{suffix}")


def fail(label: str, err: str) -> None:
    print(f"  \033[31m✗\033[0m  {label}: {err}")


def info(msg: str) -> None:
    print(f"    \033[2m{msg}\033[0m")


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


def build_runtime_session_id(customer_id: str, session_id: str) -> str:
    raw = f"{customer_id}-{session_id}"
    return raw if len(raw) >= 33 else raw.ljust(33, "0")


# ── REST helpers (for CRUD setup/teardown) ────────────────────────────────────

def rest_req(method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEV_TOKEN}",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} {method} {url}: {body_text}") from e


# ── AgentCore SigV4 invocation ────────────────────────────────────────────────

def _signed_headers(
    url: str, body: bytes, runtime_session_id: str, profile: str
) -> dict:
    session = boto3.Session(profile_name=profile)
    creds = session.get_credentials().get_frozen_credentials()

    aws_req = AWSRequest(
        method="POST",
        url=url,
        data=body,
        headers={
            "content-type": "application/json",
            "accept":        "text/event-stream",
            "x-amzn-bedrock-agentcore-runtime-session-id": runtime_session_id,
        },
    )
    SigV4Auth(creds, SERVICE, REGION).add_auth(aws_req)
    return dict(aws_req.headers)


def _parse_sse_chunk(raw: str):
    """
    Parse one SSE data value.
    AgentCore may double-encode: outer JSON is a string containing inner SSE lines.
    Yields dicts for each agent event found.
    """
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return

    if isinstance(parsed, str):
        # Double-encoded: inner value is SSE text
        for line in parsed.split("\n"):
            if line.startswith("data: "):
                try:
                    yield json.loads(line[6:])
                except (json.JSONDecodeError, ValueError):
                    pass
    elif isinstance(parsed, dict):
        yield parsed


def stream_invocation(payload: dict, runtime_session_id: str, profile: str):
    """
    POST to AgentCore, return a generator of parsed event dicts.
    Uses http.client for raw streaming (no buffering).
    """
    encoded_arn = urllib.parse.quote(AGENTCORE_ARN, safe="")
    path = f"/runtimes/{encoded_arn}/invocations"
    body = json.dumps(payload).encode()
    headers = _signed_headers(f"https://{AGENTCORE_HOST}{path}", body, runtime_session_id, profile)

    conn = http.client.HTTPSConnection(AGENTCORE_HOST, timeout=180)
    try:
        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()

        if resp.status != 200:
            error_body = resp.read().decode()
            raise RuntimeError(f"AgentCore HTTP {resp.status}: {error_body}")

        buf = ""
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            buf += chunk.decode("utf-8", errors="replace")

            # Process complete lines
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.rstrip("\r")
                if line.startswith("data: "):
                    raw_data = line[6:]
                    for event in _parse_sse_chunk(raw_data):
                        yield event
    finally:
        conn.close()


# ── Test runner ───────────────────────────────────────────────────────────────

def run_agent_test(profile: str) -> bool:
    customer_id: str | None = None
    session_id:  str | None = None

    # ── Setup ──────────────────────────────────────────────────────────────
    section("0. Setup — create test customer + session")

    try:
        c = rest_req("POST", f"{API_BASE}/customers",
                     {"name": "E2E-Agent-Test", "industry": "Technology"})
        customer_id = c["customer_id"]
        ok("Created customer", customer_id)
    except Exception as e:
        fail("Create customer", str(e))
        return False

    try:
        s = rest_req("POST", f"{API_BASE}/customers/{customer_id}/sessions",
                     {"title": "Agent Pipeline E2E"})
        session_id = s["session_id"]
        ok("Created session", session_id)
    except Exception as e:
        fail("Create session", str(e))
        _cleanup(customer_id, None)
        return False

    runtime_session_id = build_runtime_session_id(customer_id, session_id)
    info(f"Runtime session ID: {runtime_session_id}")

    # ── Phase 1: start (steps 1-2) ─────────────────────────────────────────
    section("1. Phase 1 — intake + scoring (steps 1-2)")

    start_payload = {
        "action":       "start",
        "session_id":   session_id,
        "customer_id":  customer_id,
        "answers":      INTAKE_ANSWERS,
        "industry":     "Technology",
        "pain_points":  [],
        "user_message": json.dumps(INTAKE_ANSWERS),
    }

    phase1_events: list[str] = []
    got_confirmation = False
    phase1_error: str | None = None

    t0 = time.time()
    try:
        for event in stream_invocation(start_payload, runtime_session_id, profile):
            # All AgentCore events are wrapped: {"type": "...", "data": {...}, "ts": ...}
            etype = event.get("type", "unknown")
            d = event.get("data") or {}
            phase1_events.append(etype)

            if VERBOSE:
                info(f"[event] {json.dumps(event)[:120]}")

            if etype == "step_transition":
                step = d.get("to", d.get("to_step", "?"))
                info(f"→ step_transition to step {step}")
            elif etype == "chat_message":
                content = str(d.get("content", ""))[:100]
                info(f"chat: {content}")
            elif etype in ("panel_update", "panel_complete"):
                step = d.get("step", "?")
                info(f"panel_{etype.split('_')[1]} step={step}")
            elif etype == "confirmation_request":
                got_confirmation = True
                opts = d.get("options", [])
                ok(f"confirmation_request received  options={opts}")
                break  # done with phase 1
            elif etype == "error":
                phase1_error = d.get("message", event.get("message", "unknown error"))
                break
    except Exception as e:
        fail("Phase 1 stream", str(e))
        _cleanup(customer_id, session_id)
        return False

    elapsed = round(time.time() - t0, 1)
    info(f"Phase 1 completed in {elapsed}s  ({len(phase1_events)} events)")

    if phase1_error:
        fail("Phase 1 pipeline error", phase1_error)
        _cleanup(customer_id, session_id)
        return False

    if not got_confirmation:
        fail("confirmation_request", "not received — pipeline may have failed or skipped step 2")
        _cleanup(customer_id, session_id)
        return False

    ok("Phase 1 complete")

    # ── Phase 2: confirm (steps 3-8) ───────────────────────────────────────
    section("2. Phase 2 — confirm + component → blueprint (steps 3-8)")

    confirm_payload = {
        "action":      "confirm",
        "session_id":  session_id,
        "customer_id": customer_id,
        "choice":      "Confirm",
    }

    phase2_events: list[str] = []
    got_blueprint = False
    got_complete  = False
    blueprint_data: dict = {}
    phase2_error: str | None = None

    t0 = time.time()
    try:
        for event in stream_invocation(confirm_payload, runtime_session_id, profile):
            etype = event.get("type", "unknown")
            d = event.get("data") or {}
            phase2_events.append(etype)

            if VERBOSE:
                info(f"[event] {json.dumps(event)[:120]}")

            if etype == "step_transition":
                step = d.get("to", d.get("to_step", "?"))
                info(f"→ step_transition to step {step}")
            elif etype == "chat_message":
                content = str(d.get("content", ""))[:100]
                info(f"chat: {content}")
            elif etype == "panel_complete":
                step = d.get("step", "?")
                info(f"panel_complete step={step}")
                ok(f"Step {step} complete")
                try:
                    if int(step) == 8:
                        got_blueprint = True
                        blueprint_data = d
                except (ValueError, TypeError):
                    pass
            elif etype == "panel_update":
                step = d.get("step", "?")
                info(f"panel_update step={step}")
            elif etype == "complete":
                got_complete = True
                ok("complete event received")
            elif etype == "error":
                phase2_error = d.get("message", event.get("message", "unknown error"))
                fail("Pipeline error in phase 2", phase2_error)
    except Exception as e:
        fail("Phase 2 stream", str(e))

    elapsed = round(time.time() - t0, 1)
    info(f"Phase 2 completed in {elapsed}s  ({len(phase2_events)} events)")

    if phase2_error:
        fail("Phase 2 pipeline error", phase2_error)

    if got_blueprint:
        ok("Blueprint generated (step 8 panel_complete)")
        if blueprint_data:
            pattern = blueprint_data.get("pattern_id") or blueprint_data.get("pattern", "")
            if pattern:
                info(f"Pattern selected: {pattern}")
    else:
        fail("Blueprint", "step 8 panel_complete not received")

    if got_complete:
        ok("Pipeline reached 'complete' state")

    # ── Event summary ──────────────────────────────────────────────────────
    section("3. Event summary")
    all_events = phase1_events + phase2_events
    counts = Counter(all_events)
    for etype, cnt in sorted(counts.items()):
        info(f"{etype}: {cnt}")
    info(f"Total events: {len(all_events)}")

    # ── Cleanup ────────────────────────────────────────────────────────────
    section("4. Cleanup")
    _cleanup(customer_id, session_id)

    success = got_confirmation and got_blueprint
    return success


def _cleanup(customer_id: str | None, session_id: str | None) -> None:
    if customer_id and session_id:
        try:
            rest_req("DELETE", f"{API_BASE}/customers/{customer_id}/sessions/{session_id}")
            ok("Deleted session")
        except Exception:
            pass
    if customer_id:
        try:
            rest_req("DELETE", f"{API_BASE}/customers/{customer_id}")
            ok("Deleted customer")
        except Exception:
            pass


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Platform Advisor AgentCore E2E test")
    parser.add_argument("--profile", default="platform-advisor",
                        help="AWS profile to use for SigV4 credentials (default: platform-advisor)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print every raw event")
    args = parser.parse_args()

    VERBOSE = args.verbose

    print(f"\n\033[1mPlatform Advisor — AgentCore Pipeline E2E Test\033[0m")
    print(f"Profile : {args.profile}")
    print(f"ARN     : {AGENTCORE_ARN}")
    print(f"API     : {API_BASE}")

    success = run_agent_test(args.profile)

    color = "\033[32m" if success else "\033[31m"
    print(f"\n{color}{'─' * 44}")
    print(f"  {'ALL CHECKS PASSED — pipeline healthy' if success else 'CHECKS FAILED — see errors above'}")
    print(f"{'─' * 44}\033[0m\n")

    sys.exit(0 if success else 1)
