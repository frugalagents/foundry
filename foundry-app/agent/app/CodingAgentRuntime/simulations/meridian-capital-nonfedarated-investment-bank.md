# Simulation: Meridian Capital — Non-Federated Investment Bank

## Customer Profile

| Attribute | Value |
|---|---|
| Company | Meridian Capital (major US investment bank) |
| Developers | ~6,500 in a single centrally governed organization |
| HQ | New York, NY |
| Offices | London, Singapore, Hong Kong, Mumbai |
| Regulatory | SOX, PCI-DSS, SEC Rule 17a-4, FINRA, UK FCA, MAS Singapore |
| Code domains | Java (45%), Python quant (30%), C++ low-latency (15%), COBOL legacy (5%), TypeScript (5%) |
| IDEs | VS Code (standard), JupyterLab (quant research) |
| CI/CD | GitHub Actions only — strictly controlled |
| SCM | GitHub Enterprise (centralized, enterprise admin) |
| Identity | Single Okta tenant (no exceptions) |
| Secrets | CyberArk PAM (enterprise standard) |
| Governance | Centralized IT — no BU exceptions, no self-service |

---

## Advisor Discovery

**Advisor:** Before we design anything — tell me about your regulatory environment. You mentioned SOX. Do you have any repos that touch trading systems or financial models that would be subject to model risk management review?

**Customer (CTO):** Yes. We have quant models for risk, pricing, and credit. Our Model Risk Management team validates all models used in financial decision-making. We assume that includes AI-assisted code generation for those systems.

**Advisor:** That's a critical design constraint. SR 11-7 — the OCC/Fed guidance on model risk management — may require your MRM team to validate the coding agent itself as a model before it can touch quantitative or risk code. That's not a platform team decision, it's an MRM team decision. I'd recommend scoping the initial rollout to Java infrastructure code — far from quant models — and letting MRM run their validation in parallel. Do not commit to a timeline for quant or trading coverage until MRM has assessed the tool.

**Customer:** Fair. Now — our secrets management is CyberArk, not AWS Secrets Manager. That's a hard enterprise standard. Can the MCP gateway work with CyberArk?

**Advisor:** Not out of the box. The standard AgentCore Gateway and most MCP gateway implementations inject credentials from Secrets Manager or IAM roles. CyberArk requires a custom adapter — a Lambda or sidecar that calls the CyberArk Central Credential Provider (CCP) API to fetch time-limited credentials, then injects them into the MCP tool call context. It's buildable but it's custom work. I'll flag this as a platform engineering task rather than configuration. Importantly: CyberArk issues ephemeral tokens per request — the adapter needs to handle token refresh within a session gracefully.

**Customer:** Our developers also don't have persistent GitHub credentials. They request tokens through CyberArk PAM workflows — time-limited, audited. The agent's GitHub MCP tool needs to work with these ephemeral tokens.

**Advisor:** Same CyberArk adapter handles this. The session init flow becomes: (1) developer authenticates, (2) Lambda authorizer calls CyberArk CCP to fetch an ephemeral GitHub token scoped to the developer's repos, (3) token injected into the MCP gateway's GitHub tool context, (4) token refreshed if the session exceeds the CyberArk token TTL. The key risk is session duration vs CyberArk token TTL — if developers run long sessions, the token may expire mid-session. Configure the MCP gateway to handle 401 responses from GitHub by triggering a CyberArk re-fetch rather than surfacing an error.

**Customer:** What about MNPI — Material Non-Public Information? We have code in certain repos that could reveal pending M&A analysis, trading strategy algorithms, or client position management logic. If an AI reads that code and the session is later audited in litigation, we have a potential disclosure problem.

