# Coding Platform Acceptance Test Plan

**Status:** Release-control baseline

**Scope:** Architecture-first Agentic Coding Platform Advisor

**Sources:** `docs/platform-advisor-product-vision.md`,
`docs/platform-advisor-architecture-first-implementation-plan.md`, active
backend/frontend/v3 code, and all repository tests reviewed 2026-07-31

## 1. Acceptance Contract

The release is accepted only when a customer can start with a useful
provider-neutral architecture, progressively supply requirements, understand
every architecture change, compare deployable alternatives, and publish a
versioned customer-specific package containing:

- Logical and deployable architectures.
- Selected services, compatible alternatives, rejection reasons, and decision
  matrices.
- Security controls, verification methods, best practices, economics, outcome
  measures, and a dependency-ordered roadmap.
- Requirements, assumptions, evidence, risks, decisions, versions, and a
  replayable trace.

Status means:

- **Existing:** an executable test exists in the repository; it is not evidence
  of a passing release until its command passes in CI.
- **Missing:** required automated coverage does not exist or the product
  contract is not implemented.
- **Manual:** independent human judgment is required and must produce signed
  evidence.

The untracked `architecture-first-demo/` tests are prototype evidence only.
They are not a production release gate.

## 2. Traceability Matrix

`E`, `M`, and `A` mean Existing, Missing, and Manual. Test IDs are defined in
Sections 3-5.

| Customer outcome or UX stage | Unit | Contract | Integration | Security | Deployment | Live smoke / human acceptance |
|---|---|---|---|---|---|---|
| **UX1 Start:** choose coding platform and see a useful logical baseline before intake | E01 | E06 | E07 | E08 | E10 | E11; A01 |
| **UX2 Discover:** focused question explains why it matters, supports `unknown`, and shows answer impact | E01, E02 | E06 | E07 | E08 | M13 | M08; A01 |
| **UX3 Confirm:** proposed requirement can be accepted, edited, or rejected without an implicit mutation | M01 | M04 | M05 | M10 | M13 | M08 |
| **UX4 Refine:** accepted answer creates a durable revision and visibly highlights nodes, edges, decisions, and alternatives changed | E01, E02 | E06 | E07 | E08 | M13 | M08; A02 |
| **UX5 Resolve:** assumptions, contradictions, unresolved decisions, evidence freshness, and readiness state are explicit | E01, E04 | M04 | M05 | E08 | M13 | M08; A01 |
| **UX6 Compare:** logical/deployable toggle exposes AWS, OSS, SaaS, and BYOP alternatives, trade-offs, Pareto set, and sensitivity | E03 | E06 | E07 | M10 | M13 | M08; A03 |
| **UX7 Review:** services, controls, economics, outcomes, roadmap, and trace are coherent lenses over one pinned revision | E03, E04 | E06 | M06 | M10 | M13 | M08; A03 |
| **UX8 Publish/reopen:** export a complete immutable package, reopen it, and reproduce the result | E02, E04 | M07 | M06 | M10 | M13 | M09; A03 |
| **O1 Customer-specific logical architecture and topology** | E01 | E06 | E07 | E08 | E10 | E11; A03 |
| **O2 Deployable stack and service selections** | E03 | E06 | E07 | M10 | E10 | M09; A03 |
| **O3 Alternatives, rejection reasons, decision matrix, and sensitivity** | E03 | E06 | E07 | M10 | M13 | M09; A03 |
| **O4 Controls, validation, governance, reliability, and best practices** | E04 | E06 | M06 | E08, E09 | E10 | M09; A03 |
| **O5 Token/runtime economics, capacity assumptions, ranges, and cost per outcome** | E04 | E06 | M06 | M10 | M13 | M09; A03 |
| **O6 Outcome observability and evaluation contract** | E04 | E06 | M12 | M10 | M13 | M09; A04 |
| **O7 Dependency-ordered implementation roadmap with exit criteria** | E04 | E06 | M06 | M10 | M13 | M09; A03 |
| **O8 Complete evidence trace, pinned versions, deterministic replay, and package hash** | E01, E02, E04 | M04, M07 | M06 | M10 | M13 | M09; A03 |
| **O9 Generated infrastructure and policy artifacts** | M03 | M07 | M06 | M11 | M13 | M09; A03 |
| **O10 Decision-to-implementation outcome loop and governed learning** | E04 | M04 | M12 | M10 | M13 | M09; A04 |

## 3. Existing Automated Tests

