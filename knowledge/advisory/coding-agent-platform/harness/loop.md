---
type: platform-component
title: Agent Loop
description: reason ▸ act ▸ observe
group: harness
tags: [harness, core]
timestamp: 2026-08-12T00:00:00Z
status: stable
---

The core cycle: read context, plan, call the model, invoke a tool, observe
the result, repeat — until the goal is met or a checkpoint stops it. This
loop shape is consistent across coding agent products and SDKs; what
differs between platforms is how much autonomy is granted per task and
whether a run can be paused, resumed, or replayed.

## Decisions

**Autonomy per task?**
- Step cap before a human check — bounds how far the loop runs unattended
  before requiring a checkpoint
- Plan-first — approve the plan, then run; the review happens before
  execution starts rather than being interleaved with it
- Full auto within guardrails — no per-step human checkpoint, autonomy
  bounded entirely by [Guardrails & Policy](../access/guardrails.md) and
  the [Permission Engine](perms.md) rather than by a loop-level cap

**Resumable?**
- Checkpointed — pause, resume, replay from a saved point; needed for long-
  running or multi-day tasks and for recovering from an interrupted run
  without restarting from scratch
- Stateless — restart from scratch each invocation; simplest, but any
  interruption loses all progress in that run

## Principles

- Deterministic control flow around the model — the loop's structure
  (read → plan → act → observe → repeat) is fixed and predictable even
  though the model's decisions within each step aren't
- Interruptible and steerable mid-task — a human should be able to stop or
  redirect a run in progress, not only approve or deny before it starts
- The loop's autonomy setting and the Permission Engine's default posture
  should be reconciled deliberately, not left to imply each other — "full
  auto within guardrails" only means something if guardrails are actually
  configured to catch what a step cap would otherwise have caught

## Stack Options

**Plan-first**
- Claude Code (Plan Mode) — Claude researches and proposes a plan without
  editing; edits stay blocked until the plan is explicitly approved, at
  which point the session switches to whichever permission mode the
  approval choice specifies.

**Checkpointed (pause/resume/replay)**
- AWS Bedrock AgentCore Runtime — supports session stop/resume with a
  configurable idle-session timeout and max lifetime, plus persistent
  filesystem state across stop/resume cycles without needing external
  storage.

## Connects to

- Bounded by [Guardrails & Policy](../access/guardrails.md) and the
  [Permission Engine](perms.md), especially under "full auto" autonomy
- Consumes [Context](context.md) and, when configured, [Memory](memory.md)
  on each cycle
- Dispatches tool calls through the [Tool Runtime](runtime.md)
- Subagent delegation depth/fan-out policy (see [Subagents](../registry/subagents.md))
  should be reconciled with this loop's autonomy setting — a fully
  autonomous parent spawning uncapped subagents compounds risk

## Sources

- [Claude Code — Choose a permission mode](https://code.claude.com/docs/en/permission-modes) — checked 2026-08-13 — supports: Plan Mode as a distinct mode where Claude researches/proposes without editing, edits blocked until explicit plan approval, and approval exits plan mode into whichever permission mode was chosen
- [Host agent or tools with Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.md) — checked 2026-08-12 — supports: session stop/resume with configurable idle timeout and max lifetime, persistent filesystem state surviving stop/resume without external storage
- The general reason-act-observe loop shape itself (not autonomy/resumability specifics) remains an unsourced cross-product pattern claim, per the original architecture diagram's framing ("identical across Claude Code, the Agent SDK, and managed runtimes") — the two sources above corroborate the *decision options*, not the base loop-shape assertion.
