# AgentCore Component Mapping — Platform Fabric Roles

## Purpose

This document maps all 12 AgentCore components to their roles within an enterprise agent platform fabric. Each component is described with its function, tier placement, fabric role, and framework compatibility. Use this as the canonical reference when designing platform architectures that leverage AgentCore.

**Audience**: Platform architects, VP of Engineering, solutions architects designing agent platforms.

**Usage by LLM**: When a customer asks about a specific AgentCore capability, or when mapping platform requirements to AWS services, reference this document for precise component-to-role mapping.

---

## Component Overview

AgentCore provides 12 managed components that together form a complete agent platform fabric:

| # | Component | One-Line Summary |
|---|-----------|-----------------|
| 1 | Runtime | Agent execution environment (serverless, session isolation, multi-framework) |
| 2 | Memory | Managed short-term + long-term agent memory |
| 3 | Gateway | Tool connectivity (MCP server hosting, API access) |
| 4 | Identity | OAuth2 for agents, delegated auth, user-on-behalf-of |
| 5 | Code Interpreter | Sandboxed code execution for agents |
| 6 | Browser | Managed web interaction for UI agents |
| 7 | Observability | Traces, metrics, logging for agent runs |
| 8 | Payments | Agent commerce, billing, metering |
| 9 | Evaluations | Managed eval pipelines, judge models |
| 10 | Policy | Guardrails + Automated Reasoning (formal verification) |
| 11 | Registry | Agent catalog, discovery, versioning |
| 12 | Harness | Testing framework, CI/CD integration |

---

## Component 1: AgentCore Runtime

### What It Does
Provides a fully managed, serverless execution environment for AI agents. Handles compute provisioning, session isolation, state management, and lifecycle execution. Supports multiple agent frameworks simultaneously — teams using different frameworks can share the same platform infrastructure.

