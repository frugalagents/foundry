---
type: platform-component
title: Tools & Plugins
description: file · shell · git · search
group: registry
tags: [registry, tools]
timestamp: 2026-08-12T00:00:00Z
status: candidate
traversal: conditional
trigger: [custom-tools, tool-integration, file-shell-git, specific-tool-set]
decision-question: "What built-in and custom tools will agents be permitted to invoke, and under what conditions?"
decision-domain: registry_governance
priority: 7
requires: [registry/registry, access/guardrails]
---

The capabilities the harness invokes directly — file edit, shell, git,
search — and plugins that extend them. Pulled from the registry per the
agent's grant, not available simply because the harness could technically
call them.

## Decisions

**Tool granting model?**
- Allowlist per agent — explicit, easiest to audit, doesn't scale to many
  agents with slightly different needs
- Scope-based — a role or context decides which tools are available,
  scales better than per-agent lists
- Arg-level policy on sensitive tools — not just "can this agent use Bash"
  but "can this agent run this specific command" — the finer-grained end of
  the same idea, letting a rule match an exact command or a specific
  argument value rather than gating the whole tool

## Principles

- Read and write tools separated and separately entitled — reading a file
  and writing one are different risk levels and should be grantable
  independently
- Least capability by default — a tool isn't available until granted, not
  available until explicitly denied
- Tool-name and argument-level rules should be able to target an exact
  command or argument value, not just an entire tool — coarse allow/deny at
  the tool level is necessary but often not sufficient (e.g. "allow git
  commit, deny git push" needs finer granularity than "allow git")

## Connects to

- Loaded from the [Registry / Catalog](registry.md) per the agent's grant
- Enforced by [Guardrails & Policy](../access/guardrails.md) at the actual
  call site — this component defines what's grantable, guardrails decide
  what's allowed for a given call

## Sources

- [Configure permissions](https://code.claude.com/docs/en/permissions) — checked 2026-08-12 — supports: tiered approval by tool type (read-only vs. write vs. shell), rule syntax that can scope to an exact command or a specific argument value rather than only the whole tool, least-capability-by-default posture where file modification always requires approval unless a mode/rule relaxes it
