---
type: platform-component
title: Chat / PR Bot
description: Slack · Teams · PR
group: surfaces
tags: [surfaces, async]
timestamp: 2026-08-12T00:00:00Z
status: candidate
traversal: conditional
trigger: [non-developer-users, slack-teams-integration, pr-review-bot, async-collaboration]
decision-question: "Do non-developer stakeholders or async PR workflows need a chat or bot surface?"
decision-domain: surface_strategy
priority: 7
implies: [gateway/mcpgw, ops/observability]
---

Async surface to kick off tasks, review PRs, and approve actions from where
teams already talk — mentioned in a comment or issue rather than invoked
directly by a developer sitting at a terminal or editor. The defining trait
of this surface is that the triggering event and the response are decoupled
in time: someone posts a request, the agent may take a while, and progress
appears as an update to that same thread rather than a live session.

## Decisions

**Trigger model?**
- Mention-based (e.g. `@claude` in an issue/PR comment or review) — the agent
  waits for an explicit mention rather than acting on every event
- Prompt-driven automation (no mention required) — the agent runs
  unconditionally on a given event (e.g. every PR opened, or a cron schedule),
  subject only to access checks, not a trigger phrase

**How autonomous on PRs?**
- Advisory — comments only, a human always takes the merge action
- Gating — can block merge via a check/status, but doesn't merge itself
- Author — opens its own PRs and pushes commits directly

**Who is allowed to trigger a run?**
- Anyone who can comment — simplest, but risky if the repo is public
- Write-access users only — the triggering actor must already have write
  access to the repository
- Explicit allowlist beyond write-access — for specific non-write users or
  bots that should be trusted to trigger runs, without granting them write
  access generally

## Principles

- Every action links to an audit ID / links back to the triggering
  comment or event — a human reading the thread later should be able to
  trace what the agent did and why
- Long jobs run async and notify on completion rather than blocking the
  surface — this is inherent to the surface's decoupled-in-time nature, not
  an optimization
- Reject bot-authored triggers by default (explicit allowlist to override) —
  prevents an agent's own actions from triggering itself in a loop
- Results from a mention-triggered run post as a comment on the same
  thread; results from a schedule/automation-triggered run without a mention
  post to a run log instead, since there's no thread to reply to

## Connects to

- Same [Permission Engine](../harness/perms.md) as other surfaces
- Governed by the same [Identity & Access](../access/identity.md) model —
  the write-access check above is an identity/entitlement decision, not a
  surface-specific one

## Sources

- [Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions) — checked 2026-08-12 — supports: mention-based trigger phrase vs. prompt-driven automation mode as two distinct run models, write-access + human-actor checks before a triggering user can start a run (with an allowlist escape hatch for non-write users and bots), mention-triggered results posting as a comment on the triggering thread vs. automation-mode results going to the workflow run log, audit-linkable triggering event