**Advisor:** MNPI is a distinct compliance category that sits between standard DLP and legal hold. It's not ITAR, it's not PHI — it's information asymmetry risk. The platform needs a classification tier for MNPI-adjacent repos: the agent can access these repos, but session logs must be sequestered under enhanced access controls (legal and compliance team only, not platform admins), and the DLP rules must prevent MNPI-adjacent content from appearing in any externally-routed response. This is also a strong argument for session content not being logged at all by default in MNPI repos — metadata only (file paths accessed, tool calls made, user identity, timestamp). I'll flag MNPI classification as a gap in our knowledge base — we don't have a purpose-built node for financial MNPI. You'll need your legal team to define the classification criteria.

**Customer:** SEC Rule 17a-4. All our broker-dealer electronic records need to be retained in non-erasable, non-rewritable format for 3-6 years. Do AI session logs count?

**Advisor:** If the session involved work on trading-related code or communications, almost certainly yes — they're potentially covered records under 17a-4(f). The technical requirement is WORM storage. Amazon S3 Object Lock in COMPLIANCE mode satisfies WORM for 17a-4 purposes — it's been used by financial institutions for this. GOVERNANCE mode is not sufficient; 17a-4 requires that even administrators cannot delete or modify the records. Set retention period to 6 years for all trading-adjacent session logs; 3 years minimum for others. Your compliance team should confirm which session log categories are covered records.

**Customer:** Our quant researchers are a problem. 200 people. Very high autonomy culture. If we make the corporate platform too restrictive, they'll use personal Claude accounts. Our CISO considers this the top shadow-IT risk.

**Advisor:** The solution to shadow-IT is building a platform that's better than the alternative, not locking down personal accounts (which you can't actually enforce). For quants, the key surface is JupyterLab — they live there. Claude Code doesn't have a JupyterLab extension, so we need a different approach: a Jupyter MCP server or a Jupyter kernel integration that makes the agent available inside JupyterLab. The pattern is an MCP server that wraps Jupyter's API — the agent can read and write notebook cells, execute cells, and access the kernel state. This doesn't exist as an off-the-shelf product but is buildable. Give quants the agent in their preferred environment before you worry about policy tiers.

**Customer:** What about developer productivity metrics? Our HR and legal teams have pre-emptively said: don't collect individual productivity metrics at all. They're worried about employment litigation.

**Advisor:** That's actually a clean design choice that simplifies the platform. No per-developer metrics anywhere — not in CloudWatch, not in DynamoDB, not in any dashboard. The platform collects: session events (for security audit), tool calls (for the audit trail), cost per session (for billing, attributed at team level), and errors (for ops). Individual developer data exists only in the session identity field of audit logs — and those are access-controlled to security and compliance only. No acceptance rate metrics, no velocity metrics, no PR merge rate metrics. Management dashboards show BU-level cost and adoption only. This is the most defensible position legally.

**Customer:** We have ~300K lines of COBOL for general ledger and settlement. Can the agent help with COBOL modernization?

**Advisor:** The first step is a model capability evaluation for COBOL — frontier models have seen far less COBOL than Java or Python in their training data, so we need to establish a baseline before promising anything. For the initial deployment, I'd recommend read-only access only — the agent can explain COBOL modules, generate documentation, and propose refactoring plans — but no writes. Any COBOL change touches SOX-controlled financial systems; those changes need to go through formal change control regardless of how they originate. The agent can be a comprehension accelerator; the change pipeline stays human-controlled.

**Customer:** Low-latency C++ for trading execution. The team is deeply skeptical. They're worried about latency regressions from AI-suggested code.

**Advisor:** Their skepticism is well-founded. C++ for microsecond-latency execution has constraints — memory allocation patterns, cache line behavior, branch predictor friendliness, lock-free data structures — that most AI training data doesn't capture. I'd recommend a heavily constrained pilot: read-only mode for the first 6 months, then code review suggestions only (no direct writes), then carefully evaluated write access for non-hot-path code. And a mandatory performance regression gate: every AI-assisted C++ change must pass a latency benchmark suite before merge, enforced as a CI check.

**Customer:** Our TPRM process for new AI vendors is 12-16 weeks per vendor. AWS is already approved. Anthropic needs to go through this process.

