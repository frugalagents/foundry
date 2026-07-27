# Agentic Platform Advisor App — Product Requirements Document & Architecture Spec

> **Version:** 1.0  
> **Author:** Aish Gopalan  
> **Date:** July 2026  
> **Status:** Implementation-Ready Draft  
> **Audience:** Engineering team, product stakeholders

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Tech Stack Details](#3-tech-stack-details)
4. [Data Model (DynamoDB)](#4-data-model-dynamodb)
5. [Auth Model (Cognito)](#5-auth-model-cognito)
6. [API Design](#6-api-design)
7. [Frontend Components](#7-frontend-components)
8. [Backend Skills Architecture](#8-backend-skills-architecture)
9. [MCP Integration Plan](#9-mcp-integration-plan)
10. [Streaming / A2UI Protocol](#10-streaming--a2ui-protocol)
11. [Admin Panel Design](#11-admin-panel-design)
12. [Deployment Architecture](#12-deployment-architecture)
13. [Implementation Phases](#13-implementation-phases)
14. [Open Questions](#14-open-questions)

---

## 1. Executive Summary

### What

The **Agentic Platform Advisor App** is a standalone web application that guides enterprise leaders (VP Engineering, Enterprise Architects, CTOs) through a deterministic, graph-driven decision process to produce tailored AI agent platform architecture blueprints. It is the **MVP 1** of the Enterprise AI Foundry vision — the Platform Strategy Advisor.

### Why

Enterprise leaders face information overload + no opinionated guidance for their specific constraints. Consulting engagements take weeks. This app produces a personalized, scored, visually-rich architecture blueprint in **< 15 minutes** through a structured 8-step pipeline.

### How

A **Next.js 15 frontend** with a split-panel interface (chat left, visual panels right) communicates via SSE with a **Strands SDK (Python) agent** running on **AgentCore Runtime**. The agent executes a modular skills pipeline, traverses a knowledge graph stored in DynamoDB, queries live MCP sources, and streams structured panel events to the frontend for progressive visual rendering.

### Key Differentiators

| Capability | How Achieved |
|-----------|-------------|
| **Deterministic + Explainable** | Graph traversal with visible scoring, not black-box LLM reasoning |
| **Visual-first UX** | A2UI pattern — agent sends structured data, frontend renders rich components |
| **Always current** | MCP integrations pull live AWS docs, workshops, innovations |
| **Modular / Evolvable** | New knowledge = new graph nodes/edges, not code changes |
| **Executive-grade aesthetic** | Dark theme, progressive disclosure, Bloomberg Terminal meets McKinsey |

---

## 2. Architecture Overview

### System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AGENTIC PLATFORM ADVISOR                        │
│                                                                         │
│  ┌────────────────┐         ┌──────────────────────────────────────┐   │
│  │  NEXT.JS 15    │   SSE   │        STRANDS SDK AGENT             │   │
│  │  FRONTEND      │◄───────►│        (AgentCore Runtime)           │   │
│  │                │         │                                      │   │
│  │  Chat (35%)    │         │  ┌──────┐ ┌──────┐ ┌──────┐       │   │
│  │  Visual (65%)  │         │  │Skill │ │Skill │ │Skill │ ...   │   │
│  │                │         │  │  1   │ │  2   │ │  3   │       │   │
│  └───────┬────────┘         │  └──────┘ └──────┘ └──────┘       │   │
│          │                  │                                      │   │
│          │                  └─────────────┬────────────────────────┘   │
│          │                                │                             │
│  ┌───────┴────────┐         ┌─────────────┴────────────────────────┐   │
│  │  COGNITO       │         │         DATA LAYER                    │   │
│  │  Auth/SSO      │         │                                      │   │
│  └────────────────┘         │  DynamoDB    S3       MCP Servers    │   │
│                             │  (graph,     (PDFs,   (AWS Docs,     │   │
│                             │   sessions,  diagrams) Knowledge,    │   │
│                             │   customers)          Highspot)      │   │
│                             └──────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Request Flow (Happy Path)

```
1. User authenticates via Cognito (Amazon SSO / SAML)
2. User selects/creates customer → creates/resumes session
3. Frontend establishes SSE connection to agent endpoint
4. User provides intake answers (chat or interactive form)
5. Agent executes skills pipeline (Steps 1→8):
   a. Each skill computes its output
   b. Each skill emits PanelEvent(s) via SSE stream
   c. Frontend renders corresponding React component
6. User sees visual panels populate progressively
7. Session state persisted to DynamoDB at each step
8. User can adjust inputs → agent re-runs from that step forward
9. Final blueprint exportable as PDF/PPTX
```

### Key Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | Strands SDK (Python) | AWS-native, modular skills, AgentCore-compatible |
| Frontend framework | Next.js 15 (App Router) | SSR for initial load, client components for streaming panels |
| Streaming protocol | Server-Sent Events (SSE) | Simpler than WebSocket for unidirectional agent→UI flow; fallback to WebSocket for bidirectional needs |
| Graph storage | DynamoDB (single-table) | Low latency, serverless, fits graph-as-JSON for MVP; upgrade path to Neptune |
| Panel rendering | Pre-built React components | Agent sends data, not HTML — separation of concerns, faster iteration |
| Auth | Cognito + Amazon SSO | Enterprise-grade, SAML/SSO, group-based RBAC |

---

## 3. Tech Stack Details

### Frontend

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Framework | Next.js | 15.x | App Router, RSC, streaming |
| Language | TypeScript | 5.x | Type safety, interfaces for A2UI |
| Styling | Tailwind CSS | 4.x | Dark theme utility classes |
| Charts | Highcharts | 11.x | Radar chart (Step 2), timeline |
| Diagrams | D3.js + SVG | 7.x | Architecture diagrams, service maps |
| State | Zustand | 5.x | Client state for session/panels |
| HTTP | Built-in fetch + EventSource | — | SSE streaming |
| Icons | Lucide React + AWS Icons | — | UI + service badges |
| PDF Export | @react-pdf/renderer | — | Blueprint export |
| Animation | Framer Motion | 11.x | Panel transitions, progressive reveal |

### Backend

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Agent SDK | AWS Strands SDK | Latest | Agent orchestration, skill execution |
| Language | Python | 3.12+ | Strands native language |
| Runtime | AgentCore Runtime | — | Serverless agent hosting, session isolation |
| API Layer | API Gateway (HTTP API) | v2 | WebSocket/SSE endpoint, auth integration |
| Compute | Lambda (API) + AgentCore (Agent) | — | API handlers → invoke AgentCore agent |
| Graph Engine | Custom Python module | — | Deterministic graph traversal (no LLM for scoring) |

### Infrastructure

| Component | Service | Configuration |
|-----------|---------|---------------|
| Auth | Amazon Cognito | User Pool + Identity Pool, SAML federation |
| Database | DynamoDB | Single-table design, on-demand capacity |
| Storage | S3 | Generated diagrams, PDF exports, graph snapshots |
| CDN/Hosting | Amplify Hosting | Next.js SSR deployment |
| Secrets | Secrets Manager | MCP API keys, Cognito client secrets |
| Monitoring | CloudWatch + X-Ray | Agent traces, skill latency, error rates |
| CI/CD | CodePipeline + CodeBuild | Trunk-based, preview deployments |

### MCP Servers

| Server | Purpose | Invocation |
|--------|---------|-----------|
| AWS Documentation MCP | Service details, features, API specs | `aws_search_documentation`, `aws_read_documentation` |
| AWS Knowledge MCP | Workshops, prescriptive guidance, blogs | `aws_search_documentation`, `aws_recommend` |
| AWS Highspot MCP | Sales positioning, competitive intel | `highspot_search`, `get_instant_answer` |
| Diagram Generation MCP | SVG/Mermaid rendering for exec visuals | Custom (proposed — see §9) |

---

## 4. Data Model (DynamoDB)

### Storage Responsibility Matrix

The app uses **three stores** — each with a clear, non-overlapping purpose:

| Data | Storage | Update Cadence |
|------|---------|----------------|
| **All curated knowledge** (pattern docs, research, anti-patterns, compliance, AgentCore mapping, innovation map, technology patterns, graph.json) | **Bedrock Knowledge Base** (S3 bucket → auto-indexed) | Weekly / Monthly / Quarterly |
| **Conversation state + pipeline outputs** | **AgentCore Memory (session)** | Real-time (per session) |
| **Customer long-term context** (past blueprints, decisions, follow-ups) | **AgentCore Memory (persistent)** | On session end |
| **Customer/session metadata** (name, industry, dates, status) | **DynamoDB** | On create / session end |
| **Graph learning proposals** (weight adjustments) | **DynamoDB** | On session end |
| **Config** (prompts, skill toggles, MCP settings) | **DynamoDB** | Admin edits |
| **Generated artifacts** (PDF exports, diagrams) | **S3** | Per session |
| **Auth** | **Cognito** | — |

**Key Principle:** The agent reads from TWO sources for reasoning: (1) **AgentCore Memory** for session/customer context, and (2) **Bedrock Knowledge Base** for curated knowledge. DynamoDB serves the frontend + admin panel only.

```
┌──────────────────────────────────────────────────────────────────┐
│ AGENT (Strands)               │  FRONTEND / ADMIN                │
│                               │                                   │
│ Reads:                        │  Reads/Writes:                    │
│ • AgentCore Memory            │  • DynamoDB (metadata, config)    │
│   (session + persistent)      │  • S3 (artifacts)                 │
│ • Bedrock Knowledge Base      │                                   │
│   (all curated docs + graph)  │  Publishes TO Bedrock KB:         │
│ • MCP Servers (live)          │  • Updated docs (admin panel)     │
│                               │  • Updated graph (on approval)    │
│ Writes:                       │                                   │
│ • AgentCore Memory            │                                   │
│ • DynamoDB (session meta,     │                                   │
│   on complete only)           │                                   │
└──────────────────────────────────────────────────────────────────┘
```

**Knowledge Update Pipeline:**
```
S3 Bucket (bedrock-kb-platform-advisor/)
       │ upload docs (admin panel or CI/CD)
       ▼
Bedrock Knowledge Base (re-index / sync)
       │ available to agent at runtime
       ▼
Agent reads via KB Retrieve API
```

Docs are managed directly in S3 (via admin panel upload or CI/CD pipeline). No intermediate authoring layer needed.

---

### Single-Table Design

**Table Name:** `platform-advisor-main`

| Partition Key (PK) | Sort Key (SK) | Entity Type | Description |
|--------------------|--------------:|-------------|-------------|
| `CUST#<customer_id>` | `META` | Customer | Customer metadata |
| `CUST#<customer_id>` | `SESSION#<session_id>` | Session | Session summary/status |
| `CUST#<customer_id>` | `SESSION#<sid>#STEP#<n>` | StepOutput | Output of pipeline step N |
| `CUST#<customer_id>` | `SESSION#<sid>#PANEL#<n>` | PanelState | Cached panel data for replay |
| `CUST#<customer_id>` | `SESSION#<sid>#INPUT` | IntakeAnswers | User's 12 answers + metadata |
| `USER#<user_id>` | `META` | User | User profile, group membership |
| `USER#<user_id>` | `CUST#<customer_id>` | UserCustomerLink | Which customers a user owns |
| `GRAPH#<version>` | `NODE#<node_id>` | GraphNode | Knowledge graph nodes |
| `GRAPH#<version>` | `EDGE#<edge_id>` | GraphEdge | Knowledge graph edges |
| `CONFIG#SYSTEM` | `PROMPT#<version>` | SystemPrompt | Versioned system prompts |
| `CONFIG#SYSTEM` | `SKILL#<skill_name>` | SkillConfig | Skill enable/disable + params |
| `ADMIN#METRICS` | `<date>#<metric>` | Metric | Usage analytics |

### Entity Schemas

#### Customer

```typescript
interface Customer {
  pk: string;              // CUST#<uuid>
  sk: 'META';
  entity_type: 'Customer';
  customer_id: string;
  name: string;
  industry: string;
  owner_user_id: string;   // creator
  shared_with: string[];   // other user_ids with access
  metadata: {
    company_size: string;
    region: string;
    notes: string;
  };
  created_at: string;      // ISO 8601
  updated_at: string;
  session_count: number;
  gsi1pk: string;          // USER#<owner_id> — for user's customer list
  gsi1sk: string;          // CUST#<customer_id>
}
```

#### Session

```typescript
interface Session {
  pk: string;              // CUST#<customer_id>
  sk: string;              // SESSION#<uuid>
  entity_type: 'Session';
  session_id: string;
  customer_id: string;
  user_id: string;         // who ran this session
  status: 'intake' | 'scoring' | 'components' | 'innovation' | 'services' | 'antipatterns' | 'phasing' | 'blueprint' | 'complete';
  current_step: number;    // 1-8
  pattern_selected: string | null;
  pattern_scores: Record<string, number> | null;
  created_at: string;
  updated_at: string;
  graph_version: string;   // which graph version was used
  ttl: number;             // auto-expire after 90 days (configurable)
}
```

#### IntakeAnswers

```typescript
interface IntakeAnswers {
  pk: string;              // CUST#<customer_id>
  sk: string;              // SESSION#<sid>#INPUT
  entity_type: 'IntakeAnswers';
  answers: {
    autonomy_model: 'full' | 'hitl' | 'supervised';
    team_expertise: 'high' | 'medium' | 'low';
    cloud_posture: 'single_aws' | 'aws_primary' | 'multi_cloud';
    stack_preference: 'open_source' | 'managed' | 'hybrid';
    lob_count: '1-3' | '4-10' | '10+';
    governance_model: 'centralized' | 'federated' | 'undecided';
    auth_identity: 'oauth_oidc' | 'iam_heavy' | 'greenfield' | 'complex_multi';
    observability: 'existing_stack' | 'greenfield';
    intake_maturity: 'mature' | 'emerging' | 'greenfield';
    agent_purpose: 'internal' | 'customer_facing' | 'both';
    cost_sensitivity: 'primary' | 'secondary' | 'optimize_later';
    data_gravity: 'single_region' | 'multi_region' | 'on_prem_cloud' | 'edge';
  };
  industry: string;
  pain_points: string[];
}
```

#### PanelState (for session replay)

```typescript
interface PanelState {
  pk: string;              // CUST#<customer_id>
  sk: string;              // SESSION#<sid>#PANEL#<step_number>
  entity_type: 'PanelState';
  step: number;
  panel_type: PanelType;
  data: any;               // structured data that the React component renders
  rendered_at: string;
  is_final: boolean;       // false while streaming, true when complete
}
```

### Global Secondary Indexes (GSIs)

| GSI Name | PK | SK | Purpose |
|----------|----|----|---------|
| `GSI1` | `gsi1pk` | `gsi1sk` | User's customer list, admin queries |
| `GSI2` | `entity_type` | `created_at` | Admin dashboard: list all sessions, customers |
| `GSI3` | `graph_version` | `sk` | Graph node/edge queries |

### Graph Storage Strategy

For MVP, the knowledge graph (~150 nodes, ~600 edges) is stored in DynamoDB but **loaded entirely into memory** at agent startup (or cached per session). This gives:
- Sub-millisecond traversal (no per-query DB calls during scoring)
- Atomic graph updates (write new version, swap pointer)
- Version history (each graph version is a set of rows)

**Upgrade path:** When graph exceeds 1000 nodes or needs real-time collaborative editing, migrate to Neptune Serverless with Gremlin queries.

---

## 5. Auth Model (Cognito)

### Cognito Configuration

```yaml
UserPool:
  Name: platform-advisor-users
  SignInAliases: [email]
  MFA: Optional (TOTP)
  PasswordPolicy:
    MinLength: 12
    RequireUppercase: true
    RequireNumbers: true
    RequireSymbols: true
  
  ExternalProviders:
    SAML:
      - Provider: AmazonSSO
        MetadataURL: <amazon-sso-metadata-url>
        AttributeMapping:
          email: http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress
          name: http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name
          groups: custom:groups

Groups:
  - Name: admin
    Description: Full access — all customers, dashboards, config
    Members: [thandavm@, aigopala@]
    
  - Name: user
    Description: Standard access — own customers/sessions only
    Members: [everyone else]
```

### Authorization Model

| Resource | Admin | User |
|----------|-------|------|
| Own customers/sessions | ✅ Full CRUD | ✅ Full CRUD |
| Other users' customers | ✅ Read-only (view all) | ❌ No access |
| Admin dashboard (`/admin/dashboard`) | ✅ | ❌ Redirect to `/` |
| Config panel (`/admin/config`) | ✅ | ❌ Redirect to `/` |
| System prompt editor | ✅ Edit + version | ❌ |
| Graph schema editor | ✅ Edit + publish | ❌ |
| Skill toggles | ✅ | ❌ |
| "Switch to user view" | ✅ (demo mode) | N/A |
| Export blueprints | ✅ | ✅ (own only) |
| Usage analytics | ✅ (all users) | ❌ |

### Token Structure (JWT Claims)

```json
{
  "sub": "user-uuid",
  "email": "aigopala@amazon.com",
  "cognito:groups": ["admin"],
  "custom:display_name": "Aish Gopalan",
  "iat": 1721000000,
  "exp": 1721003600
}
```

### Middleware Enforcement (Next.js)

```typescript
// middleware.ts
export function middleware(request: NextRequest) {
  const token = request.cookies.get('id_token');
  const groups = decodeToken(token)?.['cognito:groups'] || [];
  
  // Admin routes
  if (request.nextUrl.pathname.startsWith('/admin')) {
    if (!groups.includes('admin')) {
      return NextResponse.redirect(new URL('/', request.url));
    }
  }
  
  // Customer access control handled at API layer
}
```

### Admin "Switch to User View"

Admins can toggle a `?view=user` query param that:
- Hides admin navigation
- Filters customer list to only their own
- Simulates standard user experience (for demos)
- Indicated by a subtle "Admin viewing as user" badge

---

## 6. API Design

### Base URL

```
Production: https://api.platform-advisor.aws.dev/v1
Staging:    https://api-staging.platform-advisor.aws.dev/v1
```

### Authentication

All requests require `Authorization: Bearer <cognito_id_token>` header.

### REST Endpoints

#### Customers

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/customers` | List customers (user: own only; admin: all) | User+ |
| `POST` | `/customers` | Create customer | User+ |
| `GET` | `/customers/:id` | Get customer detail | Owner/Admin |
| `PUT` | `/customers/:id` | Update customer | Owner/Admin |
| `DELETE` | `/customers/:id` | Delete customer (soft) | Owner/Admin |

#### Sessions

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/customers/:id/sessions` | List sessions for customer | Owner/Admin |
| `POST` | `/customers/:id/sessions` | Create new session | Owner/Admin |
| `GET` | `/customers/:id/sessions/:sid` | Get session detail + status | Owner/Admin |
| `DELETE` | `/customers/:id/sessions/:sid` | Delete session | Owner/Admin |
| `GET` | `/customers/:id/sessions/:sid/panels` | Get all cached panel states (replay) | Owner/Admin |
| `GET` | `/customers/:id/sessions/:sid/panels/:step` | Get specific panel state | Owner/Admin |
| `PUT` | `/customers/:id/sessions/:sid/inputs` | Update intake answers (triggers re-run) | Owner/Admin |

#### Agent Streaming (SSE)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/customers/:id/sessions/:sid/run` | Start/resume agent pipeline (returns SSE stream) | Owner/Admin |
| `POST` | `/customers/:id/sessions/:sid/message` | Send chat message to agent (within active stream) | Owner/Admin |
| `POST` | `/customers/:id/sessions/:sid/whatif` | Trigger what-if scenario (re-run from step N) | Owner/Admin |

#### Admin

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/admin/dashboard` | Aggregated usage metrics | Admin |
| `GET` | `/admin/config/prompts` | List system prompt versions | Admin |
| `POST` | `/admin/config/prompts` | Save new prompt version | Admin |
| `GET` | `/admin/config/graph` | Get current graph (JSON) | Admin |
| `PUT` | `/admin/config/graph` | Update graph (new version) | Admin |
| `GET` | `/admin/config/skills` | List skills + status | Admin |
| `PUT` | `/admin/config/skills/:name` | Enable/disable skill | Admin |
| `GET` | `/admin/config/mcp-status` | MCP connection health check | Admin |

#### Export

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/customers/:id/sessions/:sid/export` | Generate PDF/PPTX export | Owner/Admin |
| `GET` | `/customers/:id/sessions/:sid/export/:format` | Download generated export | Owner/Admin |

### SSE Stream Format

The `/run` endpoint returns a text/event-stream with typed events:

```
event: panel_update
data: {"type":"panel_update","step":2,"panel_type":"radar_chart","data":{...},"streaming":true}

event: panel_complete  
data: {"type":"panel_complete","step":2,"panel_type":"radar_chart","data":{...},"streaming":false}

event: chat_message
data: {"type":"chat_message","content":"Based on your constraints, Federated scores highest.","step":2}

event: step_transition
data: {"type":"step_transition","from":2,"to":3,"status":"awaiting_confirmation"}

event: error
data: {"type":"error","message":"MCP connection failed","recoverable":true,"step":4}

event: complete
data: {"type":"complete","session_id":"...","total_steps_completed":8}
```

---

## 7. Frontend Components

### Application Shell

```
┌─────────────────────────────────────────────────────────────────────┐
│  ┌─────────┐  Platform Advisor          [User ▾] [Admin ▾]         │
│  │  Logo   │                                                        │
├──┴─────────┴────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌──────────────────────────────────────────────┐  │
│  │            │  │                                              │  │
│  │  NAV       │  │              MAIN CONTENT                    │  │
│  │            │  │                                              │  │
│  │  Dashboard │  │  (varies by route)                           │  │
│  │  Customers │  │                                              │  │
│  │  Admin ▾   │  │                                              │  │
│  │            │  │                                              │  │
│  └────────────┘  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Route: `/` — Dashboard

**For Admin:**
- Quick stats cards (total customers, sessions, blueprints)
- Pattern distribution pie chart
- Recent sessions list (all users)
- Quick actions: "New Customer", "View Config"

**For User:**
- Customer list (own only)
- Recent sessions
- Quick actions: "New Customer", "Resume Session"

### Route: `/customers`

| Component | Description |
|-----------|-------------|
| `CustomerList` | Card grid showing customer name, industry, session count, last active |
| `CustomerCreateModal` | Form: name, industry, metadata |
| `CustomerSearchBar` | Filter/search customers |

### Route: `/customers/[id]`

| Component | Description |
|-----------|-------------|
| `CustomerHeader` | Name, industry badge, edit button |
| `SessionList` | Table/cards of sessions with status badges (step indicator) |
| `NewSessionButton` | "Start New Blueprint" CTA |
| `CustomerMetadata` | Sidebar with notes, company size, region |

### Route: `/customers/[id]/sessions/[sid]` — **Main Advisor Experience**

This is the core interface. Split-panel layout:

```
┌───────────────────────────────────────────────────────────────────────┐
│  ◀ Back to Customer    Session: "Q3 Platform Review"    Step 3/8 ●●●○ │
├─────────────────────────┬─────────────────────────────────────────────┤
│                         │                                             │
│  CHAT PANEL (35%)       │  VISUAL PANEL (65%)                        │
│                         │                                             │
│  ┌───────────────────┐  │  ┌─────────────────────────────────────┐   │
│  │ Agent: Let's       │  │  │                                     │   │
│  │ understand your    │  │  │  [Dynamic React Component            │   │
│  │ organization...    │  │  │   based on current step]             │   │
│  │                    │  │  │                                     │   │
│  │ User: We have 10+  │  │  │  Step 1: IntakeForm                 │   │
│  │ LOBs, multi-cloud  │  │  │  Step 2: RadarChart                 │   │
│  │                    │  │  │  Step 3: ArchitectureDiagram         │   │
│  │ Agent: Here's how  │  │  │  Step 4: InnovationOverlay          │   │
│  │ the patterns score │  │  │  Step 5: ServiceMap                  │   │
│  │                    │  │  │  Step 6: RiskCards                   │   │
│  └───────────────────┘  │  │  Step 7: PhaseTimeline               │   │
│                         │  │  Step 8: BlueprintAssembly            │   │
│  ┌───────────────────┐  │  │                                     │   │
│  │ Type a message...  │  │  └─────────────────────────────────────┘   │
│  └───────────────────┘  │                                             │
├─────────────────────────┴─────────────────────────────────────────────┤
│  Progress: ●━━━━━━━━●━━━━━━━━●━━━━━━━━○━━━━━━━━○━━━━━━━━○           │
│            Intake   Score   Components  Innovate  Services ...         │
└───────────────────────────────────────────────────────────────────────┘
```

### Visual Panel Components (React)

#### 1. `IntakeForm` (Step 1)

```typescript
interface IntakeFormProps {
  questions: IntakeQuestion[];   // 12 questions grouped by category
  answers: Partial<IntakeAnswers>;
  onAnswerChange: (questionId: string, value: string) => void;
  onSubmit: () => void;
  streaming: boolean;
}
```

**Visual design:**
- 4 category groups (Organization 🔵, Technical 🟢, Governance 🟠, Operations 🟣)
- Each question = card with 3-4 clickable pill options
- Selected pill fills with accent color
- Industry dropdown + pain points multi-select at bottom
- Completion indicator (12/12 answered)
- "Generate Blueprint →" CTA button

#### 2. `RadarChart` (Step 2)

```typescript
interface RadarChartProps {
  axes: ['Centralization', 'Federation', 'Mesh', 'Economy', 'Simplicity'];
  patterns: {
    name: string;
    scores: number[];  // 5 values, one per axis
    color: string;
    total: number;
    selected: boolean;
  }[];
  breakdown: {
    constraint: string;
    contributions: Record<string, number>;
  }[];
  confidence: number;  // 0-1, based on score gap
  streaming: boolean;
}
```

**Visual design:**
- Highcharts polar/spider chart with 5 axes
- 4 colored polygons (Centralized=blue, Federated=green, Mesh=purple, Economy=orange)
- Winning pattern polygon glows with pulse animation
- Below chart: score breakdown table showing each constraint's contribution
- Confidence badge: "High confidence" (>30% gap) / "Consider hybrid" (<20% gap)
- "Confirm pattern?" action buttons

#### 3. `ArchitectureDiagram` (Step 3)

```typescript
interface ArchitectureDiagramProps {
  layers: {
    name: string;       // "Governance", "Orchestration", "Shared Services", etc.
    components: {
      name: string;
      base_tier: number;
      final_tier: number;
      elevation_reason: string | null;
      category: string;
    }[];
  }[];
  pattern: string;
  streaming: boolean;
}
```

**Visual design:**
- SVG-based layered architecture (5 horizontal layers)
- Components as rounded cards within layers
- Tier badges: T1 (green outline), T2 (blue filled), T3 (purple glow)
- Elevated components show subtle upward arrow + reason tooltip
- Right sidebar: tier change table (Base → Final | Reason)
- Animated build-up: layers appear one at a time during streaming

#### 4. `InnovationOverlay` (Step 4)

```typescript
interface InnovationOverlayProps {
  innovations: {
    name: string;
    date_emerged: string;
    constraint_solved: string;    // user's pain point
    replaces: string | null;      // component it swaps
    enables: string | null;       // pattern it unlocks
    aws_implementation: string;
    status: 'ga' | 'preview' | 'emerging';
    verified_via_mcp: boolean;
  }[];
  before_architecture: ArchitectureDiagramProps;  // without innovations
  after_architecture: ArchitectureDiagramProps;   // with innovations
  streaming: boolean;
}
```

**Visual design:**
- Split-view or toggle: Before ↔ After architecture
- Changed components highlighted with accent glow
- Innovation cards below:
  - Constraint it solves (quoted from user's pain point)
  - What it replaces/enables
  - AWS service badge
  - Status pill (GA ✓ / Preview ⚠ / Emerging 🔬)
- Toggle switches per innovation: enable/disable and watch diagram update

#### 5. `ServiceMap` (Step 5)

```typescript
interface ServiceMapProps {
  components: {
    name: string;
    tier: number;
    aws_services: {
      name: string;
      icon_url: string;
      notes: string;
    }[];
    workshops: { title: string; url: string }[];
    alternatives: { name: string; when: string }[];
  }[];
  streaming: boolean;
}
```

**Visual design:**
- Architecture diagram from Step 3, enhanced with AWS service badges below each component
- Tabular view toggle: Component | Tier | AWS Service | Framework Support | Workshop Links
- Clickable service badges → tooltip with description + link
- Workshop links as small colored pills

#### 6. `RiskCards` (Step 6)

```typescript
interface RiskCardsProps {
  summary: {
    total_detected: number;
    addressed: number;
    requires_attention: number;
  };
  risks: {
    name: string;
    severity: 'high' | 'medium' | 'low';
    trigger_condition: string;
    status: 'prevented' | 'warning' | 'blocked';
    prevented_by: string | null;
    recommended_fix: string | null;
  }[];
  streaming: boolean;
}
```

**Visual design:**
- Summary bar at top: "3 risks detected • 2 addressed • 1 requires attention"
- Cards with colored left border:
  - ✅ Green (prevented): name + "Addressed by [Component] at Tier [N]"
  - ⚠️ Amber (warning): name + trigger + "Fix: Add [Component] to [Phase]"
  - 🚫 Red (blocked): name + "Cannot proceed without [action]"
- Unaddressed risks are larger, more prominent

#### 7. `PhaseTimeline` (Step 7)

```typescript
interface PhaseTimelineProps {
  phases: {
    id: string;         // P0, P1, P2, P3
    name: string;
    duration: string;   // "0-3 months"
    components: {
      name: string;
      tier: number;
      aws_service: string;
      effort: 'low' | 'medium' | 'high';
      dependencies: string[];  // component names
    }[];
  }[];
  dependencies: { from: string; to: string; reason: string }[];
  streaming: boolean;
}
```

**Visual design:**
- Horizontal Gantt-style timeline
- 4 phase columns (P0/P1/P2/P3) with time labels
- Component cards positioned within their phase column
- Dependency arrows (SVG paths) connecting components across phases
- Color coding by category (same as intake)
- Effort indicators (small/medium/large dot)

#### 8. `BlueprintAssembly` (Step 8)

```typescript
interface BlueprintAssemblyProps {
  executive_summary: {
    pattern: string;
    key_innovation: string;
    timeline: string;
    confidence: number;
  };
  mini_architecture: ArchitectureDiagramProps;  // compact version
  service_summary: ServiceMapProps;             // compact version
  phase_summary: PhaseTimelineProps;            // compact version
  risk_summary: RiskCardsProps;                 // compact version
  export_ready: boolean;
  streaming: boolean;
}
```

**Visual design:**
- Dashboard-style grid layout (2x2 or 2x3 cells)
- Executive Summary card prominent at top
- Mini versions of Steps 3-7 in grid cells (clickable to expand)
- Export buttons: PDF | PPTX | Share Link
- "What-if" toggle section at bottom (change inputs, see diff)

### Design System (CSS Variables)

```css
:root {
  /* Background */
  --bg-primary: #0F1117;
  --bg-card: #161B22;
  --bg-elevated: #1E2530;
  --bg-hover: #252D38;
  
  /* Text */
  --text-primary: #E6EDF3;
  --text-secondary: #8B949E;
  --text-muted: #6E7681;
  
  /* Accents */
  --accent-blue: #58A6FF;
  --accent-green: #3FB950;
  --accent-orange: #D29922;
  --accent-red: #F85149;
  --accent-purple: #A371F7;
  --accent-cyan: #56D4DD;
  
  /* Borders */
  --border-default: #30363D;
  --border-accent: #58A6FF33;
  
  /* Tier colors */
  --tier-1: #3FB950;  /* green — foundational */
  --tier-2: #58A6FF;  /* blue — managed */
  --tier-3: #A371F7;  /* purple — autonomous */
  
  /* Typography */
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', monospace;
  
  /* Spacing */
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 16px;
  
  /* Shadows */
  --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.3);
  --shadow-elevated: 0 8px 24px rgba(0, 0, 0, 0.4);
  --glow-accent: 0 0 20px rgba(88, 166, 255, 0.15);
}
```

---

## 8. Backend Skills Architecture

### Skill Design Pattern

Each skill is a self-contained Strands SDK skill module:

```python
# skills/scoring_skill.py
from strands import Skill, SkillInput, SkillOutput
from typing import Any

class ScoringSkill(Skill):
    """Step 2: Load graph, compute pattern scores, select pattern."""
    
    name = "scoring_skill"
    description = "Compute pattern affinity scores from intake answers"
    
    def execute(self, input: SkillInput) -> SkillOutput:
        # 1. Load graph from session context (already in memory)
        graph = self.context.get("graph")
        answers = input.get("intake_answers")
        
        # 2. Deterministic scoring (NO LLM here)
        scores = self._compute_scores(graph, answers)
        
        # 3. Apply laws (hard constraints)
        filtered_scores = self._apply_laws(graph, scores, answers)
        
        # 4. Select pattern
        selected = self._select_pattern(filtered_scores)
        
        # 5. Emit panel event
        self.emit_panel_event(PanelEvent(
            type="panel_update",
            step=2,
            panel_type="radar_chart",
            data={
                "axes": ["Centralization", "Federation", "Mesh", "Economy", "Simplicity"],
                "patterns": [...],
                "breakdown": [...],
                "confidence": selected.confidence
            },
            streaming=False
        ))
        
        return SkillOutput(
            result=selected,
            next_skill="component_skill",
            requires_confirmation=True  # pause for user approval
        )
```

### Skills Pipeline (Detailed)

#### Skill 1: `intake_skill`

| Attribute | Value |
|-----------|-------|
| **Step** | 1 |
| **Responsibility** | Present 12 questions, validate completeness, normalize answers |
| **Input** | User messages (chat) or structured form data (A2UI) |
| **Output** | Validated `IntakeAnswers` object |
| **MCP Dependencies** | None |
| **LLM Usage** | Conversational interpretation of free-text answers → structured values |
| **Panel Emitted** | `intake_form` (pre-filled with any answers so far) |
| **Deterministic Logic** | Validation rules (all 12 required, valid enum values) |
| **Blocking** | Cannot proceed until all 12 answered + industry + pain points |

```python
class IntakeSkill(Skill):
    REQUIRED_FIELDS = [
        'autonomy_model', 'team_expertise', 'cloud_posture',
        'stack_preference', 'lob_count', 'governance_model',
        'auth_identity', 'observability', 'intake_maturity',
        'agent_purpose', 'cost_sensitivity', 'data_gravity'
    ]
    
    def execute(self, input: SkillInput) -> SkillOutput:
        current_answers = self.context.get("intake_answers", {})
        
        # Parse new answers from user message
        new_answers = self._parse_answers(input.message, current_answers)
        merged = {**current_answers, **new_answers}
        
        # Check completeness
        missing = [f for f in self.REQUIRED_FIELDS if f not in merged]
        
        if missing:
            self.emit_panel_event(PanelEvent(
                type="panel_update", step=1, panel_type="intake_form",
                data={"answers": merged, "missing": missing, "complete": False},
                streaming=True
            ))
            return SkillOutput(result=merged, next_skill=None, awaiting_input=True)
        
        # Complete — emit final form state
        self.emit_panel_event(PanelEvent(
            type="panel_complete", step=1, panel_type="intake_form",
            data={"answers": merged, "missing": [], "complete": True},
            streaming=False
        ))
        return SkillOutput(result=merged, next_skill="scoring_skill")
```

#### Skill 2: `scoring_skill`

| Attribute | Value |
|-----------|-------|
| **Step** | 2 |
| **Responsibility** | Load graph, compute 5-axis pattern affinity scores, select winning pattern |
| **Input** | Validated `IntakeAnswers` |
| **Output** | `PatternSelection` (scores, selected pattern, confidence) |
| **MCP Dependencies** | None |
| **LLM Usage** | None — purely deterministic graph traversal |
| **Panel Emitted** | `radar_chart` |
| **Deterministic Logic** | Weighted scoring algorithm (§ Decision Engine Spec) |
| **Confirmation Required** | Yes — pause after showing radar, ask "Does this pattern look right?" |

**Scoring Algorithm (Deterministic):**

```python
def _compute_scores(self, graph: Graph, answers: IntakeAnswers) -> dict:
    patterns = graph.get_nodes_by_type("Pattern")
    scores = {p.name: 0.0 for p in patterns}
    axis_scores = {p.name: [0.0]*5 for p in patterns}  # 5 axes
    
    for question_id, answer_value in answers.items():
        # Find constraint node matching this answer
        constraint = graph.find_constraint(question_id, answer_value)
        if not constraint:
            continue
        
        # Traverse PRESSURES_TOWARD edges
        for edge in graph.get_edges(constraint.id, "PRESSURES_TOWARD"):
            target_pattern = edge.target
            scores[target_pattern] += edge.weight * constraint.signal_weight
            axis_scores[target_pattern][edge.axis_index] += edge.weight
        
        # Traverse PRESSURES_AGAINST edges
        for edge in graph.get_edges(constraint.id, "PRESSURES_AGAINST"):
            target_pattern = edge.target
            scores[target_pattern] -= edge.weight * constraint.signal_weight
    
    return {"scores": scores, "axis_scores": axis_scores}
```

#### Skill 3: `component_skill`

| Attribute | Value |
|-----------|-------|
| **Step** | 3 |
| **Responsibility** | Determine fabric components + base tiers, apply constraint elevations + industry forces |
| **Input** | Selected pattern + `IntakeAnswers` + industry |
| **Output** | `ComponentList` with final tiers and elevation reasons |
| **MCP Dependencies** | None |
| **LLM Usage** | None — deterministic graph traversal |
| **Panel Emitted** | `architecture_diagram` |
| **Confirmation Required** | Yes — "Does this architecture look right?" |

#### Skill 4: `innovation_skill`

| Attribute | Value |
|-----------|-------|
| **Step** | 4 |
| **Responsibility** | Match user pain points → innovations, validate GA status via MCP |
| **Input** | Pain points + component list |
| **Output** | `InnovationOverlay` (applied innovations, modified architecture) |
| **MCP Dependencies** | AWS Documentation MCP (validate GA status) |
| **LLM Usage** | Pain point → innovation matching (semantic, LLM-assisted) |
| **Panel Emitted** | `innovation_overlay` |

#### Skill 5: `service_mapping_skill`

| Attribute | Value |
|-----------|-------|
| **Step** | 5 |
| **Responsibility** | Map components at their tiers → specific AWS services, fetch workshops |
| **Input** | Final component list with tiers |
| **Output** | `ServiceMap` (component → AWS service mapping + workshop links) |
| **MCP Dependencies** | AWS Documentation MCP, AWS Knowledge MCP |
| **LLM Usage** | Workshop relevance ranking |
| **Panel Emitted** | `service_map` |

#### Skill 6: `compliance_skill` (merged with antipattern_skill in rendering)

| Attribute | Value |
|-----------|-------|
| **Step** | 5.5 (sub-step, runs between 5 and 6 in pipeline) |
| **Responsibility** | Apply industry compliance overlays, force minimum tiers |
| **Input** | Industry + component list |
| **Output** | Modified component list (tier forces applied) |
| **MCP Dependencies** | None |
| **LLM Usage** | None |
| **Panel Emitted** | Updates to `architecture_diagram` (tier changes) |

#### Skill 7: `antipattern_skill`

| Attribute | Value |
|-----------|-------|
| **Step** | 6 |
| **Responsibility** | Check triggered anti-patterns, determine prevention status |
| **Input** | Selected pattern + constraints + component tiers |
| **Output** | `RiskAssessment` (triggered anti-patterns + prevention status) |
| **MCP Dependencies** | None |
| **LLM Usage** | None — deterministic graph check |
| **Panel Emitted** | `risk_cards` |

#### Skill 8: `phasing_skill`

| Attribute | Value |
|-----------|-------|
| **Step** | 7 |
| **Responsibility** | Compute build sequence from component dependencies |
| **Input** | Component list + dependency graph |
| **Output** | `PhasedRoadmap` (P0/P1/P2/P3 with ordering) |
| **MCP Dependencies** | None |
| **LLM Usage** | None — topological sort + priority rules |
| **Panel Emitted** | `timeline` |

#### Skill 9: `blueprint_skill`

| Attribute | Value |
|-----------|-------|
| **Step** | 8 |
| **Responsibility** | Assemble all outputs into final blueprint, generate executive visual |
| **Input** | All prior skill outputs |
| **Output** | `Blueprint` (composite of all steps) |
| **MCP Dependencies** | Diagram Generation MCP (SVG rendering) |
| **LLM Usage** | Executive summary generation (2-3 sentences) |
| **Panel Emitted** | `blueprint` |

#### Skill 10: `research_skill` (Background)

| Attribute | Value |
|-----------|-------|
| **Step** | Parallel (runs during Steps 4-7) |
| **Responsibility** | Background research on latest innovations, competitive landscape |
| **Input** | User's industry + pain points + selected pattern |
| **Output** | `ResearchContext` (feeds into innovation_skill and blueprint_skill) |
| **MCP Dependencies** | AWS Documentation MCP, AWS Knowledge MCP, Web search |
| **LLM Usage** | Relevance filtering, summarization |
| **Panel Emitted** | None (feeds other skills) |

### Skill Orchestration Flow

```
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐
│ INTAKE  │────▶│ SCORING │────▶│COMPONENT │────▶│INNOVATION│
│ Skill 1 │     │ Skill 2 │     │ Skill 3  │     │ Skill 4  │
└─────────┘     └────┬────┘     └────┬─────┘     └────┬─────┘
                     │               │                  │
               [confirm?]      [confirm?]              │
                                                        ▼
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│BLUEPRINT │◀────│ PHASING  │◀────│ANTIPATTRN│◀────│ SERVICE  │
│ Skill 9  │     │ Skill 8  │     │ Skill 7  │     │ Skill 5  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                                        ▲
                                                        │
                                              ┌──────────────┐
                                              │  COMPLIANCE  │
                                              │  Skill 6     │
                                              └──────────────┘

         ┌──────────────────────────────────────────────┐
         │         RESEARCH (parallel background)        │
         │         Skill 10 — feeds Skills 4, 5, 9       │
         └──────────────────────────────────────────────┘
```

### Agent Configuration (Strands)

```python
# agent_config.py
from strands import Agent, AgentConfig
from skills import (
    IntakeSkill, ScoringSkill, ComponentSkill, InnovationSkill,
    ServiceMappingSkill, ComplianceSkill, AntipatternSkill,
    PhasingSkill, BlueprintSkill, ResearchSkill
)

agent = Agent(
    config=AgentConfig(
        name="platform-advisor",
        model="us.anthropic.claude-sonnet-4-20250514",
        system_prompt=load_system_prompt(),  # from DynamoDB CONFIG#SYSTEM
        skills=[
            IntakeSkill(),
            ScoringSkill(),
            ComponentSkill(),
            InnovationSkill(),
            ServiceMappingSkill(),
            ComplianceSkill(),
            AntipatternSkill(),
            PhasingSkill(),
            BlueprintSkill(),
            ResearchSkill(),
        ],
        mcp_servers=[
            "aws-documentation-mcp",
            "aws-knowledge-mcp",
            "aws-highspot-mcp",
            "diagram-generation-mcp",
        ],
        memory_type="session",  # per-session memory
        streaming=True,
    )
)
```

---

## 9. MCP Integration Plan

### MCP Server Inventory

| Server | Purpose | Endpoints Used | When Called |
|--------|---------|---------------|------------|
| **AWS Documentation MCP** | Validate services are GA, get features | `aws_search_documentation`, `aws_read_documentation`, `aws_get_regional_availability` | Steps 4, 5 |
| **AWS Knowledge MCP** | Fetch workshops, prescriptive guidance, blogs | `aws_search_documentation`, `aws_recommend` | Steps 5, 8 |
| **AWS Highspot MCP** | Sales positioning, competitive context | `highspot_search`, `get_instant_answer` | Step 10 (research) |
| **Diagram Generation MCP** | Render exec-quality SVG diagrams | `render_architecture`, `render_timeline` | Steps 3, 7, 8 |

### Diagram Generation MCP (Proposed — Custom Build)

This is a **new MCP server** we need to build to generate executive-ready visuals:

**Capabilities:**

```typescript
// MCP Tool: render_architecture
interface RenderArchitectureInput {
  layers: Layer[];           // from component_skill output
  pattern: string;
  innovations: Innovation[];
  style: 'dark' | 'light';
  format: 'svg' | 'png';
  size: 'compact' | 'full';
}

// MCP Tool: render_timeline
interface RenderTimelineInput {
  phases: Phase[];
  dependencies: Dependency[];
  style: 'dark' | 'light';
  format: 'svg' | 'png';
}

// MCP Tool: render_radar
interface RenderRadarInput {
  axes: string[];
  datasets: Dataset[];
  selected: string;
  style: 'dark' | 'light';
  format: 'svg' | 'png';
}
```

**Implementation Options:**

| Option | Technology | Pros | Cons |
|--------|-----------|------|------|
| **A: D3.js + JSDOM** | Node.js server-side D3 rendering | Full control, beautiful SVGs | Build from scratch |
| **B: Mermaid CLI** | Mermaid diagram rendering | Quick, standard syntax | Limited styling control |
| **C: Excalidraw backend** | Programmatic Excalidraw | Hand-drawn aesthetic option | Less "executive" |
| **D: React PDF/SVG** | Server-side React rendering | Same components as frontend | Complex setup |

**Recommendation:** Option A (D3.js + JSDOM) deployed as a Lambda function exposed via MCP protocol. This gives full control over the executive aesthetic while remaining stateless and scalable.

### MCP Error Handling

```python
class MCPFallbackStrategy:
    """If MCP fails, degrade gracefully — never block the pipeline."""
    
    async def call_with_fallback(self, server: str, tool: str, input: dict):
        try:
            result = await self.mcp_client.call(server, tool, input, timeout=10)
            return MCPResult(data=result, source="live", verified=True)
        except MCPTimeoutError:
            # Use cached version if available
            cached = self.cache.get(f"{server}:{tool}:{hash(input)}")
            if cached:
                return MCPResult(data=cached, source="cache", verified=False)
            # Fall back to KB-only (no live validation)
            return MCPResult(data=None, source="none", verified=False)
        except MCPConnectionError:
            self.emit_event({"type": "error", "message": f"{server} unavailable", "recoverable": True})
            return MCPResult(data=None, source="none", verified=False)
```

### MCP Caching Strategy

| Data Type | Cache Duration | Storage |
|-----------|---------------|---------|
| Service availability (GA/Preview) | 24 hours | DynamoDB TTL |
| Workshop listings | 7 days | DynamoDB TTL |
| Documentation pages | 1 hour | In-memory (agent session) |
| Highspot content | 24 hours | DynamoDB TTL |
| Diagram renders | Session lifetime | S3 |

---

## 10. Streaming / A2UI Protocol

### Protocol Overview

The **Agent-to-UI (A2UI)** protocol defines how the Strands agent sends structured data to the Next.js frontend. The agent NEVER sends pre-rendered HTML — it sends typed data payloads that the frontend renders with its own React components.

### Event Types

```typescript
// Core event interface
interface BaseEvent {
  event_id: string;           // UUID for deduplication
  timestamp: string;          // ISO 8601
  session_id: string;
}

// Panel lifecycle events
interface PanelUpdateEvent extends BaseEvent {
  type: 'panel_update';
  step: number;               // 1-8
  panel_type: PanelType;
  data: PanelData;            // typed per panel_type
  streaming: true;            // more data coming
  progress: number;           // 0.0-1.0 within this panel
}

interface PanelCompleteEvent extends BaseEvent {
  type: 'panel_complete';
  step: number;
  panel_type: PanelType;
  data: PanelData;
  streaming: false;
}

// Incremental data events (for panels that build up)
interface CardAddEvent extends BaseEvent {
  type: 'card_add';
  step: number;
  panel_type: PanelType;
  card_id: string;
  card_data: any;             // single card to append
  position: number;           // index in list
}

interface CardUpdateEvent extends BaseEvent {
  type: 'card_update';
  step: number;
  panel_type: PanelType;
  card_id: string;
  updates: Partial<any>;      // fields to merge
}

// Chat events
interface ChatMessageEvent extends BaseEvent {
  type: 'chat_message';
  role: 'assistant';
  content: string;
  step: number;
}

interface ChatStreamEvent extends BaseEvent {
  type: 'chat_stream';
  role: 'assistant';
  delta: string;              // token-by-token streaming
  step: number;
}

// Flow control events
interface StepTransitionEvent extends BaseEvent {
  type: 'step_transition';
  from_step: number;
  to_step: number;
  status: 'auto' | 'awaiting_confirmation' | 'error';
}

interface ConfirmationRequestEvent extends BaseEvent {
  type: 'confirmation_request';
  step: number;
  question: string;           // "Does this pattern look right?"
  options: string[];          // ["Yes, continue", "No, let me adjust"]
}

interface ErrorEvent extends BaseEvent {
  type: 'error';
  step: number;
  message: string;
  recoverable: boolean;
  suggestion: string;
}

// Panel types
type PanelType = 
  | 'intake_form'
  | 'radar_chart'
  | 'architecture_diagram'
  | 'innovation_overlay'
  | 'service_map'
  | 'risk_cards'
  | 'timeline'
  | 'blueprint';
```

### Frontend Event Handler

```typescript
// hooks/useAgentStream.ts
export function useAgentStream(sessionId: string) {
  const [currentStep, setCurrentStep] = useState(1);
  const [panelData, setPanelData] = useState<Record<number, PanelData>>({});
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);

  const startStream = useCallback(async () => {
    const eventSource = new EventSource(
      `/api/v1/customers/${customerId}/sessions/${sessionId}/run`,
      { headers: { Authorization: `Bearer ${token}` } }
    );

    eventSource.addEventListener('panel_update', (e) => {
      const event: PanelUpdateEvent = JSON.parse(e.data);
      setPanelData(prev => ({ ...prev, [event.step]: event.data }));
      setCurrentStep(event.step);
      setIsStreaming(true);
    });

    eventSource.addEventListener('panel_complete', (e) => {
      const event: PanelCompleteEvent = JSON.parse(e.data);
      setPanelData(prev => ({ ...prev, [event.step]: event.data }));
      setIsStreaming(false);
    });

    eventSource.addEventListener('step_transition', (e) => {
      const event: StepTransitionEvent = JSON.parse(e.data);
      setCurrentStep(event.to_step);
      if (event.status === 'awaiting_confirmation') {
        setAwaitingConfirmation(true);
      }
    });

    eventSource.addEventListener('chat_stream', (e) => {
      const event: ChatStreamEvent = JSON.parse(e.data);
      // Append delta to current assistant message
      setChatMessages(prev => appendDelta(prev, event.delta));
    });

    eventSource.addEventListener('error', (e) => {
      // Handle reconnection logic
    });
  }, [sessionId]);

  return { currentStep, panelData, chatMessages, isStreaming, awaitingConfirmation, startStream };
}
```

### Streaming Patterns per Step

| Step | Streaming Behavior | Why |
|------|-------------------|-----|
| 1 (Intake) | `panel_update` as each answer is received | Show progress toward completeness |
| 2 (Scoring) | Single `panel_complete` (fast computation) | Scoring is instant, no need to stream |
| 3 (Architecture) | `card_add` per component, then `panel_complete` | Build diagram piece by piece |
| 4 (Innovation) | `card_add` per innovation found | Each MCP validation takes time |
| 5 (Services) | `card_update` per component (adding service info) | MCP calls are sequential |
| 6 (Risks) | `card_add` per anti-pattern checked | Quick, but visualize each check |
| 7 (Phasing) | Single `panel_complete` | Topological sort is instant |
| 8 (Blueprint) | `panel_update` with progress (assembling sections) | Diagram generation takes time |

### Reconnection & Replay

If the SSE connection drops:
1. Client reconnects with `Last-Event-ID` header
2. Server replays events from that ID forward (events cached in session)
3. If session is fully computed, serve cached panel states from DynamoDB (instant replay)

---

## 11. Admin Panel Design

### `/admin/dashboard` — Usage Analytics

```
┌─────────────────────────────────────────────────────────────────────┐
│  Admin Dashboard                                    Last 30 days ▾  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │    12    │  │    34    │  │    28    │  │   89%    │          │
│  │Customers │  │ Sessions │  │Blueprints│  │Completion│          │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘          │
│                                                                     │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐  │
│  │  Pattern Distribution (Pie) │  │  Sessions per Week (Line)   │  │
│  │                             │  │                             │  │
│  │   Federated: 45%           │  │   ╱╲    ╱╲                  │  │
│  │   Centralized: 30%        │  │  ╱  ╲╱╱  ╲                 │  │
│  │   Mesh: 15%               │  │ ╱          ╲╱╲              │  │
│  │   Hybrid: 10%             │  │                              │  │
│  └─────────────────────────────┘  └─────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐  │
│  │  Top Constraints (Bar)      │  │  Innovation Hit Rate         │  │
│  │                             │  │                             │  │
│  │  Multi-cloud ████████ 67%  │  │  Intelligent Routing: 12x   │  │
│  │  10+ LOBs   ███████  58%  │  │  Programmatic TC: 9x        │  │
│  │  Cost #1    ██████   42%  │  │  A2A Protocol: 7x           │  │
│  │  Low expert █████    38%  │  │  Dynamic Tools: 5x          │  │
│  └─────────────────────────────┘  └─────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Recent Sessions (Table)                                       │  │
│  │  Customer    │ User     │ Pattern    │ Step │ Date            │  │
│  │  Acme Corp  │ aigopala │ Federated  │ 8/8  │ Jul 22          │  │
│  │  BigBank    │ thandavm │ Mesh       │ 5/8  │ Jul 21          │  │
│  │  HealthCo   │ janedoe  │ Centralized│ 3/8  │ Jul 20          │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**Dashboard Metrics (DynamoDB Queries):**

| Metric | Query | Aggregation |
|--------|-------|-------------|
| Total customers | GSI2 where entity_type=Customer, count | Count |
| Total sessions | GSI2 where entity_type=Session, count | Count |
| Completed blueprints | Sessions where status=complete | Count |
| Completion rate | Completed / Total sessions | Percentage |
| Pattern distribution | Sessions where pattern_selected != null, group by pattern | Pie chart |
| Top constraints | Aggregate IntakeAnswers across sessions | Bar chart |
| Innovation hit rate | Count innovation applications across sessions | Ranked list |
| Sessions per week | Sessions grouped by created_at week | Time series |

### `/admin/config` — Configuration Panel

#### Tabs:

**1. System Prompt Editor**

```
┌─────────────────────────────────────────────────────────────────────┐
│  System Prompt Editor                     Version: 7 │ Published ✓  │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  [Monaco Editor with Markdown syntax highlighting]             │  │
│  │                                                               │  │
│  │  # Platform Advisor — System Prompt                           │  │
│  │  ## IDENTITY                                                  │  │
│  │  You are the **Agentic Platform Advisor**...                  │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  [Save as Draft]  [Publish v8]  │  History: v7 v6 v5 v4 [Compare] │
└─────────────────────────────────────────────────────────────────────┘
```

- Monaco editor with Markdown highlighting
- Version history (stored in DynamoDB)
- Diff view between versions
- "Publish" creates new version, immediately active for new sessions
- "Save as Draft" stores without activating

**2. Graph Schema Editor**

```
┌─────────────────────────────────────────────────────────────────────┐
│  Graph Editor                      Nodes: 147 │ Edges: 583 │ v3    │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌─────────────────────────────────────────────────┐  │
│  │ Node     │  │  [Interactive Graph Visualization]               │  │
│  │ Types:   │  │                                                 │  │
│  │          │  │  • Nodes as circles (colored by type)           │  │
│  │ Constrt  │  │  • Edges as lines (colored by relationship)    │  │
│  │ Pattern  │  │  • Click to select, inspect, edit              │  │
│  │ Compnt   │  │  • Drag to reposition                          │  │
│  │ Innovtn  │  │                                                 │  │
│  │ Law      │  │  [D3 force-directed graph]                     │  │
│  │ AntiPat  │  │                                                 │  │
│  └──────────┘  └─────────────────────────────────────────────────┘  │
│                                                                     │
│  Selected: [Constraint: "10+ LOBs"]                                 │
│  Properties: signal_id=5, weight=0.11                              │
│  Edges out: PRESSURES_TOWARD → Federated (0.9)                    │
│             PRESSURES_TOWARD → Mesh (0.7)                         │
│             PRESSURES_AGAINST → Centralized (0.8)                 │
│                                                                     │
│  [Add Node]  [Add Edge]  [Edit Weight]  [Delete]  [Publish v4]    │
└─────────────────────────────────────────────────────────────────────┘
```

- D3 force-directed graph visualization
- Node filter by type (checkboxes)
- Click node → inspect properties + connected edges
- Edit edge weights inline (slider 0.0–1.0)
- Add new nodes/edges via form
- Publish creates new graph version (old sessions keep their version)

**3. Skill Manager**

```
┌─────────────────────────────────────────────────────────────────────┐
│  Skills                                                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐            │
│  │  intake_skill       │ Step 1 │ ✅ Enabled │ [Edit] │            │
│  │  scoring_skill      │ Step 2 │ ✅ Enabled │ [Edit] │            │
│  │  component_skill    │ Step 3 │ ✅ Enabled │ [Edit] │            │
│  │  innovation_skill   │ Step 4 │ ✅ Enabled │ [Edit] │            │
│  │  service_mapping    │ Step 5 │ ✅ Enabled │ [Edit] │            │
│  │  compliance_skill   │ Step 5.5│ ✅ Enabled │ [Edit] │            │
│  │  antipattern_skill  │ Step 6 │ ✅ Enabled │ [Edit] │            │
│  │  phasing_skill      │ Step 7 │ ✅ Enabled │ [Edit] │            │
│  │  blueprint_skill    │ Step 8 │ ✅ Enabled │ [Edit] │            │
│  │  research_skill     │ BG     │ ⚠️ Disabled│ [Edit] │            │
│  └─────────────────────────────────────────────────────┘            │
│                                                                     │
│  Disabled skills are skipped in the pipeline.                       │
│  Edit → configure skill-specific parameters (e.g., MCP timeout).   │
└─────────────────────────────────────────────────────────────────────┘
```

**4. MCP Connection Status**

```
┌─────────────────────────────────────────────────────────────────────┐
│  MCP Servers                                    [Refresh All]       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  AWS Documentation MCP    │ 🟢 Connected │ Latency: 120ms │ [Test]│
│  AWS Knowledge MCP        │ 🟢 Connected │ Latency: 89ms  │ [Test]│
│  AWS Highspot MCP         │ 🟡 Degraded  │ Latency: 2100ms│ [Test]│
│  Diagram Generation MCP   │ 🔴 Down      │ Last: 10min ago│ [Test]│
│                                                                     │
│  [Test] sends a sample query and shows response time + result.      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 12. Deployment Architecture

### AWS Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              AWS CLOUD                                    │
│                                                                         │
│  ┌──────────────────────────────────┐                                   │
│  │         AMPLIFY HOSTING          │                                   │
│  │   (Next.js 15 SSR + Static)      │  ◄── CloudFront CDN              │
│  └──────────────┬───────────────────┘                                   │
│                 │                                                        │
│                 │ HTTPS                                                  │
│                 ▼                                                        │
│  ┌──────────────────────────────────┐     ┌────────────────────────┐   │
│  │       API GATEWAY (HTTP API)      │────▶│   COGNITO USER POOL    │   │
│  │   /v1/* routes                    │     │   + Identity Pool      │   │
│  │   JWT Authorizer                  │     │   + Amazon SSO SAML    │   │
│  └──────────────┬───────────────────┘     └────────────────────────┘   │
│                 │                                                        │
│       ┌─────────┴──────────┐                                            │
│       │                    │                                            │
│       ▼                    ▼                                            │
│  ┌─────────────┐    ┌─────────────────────────────────┐                │
│  │  LAMBDA     │    │     AGENTCORE RUNTIME            │                │
│  │  (API       │    │                                  │                │
│  │   Handlers) │───▶│  Strands SDK Agent               │                │
│  │             │    │  ┌─────┐┌─────┐┌─────┐┌─────┐  │                │
│  │  • CRUD ops │    │  │Sk 1 ││Sk 2 ││Sk 3 ││...  │  │                │
│  │  • Auth     │    │  └─────┘└─────┘└─────┘└─────┘  │                │
│  │  • Export   │    │                                  │                │
│  └─────────────┘    │  MCP Client                      │                │
│                     └──────────┬──────────────────────┘                │
│                                │                                        │
│              ┌─────────────────┼─────────────────────┐                  │
│              │                 │                     │                  │
│              ▼                 ▼                     ▼                  │
│  ┌───────────────┐  ┌────────────────┐  ┌────────────────────────┐    │
│  │   DYNAMODB    │  │      S3        │  │    MCP SERVERS          │    │
│  │               │  │                │  │                        │    │
│  │ • Customers   │  │ • Diagrams     │  │ • AWS Docs MCP         │    │
│  │ • Sessions    │  │ • PDF exports  │  │ • AWS Knowledge MCP    │    │
│  │ • Graph data  │  │ • Graph snaps  │  │ • AWS Highspot MCP     │    │
│  │ • Configs     │  │ • Assets       │  │ • Diagram Gen MCP      │    │
│  │ • Metrics     │  │                │  │   (Lambda + D3)        │    │
│  └───────────────┘  └────────────────┘  └────────────────────────┘    │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    OBSERVABILITY                                   │  │
│  │  CloudWatch Logs │ X-Ray Traces │ CloudWatch Metrics │ Alarms    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Environment Configuration

| Environment | Frontend URL | API URL | DynamoDB Table | Purpose |
|-------------|-------------|---------|----------------|---------|
| `dev` | localhost:3000 | localhost:8000 | `pa-dev` | Local development |
| `staging` | staging.platform-advisor.aws.dev | api-staging... | `pa-staging` | Integration testing |
| `prod` | platform-advisor.aws.dev | api.platform-advisor... | `pa-prod` | Production |

### CI/CD Pipeline

```yaml
# pipeline.yml
stages:
  - name: Source
    action: CodeCommit / GitHub push to main
    
  - name: Build-Frontend
    action: CodeBuild
    commands:
      - npm ci
      - npm run lint
      - npm run type-check
      - npm run build
      - npm run test
    artifacts: .next/

  - name: Build-Backend
    action: CodeBuild
    commands:
      - pip install -r requirements.txt
      - pytest tests/
      - python -m mypy skills/
      - sam build
    artifacts: .aws-sam/

  - name: Deploy-Staging
    action: 
      - Amplify Deploy (frontend)
      - SAM Deploy (Lambda + API Gateway)
      - AgentCore Deploy (agent)
    
  - name: Integration-Tests
    action: CodeBuild
    commands:
      - pytest tests/integration/ --env=staging

  - name: Deploy-Production
    action: Same as staging, prod config
    approval: Manual gate (admin only)
```

### Scaling Characteristics

| Component | Scaling Model | Limits |
|-----------|--------------|--------|
| Amplify (Frontend) | Auto (CloudFront + managed) | Effectively unlimited |
| API Gateway | Auto (per-request) | 10,000 req/s default |
| Lambda (API handlers) | Auto (concurrent) | 1000 concurrent (adjustable) |
| AgentCore Runtime | Managed (session-based) | Per-account agent limits |
| DynamoDB | On-demand (auto) | 40K RCU / 40K WCU burst |
| S3 | Unlimited | — |

### Security Posture

| Layer | Control |
|-------|---------|
| Network | API Gateway → Lambda in VPC (optional), private subnets for DynamoDB access |
| Auth | Cognito JWT validation at API Gateway (authorizer) |
| Data at rest | DynamoDB encryption (AWS-managed key), S3 SSE-S3 |
| Data in transit | TLS 1.3 everywhere |
| Secrets | Secrets Manager for MCP keys, Cognito secrets |
| Audit | CloudTrail for all API calls, DynamoDB Streams for data changes |
| RBAC | Cognito groups → API Gateway authorizer → Lambda enforcement |

---

## 13. Implementation Phases

### Phase 0: Foundation (Weeks 1-2)

**Goal:** Skeleton app with auth, routing, and basic infrastructure.

| Task | Deliverable | Owner |
|------|------------|-------|
| Setup Next.js 15 project with TypeScript + Tailwind | `/app` directory with layout, dark theme | Frontend |
| Setup Cognito User Pool + Amazon SSO SAML | Login flow working, groups configured | Backend |
| Setup DynamoDB table with single-table schema | Table created, seed data scripts | Backend |
| Setup API Gateway + Lambda scaffold | CRUD endpoints for customers/sessions | Backend |
| Setup Amplify Hosting | Staging deployment working | DevOps |
| Design system implementation | CSS variables, component library (buttons, cards, inputs) | Frontend |

**Exit criteria:** User can log in, see empty customer list, create a customer.

---

### Phase 1: Core Pipeline — Steps 1-3 (Weeks 3-5)

**Goal:** Intake → Scoring → Architecture working end-to-end with streaming.

| Task | Deliverable | Owner |
|------|------------|-------|
| Implement `intake_skill` | Collects 12 answers, validates, emits panel events | Backend |
| Implement `scoring_skill` | Graph traversal, pattern scoring, deterministic | Backend |
| Implement `component_skill` | Component selection, tier elevation | Backend |
| Load graph.json into DynamoDB | Graph storage + in-memory loader | Backend |
| Build `IntakeForm` React component | Interactive card-based form | Frontend |
| Build `RadarChart` React component | Highcharts polar chart with overlays | Frontend |
| Build `ArchitectureDiagram` React component | SVG layered architecture | Frontend |
| Implement SSE streaming endpoint | `/run` endpoint with event emission | Backend |
| Implement `useAgentStream` hook | Event handling, panel state management | Frontend |
| Build session page layout (chat + visual panel) | Split-panel with step indicator | Frontend |
| Deploy Strands agent to AgentCore | Agent running, reachable from Lambda | Backend |

**Exit criteria:** User answers intake, sees radar chart score, sees architecture diagram. All streaming.

---

### Phase 2: Complete Pipeline — Steps 4-8 (Weeks 6-8)

**Goal:** Full 8-step pipeline with all visual panels.

| Task | Deliverable | Owner |
|------|------------|-------|
| Implement `innovation_skill` | Pain point matching, MCP validation | Backend |
| Implement `service_mapping_skill` | Component → AWS service mapping | Backend |
| Implement `antipattern_skill` | Risk detection, prevention check | Backend |
| Implement `phasing_skill` | Dependency sort, phase assignment | Backend |
| Implement `blueprint_skill` | Assembly, executive summary | Backend |
| Wire AWS Documentation MCP | Live service validation | Backend |
| Wire AWS Knowledge MCP | Workshop fetching | Backend |
| Build `InnovationOverlay` component | Before/after split view | Frontend |
| Build `ServiceMap` component | Architecture + service badges | Frontend |
| Build `RiskCards` component | Warning/success cards | Frontend |
| Build `PhaseTimeline` component | Gantt-style horizontal timeline | Frontend |
| Build `BlueprintAssembly` component | Dashboard composite view | Frontend |
| Implement session persistence | Panels cached, session resumable | Backend |
| Implement "what-if" re-run | Change input → re-run from affected step | Backend |

**Exit criteria:** Full pipeline works end-to-end. User gets complete blueprint.

---

### Phase 3: Admin Panel + Polish (Weeks 9-10)

**Goal:** Admin dashboard, configuration panel, export.

| Task | Deliverable | Owner |
|------|------------|-------|
| Build admin dashboard | Metrics, charts, recent sessions | Frontend |
| Build system prompt editor | Monaco editor, versioning | Frontend |
| Build graph schema editor (read-only MVP) | JSON viewer, node inspector | Frontend |
| Build skill manager | Enable/disable toggles | Frontend |
| Build MCP health panel | Connection status, latency | Frontend |
| Implement admin API endpoints | Dashboard metrics, config CRUD | Backend |
| Implement PDF export | Generate PDF from blueprint data | Backend |
| Implement admin "switch to user view" | Query param toggle | Frontend |
| Implement session replay | Load cached panels for completed sessions | Frontend |
| Highspot MCP integration | Competitive context in research | Backend |

**Exit criteria:** Admins can view all data, edit prompts/graph, export blueprints.

---

### Phase 4: Production Hardening (Weeks 11-12)

**Goal:** Production-ready with monitoring, error handling, performance.

| Task | Deliverable | Owner |
|------|------------|-------|
| Error handling + graceful degradation | MCP failures don't block pipeline | Backend |
| Rate limiting + abuse prevention | API Gateway throttling config | DevOps |
| CloudWatch dashboards + alarms | Latency P99, error rate, agent failures | DevOps |
| X-Ray tracing for agent pipeline | Per-skill latency visibility | Backend |
| Load testing (50 concurrent sessions) | Performance baseline | QA |
| Security review | IAM permissions, data access patterns | Security |
| Accessibility audit | WCAG AA for frontend | Frontend |
| Documentation | API docs (OpenAPI), deployment runbook | All |
| Graph editor (full edit capability) | Add/edit/delete nodes and edges | Frontend |
| Diagram Generation MCP (custom build) | D3 server-side SVG rendering | Backend |

**Exit criteria:** Production deployment, monitoring active, <3s P99 panel render time.

---

### Phase 5: Iterate + Scale (Weeks 13+)

- User feedback incorporation
- Additional patterns (Economy, Hybrid)
- Graph weight calibration from real engagements
- PPTX export
- Multi-user collaboration on sessions
- Scheduled research_skill (background auto-update)
- Neptune migration (if graph exceeds 1000 nodes)

---

## 14. Agent Intelligence — Memory Architecture

### Overview

The agent uses **AgentCore Memory** (short-term + long-term) combined with **graph feedback** (collective learning) to deliver progressively smarter recommendations across sessions and customers.

```
┌──────────────────────────────────────────────────────────────────┐
│                    AGENT INTELLIGENCE LAYERS                       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  LAYER 1: SHORT-TERM (AgentCore Session Memory)           │     │
│  │  Scope: Single session | Lifetime: Session duration       │     │
│  │  Contents: Conversation state, intake answers so far,     │     │
│  │            pipeline step, intermediate outputs (scores)   │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  LAYER 2: LONG-TERM (AgentCore Persistent Memory)         │     │
│  │  Scope: Per customer | Lifetime: Indefinite               │     │
│  │  Contents: Previous blueprints, confirmed decisions,      │     │
│  │            pain points, follow-ups, constraint history    │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  LAYER 3: COLLECTIVE (Graph Feedback Loop)                │     │
│  │  Scope: Cross-customer | Lifetime: Permanent              │     │
│  │  Contents: Edge weight calibrations, pattern success      │     │
│  │            rates, common anti-patterns, new constraints   │     │
│  │  Access: Admin-only (review + approve)                    │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 14.1 Layer 1: Short-Term Memory (Session-Scoped)

**Purpose:** Track conversation state within a single session so the agent never "forgets" what the user said earlier.

**AgentCore Implementation:**

```python
from agentcore import Memory

class SessionMemory:
    def __init__(self, session_id: str):
        self.memory = Memory(scope="session", session_id=session_id)
    
    def store_intake(self, answers: dict):
        """Store intake answers as they're collected (partial OK)"""
        self.memory.store("intake_answers", answers)
    
    def store_pipeline_state(self, step: int, outputs: dict):
        """Track which step we're on + intermediate results"""
        self.memory.store("pipeline_state", {
            "current_step": step,
            "pattern_selected": outputs.get("pattern"),
            "components": outputs.get("components"),
            "innovations_applied": outputs.get("innovations"),
        })
    
    def recall_state(self) -> dict:
        """Recall full session state (for resumption after disconnect)"""
        return {
            "answers": self.memory.recall("intake_answers"),
            "pipeline": self.memory.recall("pipeline_state"),
        }
```

**What this enables:**
- User changes one answer mid-session → agent re-runs from that step, not from scratch
- User disconnects and reconnects → session resumes at exact state
- Agent references earlier answers without re-asking

---

### 14.2 Layer 2: Long-Term Memory (Customer-Scoped)

**Purpose:** Remember everything about a customer across sessions — blueprints generated, decisions confirmed/rejected, follow-ups, and context.

**AgentCore Implementation:**

```python
class CustomerMemory:
    def __init__(self, customer_id: str):
        self.memory = Memory(scope="persistent", namespace=f"customer:{customer_id}")
    
    def on_session_end(self, session_output: dict):
        """Persist learnings after a session completes"""
        self.memory.store("latest_blueprint", session_output["blueprint"])
        self.memory.store("intake_answers", session_output["answers"])
        self.memory.store("decisions_confirmed", session_output["confirmations"])
        self.memory.store("follow_ups", session_output.get("follow_ups", []))
        
        # Append to session history (not overwrite)
        history = self.memory.recall("session_history") or []
        history.append({
            "session_id": session_output["session_id"],
            "date": session_output["date"],
            "pattern": session_output["pattern"],
            "summary": session_output["summary"],
        })
        self.memory.store("session_history", history)
    
    def on_session_start(self) -> dict:
        """Load customer context at the start of a new session"""
        return {
            "previous_blueprint": self.memory.recall("latest_blueprint"),
            "previous_answers": self.memory.recall("intake_answers"),
            "follow_ups": self.memory.recall("follow_ups"),
            "session_history": self.memory.recall("session_history"),
        }
```

**What this enables:**
- "Welcome back" experience — agent knows their last blueprint, constraints, and follow-ups
- Detects what changed since last session (new AWS launches relevant to their pattern)
- Multiple team members from the same customer share context
- Agent can say "Last time you rejected Mesh because of expertise. Has that changed?"

**New Skill: `context_recall_skill`** (runs at session start):

```python
@skill(name="context_recall")
async def recall_customer_context(customer_id: str) -> PanelEvent:
    """Load customer history and surface relevant context"""
    mem = CustomerMemory(customer_id)
    ctx = mem.on_session_start()
    
    if ctx["previous_blueprint"]:
        # Returning customer — show context card
        return PanelEvent(
            type="panel_update",
            step=0,  # Pre-pipeline step
            panel_type="context_card",
            data={
                "previous_pattern": ctx["previous_blueprint"]["pattern"],
                "last_session_date": ctx["session_history"][-1]["date"],
                "follow_ups": ctx["follow_ups"],
                "options": ["Continue from last blueprint", "Update constraints", "New assessment"]
            }
        )
    else:
        # New customer — go directly to intake
        return None
```

---

### 14.3 Layer 3: Collective Learning (Graph Feedback)

**Purpose:** Improve recommendations over time by learning from outcomes across all customers. This is NOT stored in AgentCore Memory — it feeds back into the graph.

**Implementation:**

```python
class CollectiveLearning:
    def __init__(self, graph_store):
        self.graph = graph_store
    
    def record_outcome(self, session: dict):
        """After a session where user confirmed or rejected a recommendation"""
        recommended = session["pattern_recommended"]
        confirmed = session["pattern_confirmed"]
        
        if recommended == confirmed:
            # Success — log it (no weight change needed)
            self.graph.log_success(session["dominant_constraints"], recommended)
        else:
            # Rejection — propose weight adjustment for admin review
            self.graph.propose_update({
                "type": "weight_adjustment",
                "edge_type": "PRESSURES_TOWARD",
                "from_constraints": session["dominant_constraints"],
                "to_pattern": confirmed,
                "adjustment": "+0.05",
                "reason": f"Customer rejected {recommended}, chose {confirmed}",
                "session_id": session["session_id"],
                "status": "pending_review",  # Admin must approve
            })
    
    def get_pending_adjustments(self) -> list:
        """For admin dashboard — show proposed graph updates"""
        return self.graph.query_proposals(status="pending_review")
```

**Admin Dashboard Integration:**

```
┌─ Graph Learning ────────────────────────────────────────┐
│                                                         │
│  Pattern Acceptance Rate: 83% (25/30 sessions)          │
│                                                         │
│  Pending Weight Adjustments: 3                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Proposal #1                                         ││
│  │ "10+ LOBs + Low Expertise → Federated"              ││
│  │ Rejected 3 times — customers chose Centralized      ││
│  │ Suggested: Reduce federation_pressure 0.9 → 0.75    ││
│  │ [Approve] [Reject] [Modify: ___]                    ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  Recently Approved:                                     │
│  ✓ "Multi-cloud + OSS → increased mesh_pressure"       │
│  ✓ "Added new constraint: 'regulatory sandbox needed'" │
└─────────────────────────────────────────────────────────┘
```

---

### 14.4 DynamoDB Schema Additions for Memory

```typescript
// Add to existing DynamoDB single-table design

// Customer memory entries
interface CustomerMemoryItem {
  PK: `CUSTOMER#${string}`;      // customer_id
  SK: `MEMORY#${string}`;        // memory_key (e.g., "latest_blueprint", "follow_ups")
  value: any;                    // stored JSON
  updated_at: string;            // ISO timestamp
  version: number;               // for optimistic locking
}

// Graph learning proposals
interface GraphProposalItem {
  PK: 'GRAPH_PROPOSAL';
  SK: `PROPOSAL#${string}`;     // proposal_id
  type: 'weight_adjustment' | 'new_node' | 'new_edge';
  details: object;
  status: 'pending_review' | 'approved' | 'rejected';
  created_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
}

// GSI: Proposals by status (for admin dashboard)
// GSI3: PK=status, SK=created_at
```

---

### 14.5 A2UI Events for Memory

New event types for the streaming protocol:

```typescript
// Context loaded at session start (returning customer)
interface ContextLoadedEvent {
  type: 'context_loaded';
  data: {
    is_returning: boolean;
    previous_pattern?: string;
    last_session_date?: string;
    follow_ups?: string[];
    changes_since_last?: string[];  // "AgentCore Payments went GA"
    options: string[];  // Continue / Update / New
  };
}

// Memory update (agent stored something)
interface MemoryStoredEvent {
  type: 'memory_stored';
  data: {
    key: string;
    summary: string;  // "Saved your pattern preference"
  };
}
```

---

### 14.6 Skills Modified for Memory

| Skill | Memory Integration |
|-------|-------------------|
| `context_recall_skill` (NEW) | Loads customer long-term memory at session start |
| `context_persist_skill` (NEW) | Saves session outputs to customer memory at session end |
| `intake_skill` | Reads previous answers from memory, pre-fills if available |
| `scoring_skill` | Checks if customer previously rejected a pattern — adjusts confidence messaging |
| `blueprint_skill` | On completion, triggers `context_persist_skill` + `collective_learning` |

---

### 14.7 User Experience with Memory

**New customer (first session):**
```
Agent: "Let's understand your organization. I'll ask 12 questions..."
→ Full intake flow → blueprint
→ On completion: persist to long-term memory
```

**Returning customer (subsequent session):**
```
Agent: [Shows context card on right panel]
       "Welcome back. Your last session (July 15):
        • Pattern: Federated | 12 LOBs | SOX compliant
        • Follow-up: Evaluate mesh for APAC division
        
        Since then: AgentCore Policy now supports SOX audit templates (GA)
        
        How would you like to proceed?"
        
        [Continue blueprint] [Update constraints] [New assessment]
```

**Same customer, different user:**
```
Agent: "I see you're from [Acme Corp]. Your team has an active blueprint.
        Are you reviewing the existing recommendation, or starting fresh
        for a different division?"
```

---


---

## 15. Open Questions

### Architecture Decisions Needed

| # | Question | Options | Recommendation | Blocking? |
|---|----------|---------|----------------|-----------|
| 1 | **SSE vs WebSocket for streaming** | SSE (simpler, unidirectional) vs WebSocket (bidirectional) | SSE for panel updates (agent→UI); separate POST for user→agent messages | No (SSE sufficient for MVP) |
| 2 | **Graph storage at scale** | DynamoDB (current) vs Neptune Serverless vs Neo4j on ECS | DynamoDB for MVP (graph fits in memory). Neptune at 1000+ nodes. | No |
| 3 | **Diagram Generation MCP implementation** | D3+JSDOM Lambda vs Mermaid CLI vs Puppeteer+React | D3+JSDOM Lambda for full control over executive aesthetic | Yes (needed for Step 8) |
| 4 | **AgentCore session isolation** | One agent instance per session vs shared agent pool | Shared pool with session context injection (AgentCore manages this) | No |
| 5 | **Export format priority** | PDF first vs PPTX first | PDF first (simpler), PPTX in Phase 5 | No |
| 6 | **Multi-tenancy model for future scale** | Single table (current) vs per-customer table vs account separation | Single table with GSI for MVP. Evaluate per-customer isolation at 100+ customers. | No |

### Product Decisions Needed

| # | Question | Context | Impact |
|---|----------|---------|--------|
| 7 | **Confirmation gates** — should Steps 2 and 3 always pause for user confirmation, or auto-advance with "undo"? | Visual prompt says pause; some users may prefer speed | UX flow speed |
| 8 | **Graph editing permissions** — should non-admin users suggest graph changes (that admins approve)? | Useful for SA collaboration | Admin workflow complexity |
| 9 | **Session sharing** — can a user share a session URL with a customer (read-only)? | Useful for post-engagement review | Auth model extension |
| 10 | **Offline mode** — should completed blueprints be viewable without backend? | Useful for travel, demos | Frontend caching complexity |
| 11 | **API access** — should there be a headless API mode (no UI, just JSON in/out)? | Useful for CI/CD integration, batch processing | API design scope |
| 12 | **Knowledge freshness indicator** — should each recommendation show "last verified" date? | Builds trust, shows when MCP data was fetched | UI complexity |

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| AgentCore Runtime cold start latency | Medium | 5-10s first response | Warm pool, show loading state with progress hints |
| MCP server downtime | Low | Degraded innovation validation | Fallback to cached data, mark as "unverified" |
| Graph complexity exceeds DynamoDB efficiency | Low (not for 2+ years) | Query latency | Neptune migration path documented |
| SSE connection drops on mobile/unstable networks | Medium | Lost events | Reconnection + replay from last event ID |
| Strands SDK breaking changes | Low | Backend rebuild | Pin versions, integration tests |
| Highcharts license cost at scale | Low | Budget impact | Evaluate Apache ECharts as alternative |

---

## Appendices

### Appendix A: Full Panel Event Schema (TypeScript)

```typescript
// types/a2ui.ts

export type PanelType =
  | 'intake_form'
  | 'radar_chart'
  | 'architecture_diagram'
  | 'innovation_overlay'
  | 'service_map'
  | 'risk_cards'
  | 'timeline'
  | 'blueprint';

export type EventType =
  | 'panel_update'
  | 'panel_complete'
  | 'card_add'
  | 'card_update'
  | 'chat_message'
  | 'chat_stream'
  | 'step_transition'
  | 'confirmation_request'
  | 'error'
  | 'complete';

export interface PanelEvent {
  event_id: string;
  type: EventType;
  timestamp: string;
  session_id: string;
  step: number;
  panel_type?: PanelType;
  data?: any;
  streaming?: boolean;
  progress?: number;
}

// Panel-specific data types
export interface IntakeFormData {
  questions: IntakeQuestion[];
  answers: Partial<Record<string, string>>;
  missing: string[];
  complete: boolean;
  industry?: string;
  pain_points?: string[];
}

export interface RadarChartData {
  axes: string[];
  patterns: PatternScore[];
  breakdown: ConstraintContribution[];
  selected_pattern: string;
  confidence: number;
  hybrid_recommended: boolean;
}

export interface ArchitectureDiagramData {
  pattern: string;
  layers: ArchLayer[];
  elevations: TierElevation[];
  total_components: number;
}

export interface InnovationOverlayData {
  innovations: InnovationEntry[];
  architecture_before: ArchitectureDiagramData;
  architecture_after: ArchitectureDiagramData;
  total_modifications: number;
}

export interface ServiceMapData {
  components: ServiceMappedComponent[];
  workshops: WorkshopLink[];
  total_services: number;
}

export interface RiskCardsData {
  summary: RiskSummary;
  risks: RiskEntry[];
}

export interface TimelineData {
  phases: PhaseEntry[];
  dependencies: DependencyEntry[];
  total_duration_months: number;
}

export interface BlueprintData {
  executive_summary: ExecutiveSummary;
  architecture: ArchitectureDiagramData;
  services: ServiceMapData;
  risks: RiskCardsData;
  timeline: TimelineData;
  export_ready: boolean;
  graph_version: string;
}
```

### Appendix B: DynamoDB Access Patterns

| Access Pattern | Query | Index |
|---------------|-------|-------|
| Get customer by ID | PK=CUST#id, SK=META | Table |
| List user's customers | GSI1: PK=USER#id | GSI1 |
| List all customers (admin) | GSI2: PK=Customer | GSI2 |
| List customer's sessions | PK=CUST#id, SK begins_with SESSION# | Table |
| Get session detail | PK=CUST#id, SK=SESSION#sid | Table |
| Get session panels (replay) | PK=CUST#id, SK begins_with SESSION#sid#PANEL | Table |
| Get intake answers | PK=CUST#id, SK=SESSION#sid#INPUT | Table |
| Load graph (all nodes) | PK=GRAPH#v3, SK begins_with NODE | Table |
| Load graph (all edges) | PK=GRAPH#v3, SK begins_with EDGE | Table |
| Get system prompt | PK=CONFIG#SYSTEM, SK=PROMPT#latest | Table |
| List prompt versions | PK=CONFIG#SYSTEM, SK begins_with PROMPT | Table |
| Dashboard metrics | PK=ADMIN#METRICS, SK begins_with date | Table |
| Recent sessions (admin) | GSI2: PK=Session, SK (created_at) desc, limit 20 | GSI2 |

### Appendix C: Knowledge Base Content Inventory

| Document | Node Count | Edge Count | Update Cadence |
|----------|-----------|-----------|----------------|
| `graph.json` | ~150 | ~600 | Monthly |
| `decision-logic.md` | — | — | Quarterly |
| `pattern-centralized-platform.md` | — | — | Quarterly |
| `pattern-federated-platform.md` | — | — | Quarterly |
| `agentcore-component-mapping.md` | — | — | Monthly (service changes) |
| `constraint-innovation-map.md` | — | — | Monthly (new innovations) |
| `anti-patterns-catalog.md` | — | — | Quarterly |
| `compliance-overlays.md` | — | — | Annually |

### Appendix D: Monthly Update Sources (Summary)

| Tier | Source Category | Examples | Update Method |
|------|----------------|----------|---------------|
| 1 | AWS-Specific | AWS What's New, Docs, Workshops | MCP (live) + monthly scan |
| 2 | Vendor-Neutral | Anthropic, OpenAI, LangChain, MCP Spec | Web search + monthly scan |
| 3 | Research | arXiv, NeurIPS, Amazon Science | Quarterly scan |
| 4 | Industry Analyst | Gartner, Forrester, McKinsey | Annual (manual) |
| 5 | Community | HN, Reddit, podcasts, GitHub | Weekly scan |
| 6 | Competitive | Azure AI, Vertex, Salesforce Agentforce | Monthly scan |

---

*End of document. This spec is implementation-ready — a developer can start building from Phase 0 immediately.*
