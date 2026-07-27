#!/usr/bin/env python3
"""
End-to-end API test for Platform Advisor.
Cleans up any prior test data, then runs through the full flow.

Usage:
  python test.py                    # run against deployed API
  python test.py --local            # run against localhost:8080
  python test.py --cleanup-only     # delete all test data and exit
"""
import argparse
import json
import sys
import urllib.request
import urllib.error

PROD_BASE = "https://5kr7vlzkfj.execute-api.us-east-1.amazonaws.com/api/v1"
LOCAL_BASE = "http://localhost:8080/api/v1"

# Dev token — backend DevMode=true accepts any well-formed JWT payload
DEV_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiJ0ZXN0LXVzZXIiLCJlbWFpbCI6InRlc3RAcGxhdGZvcm0tYWR2aXNvci5kZW1vIiwiY29nbml0bzpncm91cHMiOlsiYWRtaW4iXX0"
    ".test-signature"
)

INTAKE_ANSWERS = {
    "autonomy_model": "hitl",
    "lob_count": "4-10",
    "governance_model": "centralized",
    "cloud_posture": "single_aws",
    "stack_preference": "managed",
    "auth_identity": "oauth_oidc",
    "data_gravity": "single_region",
    "observability": "existing_stack",
    "intake_maturity": "emerging",
    "agent_purpose": "internal",
    "team_expertise": "medium",
    "cost_sensitivity": "secondary",
}


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def req(method: str, url: str, body: dict | None = None) -> dict:
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


def ok(label: str, value: str = "") -> None:
    suffix = f"  \033[2m({value})\033[0m" if value else ""
    print(f"  \033[32m✓\033[0m  {label}{suffix}")


def fail(label: str, err: str) -> None:
    print(f"  \033[31m✗\033[0m  {label}: {err}")


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


# ── Cleanup ───────────────────────────────────────────────────────────────────

def cleanup(base: str) -> None:
    section("Cleanup — removing E2E test data")
    customers = req("GET", f"{base}/customers")
    deleted = 0
    for c in customers:
        if c["name"].startswith("E2E-"):
            try:
                sessions = req("GET", f"{base}/customers/{c['customer_id']}/sessions")
                for s in sessions:
                    req("DELETE", f"{base}/customers/{c['customer_id']}/sessions/{s['session_id']}")
                req("DELETE", f"{base}/customers/{c['customer_id']}")
                ok(f"Deleted {c['name']}", c["customer_id"])
                deleted += 1
            except Exception as e:
                fail(f"Delete {c['name']}", str(e))
    if deleted == 0:
        print("  No E2E test data found.")


# ── Test runner ───────────────────────────────────────────────────────────────

def run(base: str) -> bool:
    passed = 0
    failed = 0

    def check(label: str, fn):
        nonlocal passed, failed
        try:
            result = fn()
            ok(label, result or "")
            passed += 1
            return True
        except Exception as e:
            fail(label, str(e))
            failed += 1
            return False

    # ── 1. Health ──────────────────────────────────────────────────────────
    section("1. Health check")
    health_url = base.replace("/api/v1", "/health")
    check("GET /health", lambda: req("GET", health_url)["version"])

    # ── 2. Customer CRUD ───────────────────────────────────────────────────
    section("2. Customer CRUD")
    customer_id = None

    def create_customer():
        nonlocal customer_id
        c = req("POST", f"{base}/customers", {"name": "E2E-Test Corp", "industry": "Technology"})
        assert c["customer_id"].startswith("cust_"), f"Bad ID: {c}"
        customer_id = c["customer_id"]
        return customer_id

    if not check("POST /customers", create_customer):
        print("\n\033[31mCannot continue without a customer.\033[0m\n")
        return False

    check("GET /customers/{id}", lambda: req("GET", f"{base}/customers/{customer_id}")["name"])
    check("GET /customers (list)", lambda: f"{len(req('GET', f'{base}/customers'))} total")

    # ── 3. Session CRUD ────────────────────────────────────────────────────
    section("3. Session CRUD")
    session_id = None

    def create_session():
        nonlocal session_id
        s = req("POST", f"{base}/customers/{customer_id}/sessions",
                {"title": "E2E Blueprint Session"})
        assert s["session_id"].startswith("sess_"), f"Bad ID: {s}"
        session_id = s["session_id"]
        return session_id

    if not check("POST /sessions", create_session):
        print("\n\033[31mCannot continue without a session.\033[0m\n")
        return False

    check("GET /sessions/{id}", lambda: req(
        "GET", f"{base}/customers/{customer_id}/sessions/{session_id}")["status"])
    check("GET /sessions (list)", lambda: f"{len(req('GET', f'{base}/customers/{customer_id}/sessions'))} total")

    # ── 4. Intake answers ──────────────────────────────────────────────────
    section("4. Intake answers")
    check("PUT /inputs (12 answers)", lambda: req(
        "PUT", f"{base}/customers/{customer_id}/sessions/{session_id}/inputs",
        {"answers": INTAKE_ANSWERS}) or "saved")

    # ── 5. Panel state ─────────────────────────────────────────────────────
    section("5. Panel state")
    check("GET /panels", lambda: f"{len(req('GET', f'{base}/customers/{customer_id}/sessions/{session_id}/panels').get('panels', []))} panels")

    # ── 6. Session update ──────────────────────────────────────────────────
    section("6. Session update")
    check("PATCH /sessions/{id} status→complete", lambda: req(
        "PATCH", f"{base}/customers/{customer_id}/sessions/{session_id}",
        {"status": "complete"})["status"])

    # ── 7. Admin metrics ───────────────────────────────────────────────────
    section("7. Admin metrics")
    check("GET /admin/metrics", lambda: (
        lambda m: f"{m['total_customers']} customers, {m['total_sessions']} sessions"
    )(req("GET", f"{base}/admin/metrics")))

    # ── 8. Cleanup ─────────────────────────────────────────────────────────
    section("8. Cleanup")
    check("DELETE /sessions/{id}", lambda: req(
        "DELETE", f"{base}/customers/{customer_id}/sessions/{session_id}") or "deleted")
    check("DELETE /customers/{id}", lambda: req(
        "DELETE", f"{base}/customers/{customer_id}") or "deleted")

    def verify_deleted():
        try:
            req("GET", f"{base}/customers/{customer_id}")
            raise AssertionError("Customer still exists after delete")
        except RuntimeError as e:
            if "404" in str(e):
                return "confirmed gone"
            raise

    check("Verify deletion", verify_deleted)

    # ── Summary ────────────────────────────────────────────────────────────
    total = passed + failed
    color = "\033[32m" if failed == 0 else "\033[31m"
    print(f"\n{color}{'─' * 40}")
    print(f"  {passed}/{total} passed" + (f"  |  {failed} FAILED" if failed else "  — all clear"))
    print(f"{'─' * 40}\033[0m\n")
    return failed == 0


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Platform Advisor E2E test")
    parser.add_argument("--local", action="store_true", help="Target localhost:8080")
    parser.add_argument("--cleanup-only", action="store_true", help="Delete test data and exit")
    args = parser.parse_args()

    base = LOCAL_BASE if args.local else PROD_BASE
    print(f"\n\033[1mPlatform Advisor — E2E Test\033[0m")
    print(f"Target: {base}")

    cleanup(base)
    if args.cleanup_only:
        sys.exit(0)

    success = run(base)
    sys.exit(0 if success else 1)
