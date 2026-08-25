---
type: platform-component
title: Enterprise Cost Model
description: structured cost modeling methodology for a coding agent platform at enterprise scale — token economics, per-developer unit costs, tiered usage assumptions, infrastructure costs, and the finance approval process for a platform that may cost $500K–$5M/month at full rollout
group: ops
tags: [ops, cost-model, token-economics, unit-cost, finance-approval, tco, roi, budget-process, cost-attribution, chargeback]
timestamp: 2026-08-15T00:00:00Z
status: candidate
traversal: conditional
trigger: [cost-model, token-cost, per-developer-cost, budget-approval, roi, tco, finance-sign-off, cost-justification, chargeback, usage-based-billing, cost-attribution]
decision-question: "Do you need a structured cost model — per-developer unit economics, total platform cost at scale, infrastructure cost breakdown, and ROI justification — to get finance and executive approval for the platform at enterprise scale?"
decision-domain: cost_control
priority: 8
requires: [ops/cost, ops/session-economics, gateway/model-tiering]
---

Enterprise coding agent platforms at 1,000–50,000 developer scale generate
material costs: model inference tokens are the dominant variable cost, with
infrastructure (gateways, compute, storage, observability) as a smaller but
non-trivial fixed base. Finance and executive sponsors need a structured cost
model before approving a platform at this scale — not because the ROI is unclear,
but because the cost structure is unfamiliar (per-token pricing with high variance)
and the approval process requires a defensible number.

This node provides:
- A cost component taxonomy for all platform cost drivers
- Tiered usage assumption methodology (light / standard / heavy users)
- Per-developer unit cost formula
- Infrastructure baseline cost model
- ROI framing for finance approval
- Chargeback / cost attribution design for large multi-BU deployments

## Cost Component Taxonomy

All platform costs fall into four categories:

| Category | Driver | Variability |
|---|---|---|
| Model inference — input tokens | Developer prompts + code context injected per call | High — varies 10x between light and heavy users |
| Model inference — output tokens | Model-generated code, explanations, plans | High — depends on task type and model |
| Infrastructure — compute | Gateway (Lambda/ECS), runner (EC2/ECS/GKE), MCP servers | Medium — scales with active session concurrency |
| Infrastructure — storage/ops | CloudWatch logs, S3 (audit, indices), DynamoDB | Low — predictable; grows slowly with user count |

Model inference costs dominate at >80% of total platform cost for most deployments.
Infrastructure is typically 10-15% of total cost. Storage and ops are the remainder.

## Usage Tier Assumptions

Do not model all developers at the same usage level. Enterprise developer populations
distribute roughly as follows (calibrated against early enterprise deployments):

| Tier | % of developer population | Characteristics | Daily token consumption (input + output) |
|---|---|---|---|
| Light | 30–40% | Occasional use: explanation, documentation, specific bug queries | 20K–50K tokens/day |
| Standard | 40–50% | Regular use: code review, autocomplete, moderate agentic tasks | 100K–300K tokens/day |
| Heavy | 15–25% | Power users: full agentic sessions, large codebase context, long loops | 500K–2M tokens/day |

**Weighted average for planning:** Use a blended daily rate of 150K–250K tokens
per active developer across a mixed population. Adjust up for data science / quant
populations (heavy users dominate); adjust down for ops/infrastructure teams
(light use, shorter context).

**Active vs enrolled developers:** Not all enrolled developers use the platform
daily. Typical active fraction: 40–60% of enrolled developers on any given day.
Model peak concurrency (simultaneous sessions) at 15–20% of enrolled population
for capacity planning; model daily token consumption against active users, not
enrolled users.

## Per-Developer Unit Cost Formula

```
Monthly cost per active developer =
  (avg_daily_tokens_input × input_price_per_1M × 30)
  + (avg_daily_tokens_output × output_price_per_1M × 30)
  + (infrastructure_cost_per_month / active_developer_count)

Example (Claude Sonnet 4.6, standard-tier developer):
  = (200,000 × $3.00/1M × 30) + (50,000 × $15.00/1M × 30) + ($15 infra)
  = $18.00 + $22.50 + $15.00
  = $55.50/month per active developer
```

