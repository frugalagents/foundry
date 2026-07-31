"""Curated decision knowledge for the coding-agent platform (the moat).

This is the exact/checkable half of the moat: the options an agent may choose
per box, the component each maps to, the cascades a choice triggers, and the
hard constraints a customer answer asserts. The Propose agent reasons *within*
this vocabulary; the guard enforces it. The fuzzy half (best-practice prose)
lives in the Bedrock KB and is retrieved at generate time.

Phase 1 authors the Model Gateway and Harness domains end to end; more boxes
are added by extending OPTIONS + CASCADES + CONSTRAINT_RULES.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    component_id: str
    # capabilities this option genuinely provides (checked by the guard)
    capabilities: tuple[str, ...] = ()
    # is this option self-hosted / customer-operated?
    self_hosted: bool = False


@dataclass(frozen=True)
class BoxDecision:
    box_id: str
    requirement_id: str
    question: str
    options: tuple[Option, ...]


# ── Model Gateway ────────────────────────────────────────────────────────────
MODEL_GATEWAY = BoxDecision(
    box_id="model-gateway",
    requirement_id="requirement:model-gateway-impl",
    question="How is the model gateway implemented?",
    options=(
        Option("agentcore-gateway", "Amazon Bedrock AgentCore Gateway",
               "component:model-gateway",
               capabilities=("managed", "prompt-caching", "fallback", "audit"),
               self_hosted=False),
        Option("claude-gateway", "Claude Gateway (managed)",
               "component:model-gateway",
               capabilities=("managed", "prompt-caching"), self_hosted=False),
        Option("litellm", "LiteLLM (self-hosted)",
               "component:model-gateway",
               capabilities=("prompt-caching", "fallback"), self_hosted=True),
        Option("bespoke", "Bespoke gateway (self-built)",
               "component:model-gateway",
               capabilities=("fallback",), self_hosted=True),
    ),
)

# ── Harness ──────────────────────────────────────────────────────────────────
HARNESS = BoxDecision(
    box_id="harness",
    requirement_id="requirement:harness-placement",
    question="Where does the coding agent harness run?",
    options=(
        Option("developer-machine", "Developer machine", "component:local-runtime",
               capabilities=("local-exec",), self_hosted=False),
        Option("agentcore-runtime", "AWS · AgentCore Runtime (managed)",
               "component:ephemeral-runtime",
               capabilities=("managed", "isolation"), self_hosted=False),
        Option("eks", "AWS · EKS (self-managed)", "component:container-runtime",
               capabilities=("isolation",), self_hosted=True),
        Option("lambda-microvm", "AWS · Lambda microVMs", "component:ephemeral-runtime",
               capabilities=("managed", "isolation"), self_hosted=False),
    ),
)

# ── Identity & Access ─────────────────────────────────────────────────────────
IDENTITY = BoxDecision(
    box_id="identity",
    requirement_id="requirement:identity-impl",
    question="How are workforce (developer) and workload (agent) identities established?",
    options=(
        Option("cognito", "Amazon Cognito (managed IdP + workload creds)",
               "component:workforce-identity",
               capabilities=("managed", "federation", "workload-identity", "audit"),
               self_hosted=False),
        Option("okta-entra", "Okta / Entra ID federation (existing enterprise IdP)",
               "component:workforce-identity",
               capabilities=("federation", "sso", "workload-identity", "audit"),
               self_hosted=False),
        Option("self-managed-oidc", "Self-managed OIDC (Keycloak / Dex)",
               "component:workforce-identity",
               capabilities=("federation", "sso", "workload-identity"),
               self_hosted=True),
    ),
)

# ── Observability & Audit ─────────────────────────────────────────────────────
OBSERVABILITY = BoxDecision(
    box_id="observability",
    requirement_id="requirement:observability-impl",
    question="How is agent telemetry, evaluation, and audit implemented?",
    options=(
        Option("agentcore-cloudwatch", "AWS · AgentCore Observability + CloudWatch (managed)",
               "component:telemetry-pipeline",
               capabilities=("managed", "tracing", "metrics", "audit"), self_hosted=False),
        Option("managed-otel", "AWS · Managed OTel + X-Ray",
               "component:telemetry-pipeline",
               capabilities=("managed", "tracing", "metrics", "otel"), self_hosted=False),
        Option("self-hosted-otel", "Self-hosted OTel (Grafana / Prometheus / Tempo)",
               "component:telemetry-pipeline",
               capabilities=("tracing", "metrics", "otel"), self_hosted=True),
    ),
)

# ── Agent Orchestration ───────────────────────────────────────────────────────
ORCHESTRATION = BoxDecision(
    box_id="orchestration",
    requirement_id="requirement:orchestration-topology",
    question="Single coding agent, or a multi-agent topology?",
    options=(
        Option("single", "Single agent (one orchestration runtime)",
               "component:orchestration-runtime",
               capabilities=("managed", "single-agent"), self_hosted=False),
        Option("multi-agent-supervisor", "Multi-agent supervisor (planner delegates to workers)",
               "component:multi-agent-supervisor",
               capabilities=("multi-agent", "supervisor", "delegation"), self_hosted=False),
        Option("sequential-handoff", "Sequential handoff (staged specialist pipeline)",
               "component:sequential-handoff",
               capabilities=("multi-agent", "handoff", "staged"), self_hosted=False),
        Option("parallel-reviewer", "Parallel reviewer (fan-out + critic agent)",
               "component:parallel-reviewer",
               capabilities=("multi-agent", "parallel", "review"), self_hosted=False),
    ),
)

# ── Tool / MCP Gateway ────────────────────────────────────────────────────────
TOOL_GATEWAY = BoxDecision(
    box_id="toolgateway",
    requirement_id="requirement:tool-gateway-impl",
    question="How do agents broker access to enterprise tools and APIs?",
    options=(
        Option("agentcore-gateway", "Amazon Bedrock AgentCore Gateway (managed MCP)",
               "component:tool-gateway",
               capabilities=("managed", "mcp", "isolation", "audit"), self_hosted=False),
        Option("self-hosted-mcp", "Self-hosted MCP gateway (EKS / ECS)",
               "component:tool-gateway",
               capabilities=("mcp", "audit"), self_hosted=True),
        Option("direct-connectors", "Direct connectors (no broker)",
               "component:connector-registry",
               capabilities=(), self_hosted=False),
    ),
)

BOXES: dict[str, BoxDecision] = {
    b.box_id: b for b in (
        MODEL_GATEWAY, HARNESS, IDENTITY, OBSERVABILITY, ORCHESTRATION, TOOL_GATEWAY,
    )
}


# ── Cascades: a choice at one box opens a follow-up decision at another ───────
@dataclass(frozen=True)
class Cascade:
    when_box: str
    when_values: tuple[str, ...]
    opens_note: str


CASCADES: tuple[Cascade, ...] = (
    Cascade("model-gateway", ("litellm", "bespoke"),
            "A self-hosted gateway needs a hosting decision (EKS / ECS) and "
            "its own scaling, patching, and availability ownership."),
    Cascade("harness", ("eks",),
            "Self-managed EKS adds node-pool sizing, patching, and cluster "
            "operations to the platform team's scope."),
    Cascade("toolgateway", ("self-hosted-mcp",),
            "A self-hosted MCP gateway needs a hosting decision (EKS / ECS), "
            "connector lifecycle ownership, and its own availability SLO."),
    Cascade("identity", ("self-managed-oidc",),
            "A self-managed OIDC provider adds identity uptime, key rotation, "
            "and federation maintenance to the platform team."),
    Cascade("orchestration", ("multi-agent-supervisor", "sequential-handoff", "parallel-reviewer"),
            "A multi-agent topology adds inter-agent state, handoff contracts, "
            "and higher token spend — budget and observability must scale with it."),
)


# ── Constraint rules: a customer answer asserts a hard constraint ─────────────
# The guard turns these into forbidden component ids / capabilities.
@dataclass(frozen=True)
class ConstraintRule:
    id: str
    description: str
    # answer key + value that triggers the constraint
    when_key: str
    when_value: object
    forbids_capabilities: tuple[str, ...] = field(default_factory=tuple)
    forbids_self_hosted: bool = False


CONSTRAINT_RULES: tuple[ConstraintRule, ...] = (
    ConstraintRule(
        id="managed-only",
        description="Managed-only mandate: no customer-operated infrastructure.",
        when_key="operational-posture", when_value="managed-only",
        forbids_self_hosted=True,
    ),
    ConstraintRule(
        id="no-self-hosting",
        description="Explicit no-self-hosting policy.",
        when_key="allow-self-hosting", when_value=False,
        forbids_self_hosted=True,
    ),
)


def option_for(box_id: str, value: str) -> Option | None:
    box = BOXES.get(box_id)
    if not box:
        return None
    return next((o for o in box.options if o.value == value), None)


def cascades_for(box_id: str, value: str) -> list[Cascade]:
    return [c for c in CASCADES if c.when_box == box_id and value in c.when_values]
