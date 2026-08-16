# Simulation: Siemens Energy — Federated Enterprise

## Customer Profile

| Attribute | Value |
|---|---|
| Company | Global industrial conglomerate (Siemens Energy scale) |
| Developers | ~25,000 across 7 semi-autonomous Business Units |
| HQ | Munich, Germany |
| BUs | Power Generation, Industrial Automation, Rail Transportation, Healthcare Devices, Defense Electronics (US subsidiary), R&D Labs, Corporate IT |
| Code domains | Java, Python, Embedded C, AUTOSAR C++, Verilog/SystemVerilog, COBOL (legacy billing) |
| IDEs | VS Code (web/cloud), Eclipse CDT (embedded/firmware), Synopsys GUI (chip design) |
| CI/CD | Jenkins (~60%), GitHub Actions (~40%) |
| SCM | GitHub Enterprise (corporate-wide) |
| Identity | Azure Entra (HQ + 4 BUs) + 3 legacy AD forests (post-acquisition) |
| Cloud | Azure (dominant), some BUs on AWS, Industrial Automation on GCP |
| Governance | German Betriebsrat + works councils in Netherlands, France, Austria |

---

## Advisor Discovery

**Advisor:** To design this platform I need to understand your governance model first. When you say "one platform" — do you mean one codebase and policy canon with BU-level configuration autonomy, or literally one shared AWS account that all BUs use?

**Customer (Head of Platform Engineering):** We want one governance model and one policy canon. Each BU can have their own configuration within that. We are not going to force every BU into the same AWS account — they have their own cloud footprints already.

**Advisor:** Good — that's a federated governance model with a hub-and-spoke topology. The central platform team owns the policy canon; BUs run instances that inherit from it. Before we go further: do any of your BUs work on defense-related hardware or firmware?

**Customer:** Yes — our Defense Electronics BU in the US was acquired two years ago. About 800 engineers. They build hardware firmware and HDL for military communications equipment.

**Advisor:** That almost certainly involves ITAR-controlled technical data. Before we design access to those repos, you need written guidance from your export control counsel on whether Amazon Bedrock in a commercial AWS region satisfies the ITAR inference boundary, or whether GovCloud is required. I'll flag this as an escalation item — we design that instance separately and the platform team in Munich cannot have access to it. Does the US subsidiary have its own AWS account today?

**Customer:** Yes, they're already in AWS GovCloud. They set that up themselves after the acquisition.

**Advisor:** Good — that simplifies things. We extend governance to their GovCloud instance rather than building a new one. Now, your works councils — have you engaged them on this project? Germany specifically has §87 BetrVG co-determination rights over technical monitoring systems.

