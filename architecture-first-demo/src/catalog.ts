import type {
  ArchitectureComponent,
  ArchitectureEdge,
  DecisionDefinition,
  ServiceCandidate,
} from "./types";

const component = (
  id: string,
  label: string,
  detail: string,
  lane: ArchitectureComponent["lane"],
  icon: string,
  status: ArchitectureComponent["status"],
  x: number,
  y: number,
): ArchitectureComponent => ({ id, label, detail, lane, icon, status, x, y });

export const scenarioFacts = [
  "5,000 developers",
  "1,000+ concurrent tasks",
  "Claude Code + Codex",
  "GitLab SaaS",
  "Microsoft Entra ID",
  "Restricted egress",
];

export const lanePositions = [
  { id: "lane-experience", label: "Experience", y: 16, height: 106 },
  { id: "lane-control", label: "Control plane", y: 138, height: 126 },
  { id: "lane-execution", label: "Execution", y: 280, height: 126 },
  { id: "lane-integrations", label: "Integrations", y: 422, height: 110 },
  { id: "lane-agentops", label: "AgentOps", y: 548, height: 126 },
];

export const baseComponents: ArchitectureComponent[] = [
  component("developer-surface", "Coding-agent clients", "Claude Code and Codex", "Experience", "terminal", "confirmed", 70, 36),
  component("team-workspace", "Team workspace", "Projects, policy and budgets", "Experience", "users", "proposed", 330, 36),
  component("enterprise-identity", "Enterprise identity", "Entra-backed access", "Control plane", "key", "confirmed", 70, 162),
  component("agent-registry", "Agent registry", "Approved agents and versions", "Control plane", "archive", "confirmed", 330, 162),
  component("model-access", "Model access", "Routing decision unresolved", "Control plane", "route", "unresolved", 590, 162),
  component("tool-access", "Tool access", "Integration boundary unresolved", "Control plane", "plug", "unresolved", 850, 162),
  component("workflow-manifests", "Workflow manifests", "Developer-defined multi-agent flows", "Control plane", "workflow", "confirmed", 1110, 162),
  component("execution-placement", "Execution placement", "Local, cloud or hybrid?", "Execution", "cloud", "unresolved", 330, 304),
  component("gitlab", "GitLab SaaS", "Repositories, issues and merge requests", "Integrations", "git", "confirmed", 200, 442),
  component("enterprise-tools", "Enterprise tools", "CI/CD, packages, artifacts and APIs", "Integrations", "blocks", "proposed", 720, 442),
  component("audit-ledger", "Decision and audit ledger", "90-day replayable activity", "AgentOps", "scroll", "confirmed", 70, 572),
  component("telemetry", "Platform telemetry", "Outcome model unresolved", "AgentOps", "pulse", "unresolved", 590, 572),
];

export const baseEdges: ArchitectureEdge[] = [
  { source: "developer-surface", target: "enterprise-identity" },
  { source: "developer-surface", target: "agent-registry" },
  { source: "agent-registry", target: "model-access" },
  { source: "agent-registry", target: "tool-access" },
  { source: "workflow-manifests", target: "execution-placement" },
  { source: "execution-placement", target: "gitlab" },
  { source: "execution-placement", target: "enterprise-tools" },
  { source: "enterprise-identity", target: "audit-ledger" },
  { source: "model-access", target: "telemetry" },
  { source: "tool-access", target: "telemetry" },
];

export const baseServices: ServiceCandidate[] = [
  {
    component: "Coding-agent clients",
    purpose: "Developer interaction",
    recommended: ["Claude Code", "OpenAI Codex"],
    alternatives: [],
  },
  {
    component: "Enterprise identity",
    purpose: "User authentication and team access",
    recommended: ["Microsoft Entra ID"],
    alternatives: ["AWS IAM Identity Center federation"],
  },
  {
    component: "Source control",
    purpose: "Repository and merge-request transaction boundary",
    recommended: ["GitLab SaaS"],
    alternatives: [],
  },
];