**Note on model pricing:** Model pricing changes frequently. Do not hard-code
prices in the model; parameterize them and source from the Bedrock pricing page
or the latest Anthropic pricing at plan approval time. The formula above is
illustrative; update with current prices before any finance submission.

**Cross-tier weighted average example** (1,000 enrolled, 550 active, mixed population):
- 200 light users × $20/month = $4,000
- 275 standard users × $55/month = $15,125
- 75 heavy users × $200/month = $15,000
- Infrastructure base = $25,000/month
- **Total: ~$59,000/month for 550 active developers (~$107/active developer)**

## Infrastructure Cost Baseline

Infrastructure costs for a standard single-region AWS deployment:

| Component | Service | Monthly estimate | Scales with |
|---|---|---|---|
| MCP gateway | API Gateway + Lambda | $3,000–$8,000 | API calls (session volume) |
| Agent runner | ECS Fargate / Lambda | $5,000–$15,000 | Active session concurrency |
| Session logging | CloudWatch Logs + S3 | $2,000–$5,000 | Log volume (token count proxy) |
| Code intelligence (RAG) | Bedrock Knowledge Bases + OpenSearch | $4,000–$12,000 | Index size (repo count × repo size) |
| Audit log WORM storage | S3 Object Lock | $500–$2,000 | Retention period × log volume |
| DynamoDB (session state) | DynamoDB on-demand | $500–$1,500 | Session count |
| Observability | CloudWatch dashboards + alarms | $500–$1,000 | Metric count |
| **Total infrastructure** | | **$15,500–$44,500/month** | |

For multi-region or federated deployments (multiple instances), multiply the
infrastructure base by the number of active instances. Shared components (OPA
bundle server, instance registry) add $1,000–$3,000/month regardless of instance count.

## Full-Scale Cost Projection Template

Use this structure for a finance submission covering phased rollout:

```
Phase 1 — Pilot (100–500 developers, 60 days)
  Inference: $X,XXX/month
  Infrastructure: $15,000–$20,000/month (fixed base)
  Total: $XX,XXX/month
  Per-developer: $XX–$XXX (infrastructure amortizes poorly at small scale)

Phase 2 — BU rollout (1,000–5,000 developers, 6 months)
  Inference: $XX,XXX–$XXX,XXX/month (scales linearly with active users)
  Infrastructure: $20,000–$50,000/month (grows sub-linearly)
  Total: $XXX,XXX/month
  Per-developer: $50–$100

Phase 3 — Enterprise scale (10,000–50,000 developers)
  Inference: $X,XXX,XXX/month
  Infrastructure: $100,000–$300,000/month
  Total: $X.X–$5M/month
  Per-developer: $40–$80 (infrastructure amortizes well at scale)
```

The per-developer cost decreases with scale because infrastructure is largely fixed.
This is an important point for finance: early phases have high per-developer cost
not because the platform is inefficient but because fixed infrastructure costs are
amortized over a small user base.

## ROI Framing

Finance approval requires ROI framing alongside the cost model. Standard developer
productivity ROI arguments:

**Productivity improvement evidence:**
- Published research (GitHub Copilot studies, McKinsey Digital): 20–55% reduction
  in time on coding tasks for AI-assisted developers
