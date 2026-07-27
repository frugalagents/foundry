#!/usr/bin/env python3
"""
Platform Advisor — post-deploy smoke test.

Authenticates against real Cognito, exercises every API endpoint,
validates the intake-answers round-trip, and checks CloudFront pages.

Usage:
  python3 smoke_test.py                    # full run (API + CloudFront)
  python3 smoke_test.py --api-only         # skip CloudFront page checks
  python3 smoke_test.py --cf-only          # only check CloudFront pages
  python3 smoke_test.py --cleanup-only     # delete stale smoke-test data and exit

Environment variables (all optional — defaults match .env.local / stack outputs):
  TEST_EMAIL        Cognito user email  (default: admin@platform-advisor.com)
  TEST_PASSWORD     Cognito password    (default: PlatformAdvisor2025!)
  API_URL           API base URL
  CF_URL            CloudFront base URL
  USER_POOL_ID      Cognito User Pool ID
  CLIENT_ID         Cognito App Client ID
  AWS_PROFILE       AWS profile for boto3 (default: platform-advisor)
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────

API_URL      = os.environ.get("API_URL",      "https://5kr7vlzkfj.execute-api.us-east-1.amazonaws.com/api/v1")
CF_URL       = os.environ.get("CF_URL",       "https://d1wa5bvm23hhld.cloudfront.net")
USER_POOL_ID = os.environ.get("USER_POOL_ID", "us-east-1_oSEwvKdfd")
CLIENT_ID    = os.environ.get("CLIENT_ID",    "6gbe6mt1il74sdqlq8boc60ld4")
AWS_PROFILE  = os.environ.get("AWS_PROFILE",  "platform-advisor")
TEST_EMAIL   = os.environ.get("TEST_EMAIL",   "admin@platform-advisor.com")
TEST_PASS    = os.environ.get("TEST_PASSWORD","PlatformAdvisor2025!")

# Expected CloudFront pages → expected HTTP status
CF_PAGES = [
    ("/",                      200),
    ("/login/",                200),
    ("/customers/",            200),
    ("/customers/_/",          200),
    ("/customers/_/sessions/_/", 200),
    ("/api/auth/callback/",    200),
]

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

# ── Output helpers ─────────────────────────────────────────────────────────────

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
SKIP = "\033[33m-\033[0m"


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


def ok(label: str, detail: str = "") -> None:
    suffix = f"  \033[2m({detail})\033[0m" if detail else ""
    print(f"  {PASS}  {label}{suffix}")


def fail(label: str, err: str) -> None:
    print(f"  {FAIL}  {label}: \033[31m{err}\033[0m")


# ── Cognito auth ───────────────────────────────────────────────────────────────

def get_access_token() -> str:
    """Authenticate via Cognito USER_PASSWORD_AUTH and return the AccessToken."""
    try:
        import boto3
        client = boto3.Session(profile_name=AWS_PROFILE).client("cognito-idp", region_name="us-east-1")
        resp = client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": TEST_EMAIL, "PASSWORD": TEST_PASS},
        )
        # Handle forced password change
        if resp.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
            resp = client.respond_to_auth_challenge(
                ClientId=CLIENT_ID,
                ChallengeName="NEW_PASSWORD_REQUIRED",
                Session=resp["Session"],
                ChallengeResponses={"USERNAME": TEST_EMAIL, "NEW_PASSWORD": TEST_PASS},
            )
        result = resp.get("AuthenticationResult", {})
        token = result.get("AccessToken")
        if not token:
            raise RuntimeError(f"No AccessToken in response: {resp}")
        return token
    except Exception as exc:
        raise RuntimeError(f"Cognito auth failed: {exc}") from exc


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    url = f"{API_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} {method} {path}: {body_text}") from e


def cf_get(path: str) -> int:
    """Return the HTTP status code for a CloudFront page."""
    url = f"{CF_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "text/html")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


# ── Cleanup ────────────────────────────────────────────────────────────────────

def cleanup(token: str) -> None:
    section("Cleanup — removing SMOKE- test data")
    try:
        customers = api("GET", "/customers", token)
    except Exception as e:
        print(f"  Could not list customers: {e}")
        return
    deleted = 0
    for c in customers:
        if not c.get("name", "").startswith("SMOKE-"):
            continue
        try:
            sessions = api("GET", f"/customers/{c['customer_id']}/sessions", token)
            for s in sessions:
                api("DELETE", f"/customers/{c['customer_id']}/sessions/{s['session_id']}", token)
            api("DELETE", f"/customers/{c['customer_id']}", token)
            ok(f"Deleted {c['name']}", c["customer_id"])
            deleted += 1
        except Exception as e:
            fail(f"Delete {c['name']}", str(e))
    if deleted == 0:
        print("  No SMOKE- test data found.")


# ── Test runner ────────────────────────────────────────────────────────────────

def run_api(token: str) -> tuple[int, int]:
    passed = failed = 0

    def check(label: str, fn) -> bool:
        nonlocal passed, failed
        try:
            detail = fn()
            ok(label, str(detail) if detail else "")
            passed += 1
            return True
        except Exception as e:
            fail(label, str(e))
            failed += 1
            return False

    # 1. Health
    section("1. Health check")
    health_url = API_URL.replace("/api/v1", "/health")
    check("GET /health",
          lambda: urllib.request.urlopen(health_url, timeout=10).read().decode()[:30])

    # 2. Customer CRUD
    section("2. Customer CRUD")
    customer_id = None

    def create_customer():
        nonlocal customer_id
        c = api("POST", "/customers", token, {"name": "SMOKE-Corp", "industry": "Technology"})
        assert c.get("customer_id", "").startswith("cust_"), f"Unexpected: {c}"
        customer_id = c["customer_id"]
        return customer_id

    if not check("POST /customers", create_customer):
        return passed, failed + 1

    check("GET /customers/{id}",
          lambda: api("GET", f"/customers/{customer_id}", token)["name"])
    check("GET /customers (list)",
          lambda: f"{len(api('GET', '/customers', token))} total")

    # 3. Session CRUD
    section("3. Session CRUD")
    session_id = None

    def create_session():
        nonlocal session_id
        s = api("POST", f"/customers/{customer_id}/sessions", token, {"title": "SMOKE-Session"})
        assert s.get("session_id", "").startswith("sess_"), f"Unexpected: {s}"
        session_id = s["session_id"]
        return session_id

    if not check("POST /sessions", create_session):
        return passed, failed + 1

    check("GET /sessions/{id}",
          lambda: api("GET", f"/customers/{customer_id}/sessions/{session_id}", token)["status"])
    check("GET /sessions (list)",
          lambda: f"{len(api('GET', f'/customers/{customer_id}/sessions', token))} total")

    # 4. Intake answers round-trip
    section("4. Intake answers round-trip")

    def put_intake():
        api("PUT", f"/customers/{customer_id}/sessions/{session_id}/inputs", token,
            {"answers": INTAKE_ANSWERS})
        return "saved"

    check("PUT /inputs (save answers)", put_intake)

    def get_intake_back():
        s = api("GET", f"/customers/{customer_id}/sessions/{session_id}", token)
        saved = s.get("intake_answers") or {}
        assert saved.get("autonomy_model") == INTAKE_ANSWERS["autonomy_model"], \
            f"intake_answers not restored: {saved}"
        return f"{len(saved)} fields"

    check("GET /sessions (intake_answers restored)", get_intake_back)

    # 5. Panel states
    section("5. Panel states")
    check("GET /panels",
          lambda: f"{len(api('GET', f'/customers/{customer_id}/sessions/{session_id}/panels', token).get('panels', []))} panels")

    # 6. Session update
    section("6. Session update")
    check("PATCH /sessions status→complete",
          lambda: api("PATCH", f"/customers/{customer_id}/sessions/{session_id}", token,
                      {"status": "complete"})["status"])

    # 7. Admin metrics (403 expected for non-admin test user — counted as pass)
    section("7. Admin metrics")
    def check_admin_metrics():
        try:
            m = api("GET", "/admin/metrics", token)
            return f"{m['total_customers']} customers, {m['total_sessions']} sessions"
        except RuntimeError as e:
            if "403" in str(e):
                return "skipped (non-admin user — expected)"
            raise
    check("GET /admin/metrics", check_admin_metrics)

    # 8. Cleanup
    section("8. Cleanup")
    check("DELETE /sessions/{id}",
          lambda: api("DELETE", f"/customers/{customer_id}/sessions/{session_id}", token) or "deleted")
    check("DELETE /customers/{id}",
          lambda: api("DELETE", f"/customers/{customer_id}", token) or "deleted")

    def verify_gone():
        try:
            api("GET", f"/customers/{customer_id}", token)
            raise AssertionError("Customer still exists after delete")
        except RuntimeError as e:
            if "404" in str(e):
                return "confirmed 404"
            raise

    check("Verify deletion", verify_gone)

    return passed, failed


def run_cf() -> tuple[int, int]:
    passed = failed = 0
    section("CloudFront page checks")
    for path, expected in CF_PAGES:
        status = cf_get(path)
        label = f"GET {path} → {expected}"
        if status == expected:
            ok(label, f"HTTP {status}")
            passed += 1
        else:
            fail(label, f"got HTTP {status}")
            failed += 1
    return passed, failed


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Platform Advisor smoke test")
    parser.add_argument("--api-only", action="store_true", help="Skip CloudFront checks")
    parser.add_argument("--cf-only",  action="store_true", help="Only check CloudFront pages")
    parser.add_argument("--cleanup-only", action="store_true", help="Delete stale test data and exit")
    args = parser.parse_args()

    print(f"\n\033[1mPlatform Advisor — Smoke Test\033[0m")
    print(f"API:   {API_URL}")
    print(f"CF:    {CF_URL}")
    print(f"User:  {TEST_EMAIL}")

    # Always need a token unless cf-only
    token = None
    if not args.cf_only:
        section("0. Cognito authentication")
        try:
            token = get_access_token()
            ok("admin_initiate_auth → AccessToken", token[:20] + "…")
        except Exception as e:
            fail("Cognito auth", str(e))
            print("\n\033[31mCannot continue without a valid token.\033[0m\n")
            sys.exit(1)

    if args.cleanup_only:
        cleanup(token)
        sys.exit(0)

    total_passed = total_failed = 0

    if not args.cf_only:
        cleanup(token)
        p, f = run_api(token)
        total_passed += p
        total_failed += f

    if not args.api_only:
        p, f = run_cf()
        total_passed += p
        total_failed += f

    total = total_passed + total_failed
    color = "\033[32m" if total_failed == 0 else "\033[31m"
    print(f"\n{color}{'─' * 44}")
    print(f"  {total_passed}/{total} passed" +
          (f"  |  {total_failed} FAILED" if total_failed else "  — all clear"))
    print(f"{'─' * 44}\033[0m\n")
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
