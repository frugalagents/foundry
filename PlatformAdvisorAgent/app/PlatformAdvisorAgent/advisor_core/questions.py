"""Declarative v2 questionnaire catalog."""
from __future__ import annotations

from .models import Workload

QUESTIONNAIRE_VERSION = "2.0"


UNIVERSAL_QUESTIONS = [
    {"id": "audience", "path": "audience", "prompt": "Who primarily consumes this platform?", "type": "single", "critical": True, "consumers": ["requirements", "topology"]},
    {"id": "primary_workload", "path": "primary_workload", "prompt": "What is the platform's primary job over the next 12 months?", "type": "single", "critical": True, "consumers": ["questionnaire", "components", "cost"]},
    {"id": "platform_owner", "path": "ownership.platform_owner", "prompt": "Who owns the platform product and roadmap?", "type": "single", "critical": True, "consumers": ["ownership", "operating_model"]},
    {"id": "funding_owner", "path": "ownership.funding_owner", "prompt": "Who funds the platform and approves capacity spend?", "type": "single", "critical": False, "consumers": ["ownership", "roadmap"]},
    {"id": "policy_owner", "path": "ownership.policy_owner", "prompt": "Who defines and maintains platform policy and compliance controls?", "type": "single", "critical": False, "consumers": ["ownership", "controls", "risks"]},
    {"id": "identity_owner", "path": "ownership.identity_owner", "prompt": "Who owns identity, access, and tenant authorization?", "type": "single", "critical": False, "consumers": ["ownership", "topology", "controls"]},
    {"id": "agent_delivery_owner", "path": "ownership.agent_delivery_owner", "prompt": "Who builds and releases production agents?", "type": "single", "critical": True, "consumers": ["ownership", "operating_model", "roadmap"]},
    {"id": "runtime_operations_owner", "path": "ownership.runtime_operations_owner", "prompt": "Who operates agents and responds to runtime failures?", "type": "single", "critical": True, "consumers": ["ownership", "operating_model", "risks"]},
    {"id": "incident_accountability", "path": "ownership.incident_accountability", "prompt": "Who is accountable when an agent causes a production incident?", "type": "single", "critical": True, "consumers": ["ownership", "risks"]},
    {"id": "autonomy", "path": "risk.autonomy", "prompt": "What actions may the agent take without approval?", "type": "single", "critical": True, "consumers": ["requirements", "controls", "risks"]},
    {"id": "failure_impact", "path": "risk.failure_impact", "prompt": "What is the worst credible impact of an incorrect agent action?", "type": "single", "critical": True, "consumers": ["requirements", "controls", "risks"]},
    {"id": "reversible_actions", "path": "risk.reversible_actions", "prompt": "Can production actions be reliably reversed?", "type": "boolean", "critical": True, "consumers": ["controls", "risks"]},
    {"id": "data_classifications", "path": "data.classifications", "prompt": "What is the most sensitive data the platform processes?", "type": "multi", "critical": True, "consumers": ["requirements", "controls", "topology"]},
    {"id": "residency", "path": "data.residency", "prompt": "Where is processing legally and technically allowed?", "type": "single", "critical": True, "consumers": ["requirements", "topology", "aws_mapping"]},
    {"id": "regulations", "path": "data.regulations", "prompt": "Which regulatory or assurance regimes are binding?", "type": "multi", "critical": True, "consumers": ["controls", "risks", "roadmap"]},
    {"id": "tenant_isolation", "path": "nfr.tenant_isolation", "prompt": "What isolation boundary is required between consumers?", "type": "single", "critical": True, "consumers": ["topology", "components", "cost"]},
    {"id": "availability", "path": "nfr.availability_pct", "prompt": "What production availability target must the platform meet?", "type": "number", "unit": "percent", "critical": True, "consumers": ["topology", "components", "cost"]},
    {"id": "latency", "path": "nfr.p95_latency_ms", "prompt": "What p95 response-time target must the platform meet?", "type": "number", "unit": "milliseconds", "critical": True, "consumers": ["topology", "aws_mapping", "cost"]},
    {"id": "current_maturity", "path": "current.maturity", "prompt": "What is the current production maturity?", "type": "single", "critical": False, "consumers": ["roadmap"]},
    {"id": "target_months", "path": "economics.target_months", "prompt": "When must the first production release be ready?", "type": "number", "unit": "months", "critical": False, "consumers": ["roadmap", "risks"]},
]


