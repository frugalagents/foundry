---
type: platform-component
title: Permission Engine
description: allow · deny · ask
group: harness
tags: [harness, permissions]
timestamp: 2026-08-12T00:00:00Z
status: stable
traversal: probe
trigger: [allow-deny-lists, granular-permissions, tool-whitelisting, least-privilege-tools]
decision-question: "How are per-tool allow/deny decisions made at runtime, and who controls the permission policy?"
decision-domain: approval_posture
priority: 7
requires: [access/guardrails]
---

Decides, for every tool call, whether to run it, block it, or ask a human —
driven by permission modes and allow/deny/ask rules. Hooks (pre-/post-tool-
use) plug in here as the concrete programmatic enforcement point, sitting
alongside static rules rather than replacing them.

## Decisions

**Default posture?**
- Ask on writes (safe default) — matches "file modification always
  requires approval unless a mode/rule relaxes it"
- Auto-approve in sandbox, gate external effects — trust the isolated
  execution environment internally, still prompt for anything crossing its
  boundary
- Full auto in CI / isolated envs — appropriate only where the blast radius
  is already contained by the environment itself

**Enforcement mechanism?**
- Rule allow/deny/ask lists, scoped to a tool, exact command, or specific
  argument value
- Pre-/post-tool-use hooks — programmatic, can inspect the actual call and
  decide dynamically rather than matching a static pattern
- Both together — see the combining rule below; hooks and static rules are
  not alternatives, they compose

## Principles

- **Explicit deny wins over allow, always.** When multiple hooks fire on
  the same event, every matching hook runs to completion, and the *most
  restrictive* answer wins — in order deny, defer, ask, allow. A hook
  returning "allow" cannot suppress another hook's "deny" on the same call.
- A hook signals block by exiting with a specific non-zero code (with a
  written reason that gets fed back so the agent can adjust its approach);
  a zero exit is not itself an approval — the normal permission flow still
  applies on top of it
- State-changing actions fail closed — absence of an explicit allow is not
  treated as permission
- Every decision is logged, allow or deny — a permission decision without
  an audit trail is not distinguishable from an accident later

## Stack Options

**Ask on writes (default posture) + rule allow/deny/ask lists**
- Claude Code — `default` permission mode prompts on first use of each
  write/execute tool; `permissions.allow`/`deny`/`ask` rules scope this down
  to exact commands/arguments, checked into version control.

**Auto-approve in sandbox, gate external effects**
- Claude Code — `acceptEdits` mode plus the sandboxed Bash tool together:
  file edits and common filesystem commands auto-approve inside the working
  directory/sandbox boundary; anything outside it still prompts.

**Full auto in CI / isolated envs**
- Claude Code — `bypassPermissions` mode, explicitly scoped to isolated
  environments (containers/VMs) since it skips prompts even for writes to
  otherwise-protected paths; a small set of circuit-breaker prompts
  (e.g. `rm -rf /`) still fire regardless.

## Connects to

- Enforcement point referenced by every [surface](../surfaces/ide.md) —
  same engine regardless of which surface triggered the call
- Complements [Guardrails & Policy](../access/guardrails.md)'s policy layer
  — guardrails define what's *permitted for a role/identity*, this engine
  is the runtime decision point that actually executes that policy per call
- Gates every tool invocation dispatched by the [Tool Runtime](runtime.md)

## Sources

- [Automate actions with hooks](https://code.claude.com/docs/en/hooks-guide) — checked 2026-08-12 — supports: PreToolUse hooks that can block a tool call before it executes, exit-code-2-to-block convention with a stderr reason fed back to the agent, multiple hooks on the same event all running to completion with the most-restrictive-decision-wins combining rule (deny > defer > ask > allow), and the explicit note that a zero exit from a PreToolUse hook does not itself approve the call — the normal permission flow still applies
- [Configure permissions](https://code.claude.com/docs/en/permissions) — checked 2026-08-12 — supports: `default`/`acceptEdits`/`bypassPermissions` as distinct permission modes, `bypassPermissions` skipping prompts even for otherwise-protected paths while circuit-breaker prompts (e.g. root/home directory removal) still fire
