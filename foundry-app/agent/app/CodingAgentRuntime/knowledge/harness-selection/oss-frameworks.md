---
type: platform-component
title: OSS Agent Framework SDKs
description: SDK layer for building a custom harness — Strands, LangChain/LangGraph, PydanticAI, AutoGen, CrewAI, smolagents, Google ADK, Agno
group: harness-selection
tags: [harness-selection, oss, sdk, strands, langchain, pydanticai, autogen, crewai, smolagents, google-adk, agno, custom-build]
timestamp: 2026-08-16T00:00:00Z
status: candidate
traversal: conditional
trigger: [oss-framework, sdk, custom-harness, strands, langchain, langgraph, pydanticai, autogen, crewai, smolagents, google adk, agno, phidata, full control, build your own]
decision-question: "Does your team need to build and own a custom agent harness using an SDK, rather than deploying a pre-built one?"
decision-domain: harness_family
priority: 9
blocking: true
alternatives: [harness-selection/saas-products, harness-selection/coding-harnesses, harness-selection/managed-runtime]
implies: [gateway/mcpgw, gateway/modelgw]
---

## What This Node Covers

This node covers **OSS agent framework SDKs** — the primitives-and-assembly-required layer. You bring the engineering; the SDK provides model integration, tool dispatch, state management, and the agent loop skeleton. You wire them together and own the result.

**This is not the same as a pre-built coding harness.** If your team wants to configure and deploy something that already works — OpenCode, Pi, Cline, Codex CLI — see [OSS Coding Harnesses](coding-harnesses.md) instead. Framework SDKs are the right choice when pre-built harnesses cannot satisfy a specific architectural requirement, when you need custom orchestration logic, or when your platform team has the capacity to own the ops lifecycle.

The tradeoff in one sentence: framework SDKs give you full control at the cost of owning every design decision and the ongoing maintenance burden.

---

## SDK Options

| Framework | Stars | Lang | Model support | Core abstraction | MCP | Best fit |
|---|---|---|---|---|---|---|
| **Strands Agents** (AWS) | ~7k | Python/TS | Any (Bedrock, Anthropic, OpenAI, Gemini, Ollama, LiteLLM) | Model-driven loop; `@tool` decorator; hooks | Native | AWS stacks; minimal abstraction; AgentCore deployment |
| **LangChain / LangGraph** | ~40k | Python | Any (100+ via integrations) | Stateful graph (Pregel-inspired); typed state; durable checkpointing | Via `langchain-mcp-adapters` | Complex stateful workflows; maximum control; deep observability via LangSmith |
| **PydanticAI** | ~19k | Python | Any (OpenAI, Anthropic, Gemini, Bedrock, Groq, Mistral, Ollama) | Type-safe agent; Pydantic-validated tools and outputs; typed dependency injection | Native | Python teams that value end-to-end type safety; ships a first-party Coder harness (`clai`) |
| **AutoGen 0.4** (Microsoft) | ~60k | Python/.NET | Any (OpenAI, Azure, Anthropic, Gemini, Bedrock, Ollama) | Event-driven multi-agent; AgentChat team patterns; DockerCommandLineCodeExecutor | Via `autogen-ext` | Code execution workflows; research teams; Docker-sandboxed coding pipelines |
| **CrewAI** | ~57k | Python | Any | Role-based crews (sequential/hierarchical); Flows for event-driven control | Via `crewai-tools` MCPServerAdapter | Business-process framing; role-based agent teams; 100k+ certified developers |
| **smolagents** (Hugging Face) | ~29k | Python | Any (HF Hub, OpenAI, Anthropic, Bedrock via LiteLLM, Ollama) | `CodeAgent` — LLM writes Python as actions (~30% fewer steps); `ToolCallingAgent` for JSON tool calls | Via `ToolCollection.from_mcp()` | Research; open-weights models; code-as-actions paradigm; HuggingFace ecosystem |
| **Google ADK** | ~21k | Python/TS/Go/Java/Kotlin | Any (Gemini primary; Claude, OpenAI, Ollama via LiteLLM) | `LlmAgent` + WorkflowRuntime graph; Managed Agents (server-side code exec) | Via `McpToolset` | Google Cloud / Vertex AI; multi-language stacks (only SDK with Go/Java/Kotlin) |
| **Agno** (formerly PhiData) | ~42k | Python | 30+ providers | Agent + AgentOS (FastAPI backend, 50+ REST endpoints, JWT RBAC); multi-tenant SaaS runtime | Via `MCPTools` | Production multi-tenant agent platforms; BYOC deployment; teams building agent SaaS |
| **AG2** (community) | ~5k | Python | Any | Protocol-driven; Network + Hub + typed Channels; `TransitionGraph` workflows | Registry referenced | Greenfield projects wanting a cleaner AutoGen successor without Microsoft dependency |
| **OpenAI Agents SDK** | ~29k | Python | OpenAI-primary (100+ via compatible endpoints) | Agent + Handoff + Guardrail + Session; `SandboxAgent` for file/command work | Native (5 transports) | Teams already on OpenAI APIs; note: premium features (hosted MCP, Responses API) require OpenAI |
| **Custom build** | — | Any | Any | None | Your problem | Only when a named architectural requirement cannot be met by any framework primitive |

---

## Decisions

