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

Credential injection (required for API checks; never printed):
  TEST_EMAIL        Cognito user email
  TEST_PASSWORD     Cognito password
  TEST_SECRET_ID    AWS Secrets Manager secret containing JSON keys
                    "username" (or "email") and "password". When set, this
                    takes precedence over TEST_EMAIL / TEST_PASSWORD.

Other environment variables (optional; defaults match stack outputs):
  API_URL           API base URL
  CF_URL            CloudFront base URL
  S3_BUCKET         Static frontend bucket
  USER_POOL_ID      Cognito User Pool ID
  CLIENT_ID         Cognito App Client ID
  AWS_PROFILE       AWS profile for boto3 (default: platform-advisor)
  AWS_REGION        AWS region (default: us-east-1)
"""
from __future__ import annotations
import argparse
import base64
import hashlib
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
AWS_REGION   = os.environ.get("AWS_REGION",   "us-east-1")
S3_BUCKET    = os.environ.get("S3_BUCKET",    "platform-advisor-frontend-dev-616627284001")
AGENTCORE_RUNTIME_ARN = os.environ.get(
    "AGENTCORE_RUNTIME_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:616627284001:runtime/"
    "PlatformAdvisorAgent_PlatformAdvisorAgent-3U71dVBprI",
)

# Expected CloudFront pages → expected HTTP status and optional page-specific text.
CF_PAGES = [
    ("/",                         200, None),
    ("/login/",                   200, None),
    ("/customers/",               200, None),
    ("/customers/_/",             200, None),
    ("/customers/_/sessions/_/",  200, None),
    ("/api/auth/callback/",       200, None),
    ("/architecture/",            200, "Start a blueprint"),
]
ARCHITECTURE_OBJECT_KEY = "architecture/index.html"
FRONTEND_ENTRY_KEY = "index.html"

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

DEMO_CUSTOMER_ID = "cust_demo_northwind"
DEMO_SESSION_IDS = {
    "sess_demo_centralized",
    "sess_demo_federated",
    "sess_demo_decentralized",
}
DEMO_PANEL_TYPES = [
    "intake",
    "decision_summary",
    "architecture_diagram",
    "requirements",
    "compliance",
    "service_map",
    "risk_cards",
    "phase_timeline",
    "cost_estimate",
    "blueprint",
]

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

def load_test_credentials(secret_client=None) -> tuple[str, str]:
    """Load smoke credentials from Secrets Manager or explicit environment."""
    secret_id = os.environ.get("TEST_SECRET_ID", "").strip()
    if secret_id:
        if secret_client is None:
            import boto3
            secret_client = boto3.Session(profile_name=AWS_PROFILE).client(
                "secretsmanager",
                region_name=AWS_REGION,
            )
        response = secret_client.get_secret_value(SecretId=secret_id)
        secret_string = response.get("SecretString")
        if not secret_string:
            raise RuntimeError(
                "TEST_SECRET_ID must reference a JSON SecretString"
            )
        try:
            secret = json.loads(secret_string)
        except (TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "TEST_SECRET_ID must reference valid JSON"
            ) from exc
        email = str(secret.get("username") or secret.get("email") or "").strip()
        password = str(secret.get("password") or "")
    else:
        email = os.environ.get("TEST_EMAIL", "").strip()
        password = os.environ.get("TEST_PASSWORD", "")

    if not email or not password:
        raise RuntimeError(
            "Smoke credentials are required: set TEST_SECRET_ID or both "
            "TEST_EMAIL and TEST_PASSWORD"
        )
    return email, password


def get_auth_tokens() -> tuple[str, str]:
    """Authenticate via Cognito and return the API access and runtime ID tokens."""
    try:
        import boto3
        test_email, test_password = load_test_credentials()
        client = boto3.Session(profile_name=AWS_PROFILE).client(
            "cognito-idp",
            region_name=AWS_REGION,
        )
        resp = client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": test_email,
                "PASSWORD": test_password,
            },
        )
        # Handle forced password change
        if resp.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
            resp = client.respond_to_auth_challenge(
                ClientId=CLIENT_ID,
                ChallengeName="NEW_PASSWORD_REQUIRED",
                Session=resp["Session"],
                ChallengeResponses={
                    "USERNAME": test_email,
                    "NEW_PASSWORD": test_password,
                },
            )
        result = resp.get("AuthenticationResult", {})
        access_token = result.get("AccessToken")
        id_token = result.get("IdToken")
        if not access_token or not id_token:
            raise RuntimeError("Cognito response did not contain required tokens")
        return access_token, id_token
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


def cf_get(path: str) -> tuple[int, str]:
    """Return the status and body for a CloudFront page."""
    url = f"{CF_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "text/html")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception:
        return 0, ""


def require_architecture_object() -> str:
    """Require the real static object so CloudFront fallback cannot mask it."""
    import boto3

    client = boto3.Session(profile_name=AWS_PROFILE).client(
        "s3",
        region_name=AWS_REGION,
    )
    response = client.head_object(
        Bucket=S3_BUCKET,
        Key=ARCHITECTURE_OBJECT_KEY,
    )
    size = response.get("ContentLength", 0)
    assert size > 0, f"s3://{S3_BUCKET}/{ARCHITECTURE_OBJECT_KEY} is empty"
    return f"{ARCHITECTURE_OBJECT_KEY}, {size} bytes"


def require_frontend_deployment_controls(s3_client=None) -> str:
    """Require rollback-capable storage and a hash-marked entry object."""
    if s3_client is None:
        import boto3

        s3_client = boto3.Session(profile_name=AWS_PROFILE).client(
            "s3",
            region_name=AWS_REGION,
        )

    versioning = s3_client.get_bucket_versioning(Bucket=S3_BUCKET)
    assert versioning.get("Status") == "Enabled", (
        f"s3://{S3_BUCKET} versioning is not enabled"
    )
    response = s3_client.head_object(
        Bucket=S3_BUCKET,
        Key=FRONTEND_ENTRY_KEY,
    )
    version_id = response.get("VersionId")
    deployment_sha = response.get("Metadata", {}).get("deployment-sha256", "")
    assert version_id, f"s3://{S3_BUCKET}/{FRONTEND_ENTRY_KEY} has no version"
    assert len(deployment_sha) == 64, (
        f"s3://{S3_BUCKET}/{FRONTEND_ENTRY_KEY} has no deployment SHA-256"
    )
    return f"version {version_id}, sha256 {deployment_sha[:12]}"


def token_actor_id(token: str) -> str:
    """Read the immutable Cognito subject used for AgentCore user scoping."""
    parts = token.split(".")
    if len(parts) < 2:
        raise ValueError("Cognito token is not a JWT")
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    actor_id = claims.get("sub")
    if not isinstance(actor_id, str) or not actor_id:
        raise ValueError("Cognito token is missing sub")
    return actor_id


def invoke_owned_agentcore_session(
    id_token: str,
    customer_id: str,
    session_id: str,
) -> str:
    """Invoke a cheap deterministic action while enforcing runtime ownership."""
    import boto3

    actor_id = token_actor_id(id_token)
    runtime_session_id = f"{customer_id}-{session_id}".ljust(33, "0")
    payload = {
        "action": "whatif",
        "customer_id": customer_id,
        "session_id": session_id,
        "user_message": "Verify owned-session runtime access.",
    }
    client = boto3.Session(profile_name=AWS_PROFILE).client(
        "bedrock-agentcore",
        region_name=AWS_REGION,
    )
    token_header = "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Cognito-Id-Token"

    def add_identity_header(request, **_kwargs):
        request.headers[token_header] = id_token

    client.meta.events.register(
        "before-sign.bedrock-agentcore.InvokeAgentRuntime",
        add_identity_header,
    )
    response = client.invoke_agent_runtime(
        agentRuntimeArn=AGENTCORE_RUNTIME_ARN,
        runtimeSessionId=runtime_session_id,
        runtimeUserId=actor_id,
        qualifier="DEFAULT",
        contentType="application/json",
        accept="text/event-stream",
        payload=json.dumps(payload).encode(),
    )
    raw = response["response"].read()
    text = raw.decode("utf-8", errors="replace")
    assert response.get("statusCode") == 200, response
    assert "Legacy score-only what-if is removed" in text, text[:500]
    assert "Session not found" not in text, text[:500]
    return f"HTTP 200, user {actor_id[:12]}..."


# ── Cleanup ────────────────────────────────────────────────────────────────────

def architecture_workspace_exists(
    id_token: str,
    customer_id: str,
    session_id: str,
) -> bool:
    """Check the scoped workspace without mutating it."""
    import boto3

    parts = id_token.split(".")
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    actor_id = claims["sub"]
    tenant_id = (
        claims.get("custom:tenant_id")
        or claims.get("tenant_id")
        or claims.get("custom:organization_id")
        or claims.get("organization_id")
        or actor_id
    )
    digest = hashlib.sha256(
        f"{customer_id}\0{session_id}".encode()
    ).hexdigest()[:24]
    scope_id = f"customer-session-{digest}"
    table_name = os.environ.get("DYNAMODB_TABLE", "platform-advisor-main")
    table = boto3.Session(profile_name=AWS_PROFILE).resource(
        "dynamodb",
        region_name=AWS_REGION,
    ).Table(table_name)
    response = table.get_item(
        Key={
            "PK": f"TENANT#{tenant_id}#USER#{actor_id}",
            "SK": f"ARCHITECTURE#CODING-PLATFORM#{scope_id}#HEAD",
        },
        ConsistentRead=True,
    )
    return "Item" in response


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
            api("DELETE", f"/customers/{c['customer_id']}", token)
            ok(f"Deleted {c['name']}", c["customer_id"])
            deleted += 1
        except Exception as e:
            fail(f"Delete {c['name']}", str(e))
    if deleted == 0:
        print("  No SMOKE- test data found.")


# ── Test runner ────────────────────────────────────────────────────────────────

def run_api(token: str, id_token: str) -> tuple[int, int]:
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

    # 1. Browser CORS preflight
    section("1. Browser CORS preflight")

    def check_customer_create_preflight():
        req = urllib.request.Request(
            f"{API_URL}/customers",
            headers={
                "Origin": CF_URL,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
            method="OPTIONS",
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            allow_origin = response.headers.get("Access-Control-Allow-Origin")
            allow_methods = response.headers.get(
                "Access-Control-Allow-Methods", ""
            ).upper()
            allow_headers = response.headers.get(
                "Access-Control-Allow-Headers", ""
            ).lower()
            assert 200 <= response.status < 300, response.status
            assert allow_origin == CF_URL, allow_origin
            assert "POST" in allow_methods, allow_methods
            assert "authorization" in allow_headers, allow_headers
            assert "content-type" in allow_headers, allow_headers
            return f"HTTP {response.status}, origin allowed"

    check("OPTIONS /customers permits browser POST",
          check_customer_create_preflight)

    # 2. Health
    section("2. Health check")
    health_url = API_URL.replace("/api/v1", "/health")
    check("GET /health",
          lambda: urllib.request.urlopen(health_url, timeout=10).read().decode()[:30])

    # 3. Temporary customer and session
    section("3. Temporary customer and session")
    customer_id = None
    session_id = None

    def create_customer():
        nonlocal customer_id
        c = api(
            "POST",
            "/customers",
            token,
            {"name": "SMOKE-Corp", "industry": "Technology"},
        )
        assert c.get("customer_id", "").startswith("cust_"), f"Unexpected: {c}"
        customer_id = c["customer_id"]
        return customer_id

    if not check("POST /customers", create_customer):
        return passed, failed + 1

    check("GET /customers/{id}",
          lambda: api("GET", f"/customers/{customer_id}", token)["name"])
    check("GET /customers (list)",
          lambda: f"{len(api('GET', '/customers', token))} total")

    def create_session():
        nonlocal session_id
        s = api(
            "POST",
            f"/customers/{customer_id}/sessions",
            token,
            {"title": "SMOKE-Session"},
        )
        assert s.get("session_id", "").startswith("sess_"), f"Unexpected: {s}"
        session_id = s["session_id"]
        return session_id

    if not check("POST /sessions", create_session):
        return passed, failed + 1

    check("GET /sessions/{id}",
          lambda: api("GET", f"/customers/{customer_id}/sessions/{session_id}", token)["status"])
    check("GET /sessions (list)",
          lambda: f"{len(api('GET', f'/customers/{customer_id}/sessions', token))} total")

    # 4. Architecture workspace
    section("4. Architecture workspace")
    architecture_scope = (
        f"?customer_id={customer_id}&session_id={session_id}"
    )

    def check_architecture_requires_auth():
        req = urllib.request.Request(
            f"{API_URL}/architecture/workspace",
            method="GET",
        )
        try:
            urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as exc:
            assert exc.code == 401, f"Expected 401, got HTTP {exc.code}"
            return "HTTP 401"
        raise AssertionError("Unauthenticated architecture request succeeded")

    check("GET /architecture/workspace requires auth",
          check_architecture_requires_auth)

    baseline_projection = None

    def get_architecture_workspace():
        nonlocal baseline_projection
        projection = api(
            "GET",
            f"/architecture/workspace{architecture_scope}",
            token,
        )
        assert projection.get("schema_version") == "3.0", projection
        pattern = projection.get("architecture", {}).get("pattern", {})
        assert pattern.get("pattern_id") == "pattern:logical-reference", pattern
        assert projection.get("projection_hash"), "Missing projection_hash"
        assert projection.get("architecture", {}).get("planes"), "Missing planes"
        baseline_projection = projection
        return projection["projection_hash"][:24]

    check("GET /architecture/workspace returns v3 projection",
          get_architecture_workspace)

    def evaluate_architecture_workspace():
        assert baseline_projection is not None, "Baseline projection unavailable"
        baseline_requirements = {
            item["requirement_id"]: item
            for item in baseline_projection.get("requirements", [])
        }
        current_value = baseline_requirements.get(
            "requirement:long-running-workspaces",
            {},
        ).get("value")
        answer = current_value is not True
        workspace = baseline_projection.get("workspace", {})
        refined = api(
            "POST",
            f"/architecture/workspace/evaluate{architecture_scope}",
            token,
            {
                "answers": {
                    "requirement:long-running-workspaces": answer,
                },
                "base_revision_number": workspace.get(
                    "persistence_revision"
                ),
                "base_state_hash": workspace.get("persistence_hash"),
            },
        )
        requirements = {
            item["requirement_id"]: item
            for item in refined.get("requirements", [])
        }
        requirement = requirements.get("requirement:long-running-workspaces", {})
        assert requirement.get("status") == "answered", requirement
        assert requirement.get("value") is answer, requirement
        component_ids = {
            component["component_id"]
            for plane in refined.get("architecture", {}).get("planes", [])
            for component in plane.get("components", [])
        }
        assert (
            "component:persistent-workspace" in component_ids
        ) is answer, component_ids
        assert refined.get("projection_hash") != baseline_projection.get("projection_hash")
        reloaded = api(
            "GET",
            f"/architecture/workspace{architecture_scope}",
            token,
        )
        assert reloaded.get("projection_hash") == refined.get("projection_hash")
        return f"persistent workspace {'added' if answer else 'removed'}"

    check("POST /architecture/workspace/evaluate applies answer",
          evaluate_architecture_workspace)

    def reject_unknown_architecture_requirement():
        try:
            api(
                "POST",
                f"/architecture/workspace/evaluate{architecture_scope}",
                token,
                {"answers": {"requirement:not-in-catalog": True}},
            )
        except RuntimeError as exc:
            message = str(exc)
            assert "HTTP 422" in message, message
            assert "unknown requirement" in message, message
            return "HTTP 422"
        raise AssertionError("Unknown architecture requirement was accepted")

    check("POST /architecture/workspace/evaluate rejects unknown input",
          reject_unknown_architecture_requirement)

    # 5. Intake answers round-trip
    section("5. Intake answers round-trip")

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

    # 7. Panel states
    section("7. Panel states")

    def save_panel():
        api(
            "PUT",
            f"/customers/{customer_id}/sessions/{session_id}/panels/1",
            token,
            {"step": 1, "panel_type": "intake", "data": {"complete": True}},
        )
        return "saved"

    check("PUT /panels/1", save_panel)
    check("GET /panels",
          lambda: f"{len(api('GET', f'/customers/{customer_id}/sessions/{session_id}/panels', token).get('panels', []))} panels")

    # 8. Session update
    section("8. Session update")
    check("PATCH /sessions status→complete",
          lambda: api("PATCH", f"/customers/{customer_id}/sessions/{session_id}", token,
                      {"status": "complete"})["status"])

    # 9. AgentCore direct invocation with runtime user identity.
    section("9. AgentCore owned-session invocation")
    check(
        "InvokeAgentRuntimeForUser enforces owned session",
        lambda: invoke_owned_agentcore_session(id_token, customer_id, session_id),
    )

    # 10. Admin metrics. The rollout identity must be an enrolled administrator.
    section("10. Admin metrics")
    def check_admin_metrics():
        m = api("GET", "/admin/metrics", token)
        return f"{m['total_customers']} customers, {m['total_sessions']} sessions"
    check("GET /admin/metrics", check_admin_metrics)

    # 11. Admin engine manifest
    section("11. Admin engine manifest")

    def check_admin_engine():
        manifest = api("GET", "/admin/engine", token)
        version = manifest.get("engine", {}).get("version")
        branches = manifest.get("questionnaire", {}).get("branches", [])
        assert version, f"Missing engine version: {manifest}"
        assert len(branches) >= 6, f"Expected workload branches, got {len(branches)}"
        return f"v{version}, {len(branches)} workload branches"

    check("GET /admin/engine", check_admin_engine)

    # 12. Prebuilt Northwind Finance portfolio
    section("12. Northwind Finance blueprints")

    def check_demo_customer():
        customer = api("GET", f"/customers/{DEMO_CUSTOMER_ID}", token)
        assert customer.get("name") == "Northwind Finance (Demo)", customer
        return customer["name"]

    check("GET Northwind Finance customer", check_demo_customer)

    def check_demo_sessions():
        sessions = api("GET", f"/customers/{DEMO_CUSTOMER_ID}/sessions", token)
        actual_ids = {session["session_id"] for session in sessions}
        assert actual_ids == DEMO_SESSION_IDS, actual_ids
        assert all(session.get("status") == "complete" for session in sessions), sessions
        return f"{len(sessions)} completed sessions"

    check("GET three prebuilt sessions", check_demo_sessions)

    for demo_session_id in sorted(DEMO_SESSION_IDS):
        def check_demo_panels(session_id=demo_session_id):
            response = api(
                "GET",
                f"/customers/{DEMO_CUSTOMER_ID}/sessions/{session_id}/panels",
                token,
            )
            panels = sorted(response.get("panels", []), key=lambda panel: panel["step"])
            actual_types = [panel["panel_type"] for panel in panels]
            assert actual_types == DEMO_PANEL_TYPES, actual_types
            return f"{len(panels)} panels"

        check(f"GET {demo_session_id} blueprint", check_demo_panels)

    # 13. Cleanup
    section("13. Cleanup")

    def verify_workspace_persisted():
        assert architecture_workspace_exists(
            id_token,
            customer_id,
            session_id,
        ), "Architecture workspace was not persisted"
        return "persisted"

    check("Verify scoped architecture workspace exists before cascade",
          verify_workspace_persisted)
    check("DELETE /customers/{id} (cascade)",
          lambda: api("DELETE", f"/customers/{customer_id}", token) or "deleted")

    def verify_workspace_deleted():
        assert not architecture_workspace_exists(
            id_token,
            customer_id,
            session_id,
        ), "Architecture workspace survived customer cascade"
        return "confirmed deleted"

    check("Verify architecture workspace cascade", verify_workspace_deleted)

    def verify_customer_gone():
        try:
            api("GET", f"/customers/{customer_id}", token)
            raise AssertionError("Customer still exists after delete")
        except RuntimeError as e:
            if "404" in str(e):
                return "confirmed 404"
            raise

    check("Verify customer deletion", verify_customer_gone)

    def verify_session_gone():
        try:
            api("GET", f"/customers/{customer_id}/sessions/{session_id}", token)
            raise AssertionError("Blueprint still exists after customer delete")
        except RuntimeError as e:
            if "404" in str(e):
                return "confirmed 404"
            raise

    check("Verify blueprint cascade", verify_session_gone)

    def verify_panels_gone():
        try:
            api(
                "GET",
                f"/customers/{customer_id}/sessions/{session_id}/panels",
                token,
            )
            raise AssertionError("Panel route still exists after customer delete")
        except RuntimeError as exc:
            if "404" in str(exc):
                return "confirmed 404"
            raise

    check("Verify panel cascade", verify_panels_gone)

    return passed, failed


def run_cf() -> tuple[int, int]:
    passed = failed = 0
    section("CloudFront page checks")

    try:
        detail = require_architecture_object()
        ok("S3 architecture object exists", detail)
        passed += 1
    except Exception as exc:
        fail("S3 architecture object exists", str(exc))
        failed += 1

    try:
        detail = require_frontend_deployment_controls()
        ok("S3 frontend deployment is rollback-capable", detail)
        passed += 1
    except Exception as exc:
        fail("S3 frontend deployment is rollback-capable", str(exc))
        failed += 1

    for path, expected, marker in CF_PAGES:
        status, body = cf_get(path)
        label = f"GET {path} → {expected}"
        if status != expected:
            fail(label, f"got HTTP {status}")
            failed += 1
        elif marker and marker not in body:
            fail(label, f"missing page marker {marker!r}; possible fallback response")
            failed += 1
        else:
            detail = f"HTTP {status}" + (f", found {marker!r}" if marker else "")
            ok(label, detail)
            passed += 1
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

    # Always need a token unless cf-only
    token = id_token = None
    if not args.cf_only:
        section("0. Cognito authentication")
        try:
            token, id_token = get_auth_tokens()
            ok("Cognito authentication", "tokens received")
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
        p, f = run_api(token, id_token)
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
