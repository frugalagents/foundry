# Simulation: Apex Retail Group — Standard Enterprise (v4)

**Simulated date:** 2026-08-15
**Scenario type:** Standard enterprise — no exotic regulatory requirements, no federation,
no safety-critical code. Representative of a large majority of enterprise customers.
**OKF version:** 66 nodes
**Skill version:** v4 — fixes: no architecture duplication, best practices as appendix,
cost comparison at equivalent adoption rates

---

## Customer Profile

**Apex Retail Group** — US-headquartered omnichannel retailer. $12B revenue. NYSE-listed.

- **Developers:** ~3,800 (Product Eng, Platform, Data Eng, Data Science, QA, Enterprise Systems)
- **Cloud:** AWS primary — us-east-1, eu-west-1, ap-southeast-2
- **SCM / CI:** GitHub Enterprise Cloud + GitHub Actions
- **Identity:** Okta Workforce Identity + SCIM (live)
- **Compliance:** SOC 2 Type II, PCI DSS Level 1, SOX, GDPR (EU ops)

## Judge Expectations

```json
{
  "required_stage": "blueprint",
  "required_confidence": "high",
  "require_architecture": true,
  "require_blueprint": true,
  "max_open_questions": 0,
  "must_address": [
    "Okta",
    "SOX",
    "PCI",
    "data science",
    "30/90/180 rollout"
  ]
}
```

---

## Discovery Conversation

### Phase 0: Opening

**Advisor:** Tell me what's bringing you here. Are you starting from scratch,
evaluating a shortlist, or trying to figure out what to do with something already
partially deployed?

**Rachel Kim (CTO):** Partially deployed, messily. We have a GitHub Copilot
enterprise license — about 30% adoption. Some teams are using personal Claude.ai
accounts, and our data science team built something using a shared OpenAI API key
that one of the engineers set up. Security is unhappy. We want to consolidate on
something governed and roll it out properly.

**Advisor:** The shared OpenAI key is the most immediate risk in that picture.
A shared key has no DLP, no per-user audit trail, and no rate limit. If someone
on that team pastes PCI code into a prompt today, there's no record of it and
no way to know after the fact. That's what the platform needs to close first —
everything else is improvement on top.

Before I show you the architecture: the 30% Copilot adoption — do you know why
it's only 30%? That number changes how I'd design the rollout. Low adoption
usually comes from one of three places: friction getting started, skepticism
about output quality, or managers not making it a priority. Each has a
different fix and I don't want to design around the wrong one.

**Rachel:** Honest answer — both of the first two. The Copilot setup process was
painful, a lot of developers gave up during onboarding. And our senior engineers
are skeptical. They tried it on complex code and weren't impressed.

**Advisor:** That's useful — and it means the fix is specific. Low-friction
onboarding is a design requirement, not a nice-to-have: SSO-based activation
where a developer installs the extension, signs in once with their Okta
credentials, and it works. No separate account, no API key to configure.
That directly solves the dropout problem.

On the quality skepticism: that's a pilot population problem. If we launch with
developers who are already enthusiastic, the skeptics never get converted. We
need senior engineers in the pilot — not as guinea pigs but as quality validators.
When they publicly say "this is better," the remaining 70% have no credible
objection. We can design the pilot around that.

*[Inferences locked: brownfield, shared key = primary immediate risk, adoption
failure = friction + trust not awareness, rollout must address both explicitly.
3,800 developers, enterprise profile.]*

---

### Phase 0.5: Baseline Architecture

> "Here's the starting architecture — I've included JupyterLab alongside the
> IDE because your data scientists clearly won't leave their notebooks, and
> leaving them on the shared key defeats the purpose. Tell me what's wrong
> with it."

```
Developer (3,800 engineers — brownfield, onboarding friction addressed)
  └── Surface:   IDE (VS Code / JetBrains) — Claude Code, SSO activation
                 JupyterLab sidebar — Jupyter MCP server (data science team)
  └── Harness:   AgentCore managed runtime
  └── Execution: ECS Fargate, ephemeral per-session
  └── Gateway:   GitHub + Jira MCP servers; platform-approved allowlist
  └── Model:     Haiku 4.5 (completions) + Sonnet 4.6 (agentic)
  └── Ops:       Immutable audit trail → SIEM; per-team chargeback
  └── Access:    Okta SSO → IAM Identity Center; compliance overlays TBD
```