| ID | Layer | Acceptance covered | Repository evidence |
|---|---|---|---|
| E01 | Unit | Catalog integrity, approved/current evidence, stable IDs, progressive requirements, `unknown`, dependency closure, six-family feasibility, question ranking, one-variable deltas, deterministic replay | `tests/test_v3_catalog_compiler.py`, `test_v3_progressive_engine.py` |
| E02 | Unit | Projection has named architecture, assumptions, answer impacts, trace, decision history, hashes, and deterministic JSON | `tests/test_v3_projection.py` |
| E03 | Unit | Complete provider-class service coverage, compatibility fail-closed, ranked decision matrix, Pareto set, provider/BYOP handling, and sensitivity | `tests/test_v3_deployable_bundles.py` |
| E04 | Unit | Verified-control risk reduction, best-practice/assurance packet, economics formulas, outcome event contract, roadmap ordering, and packet hash | `tests/test_v3_assurance.py` |
| E05 | Regression | V1/v2 decision, graph, runtime identity, context, and guard behavior remains operational | remaining `PlatformAdvisorAgent/.../tests/` |
| E06 | API contract | Authenticated v3 projection, typed input rejection, revision/hash conflict, reset, persistence reload, deterministic projection | `backend/tests/test_architecture_workspace.py` |
| E07 | Integration | FastAPI-to-v3 projection and in-memory persistence round trip; live smoke verifies DynamoDB persistence after evaluation | `test_architecture_workspace.py`, `smoke_test.py` |
| E08 | Security | Tenant/actor isolation, customer/session ownership, auth/admin contracts, and fail-closed runtime identity | `test_tenant_authorization.py`, `test_auth_contract.py`, `test_runtime_identity.py` |
| E09 | Security contract | API default JWT, explicit public-route exceptions, scoped AgentCore invocation, trusted Cognito-group administration, non-writable privileged attributes, secret-injected smoke credentials, and DynamoDB retention are asserted | `backend/tests/test_infra_security_contract.py`, `backend/tests/test_smoke_security.py` |
| E10 | Deployment | Frontend production-env guard/build, SAM build path, CDK synth test, architecture export-object check | `Makefile`, `PlatformAdvisorAgent/agentcore/cdk/test/cdk.test.ts`, `smoke_test.py` |
| E11 | Live smoke | Real Cognito auth; `/health`; architecture auth; v3 baseline; evaluate/reload; unknown-input rejection; CloudFront route and S3 object | `smoke_test.py` |

### Exact Existing-Test Commands

Run from the repository root:

```bash
# Agent, v2 regression, and v3 unit suite
cd PlatformAdvisorAgent/app/PlatformAdvisorAgent
UV_CACHE_DIR=/private/tmp/platform-advisor-uv-cache \
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
uv run --with pytest pytest tests -q

# Backend API, persistence, tenancy, and infrastructure contracts
cd ../../..
PYTHONPATH=backend:PlatformAdvisorAgent/app/PlatformAdvisorAgent \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
backend/.venv/bin/python -m pytest backend/tests -q

# Frontend compile and production export
cd frontend
npx tsc --noEmit --incremental false
cd ..
make build-frontend

# AgentCore infrastructure
cd PlatformAdvisorAgent/agentcore/cdk
npm test -- --runInBand
cd ../../..

# Live deployed stack; requires the named AWS profile and smoke-test identity
make smoke-test AWS_PROFILE=platform-advisor AWS_REGION=us-east-1
```

Observed on 2026-07-31:

- Agent/v3 suite: **157 passed** against the current workspace.
- Backend suite: **51 passed** against the current workspace. The first run
  exposed five E09 failures; concurrent uncommitted infrastructure changes
  added edge JWT authorization, scoped/optional AgentCore invocation, explicit
  public routes, and DynamoDB replacement retention, after which all passed.
- Frontend TypeScript: **passed**.
- AgentCore CDK: **1 passed**, with a warning that its synthesized template has
  no resources.
- Production frontend build and live smoke were not run in this review.

## 4. Missing Automated Tests

| ID | Layer | Required test and acceptance |
|---|---|---|
| M01 | Frontend unit | Reducer/store and API normalization tests prove click and chat produce the same typed patch; accept/edit/reject changes state only after engine commit. |
| M02 | Frontend unit | Canvas/inspector tests prove logical data, deployable data, visible nodes, edges, selected component, deltas, and lenses remain consistent. |
| M03 | Unit | Artifact compiler validates generated IaC/policy syntax, provenance, secure defaults, unsupported-generation abstention, and content hashes. |
| M04 | API contract | Versioned command/event envelopes, append-only revision chain, accepted/rejected patches, idempotency, monotonic sequence, reconnect cursor, catalog upgrade, packet retrieval, and replay endpoints. |
| M05 | Integration | LLM extraction proposes a typed patch but cannot commit, select an offering, weaken a hard constraint, or introduce a value outside the pinned catalog. |
| M06 | Integration | One accepted command persists revision, event, outbox, decision packet, and S3 artifact atomically; replay and local/AgentCore execution produce byte-equivalent results. |
| M07 | Contract | Export schema and content test requires every O1-O9 section, pinned hashes/versions, citations, assumptions, alternatives, and checksums; reopen must reproduce the packet. |
| M08 | Browser E2E | First-time Playwright journey covers UX1-UX7, keyboard-only operation, mobile/desktop layouts, loading/error/offline/stale-write states, visible “why/change/remaining/ready” guidance, and no console/network failures. |
| M09 | Live smoke | Authenticated browser creates a named customer blueprint, answers via click and chat, observes a delta, compares alternatives, publishes, downloads, reopens, and verifies package hash against the API. |
| M10 | Security integration | Cross-tenant workspace/event/artifact/export denial, forged actor/tenant payloads, expired tokens, replayed idempotency keys, stale revisions, prompt injection, malicious links, and S3 URL/path isolation. |
| M11 | Security | Static and deploy-time scans for IAM wildcards, public storage, secret leakage, dependency vulnerabilities, generated policy/IaC violations, and artifact signature verification. |
| M12 | Integration | Advisor decision-to-agent-task-to-GitLab/CI/deployment outcome ingestion validates identity joins, duplicate/out-of-order events, consent, retention, and tenant isolation. |
| M13 | Deployment | CI workflow runs all gates; `sam validate --lint`, frontend export inspection, canary API/UI tests, rollback, CloudFront invalidation verification, log/alarm checks, and deployed catalog/engine hash parity. |
| M14 | Benchmark | Enforce artifact minimums, 60 scenarios/15 hidden, 500 counterfactuals, 10,000 property cases, mutation thresholds, BYOP corpus, generic-model comparison, and machine-readable benchmark report. |