**Which SDK?**
- **AWS stack** → Strands Agents (native Bedrock, AgentCore deployment, minimal abstraction)
- **Complex stateful workflows + max observability** → LangGraph (durable execution, LangSmith, widest production adoption)
- **Type safety + clean DX** → PydanticAI (end-to-end Pydantic validation; also ships a ready-to-use Coder harness)
- **Code execution in Docker + research pedigree** → AutoGen 0.4 (DockerCommandLineCodeExecutor; most starred)
- **Role-based multi-agent teams** → CrewAI (sequential/hierarchical crews; Flows for deterministic control)
- **Code-as-actions + open-weights models** → smolagents (CodeAgent writes Python; 30% fewer LLM steps on complex tasks)
- **Google Cloud / Vertex AI** → Google ADK (Managed Agents with built-in code execution; only SDK with Go/Java/Kotlin)
- **Production multi-tenant SaaS platform** → Agno (AgentOS provides API, auth, tracing, BYOC out of the box)
- **OpenAI ecosystem** → OpenAI Agents SDK (SandboxAgent for coding; note provider dependency)
- **Custom** → only when a core requirement cannot be met by any framework primitive above

**How is the harness deployed?**
- Embedded in an existing service — simplest, no new infra
- Standalone microservice — independently scalable and deployable
- Serverless (Lambda, Cloud Functions) — event-triggered tasks; Lambda 15-min limit applies
- Managed (AgentCore, LangGraph Cloud, Agno AgentOS) — reduces ops burden while keeping custom code

**State and session management?**
- Framework-managed state (LangGraph checkpointing, Strands session, Agno Postgres) — use where it fits
- External store (Redis, DynamoDB, PostgreSQL) — required for cross-request state that must survive restarts

---

## Stack Highlights

**Strands Agents**
- `pip install strands-agents`; model-agnostic via Bedrock or direct clients
- Deploy: Lambda, ECS Fargate, or embedded FastAPI/Flask service; native AgentCore deployment
- MCP: native support; `@tool` decorator for Python tools
- Memory: integrates with AgentCore Memory for cross-session state

**LangChain / LangGraph**
- `pip install langchain langgraph`; large dependency surface; mature ecosystem
- Deploy: FastAPI + LangGraph server on ECS or Lambda; LangGraph Cloud for managed hosting
- MCP: `pip install langchain-mcp-adapters`; not in LangGraph core
- Memory: built-in checkpointing to Postgres / DynamoDB / Redis

**PydanticAI**
- `pip install pydantic-ai`; clean dependency surface; Pydantic Logfire for OTel tracing
- Bonus: ships `clai` CLI — a first-party coding harness with workspace file access, shell exec, and planning
- MCP: native `MCP('https://...')` attachment

**AutoGen 0.4**
- `pip install autogen-agentchat autogen-ext`; 50+ extensions
- `DockerCommandLineCodeExecutor`: run model-generated code in Docker with configurable image, timeout, GPU, volume mounting
- MCP: `mcp_server_tools()` in `autogen-ext`

**smolagents**
- `pip install smolagents`; ~1,000 lines of core — maximally hackable
- `CodeAgent`: LLM generates Python code as actions rather than JSON tool calls; ~30% fewer steps
- Sandboxing: E2B, Blaxel, Modal, or Docker — the built-in `LocalPythonExecutor` is NOT a security boundary
- MCP: `ToolCollection.from_mcp()`

**Deployment patterns on AWS**
- Lambda: 15-min timeout; best for step-capped tasks; cold start is the latency consideration
- ECS Fargate: no timeout; autonomous multi-hour agents; auto-scale on task queue depth
- App Runner: simplest stateless harness API; limited for stateful sessions

---

## Principles

- Framework SDKs give control at the cost of owning the full ops lifecycle: dependency upgrades, security patches, scaling, and failure handling are yours — this is the primary reason to evaluate pre-built harnesses first
- Model-agnostic frameworks (Strands, LangChain, PydanticAI) let you swap providers without rewriting agent logic — prefer them whenever multi-provider is a real requirement
- The framework's tool dispatch IS your tool runtime; pair it with the [Registry / Catalog](../registry/tools.md) for approved-tool governance
- "Agent = Model + Harness" — the SDK wires these together; you are responsible for every decision about what the model can do and what it cannot

---

## Connects to

- [OSS Coding Harnesses](coding-harnesses.md) — if the team wants a pre-built harness rather than assembling one from SDK primitives; evaluate this first
- [Managed Runtime](managed-runtime.md) — AgentCore: bring custom SDK code, AWS manages infra and compliance primitives
- [Tool Runtime](../harness/runtime.md) — the framework IS the runtime; this node gives the implementation options
- [Agent Loop](../harness/loop.md) — framework-specific loop patterns, termination conditions, and error handling
- [Registry / Catalog](../registry/tools.md) — approved tools wired into the framework's tool dispatch
- [Lifecycle Implications](lifecycle-implications.md) — nothing is pre-resolved when using a framework SDK; all platform nodes remain open

---

## Sources

- [Strands Agents documentation](https://strandsagents.com/latest/) — to verify on first use
- [LangChain Agents conceptual guide](https://docs.langchain.com/oss/python/langchain/agents) — checked 2026-08-12 — "Agent = Model + Harness" framing; tool dispatch and loop patterns
- [The Tool Nerd — 10 Agent Harnesses Every AI Builder Should Know](https://www.thetoolnerd.com/p/10-agent-harnesses-every-ai-builder) — 2026-06-25 — framework vs. harness distinction; harness layer model