- Conservative enterprise estimate: 15–25% time savings on tasks in scope
- Task in-scope fraction: coding, code review, documentation, test writing
  (typically 40–60% of a developer's time for software engineers)
- Net productivity gain: 6–15% of total developer time

**Revenue equivalence framing:**
```
Developer fully-loaded cost: $150,000–$250,000/year (US software engineer)
  = $12,500–$20,800/month

10% productivity gain per developer:
  = $1,250–$2,080/month in productivity value per developer

Platform cost per active developer: $50–$100/month (at scale)

ROI ratio: 12x–40x (productivity value / platform cost)
```

This framing is conservative and credible. Do not claim 55% productivity improvement
for finance approval — use 10–15% and build credibility. Actual returns will
likely exceed the conservative estimate, which creates a positive surprise.

**Time-to-value considerations:**
- Developers typically reach productivity gains after 4–6 weeks of ramp-up
- Plan for a 3-month period where costs exceed realized productivity benefits
  (the investment window before ROI materializes)
- Build this into the Phase 1 cost projection: Month 1-3 costs without full
  productivity offset; Month 4+ costs with productivity gains offsetting platform cost

## Chargeback and Cost Attribution

For multi-BU enterprises, cost attribution is both a finance requirement and
a governance tool (BUs that see their costs are more engaged in usage governance).

**Attribution models:**

- **BU-level chargeback** — platform costs attributed to BUs based on actual
  token consumption per BU; monthly chargeback invoice to each BU's cost center;
  requires session logs to carry `business_unit` tag; CloudWatch metric filter
  or Athena query produces monthly consumption by BU; finance processes the chargeback
- **Flat per-developer allocation** — simpler; each BU is charged based on enrolled
  developer count regardless of actual usage; BUs don't have an incentive to
  govern usage; easier to operationalize but may cause resentment from low-usage BUs
- **Shared service with usage floor** — the platform is centrally funded up to
  a baseline usage level (e.g., 100K tokens/developer/day average); consumption
  above the baseline is charged back to the BU; encourages baseline adoption
  without penalizing teams for efficient use; heavy user BUs (data science, quant)
  pay the overage

**Attribution tagging requirements:**
- Session logs must carry `business_unit`, `team_id`, and `cost_center` as top-level
  fields; these are sourced from the developer's IdP claims at session init
- Bedrock inference invocations must carry the `business_unit` tag via the
  Bedrock `tags` parameter (if supported) or via CloudWatch custom metrics;
  enables cost attribution at the AWS billing level (not just in platform logs)
- Monthly cost attribution report: query CloudWatch metrics or Athena; aggregate
  tokens by `business_unit`; multiply by current model prices; produce CSV for
  finance; automate via a scheduled Lambda that emails the report to BU finance leads

**Cost anomaly detection:**
- CloudWatch Cost Anomaly Detection on the Bedrock spend metric — alert when
  daily inference spend exceeds 2x the rolling 7-day average; investigate before
  the bill arrives; common causes: runaway agentic loop, misconfigured context
  window size, a developer running batch jobs through the interactive agent
- Per-developer consumption alert — session analytics can surface outlier users
  (top 1% by daily token consumption); alert the platform team when a single
  developer consumes >10x the population average; may indicate misuse or a
  legitimate heavy-use case that needs a higher quota tier

## Finance Approval Process

The typical enterprise finance approval path for a platform in this cost range:

1. **Initial estimate** — platform team produces a range estimate (low/base/high)
   using the per-developer formula and tiered assumptions; no precision required
   at this stage; the goal is to size the ask and identify the right approval level

2. **Business case document** — 2-4 page document covering: cost model (phased),
   ROI framing (conservative), sensitivity analysis (what happens if adoption is
   50% of target), comparison to alternatives (per-seat SaaS products, staff
   augmentation), and proposed cost attribution model

3. **Finance review** — the finance sponsor reviews the business case; typical
   questions: "what happens to cost if adoption exceeds plan?" (answer: linear
   scaling with a known rate), "what's the kill switch if costs exceed budget?"
   (answer: quota controls per BU that can be tightened without platform redesign)

4. **Budget provisioning** — finance approves a budget envelope (typically annual
   with quarterly review); the platform team commits to staying within envelope
   and reporting monthly actuals vs plan; cost anomaly alerts are the early warning
   system for budget variance

5. **Quarterly review** — actual costs vs plan presented quarterly; per-developer
   unit cost trend (should decrease as scale increases); ROI evidence (if measurable:
   developer velocity metrics, PR throughput, defect rates)

## Principles

- Model the range, not a point estimate — token costs are highly variable between
  developers and task types; present a low/base/high range with named assumptions
  for each; a point estimate that turns out to be wrong destroys credibility;
  a range that the actual falls within builds trust
- Per-developer cost is the right unit for business stakeholders — total platform
  cost is a large number that can trigger sticker shock; per-developer cost
  ($50–$100/month) is comparable to SaaS tooling that executives already approve;
  always anchor the conversation at the per-developer level
- Quota controls are the cost governance mechanism — build per-BU and per-developer
  token quotas from the start; quota enforcement is not just for fairness, it is
  the mechanism that prevents an unexpected cost spike from breaching the budget
  envelope; demonstrate to finance that the cost is bounded by design
- Cost attribution drives usage governance — BUs that receive a monthly chargeback
  based on their actual consumption develop an organic interest in usage governance;
  they ask their developers to be efficient; they escalate outlier users; the
  platform team does not need to police usage if BU finance leads have visibility
  into their costs

## Stack Options

**Token consumption metering**
- CloudWatch custom metrics — emit `TokensConsumed` (input + output separately),
  `SessionCount`, `ActiveDevelopers` as custom metrics with `business_unit`,
  `team_id`, `model_id` dimensions; CloudWatch Math expressions compute
  per-developer and per-BU daily averages; these metrics feed both cost reporting
  and quota enforcement
- Bedrock Usage Reporting (native) — Bedrock provides model invocation logs with
  token counts natively; enable model invocation logging to S3; parse with Athena
  or Lambda; provides a cost source-of-truth independent of the platform's own
  logging (useful for audit purposes)

**Cost attribution and chargeback reporting**
- Amazon Athena on S3 session logs — session logs in S3 queried via Athena with
  `GROUP BY business_unit, model_id` to produce monthly token consumption tables;
  Lambda multiplies by current Bedrock prices and writes to a chargeback report
  in S3; finance accesses via QuickSight or downloads the CSV
- AWS Cost Explorer with resource tags — if Bedrock invocations are tagged with
  `BusinessUnit` at the API call level (via custom Bedrock request metadata),
  AWS Cost Explorer can break down Bedrock costs by business unit natively; cleaner
  than custom Athena queries but requires tagging discipline at the invocation level

**Cost anomaly detection**
- AWS Cost Anomaly Detection — configure a cost monitor on the Bedrock service
  with daily anomaly detection; alert threshold set at $500/day above expected;
  SNS notification to the platform team and finance lead on anomaly detection
- CloudWatch alarm on `TokensConsumed` metric — alarm triggers when daily token
  consumption exceeds 2.5× the 7-day rolling average; Lambda evaluates the alarm
  and posts a Slack message to the platform ops channel with the anomaly details

**Business case tooling**
- Cost model spreadsheet (Excel / Google Sheets) — parameterized model with
  input cells: developer count by tier, model price per 1M tokens, active fraction,
  infrastructure cost baseline; output: monthly cost by phase, per-developer cost,
  cumulative cost over 24 months; shareable with finance in a familiar format
- Jupyter notebook cost model — for data-science-heavy organizations; same
  parameterized model in Python; produces charts (cost vs developer count, cost
  per developer vs scale) for business case presentations

## Connects to

- [Session Economics](session-economics.md) — session economics covers real-time
  quota enforcement and per-session cost controls; this node covers planning-level
  cost modeling and finance approval; they share the same underlying token metrics
  but serve different audiences (finance vs platform ops)
- [Observability & Audit](observability.md) — the cost attribution reports are
  derived from session log data; the observability pipeline must emit
  `business_unit`, `token_counts`, and `model_id` as structured fields in every
  session log entry for cost attribution to work
- [Federation Governance](federation.md) — in federated multi-instance deployments,
  the cost model must aggregate across all instances; the hub governance layer
  collects per-instance token consumption metrics and rolls them up for enterprise-wide
  cost reporting; per-BU chargeback requires instance-level consumption data

## Sources

- [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) — to verify on first use — current model prices; update before any finance submission
- [GitHub Copilot research — developer productivity](https://github.blog/2022-09-07-research-quantifying-github-copilots-impact-on-developer-productivity-and-happiness/) — to verify on first use — 55% faster task completion in controlled study; use with caution in enterprise projections (controlled lab conditions vs real-world)
- [McKinsey Digital — developer productivity with generative AI](https://www.mckinsey.com/capabilities/mckinsey-digital/our-insights/unleashing-developer-productivity-with-generative-ai) — to verify on first use — 25–50% productivity improvement range; industry analyst framing for business case
- [AWS Cost Explorer cost anomaly detection](https://docs.aws.amazon.com/cost-management/latest/userguide/getting-started-ad.html) — to verify on first use — anomaly monitor configuration; alert thresholds; SNS integration