### Key Capabilities
- Serverless execution (no server provisioning or management)
- Session isolation (agents don't interfere with each other)
- Multi-framework support (Strands SDK, LangGraph, CrewAI, AutoGen/AG2, Semantic Kernel, LlamaIndex Agents)
- State persistence across multi-turn conversations
- Warm session pools for low-latency repeated invocations
- Canary deployments and version management
- Auto-scaling based on demand

### When You Need It (Tier Mapping)

| Tier | Need |
|------|------|
| **Tier 1 (Foundation)** | Always needed — this is the execution environment. Every agent needs somewhere to run. |
| **Tier 2 (Scale)** | Multi-framework hosting becomes critical when 4+ LOBs have different framework preferences. |
| **Tier 3 (Optimize)** | Advanced features: warm pools, canary deployments, cross-region failover. |

### Fabric Role
**Compute Plane** — The execution substrate on which all agents run. Analogous to ECS/EKS for microservices, but purpose-built for agent workloads (long-running, stateful, LLM-calling).

### Framework Support
| Framework | Support Level |
|-----------|--------------|
| Strands SDK | Native (first-class) |
| LangGraph | Full support |
| CrewAI | Full support |
| AutoGen/AG2 | Full support |
| Semantic Kernel | Full support |
| LlamaIndex Agents | Full support |
| Custom Python | Full support |

### Integration Points
- Receives agent code/config from CI/CD pipelines (CodePipeline, CodeBuild)
- Connects to Bedrock for model inference
- Uses AgentCore Memory for state
- Emits telemetry to AgentCore Observability
- Enforces AgentCore Policy guardrails on every invocation
- Accesses tools through AgentCore Gateway

---

## Component 2: AgentCore Memory

### What It Does
Provides managed short-term and long-term memory for agents. Short-term memory maintains conversation context within a session. Long-term memory persists knowledge, user preferences, and learned patterns across sessions and even across agent instances.

### Key Capabilities
- **Short-term memory**: Conversation history, working context, tool results within a session
- **Long-term memory**: Cross-session persistence, user profiles, learned preferences
- **Semantic memory**: Vector-based recall of relevant past interactions
- **Episodic memory**: Time-ordered event recall
- **Shared memory**: Multiple agents can read/write to shared memory spaces
- **Memory management**: TTL, capacity limits, relevance decay

### When You Need It (Tier Mapping)

| Tier | Need |
|------|------|
| **Tier 1 (Foundation)** | Short-term memory (conversation context) — needed for any multi-turn agent. |
| **Tier 2 (Scale)** | Long-term memory for personalization, cross-session continuity. |
| **Tier 3 (Optimize)** | Shared memory across agents, semantic recall, sophisticated memory management. |

### Fabric Role
**State Management** — Provides the "memory" component of the cognitive architecture. Prevents agents from being stateless (starting fresh every time) while managing the cost and complexity of state.

### Framework Support
All frameworks supported. Memory is exposed as an API that any framework can call. Framework-specific memory adapters translate between framework conventions and AgentCore Memory APIs.

### Integration Points
- AgentCore Runtime manages memory lifecycle per session
- Bedrock Knowledge Bases complement Memory (KB = external knowledge, Memory = agent experience)
- AgentCore Observability logs memory operations for debugging
- DynamoDB / ElastiCache as backing stores (managed by AgentCore)

---

## Component 3: AgentCore Gateway

### What It Does
Provides managed tool connectivity for agents. Hosts MCP servers, manages API access, handles authentication to external systems, and provides a unified tool registry. Agents discover and invoke tools through the Gateway regardless of where those tools live.

### Key Capabilities
- **MCP server hosting**: Deploy and manage MCP servers as managed endpoints
- **Dynamic tool discovery**: Agents find available tools at runtime
- **API access management**: Rate limiting, auth, retry policies for external APIs
- **Tool versioning**: Multiple versions of tools coexist
- **Access control**: Per-agent, per-team tool permissions
- **Monitoring**: Tool invocation metrics, latency, error rates
- **Circuit breaking**: Automatic failover when tools are unhealthy

### When You Need It (Tier Mapping)

| Tier | Need |
|------|------|
| **Tier 1 (Foundation)** | Basic tool connectivity — agents need to call APIs and use tools. |
| **Tier 2 (Scale)** | Shared tool library across teams, access control, versioning. |
| **Tier 3 (Optimize)** | Dynamic discovery, circuit breaking, cross-agent tool sharing. |

### Fabric Role
**Integration Plane** — The universal connector between agents and the outside world. Analogous to API Gateway for microservices, but with MCP protocol support, dynamic discovery, and agent-aware access control.

### Framework Support
All frameworks supported. MCP is framework-agnostic by design. Any framework that speaks MCP (all major frameworks do) can use Gateway-hosted tools.

### Integration Points
- AgentCore Runtime routes tool calls through Gateway
- AgentCore Identity provides auth tokens for external system access
- AgentCore Observability traces tool invocations
- AgentCore Policy can intercept and validate tool calls before execution
- External systems: Databases, SaaS APIs, on-prem systems, other cloud services

---

## Component 4: AgentCore Identity

### What It Does
Provides OAuth2-based identity management for agents. Manages agent credentials, supports delegated auth (acting on behalf of users), and provides the identity mesh that enables secure agent-to-agent and agent-to-system communication.

### Key Capabilities
- **Agent identity**: Each agent gets its own OAuth2 identity (not a shared service account)
- **Delegated auth (user-on-behalf-of)**: Agents inherit user permissions for specific actions
- **Credential management**: Automated rotation, secure storage, least-privilege
- **Agent-to-agent auth**: Secure communication between agents using identity tokens
- **Audit trails**: Every auth decision logged — who authorized what, when, why
- **Permission boundaries**: Fine-grained control over what each agent can access
- **Federation**: Integrate with existing enterprise identity providers (Okta, Azure AD, etc.)

### When You Need It (Tier Mapping)

| Tier | Need |
|------|------|
| **Tier 1 (Foundation)** | Basic agent identity — agents need credentials to call Bedrock and tools. |
| **Tier 2 (Scale)** | Delegated auth, per-agent permissions, credential rotation. |
| **Tier 3 (Optimize)** | Identity mesh, agent-to-agent auth, federation with enterprise IdP. |

### Fabric Role
**Security Plane** — The identity and access management layer for agents. Analogous to IAM + Cognito but purpose-built for agent-specific patterns (delegation chains, on-behalf-of, machine identity lifecycle).

### Framework Support
All frameworks supported. Identity is injected via environment/configuration — framework-agnostic.

### Integration Points
- AgentCore Runtime injects identity context into agent sessions
- AgentCore Gateway uses Identity tokens for tool access
- AgentCore Observability logs auth decisions
- IAM, Cognito, Secrets Manager as underlying AWS services
- Enterprise IdPs (Okta, Azure AD) for federation

---

## Component 5: AgentCore Code Interpreter

### What It Does
Provides sandboxed code execution environments for agents. When an agent needs to run code (data analysis, calculations, file manipulation, visualization), Code Interpreter provides a secure, isolated execution environment with pre-installed packages and controlled resource access.

### Key Capabilities
- **Sandboxed execution**: Code runs in isolated environments, can't access agent infrastructure
- **Pre-installed packages**: Common data science, analysis, and utility packages available
- **File I/O**: Agents can read/write files within the sandbox
- **Resource limits**: CPU, memory, and time limits prevent runaway code
- **Multi-language**: Python primary, with additional language support
- **Session persistence**: Results persist within a conversation for iterative analysis
- **Output capture**: Stdout, files, and visualizations returned to agent

### When You Need It (Tier Mapping)

| Tier | Need |
|------|------|
| **Tier 1 (Foundation)** | Not needed for simple Q&A or workflow agents. |
| **Tier 2 (Scale)** | Needed when agents must do calculations, data analysis, or generate files. |
| **Tier 3 (Optimize)** | Advanced: multi-step analysis, visualization generation, custom computations. |

### Fabric Role
**Execution Sandbox** — A safe environment for agents to "think by doing." Enables agents to verify their own work through computation rather than relying solely on LLM reasoning.

### Framework Support
All frameworks supported. Code Interpreter is invoked as a tool — any framework can call it.

---

## Component 6: AgentCore Browser

### What It Does
Provides managed web interaction capabilities for agents. When an agent needs to browse websites, fill forms, extract data from web pages, or interact with web UIs, Browser provides a managed headless browser environment.

### Key Capabilities
- **Web browsing**: Navigate pages, click elements, fill forms
- **Content extraction**: Extract text, tables, structured data from web pages
- **Screenshot capture**: Visual understanding of web pages
- **Session management**: Maintain login state across page navigations
- **JavaScript execution**: Interact with dynamic/SPA web applications
- **Proxy support**: Route through corporate proxies for internal sites
- **Anti-detection**: Managed browser fingerprinting for reliable access

### When You Need It (Tier Mapping)

| Tier | Need |
|------|------|
| **Tier 1 (Foundation)** | Not needed for API-integrated agents. |
| **Tier 2 (Scale)** | Needed when agents must interact with systems that only have web UIs (no API). |
| **Tier 3 (Optimize)** | Complex web workflows, multi-step form filling, web scraping at scale. |

### Fabric Role
**UI Interaction Plane** — Extends agent capabilities to the visual/web world. Critical for legacy systems that only expose web interfaces, or for agents that need to interact with third-party SaaS without API access.

### Framework Support
All frameworks supported. Browser is invoked as a tool/capability.

---

## Component 7: AgentCore Observability

### What It Does
Provides comprehensive traces, metrics, and logging for agent runs. Captures the full reasoning chain — every LLM call, tool invocation, memory access, and decision point — in a structured, queryable format. OTel-native for integration with existing observability stacks.

### Key Capabilities
- **Distributed traces**: Full reasoning chain visibility (prompt → think → act → observe → respond)
- **Token metrics**: Usage tracking per agent, per model, per invocation
- **Latency tracking**: End-to-end and per-step latency measurement
- **Error tracking**: Failure rates, error categorization, retry visibility
- **Cost metrics**: Per-invocation cost calculation and aggregation
- **OTel export**: Standard OpenTelemetry format for integration with Datadog, Grafana, Splunk
- **Dashboards**: Pre-built agent monitoring dashboards
- **Alerting**: Configurable alerts on quality, cost, latency thresholds

### When You Need It (Tier Mapping)

| Tier | Need |
|------|------|
| **Tier 1 (Foundation)** | Always needed — you can't operate agents blind. Basic traces and cost tracking. |
| **Tier 2 (Scale)** | Advanced metrics, per-LOB dashboards, alerting, OTel export. |
| **Tier 3 (Optimize)** | Custom metrics, business outcome correlation, cross-agent analytics. |

### Fabric Role
**Observability Plane** — The "eyes" of the platform. Provides the visibility needed to operate, debug, optimize, and audit agents. Without this, the platform is a black box.

### Framework Support
All frameworks supported. Observability instrumentation auto-injects into AgentCore Runtime. Frameworks that support OTel natively get richer traces.

### Integration Points
- AgentCore Runtime auto-instruments all agent executions
- AWS X-Ray for distributed tracing
- CloudWatch for metrics and logs
- OTel Collector for export to third-party observability platforms
- AgentCore Evaluations uses Observability data for quality scoring

---

## Component 8: AgentCore Payments

### What It Does
Provides commerce, billing, and metering capabilities for agent platforms. Enables organizations to monetize agents (charge per use), implement chargeback models (allocate costs to LOBs), and manage agent consumption economics.

### Key Capabilities
- **Usage metering**: Track agent invocations, tokens, tool calls per consumer
- **Billing integration**: Generate invoices, integrate with existing billing systems
- **Chargeback**: Allocate platform costs to consuming LOBs/teams
- **Pricing models**: Per-invocation, per-token, subscription, tiered pricing
- **Budget enforcement**: Hard/soft limits per consumer
- **Revenue tracking**: For product agents sold to external customers
- **Marketplace**: Agent marketplace for internal or external distribution

### When You Need It (Tier Mapping)

| Tier | Need |
|------|------|
| **Tier 1 (Foundation)** | Not needed for initial agents. |
| **Tier 2 (Scale)** | Needed when cost allocation to LOBs becomes critical (4+ consuming teams). |
| **Tier 3 (Optimize)** | Full metering, chargeback, or external monetization of agents as products. |

### Fabric Role
**Commerce Plane** — The economic layer of the platform. Transforms agents from cost centers into measurable (and potentially revenue-generating) assets. Enables the business model layer.

### Framework Support
Framework-agnostic. Payments hooks into AgentCore Runtime execution events — metering happens regardless of which framework the agent uses.

---

## Component 9: AgentCore Evaluations

### What It Does
Provides managed evaluation pipelines for measuring agent quality. Includes judge models (LLMs that evaluate other LLMs), custom metric definitions, regression detection, and continuous quality monitoring. Replaces ad-hoc "try it and see" testing with systematic, repeatable evaluation.

### Key Capabilities
- **Judge models**: LLM-as-judge for quality assessment (relevance, accuracy, helpfulness)
- **Custom metrics**: Define domain-specific quality criteria
- **Eval pipelines**: Automated evaluation runs on schedule or on-deploy
- **Regression detection**: Compare current vs. previous performance
- **Benchmark suites**: Pre-built and custom test suites
- **Human evaluation integration**: Blend automated scores with human ratings
- **A/B comparison**: Side-by-side evaluation of agent versions
- **Continuous monitoring**: Ongoing production quality measurement

### When You Need It (Tier Mapping)

| Tier | Need |
|------|------|
| **Tier 1 (Foundation)** | Basic evaluation — test agent before deploying. Manual + simple automated checks. |
| **Tier 2 (Scale)** | Automated eval pipelines in CI/CD, regression detection, quality gates. |
| **Tier 3 (Optimize)** | Continuous production monitoring, judge models, A/B testing, human eval integration. |

### Fabric Role
**Quality Assurance Plane** — The "conscience" of the platform. Ensures agents maintain quality over time. Without this, agent quality degrades silently until users complain.

### Framework Support
All frameworks supported. Evaluations runs against agent outputs regardless of how those outputs were generated.

### Integration Points
- AgentCore Harness provides test inputs for evaluation
- AgentCore Observability provides production data for continuous monitoring
- CI/CD pipelines trigger eval runs before deployment
- AgentCore Policy uses eval results to gate deployments

---

## Component 10: AgentCore Policy

### What It Does
Provides guardrails and formal verification for agent behavior. Combines content-based safety (filters, PII detection, topic blocking) with **Automated Reasoning** — formal mathematical verification that agent outputs are factually correct. This is the governance enforcement layer.

### Key Capabilities
- **Content filtering**: Block harmful, toxic, or inappropriate content
- **PII detection**: Identify and redact personal information
- **Topic restrictions**: Prevent agents from discussing unauthorized topics
- **Contextual grounding**: Validate outputs against source documents
- **Automated Reasoning**: Formal verification using mathematical logic (99% accuracy on hallucination detection)
- **Custom policies**: Define organization-specific rules (Cedar/OPA integration)
- **Policy-as-code**: Version-controlled, auditable policy definitions
- **Deployment gates**: Block deployments that fail policy checks

### When You Need It (Tier Mapping)

| Tier | Need |
|------|------|
| **Tier 1 (Foundation)** | Always needed — basic guardrails (content safety, PII) from day one. |
| **Tier 2 (Scale)** | Custom policies, contextual grounding, policy-as-code. |
| **Tier 3 (Optimize)** | Automated Reasoning for formal verification, deployment gates, advanced policy chains. |

### Fabric Role
**Governance Plane** — The "immune system" of the platform. Prevents agents from causing harm, leaking data, or producing inaccurate outputs. Differentiates enterprise platforms from hobby projects.

### Framework Support
All frameworks supported. Policy enforcement happens at the AgentCore Runtime level — all agent outputs pass through Policy regardless of framework.

### Integration Points
- AgentCore Runtime enforces Policy on every agent invocation
- Bedrock Guardrails provides the underlying content filtering engine
- Bedrock Automated Reasoning provides formal verification
- AgentCore Evaluations uses Policy results in quality scoring
- CloudTrail logs all policy decisions for audit
- Bedrock Knowledge Bases provides source documents for grounding checks

---

## Component 11: AgentCore Registry

### What It Does
Provides an agent catalog with discovery, versioning, and lifecycle management. Every agent in the organization is cataloged with metadata, capabilities, ownership, health status, and version history. Prevents sprawl, enables discovery, and supports governance.

### Key Capabilities
- **Agent catalog**: Comprehensive listing of all agents with metadata
- **Capability search**: Find agents by what they can do
- **Version management**: Track agent versions, enable rollback
- **Ownership tracking**: Every agent has an owner (team/person)
- **Lifecycle states**: Development → Staging → Production → Deprecated → Retired
- **Health scoring**: Automated health assessment (usage, errors, freshness)
- **Dependency mapping**: What tools, models, and knowledge bases does each agent use?
- **Duplicate detection**: Alert when proposed agents overlap with existing ones

### When You Need It (Tier Mapping)

| Tier | Need |
|------|------|
| **Tier 1 (Foundation)** | Optional for 1-3 agents. Document informally. |
| **Tier 2 (Scale)** | Mandatory when agent count exceeds 10. Discovery and lifecycle management become critical. |
| **Tier 3 (Optimize)** | Advanced: automated health scoring, duplicate detection, governance integration. |

### Fabric Role
**Catalog & Governance Plane** — The "directory" of the platform. Enables discoverability (don't build what exists), accountability (who owns this?), and lifecycle management (is this still healthy?).

### Framework Support
Framework-agnostic. Registry catalogs agents regardless of their implementation framework.

### Integration Points
- AgentCore Runtime registers agents on deployment
- AgentCore Harness validates before registry promotion
- AgentCore Evaluations feeds quality scores into health scoring
- AgentCore Observability provides usage data for health assessment
- Self-service portal queries Registry for agent discovery

---

## Component 12: AgentCore Harness

### What It Does
Provides a testing framework for agents with CI/CD integration. Enables automated testing of agent behavior — tool use validation, multi-turn conversation testing, regression detection, and integration testing — all within deployment pipelines.

### Key Capabilities
- **Synthetic conversations**: Generate test conversations for agent validation
- **Tool-use testing**: Verify agents call the right tools with correct parameters
- **Multi-turn validation**: Test complex conversation flows end-to-end
- **Regression detection**: Compare agent behavior before/after changes
- **CI/CD integration**: Run tests in CodePipeline, GitHub Actions, or any CI system
- **Scenario libraries**: Pre-built and custom test scenarios
- **Failure analysis**: Detailed diagnostics when tests fail
- **Performance benchmarking**: Latency, token usage, cost per test scenario

### When You Need It (Tier Mapping)

| Tier | Need |
|------|------|
| **Tier 1 (Foundation)** | Basic testing — manual + simple automated checks before deploy. |
| **Tier 2 (Scale)** | Automated test suites in CI/CD, regression detection, integration testing. |
| **Tier 3 (Optimize)** | Advanced scenario libraries, performance benchmarking, continuous testing in production. |

### Fabric Role
**Testing Plane** — The "quality gate" of the platform. Ensures agents are tested systematically before reaching production. Prevents the "deploy and pray" anti-pattern.

### Framework Support
All frameworks supported. Harness tests agents at the input/output level — the testing framework is independent of the agent's implementation framework.

### Integration Points
- CodePipeline / CodeBuild for CI/CD pipeline integration
- AgentCore Evaluations for quality scoring of test results
- AgentCore Registry for promotion gating (must pass tests before registry update)
- AgentCore Observability for test result logging and trend analysis
- AgentCore Runtime for test execution environment

---

## Cross-Component Integration Map

### How Components Work Together

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT INVOCATION FLOW                        │
│                                                                 │
│  Request → Runtime → Policy (pre) → Agent Logic → Gateway      │
│                ↕            ↕              ↕            ↕       │
│            Memory      Observability   Code Interp   Identity   │
│                ↕            ↕              ↕                    │
│            Browser     Evaluations      Payments               │
│                                                                 │
│  Agent Logic → Response → Policy (post) → User                  │
│                                  ↕                              │
│                            Registry (logs)                       │
└─────────────────────────────────────────────────────────────────┘
```

### Tier-Based Adoption Sequence

**Tier 1 — Foundation (0-6 months, 1-5 agents)**:
- Runtime (always)
- Policy (basic guardrails)
- Observability (basic traces)
- Gateway (tool access)
- Identity (basic credentials)

**Tier 2 — Scale (6-12 months, 5-20 agents)**:
- Memory (cross-session persistence)
- Registry (catalog, discovery)
- Evaluations (automated quality)
- Harness (CI/CD testing)
- Payments (cost allocation)

**Tier 3 — Optimize (12-18 months, 20+ agents)**:
- Code Interpreter (advanced capabilities)
- Browser (web interaction)
- All components at full feature depth
- Cross-component orchestration patterns

---

## Retrieval Notes for LLM

- When a customer asks "what AgentCore component handles X?", map to the appropriate component using the Fabric Role descriptions.
- AgentCore Runtime is ALWAYS the starting point — every agent needs an execution environment.
- AgentCore Policy (guardrails) should be recommended from day one, even for internal agents.
- AgentCore Observability should be recommended from day one — you can't manage what you can't see.
- Framework choice does NOT limit component access — all 12 components work with all supported frameworks.
- AgentCore is NOT a replacement for Bedrock — it complements Bedrock. Bedrock provides models and knowledge bases. AgentCore provides the agent platform infrastructure.
