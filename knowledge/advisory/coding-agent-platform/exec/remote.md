---
type: platform-component
title: Execution — Remote
description: full ephemeral cloud VM/workspace, strongest host-level isolation
group: exec
tags: [exec, sandboxing, isolation]
timestamp: 2026-08-12T00:00:00Z
status: candidate
---

Runs the harness in a dedicated remote environment entirely separate from
the developer's own machine — a cloud-hosted virtual machine or a managed
web-based session — rather than locally or in a container on local hardware.
Provides the strongest separation among the non-microVM options: its own
kernel, and in cloud/microVM deployments its own virtualized hardware,
distinct from a container's shared-kernel model.

This is one of four sandboxing components (see `exec/index.md` for the
others — `local`, `container`, `microvm`) representing genuinely different
trust/cost tradeoffs, not options within a single setting.

## Decisions

**Self-managed or provider-managed remote environment?**
- Self-managed cloud instance or local hypervisor VM — full control, full
  operational burden of provisioning and securing it yourself
- Provider-managed hosted session (e.g. a vendor's cloud-based coding agent
  session) — each session runs in an isolated, provider-managed VM with a
  network proxy enforcing a default allowlist; no infrastructure to
  provision, at the cost of depending on the provider's isolation and
  egress policy
- Self-hosted managed environment — sessions route to infrastructure you
  provision, where isolation, egress control, and credential handling
  become your deployment's own responsibility rather than the provider's

**When is remote/VM-level isolation the right call over a container?**
- Evaluating genuinely untrusted code — no trust in the repository's own
  contents at all
- A security policy specifically requires kernel-level separation between
  the agent and the host, not just process-level containment
- No host-level approach (local sandbox or container) meets a compliance
  requirement that names VM-level isolation specifically

**Credential handling for repository access?**
- Token held inside the remote environment directly — simpler, but a
  compromised session has direct access to the long-lived credential
- Token held outside the sandbox by a separate proxy, with only scoped,
  session-specific credentials issued inside — stronger, since a
  compromised session never sees the long-lived credential at all

## Principles

- Strongest separation among host-adjacent options comes from a distinct
  kernel and virtualized hardware, not merely a distinct process or
  container — this is what remote/VM buys over container isolation
  specifically
- When using a provider-managed session, credential architecture matters
  as much as compute isolation: holding the long-lived token outside the
  sandboxed environment and issuing only scoped credentials inside is
  meaningfully stronger than passing the long-lived token in directly
- A self-hosted remote environment shifts isolation and egress-control
  responsibility onto the operator — don't assume "remote" alone implies
  "someone else is handling security"

## Connects to

- Strongest option among the four sandboxing tiers alongside
  [microVM](microvm.md) — choose between them based on whether per-session
  microVM-per-invocation or a longer-lived dedicated remote environment
  fits the workload better
- Same [Guardrails & Policy](../access/guardrails.md) /
  [Permission Engine](../harness/perms.md) enforcement still applies inside
  a remote environment

## Sources

- [Choose a sandbox environment](https://code.claude.com/docs/en/sandbox-environments) — checked 2026-08-12 — supports: a dedicated VM as the strongest separation option (own kernel, own virtualized hardware in cloud/microVM deployments), use cases specifically naming untrusted-code evaluation and compliance requirements for kernel-level separation, a provider-managed web-based session running each session in an isolated Anthropic-managed VM behind a network proxy enforcing a default allowlist, a separate proxy holding a GitHub token outside the sandbox while issuing scoped credentials inside it, and self-hosted routing shifting isolation/egress/credential responsibility to the operator's own infrastructure
