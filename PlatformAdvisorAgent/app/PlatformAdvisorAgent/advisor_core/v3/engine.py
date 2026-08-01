"""Pure progressive architecture engine for the v3 workspace."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import (
    AnswerImpact,
    ArchitectureDelta,
    ArchitectureEdge,
    ArchitectureNode,
    ArchitectureState,
    ArchitectureWorkspace,
    CatalogRelease,
    DecisionRule,
    DeploymentFamilyEvaluation,
    DeploymentFeasibilityAssessment,
    FeasibilityRuleEvaluation,
    FeasibilityStatus,
    PatternRole,
    QuestionCandidate,
    RequirementConstraint,
    RequirementDefinition,
    RequirementOperator,
    RequirementPatch,
    RequirementValue,
    RequirementValueType,
    RuleOutcome,
    RulePredicate,
    RuleEvaluation,
    RuleEffect,
    WorkspaceRevision,
    content_hash,
)


class RevisionConflictError(ValueError):
    """Raised when a patch was created from an obsolete workspace revision."""


class ArchitectureConflictError(ValueError):
    """Raised when hard component rules produce an invalid architecture."""


_COMMON_FEASIBILITY_REQUIREMENT_IDS = frozenset({
    "requirement:approved-package-registries",
    "requirement:concurrent-agent-tasks",
    "requirement:developer-count",
    "requirement:enterprise-identity",
    "requirement:execution-placement",
    "requirement:private-connectivity",
    "requirement:restricted-egress",
    "requirement:runtime-isolation",
    "requirement:source-control",
})

_FAMILY_FEASIBILITY_REQUIREMENT_IDS = {
    "pattern:persistent-remote-workspace": frozenset({
        "requirement:long-running-workspaces",
    }),
}

_FAMILY_RULE_COVERAGE = {
    "pattern:developer-local": frozenset({
        "requirement:concurrent-agent-tasks",
        "requirement:execution-placement",
        "requirement:runtime-isolation",
    }),
    "pattern:vendor-ephemeral": frozenset({
        "requirement:execution-placement",
        "requirement:private-connectivity",
        "requirement:runtime-isolation",
    }),
    "pattern:managed-customer-execution": frozenset({
        "requirement:execution-placement",
        "requirement:runtime-isolation",
    }),
    "pattern:persistent-remote-workspace": frozenset({
        "requirement:execution-placement",
        "requirement:long-running-workspaces",
        "requirement:runtime-isolation",
    }),
    "pattern:self-hosted-container": frozenset({
        "requirement:execution-placement",
        "requirement:runtime-isolation",
    }),
    "pattern:self-hosted-kubernetes": frozenset({
        "requirement:execution-placement",
        "requirement:runtime-isolation",
    }),
}


def _matches(actual: Any, operator: RequirementOperator, expected: Any) -> bool:
    if actual is None:
        return False
    if operator is RequirementOperator.EQUALS:
        return actual == expected
    if operator is RequirementOperator.NOT_EQUALS:
        return actual != expected
    if operator is RequirementOperator.IN:
        return actual in expected
    if operator is RequirementOperator.NOT_IN:
        return actual not in expected
    if operator is RequirementOperator.GREATER_THAN:
        return actual > expected
    if operator is RequirementOperator.GREATER_THAN_OR_EQUAL:
        return actual >= expected
    if operator is RequirementOperator.LESS_THAN:
        return actual < expected
    if operator is RequirementOperator.LESS_THAN_OR_EQUAL:
        return actual <= expected
    if operator is RequirementOperator.CONTAINS:
        return expected in actual
    raise ValueError(f"unsupported requirement operator: {operator}")


def _validate_requirement_constraint(
    constraint: RequirementConstraint,
    catalog: CatalogRelease,
) -> None:
    definitions = {
        requirement.id: requirement for requirement in catalog.requirements
    }
    definition = definitions.get(constraint.requirement_id)
    if definition is None:
        raise ValueError(
            f"unknown requirement in patch: {constraint.requirement_id}"
        )

    value = constraint.value
    if value is None:
        return
    valid = {
        RequirementValueType.BOOLEAN: lambda item: isinstance(item, bool),
        RequirementValueType.INTEGER: lambda item: (
            isinstance(item, int) and not isinstance(item, bool)
        ),
        RequirementValueType.NUMBER: lambda item: (
            isinstance(item, (int, float)) and not isinstance(item, bool)
        ),
        RequirementValueType.STRING: lambda item: isinstance(item, str),
        RequirementValueType.STRING_SET: lambda item: (
            isinstance(item, tuple)
            and all(isinstance(member, str) for member in item)
        ),
    }[definition.value_type](value)
    if not valid:
        raise ValueError(
            f"requirement {constraint.requirement_id} expects "
            f"{definition.value_type.value}, got {type(value).__name__}"
        )
    if definition.allowed_values and value not in definition.allowed_values:
        raise ValueError(
            f"requirement {constraint.requirement_id} must be one of "
            f"{definition.allowed_values}"
        )


def _rule_matches(
    rule: DecisionRule,
    requirements: dict[str, RequirementConstraint],
) -> bool:
    return _predicates_match(rule.when, requirements)


def _predicates_match(
    predicates: tuple[RulePredicate, ...],
    requirements: dict[str, RequirementConstraint],
) -> bool:
    return all(
        predicate.requirement_id in requirements
        and _matches(
            requirements[predicate.requirement_id].value,
            predicate.operator,
            predicate.value,
        )
        for predicate in predicates
    )


def _active_rules(
    catalog: CatalogRelease,
    requirements: dict[str, RequirementConstraint],
) -> tuple[DecisionRule, ...]:
    """Activate matching rules only after their rule dependencies are active."""

    active: dict[str, DecisionRule] = {}
    pending = list(catalog.rules)
    while pending:
        next_pending: list[DecisionRule] = []
        progressed = False
        for rule in pending:
            if not _rule_matches(rule, requirements):
                continue
            if not all(
                dependency_id in active
                for dependency_id in rule.depends_on_rule_ids
            ):
                next_pending.append(rule)
                continue
            active[rule.id] = rule
            progressed = True
        if not progressed:
            break
        pending = next_pending
    return tuple(active[rule_id] for rule_id in sorted(active))


def _applicable_requirements(
    catalog: CatalogRelease,
    requirements: dict[str, RequirementConstraint],
) -> dict[str, RequirementConstraint]:
    """Keep captured child answers dormant until their prerequisites apply."""

    definitions = {
        requirement.id: requirement for requirement in catalog.requirements
    }
    applicability: dict[str, bool] = {}

    def applies(requirement_id: str, visiting: set[str]) -> bool:
        if requirement_id in applicability:
            return applicability[requirement_id]
        if requirement_id in visiting:
            raise ValueError(
                f"requirement applicability cycle includes {requirement_id}"
            )
        definition = definitions[requirement_id]
        if not definition.ask_when:
            applicability[requirement_id] = True
            return True

        visiting.add(requirement_id)
        prerequisites = {
            predicate.requirement_id: requirements[predicate.requirement_id]
            for predicate in definition.ask_when
            if (
                predicate.requirement_id in requirements
                and applies(predicate.requirement_id, visiting)
            )
        }
        visiting.remove(requirement_id)
        applicability[requirement_id] = _predicates_match(
            definition.ask_when,
            prerequisites,
        )
        return applicability[requirement_id]

    return {
        requirement_id: constraint
        for requirement_id, constraint in requirements.items()
        if applies(requirement_id, set())
    }


def _dependency_closure(
    catalog: CatalogRelease,
    component_ids: set[str],
) -> set[str]:
    components = {component.id: component for component in catalog.components}
    pending = list(component_ids)
    while pending:
        component_id = pending.pop()
        component = components.get(component_id)
        if component is None:
            raise ValueError(f"unknown component in architecture: {component_id}")
        for dependency_id in component.dependency_ids:
            if dependency_id not in component_ids:
                component_ids.add(dependency_id)
                pending.append(dependency_id)
    return component_ids


def _node_id(component_id: str) -> str:
    return f"node:{component_id.split(':', 1)[1]}"


def _edge_id(component_id: str, dependency_id: str) -> str:
    component = component_id.split(":", 1)[1]
    dependency = dependency_id.split(":", 1)[1]
    return f"edge:{component}--depends-on--{dependency}"


def _build_architecture_state(
    catalog: CatalogRelease,
    pattern_id: str,
    component_ids: set[str],
) -> ArchitectureState:
    components = {component.id: component for component in catalog.components}
    nodes = tuple(
        ArchitectureNode(
            instance_id=_node_id(component_id),
            component_id=component_id,
        )
        for component_id in sorted(component_ids)
    )
    edges = tuple(
        ArchitectureEdge(
            edge_id=_edge_id(component_id, dependency_id),
            source_instance_id=_node_id(component_id),
            target_instance_id=_node_id(dependency_id),
        )
        for component_id in sorted(component_ids)
        for dependency_id in components[component_id].dependency_ids
        if dependency_id in component_ids
    )
    return ArchitectureState(pattern_id=pattern_id, nodes=nodes, edges=edges)


def _rule_evaluations(
    rules: tuple[DecisionRule, ...],
) -> tuple[RuleEvaluation, ...]:
    return tuple(
        RuleEvaluation(
            evaluation_id=f"evaluation:{rule.id.split(':', 1)[1]}",
            rule_id=rule.id,
            effect=rule.effect,
            requirement_ids=tuple(
                predicate.requirement_id for predicate in rule.when
            ),
            target_component_ids=rule.target_component_ids,
            target_pattern_ids=rule.target_pattern_ids,
            evidence_claim_ids=rule.evidence_claim_ids,
            rationale=rule.description,
        )
        for rule in rules
    )


def _derive_state(
    catalog: CatalogRelease,
    pattern_id: str,
    requirements: dict[str, RequirementConstraint],
) -> tuple[ArchitectureState, tuple[RuleEvaluation, ...]]:
    patterns = {pattern.id: pattern for pattern in catalog.patterns}
    pattern = patterns.get(pattern_id)
    if pattern is None:
        raise ValueError(f"unknown architecture pattern: {pattern_id}")

    component_ids = set(pattern.component_ids)
    applicable_requirements = _applicable_requirements(catalog, requirements)
    activated_rules = _active_rules(catalog, applicable_requirements)
    excluded_component_ids: set[str] = set()
    for rule in activated_rules:
        if rule.effect in (RuleEffect.REQUIRE, RuleEffect.RECOMMEND):
            component_ids.update(rule.target_component_ids)
        elif rule.effect is RuleEffect.EXCLUDE:
            excluded_component_ids.update(rule.target_component_ids)

    component_ids.difference_update(excluded_component_ids)
    component_ids = _dependency_closure(catalog, component_ids)
    conflicts = component_ids & excluded_component_ids
    if conflicts:
        raise ArchitectureConflictError(
            "hard component rules exclude required dependencies: "
            f"{', '.join(sorted(conflicts))}"
        )
    state = _build_architecture_state(
        catalog,
        pattern_id,
        component_ids,
    )
    return state, _rule_evaluations(activated_rules)


def _architecture_delta(
    previous: ArchitectureState,
    current: ArchitectureState,
    previous_evaluations: tuple[RuleEvaluation, ...],
    current_evaluations: tuple[RuleEvaluation, ...],
) -> ArchitectureDelta:
    old_components = {node.component_id for node in previous.nodes}
    new_components = {node.component_id for node in current.nodes}
    old_edges = {edge.edge_id for edge in previous.edges}
    new_edges = {edge.edge_id for edge in current.edges}
    old_rules = {evaluation.rule_id for evaluation in previous_evaluations}
    new_rules = {evaluation.rule_id for evaluation in current_evaluations}
    return ArchitectureDelta(
        added_component_ids=tuple(new_components - old_components),
        removed_component_ids=tuple(old_components - new_components),
        added_edge_ids=tuple(new_edges - old_edges),
        removed_edge_ids=tuple(old_edges - new_edges),
        activated_rule_ids=tuple(new_rules - old_rules),
        deactivated_rule_ids=tuple(old_rules - new_rules),
    )


def _state_hash(
    requirements: tuple[RequirementConstraint, ...],
    architecture: ArchitectureState,
    catalog_content_hash: str,
) -> str:
    return content_hash({
        "catalog_content_hash": catalog_content_hash,
        "requirements": [
            {
                "requirement_id": requirement.requirement_id,
                "value": requirement.value,
                "source": requirement.source,
            }
            for requirement in requirements
        ],
        "architecture": architecture.model_dump(mode="json"),
    })


def validate_workspace_revision(
    revision: WorkspaceRevision,
    catalog: CatalogRelease,
) -> None:
    """Re-derive a revision from its pinned inputs before downstream use."""

    if (
        revision.catalog_release_id != catalog.id
        or revision.catalog_release_version != catalog.version
        or revision.catalog_content_hash != catalog.content_hash
    ):
        raise ValueError("workspace catalog pin does not match supplied catalog")

    requirements = {
        requirement.requirement_id: requirement
        for requirement in revision.requirements
    }
    architecture, evaluations = _derive_state(
        catalog,
        revision.architecture.pattern_id,
        requirements,
    )
    if architecture != revision.architecture:
        raise ValueError("workspace architecture does not match pinned inputs")
    if evaluations != revision.rule_evaluations:
        raise ValueError("workspace rule evaluations do not match pinned inputs")
    expected_hash = _state_hash(
        revision.requirements,
        revision.architecture,
        catalog.content_hash,
    )
    if expected_hash != revision.state_hash:
        raise ValueError("workspace state hash does not match pinned inputs")


def _evaluate_exclusion_rule(
    rule: DecisionRule,
    pattern_id: str,
    requirements: dict[str, RequirementConstraint],
) -> FeasibilityRuleEvaluation:
    unknown_requirement_ids: set[str] = set()
    has_non_match = False
    for predicate in rule.when:
        constraint = requirements.get(predicate.requirement_id)
        if constraint is None or constraint.value is None:
            unknown_requirement_ids.add(predicate.requirement_id)
            continue
        if not _matches(
            constraint.value,
            predicate.operator,
            predicate.value,
        ):
            has_non_match = True

    if has_non_match:
        outcome = RuleOutcome.SATISFIES
        unknown_requirement_ids.clear()
    elif unknown_requirement_ids:
        outcome = RuleOutcome.UNKNOWN
    else:
        outcome = RuleOutcome.VIOLATES

    rule_slug = rule.id.split(":", 1)[1]
    pattern_slug = pattern_id.split(":", 1)[1]
    return FeasibilityRuleEvaluation(
        evaluation_id=f"evaluation:{rule_slug}--{pattern_slug}",
        rule_id=rule.id,
        pattern_id=pattern_id,
        outcome=outcome,
        requirement_ids=tuple(
            predicate.requirement_id for predicate in rule.when
        ),
        unknown_requirement_ids=tuple(unknown_requirement_ids),
        evidence_claim_ids=rule.evidence_claim_ids,
        rationale=rule.description,
    )


def _requirement_applies(
    requirement_id: str,
    definitions: dict[str, RequirementDefinition],
    requirements: dict[str, RequirementConstraint],
    cache: dict[str, bool],
) -> bool:
    if requirement_id in cache:
        return cache[requirement_id]
    definition = definitions[requirement_id]
    if not definition.ask_when:
        cache[requirement_id] = True
        return True

    for predicate in definition.ask_when:
        if not _requirement_applies(
            predicate.requirement_id,
            definitions,
            requirements,
            cache,
        ):
            cache[requirement_id] = False
            return False
        constraint = requirements.get(predicate.requirement_id)
        if (
            constraint is None
            or constraint.value is None
            or not _matches(
                constraint.value,
                predicate.operator,
                predicate.value,
            )
        ):
            cache[requirement_id] = False
            return False

    cache[requirement_id] = True
    return True


def _unresolved_feasibility_requirements(
    catalog: CatalogRelease,
    pattern_id: str,
    requirements: dict[str, RequirementConstraint],
) -> tuple[str, ...]:
    material_ids = (
        _COMMON_FEASIBILITY_REQUIREMENT_IDS
        | _FAMILY_FEASIBILITY_REQUIREMENT_IDS.get(pattern_id, frozenset())
    )
    definitions = {
        requirement.id: requirement for requirement in catalog.requirements
    }
    missing_definitions = material_ids - definitions.keys()
    if missing_definitions:
        raise ValueError(
            "catalog is missing material feasibility requirements: "
            f"{', '.join(sorted(missing_definitions))}"
        )

    applicability: dict[str, bool] = {}
    return tuple(sorted(
        requirement_id
        for requirement_id in material_ids
        if (
            _requirement_applies(
                requirement_id,
                definitions,
                requirements,
                applicability,
            )
            and (
                requirement_id not in requirements
                or requirements[requirement_id].value is None
            )
        )
    ))


def _deployment_family_evaluations(
    catalog: CatalogRelease,
    requirements: dict[str, RequirementConstraint],
) -> tuple[DeploymentFamilyEvaluation, ...]:
    applicable_requirements = _applicable_requirements(catalog, requirements)
    family_patterns = tuple(
        pattern
        for pattern in catalog.patterns
        if pattern.role is PatternRole.DEPLOYMENT_FAMILY
    )
    if not family_patterns:
        raise ValueError("catalog contains no deployment-family patterns")

    hard_rules = tuple(
        rule
        for rule in catalog.rules
        if (
            rule.effect is RuleEffect.EXCLUDE
            and rule.target_pattern_ids
        )
    )
    evaluations: list[DeploymentFamilyEvaluation] = []
    for pattern in family_patterns:
        pattern_rules = tuple(
            rule
            for rule in hard_rules
            if pattern.id in rule.target_pattern_ids
        )
        if not pattern_rules:
            raise ValueError(
                f"deployment family {pattern.id} has no hard-rule coverage"
            )
        covered_requirement_ids = {
            predicate.requirement_id
            for rule in pattern_rules
            for predicate in rule.when
        }
        missing_rule_coverage = (
            _FAMILY_RULE_COVERAGE.get(pattern.id, frozenset())
            - covered_requirement_ids
        )
        if missing_rule_coverage:
            raise ValueError(
                f"deployment family {pattern.id} is missing hard-rule "
                "coverage for material requirements: "
                f"{', '.join(sorted(missing_rule_coverage))}"
            )
        architecture, active_evaluations = _derive_state(
            catalog,
            pattern.id,
            requirements,
        )
        rule_evaluations = tuple(
            _evaluate_exclusion_rule(
                rule,
                pattern.id,
                applicable_requirements,
            )
            for rule in pattern_rules
        )
        rejection_rule_ids = tuple(
            evaluation.rule_id
            for evaluation in rule_evaluations
            if evaluation.outcome is RuleOutcome.VIOLATES
        )
        if rejection_rule_ids:
            status = FeasibilityStatus.REJECTED
            blocking_requirement_ids: tuple[str, ...] = ()
        else:
            blocking_requirement_ids = _unresolved_feasibility_requirements(
                catalog,
                pattern.id,
                requirements,
            )
            status = (
                FeasibilityStatus.UNKNOWN
                if blocking_requirement_ids
                else FeasibilityStatus.FEASIBLE
            )
        evaluations.append(DeploymentFamilyEvaluation(
            pattern_id=pattern.id,
            status=status,
            architecture=architecture,
            component_rule_evaluations=tuple(
                evaluation
                for evaluation in active_evaluations
                if evaluation.target_component_ids
            ),
            feasibility_rule_evaluations=rule_evaluations,
            rejection_rule_ids=rejection_rule_ids,
            blocking_requirement_ids=blocking_requirement_ids,
        ))
    return tuple(evaluations)


def evaluate_deployment_feasibility(
    workspace: ArchitectureWorkspace,
    catalog: CatalogRelease,
) -> DeploymentFeasibilityAssessment:
    """Evaluate background deployment families without replacing the baseline."""

    current = workspace.revisions[-1]
    validate_workspace_revision(current, catalog)
    logical_patterns = [
        pattern
        for pattern in catalog.patterns
        if pattern.role is PatternRole.LOGICAL_REFERENCE
    ]
    if len(logical_patterns) != 1:
        raise ValueError("catalog requires exactly one logical-reference pattern")
    if current.architecture.pattern_id != logical_patterns[0].id:
        raise ValueError(
            "workspace architecture must remain on the logical reference"
        )
    family_evaluations = evaluate_revision_deployment_families(
        current,
        catalog,
    )
    hash_payload = {
        "baseline_pattern_id": current.architecture.pattern_id,
        "workspace_revision_id": current.revision_id,
        "catalog_release_id": catalog.id,
        "catalog_release_version": catalog.version,
        "catalog_content_hash": catalog.content_hash,
        "family_evaluations": [
            evaluation.model_dump(mode="json")
            for evaluation in family_evaluations
        ],
    }
    return DeploymentFeasibilityAssessment(
        **hash_payload,
        result_hash=content_hash(hash_payload),
    )


def evaluate_revision_deployment_families(
    revision: WorkspaceRevision,
    catalog: CatalogRelease,
) -> tuple[DeploymentFamilyEvaluation, ...]:
    """Evaluate deployment families for one validated logical revision."""

    validate_workspace_revision(revision, catalog)
    logical_patterns = [
        pattern
        for pattern in catalog.patterns
        if pattern.role is PatternRole.LOGICAL_REFERENCE
    ]
    if len(logical_patterns) != 1:
        raise ValueError("catalog requires exactly one logical-reference pattern")
    if revision.architecture.pattern_id != logical_patterns[0].id:
        raise ValueError(
            "workspace architecture must remain on the logical reference"
        )
    requirements = {
        requirement.requirement_id: requirement
        for requirement in revision.requirements
    }
    return _deployment_family_evaluations(catalog, requirements)


def initialize_workspace(
    catalog: CatalogRelease,
    *,
    workspace_id: str,
    created_at: datetime,
    pattern_id: str = "pattern:logical-reference",
) -> ArchitectureWorkspace:
    architecture, evaluations = _derive_state(catalog, pattern_id, {})
    state_hash = _state_hash((), architecture, catalog.content_hash)
    revision_hash = content_hash({
        "catalog_content_hash": catalog.content_hash,
        "revision_number": 1,
        "state_hash": state_hash,
    })
    revision = WorkspaceRevision(
        revision_id=f"revision:r-{revision_hash.split(':', 1)[1][:20]}",
        revision_number=1,
        catalog_release_id=catalog.id,
        catalog_release_version=catalog.version,
        catalog_content_hash=catalog.content_hash,
        requirements=(),
        architecture=architecture,
        rule_evaluations=evaluations,
        delta=ArchitectureDelta(
            activated_rule_ids=tuple(
                evaluation.rule_id for evaluation in evaluations
            )
        ),
        created_at=created_at,
        state_hash=state_hash,
    )
    return ArchitectureWorkspace(
        workspace_id=workspace_id,
        current_revision_id=revision.revision_id,
        revisions=(revision,),
    )


def apply_requirement_patch(
    workspace: ArchitectureWorkspace,
    patch: RequirementPatch,
    catalog: CatalogRelease,
    *,
    created_at: datetime,
) -> ArchitectureWorkspace:
    current = workspace.revisions[-1]
    if patch.base_revision_number != current.revision_number:
        raise RevisionConflictError(
            f"patch base revision {patch.base_revision_number} does not match "
            f"current revision {current.revision_number}"
        )
    validate_workspace_revision(current, catalog)
    for constraint in patch.changes:
        _validate_requirement_constraint(constraint, catalog)

    requirements = {
        requirement.requirement_id: requirement
        for requirement in current.requirements
    }
    requirements.update({
        requirement.requirement_id: requirement
        for requirement in patch.changes
    })
    ordered_requirements = tuple(
        requirements[requirement_id]
        for requirement_id in sorted(requirements)
    )
    current_requirement_map = {
        requirement.requirement_id: requirement
        for requirement in current.requirements
    }
    _, previous_evaluations = _derive_state(
        catalog,
        current.architecture.pattern_id,
        current_requirement_map,
    )
    architecture, evaluations = _derive_state(
        catalog,
        current.architecture.pattern_id,
        requirements,
    )
    delta = _architecture_delta(
        current.architecture,
        architecture,
        previous_evaluations,
        evaluations,
    )
    digest = _state_hash(
        ordered_requirements,
        architecture,
        catalog.content_hash,
    )
    revision_digest = content_hash({
        "parent_revision_id": current.revision_id,
        "revision_number": current.revision_number + 1,
        "patch_id": patch.patch_id,
        "state_hash": digest,
    })
    revision = WorkspaceRevision(
        revision_id=f"revision:r-{revision_digest.split(':', 1)[1][:20]}",
        revision_number=current.revision_number + 1,
        parent_revision_id=current.revision_id,
        catalog_release_id=catalog.id,
        catalog_release_version=catalog.version,
        catalog_content_hash=catalog.content_hash,
        requirements=ordered_requirements,
        architecture=architecture,
        rule_evaluations=evaluations,
        delta=delta,
        created_at=created_at,
        state_hash=digest,
    )
    return ArchitectureWorkspace(
        workspace_id=workspace.workspace_id,
        current_revision_id=revision.revision_id,
        revisions=workspace.revisions + (revision,),
    )


def rank_next_questions(
    workspace: ArchitectureWorkspace,
    catalog: CatalogRelease,
) -> tuple[QuestionCandidate, ...]:
    current = workspace.revisions[-1]
    validate_workspace_revision(current, catalog)
    answered = {
        requirement.requirement_id for requirement in current.requirements
    }
    requirement_by_id = {
        requirement.id: requirement for requirement in catalog.requirements
    }
    hard_risk: dict[str, bool] = {}
    for rule in catalog.rules:
        for predicate in rule.when:
            if rule.effect in (RuleEffect.REQUIRE, RuleEffect.EXCLUDE):
                hard_risk[predicate.requirement_id] = True

    current_requirements = {
        requirement.requirement_id: requirement
        for requirement in current.requirements
    }
    current_evaluations = current.rule_evaluations
    current_family_evaluations = _deployment_family_evaluations(
        catalog,
        current_requirements,
    )
    current_rejected_patterns = {
        evaluation.pattern_id
        for evaluation in current_family_evaluations
        if evaluation.status is FeasibilityStatus.REJECTED
    }
    candidates = []
    for requirement_id, definition in requirement_by_id.items():
        if requirement_id in answered:
            continue
        if definition.ask_when and not _predicates_match(
            definition.ask_when,
            current_requirements,
        ):
            continue
        risk = hard_risk.get(requirement_id, False)
        candidate_answers = _candidate_answers(definition, catalog)
        answer_impacts = []
        affected_components: set[str] = set()
        distinct_outcomes: set[str] = set()
        maximum_elimination_count = 0
        for answer in candidate_answers:
            hypothetical_requirements = dict(current_requirements)
            hypothetical_requirements[requirement_id] = RequirementConstraint(
                requirement_id=requirement_id,
                value=answer,
                source="derived",
                recorded_at=current.created_at,
            )
            architecture, evaluations = _derive_state(
                catalog,
                current.architecture.pattern_id,
                hypothetical_requirements,
            )
            delta = _architecture_delta(
                current.architecture,
                architecture,
                current_evaluations,
                evaluations,
            )
            family_evaluations = _deployment_family_evaluations(
                catalog,
                hypothetical_requirements,
            )
            feasible_pattern_ids = tuple(
                evaluation.pattern_id
                for evaluation in family_evaluations
                if evaluation.status is FeasibilityStatus.FEASIBLE
            )
            rejected_pattern_ids = tuple(
                evaluation.pattern_id
                for evaluation in family_evaluations
                if evaluation.status is FeasibilityStatus.REJECTED
            )
            unknown_pattern_ids = tuple(
                evaluation.pattern_id
                for evaluation in family_evaluations
                if evaluation.status is FeasibilityStatus.UNKNOWN
            )
            maximum_elimination_count = max(
                maximum_elimination_count,
                len(
                    set(rejected_pattern_ids)
                    - current_rejected_patterns
                ),
            )
            impact = AnswerImpact(
                answer=answer,
                **delta.model_dump(mode="python"),
                feasible_pattern_ids=feasible_pattern_ids,
                rejected_pattern_ids=rejected_pattern_ids,
                unknown_pattern_ids=unknown_pattern_ids,
            )
            answer_impacts.append(impact)
            affected_components.update(impact.added_component_ids)
            affected_components.update(impact.removed_component_ids)
            distinct_outcomes.add(content_hash({
                "added_components": impact.added_component_ids,
                "removed_components": impact.removed_component_ids,
                "added_edges": impact.added_edge_ids,
                "removed_edges": impact.removed_edge_ids,
                "activated_rules": impact.activated_rule_ids,
                "deactivated_rules": impact.deactivated_rule_ids,
                "feasible_patterns": impact.feasible_pattern_ids,
                "rejected_patterns": impact.rejected_pattern_ids,
                "unknown_patterns": impact.unknown_pattern_ids,
            }))
        if len(distinct_outcomes) <= 1 and not definition.required:
            continue
        impact_count = len(affected_components)
        outcome_count = len(distinct_outcomes)
        component_by_id = {
            component.id: component for component in catalog.components
        }
        plane_weight = max(
            (
                {
                    "access": 30,
                    "governance": 30,
                    "execution": 20,
                    "orchestration": 20,
                    "model": 20,
                    "tool": 10,
                    "knowledge": 10,
                    "observability": 10,
                    "experience": 5,
                }[component_by_id[component_id].plane.value]
                for component_id in affected_components
            ),
            default=0,
        )
        candidates.append(QuestionCandidate(
            question_id=f"question:{requirement_id.split(':', 1)[1]}",
            requirement_id=requirement_id,
            prompt=definition.description,
            candidate_answers=candidate_answers,
            candidate_elimination_count=maximum_elimination_count,
            affected_component_ids=tuple(affected_components),
            answer_impacts=tuple(answer_impacts),
            hard_constraint_risk=risk,
            information_gain=float(
                impact_count * 10
                + outcome_count * 25
                + maximum_elimination_count * 20
                + plane_weight
                + (100 if risk else 0)
            ),
            why_now=(
                f"This answer produces {outcome_count} distinct baseline "
                f"outcomes across {impact_count} components, can eliminate "
                f"{maximum_elimination_count} deployment families, and can "
                "change a hard constraint."
                if risk
                else (
                    f"This answer produces {outcome_count} distinct baseline "
                    f"outcomes across {impact_count} components and can "
                    f"eliminate {maximum_elimination_count} deployment families."
                )
            ),
        ))
    return tuple(sorted(
        candidates,
        key=lambda candidate: (
            -candidate.information_gain,
            candidate.question_id,
        ),
    ))


def _candidate_answers(
    definition: RequirementDefinition,
    catalog: CatalogRelease,
) -> tuple[RequirementValue, ...]:
    if definition.allowed_values:
        return tuple(definition.allowed_values) + (None,)
    if definition.value_type is RequirementValueType.BOOLEAN:
        return (True, False, None)

    predicate_values = [
        predicate.value
        for rule in catalog.rules
        for predicate in rule.when
        if predicate.requirement_id == definition.id
    ]
    if definition.value_type in (
        RequirementValueType.INTEGER,
        RequirementValueType.NUMBER,
    ):
        numeric_values = {
            candidate
            for value in predicate_values
            if isinstance(value, (int, float)) and not isinstance(value, bool)
            for candidate in (max(0, value - 1), value)
        }
        return tuple(sorted(numeric_values)) + (None,)

    unique_values = {
        content_hash({"value": value}): value for value in predicate_values
    }
    return tuple(unique_values[key] for key in sorted(unique_values)) + (None,)
