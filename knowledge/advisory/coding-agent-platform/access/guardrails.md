---
type: platform-component
title: Guardrails & Policy
description: filtering · approvals · DLP
group: access
tags: [access, governance, policy]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

Screens each tool call on the way in and blocks or redacts policy violations,
drives human-approval gates, and keeps secrets/PII out of the model. In
practice this is a tiered permission system rather than one on/off switch:
different tool types (read-only, shell, file-write) carry different default
approval requirements, and rules can be scoped down to a specific command or
argument rather than an entire tool.

## Decisions

**Human-approval line?**
- Any file write (strict) — every edit prompts, matching the default
  behavior where file modification always requires approval unless a mode
  or rule says otherwise
- Only merges / prod (balanced) — trust routine edits, gate only the
  actions with real external effect
- Trust in sandbox, gate external effects — an isolated execution
  environment can auto-approve internally, while anything crossing the
  sandbox boundary still prompts

**Enforcement mechanism?**
- Rule allow/deny/ask lists, scoped by tool, exact command, or argument
  value (e.g. deny a specific Bash command pattern, allow a specific MCP
  tool) — declarative, checked into version control, shared across a team
- Hooks (pre-tool-use) that evaluate permissions at runtime with custom
  logic — necessary when a decision depends on something a static rule
  can't express
- Both together — a hook's block decision takes precedence over an allow
  rule, but a hook cannot override an explicit deny/ask rule; deny always
  wins regardless of what a hook returns

**On violation?**
- Block — the call never executes
- Redact & continue — strip the violating content, let the rest through
- Warn & log — allow it, but ensure it's visible for later review

## Principles

- Deny-first precedence: an explicit deny rule blocks a call regardless of
  what any hook or allow rule says. Nothing overrides deny.
- Default-deny on state-changing actions — read-only tool calls don't
  require approval; anything that writes or executes does, unless a mode or
  rule explicitly relaxes that
- Secrets never enter the prompt; scan tool input/output for PII rather than
  trusting the model not to echo it
- One policy engine, every surface — no bypass. A surface-specific
  exception is a policy gap, not a feature
- Permission rules and execution-environment sandboxing are complementary,
  not redundant: permission rules stop the agent from attempting an action;
  sandbox boundaries stop a Bash command (or a prompt-injected one) from
  reaching outside the boundary even if the agent's own decision-making was
  bypassed. Use both — neither substitutes for the other.

## Stack Options

**Rule allow/deny/ask lists + hooks (both together)**
- Claude Code — declarative permission rules (`permissions.allow`/`deny`/`ask`
  in settings files) plus PreToolUse hooks for dynamic runtime checks; deny
  always wins over any hook or allow rule.
- AWS Bedrock AgentCore Policy — Cedar-based policy engine attached to a
  Gateway, with a `LOG_ONLY` mode (evaluates and logs, doesn't block) for
  safe rollout before switching to `ENFORCE`; `forbid` statements override
  `permit` (same deny-first precedence, different syntax).

**Trust in sandbox, gate external effects**
- Claude Code's sandboxed Bash tool + `acceptEdits` mode — auto-approves
  file edits and common filesystem commands inside the working directory,
  while anything reaching outside the sandbox boundary or working-directory
  scope still prompts.

## Connects to

- Same [Permission Engine](../harness/perms.md) enforcement point
  referenced by every surface
- Governed by the same [Identity & Access](identity.md) model — which
  identity is calling affects which rules apply
- Complements whichever [sandboxing component](../exec/index.md) the
  platform runs code in — see the sandboxing principle above

## Sources

- [Configure permissions](https://code.claude.com/docs/en/permissions) — checked 2026-08-12 — supports: tiered approval requirements by tool type (read-only vs. Bash vs. file modification), permission modes (default/acceptEdits/plan/auto/dontAsk/bypassPermissions), rule syntax scoped to exact commands/arguments, deny-first precedence that a hook cannot override, PreToolUse hooks as a runtime enforcement extension point, permissions and sandboxing as complementary defense-in-depth layers
- AgentCore Policy implementation guide (`get_policy_guide`, fetched live via the bedrock-agentcore MCP server, no stable public URL captured — flag for a follow-up Tier A source once a docs URL is confirmed) — checked 2026-08-13 — supports: Cedar-based policy engine with `forbid` overriding `permit` (deny-first precedence), `LOG_ONLY` vs `ENFORCE` gateway attachment modes for safe rollout