**Advisor:** That's a real timeline constraint. Start the TPRM process for Anthropic now — in parallel with design. Note that when using Bedrock, Anthropic doesn't directly process your data; AWS does, and AWS is already approved. Your TPRM team should confirm whether Bedrock's use of Claude constitutes a separate Anthropic vendor relationship or is covered by the AWS relationship. This could save you 12-16 weeks.

**Customer:** Singapore and Hong Kong. MAS TRM guidelines require certain data to stay in Singapore-based infrastructure.

**Advisor:** MAS TRM guidelines require that critical systems and customer data be hosted in Singapore-based infrastructure with operational resilience. For a coding agent platform, the relevant data is developer session data for Singapore-based developers. The simplest approach is a Singapore regional instance (ap-southeast-1) for Singapore and Hong Kong developers — same platform, same policy, same Claude Code deployment, but inference and log storage in the Singapore region. This is "one platform" with regional data residency enforcement, not separate governance. SCPs lock the Singapore account to ap-southeast-1 only.

---

## Platform Blueprint

### Instance Topology

```
Central Platform Team (New York)
├── Identity: Okta (single tenant, MFA enforced)
├── Secrets: CyberArk CCP API ← custom Lambda adapter
├── Policy: OPA bundle server (S3 + CloudFront, signed)
└── SIEM: Splunk (SOX audit trail + security monitoring)

Instance 1: US Commercial (us-east-1) — Primary
  Populations: Java, Python data, TypeScript, COBOL (read-only)
  Harness: Claude Code Enterprise
  MCP Gateway: AgentCore Gateway + CyberArk adapter
  Logging: S3 Object Lock COMPLIANCE (6-year, trading-adjacent) + standard (13-month)
  Metrics: Team/BU level only; no per-developer dimensions

Instance 2: Asia-Pacific (ap-southeast-1) — Singapore/HK
  Populations: Same as US Commercial, Singapore/HK developers
  Harness: Claude Code Enterprise (same config as US)
  Data residency: SCP locks to ap-southeast-1; no cross-region replication
  MAS TRM: ap-southeast-1 is AWS Singapore region; satisfies MAS data residency

Instance 3: UK / Europe (eu-west-2) — London
  Populations: London developers
  Harness: Claude Code Enterprise
  Data residency: FCA data residency requirements for UK developer data
  GDPR: UK GDPR applies; SCCs not required post-Brexit (UK adequacy decision for AWS)

[Note: No separate quant/trading instance — policy tiers handle differentiation within Instance 1]
```

### Phase 1: Foundation (Months 1–3)

**Prerequisites:**
1. TPRM for Anthropic — determine if Bedrock relationship is covered by AWS approval; if not, start TPRM immediately
2. MRM team briefing — brief Model Risk Management on SR 11-7 implications; get their assessment scope defined
3. Legal briefing — MNPI classification criteria for repos; SEC 17a-4 coverage determination for session logs
4. CyberArk adapter — platform engineering sprint to build Lambda-based CCP integration

**Identity and access:**
- Okta → IAM Identity Center (existing Okta enterprise tenant; add IAM Identity Center as SAML app)
- MFA: already enforced at Okta level; IAM Identity Center inherits via SAML assertion
- IAM roles: `meridian-developer-standard`, `meridian-developer-readonly`, `meridian-platform-admin`
- No per-developer IAM roles — team-level roles with session tags for identity

**CyberArk MCP gateway adapter:**
- Lambda function: `cyberark-credential-broker`
- Invoked at session init and on 401 response from any MCP tool
- Calls CyberArk CCP REST API with developer's Okta session token as authentication
- Returns ephemeral GitHub token scoped to developer's repo access list
- Token stored in Lambda memory only for session duration; never written to logs or environment variables
- Token TTL monitoring: Lambda tracks issue time; refreshes 5 minutes before expiry

