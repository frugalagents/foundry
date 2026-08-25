from __future__ import annotations

import re
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from workspace_state import reconcile_workspace_state

SCHEMA_VERSION = "2026-08-25.architecture-case.v1"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseFact(_StrictModel):
    id: str
    statement: str
    value: Any | None = None
    status: str = "confirmed"
    source: str = "customer"


class CaseAssumptionOption(_StrictModel):
    id: str
    label: str
    prompt: str = ""


class CaseAssumption(_StrictModel):
    id: str
    title: str
    assumed: str
    why: str = ""
    impact: str = ""
    confidence: str = ""
    options: list[CaseAssumptionOption] = Field(default_factory=list)


class CaseQuestion(_StrictModel):
    id: str
    text: str
    why_it_matters: str = ""
    blocking: bool = True
    decision_domain: str = ""
    status: str = "open"
    answer: str = ""
    source: str = "engine"


class EvidenceRef(_StrictModel):
    id: str
    kind: str
    locator: str
    summary: str = ""
    status: str = "available"


class CaseDecision(_StrictModel):
    id: str
    statement: str
    rationale: str = ""
    status: str = "selected"
    source: str = "workspace"
    alternatives_considered: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    owner: str = ""
    open_dependency: str = ""


class CaseRisk(_StrictModel):
    id: str
    risk: str
    mitigation: str = ""
    severity: str = ""
    category: str = ""
    source: str = "workspace"


class ArchitectureComponent(_StrictModel):
    id: str
    label: str
    layer: str = ""
    kind: str = ""
    sublabel: str = ""
    path_role: str = "primary"


class ArchitectureRelationship(_StrictModel):
    id: str
    source: str
    target: str
    relationship_type: str = "flow"
    color: str = ""


class RolloutItem(_StrictModel):
    phase: str
    outcome: str


class CaseArtifacts(_StrictModel):
    blueprint_markdown: str = ""
    executive_summary: str = ""
    recommendation_memo: str = ""
    architecture_narrative: str = ""
    diagram_summary: str = ""
    rollout: list[RolloutItem] = Field(default_factory=list)


class CaseObservability(_StrictModel):
    workspace_updated_at: str = ""
    canvas_updated_at: str = ""
    source_artifacts: list[str] = Field(default_factory=list)
    active_decision_path: str = ""
    decision_focus: str = ""
    candidate_option_paths: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    artifact_status: dict[str, Any] = Field(default_factory=dict)


class CaseEvaluation(_StrictModel):
    blocking_question_count: int = 0
    decision_count: int = 0
    evidence_ref_count: int = 0
    has_blueprint: bool = False
    has_architecture_snapshot: bool = False
    missing_artifacts: list[str] = Field(default_factory=list)


class ArchitectureCase(_StrictModel):
    schema_version: str = SCHEMA_VERSION
    case_id: str
    revision: int = 1
    okf_release_id: str = ""
    stage: str = "discovery"
    current_recommendation: str = ""
    operating_model: str = "undecided"
    facts: list[CaseFact] = Field(default_factory=list)
    assumptions: list[CaseAssumption] = Field(default_factory=list)
    open_questions: list[CaseQuestion] = Field(default_factory=list)
    decisions: list[CaseDecision] = Field(default_factory=list)
    risks: list[CaseRisk] = Field(default_factory=list)
    architecture_components: list[ArchitectureComponent] = Field(default_factory=list)
    relationships: list[ArchitectureRelationship] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    artifacts: CaseArtifacts = Field(default_factory=CaseArtifacts)
    observability: CaseObservability = Field(default_factory=CaseObservability)
    evaluation: CaseEvaluation = Field(default_factory=CaseEvaluation)


