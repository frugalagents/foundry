---
type: platform-component
title: OSS Coding Harnesses
description: Pre-built open-source coding agent harnesses — OpenCode, Pi, Cline, Codex CLI, Goose, Aider, OpenHands, Mastra, Deep Agents, SWE-agent, Hermes
group: harness-selection
tags: [harness-selection, oss, coding-harness, opencode, pi, cline, goose, aider, codex-cli, swe-agent, mastra, deep-agents, hermes, openhands]
timestamp: 2026-08-16T00:00:00Z
status: candidate
traversal: conditional
trigger: [coding-harness, pre-built harness, opencode, pi agent, cline, goose, aider, codex cli, swe-agent, mastra, deep agents, hermes, openhands, open source harness]
decision-question: "Do you want a pre-built OSS coding harness (configure and deploy) rather than assembling one from a framework SDK?"
---

## Framework vs. Harness — Why the Distinction Matters

**Framework SDKs** (LangChain, AutoGen, Strands, PydanticAI) give you primitives — model, tool dispatch, agent loop — that you assemble into a harness. You own the wiring.

**Coding harnesses** are pre-assembled. Every harness ships the agent loop, execution layer (tools, sandboxing, file/git ops), and tool access model (MCP or proprietary) already connected. You configure and deploy rather than build.