**Observability (no per-developer metrics):**
- CloudWatch metrics: dimensions are `team`, `language_domain`, `repo_category`, `cost_tier`
- No `developer_id` dimension anywhere in metrics
- Audit logs: `developer_id` present in log records for security investigation use only
- Log group IAM policy: audit logs readable only by `meridian-security-team` role
- DynamoDB session store: stores session metadata; `developer_id` field encrypted with CMK; key policy restricts decryption to security role

**WORM storage for SEC 17a-4:**
- S3 bucket: `meridian-session-logs-worm-trading`
- Object Lock: COMPLIANCE mode, 6-year retention
- Applied to: all sessions where any repo in context is tagged `trading-system` or `risk-model` or `mnpi-adjacent`
- Standard ops logs: separate bucket, no Object Lock, 13-month lifecycle rule
- EventBridge rule: route session events to WORM bucket if repo tags match; route to standard bucket otherwise

**Initial population: Java developers (2,900 developers)**
- Java repos: enterprise banking services, API platforms, infrastructure
- No SOX-critical financial system code in initial scope
- Standard policy tier: full Claude Code feature set
- Model tiering: Haiku for autocomplete, Sonnet for file edits
- Per-session cost ceiling: $3 soft / $8 hard
- Monthly quota: $60/developer

### Phase 2: Expanded Developer Population (Months 3–5)

**Python data engineering and analytics (~1,000 developers):**
- Non-quant Python: ETL pipelines, data platform, analytics
- Standard policy tier — same as Java
- Enable: code completion, file edits, test generation, documentation

**COBOL legacy team (~200 developers):**
- Model capability evaluation: run 6-step eval on COBOL corpus (GL and settlement code)
- Expected result: explanation and comprehension strong; refactoring uncertain; generation weak
- Initial deployment: read-only (explanation, documentation, comprehension only)
- Write access: deferred until eval results reviewed and change control process updated for AI-assisted COBOL changes
- SOX gate: any COBOL change — AI-assisted or not — goes through existing SOX change control workflow; AI is not a bypass

**Singapore/HK instance activation:**
- Deploy Claude Code Enterprise configuration in ap-southeast-1
- SCP applied: deny all resource creation outside ap-southeast-1
- Route Singapore/Hong Kong Okta users to AP instance via IAM Identity Center routing
- MAS TRM documentation: prepare system architecture document for MAS notification if required

**TypeScript internal tooling (~325 developers):**
- Standard policy tier
- Lowest-risk population; relatively unrestricted

### Phase 3: Quant Research and Trading (Months 5–9)

**Quant research enablement (prerequisite: MRM validation):**
- MRM validation scope: evaluate coding agent as a model under SR 11-7; determine if it qualifies as a "model" (likely: it provides outputs used in model development workflows); define ongoing monitoring requirements
- JupyterLab surface: build Jupyter MCP server (custom) — wraps Jupyter Server API; allows agent to read/write notebook cells, execute code, inspect kernel state; deployed as a sidecar alongside JupyterLab instances
- Quant policy tier: innovation-lab-like within compliance constraints; full Python features; access to quant repo code index (RAG over quant codebase)
- MNPI gate: quant repos tagged `mnpi-adjacent`; enhanced session log sequestration (compliance-only access); no session content in standard audit trail
- Model tiering for quants: Sonnet as default (complex statistical code); Opus on-demand for model architecture review

**C++ trading execution team (prerequisite: 6-month Java success + MRM clearance):**
- Pilot: 20 developers, read-only mode only for months 1-3 of pilot
- Capability evaluation: run eval specifically for low-latency C++ patterns (lock-free data structures, SIMD intrinsics, memory allocation patterns)
- Performance regression gate: CI check that runs latency benchmark suite on every AI-assisted C++ PR
- Write access: non-hot-path C++ only (tooling, test infrastructure, logging); hot-path execution code remains read-only
- Expanded access: evaluated at 6-month pilot review; requires trading technology leadership sign-off

