# Platform Advisor — Discovery Methodology

**Status:** Draft for review
**Purpose:** The single source of truth for *what the Platform Advisor asks the customer, in what order, and why.* All three layers — the decision graph (`graph.json`), the agent tool gating (`pipeline_tools.py`), and the intake UI (`IntakeForm.tsx`) — must reconcile to this document. Where they currently disagree, this document wins.

---

## 1. What the advisor is deciding

Every question exists to drive an **output**. Most drive one of the **three stacked decisions** below. A few drive *secondary outputs* — the innovation overlay, the risk/anti-pattern list, the roadmap phasing, or component reuse (Q9, Q10, Q11). A question is only valid if it changes one of these two categories; if it changes neither, it does not belong in the interview.

| Layer | Decision | Output values | How produced |
|---|---|---|---|
| **A. Archetype** | What *kind* of platform is this? | Coding/dev-productivity · Internal copilot · Agent-hosting platform · Customer-facing product · Process automation · Marketplace/economy | **Question filter** (Q0) |
| **B. Operating model** | Who *owns, funds, governs* it? | Centralized · Federated · Decentralized/Mesh · Economy | **Scored** by the graph engine |
| **C. Technical topology** | How do the pieces *connect*? | Hub-and-spoke · Gateway-fronted · Peer-to-peer (A2A) · Multi-cloud/hybrid · Single-account | **Rule-based lookup** (derived from B + Q5 + tenancy) |

**A is a branch (a filter).** The archetype decides *which later questions appear*. It does **not** seed scoring weights — it only controls the interview path.

**B is the one scored axis.** The graph engine ranks the four operating models from the intake pressures and picks the winner with a confidence score.

**C is a deterministic lookup, not a scored axis.** Topology is derived from the chosen operating model (B) plus data location (Q5) and tenancy answers (Q7a) via the documented rules in §3.6 — no separate scoring pass. A real recommendation reads: *"Federated operating model → hub-and-spoke topology, fronted by a shared gateway, single-cloud."*

**Naming note:** "Mesh" (operating model B) and "peer-to-peer (A2A)" (topology C) are deliberately different words. The topology value is **never** called "mesh," to avoid colliding with the Mesh operating model.

---

## 2. The shape of every question

Each question is one screen with the same five parts:

```
Q3.  How many teams will build agents on this platform
     within the next 12 months?

     Why we ask: this drives whether one central team can own
     everything, or you need to federate ownership.

     ○ One team (≤5 people)
     ○ A few teams (2–5)
     ○ Many teams (6–20)
     ○ Org-wide (20+)
     ○ Not sure — estimate for me

     [ ? Tell me more ]
```

**The six rules that make a question unambiguous:**

1. **One sentence, in the customer's words.** No internal jargon (never "federation pressure", "tier elevation").
2. **Ask a fact they know, not a decision they haven't made.** "Who gets paged when an agent breaks?" — not "What's your governance model?"
3. **Every option carries a boundary or example** so two different readers pick the same answer. "A few (2–5)" — not "Some".
4. **Options are mutually exclusive and exhaustive** — always include a None / Greenfield / Other where the space isn't closed.
5. **Every question has a "Not sure" path.** "Not sure" contributes **zero pressure** to the score — it never substitutes an opinionated default value. It is recorded and surfaced as an explicit assumption in the confirmation step (Stage 5) and the final blueprint, optionally with one clarifying sub-question. This prevents unanswered questions from silently steering the recommendation.
6. **One question per screen, progress always visible** ("4 of ~10"). No flat multi-field wall.

**Hard constraints vs. soft preferences.** Two kinds of answers:
- **Hard gates** (compliance, data residency) → can *disqualify* a pattern (graph `Law` nodes). Framed as "must satisfy".
- **Soft pressures** (cost stance, autonomy, team count) → *weight* the score (graph `Constraint` pressures). Framed as "what matters most".

