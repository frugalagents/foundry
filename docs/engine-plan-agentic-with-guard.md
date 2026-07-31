# Platform Advisor Engine — Build Plan
## Agentic edges, a thin deterministic guard

**Decision (from the paradigm debate):** The blueprint advisor is **agentic / multi-agent over your curated knowledge (the moat)**, with a **thin deterministic guard** sitting between "propose" and "show the customer." The guard vetoes only two things that must never be invented: a **violated hard constraint** and a **non-existent integration**. Everything else — probing, proposing the stack, writing rationale and best-practice docs — is agentic. This keeps the flexibility the user wants and prevents the one disqualifying failure (a confident, real-named, cited-but-wrong recommendation in front of a customer).

The seam is **propose vs. validate**, not decide vs. converse.

---

## 1. The three layers

### PROBE — agentic, over the curated question bank
- A **Probe agent** runs a warm interview. It interprets free text ("we're a bank but the platform team is three people") into typed facts.
- It draws its next question from a **ranked, applicable set** — reuse `advisor_core/v3/engine.py:rank_next_questions` (information-gain scoring: distinct outcomes, affected components, family eliminations, `hard_constraint_risk`) as *context*, not a rigid script. The agent phrases and may reorder for flow; it cannot invent questions outside the curated bank.
- **Non-overloading rule:** surface at most the top N ranked questions per turn; never dump the whole bank.

### DECIDE — agent proposes → deterministic guard vetoes
- A **Propose agent** selects services per box and resolves cascades (e.g. "bespoke gateway ⇒ needs EKS/ECS hosting"), reasoning freely over the service catalog + KB. It has full range — it *can* propose a novel stack for an unusual customer.
- Its output is a **structured proposal** (per box: chosen option, alternatives considered, one-line why).
- The **Guard** (deterministic, non-LLM) checks the proposal and can only VETO:
  1. **Constraint check** — no asserted hard constraint is weakened (e.g. "no self-hosting" ⇒ reject any self-hosted component).
  2. **Integration check** — every selected component's required integrations exist in the catalog (extends `deployable/catalog.py:_validate_bindings`).
  3. **Capability check** — no capability is claimed that isn't backed by the catalog/KB.
- On veto, the proposal bounces back to the Propose agent with the specific violation, for one bounded re-propose. Persistent violation → surfaced to the user as an open decision, never silently shipped.

### GENERATE — agentic, grounded on curated data
- On "Generate my architecture" (at any point), a **Generate agent** produces the three outputs from the validated proposal:
  1. **Solution stack** — concrete services per box (deterministic projection of the proposal).
  2. **Rationale** — "why X over Y" per decision. Every such sentence must bind to a catalog fact or a KB evidence claim; **ungrounded sentences are dropped**.
  3. **Best-practice docs** across dimensions (governance, tokenomics, security, observability) — cite only KB chunks (the 19-doc Bedrock KB, already wired via `kb_utils`).
- A **Critic agent** re-checks the generated prose against anti-pattern KB docs before it ships (reuse `antipattern_skill`).
- Gaps (unanswered decisions) are filled with **explicitly-labeled assumptions**, so partial generation is honest.

---

## 2. Agent roster (multi-agent, skill-backed)

| Agent | Role | Backed by |
|---|---|---|
| **Orchestrator** | Owns the session turn loop; routes to sub-agents; owns persistence | Strands `Agent` on AgentCore Runtime (`main.py`) |
| **Probe** | Interview, interpret free text → typed facts | `rank_next_questions` + question bank |
| **Propose** | Select services + resolve cascades → structured proposal | Service catalog + KB retrieval |
| **Guard** *(not an agent — a pure function)* | Veto violated-constraint / fake-integration / unbacked-capability | `advisor_core/v3` rules + `_validate_bindings` |
| **Generate** | Stack + rationale + best-practice docs | KB (`kb_utils`) + evidence claims |
| **Critic** | Re-check prose vs anti-patterns before ship | `antipattern_skill` |

Each domain's knowledge is packaged as a **skill** (harness, model-gateway, governance, tokenomics, …) carrying its question fragment, option set, and best-practice content — the pluggable moat.

---

## 3. The moat — curated knowledge, expressed by form

Split by *form*, because that is what determines where each asset plugs in:

| Asset | Form | Layer | Status in foundry |
|---|---|---|---|
| Question bank | Ranked policy (info-gain) | PROBE | `rank_next_questions` exists |
| Service catalog (options + integrations + provider scoring) | Typed / checkable | DECIDE (guard) | `catalogs/coding-platform-r0.2/*` exists |
| Constraint rules | Executable `when`→`veto` checks | DECIDE (guard) | `40-capability-rules.json` + rules engine exist |
| Evidence claims (provenance, freshness, reviewer) | Provenanced records | DECIDE→GENERATE | `models.py` EvidenceClaim exists |
| Best-practice / anti-pattern / governance / tokenomics docs | Retrievable (RAG) | PROBE + GENERATE + Critic | 19-doc Bedrock KB live (`EDDM8YZDNJ`) |
| Skills (per decision domain) | Retrievable procedural | GENERATE | `pipeline_skills/*` exist |