**Marcus Webb (CISO):** I need to understand what happens with PCI repos. Our
payment processing code — I'm not comfortable with it going to any model without
understanding exactly what the controls are.

**Rachel:** Do we need JupyterLab from day one? Our data scientists have been
getting by.

**Advisor:** On JupyterLab — "getting by" means the shared OpenAI key. If we
launch without JupyterLab, that team stays on the unaudited key. The shadow-IT
problem you want to solve doesn't get solved for 200 of your developers. Launch
it in read-only mode initially — the agent can read notebooks and explain code
but doesn't write anything. That gives you a governed path from day one without
the risk of autonomous cell execution before we've established trust.

On PCI: the design principle is to deny access at the session layer, before the
agent sees anything. By the time a developer is trying to commit PCI code, you've
already lost control of what was sent to the model. With session-layer enforcement,
a developer without PCI clearance simply can't open those repos in their agent
context — they're not in the tool list at all. Marcus, the question I need you
to take to your QSA before Phase 2: does AI-assisted code suggestion on PCI repos
require notification or changes to your ROC? That's not a platform decision, and
I don't want you to get to Phase 2 and find that answer is yes.

*[JupyterLab justified and accepted. PCI principle stated. QSA escalation
surfaced immediately as a Phase 2 blocker.]*

---

### Phase 1: Current Stance

**Advisor:** Three quick confirmations so I stop carrying assumptions:
1. GitHub Enterprise + GitHub Actions — any other SCM or CI systems?
2. Okta + SCIM to GitHub — live today, or something we're enabling?
3. Bedrock agreement — do you have one, or does that need to be procured?

**Rachel:** GitHub only. Okta + SCIM is live. No Bedrock agreement yet —
we're AWS-heavy, that's the natural path.

**Architecture update — Phase 1:**
```
Developer (3,800 engineers)
  └── Surface:   IDE (Claude Code, SSO) + JupyterLab sidebar
  └── Harness:   AgentCore managed runtime                      ← leaning
  └── Execution: ECS Fargate, ephemeral — us-east-1 primary
  └── Gateway:   GitHub Enterprise + Jira MCP servers; Secrets Manager
  └── Model:     Haiku 4.5 (completions) + Sonnet 4.6 (agentic)
  └── Ops:       CloudWatch → Splunk (existing SIEM)            ← UPDATED
  └── Access:    Okta + SCIM (live) → IAM Identity Center       ← UPDATED
```

---

### Phase 2: Constraint Scan

**Advisor:** Constraints force decisions rather than inform them — I want to
confirm these before we go further:

1. PCI — Marcus mentioned 15 repos. Do engineers rotate between PCI and
   non-PCI repos, or is it a distinct team?
2. SOX — you're NYSE-listed. Which systems are in scope?
3. EU presence — teams in Germany or other EU countries with works councils?
4. Multi-file autonomy — agent proposes a plan first, or autonomous within guardrails?

**Marcus:** PCI — engineers do rotate. I need session-level isolation, not
just controls at merge time.

**Rachel:** SOX — yes, ERP integrations and our financial reporting pipelines.
Internal audit owns the scope list, about 22 repos.

**Tobias Brandt (Head of Engineering, EU):** 150 developers in Berlin. Active
Betriebsrat. We had a dispute two years ago — a metrics tool that tracked
per-developer output. Works council blocked it. Individual-level data is off
the table without a Betriebsvereinbarung, and that's a 4-6 month process.

**Rachel:** Autonomy — plan and approval for multi-file changes. Inline single
file is fine to show automatically.

**Advisor:** Tobias — the platform is designed for team-level attribution only.
No individual developer metrics anywhere in the ops stack. That's how we stay
out of §87 BetrVG territory. But you still need the Betriebsvereinbarung to
cover the deployment for German employees, regardless of how the metrics are
structured. Who owns the works council engagement?

