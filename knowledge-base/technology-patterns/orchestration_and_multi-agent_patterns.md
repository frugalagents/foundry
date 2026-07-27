# Orchestration & Multi-Agent Coordination Patterns

## Introduction

The enterprise AI landscape has shifted from single-agent systems to multi-agent architectures. [Gartner reported a 1,445% surge in multi-agent system inquiries between Q1 2024 and Q2 2025](https://beam.ai/agentic-insights/multi-agent-orchestration-patterns-production), with organizations already using an average of 12 agents projected to grow 67% within two years. This document catalogs eight core orchestration patterns using a 6-question framework, covering frameworks (Strands SDK, LangGraph, CrewAI, AutoGen, Bedrock multi-agent), AWS services (Step Functions, EventBridge, Bedrock Agents), and protocol standards (A2A, MCP).

---

## Pattern 1: Sequential Chain (Single Agent, Multi-Step)

### WHAT

A sequential chain is a linear pipeline where a single agent executes multiple steps in a fixed order (A → B → C). Each step's output becomes the next step's input. The orchestration logic is deterministic — steps are explicitly defined and transitions are condition-based. [AWS describes this as a "multi-stage AI workflow pattern" using Step Functions as the orchestration backbone](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/pattern-multi-stage-ai.html).

### WHO Needs It

- Teams building document processing pipelines (OCR → extraction → classification → summarization)
- Data engineering teams with ETL-style AI enrichment stages
- Compliance teams requiring auditable, reproducible workflows
- Any team where the task decomposition is known at design time

### WHY NOW

- Foundation models are capable enough to handle individual steps but need coordination for complex tasks
- Enterprises need auditability — [Step Functions provides full state trace and visual workflow history](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html)
- Cost predictability requires bounded execution paths
- Regulatory environments demand deterministic, repeatable processing

### WHERE in Architecture

Sits as the **workflow orchestration layer** between event ingestion (EventBridge, API Gateway) and downstream services. In AWS, this is typically a Step Functions state machine that coordinates Lambda functions, Bedrock model invocations, and SDK integrations with services like Textract, Comprehend, and OpenSearch.

### HOW on AWS

| Component | AWS Service |
|-----------|-------------|
| Orchestrator | AWS Step Functions (Express or Standard workflows) |
| AI Steps | Amazon Bedrock (direct SDK integration from Step Functions) |
| Processing | AWS Lambda functions for custom logic |
| Storage | DynamoDB for state, S3 for artifacts |
| Trigger | EventBridge rule on S3 upload or API Gateway |

[Step Functions integrates directly with Amazon Bedrock](https://hidekazu-konishi.com/entry/step_functions_orchestration_patterns_for_generative_ai.html), eliminating the need for Lambda functions between AI processing steps. The visual workflow console provides built-in error handling, retries, and parallelism.

**Framework alternatives:**
- **LangGraph**: Models sequential chains as a linear graph with nodes and edges; [best for stateful, multi-step workflows with branching and cycles](https://www.groovyweb.co/blog/crewai-vs-langgraph-vs-autogen-framework-comparison-2026)
- **Strands Agents (AWS)**: Provides a model-driven loop where the agent handles tool sequencing internally

### WHAT IF NOT

Without a sequential chain pattern:
- Teams hardcode multi-step logic into monolithic Lambda functions, losing visibility and retry granularity
- Failures cascade without isolation — one bad step poisons the entire flow
- No audit trail for intermediate outputs, failing compliance requirements
- Scaling becomes impossible when steps have different compute profiles

---

## Pattern 2: Hierarchical Orchestration (Supervisor → Worker Agents)

### WHAT

A supervisor agent (or "manager") receives high-level goals, decomposes them into sub-tasks, and delegates work to specialized worker agents. The supervisor monitors progress, handles failures, and aggregates results. [This pattern automatically handles task delegation and response aggregation across various functional agents with enterprise-grade reliability and built-in monitoring](https://aws.amazon.com/it/solutions/guidance/multi-agent-orchestration-on-aws/).

### WHO Needs It

- Customer support platforms routing queries to specialized agents (billing, technical, returns)
- Complex research workflows requiring multiple domain experts
- Enterprise automation where a single request spans multiple business domains
- Organizations with existing specialized agents that need a coordination layer

### WHY NOW

- [Amazon Bedrock multi-agent collaboration](https://aws.amazon.com/it/solutions/guidance/multi-agent-orchestration-on-aws/) provides native supervisor-worker orchestration as a managed service
- LLMs are now capable enough to serve as reliable routers/planners
- Enterprises have invested in specialized agents and need a composition layer
- The pattern maps naturally to organizational hierarchies, making it intuitive for enterprise adoption

### WHERE in Architecture

The supervisor sits at the **coordination tier** — above individual agents but below the user-facing interface. It acts as a single entry point that fans out to workers and fans in their responses.

### HOW on AWS

| Component | AWS Service |
|-----------|-------------|
| Supervisor Agent | Amazon Bedrock Agents (with multi-agent collaboration) |
| Worker Agents | Individual Bedrock Agents or AgentCore-hosted agents |
| Orchestration backbone | AWS Step Functions (parallel states for fan-out) |
| Context sharing | AgentCore Memory |
| Routing logic | Bedrock agent reasoning or Step Functions Choice state |

[AWS provides a reference architecture](https://docs.aws.amazon.com/solutions/multi-agent-orchestration-on-aws/) that enables seamless agent collaboration and context sharing for complex customer scenarios, automatically selecting the best specialist agents for each need.

**Framework alternatives:**
- **CrewAI**: [Fastest path to role-based agent teams](https://www.groovyweb.co/blog/crewai-vs-langgraph-vs-autogen-framework-comparison-2026) with a manager agent delegating to workers with defined roles
- **LangGraph**: Implements supervisor as a graph node that routes to sub-graphs; supports cycles for iterative refinement
- **AutoGen**: [Leads on multi-agent collaborative patterns](https://internative.net/insights/blog/langgraph-vs-crewai-vs-autogen-2026-comparison) with GroupChat manager coordinating specialist agents

### WHAT IF NOT

Without hierarchical orchestration:
- Each agent operates in isolation, requiring users to manually route requests to the correct specialist
- No ability to decompose complex queries that span multiple domains
- Duplicated routing logic embedded in every client application
- No centralized monitoring, failure recovery, or quality control across agent interactions

---

## Pattern 3: Peer-to-Peer / Swarm (Agent-to-Agent Communication, A2A Protocol)

### WHAT

In a peer-to-peer (swarm) pattern, agents communicate directly with each other without a central controller. Agents discover each other's capabilities, delegate sub-tasks laterally, and collaborate to achieve a shared goal. [The Agent2Agent (A2A) protocol is an open standard released by Google in April 2025](https://developers.googleblog.com/a2a-a-new-era-of-agent-interoperability/) that defines how AI agents from different frameworks and vendors communicate, delegate tasks, and exchange results.

### WHO Needs It

- Multi-vendor enterprise environments where agents are built on different platforms
- Distributed organizations where no single team owns all agents
- Scenarios requiring emergent collaboration (e.g., collaborative research, debate patterns)
- Cross-company supply chain automation where agents span organizational boundaries

### WHY NOW

- [A2A v1.0 was released in April 2026 with 150+ supporting organizations](https://note.com/snake_dragon/n/n21e343579a34?hl=en) including every major hyperscaler
- The protocol was [donated to the Linux Foundation](https://note.com/snake_dragon/n/n21e343579a34?hl=en) for vendor-neutral governance
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/specification/2025-11-25) handles agent-to-tool communication; A2A handles agent-to-agent — together they form the complete interoperability stack
- Enterprise adoption of multi-vendor AI strategies makes interoperability non-optional

### WHERE in Architecture

A2A operates at the **inter-agent communication layer** — the protocol fabric that connects agents across services, clouds, and organizations. It sits alongside (not replacing) internal orchestration patterns.

**A2A Core Concepts:**
- **Agent Card**: JSON metadata describing an agent's capabilities, endpoint, and authentication requirements — enables discovery
- **Task**: The unit of work exchanged between agents, with lifecycle states (submitted, working, completed, failed)
- **Message/Part**: Structured payloads (text, files, structured data) exchanged within a task
- **Streaming**: SSE-based push updates for long-running tasks

### HOW on AWS

| Component | AWS Service / Protocol |
|-----------|----------------------|
| Agent discovery | A2A Agent Cards served via API Gateway |
| Agent runtime | Amazon Bedrock AgentCore Runtime |
| Communication | A2A protocol over HTTPS (REST + SSE streaming) |
| Message bus (alternative) | Amazon MQ or EventBridge for internal swarms |
| Security | OAuth 2.0 / IAM for agent-to-agent auth |

[AWS multi-agent architectures documentation](https://aws.amazon.com/marketplace/build-learn/ai-agent-learning-series/multi-agent-architectures) covers peer-to-peer implementations using LangGraph on Step Functions, EventBridge, and Amazon MQ.

**Framework alternatives:**
- **OpenAI Swarm** (archived): Pioneered the lightweight swarm concept — [agents are just system prompts with functions, handoffs are just functions that return another agent](https://kindatechnical.com/agentic-ai/openai-swarm-and-handoff-patterns.html)
- **AutoGen**: GroupChat pattern enables peer-to-peer debate and collaboration
- **Google ADK**: Native A2A protocol support for cross-framework agent communication

### WHAT IF NOT

Without peer-to-peer coordination:
- Vendor lock-in: agents can only collaborate within a single framework
- Central orchestrator becomes a bottleneck and single point of failure
- Cross-organization agent collaboration is impossible
- No standard for capability discovery — each integration is bespoke

---

## Pattern 4: Event-Driven Agent Activation (Reactive Agents)

### WHAT

Agents subscribe to specific event types and activate autonomously when relevant events occur in the data environment — rather than polling or being called directly. [Event-driven architecture for AI agents means each agent subscribes to specific event types and reacts the moment a relevant change occurs](https://atlan.com/know/event-driven-architecture-for-ai-agents/). The system is reactive, loosely coupled, and scales independently.

### WHO Needs It

- DevOps/SRE teams needing agents that respond to incidents automatically
- Data platform teams where agents react to data quality changes, schema drift, or pipeline failures
- Security teams with agents monitoring for anomalous events
- Customer experience teams where agents activate on user behavior signals

### WHY NOW

- [AWS EventBridge now integrates natively with AgentCore agents](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html) — agents can emit and subscribe to events using the AgentCore SDK
- [Production example: EventBridge rules detect alarm state changes and invoke Lambda that calls DevOps Agent CreateBacklogTask API](https://repost.aws/articles/ARnrvREIynRsKAdzRwYVF1_A/automating-aws-devops-agent-investigation-from-incident-detection-and-response-alarms)
- The shift from request-response to proactive agents requires event-driven infrastructure
- Serverless scaling (pay-per-event) makes always-on agent monitoring economically viable

### WHERE in Architecture

EventBridge sits as the **central nervous system** — the event bus routing agent state changes, task completion events, and error events to appropriate downstream consumers. [It provides deterministic, auditable event routing while AgentCore Memory + A2A provides semantic state sharing](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html).

### HOW on AWS

| Component | AWS Service |
|-----------|-------------|
| Event bus | Amazon EventBridge |
| Event producers | S3, CloudWatch, custom applications |
| Agent activation | EventBridge rule → Lambda → Bedrock Agent / AgentCore |
| State persistence | DynamoDB (agent state), AgentCore Memory |
| Downstream triggers | EventBridge emits completion/error events |
| Monitoring | CloudWatch, EventBridge Archive for replay |

[The architecture](https://sudoconsultants.com/building-resilient-agentic-ai-workflows-on-aws-using-amazon-bedrock-and-eventbridge/) centers on: API Gateway/Lambda as entry points → DynamoDB for agent state → EventBridge as central event bus → Agent reasoning loops with tool invocations → Further event emissions for downstream processing.

### WHAT IF NOT

Without event-driven activation:
- Agents require polling, wasting compute and increasing latency
- Tight coupling between producers and consumers — changes ripple through the system
- No independent scaling: a surge in one event type overwhelms all agents
- Lost events during failures with no replay capability
- Inability to compose agents reactively (each needs explicit invocation)

---

## Pattern 5: Human-in-the-Loop Orchestration (Approval Gates, Escalation Patterns)

### WHAT

Agents execute autonomously on routine decisions but pause at defined checkpoints to request human approval, confirmation, or input before proceeding with high-stakes or low-confidence actions. [HITL is the gold standard for high-risk operations such as financial transactions over a certain threshold or legal document finalization](https://www.accio.com/wow/guide-human-in-the-loop-ai-agent-2026.html).

### WHO Needs It

- Financial services (transaction approval above thresholds)
- Healthcare (treatment recommendations requiring clinician sign-off)
- Legal (contract generation needing lawyer review)
- Any regulated industry with compliance requirements for human oversight
- Teams building agents that modify production systems

### WHY NOW

- [EU AI Act and similar regulations mandate human oversight for high-risk AI applications](https://dzone.com/articles/agent-frameworks-human-loop?fromrel=true)
- Agents are capable enough to handle 80% of cases autonomously but need escalation for edge cases
- [Step Functions callback pattern allows state machines to pause indefinitely (up to one year) waiting for a Task Token](https://annpastushko.substack.com/p/step-functions-for-human-in-the-loop) — purpose-built for approval gates
- Trust is the bottleneck for enterprise AI adoption; HITL bridges the trust gap

### WHERE in Architecture

HITL gates sit at **decision points within the workflow** — between agent reasoning and action execution. They can be implemented at the tool level (before a specific tool executes), the task level (before a task result is committed), or the workflow level (before moving to the next phase).

**Three Implementation Patterns:**

1. **Durable Graph Interrupt** (LangGraph): [The execution graph serializes entire state and suspends at the exact node where approval was needed](https://dzone.com/articles/agent-frameworks-human-loop?fromrel=true). Resume from checkpoint after decision.
2. **Callback Token** (Step Functions): Workflow sends notification, pauses, and waits for a unique token to be returned via API.
3. **Tool-Level Approval** (OpenAI Agents SDK): [Tools declare when they need approval; run results surface pending approvals as interruptions](https://openai.github.io/openai-agents-python/human_in_the_loop/).

### HOW on AWS

| Component | AWS Service |
|-----------|-------------|
| Workflow with pause | AWS Step Functions (waitForTaskToken) |
| Notification | Amazon SNS, SES, or Slack integration |
| Approval interface | Custom UI, or Step Functions callback API |
| Timeout handling | Step Functions HeartbeatSeconds + timeout fallback |
| Audit trail | CloudWatch Logs, Step Functions execution history |
| Agent-native HITL | Bedrock Agents with return-of-control action |

**Framework alternatives:**
- **LangGraph**: `interrupt()` function + external checkpointer (Redis, Postgres) for durable suspension
- **OpenAI Agents SDK**: Built-in HITL via tool approval declarations and RunState serialization
- **Cloudflare Agents**: [Native HITL patterns with durable state and approval webhooks](https://developers.cloudflare.com/agents/guides/human-in-the-loop/index.md)

### WHAT IF NOT

Without human-in-the-loop:
- Agents execute high-risk actions autonomously with no safety net
- Regulatory non-compliance in industries requiring human oversight
- Catastrophic errors propagate before anyone notices (e.g., wrong refund amount, incorrect medical recommendation)
- No mechanism to build incremental trust — it's all-or-nothing autonomy
- Teams refuse to deploy agents at all, losing competitive advantage

---

## Pattern 6: Deterministic + Agentic Hybrid (Step Functions for Guardrails + LLM for Decisions)

### WHAT

A hybrid pattern combining deterministic orchestration (Step Functions) for predictable guardrails with AI-native orchestration (Bedrock Agents) for flexible decision-making. [Step Functions manages HOW things happen; Agents decide WHAT should happen based on user goals](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html). The deterministic layer provides auditability, error handling, and compliance boundaries; the agentic layer provides semantic flexibility and goal-directed reasoning.

### WHO Needs It

- Enterprise teams requiring both flexibility AND compliance
- Organizations transitioning from rule-based automation to AI — need a gradual migration path
- Workflows where some steps must be deterministic (payment processing, data validation) and others benefit from AI reasoning (summarization, classification, customer interaction)
- Teams that need visual workflow debugging alongside LLM-powered decision-making

### WHY NOW

- [AWS prescriptive guidance explicitly recommends this hybrid approach](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html): "Use Step Functions for controlled processes and Amazon Bedrock Agents for natural language interaction and flexible goal fulfillment"
- [Step Functions now integrates directly with Amazon Bedrock](https://hidekazu-konishi.com/entry/step_functions_orchestration_patterns_for_generative_ai.html) — no Lambda functions needed for AI invocations
- Enterprises cannot accept fully autonomous agents in regulated domains but can't afford fully manual processes
- The pattern provides a migration path: start deterministic, progressively delegate decisions to agents

### WHERE in Architecture

Step Functions sits as the **outer orchestration shell** providing the deterministic skeleton. Within specific states, Bedrock Agents (or direct Bedrock model invocations) handle the AI-powered decisions. Think of it as "guardrails on the outside, intelligence on the inside."

### HOW on AWS

| Component | AWS Service |
|-----------|-------------|
| Outer orchestration | AWS Step Functions |
| AI decision nodes | Amazon Bedrock (InvokeModel) or Bedrock Agents |
| Guardrails | Step Functions Choice states, input validation Lambda |
| Error boundaries | Step Functions Catch/Retry with exponential backoff |
| Parallel processing | Step Functions Parallel/Map states |
| Audit | Step Functions execution history + CloudWatch |

**Architecture pattern:**
```
EventBridge → Step Functions
                ├── [Deterministic] Validate input (Lambda)
                ├── [Agentic] Classify intent (Bedrock InvokeModel)
                ├── [Deterministic] Route based on classification (Choice state)
                ├── [Agentic] Generate response (Bedrock Agent)
                ├── [Deterministic] Apply compliance filters (Lambda)
                └── [Deterministic] Store result (DynamoDB SDK integration)
```

[ServerlessLand provides a reference pattern](https://serverlessland.com/patterns/sfn-parallel-bedrock-agentcore-multi-agent-cdk) deploying Step Functions workflows that orchestrate multiple specialized AI agents running on AgentCore and synthesize their results.

### WHAT IF NOT

Without the hybrid approach:
- **Fully deterministic**: Cannot handle ambiguity, variation, or natural language — brittle and expensive to maintain
- **Fully agentic**: No audit trail, unpredictable costs, hallucination risks in critical paths, regulatory exposure
- Teams oscillate between "no AI" and "all AI" without a pragmatic middle ground
- No clear boundary between what the AI controls and what the system guarantees

---

## Pattern 7: Agent Handoff Patterns (Transferring Context Between Specialized Agents)

### WHAT

An agent completes its portion of a task and explicitly transfers control — along with conversation history and relevant context — to another specialized agent. [The OpenAI Agents SDK's core primitive is the Handoff, allowing one agent to transfer a conversation and its context to another specialized agent](https://fast.io/resources/openai-agents-sdk/). Think of it like a relay race where each runner hands the baton to the next.

### WHO Needs It

- Customer service platforms with specialized tiers (general → billing → technical → escalation)
- Multi-stage workflows where different AI capabilities are needed at each stage
- Applications where conversation context must flow seamlessly across agent boundaries
- Teams building modular agent architectures that can be updated independently

### WHY NOW

- [OpenAI graduated its experimental Swarm project into a production-ready Agents SDK](https://effloow.hashnode.dev/ai-agent-frameworks-compared-2026) with handoffs as a first-class primitive
- Context window limits make it impractical for a single agent to handle everything
- Specialization improves quality — a focused agent outperforms a generalist
- [Handoffs are now standardized across frameworks](https://github.com/openai/openai-agents-python/blob/main/docs/handoffs.md): "Handoffs allow an agent to delegate tasks to another agent. This is particularly useful in scenarios where different agents specialize in distinct areas."

### WHERE in Architecture

Handoffs occur at the **agent-to-agent boundary** within a single system (unlike A2A which is cross-system). They sit within the agent runtime layer and are typically managed by the orchestrating framework.

**Handoff Mechanisms:**
1. **Function-based** (OpenAI Swarm/Agents SDK): [Handoffs are just functions that return another agent](https://kindatechnical.com/agentic-ai/openai-swarm-and-handoff-patterns.html) — minimal overhead
2. **Graph-edge** (LangGraph): Conditional edges in the state graph route to different agent nodes based on state
3. **Protocol-based** (A2A): Cross-framework handoff via standardized task delegation

### HOW on AWS

| Component | AWS Service |
|-----------|-------------|
| Agent hosting | Amazon Bedrock AgentCore Runtime |
| Context persistence | AgentCore Memory (shared across agents) |
| Handoff routing | Bedrock multi-agent collaboration / Step Functions |
| Conversation history | DynamoDB or AgentCore Memory |
| Context compression | Bedrock model for summarization before handoff |

**Framework implementations:**
- **OpenAI Agents SDK**: `Handoff(target_agent)` as a tool — when the model calls it, control transfers with full conversation history
- **LangGraph**: State graph with conditional routing; shared `State` object carries context between nodes
- **CrewAI**: Task delegation between agents with role-based routing
- **Bedrock Multi-Agent**: [Supervisor agent routes to specialists and aggregates responses](https://docs.aws.amazon.com/solutions/multi-agent-orchestration-on-aws/)

### WHAT IF NOT

Without agent handoff patterns:
- Context is lost when switching between specialized agents, requiring users to repeat information
- Monolithic agents try to handle everything, degrading quality on specialized tasks
- No clean separation of concerns — updating one capability risks breaking others
- Conversation feels disjointed as users are bounced between systems without continuity

---

## Pattern 8: Long-Running Agent Sessions (Stateful Multi-Turn Workflows)

### WHAT

Agents maintain persistent state across multiple interactions over extended periods — hours, days, or weeks. Unlike stateless request-response patterns, long-running sessions preserve conversation history, task progress, accumulated context, and intermediate results across invocations. [AgentCore Memory provides persistent, structured storage for context, state, and task history, enabling agents to maintain continuity across invocations and workflows](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html).

### WHO Needs It

- Complex investigation workflows (fraud analysis spanning multiple data pulls over days)
- Project management agents tracking multi-week initiatives
- Customer relationship agents maintaining context across touchpoints
- Research agents conducting iterative analysis with human feedback loops
- Any workflow where the agent needs to "remember" previous interactions

### WHY NOW

- [AgentCore Memory supports both ephemeral and long-term memory modes](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html) — purpose-built for this pattern
- Context windows are larger but still finite — session management with retrieval is necessary for multi-turn workflows
- Enterprise workflows are inherently long-running (procurement cycles, audit processes, incident investigations)
- [Step Functions Standard workflows support execution durations up to one year](https://annpastushko.substack.com/p/step-functions-for-human-in-the-loop) with pause/resume capability

### WHERE in Architecture

Session state management sits at the **persistence and memory layer** — below the agent reasoning layer but above raw data storage. It mediates between the agent's working memory (context window) and durable storage.

**State Components:**
- **Conversation history**: Full or summarized message log
- **Task state**: Progress, intermediate results, pending actions
- **Working memory**: Key facts and decisions accumulated during the session
- **Checkpoints**: Serialized agent state for resume-after-failure

### HOW on AWS

| Component | AWS Service |
|-----------|-------------|
| Session memory | Amazon Bedrock AgentCore Memory |
| Durable state | DynamoDB (TTL for session expiry) |
| Long-running orchestration | Step Functions Standard workflows (up to 1 year) |
| Checkpoint storage | S3 (for large state serialization) |
| Session resumption | Lambda + DynamoDB for state hydration |
| Memory synchronization | AgentCore Memory → DynamoDB/S3 for compliance |

**Framework approaches:**
- **LangGraph**: Checkpointer interface (Redis, Postgres, SQLite) serializes full graph state; resume from any checkpoint
- **OpenAI Agents SDK**: Sessions primitive with built-in state persistence and `RunState` for serialization/resumption
- **Strands Agents (AWS)**: Session management with AgentCore Memory integration
- **Temporal**: [Durable execution framework](https://futureagi.com/blog/best-ai-agent-orchestration-platforms-2026/) — workflows survive process restarts, ideal for multi-day agent sessions

### WHAT IF NOT

Without long-running session support:
- Agents lose context between interactions — users must re-explain context every time
- Multi-step workflows cannot survive infrastructure failures or restarts
- No ability to pause for async input (human review, external system response) and resume
- Accumulated insights from earlier steps are lost, forcing redundant processing
- Workflows that span days or weeks are impossible to implement

---

## Protocol Standards: A2A and MCP

### Model Context Protocol (MCP) — Agent-to-Tool

[MCP is an open standard released by Anthropic in November 2024](https://www.ml4devs.com/what-is/mcp-model-context-protocol/) that defines how AI models and agents connect to external tools, data sources, and APIs. Think of it as "USB-C for AI applications" — a standardized connector that replaces bespoke integrations.

**Key facts:**
- [Adopted by Anthropic, OpenAI, Google DeepMind, and Microsoft within months of release](https://www.sitepoint.com/model-context-protocol-mcp/)
- [Donated to the Linux Foundation's Agentic AI Foundation in December 2025](https://nerdleveltech.com/guides/model-context-protocol)
- Specification evolved through 2025 with OAuth2, enterprise authorization, and mandatory PKCE
- [Streamable HTTP replaced SSE as the recommended remote transport in spec 2025-03-26](https://nerdleveltech.com/guides/model-context-protocol)
- [AgentCore Gateway provides managed MCP interfaces](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html) for securely invoking AWS services and external APIs

**MCP provides:** Resources (read data), Tools (execute actions), Prompts (reusable templates)

### Agent2Agent Protocol (A2A) — Agent-to-Agent

[A2A is an open standard announced by Google in April 2025](https://developers.googleblog.com/a2a-a-new-era-of-agent-interoperability/) enabling agents built on diverse frameworks by different companies to communicate and collaborate — as agents, not just as tools.

**Key facts:**
- [Version 1.0 released April 2026; 150+ supporting organizations](https://note.com/snake_dragon/n/n21e343579a34?hl=en)
- [Governed by the Linux Foundation since June 2025](https://www.ml4devs.com/what-is/a2a-agent-to-agent-protocol/)
- Core primitives: Agent Card (discovery), Task (work unit), Message/Part (payload), Streaming (SSE updates)
- [Addresses the critical challenge of enabling agents from different frameworks running on separate servers to communicate effectively](https://github.com/google-a2a/A2A)

**The MCP + A2A relationship:**
- MCP = how an agent uses tools (vertical integration)
- A2A = how agents collaborate with each other (horizontal integration)
- Together they form the complete interoperability stack for multi-agent enterprises

---

## Framework Comparison Matrix

| Framework | Best For | Orchestration Model | Session/State | HITL Support |
|-----------|----------|-------------------|---------------|--------------|
| **LangGraph** | [Stateful production workflows with branching, cycles, and human-in-the-loop](https://www.groovyweb.co/blog/crewai-vs-langgraph-vs-autogen-framework-comparison-2026) | State graph (nodes + edges) | Checkpointer (Redis/Postgres) | `interrupt()` + resume |
| **CrewAI** | [Fast role-based agent teams with minimal boilerplate](https://www.groovyweb.co/blog/crewai-vs-langgraph-vs-autogen-framework-comparison-2026) | Manager + Workers | Built-in memory | Delegation patterns |
| **OpenAI Agents SDK** | Production multi-agent with handoffs | Handoff-based relay | Sessions + RunState | Tool-level approval |
| **Strands Agents (AWS)** | AWS-native agent development | Model-driven loop | AgentCore Memory | Return-of-control |
| **AutoGen/MS Agent Framework** | [Multi-agent collaborative patterns](https://internative.net/insights/blog/langgraph-vs-crewai-vs-autogen-2026-comparison) | GroupChat / Conversations | Conversation history | Human proxy agent |
| **Google ADK** | A2A-native, multi-platform | Agent-to-agent protocol | Stateful sessions | Approval callbacks |
| **Bedrock Multi-Agent** | Managed AWS enterprise deployment | Supervisor → specialists | AgentCore Memory | Return-of-control action |

[In 2026, most enterprise systems use LangGraph + MCP for tools](https://internative.net/insights/blog/langgraph-vs-crewai-vs-autogen-2026-comparison) as the production default, while CrewAI dominates rapid prototyping and role-based teams.

---

## Summary: Key Takeaways

1. **No single pattern suffices** — Production systems combine patterns (e.g., hierarchical orchestration with HITL gates, event-driven activation feeding into sequential chains). The [hybrid deterministic + agentic approach](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html) is AWS's recommended default.

2. **Two protocols define the interoperability stack** — [MCP (Anthropic, Nov 2024)](https://modelcontextprotocol.io/specification/2025-11-25) standardizes agent-to-tool connections; [A2A (Google, Apr 2025)](https://developers.googleblog.com/a2a-a-new-era-of-agent-interoperability/) standardizes agent-to-agent communication. Both are now under Linux Foundation governance with broad industry adoption.

3. **AWS has a complete orchestration stack** — Step Functions (deterministic guardrails) + EventBridge (event-driven activation) + Bedrock Agents/AgentCore (AI-native reasoning) + AgentCore Memory (stateful sessions). The [multi-agent orchestration guidance](https://aws.amazon.com/it/solutions/guidance/multi-agent-orchestration-on-aws/) provides reference architectures.

4. **Human-in-the-loop is non-negotiable for enterprise** — Regulatory pressure (EU AI Act) and trust requirements mean every production agent system needs approval gates. [Step Functions callback tokens](https://annpastushko.substack.com/p/step-functions-for-human-in-the-loop) and [LangGraph interrupts](https://dzone.com/articles/agent-frameworks-human-loop) are the two dominant implementation approaches.

5. **Framework convergence is happening** — [Microsoft merged Semantic Kernel and AutoGen into a single Agent Framework; OpenAI graduated Swarm into Agents SDK](https://effloow.hashnode.dev/ai-agent-frameworks-compared-2026). The surviving frameworks (LangGraph, CrewAI, OpenAI Agents SDK, Strands, Google ADK) each optimize for different patterns rather than competing head-to-head.

6. **Event-driven is the activation model** — Whether using rule-based or AI-native orchestration, [events are the mechanism that activate intelligence in serverless systems](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html). EventBridge is the central nervous system connecting all patterns.

7. **State management is the hardest problem** — Long-running sessions, context handoffs, and checkpoint/resume are where most systems fail. [AgentCore Memory](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html) and [LangGraph checkpointers](https://dzone.com/articles/agent-frameworks-human-loop) represent the current state of the art, but this remains an active area of innovation.