The UI should visually distinguish the two so the customer knows which answers are binding.

**Current state vs. target state.** Some questions capture what exists today (maturity, existing identity/observability), others capture the desired end state (autonomy, scale). The **gap between them is the roadmap** and feeds the phasing output directly.

---

## 3. The interview path

Five stages. A **spine** everyone answers (Q1–Q6, Q8–Q11), an **archetype branch** (Q0), and **archetype-specific questions** (Q7x, ~2 per path). Any single customer sees ~9–12 questions.

```
STAGE 1  Frame      → Q0 archetype  (+ Q0b secondary)      [branches everything]
STAGE 2  Spine      → Q1  Q2  Q3  Q4  Q5  Q6               [everyone]
STAGE 3  Branch     → Q7x  (only the questions this archetype needs)
STAGE 4  Tune       → Q8  Q9  Q10  Q11                     [everyone]
STAGE 5  Confirm    → echo the frame back in plain English before scoring
```

---

### STAGE 1 — Frame (archetype)

#### Q0. What is the primary job of this platform over the next 12 months?
*Why we ask: this decides which questions you'll see next.* — single-select

| Option | Plain description |
|---|---|
| Coding & dev-productivity agents | Help our engineers write, review, and ship code (Claude Code / Copilot style) |
| Internal copilot / knowledge assistant | Answer questions and do tasks for employees over our own data |
| A platform for other teams to build & run agents | We provide the infrastructure; other teams build on it |
| Customer-facing agentic product | Agents embedded in a product our customers use |
| Process / workflow automation | Back-office automation — ops, claims, incident response |
| Agent marketplace / economy | Agents that discover, compose, and transact with each other |

*Not sure* → sub-question: **"Who uses the agents — your engineers, your employees, or your customers?"** (maps to the first three).

Q0 is a **pure question filter**: it decides which Stage-3 branch questions appear (§3). It does **not** feed scoring weights. If more than one archetype genuinely applies (e.g. a hosting platform whose first tenant is a coding assistant), pick the one that best describes *who owns and funds the platform*; the Stage-3 branches for the others can be revisited in a later session.

---

### STAGE 2 — Spine (everyone)

#### Q1. How much should agents be allowed to act on their own?
*Why: sets your autonomy tier and how many guardrails you need.* — single-select
- Act independently — take actions without a human checking first
- Act with approval gates — propose; a human approves before it executes
- Suggest only — the human always performs the action (copilot style)
- Not sure → **zero pressure**, recorded as assumption

#### Q2. How many distinct teams will build agents on this within 12 months?
*Why: the single biggest driver of Centralized vs. Federated.* — single-select. (Counts **teams**, not people — team size is captured separately if needed.)
- One team · A few teams (2–5) · Many teams (6–20) · Org-wide (20+ teams)
- Not sure → **zero pressure**, recorded as assumption

#### Q3. Today, when an automated system causes a production incident, who is accountable?
*Why: reveals your real governance model — not the one on a slide.* — single-select
- One central platform/ops team · Each team owns their own · No clear owner yet

#### Q4. Who will build the agents?
*Why: decides managed-vs-open-source and the component tier.* — single-select
- AI/ML engineers · General full-stack developers · Business users / low-code · A mix of all
- Not sure → **zero pressure**, recorded as assumption

#### Q5. Where does the data the agents need actually live right now?
*Why: a hard constraint on topology and residency.* — single-select
- One cloud region · Multiple regions · On-prem + cloud (hybrid) · Across multiple clouds
- Not sure → sub-question about primary cloud provider

#### Q6. Which regulations must this platform satisfy? *(select all)*
*Why: some combinations rule out certain architectures entirely (hard gate).* — multi-select
- SOX · PCI-DSS · HIPAA · FedRAMP · GDPR · EU AI Act · None / not yet
- Not sure → sub-question: *"What industry are you in?"* → infer likely regimes and confirm.

---