**Tobias:** HR Legal. I can start that.

**Advisor:** Start it this week. That process can't be accelerated and it's on
the critical path for the EU instance. The platform build can run in parallel —
just don't wait to kick it off.

*[PCI: session-layer isolation confirmed. SOX: 22 repos, change management
+ WORM. GDPR + §87 BetrVG: team-level only, Betriebsvereinbarung must start now.
Autonomy: plan-then-approve for multi-file.]*

---

### Phase 3: Goals and Success

**Advisor:** Two questions:
1. Primary driver?
2. What does success look like in 12 months that you could put in front of
   your board?

**Rachel:** Primary: get everyone off personal accounts — one governed platform,
measurably within 90 days of launch. Secondary: data engineering productivity.
That team spends 40% of their time on boilerplate dbt and Spark transforms.

**Success:** Shadow-IT gone — visible in Okta, no more Claude.ai or OpenAI
expense reports from engineering. Data engineering PR throughput up 20%.

**Advisor:** The Okta SSO signal is the cleanest proxy you have for shadow-IT
elimination — you can see it today without any new instrumentation. Zero personal
AI account SSO sessions from the pilot population by week 8. That's your pilot
exit criterion and it's a metric you can take directly to your board.

---

### Phase 3.5: Harness Selection

**Advisor:** One foundational question — your platform team size, and do they
want to own the agent loop or build governance on top of something managed?

**Sam Torres (Platform Lead):** 8 engineers. We don't want to maintain an
orchestration framework. We'll build the governance layer — auth, policy,
audit routing — on top of something that handles the agent loop.

**Advisor:** AgentCore. Strands and LangChain give you more control but they
mean version upgrades, security patches, and framework bugs become your team's
problem. With 8 engineers who also need to own a Lambda authorizer, OPA policy
bundle, and audit pipeline, there's no capacity for that. AgentCore handles
session lifecycle, tool routing, and MCP protocol. Your team builds roughly
500 lines of governance layer on top. That's the right split for your size.

**Architecture update — Phase 3.5:**
```
Developer (3,800 engineers)
  └── Surface:   IDE (Claude Code, SSO) + JupyterLab sidebar
  └── Harness:   Amazon Bedrock AgentCore Runtime (managed)     ← CONFIRMED
  └── Execution: ECS Fargate (standard) + JupyterHub EKS sidecar (DS team)
  └── Gateway:   GitHub Enterprise + Jira MCP servers; Secrets Manager
  └── Model:     Haiku 4.5 (completions) + Sonnet 4.6 (agentic)
  └── Ops:       CloudWatch → Datadog (APM) + Splunk (SIEM)     ← UPDATED
  └── Access:    Okta + SCIM → IAM Identity Center; overlays TBD
```

---

### Phase 4: Key Architecture Decisions

**Surfaces:**
IDE via Claude Code enterprise extension — SSO activation, no manual API key
setup. Directly fixes the Copilot onboarding dropout.

JupyterLab via Jupyter MCP server sidecar in JupyterHub pods — phased by
capability not by calendar:
- **Read-only at pilot:** agent reads cells, explains code, suggests in the
  chat panel but doesn't write. The reason: data science notebooks often contain
  in-memory dataframes with loyalty member PII. Read-only is reversible. A PII
  leak isn't. We observe what's actually in those notebooks during Phase 1 before
  granting write access.
- **Read + write cells after Phase 1 review:** agent proposes and writes cell
  content, developer reviews and executes.
- **Cell execution in Phase 2:** evaluate based on Phase 1 behavior, not assumption.

**Execution:**
ECS Fargate for standard sessions — right-sized, ephemeral, no idle cost.
No microVM needed here. PCI isolation is a session policy problem, not a
hardware isolation problem. The session tag gates access before the agent
sees anything. Adding Firecracker overhead for a policy control would be
over-engineering.

**Credentials:**
AWS Secrets Manager — you're AWS-native, no Vault, no CyberArk in your stack.
GitHub PAT and Jira token stored and auto-rotated. PCI sessions get separate
Secrets Manager ARNs, accessible only when `pci_access` session tag is present.

