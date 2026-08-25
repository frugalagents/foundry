---
type: platform-component
title: Execution — Container
description: dev container or custom container, shared-kernel isolation
group: exec
tags: [exec, sandboxing, isolation]
timestamp: 2026-08-12T00:00:00Z
status: candidate
traversal: conditional
trigger: [container-isolation, devcontainer, shared-kernel-sandbox, reproducible-environment]
decision-question: "Do you need container-level isolation for agent code execution, and is a devcontainer approach sufficient?"
decision-domain: execution_boundary
priority: 8
alternatives: [exec/local, exec/microvm, exec/remote, exec/on-prem-runner]
---

Runs the whole harness process inside a Docker/OCI container rather than
directly on the host — isolates the full development environment (not just
Bash, unlike [Local](local.md)'s narrow per-command sandbox), at the cost of
requiring container infrastructure. Shares the host kernel, which is the key
distinction from [microVM](microvm.md)'s per-session separate-kernel
isolation.

This is one of four sandboxing components (see `exec/index.md` for the
others — `local`, `microvm`, `remote`) representing genuinely different
trust/cost tradeoffs, not options within a single setting.

## Decisions

**Dev container or custom container?**
- Dev container — a preconfigured, editor-managed container (e.g. via a
  `.devcontainer/` directory) with your project mounted in; standardizes an
  environment across a team, and a default-deny network firewall
  configuration can support running with reduced permission prompts for
  unattended work
- Custom container — any Docker/OCI image with your own network policy,
  mounted volumes, and seccomp profile; the common path for organizations
  with existing container infrastructure or CI runners already in place

**Network egress policy?**
- Default-deny with an explicit allowlist — supports safely running
  unattended with fewer permission prompts, since egress is what a firewall
  can actually stop even if permission checks are skipped
- Open — simpler, but removes the firewall as a backstop against a
  compromised or prompt-injected session exfiltrating data

**Layer the local per-command sandbox inside the container too?**
- Yes — the built-in Bash sandbox can run nested inside a container for
  per-command restriction on top of the container boundary (unprivileged
  containers need a specific nested-sandbox setting)
- No — rely on the container boundary alone

## Principles

- A container isolates the full environment, not just shell commands — file
  tools, MCP servers, and hooks are inside the boundary too, unlike a
  Bash-only local sandbox
- For anything running with reduced permission prompts, review what's
  mounted writable and what credentials/tokens are reachable inside the
  container — the same review that applies to any isolation approach
- A container shares the host kernel — this is real, not hypothetical:
  choose [microVM](microvm.md) instead when the isolation requirement is
  specifically "no shared kernel with other tenants"
- Standardizing a dev container across a team is a convention, not an
  enforcement boundary on its own — nothing stops running outside it unless
  paired with organizational device/software controls

## Connects to

- Complementary to, not a substitute for, [microVM](microvm.md) when the
  requirement is stronger than shared-kernel isolation
- Same [Guardrails & Policy](../access/guardrails.md) /
  [Permission Engine](../harness/perms.md) enforcement applies inside the
  container as anywhere else

## Sources

- [Choose a sandbox environment](https://code.claude.com/docs/en/sandbox-environments) — checked 2026-08-12 — supports: dev containers vs. custom containers as the two container-based options, a default-deny firewall dev-container example enabling safer unattended/reduced-permission-prompt operation, custom containers as the common path for orgs with existing container/CI infrastructure, layering the built-in Bash sandbox inside a container for additional per-command restriction, and containers sharing the host kernel as the explicit contrast point against VM/microVM-level isolation