def build_architecture_case(
    *,
    case_id: str,
    workspace: Mapping[str, Any] | None,
    canvas_snapshot: Mapping[str, Any] | None = None,
    revision: int = 1,
    okf_release_id: str = "",
) -> ArchitectureCase:
    reconciled = reconcile_workspace_state(dict(workspace or {}))
    canvas = _normalize_canvas_snapshot(canvas_snapshot)
    evidence_refs = _build_evidence_refs(reconciled, canvas)
    evidence_ids = {item.id for item in evidence_refs}
    decisions = _build_decisions(reconciled, canvas, evidence_ids)
    questions = _build_open_questions(reconciled)
    components = _build_components(canvas)
    relationships = _build_relationships(canvas)
    artifacts = _build_artifacts(reconciled, canvas)
    observability = _build_observability(reconciled, canvas)

    return ArchitectureCase(
        case_id=case_id,
        revision=max(1, int(revision)),
        okf_release_id=str(okf_release_id or "").strip(),
        stage=str(reconciled.get("stage") or "discovery").strip() or "discovery",
        current_recommendation=str(reconciled.get("recommendation") or "").strip(),
        operating_model=str(reconciled.get("operating_model") or "undecided").strip() or "undecided",
        facts=_build_facts(reconciled),
        assumptions=_build_assumptions(reconciled),
        open_questions=questions,
        decisions=decisions,
        risks=_build_risks(reconciled, canvas),
        architecture_components=components,
        relationships=relationships,
        evidence_refs=evidence_refs,
        artifacts=artifacts,
        observability=observability,
        evaluation=_build_evaluation(
            questions=questions,
            decisions=decisions,
            evidence_refs=evidence_refs,
            artifacts=artifacts,
            components=components,
        ),
    )


def build_architecture_case_payload(**kwargs: Any) -> dict[str, Any]:
    return build_architecture_case(**kwargs).model_dump(mode="json")


def _build_facts(workspace: Mapping[str, Any]) -> list[CaseFact]:
    facts: list[CaseFact] = []
    seen_ids: set[str] = set()
    seen_statements: set[str] = set()
    structured = _confirmed_structured_facts(workspace)

    for index, item in enumerate(structured):
        if not isinstance(item, Mapping):
            continue
        fact_id = str(item.get("key") or "").strip() or f"fact-{index + 1}"
        statement = str(item.get("fact_text") or _render_fact_statement(fact_id, item.get("value"))).strip()
        if not statement:
            continue
        normalized = statement.lower()
        if fact_id in seen_ids or normalized in seen_statements:
            continue
        facts.append(
            CaseFact(
                id=fact_id,
                statement=statement,
                value=item.get("value"),
                status=str(item.get("status") or "confirmed").strip() or "confirmed",
                source=str(item.get("source") or "customer").strip() or "customer",
            )
        )
        seen_ids.add(fact_id)
        seen_statements.add(normalized)

    for index, item in enumerate(_string_list(workspace.get("facts"))):
        normalized = item.lower()
        if normalized in seen_statements:
            continue
        fact_id = _slug(f"fact-{item}", default=f"fact-{index + 1}")
        if fact_id in seen_ids:
            fact_id = f"{fact_id}-{index + 1}"
        facts.append(CaseFact(id=fact_id, statement=item))
        seen_ids.add(fact_id)
        seen_statements.add(normalized)

    return facts


def _build_assumptions(workspace: Mapping[str, Any]) -> list[CaseAssumption]:
    assumptions: list[CaseAssumption] = []
    raw_items = workspace.get("assumptions") if isinstance(workspace.get("assumptions"), list) else []
    for index, item in enumerate(raw_items):
        if not isinstance(item, Mapping):
            continue
        title = str(item.get("title") or "").strip()
        assumed = str(item.get("assumed") or "").strip()
        if not title or not assumed:
            continue
        options: list[CaseAssumptionOption] = []
        raw_options = item.get("options") if isinstance(item.get("options"), list) else []
        for option_index, option in enumerate(raw_options):
            if not isinstance(option, Mapping):
                continue
            label = str(option.get("label") or "").strip()
            if not label:
                continue
            options.append(
                CaseAssumptionOption(
                    id=str(option.get("id") or _slug(label, default=f"option-{option_index + 1}")),
                    label=label,
                    prompt=str(option.get("prompt") or "").strip(),
                )
            )
        assumptions.append(
            CaseAssumption(
                id=str(item.get("id") or _slug(title, default=f"assumption-{index + 1}")),
                title=title,
                assumed=assumed,
                why=str(item.get("why") or "").strip(),
                impact=str(item.get("impact") or "").strip(),
                confidence=str(item.get("confidence") or "").strip(),
                options=options,
            )
        )
    return assumptions