**PCI:**
Session-layer allowlist gate: developers without `pci_access=true` cannot open
PCI repos in their agent context — removed from the tool list at session init,
not blocked at merge. For developers with PCI access: read and suggest only,
no agent-direct commit path. Bedrock Guardrails DLP catches PAN and CVV patterns
in prompts. Blocked prompts are not logged — a log of a blocked PCI prompt is
itself a PCI data record and creates the problem we're trying to avoid.

**SOX:**
The highest-value use case on SOX repos isn't code generation, it's comprehension.
David Park's enterprise systems team has 15-year-old ERP integration code that
nobody fully understands. The agent can read and explain that code from day one
without any change management requirement. For suggestions: every change requires
a Jira ticket in Approved state and two reviewers. The developer who prompted
cannot self-approve — GitHub branch protection enforces that. Session logs:
S3 Object Lock Compliance, 7-year retention.

**GDPR + §87 BetrVG:**
`developer_id` is prohibited as a CloudWatch metric dimension on the EU instance —
all metrics are `team_id` and `business_unit` only. This is the technical
implementation of the Betriebsvereinbarung, not a workaround. EU session logs
stay in eu-west-1, no replication to us-east-1. Individual session data is
visible only to the developer themselves and security for incident review — not
accessible to managers or business analytics.

**Final architecture:**
```
Developer (3,800 engineers — Product, Platform, Data Eng, Data Science, QA, Enterprise Sys)
  └── Surface:   VS Code / JetBrains — Claude Code enterprise extension (SSO, zero config)
                 JupyterLab sidebar — Jupyter MCP server sidecar (200 data scientists)
  └── Harness:   Amazon Bedrock AgentCore Runtime (managed)
                 Platform team builds: Lambda authorizer + OPA policy + audit routing (~500 lines)
  └── Execution: ECS Fargate, ephemeral per-session — us-east-1 / eu-west-1 / ap-southeast-2
                 JupyterHub on EKS (Zero to JupyterHub), data science team only
  └── Gateway:   GitHub Enterprise MCP server (read + PR create)
                 Jira MCP server (read + comment)
                 Secrets Manager: GitHub PAT + Jira token (auto-rotated)
                 PCI-scoped ARNs gated on pci_access session tag
  └── Model:     Claude Haiku 4.5 — inline completions, short Q&A (~40% of volume)
                 Claude Sonnet 4.6 — agentic sessions, code review, refactoring
                 Bedrock Guardrails — PAN/CVV DLP active on all sessions
  └── Ops:       CloudWatch → Datadog (APM) + Splunk (SIEM via Kinesis Firehose)
                 S3 Object Lock Compliance — SOX-scoped sessions, 7-year retention
                 Per-BU token consumption → monthly chargeback report
  └── Access:    Okta + SCIM → IAM Identity Center session tags:
                   pci_access | eu_developer | cost_center | business_unit
                 [PCI]  Session-layer allowlist gate + Guardrails DLP (blocked prompts not logged)
                 [SOX]  Jira change ticket + two-reviewer SOD + WORM audit
                 [GDPR] Team-level-only metrics + eu-west-1 data residency
```

---

## Platform Blueprint — Apex Retail Group

*2026-08-15 · Enterprise profile · AgentCore managed runtime*

---

### Architecture

Architecture as agreed during discovery:

```
Developer (3,800 engineers — Product, Platform, Data Eng, Data Science, QA, Enterprise Sys)
  └── Surface:   VS Code / JetBrains — Claude Code enterprise extension (SSO, zero config)
                 JupyterLab sidebar — Jupyter MCP server sidecar (200 data scientists)
  └── Harness:   Amazon Bedrock AgentCore Runtime (managed)
                 Platform team builds: Lambda authorizer + OPA policy + audit routing (~500 lines)
  └── Execution: ECS Fargate, ephemeral per-session — us-east-1 / eu-west-1 / ap-southeast-2
                 JupyterHub on EKS, data science team only
  └── Gateway:   GitHub Enterprise MCP server (read + PR create)
                 Jira MCP server (read + comment)
                 Secrets Manager: GitHub PAT + Jira token (auto-rotated)
                 PCI-scoped ARNs gated on pci_access session tag
  └── Model:     Claude Haiku 4.5 — inline completions (~40% of volume)
                 Claude Sonnet 4.6 — agentic sessions, code review, refactoring
                 Bedrock Guardrails — PAN/CVV DLP on all sessions
  └── Ops:       CloudWatch → Datadog (APM) + Splunk (SIEM via Kinesis Firehose)
                 S3 Object Lock Compliance — SOX-scoped sessions, 7-year retention
                 Per-BU token consumption → monthly chargeback
  └── Access:    Okta + SCIM → IAM Identity Center session tags:
                   pci_access | eu_developer | cost_center | business_unit
                 [PCI]  Session-layer allowlist gate + Guardrails DLP
                 [SOX]  Jira change ticket + two-reviewer SOD + WORM audit
                 [GDPR] Team-level-only metrics + eu-west-1 data residency
```

A backend engineer installs the Claude Code extension in VS Code, signs in with
their Okta credentials once, and it connects — no API key, no separate account.
The agent reads their current repo and responds to questions, reviews code,
suggests refactors, and writes tests. For anything touching multiple files it
shows a plan first and waits for their approval. Senior engineers who found
Copilot underwhelming on complex code will find Sonnet materially better —
that's the quality signal that converts the skeptics. For Priya's data science
team, the same agent is available inside JupyterLab without leaving the notebook.
The shared OpenAI key goes away because this is governed, auditable, and works
as well or better in the environment they're already in.

---

### Compliance Overlay

**PCI DSS — 15 repos:**
The design principle is session-layer denial, not merge-layer. Developers
without PCI clearance cannot open those repos in their agent context at all —
they're removed from the tool list at session init. No prompt is ever sent.
Developers with PCI access get read and suggest only; no agent-direct commit
path. Bedrock Guardrails catches PAN and CVV patterns in prompts; blocked
prompts are not logged (a logged PCI prompt is itself a PCI data record).
DLP events go to Splunk. PCI session logs in a separate S3 bucket, KMS CMK,
security team access only.

**SOX — 22 repos (ERP integrations, financial reporting pipelines):**
Best use case is comprehension, not generation. David Park's team can use the
agent to understand legacy ERP code from day one with no change management
requirement. For any code suggestion: Jira change ticket in Approved state
plus two reviewers, prompting developer cannot self-approve (GitHub branch
protection). Session logs: S3 Object Lock Compliance, 7-year retention,
scoped read-only IAM role for external auditor access during annual audit.

**GDPR + §87 BetrVG — 150 developers, eu-west-1:**
`developer_id` is never a CloudWatch metric dimension on the EU instance.
All metrics are `team_id` and `business_unit`. This is the technical control
that keeps the platform out of §87 BetrVG scope. Session logs stay in eu-west-1,
no replication to us-east-1. Individual session data is visible only to the
developer themselves and security for incident review — not to managers.
Betriebsvereinbarung must be started this week; it governs the deployment, not
just the metrics configuration.

---

### Architecture Decisions