### Key Tradeoffs Accepted

| Decision | Choice | Rationale |
|---|---|---|
| No per-developer metrics | Zero individual metrics collected | HR/legal risk mitigation; works council equivalent (employment litigation risk in US + EU) |
| CyberArk adapter | Custom Lambda, not Secrets Manager | Enterprise secrets standard is non-negotiable; buildable with 1 sprint |
| COBOL read-only initially | No writes | Model capability unproven; SOX change control must be updated for AI-assisted changes first |
| Quant rollout last | After MRM validation | SR 11-7 compliance; quant access to production risk models requires MRM clearance |
| Trading C++ pilot | Read-only → review-only → limited write | Team skepticism justified; performance regression risk is real |
| JupyterLab surface | Custom MCP server | No off-the-shelf solution; required to capture quant population and prevent shadow IT |
| MNPI sequestration | Metadata-only logging, compliance access only | Legal/compliance determination; MNPI in session logs creates disclosure risk |

### Platform Best Practices

- **Resilience:** AWS SDK adaptive retry; circuit-breaker on CyberArk CCP calls (if CyberArk is unavailable, session gracefully degrades to no MCP tool access rather than failing completely)
- **Credential hygiene:** CyberArk adapter injects ephemeral tokens; tokens never persist beyond session; truffleHog on all platform repos; Macie on session log buckets scanning for inadvertently logged credentials
- **Change safety:** All developer sessions auto-branch; no direct main commits; idle session timeout 20 minutes (trading floor security policy)
- **Supply chain:** MCP server versions pinned in AgentCore Gateway allowlist; AWS Signer for container images; quarterly dependency review
- **WORM integrity:** Monthly S3 Object Lock inventory report; verify no COMPLIANCE objects have been modified (should be impossible; verification is the audit evidence)

### Org Readiness Flags

| Dimension | What's needed | Owner |
|---|---|---|
| MRM validation | SR 11-7 assessment of coding agent; validation report; ongoing monitoring plan | Model Risk Management team |
| MNPI classification | Define which repos are MNPI-adjacent; maintain the classification list | Legal / Compliance |
| CyberArk adapter | 1 sprint to build and test Lambda-based CCP integration | Platform Engineering |
| Jupyter MCP server | 2-3 sprint custom build; requires Jupyter Server API expertise | Platform Engineering |
| SOX change control update | Update change control procedure for AI-assisted COBOL/financial system changes | IT Audit + Platform team |
| Trading latency benchmarks | Define benchmark suite for C++ AI-assisted PR gate; integrate into CI | Trading Technology |
| Developer onboarding | Prompt engineering for quant Python, COBOL comprehension, low-latency C++ | BU-specific L&D |

---

## Post-Simulation Advisor Notes

### What the Advisor Handled Well