These tests become executable with these canonical commands:

```bash
# Proposed frontend unit and browser suites
cd frontend && npm run test
cd frontend && npm run test:e2e

# Proposed benchmark and package contracts
cd PlatformAdvisorAgent/app/PlatformAdvisorAgent
PYTHONPATH=. uv run --with pytest pytest tests/test_v3_benchmarks.py \
  tests/test_v3_properties.py tests/test_v3_mutations.py -q
cd ../../..
PYTHONPATH=backend:PlatformAdvisorAgent/app/PlatformAdvisorAgent \
uv run --with pytest --with-requirements backend/requirements.txt pytest \
  backend/tests/test_workspace_events.py \
  backend/tests/test_workspace_export.py -q

# Proposed infrastructure/security gate
sam validate --lint --template-file infra/template.yaml
make build-frontend
make deploy AWS_PROFILE=platform-advisor AWS_REGION=us-east-1
make deploy-agentcore AWS_PROFILE=platform-advisor AWS_REGION=us-east-1
make deploy-frontend AWS_PROFILE=platform-advisor AWS_REGION=us-east-1
make smoke-test AWS_PROFILE=platform-advisor AWS_REGION=us-east-1
```

The proposed commands intentionally fail until the named tests/scripts and
required product contracts are implemented.

## 5. Manual Acceptance

| ID | Evidence required | Pass threshold |
|---|---|---|
| A01 | Five first-time target users complete UX1-UX7 without coaching; moderated notes and recordings retained | 5/5 can state where they are, what is required, why a recommendation changed, what remains unresolved, and whether it is publishable |
| A02 | Accessibility review at desktop and mobile, keyboard-only, screen reader, zoom, and reduced motion | WCAG 2.2 AA; no clipped/overlapping content or inaccessible canvas-only information |
| A03 | Three principal architects independently review held-out customer packages | 100% safety-critical agreement, >=90% feasibility/rejection agreement, kappa >=0.70, and no generic/unsupported package section |
| A04 | Three consented design partners complete implementation and baseline/30/90/180-day reviews | Every recommendation links to implementation status, deviations, control evidence, costs, incidents, and outcomes; no automatic rule promotion |

## 6. Release Gates

1. **G0 - Merge:** E01-E10 pass in CI; TypeScript and production build pass;
   no skipped/xfailed release tests; no unresolved critical/high vulnerability.
   The current workspace passes E09, but G0 remains unproven until the
   uncommitted infrastructure changes and all commands pass in CI.
2. **G1 - Engine R0.3:** M14 passes the implementation plan’s inventory and
   benchmark thresholds: 100% hard-constraint safety/expected abstention/
   referential integrity/replay, zero missing or incompatible selections, zero
   unverified risk reduction, >=95% feasible-set and capability/control recall,
   >=90% Pareto agreement/mutation score, and 100% safety mutation kills.
3. **G2 - API and security:** M04-M07, M10, and M11 pass. No browser-supplied
   tenant or actor is authorization evidence; every mutation is authenticated,
   idempotent, optimistic, append-only, and tenant scoped.
4. **G3 - Self-explanatory UX:** M01, M02, and M08 pass at desktop and mobile;
   A01 and A02 are signed. Snapshot/offline mode cannot appear publishable and
   chat cannot change architecture without an accepted visible patch.
5. **G4 - Customer package:** M07 and M09 prove a complete package can be
   exported, hash-verified, reopened, and replayed. A03 is signed against three
   held-out cases.
6. **G5 - AWS promotion:** deploy backend, AgentCore, and frontend as separate
   surfaces; M13 and E11 pass against the target account; deployed engine,
   catalog, API, and frontend hashes match the approved release; alarms are
   healthy and rollback is proven.
7. **G6 - Pilot/general availability:** M12 and A04 pass; design-partner
   disagreements are converted to scenarios, catalog/rule changes, or explicit
   coverage boundaries through normal reviewed release promotion.

No deployment or production promotion is acceptable while any earlier gate is
red.