| Layer | Decision | Alternatives Considered | Reasoning |
|---|---|---|---|
| Surfaces | Claude Code (SSO activation) + Jupyter MCP sidecar | GitHub Copilot (existing), Cursor Enterprise | Copilot dropout was the stated failure mode — SSO zero-config directly fixes it. Cursor has no JupyterLab integration. Claude Code + Jupyter sidecar covers both populations with one platform. |
| Harness | AgentCore managed runtime | Strands / LangChain OSS, SaaS-only product | 8-person team, governance layer is their value-add. OSS framework maintenance not absorb-able. SaaS-only can't satisfy PCI/SOX audit evidence requirements. |
| Execution | ECS Fargate + EKS JupyterHub sidecar | microVM (Firecracker), Lambda | PCI isolation is a session policy control, not a hardware isolation problem. microVM adds operational overhead the platform team can't absorb. Lambda cold start breaks multi-step agentic sessions. |
| MCP tools | GitHub Enterprise + Jira; strict allowlist | Self-service catalog | Shadow-IT risk from ungoverned MCP servers on day one. Strict allowlist at launch, expand after adoption baseline is established. |
| Credentials | AWS Secrets Manager | HashiCorp Vault, CyberArk | No Vault or CyberArk in the environment. Secrets Manager is native, auto-rotates, no additional infrastructure. |
| Model gateway | Bedrock in-region (us-east-1 + eu-west-1) | Anthropic API direct, Vertex AI | AWS-native billing + audit log. In-region inference satisfies GDPR data residency. No separate Anthropic contract needed. |
| Model tiering | Haiku 4.5 (completions) + Sonnet 4.6 (agentic) | Sonnet only | ~40% cost reduction on high-volume completion tasks. Sonnet reserved for context-heavy work where quality is visible to the senior engineers we need to convert. |
| Observability | CloudWatch → Datadog + Splunk | CloudWatch only | Datadog is existing APM. Splunk is existing SIEM. Platform integrates into what security already monitors — no new tooling, no new log destination to govern. |
| EU metrics | team_id + business_unit only; developer_id prohibited | Per-developer metrics | §87 BetrVG compliance. Technical constraint, not a design choice. |
| JupyterLab capability | Read-only at pilot → write after Phase 1 review → execution in Phase 2 | Full capability day one | Notebook outputs can contain loyalty member PII. Read-only is reversible. Observe actual notebook content in Phase 1 before granting write, then execution. |

---

### Rollout Phases

**Phase 1 — Pilot (weeks 1–8, 200 developers):**
- Population: 50 senior backend engineers (the trust problem came from this group —
  they need to be first, not last), 50 data engineers, 50 data scientists
  (JupyterLab read-only), 50 platform engineers
- Capabilities: IDE read + suggest; JupyterLab read-only; no PCI repo access yet
- Exit criteria:
  - >60% weekly active usage in pilot population by week 6
  - Zero Claude.ai / ChatGPT SSO sessions from pilot population by week 8 (Okta)
  - SOX audit trail format confirmed acceptable by internal audit
  - Zero DLP incidents involving PCI patterns
- What Phase 1 must prove before Phase 2 unlocks: senior engineers publicly
  validate quality (the conversion event for the remaining 70%), JupyterLab
  read-only behavior reviewed for PII risk

**Phase 2 — BU Rollout (months 3–6, 1,500 developers):**
- PCI-scoped access enabled for `pci_access=true` developers
  *(requires QSA confirmation — Marcus starts this conversation now)*
- GitHub Actions CI code review bot live
- JupyterLab read+write cells enabled (Phase 1 notebook content review complete)
- SOX change ticket CI enforcement live
- EU instance live *(requires Betriebsvereinbarung — Tobias starts this week)*

**Phase 3 — Full Enterprise (months 7–12, 3,800 developers):**
- All BUs onboarded; per-BU chargeback active
- Code intelligence RAG over internal libraries (data engineering priority)
- JupyterLab cell execution evaluated based on Phase 2 behavior
- Copilot license retired
- Model capability evaluation on data engineering domain tasks

---

### Key Tradeoffs Accepted

- **ECS Fargate over microVM** — PCI requirements here are satisfied by
  session-layer policy controls. The 8-person platform team can't operate
  Firecracker. Revisit only if a genuine multi-tenant hardware isolation
  requirement emerges from the QSA conversation.
- **No code intelligence RAG at launch** — Bedrock Knowledge Bases over Apex's
  internal codebase would improve quality significantly for data engineering and
  the enterprise systems team. Deferred to Phase 3 to ship governed access first.
  This is the right call: quality improvement on top of an untrusted platform
  doesn't build trust; quality improvement on top of a working platform does.
- **JupyterLab read-only at pilot** — execution is the most powerful and most
  risky mode. PII in notebook outputs is not hypothetical for a loyalty program
  with member data. Earn execution capability based on observed behavior rather
  than assumption.
- **Senior engineers in the pilot, not enthusiasts** — costs political capital
  but it's the necessary investment. The 70% non-adopters need to hear from the
  people they trust, not from the people who were going to adopt anyway.