**The seam rule:** *exact + checkable* for the guard (retrieval must never govern a liability-bearing pick); *retrievable/fuzzy* for probe and generate (narration, not decision).

---

## 4. Addressing the honest risk

**The risk:** a "harden over time" agentic system accumulates a **cohort of un-auditable historical recommendations** made before a given check existed — and temp-0 agents are **not bit-reproducible** across model/hardware versions. So "replayable" is weaker than a deterministic engine's guarantee.

**Containment — a full provenance record per generation, so every agentic decision is forensically reconstructable even if not bit-identical:**

1. **Decision Record (immutable, per generate):** persist a signed record containing —
   - the full **answer set** and derived typed facts at generation time;
   - the **proposal** (every box: chosen option + alternatives + agent's reasoning);
   - the **guard verdict** (which checks ran, pass/veto, any re-propose loop);
   - the **KB citations** used (doc id + chunk + retrieval score);
   - the **model id + version + prompt hash + temperature**, and the **catalog/guard `content_hash`** in force;
   - a **schema/guard version stamp**.
   Reuse the existing `state_hash` + `persistence_revision` substrate (`db/dynamodb.py`) — extend it from storing just `answers` to storing this record.

2. **Guard-version stamping:** every record records which guard version validated it. When a new check is added, records validated by older guards are **queryable** ("show all live blueprints whose stack a current check would now veto"). The historical cohort stops being invisible — it becomes a **remediation backlog**, not a silent liability.

3. **Re-validation on reopen:** when a saved blueprint is reopened, re-run the *current* guard against the stored proposal. If a now-existing check would veto it, surface a **non-blocking banner** ("this decision predates the X check; review recommended"). Cheap (guard is a pure function), and converts drift into an explicit prompt.

4. **Reproducibility honesty:** the record is labeled **"reproducible-with-trace, not bit-identical."** The audit an SA relies on is: *what was proposed, what was checked, what was cited, under which knowledge version* — which the record fully captures. We do **not** claim deterministic replay for the agentic layers, and we say so in the UI.

5. **Pin the highest-stakes decisions to hard rules over time.** The instrumentation (below) shows which decisions the guard repeatedly has to veto/correct; those graduate from "agent proposes" to "rules decide" — moving the seam downward only where evidence demands it. This is the controlled path from flexible-day-one to hardened-where-it-matters.

---

## 5. Build sequence

**Phase 0 — Save current UX (prereq).** Commit the React Flow canvas + blueprint flow (currently uncommitted on `feat/provider-slice`).

**Phase 1 — Agentic vertical, one domain end-to-end (Model Gateway).**
Probe → Propose → Guard → Generate for the model-gateway decision, over the live KB. Proves the full loop and the Decision Record. Reuse `main.py` Strands agent + `kb_utils` + `blueprint_skill` pattern. *No new AWS resources.*

**Phase 2 — The guard.** Author the three checks (constraint / integration / capability) as pure functions on top of `advisor_core/v3` + `_validate_bindings`. Wire the veto→re-propose loop. Author the initial constraint set (small: residency, self-hosting, egress, data-boundary).

**Phase 3 — Decision Record + persistence.** Extend workspace state to store the full record (§4.1); add guard-version stamping and reopen re-validation.

**Phase 4 — Scale domains.** Package each box as a skill (harness, execution, identity, observability, tokenomics…) with its question fragment + option set + best-practice content. Add the Critic pass.

**Phase 5 — Instrument & harden.** Log guard vetoes and agent corrections; promote the most-corrected decisions to hard rules.

**Reuse vs add:**
- *Reuse:* Strands/AgentCore runtime, `rank_next_questions`, the v3 catalog + rules + `_validate_bindings`, evidence-claim model, the Bedrock KB + `kb_utils`, the workspace-state persistence, the pipeline skills.
- *Add:* the Guard as an explicit veto layer, the multi-agent Propose/Generate/Critic split, the Decision Record schema + guard-version stamping, per-box skills.

---

## 6. Open decisions to confirm before Phase 1
1. **Rationale authorship** — agent-generated (grounded on KB + catalog) vs. author-curated per matrix. Plan assumes agent-generated-then-grounded; the guard ensures it can't cite-launder a wrong pick.
2. **First domain** — plan picks Model Gateway (already partially wired). Alternative: Harness (the box with the richest cascade).
3. **Where the agents run** — extend the existing AgentCore Strands agent (`main.py`) vs. a new orchestrator. Plan assumes extend.
