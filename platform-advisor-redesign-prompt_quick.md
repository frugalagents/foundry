# Feedback Prompt for Claude: Redesign the Platform Advisor App

## Context

I've built a Strands-based "Agentic Platform Advisor" app (Next.js frontend + AgentCore backend). The architecture is solid — deterministic graph scoring, modular skills pipeline, A2UI streaming, Bedrock KB integration, MCP support. BUT when I use it, the output feels no different from what I'd get from ChatGPT with a good prompt.

## The Problem

The app currently does:
1. Ask 9 intake questions
2. Score → select a pattern (Centralized/Federated/Mesh/Economy)
3. List components at tiers
4. List innovations
5. Produce a 400-word "executive summary" markdown

That's a **recommendation generator**. It's not an **advisor**. A VP gets the same output from ChatGPT in 2 minutes.

## What I Need You to Rebuild

Transform this from a "one-shot recommendation report" into an **interactive advisory platform** that a VP would find genuinely more valuable than ChatGPT. Here are the 5 design principles to follow:

---

### Principle 1: DEPTH ON DEMAND (Google Maps Model)

The app should work like Google Maps — start at country level, zoom to street level.

**Current:** Panel shows "Agent Registry — Tier 2 — AgentCore Registry" (one line, done).

**Target:** Click "Agent Registry" → EXPLODES into:
- WHY you need it (from curated KB docs — not LLM-generated)
- Implementation options comparison (AgentCore Registry vs. custom DynamoDB-based vs. hybrid)
- CDK template / IaC code snippet (actual code, not pseudocode)
- Time to implement (e.g., "2 weeks for team of 2 based on similar deployments")
- Cost estimate at your scale (e.g., "$340/month for 500 agents registered")
- Relevant workshop (live link from MCP: "Building Agent Registries on AgentCore — 4hr lab")
- Reference architecture (link from MCP or KB)
- What other similar companies did (anonymized pattern from engagement history)

**Implementation:** Each component card should have an `expandable: true` state. On expand, the innovation_skill + service_mapping_skill + kb_utils are called AGAIN with a deeper query specific to that component. Stream the drilldown results into an expanded panel.

---

### Principle 2: CONVERSATIONAL DEPTH (Not 9 Questions and Done)

The 9 intake questions select the PATTERN. But after pattern selection, the app should enter a **guided exploration mode** where it asks CONTEXTUAL follow-up questions per component:

- "You said you have existing Datadog — which agents are you already monitoring? This changes how we design the observability layer."
- "You selected 10+ LOBs — are they all at the same maturity, or do 2-3 lead while others follow? This determines whether you do big-bang federation or progressive."
- "You mentioned MCP is hard — is it the protocol itself or the operational burden of hosting servers? Different solutions for each."

These follow-ups should:
- Appear as chat messages on the LEFT (conversational)
- Update the visual panels on the RIGHT in real-time as the user answers
- Be OPTIONAL — user can skip and get the default recommendation
- Store answers in LTM for next session

---

### Principle 3: QUANTIFIED, NOT QUALITATIVE

Every recommendation should have a NUMBER attached:

| Current (qualitative) | Target (quantified) |
|---|---|
| "Cost-optimized architecture" | "Estimated $47K/month without routing → $12K/month with. Savings: $420K/year." |
| "Phase 0: 0-3 months" | "Phase 0: 6 weeks. 3 developers needed. Based on similar FinServ deployments." |
| "Tier 3 Policy Engine required" | "SOX Section 404 requires audit trail. Automated Reasoning: $0.002/check × 10K checks/day = $600/month. Non-compliance fine: $5M+." |
| "10+ LOBs → Federated" | "With 12 LOBs, centralized would create a 3-week queue per agent request (based on single-team throughput). Federated reduces to 2-day self-serve." |

The graph should store cost models, time estimates, and team-size requirements alongside components. The blueprint_skill should CALCULATE, not just DESCRIBE.

---

### Principle 4: INTERACTIVE "WHAT-IF" EXPLORATION

The right panel should let the VP PLAY with the architecture:

