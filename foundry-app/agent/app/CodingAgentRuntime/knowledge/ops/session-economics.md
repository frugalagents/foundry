---
type: platform-component
title: Session Economics
description: per-session cost ceilings, duration caps, and compaction checkpoints
group: ops
tags: [ops, cost, session-economics, session-cap, long-running-sessions]
timestamp: 2026-08-13T00:00:00Z
status: candidate
traversal: conditional
trigger: [session-cost, long-running-sessions, session-budget, runaway-session, cost-per-session]
decision-question: "How will you prevent a single long agentic session from consuming a developer's entire monthly quota, and what recovery path exists when a session hits its ceiling?"
---

A long agentic session is qualitatively different from a short query. Context
fills, tool calls compound, and cost grows non-linearly without a ceiling.
Session economics designs per-session controls before a developer discovers a
$50 session charge in their quota report.

## The Cost Structure of a Long Session

A typical short task (code review, single-file edit): cents.

An uncapped multi-hour agentic session filling a 200K-token context with hundreds
of tool calls at Opus-class pricing: $10–$50+ per session. Multiply by a team of
20 developers running parallel sessions and a monthly quota disappears in hours.

Per-session controls are a complement to monthly quotas, not a duplicate:
- Monthly quota: prevents total org spend from exceeding budget
- Session ceiling: prevents a single runaway task from consuming a developer's
  entire monthly allowance in one sitting

## Decisions

**Per-session cost ceiling?**
- None — rely on monthly quota; simplest; single runaway session can consume
  a large fraction of a monthly cap before the monthly alert fires
- Soft ceiling — warn developer at threshold (e.g., $5 spent in this session),
  allow continuation with acknowledged warning
- Hard ceiling — block new model/tool calls when session cost exceeds limit;
  developer must checkpoint and restart; disruptive if done without clear
  recovery path

**Session duration cap?**
- None
- Idle timeout — terminate after N minutes of inactivity; prevents abandoned
  sessions consuming context-held state
- Wall-clock cap — maximum session duration regardless of activity; forces
  context compaction and restart; useful for very long autonomous tasks

**Context compaction strategy?**
- Manual — developer triggers compaction explicitly; relies on developer awareness
- Automatic threshold — compact when context reaches X% of window; must preserve
  in-flight reasoning; see [Context](../harness/context.md) for compaction patterns
- Checkpoint and resume — serialize current progress to [Memory](../harness/memory.md)
  or an external store at checkpoints; allows cost-controlled long tasks with
  recovery after a session ceiling hit

**How are session costs attributed?**
- Per-developer session log — aligns with quota enforcement; developer can see
  their session history
- Per-team session aggregate — for chargeback reporting
- Both — recommended for full cost visibility at individual and team level

## Stack Options

**Per-session cost ceiling (SaaS)**
- Claude Code enterprise spend limits — per-user and per-group monthly caps
  enforced by the admin console; alert + throttle + hard-block levels
  configurable; the simplest option if Claude Code is the harness; session-
  level granularity is within the monthly cap

**Per-session cost ceiling (custom on AWS)**
- DynamoDB atomic counter — increment on every model call in the session with
  the token cost; check against the ceiling before dispatching; write is
  atomic so concurrent calls don't race past the limit; Lambda handles the
  check and block logic
- Amazon API Gateway usage plans — enforce request-rate ceilings per developer
  key; blunt (request count, not cost) but simple and enforced at the
  infrastructure layer without custom code

**Session duration cap**
- AWS Lambda timeout (serverless harness) — hard wall-clock limit built in;
  session terminates when Lambda times out; not graceful, so pair with
  checkpoint-before-timeout logic
- AgentCore session TTL — configure session idle timeout and max duration via
  the runtime API; sessions expire gracefully with a final event for the
  harness to checkpoint state
- Custom watchdog Lambda — EventBridge scheduled rule fires every N minutes;
  checks session age and cost in DynamoDB; sends a "soft ceiling" event to
  the session if thresholds are approaching; terminates if hard ceiling is hit

**Context compaction checkpoint**
- Claude Code automatic compaction — Claude Code handles context compaction
  natively when the window approaches its limit; operator can configure
  compaction threshold
- AgentCore Memory session checkpointing — serialize in-progress session
  state to AgentCore Memory at defined intervals; resume from the latest
  checkpoint if the session hits a ceiling or times out
- Custom Lambda + S3 — at a defined token count or time interval, the harness
  summarizes the current session state to S3 and restarts the context window
  with the summary as the new opening; full control, more implementation cost

**Session cost attribution**
- Amazon CloudWatch custom metrics — publish `session_cost_usd`, `session_id`,
  `developer_id`, `team_id` as dimensions on every model call; query with
  CloudWatch Insights for per-team chargeback reports
- AWS Cost Explorer tags — tag all Bedrock inference calls with session and
  team tags; roll up in Cost Explorer for chargeback; simpler reporting,
  less real-time resolution than custom metrics

## Principles

- Session ceilings and monthly quotas are complementary — set both; don't
  assume one substitutes for the other
- A hard session block with no recovery path destroys developer trust — pair
  every ceiling with a clear "here is how you resume" message and a checkpoint
  mechanism
- Compaction checkpoints are the mechanism that makes long autonomous tasks
  cost-tractable — design them as a first-class feature of your long-running
  agent workflows, not as an emergency measure
- Developer experience: a developer should be able to see their running session
  cost in the IDE surface before hitting a ceiling — proactive visibility reduces
  surprise friction more than post-hoc alerts

## Connects to

- [Quota & Rate Limits](../access/quota.md) — session ceiling is a sub-unit of
  the monthly quota; both must be configured consistently so a session ceiling hit
  is always ≤ the monthly cap remainder
- [Token Economics](../ops/token.md) — prompt cache stability and context right-
  sizing directly reduce per-session cost; address those before tuning the ceiling
- [Context](../harness/context.md) — context compaction is the mechanism for
  making long sessions tractable; session economics sets the policy, context
  management provides the implementation
- [Cost Management](../ops/cost.md) — session-level attribution feeds team
  chargeback and cost-per-task reporting
