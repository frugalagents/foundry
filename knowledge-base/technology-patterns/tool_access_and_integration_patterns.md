# Tool Access & Integration Patterns for Agentic Platforms

## 1. Programmatic / Dynamic Tool Calling (Runtime Tool Definition Without MCP Servers)

### WHAT Is It

Programmatic Tool Calling (PTC) is a model-API pattern where tool definitions are passed as JSON Schema objects directly in each inference request, and the model emits structured tool-call outputs (function name + typed arguments) rather than free text. The application code is responsible for executing the tool and feeding results back. Unlike MCP, there is no persistent server or protocol—tools are defined ephemerally per request.

In traditional tool calling, each invocation requires a full round trip back to the model: call tool → receive result → reason → call next tool. PTC advances this by allowing the LLM to emit code (Python/JavaScript) that orchestrates multiple tool calls in a single execution pass—loops, conditionals, and data transformations happen in a sandboxed container without returning to the model between each step. [Implementing Programmatic Tool Calling on Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/implementing-programmatic-tool-calling-on-amazon-bedrock/)

The key primitives:
- **Tool catalog**: A JSON array of `{name, description, inputSchema}` objects sent with the prompt
- **Model output**: A structured `tool_use` block with name and arguments (not free text)
- **Execution loop**: Application code runs the function, returns results, model incorporates them
- **Advanced PTC**: Model writes orchestration code that calls multiple tools programmatically without per-call model inference [Anthropic Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)

### WHO Needs It

- **Teams building single-application agents** where tools are owned end-to-end and don't need cross-client reuse
- **Low-latency use cases** where MCP server overhead (connection, discovery) is unacceptable
- **Rapid prototyping** teams that need tool access in hours, not days
- **Applications with dynamic tool sets** that change per-request based on user context or permissions
- **Cost-sensitive deployments** where minimizing round-trips directly reduces token consumption and inference cost

### WHY NOW (2025–2026)