### STAGE 3 — Archetype branch (only relevant questions appear)

**IF Q0 = Agent-hosting platform:**
- **Q7a. How should teams be isolated from each other?** — Shared with role-based access · Separate namespaces · Separate accounts · Tiered (mix)
- **Q7b. How self-service should it be?** — Fully self-service · Request-and-approve · Central team provisions

**IF Q0 = Coding / dev-productivity:**
- **Q7c. What's your hard limit on code/IP leaving your environment?** — Nothing leaves our VPC · Approved SaaS is fine · No constraint
- **Q7d. What matters most?** — Response latency · Breadth of tool/repo access · Cost per developer

**IF Q0 = Customer-facing product:**
- **Q7e. Peak expected volume?** — <10 req/s · 10–100 · 100–1,000 · >1,000
- **Q7f. Cost of a wrong answer to a customer?** — Low · Reputational · Financial/legal

**IF Q0 = Marketplace / economy:**
- **Q7g. Will agents transact with third-party/external agents?** — Internal only · Internal + external · Fully open
- **Q7h. How are agents billed/metered?** — Not yet · Per-call · Per-outcome

**IF Q0 = Process automation OR Internal copilot:**
- **Q7i. How critical is a full audit trail of every agent action?** — Nice to have · Required · Regulator-facing

---

### STAGE 4 — Tune & prioritize (everyone)

#### Q8. What's your stance on cost?
- Cost is the #1 constraint · Performance over cost · Predictable/flat spend · Pay for outcomes
- Not sure → **zero pressure**, recorded as assumption

#### Q9. What's your single biggest frustration with agents today? *(select up to 3)*
- Too expensive · Can't govern/control them · Teams build silos, no reuse · Tool integration is slow · Auth/identity is a mess · Can't trust the outputs · No good data grounding
*Drives the innovation overlay and anti-pattern outputs.*

#### Q10. Where are you today with AI in production?
- Mature (agents/LLMs already in prod) · Emerging (pilots, POCs) · Greenfield (starting now)
*Sets the starting point of the roadmap.*

#### Q11. What identity & observability do you already run?
- Identity: OAuth/OIDC · IAM-heavy · Multiple IdPs · Greenfield
- Observability: We have a stack (Datadog / CloudWatch / etc.) · Greenfield
*Decides reuse vs. build-new components.*

---

### STAGE 5 — Confirm the frame

Before scoring, echo the answers back in plain English for correction:

> "Here's what I heard: you're building **an internal copilot** for **a few teams**, governed by **one central team**, on **AWS single-region**, under **SOC 2**, cost-conscious with **predictable spend**, currently at the **pilot** stage. Your biggest pains are **governance** and **trust in outputs**. Right?" → **[Yes, score it]** / **[Let me fix something]**

Any question answered "Not sure" is listed here as an **explicit assumption** ("Assuming: cost stance = predictable spend") so the customer can correct it before scoring.

---

### 3.6 Topology derivation (axis C — rule-based, not scored)

Topology is computed deterministically *after* the operating model (B) is chosen, from B + Q5 (data location) + Q7a (tenancy, when present). It is not scored. Rules applied in order; first match wins for the base topology, then modifiers are layered on:

| # | Condition | Base topology |
|---|---|---|
| 1 | Operating model = Centralized **and** Q2 = One team | **Single-account** |
| 2 | Operating model = Centralized (multi-team) | **Hub-and-spoke** (shared hub, thin spokes) |
| 3 | Operating model = Federated | **Hub-and-spoke** (shared spine + LOB spokes) |
| 4 | Operating model = Mesh | **Peer-to-peer (A2A)** |
| 5 | Operating model = Economy | **Peer-to-peer (A2A)** + marketplace control plane |

