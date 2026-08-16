---
type: platform-component
title: CI/CD Trigger
description: agent in the pipeline
group: surfaces
tags: [surfaces, automation, ci-cd]
timestamp: 2026-08-12T00:00:00Z
status: candidate
traversal: conditional
trigger: [ci-cd-automation, pr-automation, pipeline-agent, autonomous-review]
decision-question: "Should the agent run autonomously inside CI/CD pipelines or PR workflows?"
---

Agent invoked by pipelines — fix builds, bump dependencies, generate tests
on event or schedule, rather than in response to a person's direct request.
This overlaps with Chat/PR Bot's "automation mode" (no mention required) but
is worth treating as its own surface because the triggering context is a
pipeline event (a scheduled cron, a push, a build failure) rather than a
person posting a comment — the trust model and what tools are available by
default differ accordingly.

## Decisions

**Trust in the pipeline?**
- Suggest — opens a PR for humans to review and merge; the agent never
  commits directly
- Act — commits within guardrails, e.g. a scheduled job that pushes a fix
  directly rather than proposing one

**Tool/API access by default?**
- None until granted — a plain-text prompt has no shell or GitHub API access
  until the pipeline explicitly grants the tools the prompt needs
- Scoped MCP tools — grant only the specific read/write API calls the
  scheduled task needs (e.g. list commits, list issues) rather than broad
  shell access

**What triggers a run?**
- A specific event (push, PR opened, build failure)
- A schedule (e.g. daily report, dependency-bump sweep) — note that
  scheduled workflows typically only run from a default/main branch and may
  be disabled automatically after a long period of repository inactivity

## Principles

- Budget-capped runs — a turn limit and/or spend cap on every pipeline
  invocation, same reasoning as the CLI's headless-mode budget controls
  (see [CLI / Terminal](cli.md))
- No prod actions without approval — "Act" trust level should still gate
  anything touching production, even if it's trusted to commit to a working
  branch unattended
- CI must be able to actually observe the agent's own commits — some CI
  systems don't trigger workflows on commits authored by a default
  machine-identity token, which silently breaks "run tests on what the agent
  just pushed" unless configured to authenticate as a distinct identity
- Workflow-level timeouts and concurrency limits guard against a runaway
  scheduled job stacking up parallel runs

## Connects to

- Governed by the same [Identity & Access](../access/identity.md) model —
  which identity the pipeline's commits are authored as affects whether
  downstream CI even sees them
- Executes through whichever [sandboxing component](../exec/index.md) the
  platform uses for pipeline-triggered work

## Sources

- [Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions) — checked 2026-08-12 — supports: automation mode (prompt input, no tools until granted via allowedTools/settings), scheduled (cron) triggers with default-branch-only execution and auto-disable after 60 days of repository inactivity, `--max-turns` and workflow-level timeouts/concurrency controls for cost and runaway-job management, the specific failure mode where CI doesn't trigger on commits authored by the default GITHUB_TOKEN