---

### Escalations Required Before Build

These are not platform team decisions. Each one blocks a specific phase.
Neither of the first two can be accelerated once started — they need to start now.

| Item | Determination needed | Blocks | Owner | Start |
|---|---|---|---|---|
| PCI QSA confirmation | Does AI-assisted code suggestion on PCI repos require ROC changes or QSA notification? | Phase 2 PCI access | Marcus Webb + external QSA | This week |
| Betriebsvereinbarung | Works council agreement for Berlin team covering this deployment model | EU instance launch | Tobias Brandt + HR Legal | This week |
| SOX ITGC scope | Internal audit confirms session logs satisfy ITGC evidence requirements for Deloitte | Phase 2 SOX enforcement | Internal Audit + Deloitte | Can run during Phase 1 |
| AWS GDPR DPA | Data Processing Agreement for Bedrock inference touching EU personal data | EU instance launch | Privacy / Legal | Before eu-west-1 deploy |

---

### Org Readiness — Non-Platform Actions

| Dimension | What's needed | Owner | When |
|---|---|---|---|
| Senior engineer briefing | Brief the 50 pilot senior engineers before launch — they need to understand they're the quality validators, not guinea pigs. This is Rachel's conversation, not Sam's. | Rachel Kim | Week 1, before pilot opens |
| Copilot transition comms | Explain to all 3,800 developers why this replaces Copilot, when the license retires, and what to do now. Frame it around capability and quality, not governance — developers don't respond to governance messaging. | Rachel Kim + Eng leads | Before pilot launch |
| Data science onboarding | Dedicated onboarding session for JupyterLab surface — different workflow from IDE, different capabilities at pilot vs Phase 2. Priya leads, data science team leads as internal champions. | Priya Nair | Week 2 |
| SOX workflow change | The change ticket linkage requirement is new behavior for developers on SOX repos. David Park's team needs to understand it before Phase 2 enforcement goes live, not after the first merge is blocked. | David Park + Internal Audit | Month 2 |
| New KPIs | Weekly active usage, acceptance rate, DLP incident rate, Okta shadow-IT signal. Agree with Finance on what goes in the board report before the pilot ends — don't invent KPIs after the fact. | Sam Torres + Finance | Before pilot exit |
| Betriebsvereinbarung | Start the works council engagement this week. 4-6 months. Cannot be accelerated. | Tobias Brandt + HR Legal | This week |

---

## Exec Summary — Apex Retail Group Coding Agent Platform

---

### What We're Building

A governed coding agent platform that replaces the fragmented mix of GitHub
Copilot (30% adoption), personal Claude.ai accounts, and an ungoverned shared
OpenAI API key currently used by the data science team. Every Apex developer
gets access to Claude in their IDE or JupyterLab, through Apex's own identity
controls, with PCI and SOX compliance and a full audit trail. The shared key
gets closed. Shadow-IT stops.

### Architecture Decision

Amazon Bedrock AgentCore managed runtime, delivered via Claude Code IDE extension
and JupyterLab sidebar, on AWS in three regions (US, EU, AU). Platform team
builds the governance layer; AWS manages the agent infrastructure.

### Rollout Plan

| Phase | Population | Timeline | Exit criterion |
|---|---|---|---|
| Pilot | 200 developers (senior backend + data science + data eng) | Weeks 1–8 | Zero personal AI account SSO sessions from pilot population by week 8 |
| BU rollout | 1,500 developers | Months 3–6 | PCI access live; EU instance live |
| Full enterprise | 3,800 developers | Months 7–12 | Copilot retired; per-BU chargeback active |

### Cost

| Phase | Monthly cost | Per enrolled developer/year |
|---|---|---|
| Pilot | $28K–$38K | — |
| BU rollout | $115K–$155K | — |
| Full rollout | $260K–$340K | ~$85–$110/enrolled developer/year |