def _build_open_questions(workspace: Mapping[str, Any]) -> list[CaseQuestion]:
    questions: list[CaseQuestion] = []
    raw_items = workspace.get("question_state") if isinstance(workspace.get("question_state"), list) else []
    for index, item in enumerate(raw_items):
        if not isinstance(item, Mapping):
            continue
        status = str(item.get("status") or "open").strip().lower()
        if status != "open":
            continue
        text = str(item.get("text") or item.get("question") or "").strip()
        if not text:
            continue
        questions.append(
            CaseQuestion(
                id=str(item.get("id") or _slug(text, default=f"question-{index + 1}")),
                text=text,
                why_it_matters=str(item.get("why_it_matters") or "").strip(),
                blocking=bool(item.get("blocking", True)),
                decision_domain=str(item.get("decision_domain") or "").strip(),
                status=status,
                answer=str(item.get("answer") or "").strip(),
                source=str(item.get("source") or "engine").strip() or "engine",
            )
        )
    return questions


def _build_decisions(
    workspace: Mapping[str, Any],
    canvas: Mapping[str, Any],
    evidence_ids: set[str],
) -> list[CaseDecision]:
    decisions: list[CaseDecision] = []
    seen_statements: set[str] = set()
    for index, statement in enumerate(_string_list(workspace.get("decisions"))):
        if statement.lower() in seen_statements:
            continue
        decisions.append(
            CaseDecision(
                id=_slug(statement, default=f"decision-workspace-{index + 1}"),
                statement=statement,
                source="workspace",
                evidence_refs=_decision_evidence_refs(evidence_ids),
            )
        )
        seen_statements.add(statement.lower())

    if decisions:
        return decisions

    advisory_case = workspace.get("advisory_case") if isinstance(workspace.get("advisory_case"), Mapping) else {}
    raw_decisions = advisory_case.get("decisions") if isinstance(advisory_case.get("decisions"), list) else []
    for index, item in enumerate(raw_decisions):
        if not isinstance(item, Mapping):
            continue
        statement = str(item.get("statement") or "").strip()
        if not statement or statement.lower() in seen_statements:
            continue
        decisions.append(
            CaseDecision(
                id=_slug(str(item.get("id") or statement), default=f"decision-{index + 1}"),
                statement=statement,
                rationale=str(item.get("why") or "").strip(),
                source="advisory_case",
                alternatives_considered=_string_list(item.get("options_considered")) or _string_list(item.get("tradeoffs_accepted")),
                evidence_refs=_decision_evidence_refs(evidence_ids),
                owner=str(item.get("owner") or "").strip(),
                open_dependency=str(item.get("open_dependency") or "").strip(),
            )
        )
        seen_statements.add(statement.lower())

    if decisions:
        return decisions

    architecture_artifact = canvas.get("architecture_artifact") if isinstance(canvas.get("architecture_artifact"), Mapping) else {}
    raw_arch_decisions = architecture_artifact.get("decisions") if isinstance(architecture_artifact.get("decisions"), list) else []
    for index, item in enumerate(raw_arch_decisions):
        if not isinstance(item, Mapping):
            continue
        statement = str(item.get("decision") or "").strip()
        if not statement or statement.lower() in seen_statements:
            continue
        decisions.append(
            CaseDecision(
                id=_slug(statement, default=f"decision-arch-{index + 1}"),
                statement=statement,
                rationale=str(item.get("why") or "").strip(),
                source="architecture_artifact",
                alternatives_considered=_string_list(item.get("alternatives_rejected")),
                evidence_refs=_decision_evidence_refs(evidence_ids),
            )
        )
        seen_statements.add(statement.lower())

    return decisions