BRANCH_QUESTIONS: dict[Workload, list[dict]] = {
    Workload.CODING: [
        {"id": "coding_developers", "path": "workload_profile.developers", "prompt": "How many developers will use the platform?", "type": "range", "unit": "developers", "critical": True, "consumers": ["cost", "capacity"]},
        {"id": "coding_sessions", "path": "workload_profile.concurrent_sessions", "prompt": "How many concurrent coding sessions must it support?", "type": "range", "unit": "sessions", "critical": True, "consumers": ["topology", "capacity", "cost"]},
        {"id": "coding_calls", "path": "workload_profile.monthly_model_calls", "prompt": "What monthly model-call range do you expect?", "type": "range", "unit": "calls", "critical": True, "consumers": ["capacity", "cost"]},
        {"id": "coding_tokens", "path": "workload_profile.tokens_per_call", "prompt": "What input-plus-output token range do you expect per model call?", "type": "range", "unit": "tokens", "critical": True, "consumers": ["cost"]},
        {"id": "coding_boundary", "path": "workload_profile.code_boundary", "prompt": "What is the hard boundary for source code and IP?", "type": "single", "critical": True, "consumers": ["requirements", "topology", "controls"]},
        {"id": "coding_sandbox", "path": "workload_profile.execution_sandbox", "prompt": "Will agents execute generated code or repository commands?", "type": "boolean", "critical": True, "consumers": ["components", "controls", "risks"]},
    ],
    Workload.INTERNAL_COPILOT: [
        {"id": "copilot_users", "path": "workload_profile.monthly_active_users", "prompt": "How many employees will actively use it each month?", "type": "range", "unit": "users", "critical": True, "consumers": ["capacity", "cost"]},
        {"id": "copilot_queries", "path": "workload_profile.monthly_queries", "prompt": "What monthly query range do you expect?", "type": "range", "unit": "queries", "critical": True, "consumers": ["capacity", "cost"]},
        {"id": "copilot_tokens", "path": "workload_profile.tokens_per_query", "prompt": "What input-plus-output token range do you expect per query?", "type": "range", "unit": "tokens", "critical": True, "consumers": ["cost"]},
        {"id": "copilot_domains", "path": "workload_profile.data_domains", "prompt": "How many governed data domains must it access?", "type": "number", "critical": True, "consumers": ["components", "roadmap"]},
        {"id": "copilot_actions", "path": "workload_profile.action_enabled", "prompt": "Will it take actions in enterprise systems?", "type": "boolean", "critical": True, "consumers": ["requirements", "controls", "risks"]},
    ],
    Workload.HOSTING: [
        {"id": "hosting_teams", "path": "workload_profile.builder_teams", "prompt": "How many teams will build agents?", "type": "number", "critical": True, "consumers": ["ownership", "roadmap"]},
        {"id": "hosting_tenants", "path": "workload_profile.tenants", "prompt": "How many isolated tenants must the platform host?", "type": "range", "unit": "tenants", "critical": True, "consumers": ["topology", "capacity", "cost"]},
        {"id": "hosting_agents", "path": "workload_profile.deployed_agents", "prompt": "How many production agents will be deployed?", "type": "range", "unit": "agents", "critical": True, "consumers": ["capacity", "cost"]},
        {"id": "hosting_calls", "path": "workload_profile.monthly_model_calls", "prompt": "What monthly model-call range do you expect?", "type": "range", "unit": "calls", "critical": True, "consumers": ["capacity", "cost"]},
        {"id": "hosting_tokens", "path": "workload_profile.tokens_per_call", "prompt": "What input-plus-output token range do you expect per model call?", "type": "range", "unit": "tokens", "critical": True, "consumers": ["cost"]},
        {"id": "hosting_self_service", "path": "workload_profile.self_service", "prompt": "How independently should teams provision and deploy agents?", "type": "single", "critical": True, "consumers": ["ownership", "components", "roadmap"]},
    ],
    Workload.CUSTOMER_FACING: [
        {"id": "customer_tenants", "path": "workload_profile.tenants", "prompt": "How many customer tenants must be isolated?", "type": "range", "unit": "tenants", "critical": True, "consumers": ["topology", "capacity", "cost"]},
        {"id": "customer_rps", "path": "workload_profile.average_rps", "prompt": "What average request-rate range do you expect?", "type": "range", "unit": "requests/second", "critical": True, "consumers": ["capacity", "cost"]},
        {"id": "customer_peak", "path": "workload_profile.peak_rps", "prompt": "What peak requests per second must it sustain?", "type": "number", "unit": "requests/second", "critical": True, "consumers": ["topology", "capacity"]},
        {"id": "customer_calls", "path": "workload_profile.monthly_model_calls", "prompt": "What monthly model-call range do you expect?", "type": "range", "unit": "calls", "critical": True, "consumers": ["capacity", "cost"]},
        {"id": "customer_tokens", "path": "workload_profile.tokens_per_call", "prompt": "What input-plus-output token range do you expect per request?", "type": "range", "unit": "tokens", "critical": True, "consumers": ["cost"]},
    ],
    Workload.PROCESS_AUTOMATION: [
        {"id": "automation_workflows", "path": "workload_profile.workflows", "prompt": "How many distinct production workflows are in scope?", "type": "number", "critical": True, "consumers": ["components", "roadmap"]},
        {"id": "automation_executions", "path": "workload_profile.monthly_executions", "prompt": "What monthly execution range do you expect?", "type": "range", "unit": "executions", "critical": True, "consumers": ["capacity", "cost"]},
        {"id": "automation_tokens", "path": "workload_profile.tokens_per_execution", "prompt": "What token range do you expect per workflow execution?", "type": "range", "unit": "tokens", "critical": True, "consumers": ["cost"]},
        {"id": "automation_duration", "path": "workload_profile.average_duration_minutes", "prompt": "How long does an average workflow run?", "type": "number", "unit": "minutes", "critical": True, "consumers": ["aws_mapping", "cost"]},
        {"id": "automation_exceptions", "path": "workload_profile.exception_rate_pct", "prompt": "What exception rate requires human handling?", "type": "number", "unit": "percent", "critical": True, "consumers": ["risks", "roadmap", "cost"]},
        {"id": "automation_approval", "path": "workload_profile.approval_required", "prompt": "Must a human approve any workflow actions before execution?", "type": "boolean", "critical": True, "consumers": ["requirements", "controls", "risks"]},
    ],
    Workload.MARKETPLACE: [
        {"id": "market_publishers", "path": "workload_profile.publishers", "prompt": "How many agent publishers are expected?", "type": "range", "unit": "publishers", "critical": True, "consumers": ["ownership", "capacity"]},
        {"id": "market_consumers", "path": "workload_profile.consumers", "prompt": "How many agent consumers are expected?", "type": "range", "unit": "consumers", "critical": True, "consumers": ["capacity", "cost"]},
        {"id": "market_agents", "path": "workload_profile.listed_agents", "prompt": "How many agents will be listed?", "type": "range", "unit": "agents", "critical": True, "consumers": ["capacity", "cost"]},
        {"id": "market_transactions", "path": "workload_profile.monthly_transactions", "prompt": "What monthly transaction range do you expect?", "type": "range", "unit": "transactions", "critical": True, "consumers": ["capacity", "cost"]},
        {"id": "market_tokens", "path": "workload_profile.tokens_per_transaction", "prompt": "What token range do you expect per transaction?", "type": "range", "unit": "tokens", "critical": True, "consumers": ["cost"]},
        {"id": "market_external", "path": "workload_profile.external_agents", "prompt": "May third-party agents publish or transact?", "type": "boolean", "critical": True, "consumers": ["requirements", "controls", "risks"]},
        {"id": "market_billing", "path": "workload_profile.billing_model", "prompt": "How will agent usage be billed?", "type": "single", "critical": True, "consumers": ["components", "cost"]},
    ],
}


def build_questionnaire(workload: Workload | str | None = None) -> dict:
    selected = Workload(workload) if workload else None
    branch = BRANCH_QUESTIONS.get(selected, []) if selected else []
    return {
        "schema_version": QUESTIONNAIRE_VERSION,
        "questions": UNIVERSAL_QUESTIONS + branch,
        "branch": selected.value if selected else None,
    }