- **SR 11-7 proactive surfacing:** Raised model risk management before the customer mentioned it; correctly scoped it as an MRM determination, not a platform team decision. This is a genuinely high-stakes constraint that would delay quant rollout significantly if discovered late.
- **CyberArk integration:** Correctly identified as a non-standard path requiring custom work; provided a concrete pattern (Lambda CCP adapter, token refresh on 401). Grounded in general MCP gateway knowledge applied to the specific constraint.
- **MNPI classification:** Correctly identified MNPI as distinct from DLP, legal hold, and standard classification. No OKF node covers this — the advisor correctly flagged it as a gap and deferred to legal.
- **SEC 17a-4 WORM:** Applied the legal hold node's COMPLIANCE mode S3 Object Lock pattern correctly to the financial records context. The technical mechanism is the same; the trigger is different.
- **No productivity metrics:** Treated as a valid first-class design choice rather than a limitation. Correctly identified the downstream simplification this creates.
- **JupyterLab shadow-IT framing:** Correctly identified the root problem (quants will defect to personal tools if corporate platform doesn't serve their environment) and proposed the right solution (Jupyter MCP server) rather than a policy-only response.
- **Staged rollout by risk:** Java first → Python data → COBOL read-only → quant (post-MRM) → trading C++ pilot. Risk-stratified sequence is correct.

### What Stretched the Knowledge Base

- **SR 11-7 / model risk management:** The advisor surfaced it correctly but the OKF has no node for it. Specific guidance on what MRM validation looks like for a coding agent, what the ongoing monitoring requirements are, and how to document model risk for an AI developer tool is missing.
- **MNPI classification:** Correctly identified as a gap. No OKF node covers financial information classification tiers, MNPI-specific DLP configuration, or the specific session log access control pattern for MNPI.
- **CyberArk integration:** The advisor provided a reasonable pattern but the OKF has no node for third-party PAM integration. The CyberArk CCP API details, token handling patterns, and failure modes are not documented.
- **JupyterLab MCP server:** Advised building a custom Jupyter MCP server but the OKF has no guidance on Jupyter API integration patterns, notebook cell read/write semantics, or kernel state access for agents.
- **FINRA / FCA specifics:** The advisor correctly flagged these regulators but didn't address their specific technical requirements beyond data residency. FINRA Rule 17a-4 has nuances beyond SEC Rule 17a-4; FCA has SYSC requirements.

### OKF Gaps Identified

| Gap Name | Description | Priority | Trigger Signals |
|---|---|---|---|
| `access/model-risk-management.md` | SR 11-7 and OCC guidance on AI model risk management — validation scope for coding agents, ongoing monitoring requirements, MRM team engagement pattern, what documentation is required | High | sr-11-7, model-risk, mrm, occ-guidance, fed-guidance, financial-model-validation, ai-validation |
| `access/mnpi.md` | Material Non-Public Information classification for financial institutions — what repos require MNPI classification, session log sequestration pattern, DLP configuration for trading strategy and M&A code, legal team access controls | High | mnpi, material-nonpublic, trading-strategy, ma-code, financial-ip, information-barriers |
| `gateway/cyberark-integration.md` | CyberArk PAM integration for MCP gateway credential injection — CCP API adapter pattern, ephemeral token handling, session duration vs token TTL management, failure modes | Medium | cyberark, pam, privileged-access, cyberark-ccp, ephemeral-credentials, no-secrets-manager |
| `surfaces/jupyterlab.md` | JupyterLab as an agent surface — Jupyter Server API MCP server pattern, notebook cell read/write, kernel state access, quant researcher workflow integration | High | jupyterlab, jupyter, notebook, quant-research, data-science-surface |
| `access/sox.md` | SOX (Sarbanes-Oxley) compliance for coding agent platforms — Section 302/404 implications, audit trail requirements for AI-assisted financial system code changes, change control integration, SOX-controlled repo classification | Medium | sox, sarbanes-oxley, financial-controls, audit-trail, financial-system-code |
| `access/finra-fca.md` | Financial services regulator-specific requirements beyond SEC — FINRA Rule 17a-4 nuances, FCA SYSC operational resilience, MAS TRM operational specifics | Low | finra, fca, mas-trm, broker-dealer, uk-financial-services, singapore-financial |

### Signals That Would Trigger These Gaps

- `sr-11-7`, `model-risk`, `mrm`, `occ`, `ai-model-validation` → `access/model-risk-management.md`
- `mnpi`, `trading-strategy`, `information-barriers`, `material-nonpublic` → `access/mnpi.md`
- `cyberark`, `pam`, `privileged-access-management`, `no-secrets-manager` → `gateway/cyberark-integration.md`
- `jupyterlab`, `jupyter-notebook`, `quant-research`, `data-science` → `surfaces/jupyterlab.md`
- `sox`, `sarbanes-oxley`, `financial-controls`, `sox-audit` → `access/sox.md`
- `finra`, `fca`, `mas-trm`, `broker-dealer` → extend `access/regional-compliance.md` with financial regulator section