def _build_risks(workspace: Mapping[str, Any], canvas: Mapping[str, Any]) -> list[CaseRisk]:
    risks: list[CaseRisk] = []
    seen: set[str] = set()
    for index, risk in enumerate(_string_list(workspace.get("risks"))):
        if risk.lower() in seen:
            continue
        risks.append(CaseRisk(id=_slug(risk, default=f"risk-workspace-{index + 1}"), risk=risk))
        seen.add(risk.lower())

    if risks:
        return risks

    advisory_case = workspace.get("advisory_case") if isinstance(workspace.get("advisory_case"), Mapping) else {}
    raw_risks = advisory_case.get("risks") if isinstance(advisory_case.get("risks"), list) else []
    for index, item in enumerate(raw_risks):
        if not isinstance(item, Mapping):
            continue
        risk = str(item.get("risk") or "").strip()
        if not risk or risk.lower() in seen:
            continue
        risks.append(
            CaseRisk(
                id=_slug(risk, default=f"risk-{index + 1}"),
                risk=risk,
                mitigation=str(item.get("mitigation") or "").strip(),
                severity=str(item.get("severity") or "").strip(),
                category=str(item.get("category") or "").strip(),
                source="advisory_case",
            )
        )
        seen.add(risk.lower())

    if risks:
        return risks

    architecture_artifact = canvas.get("architecture_artifact") if isinstance(canvas.get("architecture_artifact"), Mapping) else {}
    raw_arch_risks = architecture_artifact.get("risks") if isinstance(architecture_artifact.get("risks"), list) else []
    for index, item in enumerate(raw_arch_risks):
        if not isinstance(item, Mapping):
            continue
        risk = str(item.get("risk") or "").strip()
        if not risk or risk.lower() in seen:
            continue
        risks.append(
            CaseRisk(
                id=_slug(risk, default=f"risk-arch-{index + 1}"),
                risk=risk,
                mitigation=str(item.get("mitigation") or "").strip(),
                source="architecture_artifact",
            )
        )
        seen.add(risk.lower())

    return risks


def _build_components(canvas: Mapping[str, Any]) -> list[ArchitectureComponent]:
    nodes = canvas.get("nodes") if isinstance(canvas.get("nodes"), list) else []
    components: list[ArchitectureComponent] = []
    for item in nodes:
        if not isinstance(item, Mapping):
            continue
        component_id = str(item.get("id") or "").strip()
        label = str(item.get("label") or "").strip()
        if not component_id or not label:
            continue
        components.append(
            ArchitectureComponent(
                id=component_id,
                label=label,
                layer=str(item.get("layer") or "").strip(),
                kind=str(item.get("kind") or "").strip(),
                sublabel=str(item.get("sublabel") or "").strip(),
                path_role=str(item.get("path_role") or "primary").strip() or "primary",
            )
        )
    return components


def _build_relationships(canvas: Mapping[str, Any]) -> list[ArchitectureRelationship]:
    edges = canvas.get("edges") if isinstance(canvas.get("edges"), list) else []
    relationships: list[ArchitectureRelationship] = []
    for item in edges:
        if not isinstance(item, Mapping):
            continue
        source = str(item.get("source") or "").strip()
        target = str(item.get("target") or "").strip()
        if not source or not target:
            continue
        relationships.append(
            ArchitectureRelationship(
                id=str(item.get("id") or f"{source}->{target}"),
                source=source,
                target=target,
                relationship_type="control_overlay" if bool(item.get("dashed")) else "flow",
                color=str(item.get("color") or "").strip(),
            )
        )
    return relationships