- Every major model provider (OpenAI, Anthropic, Google, Meta) now supports native function calling with structured outputs—this wasn't universally available before mid-2024 [LLM Function Calling 2025](https://futureagi.com/blog/llm-function-calling-2025/)
- Amazon Bedrock's Converse API unified tool calling across 20+ model families (Claude, Llama, Mistral, Cohere) with a single schema format, removing the vendor-specific wrapper problem [Implementing Programmatic Tool Calling on Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/implementing-programmatic-tool-calling-on-amazon-bedrock/)
- Anthropic's November 2025 "advanced tool use" introduced code-execution-based tool orchestration, eliminating the O(n) latency of sequential tool calls [Anthropic Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)
- Prompt engineering research (arxiv 2407.04997) demonstrated that even non-fine-tuned models can achieve tool calling via dynamic prompt injection of schemas [Achieving Tool Calling via Prompt Engineering](https://arxiv.org/html/2407.04997v1)

### WHERE in the Architecture

PTC operates at the **model-API interface layer**—between the orchestrator/application and the LLM inference endpoint. It sits below the agent framework (LangChain, Strands, CrewAI) and above the actual tool execution runtime:

```
[User Request] → [Agent Framework/Orchestrator] → [Model API + Tool Definitions] → [LLM]
                                                                                      ↓
[Tool Execution Runtime] ← [Structured tool_use output] ← ← ← ← ← ← ← ← ← ← ← ← ←
```

It replaces: custom prompt-engineering hacks, regex-based output parsing, and bespoke "plugin" formats.

### HOW on AWS

| Component | AWS Service | Configuration |
|-----------|-------------|---------------|
| Model inference | Amazon Bedrock (Converse API) | `toolConfig.tools[]` with JSON Schema definitions |
| Tool execution | AWS Lambda, ECS tasks, or in-process | Lambda for stateless; ECS for long-running |
| Schema storage | Amazon DynamoDB or S3 | Per-user/per-session tool catalogs |
| Orchestration | Bedrock AgentCore Runtime or custom | `toolChoice: "auto"` / `"any"` / `{"tool": {"name": "..."}}` |
| Advanced PTC | Bedrock + code sandbox (Docker/Firecracker) | Model emits Python, executed in sandboxed container |

Key Bedrock Converse API configuration:
```json
{
  "toolConfig": {
    "tools": [
      {
        "toolSpec": {
          "name": "get_weather",
          "description": "Get current weather for a city",
          "inputSchema": {
            "json": {
              "type": "object",
              "properties": {
                "city": {"type": "string"},
                "units": {"type": "string", "enum": ["celsius", "fahrenheit"]}
              },
              "required": ["city"]
            }
          }
        }
      }
    ],
    "toolChoice": {"auto": {}}
  }
}
```

### WHAT IF NOT (Anti-Pattern)

Without programmatic tool calling:
- **Regex parsing of free text**: Models output tool calls in natural language, parsed with fragile regex → breaks on model version changes, hallucinated formats
- **One-tool-at-a-time latency**: Each tool invocation requires a full model round-trip → 5 tool calls = 5× inference latency (2-15 seconds each)
- **No type safety**: Arguments are unvalidated strings → runtime errors, injection vulnerabilities
- **Context window bloat**: Without structured tool results, raw outputs pile into context whether useful or not

---

## 2. MCP Server Architecture (Model Context Protocol for Tool Standardization)

### WHAT Is It

The Model Context Protocol (MCP) is an open standard (initially released by Anthropic, now adopted by OpenAI, Google DeepMind, and Microsoft) that defines a transport-layer protocol for AI agents to discover, authenticate against, and invoke external tools and data sources. It uses a client-server architecture with JSON-RPC 2.0 messaging over Streamable HTTP or STDIO transports. [MCP Complete 2026 Guide](https://www.sitepoint.com/model-context-protocol-mcp/)

Core architecture components:
- **MCP Host**: The AI application (Claude Desktop, IDE, custom agent) that initiates connections
- **MCP Client**: Protocol handler within the host that manages 1:1 server connections
- **MCP Server**: Lightweight service exposing capabilities via three primitives:
  - **Tools**: Functions the model can invoke (with JSON Schema input/output)
  - **Resources**: Data sources the model can read (files, DB records, API responses)
  - **Prompts**: Reusable prompt templates for specific workflows
- **Transport**: Streamable HTTP (production) or STDIO (local development) [Kubiya MCP Architecture](https://www.kubiya.ai/blog/model-context-protocol-mcp-architecture-components-and-workflow)

The protocol specification (version 2025-11-25) mandates:
- Tool discovery via `tools/list` method
- Tool invocation via `tools/call` method
- Capability negotiation during initialization handshake
- Stateful sessions with server-sent notifications

### WHO Needs It

- **Multi-agent, multi-tool enterprises** with the N×M integration problem (N agents × M tools = N×M custom integrations reduced to N+M) [CData Enterprise MCP](https://www.cdata.com/blog/implementing-mcp-enterprise-environments)
- **Organizations using multiple AI platforms** (Claude, GPT, Gemini, open-source) that need one tool integration to work everywhere
- **Platform teams** building shared tool infrastructure for multiple application teams
- **Compliance-driven orgs** needing centralized audit trails of all tool invocations
- **ISVs/SaaS vendors** wanting to expose their APIs to any AI agent without building provider-specific plugins

### WHY NOW (2025–2026)

- MCP adoption reached critical mass: Anthropic, OpenAI, Google DeepMind, and Microsoft all adopted the protocol within months of its late-2024 release [SitePoint MCP Guide](https://www.sitepoint.com/model-context-protocol-mcp/)
- PwC integrated MCP into their agent OS for enterprise customers, validating production readiness [PwC MCP Announcement](https://www.pwc.com/us/en/about-us/newsroom/press-releases/pwc-adds-support-for-mcp-in-agent-os.html)
- The 2025-11-25 spec version added OAuth 2.1 authorization, making enterprise security feasible
- Community MCP server ecosystem exceeded 1000+ published servers by early 2026
- April 2026 STDIO RCE vulnerability disclosure made gateway-mediated MCP mandatory for enterprises [FutureAGI MCP Gateway 2026](https://futureagi.com/blog/what-is-mcp-gateway-2026/)

### WHERE in the Architecture

MCP operates at the **integration/transport layer**—between the agent orchestrator and external systems:

```
[LLM + Agent Framework] → [MCP Client] ←→ [MCP Server] → [External System/API/DB]
                              ↕ (JSON-RPC over Streamable HTTP)
                         [MCP Gateway] (optional, for enterprise)
                              ↕
                    [Multiple MCP Servers]
```

Enterprise topology (per markaicode.com):
1. **Gateway Layer**: Routing, authentication, tool catalog filtering
2. **Orchestrator Layer**: Session management, tool execution coordination
3. **MCP Server Pools**: Domain-specific tool servers (CRM, ERP, DevOps, etc.)

[Enterprise MCP Architecture](https://markaicode.com/architecture/enterprise-mcp-architecture/)

### HOW on AWS

| Component | AWS Service | Configuration |
|-----------|-------------|---------------|
| MCP Gateway | Amazon Bedrock AgentCore Gateway | Fully managed; supports MCP 2025-03-26 spec |
| MCP Server hosting | AgentCore Runtime | Deploy MCP servers as managed containers |
| MCP Server (custom) | ECS Fargate, Lambda (for STDIO→HTTP bridge) | Streamable HTTP transport |
| Authentication (inbound) | Amazon Cognito + OAuth 2.1 | JWT validation at gateway |
| Authentication (outbound) | AgentCore Identity | Credential providers (API key, OAuth 2LO) |
| Tool discovery | AgentCore semantic search | `x_amz_bedrock_agentcore_search` built-in tool |
| Observability | CloudWatch + CloudTrail | Per-invocation metrics and audit logs |
| Private connectivity | AgentCore VPC connectivity | PrivateLink for tools in VPCs |

[Amazon Bedrock AgentCore Gateway](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-gateway-transforming-enterprise-ai-agent-tool-development/)

### WHAT IF NOT (Anti-Pattern)

Without MCP standardization:
- **N×M integration hell**: Each agent-tool pair requires custom adapter code → engineering cost grows quadratically
- **Vendor lock-in**: Tools built for OpenAI plugins don't work with Claude or Gemini → duplicate effort
- **No dynamic discovery**: Agents must have tools hardcoded at build time → can't adapt to new capabilities
- **Security sprawl**: Each integration manages its own auth → inconsistent policies, credential leakage
- **Shadow MCP**: Developers pip-install community MCP servers directly, bypassing security controls → the April 2026 STDIO RCE incident pattern

---

## 3. Hybrid Tool Access (MCP + Programmatic for Different Use Cases)

### WHAT Is It

Hybrid tool access is an architectural pattern where an agent system uses **both** MCP (for standardized, discoverable, cross-platform integrations) and **programmatic/direct tool calling** (for tightly-coupled, latency-sensitive, or single-application tools) simultaneously. The agent framework routes tool calls to the appropriate mechanism based on tool characteristics.

The key insight: MCP and function calling are not competing technologies—they operate at different layers of the stack. Function calling is the model-level ability; MCP is the integration-level standard that organizes how tools are exposed, discovered, and invoked. [Metavert: Tool Use vs MCP](https://metavert.io/tool-use-vs-model-context-protocol)

Hybrid routing decision matrix:
| Criterion | Use Programmatic | Use MCP |
|-----------|-----------------|---------|
| Tool ownership | You own it end-to-end | Third-party or shared |
| Reuse scope | Single app only | Multiple agents/apps |
| Latency budget | <100ms required | 200-500ms acceptable |
| Discovery needs | Static, known at build | Dynamic, changes at runtime |
| Auth complexity | Simple (same trust boundary) | Cross-boundary (OAuth) |

[Oracle: Agent Communication Matrix](https://blogs.oracle.com/developers/the-agent-communication-matrix-when-mcp-a2a-and-plain-rest-each-win)

### WHO Needs It

- **Enterprise platform teams** with both internal microservices (fast, direct) and external SaaS integrations (standardized, discoverable)
- **Agent builders migrating incrementally** from direct tool calling to MCP without big-bang rewrites
- **Performance-critical applications** (trading, real-time monitoring) that can't accept MCP overhead for hot-path tools but want MCP for cold-path integrations
- **Multi-framework organizations** where different teams use different agent SDKs but share some tools via MCP

### WHY NOW (2025–2026)

- The "MCP vs Function Calling" debate resolved in 2025-2026 with industry consensus that they're complementary layers, not alternatives [MCP vs Function Calling 2026](https://markaicode.com/vs/mcp-vs-function-calling/)
- Agent frameworks (LangChain, Strands, AutoGen) added native support for mixing MCP tools with programmatic tools in the same agent loop
- Frends.com and other iPaaS vendors documented hybrid integration patterns combining MCP for discovery with direct API calls for execution [Frends: MCP Hybrid Patterns](https://frends.com/insights/mcp-and-enterprise-integration-architecture-governance-and-hybrid-patterns)
- Production evidence showed pure-MCP architectures hit latency walls at >500 concurrent requests; hybrid approaches cap p95 at 280ms [MCP Agent Architecture](https://markaicode.com/architecture/mcp-agent-architecture/)

### WHERE in the Architecture

```
[Agent Orchestrator]
       ├── [Programmatic Tools] ← Direct function calls (in-process or Lambda)
       │       • Calculator, formatter, validator
       │       • Hot-path domain logic
       │       • Owned microservices via SDK
       │
       └── [MCP Client] → [MCP Gateway] → [MCP Servers]
               • CRM integration (Salesforce, HubSpot)
               • Document management (SharePoint, Confluence)
               • External SaaS APIs
               • Cross-team shared tools
```

The orchestrator maintains a unified tool registry that merges both sources and presents a single tool catalog to the model.

### HOW on AWS

| Component | AWS Service | Pattern |
|-----------|-------------|---------|
| Programmatic tools | Lambda (direct invoke), Bedrock Converse `toolConfig` | Inline JSON Schema, direct execution |
| MCP tools | AgentCore Gateway | Streamable HTTP, OAuth-protected |
| Unified registry | Agent framework layer (Strands/LangChain) | Merges `toolConfig` tools + MCP `tools/list` |
| Routing logic | Custom orchestrator or Strands Agent | Tool metadata tags determine path |
| Hot-path execution | Lambda with provisioned concurrency | <50ms cold start |
| Cold-path execution | AgentCore Gateway → target | 200-500ms including auth |

### WHAT IF NOT (Anti-Pattern)

Without hybrid architecture:
- **All-MCP**: Every tool call pays network + auth + discovery overhead → unacceptable for math operations, string formatting, or any sub-100ms tool
- **All-programmatic**: Loses cross-platform reuse, dynamic discovery, centralized governance → tool sprawl returns
- **Inconsistent UX**: Some tools work in Claude but not GPT, others vice versa → developer confusion
- **Over-engineering simple tools**: Wrapping a 3-line calculator function in an MCP server adds operational complexity with zero benefit

---

## 4. API Gateway as Agent Interface (Exposing Enterprise APIs to Agents)

### WHAT Is It

This pattern uses a managed gateway service to transform existing enterprise REST APIs into agent-consumable tools. The gateway acts as a protocol translator—it accepts MCP requests from agents, translates them to HTTP API calls, handles authentication, and returns structured results. It solves the "last mile" problem of making legacy/existing APIs available to AI agents without modifying the APIs themselves.

Amazon Bedrock AgentCore Gateway is the canonical AWS implementation: it accepts OpenAPI specifications or Smithy models as input and automatically generates MCP-compatible tool interfaces, handling schema translation, credential management, and observability. [AgentCore Gateway Introduction](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-gateway-transforming-enterprise-ai-agent-tool-development/)

Key gateway functions:
- **Protocol translation**: MCP ↔ REST/GraphQL/gRPC
- **Schema generation**: OpenAPI spec → MCP tool definitions (automatic)
- **Credential management**: Inbound OAuth validation + outbound credential injection
- **Composition**: Multiple APIs/Lambda functions → single MCP endpoint
- **Rate limiting & circuit breaking**: Protect backends from agent traffic patterns
- **Observability**: Per-tool, per-agent metrics and audit trails

### WHO Needs It

- **Enterprises with existing API catalogs** (hundreds of REST APIs) that want agent access without rewriting
- **Security/compliance teams** requiring a single control plane for all agent-to-system traffic
- **Organizations with heterogeneous auth** (API keys, OAuth, IAM, SAML) needing unified credential management
- **Platform teams** wanting to offer "tools as a service" to agent developers without exposing raw infrastructure
- **Regulated industries** (finance, healthcare) needing audit trails of every agent action

### WHY NOW (2025–2026)

- AWS launched AgentCore Gateway (August 2025) as a fully managed service, removing the need to build custom protocol bridges [AgentCore Gateway Blog](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-gateway-transforming-enterprise-ai-agent-tool-development/)
- Kong, Cloudflare, and other API gateway vendors added MCP-native support in 2025-2026, creating a competitive category [Kong MCP Registry](https://konghq.com/blog/learning-center/what-is-an-mcp-registry)
- The explosion of AI agents in enterprise (PwC, Deloitte, Accenture all shipping agent products) created urgent demand for API-to-agent bridges [PwC Agent OS](https://www.pwc.com/us/en/about-us/newsroom/press-releases/pwc-adds-support-for-mcp-in-agent-os.html)
- OpenAPI specification (v3.1+) became the de facto enterprise API contract format, making automatic schema translation feasible
- The "LLM Tool Gateway" emerged as a distinct infrastructure category in 2026 [LLM Tool Gateways Guide](https://o-mega.ai/articles/llm-tool-gateways-the-2026-builder-s-guide)

### WHERE in the Architecture

```
[AI Agents] → [MCP Client] → [API Gateway / AgentCore Gateway]
                                        ↓
                              ┌─────────┼─────────┐
                              ↓         ↓         ↓
                        [REST API]  [Lambda]  [Smithy Service]
                        (OpenAPI)   (Custom)   (AWS native)
```

The gateway replaces: custom MCP server implementations per API, bespoke auth handling per integration, manual tool schema authoring.

It sits at the **integration boundary**—the trust perimeter between agent-controlled traffic and enterprise backend systems.

### HOW on AWS

| Component | AWS Service | Detail |
|-----------|-------------|--------|
| Gateway | Amazon Bedrock AgentCore Gateway | `protocolType='MCP'`, Streamable HTTP |
| API targets | OpenAPI spec on S3 | `targetConfiguration.mcp.openApiSchema.s3.uri` |
| Lambda targets | Lambda function ARN | `targetConfiguration.mcp.lambda.lambdaArn` |
| Inbound auth | Cognito + Custom JWT | `authorizerType='CUSTOM_JWT'`, supports multiple client IDs |
| Outbound auth (API key) | AgentCore Identity | `create_api_key_credential_provider()` |
| Outbound auth (OAuth) | AgentCore Identity | 2LO client credentials grant |
| Outbound auth (IAM) | Gateway IAM Role | For Lambda and Smithy targets |
| Semantic discovery | Built-in search tool | `x_amz_bedrock_agentcore_search` with SEMANTIC searchType |
| VPC access | AgentCore VPC connectivity | PrivateLink for private APIs |
| Monitoring | CloudWatch + CloudTrail | Invocation metrics, latency, error rates |

[AgentCore Gateway Docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)

### WHAT IF NOT (Anti-Pattern)

Without an API gateway pattern:
- **Direct client-to-tool connections**: Every agent connects directly to APIs → no isolation layer, one tool failure = system-wide outage [Enterprise MCP Architecture](https://markaicode.com/architecture/enterprise-mcp-architecture/)
- **Custom MCP servers per API**: Engineering teams build and maintain hundreds of bespoke MCP servers → unsustainable operational burden
- **Credential sprawl**: Each agent stores its own API keys → leaked credentials, no rotation policy, audit gaps
- **No traffic shaping**: Agents generate unpredictable burst patterns → backends overwhelmed without rate limiting
- **Schema drift**: API changes break agents silently → no versioning or compatibility layer

---

## 5. Tool Registry & Discovery (Agents Finding Available Tools at Runtime)

### WHAT Is It

A tool registry is a centralized catalog that tells agents what tools exist, where they're deployed, what they do, and how to connect to them. It solves the "how does the agent know which tools exist?" problem that MCP alone doesn't answer. Think of it as the service catalog for the agentic era—a discovery layer whose primary consumers are machines querying programmatically, not humans browsing documentation. [Kong: What Is an MCP Registry](https://konghq.com/blog/learning-center/what-is-an-mcp-registry)

Registry capabilities:
- **Tool metadata storage**: Name, description, input/output schema, version, owner, SLA
- **Semantic search**: Natural language queries to find relevant tools ("find tools that query customer data")
- **Access control**: Per-agent or per-role tool allowlists
- **Version management**: Multiple versions of the same tool with routing rules
- **Health/availability**: Real-time status of tool backends
- **Usage analytics**: Which agents use which tools, call frequency, error rates

Discovery mechanisms:
1. **Static list** (`tools/list`): Agent retrieves full catalog at session start—works for <50 tools
2. **Semantic search**: Agent searches by intent, receives relevant subset—scales to thousands of tools
3. **Contextual filtering**: Registry returns tools based on user role, task type, or conversation state

[TrueFoundry: MCP Tool Discovery](https://www.truefoundry.com/blog/mcp-tool-discovery-for-enterprise-ai-agents)

### WHO Needs It

- **Organizations scaling beyond 50 tools**: Full tool catalogs overwhelm model context windows and cause "tool overload" hallucinations
- **Multi-team enterprises**: Different teams publish tools independently; agents need to discover across org boundaries
- **Governance/security teams**: Need visibility into which agents access which tools, with ability to revoke
- **Agent developers**: Want to discover existing tools before building new ones (avoid duplication)
- **Organizations with dynamic tool landscapes**: Tools added/removed frequently (microservices, SaaS integrations)

### WHY NOW (2025–2026)

- "Tool overload" became a recognized failure mode: agents presented with >30 tools experience degraded accuracy due to context window consumption and decision complexity [AgentCore Gateway Blog](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-gateway-transforming-enterprise-ai-agent-tool-development/)
- Arxiv research (2508.03095) formalized agent registry infrastructure patterns across centralized, enterprise, and distributed approaches [Agent Registry Architectures](https://arxiv.org/html/2508.03095)
- AWS AgentCore Gateway shipped built-in semantic search (`x_amz_bedrock_agentcore_search`) that returns only relevant tools per query
- Kong, Arcade.dev, and others launched dedicated MCP registry products in early 2026 [Arcade.dev MCP Gateways Guide](https://www.arcade.dev/blog/mcp-gateways-runtimes-registries-guide)
- Arthur.ai documented the "agent discovery and governance" landscape with 10+ competing platforms [Arthur.ai Agent Discovery](https://www.arthur.ai/column/agent-discovery-governance-landscape)
- GitHub community projects (agentic-community/mcp-gateway-registry) demonstrated open-source enterprise registry patterns [MCP Gateway Registry](https://github.com/agentic-community/mcp-gateway-registry)

### WHERE in the Architecture

```
[Agent] → "I need to check inventory" → [Tool Registry / Semantic Search]
                                                    ↓
                                          [Relevant Tool Subset]
                                          (3-5 tools, not 500)
                                                    ↓
[Agent] → [Selected Tool] → [MCP Gateway or Direct Call] → [Backend]
```

The registry sits **above** MCP servers but **below** the agent orchestrator—it's the discovery layer that curates what the agent sees:

```
[Agent Framework] → [Tool Registry (Discovery)] → [MCP Gateway (Execution)] → [Tools]
```

### HOW on AWS

| Component | AWS Service | Detail |
|-----------|-------------|--------|
| Registry + search | AgentCore Gateway semantic search | `searchType: "SEMANTIC"` in gateway config |
| Search invocation | Built-in MCP tool | `x_amz_bedrock_agentcore_search` with natural language query |
| Embedding model | Bedrock (automatic) | Powers semantic matching of query to tool descriptions |
| Tool metadata | Gateway target definitions | Name, description, schema per target |
| Access control | OAuth scopes + gateway config | Per-client tool visibility |
| Custom registry | DynamoDB + OpenSearch | For organizations needing custom metadata/workflows |
| Governance | CloudTrail + custom dashboards | Track tool usage per agent/user |

Configuration to enable semantic discovery:
```python
search_config = {
    "mcp": {"searchType": "SEMANTIC", "supportedVersions": ["2025-03-26"]}
}
response = agentcore_client.create_gateway(
    name='MyGateway',
    protocolConfiguration=search_config,
    # ... other config
)
```

### WHAT IF NOT (Anti-Pattern)

Without tool registry and discovery:
- **Full catalog in every prompt**: 500 tool definitions consume 50K+ tokens → expensive, slow, reduced reasoning quality
- **Hardcoded tool lists**: Agent can only use tools known at build time → no adaptability to new capabilities
- **Tool overload hallucinations**: Model selects wrong tool or invents non-existent tools when overwhelmed
- **Duplicate tools**: Multiple teams build the same integration → wasted effort, inconsistent behavior
- **No governance**: No visibility into which agents access which tools → compliance violations, shadow AI

---

## 6. Action Groups / Function Calling Schemas

### WHAT Is It

Action Groups are a structured abstraction (pioneered by Amazon Bedrock Agents) that packages related tools into logical groups with shared configuration—execution backend, authentication, guardrails, and return behavior. Each action group defines the APIs an agent can call and the logic for calling them, providing a higher-level organizational unit than individual tool definitions.

Function Calling Schemas are the JSON Schema-based contracts that define individual tools within action groups. They specify:
- Function name and description (used by the model for selection)
- Input parameters with types, descriptions, and validation rules
- Required vs. optional parameters
- Return schema (increasingly supported in 2025-2026)

The distinction from raw function calling: Action Groups add **operational semantics**—they define not just *what* a tool does but *how* it should be executed (Lambda, HTTP, return-to-caller), *who* can invoke it (IAM policies), and *what happens on failure* (retry, fallback).

Note: Amazon Bedrock Agents Classic (the original action groups implementation) transitioned to Bedrock AgentCore in 2026, with new customers directed to AgentCore after July 30, 2026. [Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-how.html)

Key schema patterns across providers:
- **OpenAI**: `functions[]` → `tools[{type: "function", function: {name, description, parameters}}]`
- **Anthropic**: `tools[{name, description, input_schema}]`
- **Bedrock Converse**: `toolConfig.tools[{toolSpec: {name, description, inputSchema}}]`
- **Bedrock Agents Classic**: Action Groups with OpenAPI spec or Lambda function schemas

[MCP vs OpenAPI Plugins vs Custom Tool Calling](https://startdebugging.net/2026/06/mcp-vs-openapi-plugins-vs-custom-tool-calling-for-ai-agents/)

### WHO Needs It

- **Any team using LLM tool calling**: Schemas are the foundational primitive—without them, models can't reliably call tools
- **Organizations standardizing across providers**: Need translation layers between OpenAI/Anthropic/Bedrock schema formats
- **Teams building complex agents**: Action groups provide logical bundling (e.g., "CRM actions", "billing actions") for governance and observability
- **Enterprises with "return control" patterns**: Where the agent must hand execution back to the application (e.g., for human approval workflows)
- **API product teams**: Want to make existing APIs agent-ready with minimal changes

### WHY NOW (2025–2026)

- Schema convergence: All major providers settled on JSON Schema as the tool definition format, making cross-provider tooling feasible [Prefect: MCP vs Function Calling](https://www.prefect.io/resources/mcp-vs-function-calling)
- Bedrock Converse API (2024-2025) unified tool calling across 20+ models with a single schema format—previously each model family had different tool formats
- "Return control" patterns matured: Bedrock's `RETURN_CONTROL` action group signature lets agents pause for human approval without breaking the conversation flow [Bedrock Return Control](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-returncontrol.html)
- OpenAI's "strict mode" (2024-2025) and Anthropic's "tool use with streaming" eliminated common schema compliance failures
- The migration from Bedrock Agents Classic to AgentCore (2026) validated action groups as a production pattern worth preserving in next-gen architectures
- TuringPost (July 2026): "In 2026, tool integration is moving toward function calling, MCP, and structured agent frameworks" [TuringPost: The Architecture of Action](https://www.turingpost.com/p/action)

### WHERE in the Architecture

```
[Agent Definition Layer]
    └── Action Group: "Order Management"
            ├── Tool: get_order (inputSchema: {orderId: string})
            ├── Tool: update_order (inputSchema: {orderId, status, note})
            └── Tool: cancel_order (inputSchema: {orderId, reason})
                    ↓ (execution)
            [Lambda Function / API Endpoint]
```

Action groups sit at the **agent definition layer**—above the raw model API but below the business logic. They're the unit of:
- **Deployment**: An action group is deployed/versioned as a unit
- **Authorization**: IAM policies attach at the action group level
- **Monitoring**: Metrics aggregate by action group
- **Testing**: Action groups are the unit of integration testing

### HOW on AWS

| Component | AWS Service | Detail |
|-----------|-------------|--------|
| Action group definition | Bedrock AgentCore (or Agents Classic) | OpenAPI spec or inline function schemas |
| Execution | Lambda functions | Event-driven, per-invocation billing |
| Schema format | OpenAPI 3.0 or inline `functionSchema` | JSON Schema for each function |
| Return control | `parentActionGroupSignature: AMAZON.UserInput` | Agent returns elicited info to caller |
| Powertools integration | AWS Lambda Powertools for Python | `@app.tool()` decorator auto-generates schemas |
| Schema validation | Bedrock service-side | Validates model output against schema before execution |
| Versioning | Agent aliases + versions | Route traffic between action group versions |

Bedrock Agents Classic action group creation:
```python
response = bedrock_agent.create_agent_action_group(
    agentId='AGENT_ID',
    agentVersion='DRAFT',
    actionGroupName='OrderManagement',
    actionGroupExecutor={'lambda': 'arn:aws:lambda:...'},
    functionSchema={
        'functions': [
            {
                'name': 'get_order',
                'description': 'Retrieve order details by ID',
                'parameters': {
                    'orderId': {
                        'type': 'string',
                        'description': 'The order identifier',
                        'required': True
                    }
                }
            }
        ]
    }
)
```

### WHAT IF NOT (Anti-Pattern)

Without action groups / structured schemas:
- **Hallucinated function calls**: Without strict schema, model invents parameter names or calls non-existent functions
- **No execution boundary**: Individual tools have no logical grouping → can't apply policies, monitoring, or access control at meaningful granularity
- **Schema drift**: Tool implementations change but model-facing definitions don't → silent failures
- **Provider lock-in at the schema level**: Teams hard-code OpenAI format, then can't switch to Bedrock without rewriting all definitions
- **No return-control pattern**: Agent can't pause for human approval → either fully autonomous (risky) or fully manual (slow)

---

## Summary: Key Takeaways

### The 2025–2026 Landscape

1. **Function calling and MCP are complementary layers, not competitors.** Function calling is the model-level primitive (how the LLM emits structured tool requests). MCP is the transport/integration standard (how tools are discovered, authenticated, and invoked across systems). Every production system needs both.

2. **The API Gateway has become the critical control plane for agent-to-tool traffic.** AWS AgentCore Gateway, Kong MCP Gateway, and others represent a new infrastructure category—the "LLM Tool Gateway"—that didn't exist before 2025. It provides the missing security, observability, and governance layer.

3. **Tool discovery/registry is the emerging differentiator.** As tool catalogs scale beyond 50-100 tools, semantic search and intelligent filtering become essential. "Tool overload" is now a recognized failure mode that degrades agent accuracy.

4. **Hybrid architectures win in production.** Pure-MCP adds unnecessary overhead for simple/owned tools. Pure-programmatic loses governance and reuse. The pattern: MCP for shared/external/discoverable tools + programmatic for owned/hot-path/simple tools.

5. **AWS's trajectory: Bedrock Agents Classic → AgentCore.** The transition (completing July 2026) consolidates action groups, MCP gateway, tool registry, and runtime into a unified platform. AgentCore Gateway is the centerpiece—zero-code API-to-MCP conversion with built-in semantic discovery.

6. **Security is non-negotiable.** The April 2026 STDIO RCE vulnerability demonstrated that ungoverned MCP access is an enterprise-grade security risk. OAuth 2.1, tool allowlists, and gateway-mediated access are now mandatory patterns, not nice-to-haves.

### Pattern Selection Guide

| Your Constraint | Primary Pattern | AWS Service |
|----------------|-----------------|-------------|
| Single app, <10 tools, latency-critical | Programmatic Tool Calling | Bedrock Converse API |
| Multi-agent, multi-provider, shared tools | MCP Server Architecture | AgentCore Gateway + Runtime |
| Mixed workload (fast + discoverable) | Hybrid Tool Access | Bedrock Converse + AgentCore Gateway |
| Large existing API catalog | API Gateway as Agent Interface | AgentCore Gateway (OpenAPI targets) |
| >50 tools, dynamic landscape | Tool Registry & Discovery | AgentCore semantic search |
| Team needs logical tool bundling | Action Groups | AgentCore (or Agents Classic) |