const executionComponents = {
  hybrid: [
    component("local-runtime", "Managed local runtime", "Interactive coding on managed laptops", "Execution", "laptop", "confirmed", 70, 304),
    component("ephemeral-runtime", "Ephemeral task runtime", "Isolated issue-to-PR execution", "Execution", "timer", "confirmed", 460, 304),
    component("persistent-runtime", "Persistent workspace", "Long migrations and team environments", "Execution", "server", "proposed", 850, 304),
    component("sandbox-policy", "Sandbox policy", "Image, network and resource controls", "Execution", "shield", "confirmed", 1110, 304),
  ],
  local: [
    component("local-runtime", "Managed local runtime", "All agent execution on managed laptops", "Execution", "laptop", "confirmed", 200, 304),
    component("endpoint-policy", "Endpoint policy", "Local sandbox and egress enforcement", "Execution", "shield", "confirmed", 720, 304),
  ],
  cloud: [
    component("ephemeral-runtime", "Ephemeral task runtime", "Short-lived isolated task execution", "Execution", "timer", "confirmed", 200, 304),
    component("persistent-runtime", "Persistent workspace", "Developer and migration environments", "Execution", "server", "confirmed", 590, 304),
    component("sandbox-policy", "Sandbox policy", "Image, network and resource controls", "Execution", "shield", "confirmed", 980, 304),
  ],
};