**Comparison at equivalent adoption:** GitHub Copilot at 30% adoption costs
$180/enrolled developer/year. This platform at 30% adoption would cost
~$95/enrolled developer/year — less, because you pay per active token consumed,
not per seat. At 70% adoption (the target), the new platform costs
~$200/enrolled developer/year vs $180 for Copilot — a modest premium for
significantly higher capability, a JupyterLab surface Copilot doesn't offer,
and full audit coverage including the population currently on personal accounts.

### Return on Investment

10% productivity improvement (conservative) × $180K fully-loaded developer cost
= $18,000/developer/year productivity value.
Platform cost at full adoption: ~$200/enrolled developer/year.
**~90:1 ROI on the marginal cost over existing Copilot spend.**
At 3,800 developers: ~$68M annual productivity value, ~$4M total platform cost.

### Four Things That Need a Decision Before Phase 2

1. **PCI QSA confirmation** — ROC changes required? — Marcus Webb + QSA — start this week
2. **Betriebsvereinbarung** — works council agreement, Berlin team — Tobias Brandt + HR Legal — start this week, 4-6 months
3. **SOX ITGC scope** — session logs satisfy ITGC evidence? — Internal Audit + Deloitte — during Phase 1
4. **AWS GDPR DPA** — EU Bedrock inference — Privacy/Legal — before EU deploy

### Recommended Next Step

Marcus and Tobias each have a conversation to start this week. Neither can be
accelerated once the process begins. Everything else can wait until Monday.

---

## Appendix: Standard Platform Hygiene

The following controls apply to every Apex deployment. They are not design
decisions — they are baseline requirements.

- **Resilience:** AWS SDK adaptive retry on all Bedrock calls; circuit-breaker
  per MCP server; single server failure does not terminate a session
- **Credential hygiene:** All credentials via Secrets Manager injection; no static
  API keys anywhere in the platform; TruffleHog pre-commit hook on platform repos
- **Change safety:** Auto-branch creation on by default; no direct main commits;
  30-minute idle session timeout
- **Supply chain:** MCP server versions pinned in allowlist; quarterly review;
  ECR container images signed
- **Context discipline:** System prompt token budget reviewed quarterly; context
  compaction at 70% utilization

---

## Post-Simulation Notes (v4 vs v3)

### What the three fixes changed

**Architecture shown once:**
v3 rendered the architecture at the end of Phase 4 and again identically at the
top of the Blueprint. v4 shows it once during Phase 4, then the Blueprint opens
with "Architecture as agreed during discovery" and reproduces it as the canonical
reference. The two versions are now visually identical — there's nothing to
reconcile.

**Best practices as appendix:**
v3 had a "Platform Best Practices" section mid-blueprint between Tradeoffs and
Org Readiness, containing items like "CLAUDE.md token budget reviewed quarterly"
that Rachel doesn't have context for. v4 moves this to a clearly-labeled appendix
titled "Standard Platform Hygiene" and reframes items in terms of the Apex stack
(e.g., "ECR container images signed" instead of "sign container images"). It reads
as a checklist for the build team, not as consulting advice mixed into the main
document.

**Cost comparison fixed:**
v3 compared $600/active developer/year (Copilot at 30% adoption) against
$1,000/active developer/year (new platform). This is an unfair comparison —
the new platform will have higher adoption, so using current active-user cost
for the old tool while projecting higher adoption for the new one inflates the
apparent premium. v4 compares both tools at 30% adoption ($180 vs ~$95 per
enrolled developer — the new platform is cheaper at low adoption because it's
consumption-based not seat-based) and at the 70% target ($180 vs ~$200 per
enrolled developer — a small premium for higher capability and broader coverage).
The ROI story is actually stronger when framed honestly.

### OKF gaps (unchanged)

| Gap | Description | Priority |
|---|---|---|
| APEX-01 | Multi-compliance repo overlap (PCI + SOX on same repo simultaneously) | Medium |
| APEX-02 | Tiered developer quota by persona — not in session-economics node | Low |
| APEX-03 | CCPA — no node; GDPR pattern covers the platform design | Low |
| APEX-04 | Datadog metric stream pattern — not in observability.md | Low |
| APEX-05 | Developer adoption / tool migration change management node | Medium |