**Modifiers (additive, can apply to any base):**
- Q5 = "Across multiple clouds" **or** "On-prem + cloud" → add **Multi-cloud/hybrid** overlay (portable orchestration, cross-cloud bridges).
- Archetype ∈ {coding, customer-facing} **or** Q9 includes "auth mess" / "tool integration slow" → add **Gateway-fronted** (shared control plane for model + tool access, auth, rate/cost limits).
- Q7a = "Separate accounts" → escalate spokes to account-level isolation.

The output names the base plus any modifiers, e.g. *"Hub-and-spoke, gateway-fronted, single-cloud."*

---

## 4. Traceability — every question maps to an output

| Q | Drives | Output | Graph node | Kind |
|---|---|---|---|---|
| Q0 | Which Stage-3 questions appear | A. Archetype (filter only) | *(UI/tool filter — not scored)* | filter |
| Q1 | Autonomy tier, guardrails | B + component tier | `constraint:q1:*` | soft |
| Q2 | Centralized ↔ Federated | B + topology rule | `constraint:q3:*` | soft |
| Q3 | Governance evidence | B | *(new — governance constraint)* | soft |
| Q4 | Managed vs OSS, tier | components | `constraint:q2:*` | soft |
| Q5 | Residency + topology rule | B (residency) + C input | `constraint:q5/q6:*` | hard + soft |
| Q6 | Disqualifiers | B gates | `constraint:q8:*`, `Law` nodes | hard |
| Q7a/b | Tenancy, self-service | C input + components | `constraint:q*` (hosting) | soft |
| Q7c/d | IP boundary, latency/cost | C modifier + components | *(new)* | hard + soft |
| Q7e/f | Scale, safety | components, tier | *(new)* | soft |
| Q7g/h | External agents, metering | B (economy) | *(new)* | soft |
| Q7i | Audit trail | components, compliance | `Law` nodes | soft |
| Q8 | Cost weights, model routing | components, cost | `constraint:q7:*` | soft |
| Q9 | Innovations + anti-patterns + gateway modifier | overlay, risks, C | `constraint:q9:*` | soft |
| Q10 | Roadmap start point | phasing | *(new — maturity)* | current-state |
| Q11 | Reuse vs greenfield | components | *(new — identity/obs)* | current-state |

Note: axis C (topology) has no graph nodes of its own — it is derived by the §3.6 rules from B, Q5, Q7a, Q9 and the archetype.

---

## 5. Reconciliation gaps to close (for implementation)

The three layers currently diverge. Against this spec, in build order:

1. **Engine `graph_engine.py`** (prerequisite bug-fixes — must land first):
   - Mesh and Economy are currently disqualified on *every* input because Law nodes have no `trigger_condition`, so their `BLOCKS` edges fire unconditionally. Blocks must only fire when a law's trigger actually matches the answers.
   - Answer→constraint matching uses free-text substring first-match, which mis-attributes answers across questions (e.g. a data-location answer applying team-count pressure). Bind matching to the question's `signal_id` / intake key.
   - Add a regression test asserting all four operating models are winnable and no cross-question collisions occur.
2. **Graph `graph.json`** — encode this spec: reword/add constraints for the governance-evidence question (Q3), maturity (Q10), and identity/observability (Q11); give `Law` nodes real `trigger_condition` dicts (from Q6 + Q1); ensure every constraint's `answer_value` text contains the keywords the engine's expansion map looks for. **No topology scoring nodes** — topology is the §3.6 rule-based lookup.
3. **Agent tool gating** (`pipeline_tools._INTAKE_REQUIRED`) — replace the current 12 ad-hoc fields with the spine set (Q1–Q6, Q8–Q11) plus archetype (Q0); make Q7x conditional on archetype.
4. **Intake UI** (`IntakeForm.tsx`) — rebuild the flat 13-field form into the staged/branching wizard (one question per screen, archetype filter, "Not sure" = zero-pressure assumption, hard/soft visual distinction, Stage-5 confirmation with assumptions listed).

**Build sequence:** fix engine (1) → reconcile graph (2) → reconcile tool gating (3) → rebuild UI (4).