**Customer (General Counsel's representative):** We haven't formally engaged the Betriebsrat yet. We know they blocked two prior tools — an activity monitoring tool and a code review analytics platform — because they felt those could be used for performance surveillance.

**Advisor:** Then we need to design for works council approval, not around it. The key question is whether the platform logs individual developer activity in a way that management can use for evaluation. If we design with team-level attribution from the start — no per-developer metrics in management dashboards, developer self-service only for their own data — we give the Betriebsrat a much stronger position to approve. We also have similar obligations in Netherlands, France, and Austria. What's the timeline pressure?

**Customer:** We want to be live in Germany and the US within 6 months. The Betriebsrat process alone could take 4-6 weeks minimum.

**Advisor:** Start that process now, in parallel with design. They should be reviewing a design document, not a finished system. Now — your Rail Transportation BU writes AUTOSAR C++ certified to ISO 26262 ASIL-D. Have you considered whether an AI agent should be writing code in safety-critical files?

**Customer (Rail BU representative):** We actually want the agent for documentation and code explanation, not code generation. Our safety engineers spend a lot of time understanding legacy AUTOSAR modules they didn't write.

**Advisor:** That's the right call. I'd recommend configuring Rail Transportation repos as read-only in the permission engine — agent can explain, document, and review, but cannot write. We'll also need a model capability evaluation for AUTOSAR C++ before deployment — frontier models have limited training data for AUTOSAR-specific patterns like timing budgets and ASIL decomposition.

**Customer:** What about Healthcare Devices? Similar situation — we have IEC 62304 Class C firmware.

**Advisor:** Same recommendation — model capability evaluation first, read-only by default, write access only after validation and only for non-safety-critical paths. Class C IEC 62304 requires formal change control anyway; any AI-suggested change needs to go through your validation process, so the agent should be generating proposals to the change control system, not committing directly.

**Customer:** Our R&D Labs write SystemVerilog for custom power management ASICs. They're very interested in piloting the agent. But they're worried about IP leakage — their designs are unreleased silicon.

**Advisor:** Two issues there. First, we need a model capability evaluation for SystemVerilog — this is a domain where we genuinely don't know how good frontier models are. Second, IP protection: the DLP rules on R&D Labs repos need to be stricter than standard. I'd recommend an innovation lab policy tier for R&D — full-featured, experimental capabilities enabled, but enhanced DLP that blocks responses containing chip architecture details from being logged in any form that could exit the boundary. We should also confirm that SystemVerilog files stay within a VPC endpoint — no public internet path for that inference.

**Customer:** The Industrial Automation BU is on GCP. They acquired a GCP-native company 18 months ago. Migration is "on the roadmap" but I'll be honest — it's not funded.

**Advisor:** Then we treat them as a permanent multi-cloud instance, not a temporary one. For Industrial Automation on GCP, I'd recommend deploying an OSS framework — Strands or LangChain — on Google Cloud Run or GKE, federated to the central identity broker, with OPA/Rego policy bundles pulled from the same canon server as every other instance. Governance parity without requiring a GCP → AWS migration.

**Customer:** What about Eclipse CDT? A large portion of our embedded developers use Eclipse, not VS Code. Does Claude Code support Eclipse?

**Advisor:** It doesn't — Claude Code's IDE integration covers VS Code and JetBrains. Eclipse CDT is a gap. The workaround is the Claude Code CLI, which works in any terminal. Embedded developers can run the CLI alongside Eclipse and interact with the agent from the terminal while the IDE handles compilation and debugging. It's not seamless but it's functional. JetBrains CLion is another option for C/C++ if you're willing to standardize embedded developers on that IDE over time.

**Customer:** Our China R&D center has about 400 engineers. They do software work — no ITAR. But we know China has data localization requirements.

**Advisor:** China PIPL and potentially MLPS require their session data and processed code to stay in China. Bedrock is not available in AWS China regions. The China instance needs to run on AWS China (SINNET/GCL) or Alibaba Cloud with a Chinese LLM provider — Alibaba Tongyi via DashScope is the most enterprise-ready option currently. LiteLLM as the model gateway abstracts the provider difference. Critically: no data path from the China instance to the global platform. Separate IdP connection, separate observability stack. The only shared element is the platform code.

**Customer:** That's five separate instances now. Our platform team has 12 engineers.

**Advisor:** That's manageable with the right federation governance. You need an OPA bundle server — an S3 bucket serving signed policy bundles — where every instance polls for updates. Policy changes deploy to all instances simultaneously. An instance registry in DynamoDB tracks what exists. AWS Config conformance packs on each spoke account detect drift. The central team governs the policy canon; BU owners handle instance operations with guardrails enforced from the center.

**Customer:** What's our cost exposure at 25,000 developers?

**Advisor:** With model tiering — Haiku for autocomplete, Sonnet for single-file edits, Opus only for complex multi-file tasks — you're looking at roughly $25–60 per developer per month depending on usage intensity, which is $625K–$1.5M/month. That's the ceiling. Per-session cost ceilings and monthly quotas per BU bring actual spend lower. You should build the cost model assuming 30–40% of developers are active on any given day in year one.

---

## Platform Blueprint

### Instance Topology

```
Central Platform Team (Munich) — Policy Canon + Identity Broker + Central SIEM
├── Policy Canon: OPA bundle server (S3 + CloudFront, signed bundles)
├── Identity Broker: AWS IAM Identity Center ← Okta orchestrator
│   ├── Upstream: Azure Entra (HQ + 4 BUs)
│   ├── Upstream: AD Forest 1 (Power Generation legacy)
│   ├── Upstream: AD Forest 2 (Rail Transportation legacy)
│   ├── Upstream: AD Forest 3 (Industrial Automation legacy)
│   └── Upstream: US GovCloud Okta (Defense Electronics — one-way, ITAR)
└── Central SIEM: Splunk / Security Lake (aggregates from all non-China instances)

Instance 1: Global Commercial (eu-central-1)
  BUs: Power Generation, Rail Transportation, Healthcare Devices, Corporate IT
  Harness: Claude Code (SaaS) for standard developers
  Execution: Claude Code IDE extension (VS Code) + CLI (Eclipse CDT users)
  Policy: Standard + Safety-Critical overlay (read-only for AUTOSAR/IEC 62304 repos)
  Model: Bedrock (Haiku/Sonnet/Opus tiered) via VPC endpoint
  Works council: EU-compliant attribution model (team-level only, no dev metrics)

Instance 2: R&D Labs (eu-west-1, isolated account)
  BU: R&D Labs (SystemVerilog, experimental AI research)
  Harness: Strands Agents (OSS) — innovation lab tier, experimental features
  Policy: Innovation lab tier; enhanced DLP for chip IP; capability eval required
  Model: Bedrock (Sonnet/Opus) — evaluated for SystemVerilog domain first

Instance 3: ITAR GovCloud (us-gov-east-1) — EXISTING
  BU: Defense Electronics (~800 engineers)
  Harness: Claude Code or Strands (evaluate current GovCloud availability)
  Policy: Maximum restriction — read-only for ITAR repos; US-person gate at session init
  Model: Bedrock GovCloud — verify model availability before committing
  Access: US persons only; Munich platform team has NO access to this instance

Instance 4: Industrial Automation (GCP — governance overlay)
  BU: Industrial Automation (~3,000 engineers)
  Harness: Strands Agents on Google Cloud Run
  Policy: OPA bundle pulled from central canon server; same Rego policies as Instance 1
  Model: Vertex AI (Gemini) or Bedrock via public endpoint — data residency assessment required
  Identity: GCP Workload Identity Federation → central IAM Identity Center broker

Instance 5: China (AWS China — Ningxia region)
  BU: China R&D Center (~400 engineers)
  Harness: LangChain on AWS China ECS
  Policy: Separate OPA bundle (subset of global canon, PIPL-compliant)
  Model: Alibaba Tongyi/DashScope via LiteLLM (Bedrock not available in AWS China)
  Identity: Separate China IdP — NO connection to global broker (PIPL compliance)
  Logging: Local-only; NOT exported to global SIEM
```

### Phase 1: Foundation — Global Commercial Instance (Months 1–3)

**Prerequisites before code:**
1. Engage Betriebsrat in Germany — present design document; begin Betriebsvereinbarung negotiation
2. Engage works councils in Netherlands, France, Austria — lighter obligation than Germany but required
3. Export control counsel: written determination on ITAR boundary for GovCloud instance
4. Privacy counsel: data processor agreement review for EU developer data processed through Bedrock

**Identity setup:**
- Deploy Okta Workforce Identity Cloud as the central orchestrator
- Configure Azure Entra federation into Okta (SAML/OIDC)
- Configure 3 legacy AD forests into Okta via LDAP sync + SAML
- Claim normalization: map `country`, `department`, `employeeType` from all 4 sources to consistent schema
- Federate Okta → AWS IAM Identity Center as external IdP
- IAM Identity Center permission sets: standard-developer, safety-critical-readonly, platform-admin
- MFA enforcement: required for all sessions; Okta Verify or hardware token

**Works council compliance (EU instance):**
- Attribution model: team-level only in all management-facing dashboards
- No per-developer session metrics visible to anyone except the developer themselves
- CloudWatch metrics: dimensions are `team`, `business_unit`, `repo_category` — no `developer_id`
- Developer self-service API: Lambda-backed endpoint returning own session history only
- S3 lifecycle rules: 13-month retention on session logs (Betriebsvereinbarung will specify exact period)
- Purpose limitation: separate log streams tagged `security-audit`, `cost-attribution`, `operations`

**Core platform:**
- Claude Code enterprise deployment (GitHub Enterprise SCM integration)
- MCP Gateway: AgentCore Gateway (allowlist-enforced tool routing)
- Tool allowlist: GitHub (read + PR creation), Jira (read + comment), file edit tools, test runners
- Model tiering: Haiku (autocomplete, T1), Sonnet (file edits, T2), Opus (multi-file refactors, T3)
- Per-session cost ceiling: €2 soft / €5 hard
- Monthly BU quota: set by BU platform owner, enforced via DynamoDB atomic counter
- Bedrock via VPC endpoint (eu-central-1): no public internet path for inference

**Safety-critical repo configuration:**
- Repo topic `safety-critical-asil` (Rail AUTOSAR) and `safety-critical-iec62304` (Healthcare)
- Session init Lambda checks topic; removes write tools from allowlist if present
- Agent can: read files, explain code, generate documentation, review for defects
- Agent cannot: edit files, create branches, commit, create PRs on safety-critical repos
- Model capability evaluation for AUTOSAR C++ and IEC 62304 C: required before deployment

### Phase 2: Specialized Instances (Months 3–5)

**R&D Labs instance:**
- Innovation lab policy tier: experimental features enabled, broader tool access
- Model capability evaluation: run 6-step evaluation on SystemVerilog corpus before developer access
- DLP configuration: Bedrock Guardrails with custom regex for ASIC IP markers (part numbers, process node identifiers, unreleased product codenames)
- Chip IP classification: repos tagged `chip-ip-unreleased`; enhanced DLP active
- Separate AWS account (eu-west-1); cross-account federation from central broker
- Strands Agents OSS framework (more configurability than Claude Code SaaS for experimental use)

**GovCloud extension:**
- Platform team contacts Defense Electronics BU; map existing GovCloud setup to platform canon
- Deploy OPA sidecar in GovCloud receiving bundles from a GovCloud-resident bundle server (cannot pull from eu-central-1 bundle server — ITAR boundary)
- US-person gate: Lambda authorizer queries HR API for `usPersonStatus` attribute at session init
- Repo classification: ITAR topics on GitHub Enterprise; session init Lambda blocks ITAR repos if US-person check fails
- All ITAR logs: remain in GovCloud; NOT exported to Splunk in Europe
- Munich platform team: no IAM roles, no cross-account access, no log access to this instance

**Industrial Automation GCP overlay:**
- Deploy Strands Agents on Google Cloud Run (serverless containers)
- OPA policy bundle fetched from central S3 bundle server at startup (or GCS mirror if Direct Peering preferred)
- GCP Workload Identity Federation for AWS resource access (pulls bundle from S3 without static keys)
- Identity: GCP IAM federation → Okta → central broker; developer login is their corporate Okta credential
- Model: evaluate Vertex AI Gemini for GCP-native latency; Bedrock via internet endpoint as alternative (assess data residency implications)
- Observability: GCP Cloud Logging → Pub/Sub → Dataflow → central Splunk (or Security Lake via GCS export)

### Phase 3: China Instance + Full Rollout (Months 5–6)

**China instance:**
- AWS China (Ningxia region) account — separate AWS account, separate credentials
- Separate IdP: China-specific Azure Entra tenant or Active Directory; NO connection to global Okta
- Alibaba DashScope API (Tongyi Qianwen) fronted by LiteLLM; deployed on ECS in Ningxia
- OPA bundle: a China-specific subset of the global canon, without ITAR/EAR rules (not applicable)
- Observability: local CloudWatch in Ningxia only; NOT exported outside China
- MLPS Level 2 assessment: work with AWS China (SINNET) on MLPS filing requirements

**Full BU rollout:**
- Corporate IT: standard commercial instance, no restrictions
- Power Generation: standard + safety-critical read-only for nuclear control system code subset
- Rail Transportation: read-only for AUTOSAR repos (pending capability evaluation results)
- Healthcare Devices: read-only for IEC 62304 Class C repos (pending capability evaluation results)
- Industrial Automation: GCP overlay instance
- R&D Labs: innovation lab instance (SystemVerilog eval complete before activation)
- Defense Electronics: GovCloud instance (ITAR counsel determination complete)
- China R&D: China instance

### Key Tradeoffs Accepted

| Decision | Choice | Rationale |
|---|---|---|
| Eclipse CDT gap | CLI workaround, not native IDE integration | No Eclipse plugin exists; CLI is functional for terminal-comfortable embedded developers |
| GCP instance on OSS framework | Strands on Cloud Run, not Claude Code | Claude Code SaaS has no GCP-native deployment; OSS framework gives governance parity |
| China LLM provider | Alibaba Tongyi, not Claude | Bedrock not available in AWS China; Tongyi is the most enterprise-ready option |
| Safety-critical repos | Read-only by default | Model capability unproven for AUTOSAR/IEC 62304; write access after evaluation only |
| Works council timeline | Start engagement immediately | Cannot deploy EU instance to developers without Betriebsvereinbarung; parallel workstream |
| GovCloud instance independence | Munich team has zero access | ITAR boundary requirement; not a governance preference |

### Escalations to Legal / Compliance

1. **ITAR counsel:** Written determination — does Bedrock GovCloud satisfy ITAR inference boundary for Defense Electronics firmware?
2. **Export control counsel:** EAR assessment for any dual-use software in Power Generation and Industrial Automation
3. **Employment law — Germany:** Betriebsvereinbarung text specifying permitted uses, data collected, retention periods, access controls
4. **Employment law — Netherlands, France, Austria:** Jurisdiction-specific assessment of co-determination obligations
5. **Privacy counsel — EU:** Data processor agreement with AWS for EU developer personal data; Transfer Impact Assessment for EU → US data flows (if any)
6. **Privacy counsel — China:** PIPL assessment; MLPS level determination for China R&D instance

### Platform Best Practices

- **Resilience:** AWS SDK adaptive retry (adaptive mode) on all Bedrock calls; circuit-breaker per MCP server instance; single MCP server failure does not terminate session
- **Credential hygiene:** All credentials injected via AgentCore Identity or Vault integration; no static API keys in code or environment variables; truffleHog scan on every commit to platform repos
- **Change safety:** Auto-branch creation enabled by default; no direct commits to main; idle session timeout 30 minutes
- **Context discipline:** CLAUDE.md token budget reviewed quarterly; compaction checkpoint at 70% context utilization
- **Supply chain:** Pin MCP server versions in the allowlist; quarterly review of pinned versions; AWS Signer for container image signing
- **Policy bundle integrity:** All OPA bundles signed; instance OPA sidecars verify signature before applying; unsigned bundle = alert + rollback to previous version

### Org Readiness Flags

| Dimension | What's needed | Owner |
|---|---|---|
| Developer upskilling | Prompt engineering for domain-specific code (AUTOSAR, IEC 62304); 2-day workshop per BU | BU Learning & Development |
| Works council engagement | Betriebsrat presentation + Betriebsvereinbarung negotiation | HR Legal + Platform Team |
| Safety engineering process | Update change control procedure to classify AI-suggested changes; ASIL determination for AI outputs | Rail/Healthcare Safety Teams |
| Model capability evaluation | Run eval for AUTOSAR, IEC 62304, SystemVerilog before enabling those populations | Platform Team + Domain Experts |
| China operations | Identify local platform admin (PIPL requires China-resident data controller) | China Engineering Leadership |
| ITAR access roster | Maintain current US-person roster in HR system for GovCloud session gate | Defense Electronics HR |

---

## Post-Simulation Advisor Notes

### What the Advisor Handled Well

- **Federation model:** Hub-and-spoke topology with OPA policy canon, instance registry, and drift detection was the correct architecture for a 25K-developer organization with 7 BUs. The pattern from `ops/federation.md` applied cleanly.
- **Works council proactive surfacing:** Raised Betriebsrat before the customer did; correctly identified attribution model (team-level only) as the design lever for works council approval. Grounded in `access/regional-compliance.md`.
- **ITAR separation:** Correctly identified GovCloud as the boundary requirement and enforced zero-access for the Munich team. Grounded in `access/export-control.md`.
- **Safety-critical read-only:** Correctly defaulted AUTOSAR and IEC 62304 repos to read-only pending capability evaluation. Grounded in `quality/model-capability-eval.md`.
- **China isolation:** Correctly identified PIPL/MLPS requirements and recommended complete isolation from the global platform, including separate IdP and separate observability stack. Grounded in `access/data-jurisdiction.md`.
- **Eclipse CDT gap acknowledgment:** Correctly identified Claude Code's IDE surface limitation and recommended CLI workaround rather than overselling.
- **Cost model:** Proactively surfaced the €625K–€1.5M/month range with mitigation (tiering + quotas).

### What Stretched the Knowledge Base

- **GCP multi-cloud execution:** The multi-cloud governance node covers OPA policy parity but doesn't detail GCP-specific deployment (Cloud Run, Workload Identity Federation, Pub/Sub log export). Some advisor responses were high-level here.
- **Synopsys EDA tool integration:** The chip design team uses Synopsys Design Compiler. No MCP server for EDA tools exists in the current OKF — the advisor could only say "the agent works alongside the tool" without a concrete integration pattern.
- **AUTOSAR-specific model evaluation:** The model capability eval framework applies generically; it doesn't have AUTOSAR-specific evaluation criteria (timing budget analysis, ASIL decomposition, RTE configuration review). A domain expert would need to design the evaluation dataset.
- **MLPS Level determination:** The advisor flagged MLPS but couldn't specify whether the China instance requires Level 2 or Level 3 filing — this is determined by data sensitivity and system criticality, which requires a China-specific assessment.

### OKF Gaps Identified

| Gap Name | Description | Priority | Trigger Signals |
|---|---|---|---|
| `exec/gcp-runner.md` | GCP-specific deployment patterns for OSS agent frameworks: Cloud Run configuration, Workload Identity Federation for AWS resource access, Pub/Sub log export pipeline | Medium | gcp, google-cloud, gcp-acquisition, cloud-run |
| `quality/safety-critical-eval.md` | Domain-specific capability evaluation criteria for safety-critical code (AUTOSAR, IEC 62304, DO-178C) — not just generic eval framework but specific test case patterns, pass/fail criteria, and human evaluator roles for safety domains | High | autosar, iec-62304, do-178c, asil, safety-critical-code, functional-safety |
| `gateway/eda-integration.md` | MCP tool integration patterns for EDA toolchains (Synopsys, Cadence, Mentor) — how agents interact with design compiler, waveform viewers, FPGA synthesis tools without IDE plugin support | Low | eda-tools, synopsys, cadence, fpga, asic, chip-design-toolchain |
| `access/mlps.md` or extend `data-jurisdiction.md` | China MLPS Level 2/3 determination framework — what platform design choices affect MLPS level; AWS China SINNET filing process; Level 2 vs Level 3 security baseline differences | Medium | china, mlps, aws-china, china-compliance |
| `ops/cost-model-enterprise.md` | Structured cost modeling methodology for large deployments — tiered model usage assumptions, active developer percentage, BU quota allocation methodology, finance approval process | Medium | cost-model, budget-approval, enterprise-cost, 10000-developers |

### Signals That Would Trigger These Gaps

- `gcp`, `google-cloud`, `gcp-acquisition`, `cloud-run` → `exec/gcp-runner.md`
- `autosar`, `iec-62304`, `asil`, `functional-safety`, `safety-critical-code` → `quality/safety-critical-eval.md`
- `synopsys`, `cadence`, `eda-tools`, `fpga-synthesis`, `asic` → `gateway/eda-integration.md`
- `china`, `mlps`, `aws-china`, `china-compliance` → extend `access/data-jurisdiction.md` with MLPS section
- `cost-model`, `budget-approval`, `25000-developers`, `enterprise-cost` → `ops/cost-model-enterprise.md`