export const decisions: DecisionDefinition[] = [
  {
    id: "execution",
    number: "01",
    category: "Runtime topology",
    title: "Place execution by interaction mode",
    recommendation:
      "Use local execution for interactive coding, ephemeral cloud runtimes for asynchronous issue-to-PR work, and persistent workspaces only for long migrations.",
    whyNow: "This determines the trust boundary, runtime services and operating burden.",
    options: [
      {
        id: "hybrid",
        label: "Adopt hybrid placement",
        description: "Local for interactive work, cloud for autonomous and long-running tasks.",
        consequence: "Best workflow fit; requires a common policy and telemetry contract across runtimes.",
        recommended: true,
        components: executionComponents.hybrid,
        removeComponents: ["execution-placement"],
        edges: [
          { source: "workflow-manifests", target: "local-runtime" },
          { source: "workflow-manifests", target: "ephemeral-runtime" },
          { source: "workflow-manifests", target: "persistent-runtime" },
          { source: "sandbox-policy", target: "ephemeral-runtime" },
          { source: "local-runtime", target: "gitlab" },
          { source: "ephemeral-runtime", target: "gitlab" },
          { source: "persistent-runtime", target: "gitlab" },
        ],
        services: [
          {
            component: "Managed local runtime",
            purpose: "Interactive coding on governed endpoints",
            recommended: ["Claude Code", "OpenAI Codex", "Microsoft Intune policies"],
            alternatives: ["Developer-managed CLI"],
          },
          {
            component: "Ephemeral task runtime",
            purpose: "Isolated asynchronous execution",
            recommended: ["AWS CodeBuild", "AgentCore Runtime"],
            alternatives: ["Lambda MicroVMs", "Kubernetes Jobs"],
          },
          {
            component: "Persistent workspace",
            purpose: "Long migrations and durable environments",
            recommended: ["Coder on Amazon EKS"],
            alternatives: ["EC2 development environments"],
          },
        ],
      },
      {
        id: "local",
        label: "Keep execution local",
        description: "Agents run only on managed developer laptops.",
        consequence: "Fastest rollout; limits centralized isolation, concurrency and unattended execution.",
        components: executionComponents.local,
        removeComponents: ["execution-placement"],
        edges: [
          { source: "workflow-manifests", target: "local-runtime" },
          { source: "endpoint-policy", target: "local-runtime" },
          { source: "local-runtime", target: "gitlab" },
        ],
        services: [
          {
            component: "Managed local runtime",
            purpose: "All coding-agent execution",
            recommended: ["Claude Code", "OpenAI Codex", "Microsoft Intune policies"],
            alternatives: [],
          },
        ],
      },
      {
        id: "cloud",
        label: "Centralize in cloud",
        description: "Interactive and autonomous work run in company-controlled cloud environments.",
        consequence: "Strong governance and isolation; higher latency and platform operations.",
        components: executionComponents.cloud,
        removeComponents: ["execution-placement"],
        edges: [
          { source: "workflow-manifests", target: "ephemeral-runtime" },
          { source: "workflow-manifests", target: "persistent-runtime" },
          { source: "sandbox-policy", target: "ephemeral-runtime" },
          { source: "sandbox-policy", target: "persistent-runtime" },
          { source: "ephemeral-runtime", target: "gitlab" },
          { source: "persistent-runtime", target: "gitlab" },
        ],
        services: [
          {
            component: "Cloud execution fabric",
            purpose: "Centralized interactive and asynchronous execution",
            recommended: ["AgentCore Runtime", "AWS CodeBuild", "Coder on Amazon EKS"],
            alternatives: ["Kubernetes Jobs", "EC2 development environments"],
          },
        ],
      },
    ],
  },
  {
    id: "boundaries",
    number: "02",
    category: "Control plane",
    title: "Make team workspaces the governance boundary",
    recommendation:
      "Run one enterprise control plane with Entra-backed team workspaces, delegated administration, independent quotas and policy profiles.",
    whyNow: "This resolves how 5,000 developers share the platform without creating a control plane per team.",
    options: [
      {
        id: "team",
        label: "Use team workspaces",
        description: "Shared control plane with isolated policy, quota and audit scopes.",
        consequence: "Balances central governance with team autonomy.",
        recommended: true,
        components: [
          component("workspace-policy", "Workspace policy", "Team-scoped controls and exceptions", "Control plane", "shield", "confirmed", 200, 220),
          component("quota-manager", "Quota and budget manager", "Team concurrency and spend limits", "Control plane", "gauge", "confirmed", 720, 220),
        ],
        edges: [
          { source: "enterprise-identity", target: "team-workspace" },
          { source: "team-workspace", target: "workspace-policy" },
          { source: "team-workspace", target: "quota-manager" },
          { source: "workspace-policy", target: "audit-ledger" },
        ],
        services: [
          {
            component: "Team workspace",
            purpose: "Delegated administration and authorization",
            recommended: ["Microsoft Entra groups", "Git-backed workspace manifests"],
            alternatives: ["Dedicated AWS accounts for exceptional teams"],
          },
          {
            component: "Policy and quota",
            purpose: "Team controls, budgets and concurrency",
            recommended: ["AgentCore Policy", "Amazon DynamoDB quota ledger"],
            alternatives: ["OPA", "Cedar policy service"],
          },
        ],
      },
      {
        id: "shared",
        label: "Use shared RBAC",
        description: "One shared workspace with role-based repository access.",
        consequence: "Simpler operations; weak blast-radius and cost attribution boundaries.",
        components: [
          component("shared-rbac", "Shared RBAC", "Repository-level authorization", "Control plane", "users", "confirmed", 460, 220),
        ],
        removeComponents: ["team-workspace"],
        edges: [
          { source: "enterprise-identity", target: "shared-rbac" },
          { source: "shared-rbac", target: "audit-ledger" },
        ],
        services: [
          {
            component: "Shared authorization",
            purpose: "Repository-level access",
            recommended: ["Microsoft Entra groups"],
            alternatives: ["GitLab project roles"],
          },
        ],
      },
      {
        id: "dedicated",
        label: "Use dedicated business-unit planes",
        description: "Separate control and execution planes for major organizational units.",
        consequence: "Strongest isolation; duplicates platform operations and slows rollout.",
        components: [
          component("federated-planes", "Federated control planes", "Dedicated organizational boundaries", "Control plane", "network", "confirmed", 460, 220),
        ],
        removeComponents: ["team-workspace"],
        edges: [
          { source: "enterprise-identity", target: "federated-planes" },
          { source: "federated-planes", target: "audit-ledger" },
        ],
        services: [
          {
            component: "Federated platform planes",
            purpose: "Infrastructure-level organizational isolation",
            recommended: ["AWS Organizations", "Dedicated platform stacks"],
            alternatives: ["Dedicated EKS clusters"],
          },
        ],
      },
    ],
  },
  {
    id: "routing",
    number: "03",
    category: "Model strategy and tokenomics",
    title: "Route models against task value and token budget",
    recommendation:
      "Keep developer choice, but add policy-based routing for automated tasks, provider fallback, token budgets and cache-aware context reuse.",
    whyNow: "At this scale, provider choice is an economic and resilience control, not a client preference.",
    options: [
      {
        id: "adaptive",
        label: "Use adaptive routing",
        description: "Classify tasks and route by capability, cost, residency and availability.",
        consequence: "Lowest expected cost per successful task; requires routing evaluation and policy.",
        recommended: true,
        components: [
          component("model-router", "Model router", "Task, policy and provider selection", "Control plane", "route", "confirmed", 590, 162),
          component("provider-adapters", "Provider adapters", "Bedrock, OpenAI and Anthropic", "Control plane", "plug", "confirmed", 850, 220),
          component("token-budget", "Token budget policy", "Per-task and per-team limits", "AgentOps", "coins", "confirmed", 330, 630),
          component("context-cache", "Context and response cache", "Reuse safe repository context", "AgentOps", "database", "proposed", 850, 630),
        ],
        removeComponents: ["model-access"],
        edges: [
          { source: "agent-registry", target: "model-router" },
          { source: "model-router", target: "provider-adapters" },
          { source: "quota-manager", target: "model-router" },
          { source: "model-router", target: "token-budget" },
          { source: "context-cache", target: "model-router" },
          { source: "model-router", target: "telemetry" },
        ],
        services: [
          {
            component: "Model access and routing",
            purpose: "Model selection, fallback and policy enforcement",
            recommended: ["Amazon Bedrock", "Provider adapters"],
            alternatives: ["LiteLLM", "Kong AI Gateway", "SaaS AI gateways"],
          },
          {
            component: "Context cache",
            purpose: "Reduce repeated context tokens",
            recommended: ["Amazon ElastiCache for Valkey"],
            alternatives: ["Self-managed Valkey"],
          },
          {
            component: "Token economics",
            purpose: "Budgets, attribution and anomaly detection",
            recommended: ["Amazon DynamoDB", "Amazon Athena"],
            alternatives: ["OpenCost-style custom ledger"],
          },
        ],
      },
      {
        id: "manual",
        label: "Let developers choose",
        description: "Expose approved providers and leave model selection to each developer.",
        consequence: "Fast and transparent; weak cost optimization and automated-task consistency.",
        components: [
          component("model-catalog", "Approved model catalog", "Developer-selected providers", "Control plane", "archive", "confirmed", 590, 162),
          component("provider-adapters", "Provider adapters", "Bedrock, OpenAI and Anthropic", "Control plane", "plug", "confirmed", 850, 220),
        ],
        removeComponents: ["model-access"],
        edges: [
          { source: "agent-registry", target: "model-catalog" },
          { source: "model-catalog", target: "provider-adapters" },
          { source: "provider-adapters", target: "telemetry" },
        ],
        services: [
          {
            component: "Approved model catalog",
            purpose: "Governed developer choice",
            recommended: ["Amazon Bedrock", "OpenAI API", "Anthropic API"],
            alternatives: [],
          },
        ],
      },
      {
        id: "premium",
        label: "Prefer maximum capability",
        description: "Use the strongest approved model by default with fallback for availability.",
        consequence: "Higher expected task quality; highest token spend and provider concentration.",
        components: [
          component("quality-router", "Quality-first router", "Premium model with provider fallback", "Control plane", "route", "confirmed", 590, 162),
          component("provider-adapters", "Provider adapters", "Bedrock, OpenAI and Anthropic", "Control plane", "plug", "confirmed", 850, 220),
          component("token-budget", "Token budget policy", "Guardrail rather than optimizer", "AgentOps", "coins", "confirmed", 330, 630),
        ],
        removeComponents: ["model-access"],
        edges: [
          { source: "agent-registry", target: "quality-router" },
          { source: "quality-router", target: "provider-adapters" },
          { source: "quality-router", target: "token-budget" },
          { source: "quality-router", target: "telemetry" },
        ],
        services: [
          {
            component: "Quality-first model access",
            purpose: "Premium model selection and fallback",
            recommended: ["Amazon Bedrock", "OpenAI API", "Anthropic API"],
            alternatives: ["SaaS AI gateways"],
          },
        ],
      },
    ],
  },
  {
    id: "tools",
    number: "04",
    category: "Integration and trust",
    title: "Broker tools instead of distributing credentials",
    recommendation:
      "Place GitLab, CI/CD, package, artifact and enterprise APIs behind an allowlisted tool gateway with action-scoped credentials.",
    whyNow: "This converts broad integration access into an enforceable and auditable architecture boundary.",
    options: [
      {
        id: "governed",
        label: "Use a governed tool gateway",
        description: "MCP and API tools are registered, policy checked and credential brokered.",
        consequence: "Strong audit and revocation; teams must onboard tools through a contract.",
        recommended: true,
        components: [
          component("tool-gateway", "MCP and tool gateway", "Allowlisted tools and action policy", "Control plane", "plug", "confirmed", 980, 162),
          component("credential-broker", "Credential broker", "User and workload identity by action", "Control plane", "key", "confirmed", 1110, 220),
          component("egress-control", "Egress control", "GitLab and approved registries only", "Integrations", "shield", "confirmed", 1110, 442),
        ],
        removeComponents: ["tool-access"],
        edges: [
          { source: "agent-registry", target: "tool-gateway" },
          { source: "enterprise-identity", target: "credential-broker" },
          { source: "credential-broker", target: "tool-gateway" },
          { source: "tool-gateway", target: "gitlab" },
          { source: "tool-gateway", target: "enterprise-tools" },
          { source: "egress-control", target: "enterprise-tools" },
          { source: "tool-gateway", target: "telemetry" },
        ],
        services: [
          {
            component: "Tool gateway",
            purpose: "MCP/API registry, action policy and audit",
            recommended: ["AgentCore Gateway"],
            alternatives: ["Self-hosted MCP gateway"],
          },
          {
            component: "Credential broker",
            purpose: "Short-lived action-scoped credentials",
            recommended: ["AWS Secrets Manager", "AWS IAM roles"],
            alternatives: ["Enterprise secrets broker"],
          },
          {
            component: "Restricted egress",
            purpose: "Allow GitLab and approved package registries only",
            recommended: ["VPC endpoints", "AWS Network Firewall"],
            alternatives: ["Enterprise egress proxy"],
          },
        ],
      },
      {
        id: "direct",
        label: "Use direct integrations",
        description: "Each agent manages approved integrations and credentials.",
        consequence: "Fastest onboarding; duplicated security logic and fragmented audit trails.",
        components: [
          component("direct-tools", "Direct agent integrations", "Per-agent API and MCP configuration", "Control plane", "plug", "confirmed", 980, 162),
        ],
        removeComponents: ["tool-access"],
        edges: [
          { source: "agent-registry", target: "direct-tools" },
          { source: "direct-tools", target: "gitlab" },
          { source: "direct-tools", target: "enterprise-tools" },
          { source: "direct-tools", target: "telemetry" },
        ],
        services: [
          {
            component: "Direct integrations",
            purpose: "Per-agent access to enterprise tools",
            recommended: ["Agent-native GitLab and MCP integrations"],
            alternatives: [],
          },
        ],
      },
    ],
  },
  {
    id: "outcomes",
    number: "05",
    category: "Outcome operations",
    title: "Operate against coding outcomes, not token volume",
    recommendation:
      "Use accepted changes, test quality, rework, cycle time and cost per successful task as platform SLOs. Keep token and latency metrics as diagnostics.",
    whyNow: "This changes observability from infrastructure monitoring into an improvement and investment system.",
    options: [
      {
        id: "balanced",
        label: "Use balanced outcome SLOs",
        description: "Measure delivery, quality, economics, safety and developer intervention.",
        consequence: "Best decision signal; requires joining agent traces with GitLab and CI outcomes.",
        recommended: true,
        components: [
          component("outcome-telemetry", "Outcome telemetry", "Task-to-merge and CI correlation", "AgentOps", "pulse", "confirmed", 590, 572),
          component("evaluation-engine", "Evaluation engine", "Quality, safety and routing evaluation", "AgentOps", "check", "confirmed", 850, 572),
          component("outcome-ledger", "Outcome and cost ledger", "Cost per accepted change", "AgentOps", "chart", "confirmed", 1110, 572),
        ],
        removeComponents: ["telemetry"],
        edges: [
          { source: "gitlab", target: "outcome-telemetry" },
          { source: "enterprise-tools", target: "outcome-telemetry" },
          { source: "outcome-telemetry", target: "evaluation-engine" },
          { source: "evaluation-engine", target: "outcome-ledger" },
          { source: "token-budget", target: "outcome-ledger" },
          { source: "outcome-ledger", target: "audit-ledger" },
        ],
        services: [
          {
            component: "Outcome telemetry",
            purpose: "Correlate agent traces, merge requests and CI results",
            recommended: ["OpenTelemetry", "Amazon CloudWatch"],
            alternatives: ["Datadog", "Splunk"],
          },
          {
            component: "Evaluation engine",
            purpose: "Task quality, safety and routing effectiveness",
            recommended: ["AgentCore Evaluations", "Custom deterministic evaluators"],
            alternatives: ["Langfuse", "Arize Phoenix"],
          },
          {
            component: "Outcome ledger",
            purpose: "Cost and outcome analytics",
            recommended: ["Amazon S3", "Amazon Athena"],
            alternatives: ["Enterprise analytics platform"],
          },
        ],
      },
      {
        id: "delivery",
        label: "Prioritize delivery outcomes",
        description: "Focus on accepted PRs, cycle time, test pass rate and rework.",
        consequence: "Clear engineering impact; weaker cost and routing feedback.",
        components: [
          component("delivery-telemetry", "Delivery telemetry", "Merge, CI and rework outcomes", "AgentOps", "pulse", "confirmed", 590, 572),
          component("evaluation-engine", "Evaluation engine", "Code and task quality", "AgentOps", "check", "confirmed", 980, 572),
        ],
        removeComponents: ["telemetry"],
        edges: [
          { source: "gitlab", target: "delivery-telemetry" },
          { source: "enterprise-tools", target: "delivery-telemetry" },
          { source: "delivery-telemetry", target: "evaluation-engine" },
          { source: "evaluation-engine", target: "audit-ledger" },
        ],
        services: [
          {
            component: "Delivery telemetry",
            purpose: "Task-to-merge and CI correlation",
            recommended: ["OpenTelemetry", "Amazon CloudWatch", "GitLab events"],
            alternatives: ["Datadog", "Splunk"],
          },
        ],
      },
      {
        id: "economics",
        label: "Prioritize unit economics",
        description: "Focus on token efficiency, cost per task and budget variance.",
        consequence: "Strong AI FinOps control; may underweight code quality and developer rework.",
        components: [
          component("cost-telemetry", "Cost telemetry", "Tokens, runtime and provider spend", "AgentOps", "coins", "confirmed", 590, 572),
          component("outcome-ledger", "Cost ledger", "Unit economics by team and task", "AgentOps", "chart", "confirmed", 980, 572),
        ],
        removeComponents: ["telemetry"],
        edges: [
          { source: "model-router", target: "cost-telemetry" },
          { source: "quality-router", target: "cost-telemetry" },
          { source: "model-catalog", target: "cost-telemetry" },
          { source: "provider-adapters", target: "cost-telemetry" },
          { source: "cost-telemetry", target: "outcome-ledger" },
          { source: "outcome-ledger", target: "audit-ledger" },
        ],
        services: [
          {
            component: "Cost telemetry and ledger",
            purpose: "Token, runtime and team cost attribution",
            recommended: ["Amazon CloudWatch", "Amazon S3", "Amazon Athena"],
            alternatives: ["Enterprise FinOps platform"],
          },
        ],
      },
    ],
  },
];