- **Toggle inputs:** "What if we only have 4 LOBs instead of 12?" → radar chart re-scores, components shift, cost changes, all live
- **Toggle innovations:** "What if we DON'T use Intelligent Routing?" → cost estimate jumps, "with vs without" comparison appears
- **Toggle compliance:** "Add HIPAA" → new components forced, timeline extends, cost increases — shown as a DIFF overlay
- **Drag components between phases:** "What if we move Identity Mesh to P0?" → dependency check, timeline recalculates, warnings appear if dependencies not met

This makes the app a DECISION EXPLORATION TOOL — not a one-shot report generator.

---

### Principle 5: LIVING RELATIONSHIP (Session Continuity + Proactive Updates)

The app should NOT end when the blueprint is generated:

- **Return next week:** "Since your last session, AgentCore Payments went GA. This enables the Economy variant we discussed. Want me to update your blueprint?"
- **Progress tracking:** "Your P0 has 3 components. You've deployed Registry (done ✓). Policy Engine (in progress). Observability (not started). ETA: 2 weeks behind plan."
- **Weekly digest:** (if wired to a scheduled task) "3 AWS launches this week that affect your blueprint: [list]. 1 requires a tier change."
- **Re-engagement triggers:** "It's been 30 days since your session. Your P1 starts in 2 weeks — want to review readiness?"

---

## Specific Technical Changes Required

### Backend (`pipeline_skills/`):

1. **Add `drilldown_skill.py`** — new skill triggered when user clicks a component. Queries KB + MCP with deep specificity (CDK snippets, cost models, workshop links). Returns expanded panel data.

2. **Add `cost_estimation_skill.py`** — new skill that takes component list + tier choices + scale inputs (LOBs, agents, invocations/day) → calculates estimated monthly cost per component and total. Use a simple pricing model stored in graph.json.

3. **Add `whatif_skill.py`** — new skill that takes current pipeline state + a single changed input → re-runs affected pipeline steps ONLY → returns a DIFF (what changed vs. current).

4. **Modify `blueprint_skill.py`** — instead of generating a 400-word LLM summary, assemble a STRUCTURED payload that the frontend renders as an interactive dashboard (mini architecture diagram + cost summary + timeline + risk cards + export actions). The LLM generates ONLY the "executive narrative" paragraph (2-3 sentences), everything else is DATA from the pipeline.

5. **Add `followup_questions_skill.py`** — after pattern selection, generates 3-5 contextual follow-up questions based on which components were selected + user's answers. These refine the blueprint without requiring re-run.

### Frontend (`components/panels/`):

1. **Make component cards expandable** — click to drill down. Shows loading state while `drilldown_skill` runs. Expands inline with implementation details.

2. **Add cost estimation panel** — appears after service mapping. Shows cost breakdown by component, total monthly/yearly, comparison (with vs without optimization).

3. **Add what-if controls** — toggle switches on the intake form that re-trigger scoring without full page reload. Show DIFF overlay on architecture diagram.

4. **Add progress tracking view** — for returning customers. Shows which P0 components are deployed/in-progress/pending.

5. **Make the final blueprint an INTERACTIVE DASHBOARD** — not a markdown blob. Clickable components, hoverable cost estimates, exportable sections.

### Knowledge / Graph:

1. **Add cost models to graph.json** — each component node gets `cost_per_unit`, `unit_type` (per-agent, per-invocation, per-month), `base_cost` fields.

2. **Add implementation metadata** — each component gets `team_size`, `estimated_weeks`, `cdk_construct_name`, `workshop_url_hint` (for MCP lookup).

3. **Add engagement patterns** — anonymized "what similar companies did" as graph nodes connected to components. E.g., "3 FinServ companies deployed Registry in avg 2.5 weeks with 2 engineers."

---

## What SUCCESS Looks Like

A VP opens the app and after 20 minutes of interaction can say:

> "I now know EXACTLY what to build, in what order, how much it costs, how long it takes, what my team needs to learn, and what workshops to book. I couldn't have gotten this from ChatGPT because it's tailored to MY 12 LOBs, MY SOX compliance needs, MY team's existing Datadog setup, and MY cost constraints. And next month when I come back, it'll remember where I am and what changed."

That's the bar. Rebuild toward it.
