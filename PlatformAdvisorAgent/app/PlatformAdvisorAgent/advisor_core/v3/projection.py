"""Deterministic, JSON-ready frontend projection for advisor_core v3."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Sequence

from .authority import decision_authority_projection
from .assurance import SelectedBundleContext, build_assurance_outputs
from .assurance.models import BundleImplementation
from .deployable import (
    RecommendationState,
    build_deployable_solution,
    compile_deployable_catalog,
)
from .deployable.models import DeployableCatalogRelease
from .engine import evaluate_deployment_feasibility, rank_next_questions
from .question_enrichment import get_answer_label, get_enrichment
from .models import (
    AnswerImpact,
    ArchitectureEdge,
    ArchitectureState,
    ArchitectureWorkspace,
    CatalogRelease,
    DecisionTraceTransition,
    DeploymentFamilyEvaluation,
    QuestionCandidate,
    RequirementChange,
    RequirementConstraint,
    RuleEvaluation,
    RuleOutcome,
    WorkspaceRevision,
    content_hash,
)


PROJECTION_SCHEMA_VERSION = "3.0"
PLANE_ORDER = (
    "experience",
    "access",
    "orchestration",
    "model",
    "tool",
    "execution",
    "knowledge",
    "governance",
    "observability",
)


def _requirement_ref(
    requirement_id: str,
    definitions: dict[str, object],
    constraints: dict[str, RequirementConstraint],
) -> dict[str, object]:
    definition = definitions[requirement_id]
    constraint = constraints.get(requirement_id)
    return {
        "requirement_id": requirement_id,
        "name": definition.name,
        "value": constraint.value if constraint is not None else None,
        "source": constraint.source if constraint is not None else None,
        "assumption": (
            constraint.assumption.model_dump(mode="json")
            if constraint is not None and constraint.assumption is not None
            else None
        ),
    }


def _component_ref(component_id: str, components: dict[str, object]) -> dict[str, str]:
    component = components[component_id]
    return {
        "component_id": component_id,
        "name": component.name,
        "plane": component.plane.value,
    }


def _edge_projection(
    edge: ArchitectureEdge,
    *,
    node_components: dict[str, str],
    components: dict[str, object],
    baseline_edge_ids: set[str],
) -> dict[str, object]:
    source_component_id = node_components[edge.source_instance_id]
    target_component_id = node_components[edge.target_instance_id]
    return {
        "edge_id": edge.edge_id,
        "source": {
            "instance_id": edge.source_instance_id,
            **_component_ref(source_component_id, components),
        },
        "target": {
            "instance_id": edge.target_instance_id,
            **_component_ref(target_component_id, components),
        },
        "relationship": edge.relationship.value,
        "status": (
            "baseline" if edge.edge_id in baseline_edge_ids else "added"
        ),
    }


def _family_reason(
    evaluation: DeploymentFamilyEvaluation,
    *,
    requirements: dict[str, object],
    rules: dict[str, object],
) -> str:
    if evaluation.rejection_rule_ids:
        names = [
            rules[rule_id].name for rule_id in evaluation.rejection_rule_ids
        ]
        return f"Rejected by: {', '.join(names)}."
    if evaluation.blocking_requirement_ids:
        names = [
            requirements[requirement_id].name
            for requirement_id in evaluation.blocking_requirement_ids
        ]
        return f"Unresolved until answered: {', '.join(names)}."
    return "No catalog hard constraint rejects this deployment family."


def _family_projection(
    evaluation: DeploymentFamilyEvaluation,
    *,
    patterns: dict[str, object],
    requirements: dict[str, object],
    constraints: dict[str, RequirementConstraint],
    rules: dict[str, object],
) -> dict[str, object]:
    pattern = patterns[evaluation.pattern_id]
    return {
        "pattern_id": evaluation.pattern_id,
        "name": pattern.name,
        "description": pattern.description,
        "status": evaluation.status.value,
        "reason": _family_reason(
            evaluation,
            requirements=requirements,
            rules=rules,
        ),
        "rejection_rule_ids": list(evaluation.rejection_rule_ids),
        "blocking_requirements": [
            _requirement_ref(requirement_id, requirements, constraints)
            for requirement_id in evaluation.blocking_requirement_ids
        ],
        "rule_evaluations": [
            {
                "evaluation_id": rule_evaluation.evaluation_id,
                "rule_id": rule_evaluation.rule_id,
                "rule_name": rules[rule_evaluation.rule_id].name,
                "authority": rule_evaluation.authority.value,
                "outcome": rule_evaluation.outcome.value,
                "requirements": [
                    _requirement_ref(
                        requirement_id,
                        requirements,
                        constraints,
                    )
                    for requirement_id in rule_evaluation.requirement_ids
                ],
                "unknown_requirement_ids": list(
                    rule_evaluation.unknown_requirement_ids
                ),
                "rationale": rule_evaluation.rationale,
                "evidence_claim_ids": list(
                    rule_evaluation.evidence_claim_ids
                ),
            }
            for rule_evaluation in evaluation.feasibility_rule_evaluations
            if rule_evaluation.outcome is not RuleOutcome.SATISFIES
        ],
    }


def _impact_projection(
    impact: AnswerImpact,
    *,
    components: dict[str, object],
    patterns: dict[str, object],
) -> dict[str, object]:
    def component_refs(component_ids: tuple[str, ...]) -> list[dict[str, str]]:
        return [
            _component_ref(component_id, components)
            for component_id in component_ids
        ]

    def pattern_refs(pattern_ids: tuple[str, ...]) -> list[dict[str, str]]:
        return [
            {
                "pattern_id": pattern_id,
                "name": patterns[pattern_id].name,
            }
            for pattern_id in pattern_ids
        ]

    return {
        "answer": impact.answer,
        "components": {
            "added": component_refs(impact.added_component_ids),
            "removed": component_refs(impact.removed_component_ids),
        },
        "edges": {
            "added_edge_ids": list(impact.added_edge_ids),
            "removed_edge_ids": list(impact.removed_edge_ids),
        },
        "rules": {
            "activated_rule_ids": list(impact.activated_rule_ids),
            "deactivated_rule_ids": list(impact.deactivated_rule_ids),
        },
        "deployment_families": {
            "feasible": pattern_refs(impact.feasible_pattern_ids),
            "rejected": pattern_refs(impact.rejected_pattern_ids),
            "unknown": pattern_refs(impact.unknown_pattern_ids),
        },
    }


def _question_projection(
    question: QuestionCandidate | None,
    *,
    requirements: dict[str, object],
    components: dict[str, object],
    patterns: dict[str, object],
) -> dict[str, object] | None:
    if question is None:
        return None
    definition = requirements[question.requirement_id]
    enrichment = get_enrichment(question.requirement_id)
    return {
        "question_id": question.question_id,
        "requirement_id": question.requirement_id,
        "requirement_name": definition.name,
        "prompt": question.prompt,
        "customer_question": enrichment.get("customer_question") or question.prompt,
        "why_it_matters": enrichment.get("why_it_matters"),
        "candidate_answers": list(question.candidate_answers),
        "answer_enrichments": [
            get_answer_label(question.requirement_id, answer)
            for answer in question.candidate_answers
        ],
        "hard_constraint_risk": question.hard_constraint_risk,
        "information_gain": question.information_gain,
        "candidate_elimination_count": question.candidate_elimination_count,
        "affected_components": [
            _component_ref(component_id, components)
            for component_id in question.affected_component_ids
        ],
        "why_now": question.why_now,
        "answer_impacts": [
            _impact_projection(
                impact,
                components=components,
                patterns=patterns,
            )
            for impact in question.answer_impacts
        ],
    }


def _decision_projection(
    evaluation: RuleEvaluation,
    *,
    rules: dict[str, object],
    requirements: dict[str, object],
    constraints: dict[str, RequirementConstraint],
    components: dict[str, object],
    patterns: dict[str, object],
) -> dict[str, object]:
    rule = rules[evaluation.rule_id]
    return {
        "evaluation_id": evaluation.evaluation_id,
        "rule_id": evaluation.rule_id,
        "rule_name": rule.name,
        "authority": evaluation.authority.value,
        "effect": evaluation.effect.value,
        "requirements": [
            _requirement_ref(requirement_id, requirements, constraints)
            for requirement_id in evaluation.requirement_ids
        ],
        "target_components": [
            _component_ref(component_id, components)
            for component_id in evaluation.target_component_ids
        ],
        "target_patterns": [
            {
                "pattern_id": pattern_id,
                "name": patterns[pattern_id].name,
            }
            for pattern_id in evaluation.target_pattern_ids
        ],
        "rationale": evaluation.rationale,
        "evidence_claim_ids": list(evaluation.evidence_claim_ids),
    }


def _constraint_projection(
    constraint: RequirementConstraint | None,
) -> dict[str, object] | None:
    if constraint is None:
        return None
    return {
        "value": constraint.value,
        "source": constraint.source,
        "recorded_at": constraint.recorded_at.isoformat(),
        "assumption": (
            constraint.assumption.model_dump(mode="json")
            if constraint.assumption is not None
            else None
        ),
    }


def _build_decision_transitions(
    workspace: ArchitectureWorkspace,
) -> tuple[DecisionTraceTransition, ...]:
    transitions = []
    for prior, current in zip(workspace.revisions, workspace.revisions[1:]):
        prior_requirements = {
            constraint.requirement_id: constraint
            for constraint in prior.requirements
        }
        current_requirements = {
            constraint.requirement_id: constraint
            for constraint in current.requirements
        }
        requirement_changes = tuple(
            RequirementChange(
                requirement_id=requirement_id,
                previous=prior_requirements.get(requirement_id),
                current=current_requirements.get(requirement_id),
            )
            for requirement_id in sorted(
                set(prior_requirements) | set(current_requirements)
            )
            if (
                prior_requirements.get(requirement_id)
                != current_requirements.get(requirement_id)
            )
        )
        prior_evaluations = {
            evaluation.rule_id: evaluation
            for evaluation in prior.rule_evaluations
        }
        current_evaluations = {
            evaluation.rule_id: evaluation
            for evaluation in current.rule_evaluations
        }
        activated = tuple(
            current_evaluations[rule_id]
            for rule_id in current.delta.activated_rule_ids
        )
        deactivated = tuple(
            prior_evaluations[rule_id]
            for rule_id in current.delta.deactivated_rule_ids
        )
        transition_id = (
            f"trace:r-{prior.revision_number}-to-r-{current.revision_number}"
        )
        hash_payload = {
            "transition_id": transition_id,
            "prior_revision_id": prior.revision_id,
            "prior_revision_number": prior.revision_number,
            "prior_state_hash": prior.state_hash,
            "current_revision_id": current.revision_id,
            "current_revision_number": current.revision_number,
            "current_state_hash": current.state_hash,
            "requirement_changes": [
                change.model_dump(mode="json")
                for change in requirement_changes
            ],
            "activated_rule_evaluations": [
                evaluation.model_dump(mode="json")
                for evaluation in activated
            ],
            "deactivated_rule_evaluations": [
                evaluation.model_dump(mode="json")
                for evaluation in deactivated
            ],
            "architecture_delta": current.delta.model_dump(mode="json"),
        }
        transitions.append(DecisionTraceTransition(
            **hash_payload,
            transition_hash=content_hash(hash_payload),
        ))
    return tuple(transitions)


def _revision_ref(revision: WorkspaceRevision) -> dict[str, object]:
    return {
        "revision_id": revision.revision_id,
        "revision_number": revision.revision_number,
        "parent_revision_id": revision.parent_revision_id,
        "state_hash": revision.state_hash,
        "created_at": revision.created_at.isoformat(),
    }


def _trace_edge_projection(
    edge: ArchitectureEdge,
    architecture: ArchitectureState,
    *,
    components: dict[str, object],
) -> dict[str, object]:
    node_components = {
        node.instance_id: node.component_id for node in architecture.nodes
    }
    return {
        "edge_id": edge.edge_id,
        "source": {
            "instance_id": edge.source_instance_id,
            **_component_ref(
                node_components[edge.source_instance_id],
                components,
            ),
        },
        "target": {
            "instance_id": edge.target_instance_id,
            **_component_ref(
                node_components[edge.target_instance_id],
                components,
            ),
        },
        "relationship": edge.relationship.value,
    }


def _decision_history_projection(
    workspace: ArchitectureWorkspace,
    *,
    requirements: dict[str, object],
    components: dict[str, object],
    patterns: dict[str, object],
    rules: dict[str, object],
) -> dict[str, object]:
    revisions = {revision.revision_id: revision for revision in workspace.revisions}
    transitions = []
    for transition in _build_decision_transitions(workspace):
        prior = revisions[transition.prior_revision_id]
        current = revisions[transition.current_revision_id]
        prior_constraints = {
            constraint.requirement_id: constraint
            for constraint in prior.requirements
        }
        current_constraints = {
            constraint.requirement_id: constraint
            for constraint in current.requirements
        }
        prior_edges = {edge.edge_id: edge for edge in prior.architecture.edges}
        current_edges = {
            edge.edge_id: edge for edge in current.architecture.edges
        }
        transition_projection = {
            "transition_id": transition.transition_id,
            "prior_revision": _revision_ref(prior),
            "current_revision": _revision_ref(current),
            "requirement_changes": [
                {
                    "requirement_id": change.requirement_id,
                    "name": requirements[change.requirement_id].name,
                    "change_type": (
                        "added"
                        if change.previous is None
                        else "removed"
                        if change.current is None
                        else "updated"
                    ),
                    "previous": _constraint_projection(change.previous),
                    "current": _constraint_projection(change.current),
                }
                for change in transition.requirement_changes
            ],
            "rules": {
                "activated": [
                    _decision_projection(
                        evaluation,
                        rules=rules,
                        requirements=requirements,
                        constraints=current_constraints,
                        components=components,
                        patterns=patterns,
                    )
                    for evaluation in transition.activated_rule_evaluations
                ],
                "deactivated": [
                    _decision_projection(
                        evaluation,
                        rules=rules,
                        requirements=requirements,
                        constraints=prior_constraints,
                        components=components,
                        patterns=patterns,
                    )
                    for evaluation in transition.deactivated_rule_evaluations
                ],
            },
            "architecture_delta": {
                "components": {
                    "added": [
                        _component_ref(component_id, components)
                        for component_id
                        in transition.architecture_delta.added_component_ids
                    ],
                    "removed": [
                        _component_ref(component_id, components)
                        for component_id
                        in transition.architecture_delta.removed_component_ids
                    ],
                },
                "edges": {
                    "added": [
                        _trace_edge_projection(
                            current_edges[edge_id],
                            current.architecture,
                            components=components,
                        )
                        for edge_id in transition.architecture_delta.added_edge_ids
                    ],
                    "removed": [
                        _trace_edge_projection(
                            prior_edges[edge_id],
                            prior.architecture,
                            components=components,
                        )
                        for edge_id
                        in transition.architecture_delta.removed_edge_ids
                    ],
                },
            },
            "transition_hash": transition.transition_hash,
        }
        transitions.append(transition_projection)

    history: dict[str, object] = {
        "initial_revision": _revision_ref(workspace.revisions[0]),
        "current_revision": _revision_ref(workspace.revisions[-1]),
        "transitions": transitions,
    }
    history["history_hash"] = content_hash(history)
    return history


def _evidence_projection(
    referenced_claim_ids: set[str],
    *,
    claims: dict[str, object],
    sources: dict[str, object],
) -> list[dict[str, object]]:
    """Resolve referenced claim ids into a flat, cited evidence block.

    Deterministic: sorted by claim id. Only claims actually referenced by the
    current decision trace or its components are surfaced, so the frontend can
    render an auditable citation next to each decision. Unknown ids are skipped
    rather than raising, since catalog compilation already guarantees every
    referenced claim exists.
    """
    resolved: list[dict[str, object]] = []
    for claim_id in sorted(referenced_claim_ids):
        claim = claims.get(claim_id)
        if claim is None:
            continue
        source = sources.get(claim.source_id)
        resolved.append({
            "claim_id": claim.id,
            "statement": claim.statement,
            "review_status": claim.review_status.value,
            "effective_on": claim.effective_on.isoformat(),
            "source_locator": claim.source_locator,
            "source_id": claim.source_id,
            "source_title": source.title if source is not None else None,
            "source_uri": source.uri if source is not None else None,
            "source_publisher": source.publisher if source is not None else None,
        })
    return resolved


def build_frontend_projection(
    workspace: ArchitectureWorkspace,
    catalog: CatalogRelease,
    *,
    deployable_catalog: DeployableCatalogRelease | None = None,
) -> dict[str, object]:
    """Project a validated workspace into a deterministic frontend contract."""

    initial = workspace.revisions[0]
    current = workspace.revisions[-1]
    feasibility = evaluate_deployment_feasibility(workspace, catalog)
    # Production supplies the deployable catalog from the same verified release.
    # Source compilation remains available only for explicit local/test callers.
    resolved_deployable_catalog = (
        deployable_catalog or compile_deployable_catalog(catalog)
    )
    capability_rules = resolved_deployable_catalog.capability_rules
    questions = rank_next_questions(workspace, catalog, extra_capability_rules=capability_rules)

    requirements = {
        requirement.id: requirement for requirement in catalog.requirements
    }
    constraints = {
        constraint.requirement_id: constraint
        for constraint in current.requirements
    }
    components = {
        component.id: component for component in catalog.components
    }
    patterns = {pattern.id: pattern for pattern in catalog.patterns}
    rules = {rule.id: rule for rule in catalog.rules}
    claims = {claim.id: claim for claim in catalog.evidence_claims}
    sources = {source.id: source for source in catalog.evidence_sources}
    deployable = build_deployable_solution(
        current,
        catalog,
        resolved_deployable_catalog,
    )
    automatically_selected_candidate = next(
        (
            candidate
            for candidate in deployable.candidates
            if (
                deployable.recommendation.state
                is RecommendationState.RECOMMENDED
                and candidate.bundle_id
                == deployable.recommendation.candidate_id
            )
        ),
        None,
    )
    selected_bundle = (
        SelectedBundleContext(
            bundle_id=automatically_selected_candidate.bundle_id,
            implementations=tuple(
                BundleImplementation(
                    component_id=selection.component_id,
                    offering_id=selection.service_variant_id,
                    provider=selection.provider_class.value.upper(),
                    product=selection.service_name,
                )
                for selection in automatically_selected_candidate.selections
            ),
        )
        if automatically_selected_candidate is not None
        else None
    )
    assurance = build_assurance_outputs(
        workspace,
        catalog,
        selected_bundle,
        as_of=catalog.validated_as_of,
        deployable_catalog=resolved_deployable_catalog,
    )

    baseline_component_ids = {
        node.component_id for node in initial.architecture.nodes
    }
    baseline_edge_ids = {
        edge.edge_id for edge in initial.architecture.edges
    }
    node_components = {
        node.instance_id: node.component_id
        for node in current.architecture.nodes
    }
    current_component_ids = set(node_components.values())
    referenced_claim_ids: set[str] = set()
    for evaluation in current.rule_evaluations:
        referenced_claim_ids.update(evaluation.evidence_claim_ids)
    for component_id in current_component_ids:
        component = components.get(component_id)
        if component is not None:
            referenced_claim_ids.update(component.evidence_claim_ids)
    pattern = patterns[current.architecture.pattern_id]
    requirement_projection = [
        {
            "requirement_id": requirement_id,
            "name": definition.name,
            "description": definition.description,
            "customer_question": get_enrichment(requirement_id).get("customer_question"),
            "why_it_matters": get_enrichment(requirement_id).get("why_it_matters"),
            "value_type": definition.value_type.value,
            "candidate_answers": (
                list(definition.allowed_values)
                if definition.allowed_values
                else [True, False]
                if definition.value_type.value == "boolean"
                else []
            ),
            "required": definition.required,
            "status": (
                "unanswered"
                if requirement_id not in constraints
                else (
                    "unknown"
                    if constraints[requirement_id].value is None
                    else (
                        "assumed"
                        if constraints[requirement_id].source == "assumption"
                        else "answered"
                    )
                )
            ),
            "value": (
                constraints[requirement_id].value
                if requirement_id in constraints
                else None
            ),
            "source": (
                constraints[requirement_id].source
                if requirement_id in constraints
                else None
            ),
            "assumption": (
                constraints[requirement_id].assumption.model_dump(mode="json")
                if (
                    requirement_id in constraints
                    and constraints[requirement_id].assumption is not None
                )
                else None
            ),
        }
        for requirement_id, definition in sorted(requirements.items())
    ]

    planes = []
    for plane_id in PLANE_ORDER:
        plane_components = [
            {
                "instance_id": node.instance_id,
                "component_id": node.component_id,
                "name": components[node.component_id].name,
                "description": components[node.component_id].description,
                "kind": components[node.component_id].kind.value,
                "status": (
                    "baseline"
                    if node.component_id in baseline_component_ids
                    else "added"
                ),
            }
            for node in current.architecture.nodes
            if components[node.component_id].plane.value == plane_id
        ]
        planes.append({
            "plane_id": plane_id,
            "name": plane_id.replace("_", " ").title(),
            "components": plane_components,
        })

    payload: dict[str, object] = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "decision_authority": decision_authority_projection(),
        "workspace": {
            "workspace_id": workspace.workspace_id,
            "current_revision_id": workspace.current_revision_id,
        },
        "catalog": {
            "catalog_release_id": catalog.id,
            "version": catalog.version,
            "content_hash": catalog.content_hash,
            "validated_as_of": catalog.validated_as_of.isoformat(),
        },
        "revision": {
            "revision_id": current.revision_id,
            "revision_number": current.revision_number,
            "parent_revision_id": current.parent_revision_id,
            "created_at": current.created_at.isoformat(),
            "state_hash": current.state_hash,
        },
        "requirements": requirement_projection,
        "assumptions": [
            {
                "requirement_id": item["requirement_id"],
                "name": item["name"],
                "value": item["value"],
                **item["assumption"],
            }
            for item in requirement_projection
            if item["assumption"] is not None
        ],
        "architecture": {
            "pattern": {
                "pattern_id": pattern.id,
                "name": pattern.name,
                "description": pattern.description,
            },
            "summary": {
                "baseline_component_count": len(baseline_component_ids),
                "current_component_count": len(current_component_ids),
                "added_component_count": len(
                    current_component_ids - baseline_component_ids
                ),
                "baseline_edge_count": len(baseline_edge_ids),
                "current_edge_count": len(current.architecture.edges),
                "added_edge_count": len(
                    {
                        edge.edge_id for edge in current.architecture.edges
                    }
                    - baseline_edge_ids
                ),
            },
            "planes": planes,
            "edges": [
                _edge_projection(
                    edge,
                    node_components=node_components,
                    components=components,
                    baseline_edge_ids=baseline_edge_ids,
                )
                for edge in current.architecture.edges
            ],
        },
        "deployment_families": [
            _family_projection(
                evaluation,
                patterns=patterns,
                requirements=requirements,
                constraints=constraints,
                rules=rules,
            )
            for evaluation in feasibility.family_evaluations
        ],
        "deployable_solution": deployable.model_dump(mode="json"),
        "assurance": assurance.model_dump(mode="json"),
        "next_question": _question_projection(
            questions[0] if questions else None,
            requirements=requirements,
            components=components,
            patterns=patterns,
        ),
        "decision_trace": [
            _decision_projection(
                evaluation,
                rules=rules,
                requirements=requirements,
                constraints=constraints,
                components=components,
                patterns=patterns,
            )
            for evaluation in current.rule_evaluations
        ],
        "decision_history": _decision_history_projection(
            workspace,
            requirements=requirements,
            components=components,
            patterns=patterns,
            rules=rules,
        ),
        "evidence": _evidence_projection(
            referenced_claim_ids,
            claims=claims,
            sources=sources,
        ),
    }
    payload["projection_hash"] = content_hash(payload)
    return payload


def write_projection(
    projection: dict[str, object],
    output: Path | None = None,
) -> str:
    """Serialize a projection once for byte-stable CLI and file output."""

    serialized = json.dumps(
        projection,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ) + "\n"
    if output is not None:
        output.write_text(serialized, encoding="utf-8")
    return serialized


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Build the v3 coding-platform frontend projection."
    )
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=date.today(),
        help="Evidence validation date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the deterministic JSON projection to this path.",
    )
    args = parser.parse_args(argv)

    from .demo import build_demo_workspace

    catalog, workspace = build_demo_workspace(args.as_of)
    serialized = write_projection(
        build_frontend_projection(workspace, catalog),
        args.output,
    )
    if args.output is None:
        print(serialized, end="")


if __name__ == "__main__":
    main()