def _build_evidence_refs(workspace: Mapping[str, Any], canvas: Mapping[str, Any]) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    seen: set[str] = set()
    traversal_state = workspace.get("traversal_state") if isinstance(workspace.get("traversal_state"), Mapping) else {}
    structured = _confirmed_structured_facts(workspace)

    for item in structured:
        if not isinstance(item, Mapping):
            continue
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        ref_id = f"fact:{key}"
        if ref_id in seen:
            continue
        refs.append(
            EvidenceRef(
                id=ref_id,
                kind="fact",
                locator=f"traversal_state.structured_facts.{key}",
                summary=str(item.get("fact_text") or _render_fact_statement(key, item.get("value"))).strip(),
                status=str(item.get("status") or "confirmed").strip() or "confirmed",
            )
        )
        seen.add(ref_id)

    active_decision = traversal_state.get("active_slice") if isinstance(traversal_state.get("active_slice"), Mapping) else {}
    if not active_decision:
        active_decision = traversal_state.get("active_decision") if isinstance(traversal_state.get("active_decision"), Mapping) else {}
    active_path = str(active_decision.get("path") or "").strip()
    if active_path:
        ref_id = f"okf:active:{active_path}"
        refs.append(
            EvidenceRef(
                id=ref_id,
                kind="okf_node",
                locator=active_path,
                summary=str(active_decision.get("title") or active_path).strip(),
                status="selected",
            )
        )
        seen.add(ref_id)

    candidate_options = traversal_state.get("candidate_options") if isinstance(traversal_state.get("candidate_options"), list) else []
    for item in candidate_options:
        if not isinstance(item, Mapping):
            continue
        path = str(item.get("path") or "").strip()
        if not path:
            continue
        ref_id = f"okf:candidate:{path}"
        if ref_id in seen:
            continue
        refs.append(
            EvidenceRef(
                id=ref_id,
                kind="okf_candidate",
                locator=path,
                summary=str(item.get("title") or path).strip(),
                status=str(item.get("position") or "candidate").strip() or "candidate",
            )
        )
        seen.add(ref_id)

    architecture_artifact = canvas.get("architecture_artifact") if isinstance(canvas.get("architecture_artifact"), Mapping) else {}
    summary = str(architecture_artifact.get("executive_summary") or "").strip()
    if summary:
        refs.append(
            EvidenceRef(
                id="artifact:architecture-summary",
                kind="artifact",
                locator="canvas.architecture_artifact.executive_summary",
                summary=summary,
                status="derived",
            )
        )

    return refs


def _confirmed_structured_facts(workspace: Mapping[str, Any]) -> list[dict[str, Any]]:
    traversal_state = workspace.get("traversal_state") if isinstance(workspace.get("traversal_state"), Mapping) else {}
    structured = (
        traversal_state.get("customer_confirmed_facts")
        if isinstance(traversal_state.get("customer_confirmed_facts"), list)
        else traversal_state.get("structured_facts")
        if isinstance(traversal_state.get("structured_facts"), list)
        else []
    )
    confirmed: list[dict[str, Any]] = []
    for item in structured:
        if not isinstance(item, Mapping):
            continue
        source = str(item.get("source") or "").strip().lower()
        if source and source not in {"customer", "customer_confirmed", "explicit_constraint", "operating_model"}:
            continue
        confirmed.append(dict(item))
    return confirmed


def _build_artifacts(workspace: Mapping[str, Any], canvas: Mapping[str, Any]) -> CaseArtifacts:
    advisory_case = workspace.get("advisory_case") if isinstance(workspace.get("advisory_case"), Mapping) else {}
    output_pack = advisory_case.get("output_pack") if isinstance(advisory_case.get("output_pack"), Mapping) else {}
    architecture_artifact = canvas.get("architecture_artifact") if isinstance(canvas.get("architecture_artifact"), Mapping) else {}

    rollout_items: list[RolloutItem] = []
    advisory_rollout = output_pack.get("rollout_30_90_180") if isinstance(output_pack.get("rollout_30_90_180"), list) else []
    if advisory_rollout:
        for item in advisory_rollout:
            if not isinstance(item, Mapping):
                continue
            phase = str(item.get("horizon") or "").strip()
            outcome = str(item.get("outcome") or "").strip()
            if phase and outcome:
                rollout_items.append(RolloutItem(phase=phase, outcome=outcome))
    else:
        artifact_rollout = architecture_artifact.get("rollout") if isinstance(architecture_artifact.get("rollout"), list) else []
        for item in artifact_rollout:
            if not isinstance(item, Mapping):
                continue
            phase = str(item.get("phase") or "").strip()
            outcome = str(item.get("outcome") or "").strip()
            if phase and outcome:
                rollout_items.append(RolloutItem(phase=phase, outcome=outcome))

    return CaseArtifacts(
        blueprint_markdown=str(workspace.get("blueprint_markdown") or "").strip(),
        executive_summary=str(output_pack.get("executive_summary") or "").strip(),
        recommendation_memo=str(output_pack.get("recommendation_memo") or "").strip(),
        architecture_narrative=str(output_pack.get("architecture_narrative") or "").strip(),
        diagram_summary=str(architecture_artifact.get("executive_summary") or "").strip(),
        rollout=rollout_items,
    )