The practical consequence: harness architecture influences outcome quality independently of model selection. The [SWE-bench leaderboard](https://www.swebench.com/) tracks performance across coding agents on real GitHub issues — consult it when evaluating harnesses for autonomous code-fix workflows.

**Choose a pre-built harness when:** your team wants to configure and deploy rather than build and maintain the agent loop. Choose a framework SDK when you need custom orchestration the harnesses don't support.

---

## OSS Harness Options

### OpenCode
- **Repo:** `opencode-ai/opencode` (archived; active development migrated to `charmbracelet/crush`) · **Stars:** ~14k · **License:** MIT
- **What it is:** Terminal coding agent with multi-provider model routing (OpenAI, Anthropic, Google, Bedrock, Groq, Azure, OpenRouter). Supports configurable agent roles (`coder`, `task`, `title`). The original repo is archived — verify the active repo (`charmbracelet/crush`) before adopting.
- **Execution:** Local filesystem + shell access; no explicit sandboxing mechanism documented
- **MCP:** Native — configured via `mcpServers` in config, supporting stdio and SSE connection types
- **Best for:** Teams that want a multi-provider terminal harness; verify against the active `charmbracelet/crush` repo for current feature set

### Codex CLI (OpenAI)
- **Repo:** `openai/codex` · **Stars:** ~106k · **License:** Apache 2.0
- **What it is:** OpenAI's open-source terminal harness — distinct from the OpenAI Agents SDK (which is a framework). Tied to the OpenAI ecosystem; authentication via OpenAI API keys or ChatGPT account.
- **Execution:** Built-in sandboxing (macOS Seatbelt + network-disable flag); file and shell access with `/permissions` control
- **MCP:** Native — `codex mcp` command connects local or remote MCP servers
- **Best for:** Teams in the OpenAI ecosystem wanting a vetted OSS terminal harness

### Pi
- **Docs:** https://pi.dev/docs/latest · **Repo:** `earendil-works/pi` · **Stars:** ~91k · **License:** MIT
- **What it is:** Deliberately minimal. Ships only four tools: Read, Bash, Edit, Write (confirmed in docs). Everything else is optional extension.
- **Execution:** Direct local shell; no built-in sandboxing — the docs explicitly state this and recommend operator-provided container, VM, or microVM isolation
- **MCP:** MCP Registry referenced in navigation; extension mechanism documented but MCP-specific integration details are sparse in current docs
- **Best for:** Teams that want maximum control and minimum abstraction; willing to add their own sandbox layer; performance-priority deployments

### Cline
- **Repo:** `cline/cline` · **Stars:** ~63k · **License:** Apache 2.0
- **What it is:** IDE extension (VS Code, JetBrains, Cursor, Windsurf, and others) + CLI + SDK. Used by millions of developers. Strong MCP integration — MCP servers are configured externally and expose tools alongside Cline's built-in tool set.
- **Execution:** IDE-managed; file ops via editor; shell execution with explicit approval flow required for every action
- **MCP:** Supported via configurable protocol layer (`mcp.json`); MCP tools surface alongside built-in tools
- **Best for:** Teams deploying coding agents inside the IDE surface rather than terminal; organizations that want MCP as the primary tool extensibility model

### OpenHands
- **Repo:** `OpenHands/OpenHands` · **Stars:** ~84k · **License:** MIT
- **What it is:** Full platform: browser-based web client (Agent Canvas), CLI, and REST/WebSocket APIs. Wraps and orchestrates other agents (Claude Code, Codex, Gemini, and ACP-compatible agents) as substrates. Best-positioned for always-on self-hosted deployments.
- **Execution:** Sandboxed execution environment; underlying mechanism not specified in top-level docs — verify before production deployment
- **MCP:** Via underlying agent substrate
- **Best for:** Enterprise teams that want a self-hosted platform layer on top of SaaS agents; multi-agent orchestration without building the coordination layer

### Goose
- **Repo:** `aaif-goose/goose` · **Stars:** ~52k · **License:** Open (Agentic AI Foundation)
- **What it is:** General-purpose OSS agent; governance transferred to the Agentic AI Foundation (AAIF). Coding-capable but not exclusively focused on it — use cases include coding, research, writing, automation, and data analysis.
- **Execution:** Primarily local (desktop app for macOS/Linux/Windows + CLI); extension-based connections to remote services
- **MCP:** Native — one of the earliest MCP adopters; 70+ extensions available via MCP
- **Best for:** Teams that want a general-purpose OSS agent with strong MCP ecosystem; organizations that want a coding-capable agent without a coding-only scope

### Aider
- **Repo:** `Aider-AI/aider` · **Stars:** ~48k · **License:** Apache 2.0
- **What it is:** Terminal pair programmer. Uniquely strong on git: automatic commits with descriptive messages, codebase mapping for large repos (100+ files), and self-fixing via linter/test feedback loops.
- **Execution:** Local filesystem + shell; no sandboxing — designed for developer-at-keyboard use
- **MCP:** Not supported
- **Best for:** Individual developers or small teams wanting terminal-native AI pair programming with deep git integration; not suitable as an orchestration substrate for autonomous pipelines

### Mastra
- **Repo:** `mastra-ai/mastra` · **Stars:** ~27k · **License:** Apache 2.0 (core); proprietary for enterprise `ee/` features
- **What it is:** TypeScript-native AI agent framework. Ships with a local Studio UI (accessible at `localhost:4111`) for visual development and testing of agents, workflows, and tools.
- **Execution:** Node.js runtime (v22+); TypeScript-first tooling
- **MCP:** Supported — can author MCP servers exposing agents and tools via the MCP interface
- **Best for:** TypeScript/Node.js shops; teams that want an agent framework in the same language as their application stack; differentiator vs. all other harnesses which are Python-first

### Deep Agents
- **Repo:** LangChain org · **Stars:** ~24k · **License:** MIT
- **What it is:** LangGraph-based harness built and maintained by the LangChain team. Designed for backend and pipeline deployment rather than interactive developer use. File system access for complex multi-step tasks.
- **Execution:** LangGraph durable execution; containerizable
- **MCP:** Via LangChain MCP adapters
- **Best for:** Teams already on LangGraph who want a pre-built harness rather than assembling one; CI/CD and pipeline automation use cases

### SWE-agent
- **Repo:** `SWE-agent/SWE-agent` · **Stars:** ~20k · **License:** MIT
- **What it is:** Purpose-built for the GitHub issues → code fix pipeline. Not a general-purpose harness — a configurable single-purpose system. Held state-of-the-art SWE-bench scores among OSS systems as of February 2025. **Note:** the main repo is now in maintenance mode; active development has shifted to `mini-swe-agent` — verify which to adopt.
- **Execution:** Repo access + shell; GitHub Codespaces supported for browser-based runs
- **MCP:** Not supported
- **Best for:** Autonomous issue resolution and PR generation; teams that want a battle-tested GitHub automation harness; benchmark reference implementation

### Hermes Agent
- **Repo:** Community OSS · **Stars:** — · **License:** Open
- **What it is:** Self-hosted, cost-optimized harness. Designed for cost-sensitive deployments; trades some capability ceiling for lower per-task cost.
- **Execution:** Self-hosted; bring-your-own infrastructure
- **MCP:** Not confirmed
- **Best for:** Cost-sensitive deployments; teams with infrastructure to self-host and cost-per-task as a primary constraint

---

## Decisions

**Which harness?**

| If your priority is... | Consider |
|---|---|
| Multi-provider terminal harness | OpenCode / charmbracelet/crush (verify active repo) |
| Minimal abstraction + maximum control | Pi |
| IDE-native + strongest MCP | Cline |
| Self-hosted platform with agent wrapping | OpenHands |
| TypeScript-native stack | Mastra |
| GitHub issue → PR automation | SWE-agent |
| Cost-sensitive self-hosted deployment | Hermes Agent |
| OpenAI ecosystem + OSS terminal | Codex CLI |
| Git-native terminal pair programming | Aider |
| LangGraph-based pipeline deployment | Deep Agents |

**Sandboxing posture?**
- Pi and Aider provide no built-in sandbox (Pi docs state this explicitly) — operator must layer container or microVM isolation
- Codex CLI has built-in sandboxing (macOS Seatbelt + network controls); Cline uses IDE-managed approval flows
- OpenCode and OpenHands have sandboxing referenced but the specific mechanism is not detailed in top-level docs — verify before production use
- For production multi-tenant or regulated workloads, pair any harness with a dedicated execution layer — see [Container Execution](../exec/container.md) and [microVM](../exec/microvm.md)

**Make or buy the harness?**
- Pre-built harness (this node) → fastest time to value; maintenance burden shifts to the harness project
- Framework SDK ([OSS Frameworks](oss-frameworks.md)) → full control; you own the ops lifecycle
- Managed runtime ([Managed Runtime](managed-runtime.md)) → compliance primitives without building the loop
- SaaS product ([SaaS Products](saas-products.md)) → zero infra; least control

---

## Principles

- Benchmark scores are task-set-specific — results vary by task corpus, model, and configuration. Run your own evals on representative tasks before committing to a harness for production; use the [SWE-bench leaderboard](https://www.swebench.com/) as a reference baseline
- Adoption signals (star counts) are a proxy for community support and issue triage velocity, not production suitability — star count alone does not predict pass rate or runtime performance
- Harness lock-in is real but recoverable: the agent loop, memory, and context patterns are harness-specific, but model choice and MCP tools remain portable
- The framework vs. harness distinction is not binary — Deep Agents and Mastra sit between the two; they are opinionated harnesses built on framework primitives

---

## Connects to

- [OSS Frameworks](oss-frameworks.md) — framework SDKs (Strands, LangChain, PydanticAI, AutoGen) for teams building a custom harness
- [SaaS Products](saas-products.md) — fully managed coding agent products (Claude Code Enterprise, Cursor, GitHub Copilot, Kiro)
- [Managed Runtime](managed-runtime.md) — Amazon Bedrock AgentCore and equivalents: compliance-grade runtime without the full build burden
- [Lifecycle Implications](lifecycle-implications.md) — what harness choice pre-resolves downstream
- [Container Execution](../exec/container.md) — sandboxing layer for harnesses without built-in isolation
- [MCP Gateway](../gateway/mcpgw.md) — tool access model; MCP support varies significantly across harnesses

---

## Sources

- [Pi docs](https://pi.dev/docs/latest) — canonical source; GitHub repo at `earendil-works/pi`
- [OpenCode repo](https://github.com/opencode-ai/opencode) — archived; active development migrated to `charmbracelet/crush`; verify current docs URL against active repo
- [Cline docs](https://docs.cline.bot/) — MCP integration model, approval flows, multi-IDE extension (VS Code, JetBrains, Cursor, Windsurf, and others)
- [OpenHands docs](https://docs.openhands.dev/overview/introduction) — repo at `OpenHands/OpenHands`; browser client + CLI + REST/WebSocket APIs
- [Goose docs](https://goose-docs.ai/) — repo at `aaif-goose/goose` (Agentic AI Foundation); 70+ MCP extensions
- [Aider docs](https://aider.chat/) — changelog at aider.chat/HISTORY.html; coding model leaderboard at aider.chat/docs/leaderboards/
- [Mastra docs](https://mastra.ai/docs) — TypeScript-native; repo at `mastra-ai/mastra`; Apache 2.0 core
- [SWE-agent docs](https://swe-agent.com/latest/) — main repo in maintenance mode; active development at `mini-swe-agent`
- [SWE-bench leaderboard](https://www.swebench.com/) — authoritative cross-harness benchmark on real GitHub issues; check weekly
- [Codex CLI docs](https://learn.chatgpt.com/docs/codex/cli) — official CLI docs; repo at `openai/codex`
