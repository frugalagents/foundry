---
type: platform-component
title: Execution — Local
description: direct execution on the developer's own machine, optionally OS-sandboxed
group: exec
tags: [exec, sandboxing, isolation]
timestamp: 2026-08-12T00:00:00Z
status: stable
traversal: mandate
decision-question: "What is your baseline execution environment for agent-driven code actions, and what OS-level sandbox applies?"
decision-domain: execution_boundary
priority: 6
alternatives: [exec/container, exec/microvm, exec/remote, exec/on-prem-runner]
advisory:
  slice: true
  fact-rules:
    - key: local_execution_requested
      value: true
      match-any: [local execution, local exec, run locally, developer laptop, developer laptops, local-only, workstation]
      fact-text: "At least one population or business unit is asking for local execution."
    - key: local_execution_scope
      value: non_regulated_only
      match-any: [non-regulated only, only for non-regulated, general repos only, not for regulated, excluding regulated, except regulated]
      fact-text: "Local execution, if allowed, is being scoped to non-regulated workflows."
  activate:
    requires-facts-all: [local_execution_requested]
  output:
    decision-focus: execution_boundary
    question:
      id: execution-boundary-local-scope
      text: "Should local execution be allowed for all repositories, or only for non-regulated populations with a separate controlled lane for sensitive code?"
      why-it-matters: "This determines whether the platform needs a split execution model instead of one default developer path."
      decision-domain: execution_boundary
    recommendation: "Do not lock in local execution as the universal default until you decide which repo classes and populations it actually applies to."
    options:
      - path: decision/execution-boundary/split-by-repo-class
        title: Split execution by repo class
        summary: Allow local execution for general engineering workflows but keep sensitive lanes on a separate controlled runtime.
        decision-domain: execution_boundary
        position: recommended
      - path: decision/execution-boundary/remote-default
        title: Remote controlled execution by default
        summary: Centralize execution to a controlled environment and keep local execution out of the default path.
        decision-domain: execution_boundary
        position: viable
  resolutions:
    - when-facts-all: [local_execution_requested, local_execution_scope=non_regulated_only]
      decision: "Local execution, if allowed, is limited to non-regulated or otherwise lower-sensitivity workflows."
---

Runs commands directly on the machine the harness is invoked from — fastest,
full access to the local filesystem and network by default, hardest to
govern centrally. "Local" doesn't have to mean unconstrained: an OS-level
sandbox can restrict what a command touches without leaving the host
machine or requiring a container.

This is one of four sandboxing components (see `exec/index.md` for the
others — `container`, `microvm`, `remote`) representing genuinely different
trust/cost tradeoffs, not options within a single setting.

## Decisions

**Constrained or unconstrained local execution?**
- Unconstrained — full local access, fastest, no setup; appropriate only
  for fully-trusted internal tooling on the developer's own machine
- OS-level sandboxed Bash — the operating system (Seatbelt on macOS,
  seccomp/bubblewrap on Linux/WSL2) restricts filesystem and network access
  per-command, without a container
- Sandboxed runtime wrapping the whole process — extends the same OS-level
  boundary to cover file tools, MCP servers, and hooks too, not just shell
  commands

**What's covered by the sandbox boundary, if enabled?**
- Bash commands and their child processes only — the narrowest option;
  built-in file tools and MCP servers still run unconstrained on the host
- The whole process — file tools, MCP servers, and hooks all inside one
  boundary; necessary before running unattended with reduced permission
  prompts

## Principles

- A per-command Bash sandbox alone is not sufficient for fully unattended
  runs — MCP servers and hooks are separate processes that stay
  unconstrained unless the whole process is wrapped
- Isolation does not change what's sent to the model — prompts and file
  contents still reach the model provider whether or not a sandbox is
  enabled; a sandbox limits blast radius on the machine, not data exposure
  to the model
- Isolation reduces impact, it doesn't eliminate risk — network egress can
  still leak readable data, and a writable mounted project directory can
  still be modified even inside a sandbox
- Running with reduced permission prompts on the local host without any
  isolation boundary is the combination to avoid — the isolation boundary
  is what protects the system once prompts stop catching mistakes

## Connects to

- Complements, doesn't replace, [Guardrails & Policy](../access/guardrails.md)
  and the [Permission Engine](../harness/perms.md) — permission rules stop
  the agent from attempting an action; the sandbox boundary stops a command
  (or a prompt-injected one) from reaching outside it even if the agent's
  own decision-making was bypassed

## Sources

- [Configure the sandboxed Bash tool](https://code.claude.com/docs/en/sandboxing) — checked 2026-08-12 — supports: OS-level sandboxing via macOS Seatbelt (built-in) and Linux/WSL2 seccomp/bubblewrap, filesystem and network access restricted per Bash command and child process
- [Choose a sandbox environment](https://code.claude.com/docs/en/sandbox-environments) — checked 2026-08-12 — supports: the distinction between the narrow Bash-only sandbox and a sandbox runtime that wraps the whole process (file tools, MCP servers, hooks); the explicit warning that isolation reduces but doesn't eliminate risk, and doesn't change what's transmitted to the model provider; unattended/reduced-prompt runs needing a real isolation boundary rather than running directly on an unconstrained host