def _build_observability(workspace: Mapping[str, Any], canvas: Mapping[str, Any]) -> CaseObservability:
    traversal_state = workspace.get("traversal_state") if isinstance(workspace.get("traversal_state"), Mapping) else {}
    active_decision = traversal_state.get("active_slice") if isinstance(traversal_state.get("active_slice"), Mapping) else {}
    if not active_decision:
        active_decision = traversal_state.get("active_decision") if isinstance(traversal_state.get("active_decision"), Mapping) else {}
    candidate_options = traversal_state.get("candidate_options") if isinstance(traversal_state.get("candidate_options"), list) else []
    missing_evidence = traversal_state.get("missing_evidence") if isinstance(traversal_state.get("missing_evidence"), list) else []
    source_artifacts = ["workspace"]
    if _has_content(workspace.get("advisory_case")):
        source_artifacts.append("workspace.advisory_case")
    if _has_content(workspace.get("blueprint_markdown")):
        source_artifacts.append("workspace.blueprint_markdown")
    if _has_content(canvas.get("architecture_artifact")) or _has_content(canvas.get("nodes")):
        source_artifacts.append("canvas.architecture_artifact")
    missing_evidence_texts: list[str] = []
    for item in missing_evidence:
        if isinstance(item, Mapping):
            text = str(item.get("question") or item.get("text") or "").strip()
        else:
            text = str(item).strip()
        if text:
            missing_evidence_texts.append(text)

    return CaseObservability(
        workspace_updated_at=str(workspace.get("updated_at") or "").strip(),
        canvas_updated_at=str(canvas.get("updated_at") or "").strip(),
        source_artifacts=source_artifacts,
        active_decision_path=str(active_decision.get("path") or "").strip(),
        decision_focus=str(traversal_state.get("decision_focus") or "").strip(),
        candidate_option_paths=[
            str(item.get("path") or "").strip()
            for item in candidate_options
            if isinstance(item, Mapping) and str(item.get("path") or "").strip()
        ],
        missing_evidence=missing_evidence_texts,
        artifact_status=dict(workspace.get("artifact_status") or {}),
    )


def _build_evaluation(
    *,
    questions: list[CaseQuestion],
    decisions: list[CaseDecision],
    evidence_refs: list[EvidenceRef],
    artifacts: CaseArtifacts,
    components: list[ArchitectureComponent],
) -> CaseEvaluation:
    missing_artifacts: list[str] = []
    if not artifacts.blueprint_markdown:
        missing_artifacts.append("blueprint")
    if not components:
        missing_artifacts.append("architecture_snapshot")
    if not decisions:
        missing_artifacts.append("decisions")
    if not evidence_refs:
        missing_artifacts.append("evidence")

    return CaseEvaluation(
        blocking_question_count=sum(1 for item in questions if item.blocking),
        decision_count=len(decisions),
        evidence_ref_count=len(evidence_refs),
        has_blueprint=bool(artifacts.blueprint_markdown),
        has_architecture_snapshot=bool(components),
        missing_artifacts=missing_artifacts,
    )


def _normalize_canvas_snapshot(snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    snapshot = snapshot or {}
    return {
        "nodes": snapshot.get("nodes") if isinstance(snapshot.get("nodes"), list) else [],
        "edges": snapshot.get("edges") if isinstance(snapshot.get("edges"), list) else [],
        "architecture_artifact": snapshot.get("architecture_artifact") if isinstance(snapshot.get("architecture_artifact"), Mapping) else {},
        "updated_at": str(snapshot.get("updated_at") or "").strip(),
    }


def _decision_evidence_refs(evidence_ids: set[str]) -> list[str]:
    ordered = [
        evidence_id
        for evidence_id in sorted(evidence_ids)
        if evidence_id.startswith("okf:active:") or evidence_id.startswith("fact:")
    ]
    return ordered[:4]


def _render_fact_statement(key: str, value: Any) -> str:
    label = key.replace("_", " ").strip()
    if isinstance(value, list):
        rendered = ", ".join(str(item).strip() for item in value if str(item).strip())
        return f"{label}: {rendered}".strip()
    if value is True:
        return label
    if value in (False, None, ""):
        return label
    return f"{label}: {value}".strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [re.sub(r"\s+", " ", str(item).strip()) for item in value if str(item).strip()]


def _slug(value: str, *, default: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or default


def _has_content(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return any(_has_content(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_content(item) for item in value)
    return bool(value)
