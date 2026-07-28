"""Typed, deterministic architecture decision pipeline."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from .catalogs import (
    BASE_COMPONENT_MONTHLY,
    CATALOG_VERSION,
    COMPONENTS,
    METHODOLOGY_VERSION,
    PLANNING_RATES,
    PRICE_CATALOG_DATE,
    REGULATION_CONTROLS,
)
from .models import (
    AssessmentInput,
    AssessmentResult,
    Autonomy,
    CapabilityOwnership,
    ComponentDecision,
    ControlDecision,
    CostEstimate,
    CostScenario,
    DataClass,
    EvidenceGap,
    Impact,
    Isolation,
    Maturity,
    OverrideRecord,
    Ownership,
    Requirement,
    Residency,
    RiskDecision,
    RoadmapPhase,
    TopologyDecision,
    TraceRecord,
    VolumeRange,
    Workload,
)


class DecisionEngine:
    """Pure decision kernel. No LLM, network, persistence, or UI dependencies."""

    def assess(
        self,
        assessment: AssessmentInput,
        overrides: Iterable[OverrideRecord] | None = None,
    ) -> AssessmentResult:
        applied_overrides = list(overrides or [])
        self._validate_overrides(applied_overrides)
        gaps = self._validate_evidence(assessment)
        ownership, ownership_trace = self._ownership_matrix(assessment)
        operating_model, model_trace = self._operating_model(assessment)
        operating_override = self._override_value(applied_overrides, "operating_model")
        if operating_override:
            operating_model = operating_override
            model_trace.append(TraceRecord(
                decision="operating_model",
                rule_id="override.operating_model",
                evidence=[self._override_reason(applied_overrides, "operating_model")],
                outcome=operating_model,
            ))

        requirements, requirement_trace = self._requirements(assessment)
        topology, topology_trace = self._topology(assessment, operating_model)
        topology = self._apply_topology_overrides(topology, applied_overrides)
        components, component_trace = self._components(assessment, requirements, topology)
        controls, control_trace = self._controls(assessment, requirements)
        risks, risk_trace = self._risks(assessment, controls)

        critical_count = len(self._critical_fields(assessment))
        coverage = 1.0 if critical_count == 0 else round(
            max(0.0, (critical_count - len(gaps)) / critical_count), 4
        )
        status = "needs_information" if gaps else ("overridden" if applied_overrides else "complete")

        roadmap: list[RoadmapPhase] = []
        cost = None
        roadmap_trace: list[TraceRecord] = []
        cost_trace: list[TraceRecord] = []
        if not gaps:
            roadmap, roadmap_trace = self._roadmap(assessment, components)
            cost, cost_trace = self._cost(assessment, components, topology)

        return AssessmentResult(
            methodology_version=METHODOLOGY_VERSION,
            catalog_version=CATALOG_VERSION,
            status=status,
            evidence_coverage=coverage,
            missing_evidence=gaps,
            assumptions=self._assumptions(assessment),
            ownership_matrix=ownership,
            operating_model=operating_model,
            requirements=requirements,
            topology=topology,
            components=components,
            controls=controls,
            risks=risks,
            roadmap=roadmap,
            cost=cost,
            trace=(
                ownership_trace + model_trace + requirement_trace + topology_trace
                + component_trace + control_trace + risk_trace + roadmap_trace + cost_trace
            ),
            overrides=applied_overrides,
        )

    def create_override(
        self,
        *,
        decision_path: str,
        engine_value: str,
        override_value: str,
        rationale: str,
        author: str,
    ) -> OverrideRecord:
        return OverrideRecord(
            decision_path=decision_path,
            engine_value=engine_value,
            override_value=override_value,
            rationale=rationale,
            author=author,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _critical_fields(self, a: AssessmentInput) -> list[str]:
        common = [
            "ownership.platform_owner",
            "ownership.agent_delivery_owner",
            "ownership.runtime_operations_owner",
            "ownership.incident_accountability",
            "risk.autonomy",
            "risk.failure_impact",
            "risk.reversible_actions",
            "data.classifications",
            "data.residency",
            "data.regulations",
            "nfr.tenant_isolation",
            "nfr.availability_pct",
            "nfr.p95_latency_ms",
        ]
        branch = {
            Workload.CODING: [
                "workload_profile.developers", "workload_profile.concurrent_sessions",
                "workload_profile.monthly_model_calls", "workload_profile.tokens_per_call",
                "workload_profile.code_boundary", "workload_profile.execution_sandbox",
            ],
            Workload.INTERNAL_COPILOT: [
                "workload_profile.monthly_active_users", "workload_profile.data_domains",
                "workload_profile.monthly_queries", "workload_profile.tokens_per_query",
                "workload_profile.action_enabled",
            ],
            Workload.HOSTING: [
                "workload_profile.builder_teams", "workload_profile.tenants",
                "workload_profile.deployed_agents", "workload_profile.monthly_model_calls",
                "workload_profile.tokens_per_call", "workload_profile.self_service",
            ],
            Workload.CUSTOMER_FACING: [
                "workload_profile.tenants", "workload_profile.average_rps",
                "workload_profile.peak_rps", "workload_profile.monthly_model_calls",
                "workload_profile.tokens_per_call",
            ],
            Workload.PROCESS_AUTOMATION: [
                "workload_profile.workflows", "workload_profile.monthly_executions",
                "workload_profile.tokens_per_execution",
                "workload_profile.average_duration_minutes",
                "workload_profile.exception_rate_pct",
                "workload_profile.approval_required",
            ],
            Workload.MARKETPLACE: [
                "workload_profile.publishers", "workload_profile.consumers",
                "workload_profile.listed_agents", "workload_profile.monthly_transactions",
                "workload_profile.tokens_per_transaction",
                "workload_profile.external_agents", "workload_profile.billing_model",
            ],
        }
        return common + branch[a.primary_workload]

    def _validate_evidence(self, a: AssessmentInput) -> list[EvidenceGap]:
        raw = a.model_dump(mode="json")
        gaps: list[EvidenceGap] = []
        for path in self._critical_fields(a):
            value = self._get_path(raw, path)
            missing = value is None or value == "" or value == [] or value == "unknown"
            if missing:
                gaps.append(EvidenceGap(
                    field=path,
                    reason="Required to produce a decision-grade architecture",
                    question_id=path.replace(".", "_"),
                ))
        if (
            a.audience.value in ("external_customers", "third_parties")
            and a.risk.failure_impact in (Impact.HIGH, Impact.SEVERE)
            and a.nfr.tenant_isolation == Isolation.SHARED_RBAC
        ):
            gaps.append(EvidenceGap(
                field="nfr.tenant_isolation",
                reason="Shared RBAC is insufficient for a high-impact external trust boundary",
                question_id="isolation",
            ))
        return gaps

    def _ownership_matrix(
        self, a: AssessmentInput
    ) -> tuple[list[CapabilityOwnership], list[TraceRecord]]:
        source = a.ownership
        assignments = [
            (
                "strategy_and_funding",
                source.platform_owner if source.platform_owner != Ownership.UNKNOWN else source.funding_owner,
                ["ownership.platform_owner", "ownership.funding_owner"],
            ),
            ("policy_and_compliance", source.policy_owner, ["ownership.policy_owner"]),
            ("identity_and_access", source.identity_owner, ["ownership.identity_owner"]),
            ("platform_control_plane", source.platform_owner, ["ownership.platform_owner"]),
            ("agent_development", source.agent_delivery_owner, ["ownership.agent_delivery_owner"]),
            ("data_products", source.agent_delivery_owner, ["ownership.agent_delivery_owner"]),
            ("runtime_operations", source.runtime_operations_owner, ["ownership.runtime_operations_owner"]),
            ("incident_response", source.incident_accountability, ["ownership.incident_accountability"]),
        ]
        rows = [
            CapabilityOwnership(capability=capability, owner=owner, evidence=evidence)
            for capability, owner, evidence in assignments
        ]
        trace = [
            TraceRecord(
                decision=f"ownership.{row.capability}",
                rule_id="ownership.explicit_accountability",
                evidence=row.evidence,
                outcome=row.owner.value,
            )
            for row in rows
        ]
        return rows, trace

    def _operating_model(self, a: AssessmentInput) -> tuple[str, list[TraceRecord]]:
        delivery = a.ownership.agent_delivery_owner
        runtime = a.ownership.runtime_operations_owner
        platform = a.ownership.platform_owner
        if delivery == Ownership.CENTRAL and runtime == Ownership.CENTRAL:
            model = "centralized"
            rule = "operating.central_delivery_and_runtime"
        elif (
            delivery == Ownership.DOMAIN
            and runtime == Ownership.DOMAIN
            and platform in (Ownership.DOMAIN, Ownership.UNKNOWN)
        ):
            model = "decentralized"
            rule = "operating.domain_delivery_and_runtime"
        else:
            model = "federated"
            rule = "operating.shared_control_domain_delivery"
        trace = [TraceRecord(
            decision="operating_model",
            rule_id=rule,
            evidence=[
                f"agent_delivery_owner={delivery.value}",
                f"runtime_operations_owner={runtime.value}",
                f"platform_owner={platform.value}",
            ],
            outcome=model,
        )]
        return model, trace

    def _requirements(
        self, a: AssessmentInput
    ) -> tuple[list[Requirement], list[TraceRecord]]:
        requirements: list[Requirement] = []

        def add(req_id: str, category: str, statement: str, evidence: list[str], hard: bool = False):
            requirements.append(Requirement(
                id=req_id, category=category, statement=statement, evidence=evidence, hard=hard
            ))

        add("req-identity", "security", "Every user, agent, and tool requires attributable workload identity.", ["audience"])
        add("req-observability", "operations", "Record model, tool, policy, latency, cost, and outcome telemetry.", ["risk.failure_impact"])
        if a.risk.autonomy == Autonomy.AUTONOMOUS or a.risk.failure_impact in (Impact.HIGH, Impact.SEVERE):
            add("req-policy", "safety", "Enforce policy before tool execution and high-impact actions.", ["risk.autonomy", "risk.failure_impact"], True)
        if a.risk.human_approval_required or not a.risk.reversible_actions:
            add("req-approval", "safety", "Provide durable approval gates and idempotent execution.", ["risk.human_approval_required", "risk.reversible_actions"], True)
        if a.data.classifications and any(
            item in (DataClass.CONFIDENTIAL, DataClass.RESTRICTED, DataClass.PHI, DataClass.PCI)
            for item in a.data.classifications
        ):
            add("req-sensitive-data", "data", "Keep sensitive data encrypted, scoped, and auditable.", ["data.classifications"], True)
        if a.data.residency in (Residency.COUNTRY_BOUND, Residency.HYBRID, Residency.MULTI_CLOUD):
            add("req-residency", "data", "Enforce processing and storage placement by jurisdiction.", ["data.residency"], True)
        if a.nfr.tenant_isolation in (Isolation.ACCOUNT, Isolation.DEDICATED_STACK):
            add("req-tenant-isolation", "security", "Use infrastructure-level tenant isolation and independent quotas.", ["nfr.tenant_isolation"], True)
        if (a.nfr.availability_pct or 0) >= 99.9 or (a.nfr.regions or 1) > 1:
            add("req-resilience", "reliability", "Survive a regional or zonal runtime failure within stated recovery objectives.", ["nfr.availability_pct", "nfr.regions"], True)
        if a.primary_workload == Workload.CODING:
            add("req-code-boundary", "security", "Enforce source-code egress and isolated execution policy.", ["workload_profile.code_boundary"], True)
        if a.primary_workload == Workload.MARKETPLACE:
            add("req-market-trust", "commercial", "Verify publisher identity, agent provenance, entitlement, and transaction evidence.", ["workload_profile.external_agents"], True)
        if a.primary_workload in (Workload.HOSTING, Workload.CUSTOMER_FACING, Workload.MARKETPLACE):
            add("req-multitenancy", "platform", "Provide tenant-aware identity, quotas, routing, and observability.", ["primary_workload", "nfr.tenant_isolation"], True)
        if a.primary_workload == Workload.INTERNAL_COPILOT:
            add("req-data-access", "data", "Preserve source-system permissions during retrieval and action execution.", ["workload_profile.data_domains"], True)
        if (
            a.primary_workload == Workload.PROCESS_AUTOMATION
            and a.workload_profile.approval_required
            and "req-approval" not in {item.id for item in requirements}
        ):
            add("req-approval", "safety", "Provide durable approval gates and idempotent execution.", ["workload_profile.approval_required"], True)

        trace = [
            TraceRecord(
                decision=f"requirements.{r.id}",
                rule_id=f"requirement.{r.id}",
                evidence=r.evidence,
                outcome=r.statement,
            )
            for r in requirements
        ]
        return requirements, trace

    def _topology(
        self, a: AssessmentInput, operating_model: str
    ) -> tuple[TopologyDecision, list[TraceRecord]]:
        if operating_model == "centralized":
            control_plane = "central_shared"
            runtime = "shared_runtime"
        elif operating_model == "decentralized":
            control_plane = "enterprise_policy_only"
            runtime = "domain_runtimes"
        else:
            control_plane = "shared_enterprise_spine"
            runtime = "domain_or_tenant_runtimes"

        isolation = {
            Isolation.SHARED_RBAC: "shared_service",
            Isolation.NAMESPACE: "namespace",
            Isolation.ACCOUNT: "account",
            Isolation.DEDICATED_STACK: "dedicated_stack",
            Isolation.UNKNOWN: "undetermined",
        }[a.nfr.tenant_isolation]

        if a.data.residency == Residency.SINGLE_REGION and (a.nfr.regions or 1) == 1:
            regional = "single_region"
        elif a.data.residency in (Residency.HYBRID, Residency.MULTI_CLOUD):
            regional = "hybrid_or_multicloud"
        else:
            regional = "multi_region"

        modifiers: list[str] = []
        if a.primary_workload in (Workload.CODING, Workload.CUSTOMER_FACING, Workload.MARKETPLACE):
            modifiers.append("gateway_fronted")
        if a.primary_workload == Workload.CODING and a.workload_profile.code_boundary == "vpc_only":
            modifiers.append("private_egress")
        if (
            a.primary_workload == Workload.CUSTOMER_FACING
            and (a.workload_profile.peak_rps or 0) >= 500
        ):
            modifiers.append("autoscaled_edge")
        if a.primary_workload == Workload.MARKETPLACE:
            modifiers.append("brokered_external_edge")
        if a.data.residency in (Residency.COUNTRY_BOUND, Residency.HYBRID, Residency.MULTI_CLOUD):
            modifiers.append("placement_policy")

        result = TopologyDecision(
            control_plane=control_plane,
            runtime_placement=runtime,
            isolation_boundary=isolation,
            regional_model=regional,
            modifiers=modifiers,
        )
        trace = [TraceRecord(
            decision="topology",
            rule_id="topology.ownership_isolation_residency",
            evidence=[
                f"operating_model={operating_model}",
                f"tenant_isolation={a.nfr.tenant_isolation.value}",
                f"residency={a.data.residency.value}",
                f"primary_workload={a.primary_workload.value}",
            ],
            outcome=result.model_dump_json(),
        )]
        return result, trace

    def _components(
        self,
        a: AssessmentInput,
        requirements: list[Requirement],
        topology: TopologyDecision,
    ) -> tuple[list[ComponentDecision], list[TraceRecord]]:
        requirement_ids = {r.id for r in requirements}
        active: dict[str, list[str]] = {
            "identity": ["req-identity"],
            "runtime": ["primary_workload"],
            "observability": ["req-observability"],
            "deployment": ["primary_workload", "current.maturity"],
        }
        if "req-policy" in requirement_ids or "req-approval" in requirement_ids:
            active["gateway"] = ["req-policy" if "req-policy" in requirement_ids else "req-approval"]
            active["policy"] = sorted(requirement_ids & {"req-policy", "req-approval"})
        if a.primary_workload in (Workload.HOSTING, Workload.MARKETPLACE) or len(a.secondary_workloads) > 0:
            active["registry"] = ["primary_workload", "secondary_workloads"]
        if a.primary_workload == Workload.CODING and a.workload_profile.execution_sandbox:
            active["sandbox"] = ["req-code-boundary"]
            active.setdefault("gateway", []).append("req-code-boundary")
            active.setdefault("policy", []).append("req-code-boundary")
        if a.primary_workload == Workload.INTERNAL_COPILOT or "req-sensitive-data" in requirement_ids:
            active["data_access"] = ["req-data-access"] if "req-data-access" in requirement_ids else ["req-sensitive-data"]
        real_regulations = {
            self._normalize_regulation(item)
            for item in a.data.regulations
            if self._normalize_regulation(item) not in ("NONE", "NONE-IDENTIFIED")
        }
        if real_regulations or "req-sensitive-data" in requirement_ids or "req-market-trust" in requirement_ids:
            active["audit"] = ["data.regulations", "req-sensitive-data", "req-market-trust"]
        if "req-multitenancy" in requirement_ids or topology.isolation_boundary in ("account", "dedicated_stack"):
            active["tenant_control"] = ["req-multitenancy", "nfr.tenant_isolation"]
            active.setdefault("gateway", []).append("req-multitenancy")
        if "req-resilience" in requirement_ids:
            active["resilience"] = ["req-resilience"]
        if a.primary_workload == Workload.MARKETPLACE:
            active["metering"] = ["req-market-trust", "workload_profile.billing_model"]

        components: list[ComponentDecision] = []
        for comp_id, activation in active.items():
            catalog = COMPONENTS[comp_id]
            scope = (
                "per_domain" if topology.runtime_placement == "domain_runtimes" and comp_id in {"runtime", "observability", "deployment"}
                else "per_tenant" if topology.isolation_boundary == "dedicated_stack" and comp_id in {"runtime", "data_access"}
                else "shared"
            )
            components.append(ComponentDecision(
                id=comp_id,
                name=catalog["name"],
                layer=catalog["layer"],
                scope=scope,
                activation_requirements=sorted(set(activation)),
                dependencies=[d for d in catalog["dependencies"] if d in active],
                aws_services=catalog["aws"],
            ))
        trace = [
            TraceRecord(
                decision=f"components.{c.id}",
                rule_id=f"component.activate.{c.id}",
                evidence=c.activation_requirements,
                outcome=f"{c.scope}:{c.name}",
            )
            for c in components
        ]
        return components, trace

    def _controls(
        self, a: AssessmentInput, requirements: list[Requirement]
    ) -> tuple[list[ControlDecision], list[TraceRecord]]:
        controls: list[ControlDecision] = [
            ControlDecision(
                id="baseline-identity",
                name="Attributable least-privilege identity",
                source="baseline",
                implementation="IAM roles, short-lived credentials, and workload identity",
                requirement_ids=["req-identity"],
            ),
            ControlDecision(
                id="baseline-observability",
                name="End-to-end decision and tool telemetry",
                source="baseline",
                implementation="Structured traces, metrics, logs, and evaluation records",
                requirement_ids=["req-observability"],
            ),
        ]
        requirement_ids = {r.id for r in requirements}
        if "req-policy" in requirement_ids:
            controls.append(ControlDecision(
                id="action-policy", name="Pre-execution action policy", source="risk",
                implementation="Deny-by-default tool policy with argument validation",
                requirement_ids=["req-policy"],
            ))
        if "req-approval" in requirement_ids:
            controls.append(ControlDecision(
                id="durable-approval", name="Durable human approval", source="risk",
                implementation="Signed approval record, expiry, and idempotency key",
                requirement_ids=["req-approval"],
            ))
        if "req-tenant-isolation" in requirement_ids:
            controls.append(ControlDecision(
                id="tenant-boundary", name="Infrastructure tenant boundary", source="isolation",
                implementation="Separate account or dedicated deployment with tenant-scoped keys",
                requirement_ids=["req-tenant-isolation"],
            ))
        seen = {c.id for c in controls}
        for raw_regime in a.data.regulations:
            regime = self._normalize_regulation(raw_regime)
            for item in REGULATION_CONTROLS.get(regime, []):
                if item["id"] in seen:
                    continue
                seen.add(item["id"])
                controls.append(ControlDecision(
                    id=item["id"],
                    name=item["name"],
                    source=regime,
                    implementation=item["implementation"],
                    requirement_ids=["req-sensitive-data"] if "req-sensitive-data" in requirement_ids else [],
                ))
        trace = [
            TraceRecord(
                decision=f"controls.{c.id}",
                rule_id=f"control.{c.source.lower()}",
                evidence=c.requirement_ids or [f"regulation={c.source}"],
                outcome=c.implementation,
            )
            for c in controls
        ]
        return controls, trace

    def _risks(
        self, a: AssessmentInput, controls: list[ControlDecision]
    ) -> tuple[list[RiskDecision], list[TraceRecord]]:
        control_ids = {c.id for c in controls}
        risks: list[RiskDecision] = []
        impact = a.risk.failure_impact

        def add(risk_id: str, scenario: str, exposure: str, relevant: list[str], owner: Ownership):
            selected = sorted(control_ids.intersection(relevant))
            residual = self._residual_impact(impact, bool(selected))
            risks.append(RiskDecision(
                id=risk_id,
                scenario=scenario,
                inherent=impact,
                exposure=exposure,
                controls=selected,
                residual=residual,
                owner=owner,
                treatment="accept" if residual in (Impact.LOW, Impact.MODERATE) else "mitigate_before_production",
            ))

        if a.risk.autonomy == Autonomy.AUTONOMOUS:
            add(
                "unauthorized-action",
                "An autonomous agent performs an unauthorized or incorrectly scoped action.",
                "autonomous_tool_execution",
                ["action-policy", "durable-approval", "baseline-identity"],
                a.ownership.incident_accountability,
            )
        if a.data.classifications and any(c != DataClass.PUBLIC for c in a.data.classifications):
            add(
                "sensitive-data-disclosure",
                "Model, tool, or trace output discloses sensitive data outside its authorized boundary.",
                "sensitive_data_in_context",
                ["baseline-identity", "tenant-boundary", "hipaa-access", "pci-segmentation"],
                a.ownership.policy_owner,
            )
        if a.primary_workload in (Workload.HOSTING, Workload.CUSTOMER_FACING, Workload.MARKETPLACE):
            add(
                "cross-tenant-access",
                "A request or retrieved context crosses a tenant boundary.",
                a.nfr.tenant_isolation.value,
                ["tenant-boundary", "baseline-identity"],
                a.ownership.runtime_operations_owner,
            )
        if a.primary_workload == Workload.MARKETPLACE:
            add(
                "untrusted-agent-supply-chain",
                "An untrusted publisher distributes a malicious or misleading agent.",
                "third_party_publishers",
                ["action-policy", "baseline-observability", "euai-risk"],
                a.ownership.policy_owner,
            )

        trace = [
            TraceRecord(
                decision=f"risks.{r.id}",
                rule_id=f"risk.scenario.{r.id}",
                evidence=[r.exposure] + r.controls,
                outcome=f"inherent={r.inherent.value};residual={r.residual.value}",
            )
            for r in risks
        ]
        return risks, trace

    def _roadmap(
        self, a: AssessmentInput, components: list[ComponentDecision]
    ) -> tuple[list[RoadmapPhase], list[TraceRecord]]:
        ids = {c.id for c in components}
        current = a.current
        phases: list[RoadmapPhase] = []
        foundation = [x for x in ("identity", "gateway", "policy", "tenant_control", "audit") if x in ids]
        runtime = [x for x in ("runtime", "sandbox", "data_access", "registry") if x in ids]
        operations = [x for x in ("deployment", "observability", "resilience", "metering") if x in ids]

        phases.append(RoadmapPhase(
            id="P0", name="Decisions and control foundations", duration_weeks=(2, 4),
            component_ids=foundation,
            exit_criteria=[
                "Named owners accept the capability ownership matrix",
                "Hard requirements and trust boundaries are approved",
                "Identity, policy, and audit paths pass a threat-model review",
            ],
        ))
        phases.append(RoadmapPhase(
            id="P1", name="Production reference workload", duration_weeks=(4, 8),
            component_ids=runtime,
            exit_criteria=[
                "Primary workload runs through the selected topology",
                "Required controls are enforced and evidenced",
                "Load and failure tests meet stated NFRs",
            ],
            dependencies=["P0"],
        ))
        phases.append(RoadmapPhase(
            id="P2", name="Operationalization and scale", duration_weeks=(4, 8),
            component_ids=operations,
            exit_criteria=[
                "Delivery, observability, incident, and cost ownership are operational",
                "Residual high risks have approved treatment",
                "Secondary workload overlays have go/no-go evidence",
            ],
            dependencies=["P1"],
        ))
        if current.maturity in (Maturity.PRODUCTION, Maturity.SCALED):
            phases[0].duration_weeks = (1, 3)
            phases[1].duration_weeks = (3, 6)
        trace = [TraceRecord(
            decision=f"roadmap.{phase.id}",
            rule_id="roadmap.dependencies_and_current_state",
            evidence=[f"current.maturity={current.maturity.value}"] + phase.component_ids,
            outcome=f"{phase.name}:{phase.duration_weeks[0]}-{phase.duration_weeks[1]} weeks",
        ) for phase in phases]
        return phases, trace

    def _cost(
        self,
        a: AssessmentInput,
        components: list[ComponentDecision],
        topology: TopologyDecision,
    ) -> tuple[CostEstimate, list[TraceRecord]]:
        requests, tokens = self._workload_cost_ranges(a)
        topology_multiplier = {
            "shared_service": 1.0,
            "namespace": 1.15,
            "account": 1.45,
            "dedicated_stack": 1.9,
            "undetermined": 1.0,
        }[topology.isolation_boundary]
        if topology.regional_model == "multi_region":
            topology_multiplier *= 1.6
        elif topology.regional_model == "hybrid_or_multicloud":
            topology_multiplier *= 1.8

        fixed_base = sum(BASE_COMPONENT_MONTHLY[c.id] for c in components)
        capacity_multiplier, capacity_evidence = self._capacity_multiplier(a)
        fixed = fixed_base * topology_multiplier * capacity_multiplier
        line_items = [
            {
                "id": c.id,
                "name": c.name,
                "monthly_base_usd": BASE_COMPONENT_MONTHLY[c.id],
                "scope": c.scope,
                "aws_services": c.aws_services,
            }
            for c in components
        ]

        def scenario(request_count: float, tokens_per_request: float) -> CostScenario:
            model = (
                request_count * tokens_per_request / 1_000_000
                * PLANNING_RATES["blended_model_per_million_tokens"]
            )
            gateway = request_count / 1_000_000 * PLANNING_RATES["gateway_per_million_requests"]
            telemetry = request_count / 1_000_000 * PLANNING_RATES["observability_per_million_events"]
            monthly = round(fixed + model + gateway + telemetry, 2)
            return CostScenario(monthly_usd=monthly, annual_usd=round(monthly * 12, 2))

        estimate = CostEstimate(
            price_catalog_date=PRICE_CATALOG_DATE,
            low=scenario(requests.low, tokens.low),
            base=scenario(requests.expected, tokens.expected),
            high=scenario(requests.high, tokens.high),
            assumptions=[
                "Planning estimate, not an AWS quote",
                f"Topology multiplier={topology_multiplier:.2f}",
                f"Workload capacity multiplier={capacity_multiplier:.2f}",
                f"Blended model rate=${PLANNING_RATES['blended_model_per_million_tokens']}/million tokens",
                "Volume ranges come directly from intake evidence",
            ],
            line_items=line_items,
        )
        trace = [TraceRecord(
            decision="cost",
            rule_id="cost.workload_volume_x_catalog_rates",
            evidence=[
                f"requests={requests.model_dump_json()}",
                f"tokens={tokens.model_dump_json()}",
                f"topology_multiplier={topology_multiplier:.2f}",
                f"capacity_multiplier={capacity_multiplier:.2f}",
                *capacity_evidence,
                f"price_catalog_date={PRICE_CATALOG_DATE}",
            ],
            outcome=estimate.model_dump_json(),
        )]
        return estimate, trace

    def _capacity_multiplier(self, a: AssessmentInput) -> tuple[float, list[str]]:
        p = a.workload_profile
        if a.primary_workload == Workload.CODING:
            sessions = p.concurrent_sessions.expected
            developers = p.developers.expected
            multiplier = max(1.0, sessions / 100, developers / 1000)
            evidence = [f"concurrent_sessions={sessions}", f"developers={developers}"]
        elif a.primary_workload == Workload.INTERNAL_COPILOT:
            users = p.monthly_active_users.expected
            domains = p.data_domains or 0
            multiplier = max(1.0, users / 10_000, domains / 20)
            evidence = [f"monthly_active_users={users}", f"data_domains={domains}"]
        elif a.primary_workload == Workload.HOSTING:
            agents = p.deployed_agents.expected
            tenants = p.tenants.expected
            multiplier = max(1.0, agents / 500, tenants / 25)
            evidence = [f"deployed_agents={agents}", f"tenants={tenants}", f"builder_teams={p.builder_teams}"]
        elif a.primary_workload == Workload.CUSTOMER_FACING:
            peak = p.peak_rps or 0
            tenants = p.tenants.expected
            multiplier = max(1.0, peak / 500, tenants / 250)
            evidence = [f"peak_rps={peak}", f"tenants={tenants}", f"monthly_active_users={p.monthly_active_users.expected}"]
        elif a.primary_workload == Workload.PROCESS_AUTOMATION:
            workflows = p.workflows or 0
            duration = p.average_duration_minutes or 0
            multiplier = max(1.0, workflows / 50, duration / 15)
            evidence = [f"workflows={workflows}", f"average_duration_minutes={duration}", f"exception_rate_pct={p.exception_rate_pct}"]
        else:
            agents = p.listed_agents.expected
            publishers = p.publishers.expected
            multiplier = max(1.0, agents / 500, publishers / 50)
            evidence = [f"listed_agents={agents}", f"publishers={publishers}", f"consumers={p.consumers.expected}"]
        return round(multiplier, 4), evidence

    def _workload_cost_ranges(self, a: AssessmentInput) -> tuple[VolumeRange, VolumeRange]:
        p = a.workload_profile
        if a.primary_workload == Workload.CODING:
            return p.monthly_model_calls, p.tokens_per_call
        if a.primary_workload == Workload.INTERNAL_COPILOT:
            return p.monthly_queries, p.tokens_per_query
        if a.primary_workload in (Workload.HOSTING, Workload.CUSTOMER_FACING):
            return p.monthly_model_calls, p.tokens_per_call
        if a.primary_workload == Workload.PROCESS_AUTOMATION:
            return p.monthly_executions, p.tokens_per_execution
        return p.monthly_transactions, p.tokens_per_transaction

    @staticmethod
    def _residual_impact(inherent: Impact, controlled: bool) -> Impact:
        if not controlled or inherent == Impact.UNKNOWN:
            return inherent
        order = [Impact.LOW, Impact.MODERATE, Impact.HIGH, Impact.SEVERE]
        index = order.index(inherent)
        return order[max(0, index - 1)]

    @staticmethod
    def _normalize_regulation(value: str) -> str:
        normalized = value.strip().upper().replace("_", "-").replace(" ", "-")
        aliases = {
            "PCI": "PCI-DSS",
            "PCIDSS": "PCI-DSS",
            "EU-AI-ACT": "EU-AI-ACT",
            "EU-AIACT": "EU-AI-ACT",
            "FED-RAMP": "FEDRAMP",
            "SOC-2": "SOC2",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _get_path(data: dict, path: str):
        value = data
        for part in path.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(part)
        return value

    @staticmethod
    def _override_value(overrides: list[OverrideRecord], path: str) -> str | None:
        match = next((o for o in reversed(overrides) if o.decision_path == path), None)
        return match.override_value if match else None

    @staticmethod
    def _override_reason(overrides: list[OverrideRecord], path: str) -> str:
        match = next(o for o in reversed(overrides) if o.decision_path == path)
        return f"override by {match.author}: {match.rationale}"

    def _apply_topology_overrides(
        self, topology: TopologyDecision, overrides: list[OverrideRecord]
    ) -> TopologyDecision:
        values = topology.model_dump()
        for key in ("control_plane", "runtime_placement", "isolation_boundary", "regional_model"):
            override = self._override_value(overrides, f"topology.{key}")
            if override:
                values[key] = override
        return TopologyDecision.model_validate(values)

    @staticmethod
    def _validate_overrides(overrides: list[OverrideRecord]) -> None:
        allowed = {
            "operating_model": {"centralized", "federated", "decentralized"},
            "topology.control_plane": {"central_shared", "enterprise_policy_only", "shared_enterprise_spine"},
            "topology.runtime_placement": {"shared_runtime", "domain_runtimes", "domain_or_tenant_runtimes"},
            "topology.isolation_boundary": {"shared_service", "namespace", "account", "dedicated_stack"},
            "topology.regional_model": {"single_region", "multi_region", "hybrid_or_multicloud"},
        }
        for override in overrides:
            values = allowed.get(override.decision_path)
            if values is None:
                raise ValueError(f"Unsupported override path: {override.decision_path}")
            if override.override_value not in values:
                raise ValueError(
                    f"Unsupported value for {override.decision_path}: {override.override_value}"
                )

    @staticmethod
    def _assumptions(a: AssessmentInput) -> list[str]:
        assumptions = [
            "Secondary workloads are roadmap overlays and are not included in primary workload capacity.",
            "AWS mappings are recommendations downstream of provider-neutral architecture decisions.",
        ]
        if a.economics.monthly_budget_usd is None:
            assumptions.append("No monthly budget ceiling was supplied; cost is not budget-validated.")
        if a.economics.target_months is None:
            assumptions.append("No target delivery date was supplied; roadmap durations are dependency-based.")
        return assumptions
