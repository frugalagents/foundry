"""Deterministic R0.2 candidate generation and decision-matrix ranking."""
from __future__ import annotations

from collections import defaultdict

from ..engine import (
    evaluate_revision_deployment_families,
    validate_workspace_revision,
)
from ..models import (
    CatalogRelease,
    DeploymentFamilyEvaluation,
    FeasibilityStatus,
    RequirementConstraint,
    WorkspaceRevision,
    content_hash,
)
from .catalog import compile_deployable_catalog
from .models import (
    BundleSelection,
    BundleTemplate,
    CandidateBundle,
    CompatibilityFinding,
    CompatibilityStatus,
    DeployableCatalogRelease,
    DeployableDecisionMatrix,
    DimensionScore,
    FindingSeverity,
    ProviderClass,
    Recommendation,
    RecommendationState,
    RequirementCapabilityRule,
    ScoreProfile,
    SensitivityIndicator,
    ServiceVariant,
    TradeOff,
    TradeOffKind,
)


def _validate_revision_pin(
    revision: WorkspaceRevision,
    catalog: CatalogRelease,
) -> None:
    validate_workspace_revision(revision, catalog)


def _provider_class_for_component(
    template: BundleTemplate,
    component_id: str,
    plane: object,
) -> ProviderClass:
    component_overrides = {
        item.component_id: item.provider_class
        for item in template.component_selections
    }
    if component_id in component_overrides:
        return component_overrides[component_id]
    plane_overrides = {
        item.plane: item.provider_class
        for item in template.plane_selections
    }
    return plane_overrides.get(plane, template.default_provider_class)


def _select_services(
    logical_catalog: CatalogRelease,
    deployable_catalog: DeployableCatalogRelease,
    template: BundleTemplate,
    component_ids: tuple[str, ...],
) -> tuple[BundleSelection, ...]:
    component_by_id = {
        component.id: component for component in logical_catalog.components
    }
    variant_by_key = {
        (variant.component_id, variant.provider_class): variant
        for variant in deployable_catalog.service_variants
    }
    selections: list[BundleSelection] = []
    for component_id in component_ids:
        component = component_by_id.get(component_id)
        if component is None:
            continue
        provider_class = _provider_class_for_component(
            template,
            component_id,
            component.plane,
        )
        variant = variant_by_key.get((component_id, provider_class))
        if variant is None:
            continue
        selections.append(BundleSelection(
            component_id=component_id,
            service_variant_id=variant.id,
            service_name=variant.name,
            provider_class=provider_class,
            delivery_model=variant.delivery_model,
        ))
    return tuple(selections)


def _family_findings(
    template: BundleTemplate,
    revision: WorkspaceRevision,
    evaluation: DeploymentFamilyEvaluation,
) -> tuple[CompatibilityFinding, ...]:
    if evaluation.status is FeasibilityStatus.FEASIBLE:
        return ()
    family_slug = evaluation.pattern_id.split(":", 1)[1]
    if evaluation.status is FeasibilityStatus.REJECTED:
        return (_finding(
            template=template,
            revision=revision,
            suffix=f"family-{family_slug}-rejected",
            status=CompatibilityStatus.INCOMPATIBLE,
            severity=FindingSeverity.ERROR,
            code="deployment_family_rejected",
            message=(
                f"{evaluation.pattern_id} is rejected by "
                f"{list(evaluation.rejection_rule_ids)!r}."
            ),
        ),)
    return (_finding(
        template=template,
        revision=revision,
        suffix=f"family-{family_slug}-unresolved",
        status=CompatibilityStatus.CONDITIONAL,
        severity=FindingSeverity.WARNING,
        code="deployment_family_unresolved",
        message=(
            f"{evaluation.pattern_id} cannot be considered eligible until "
            f"{list(evaluation.blocking_requirement_ids)!r} are resolved."
        ),
    ),)


def _selection_findings(
    template: BundleTemplate,
    revision: WorkspaceRevision,
    logical_catalog: CatalogRelease,
    deployable_catalog: DeployableCatalogRelease,
    expected_component_ids: tuple[str, ...],
    selections: tuple[BundleSelection, ...],
) -> tuple[CompatibilityFinding, ...]:
    expected = set(expected_component_ids)
    selected = {selection.component_id for selection in selections}
    component_by_id = {
        component.id: component for component in logical_catalog.components
    }
    variant_by_id = {
        variant.id: variant for variant in deployable_catalog.service_variants
    }
    provider_ids = {
        provider.id for provider in deployable_catalog.providers
    }
    binding_by_component = {
        binding.component_id: binding
        for binding in deployable_catalog.component_bindings
    }
    findings: list[CompatibilityFinding] = []

    for component_id in sorted(expected - selected):
        component_slug = component_id.split(":", 1)[1]
        findings.append(_finding(
            template=template,
            revision=revision,
            suffix=f"variant-{component_slug}-missing",
            status=CompatibilityStatus.INCOMPATIBLE,
            severity=FindingSeverity.ERROR,
            code="missing_service_variant",
            message=(
                f"No service variant satisfies the provider selection for "
                f"{component_id}."
            ),
            component_ids=(component_id,),
        ))

    for selection in selections:
        variant = variant_by_id.get(selection.service_variant_id)
        compatible_identity = (
            variant is not None
            and variant.component_id == selection.component_id
            and variant.provider_class == selection.provider_class
            and variant.delivery_model == selection.delivery_model
            and variant.provider_id in provider_ids
        )
        if not compatible_identity:
            component_slug = selection.component_id.split(":", 1)[1]
            findings.append(_finding(
                template=template,
                revision=revision,
                suffix=f"variant-{component_slug}-incompatible",
                status=CompatibilityStatus.INCOMPATIBLE,
                severity=FindingSeverity.ERROR,
                code="incompatible_service_variant",
                message=(
                    f"{selection.service_variant_id} does not match the selected "
                    f"component, provider class, and delivery model."
                ),
                component_ids=(selection.component_id,),
            ))
            continue
        assert variant is not None
        component = component_by_id[selection.component_id]
        component_slug = selection.component_id.split(":", 1)[1]
        if set(variant.dependency_component_ids) != set(
            component.dependency_ids
        ):
            findings.append(_finding(
                template=template,
                revision=revision,
                suffix=f"variant-{component_slug}-dependencies",
                status=CompatibilityStatus.INCOMPATIBLE,
                severity=FindingSeverity.ERROR,
                code="incompatible_variant_dependencies",
                message=(
                    f"{variant.id} dependency contract does not match "
                    f"{selection.component_id}."
                ),
                component_ids=(selection.component_id,),
            ))
        missing_dependencies = sorted(
            set(variant.dependency_component_ids) - selected
        )
        if missing_dependencies:
            findings.append(_finding(
                template=template,
                revision=revision,
                suffix=f"dependency-{component_slug}-missing",
                status=CompatibilityStatus.INCOMPATIBLE,
                severity=FindingSeverity.ERROR,
                code="missing_variant_dependency",
                message=(
                    f"{variant.id} is selected without required components "
                    f"{missing_dependencies!r}."
                ),
                component_ids=tuple(
                    (selection.component_id, *missing_dependencies)
                ),
            ))

        binding = binding_by_component.get(selection.component_id)
        if binding is None:
            findings.append(_finding(
                template=template,
                revision=revision,
                suffix=f"interface-binding-{component_slug}-missing",
                status=CompatibilityStatus.INCOMPATIBLE,
                severity=FindingSeverity.ERROR,
                code="missing_interface_binding",
                message=(
                    f"{selection.component_id} has no interface contract "
                    "binding."
                ),
                component_ids=(selection.component_id,),
            ))
        elif (
            variant.provides_interface_ids
            != binding.provides_interface_ids
            or variant.requires_interface_ids
            != binding.requires_interface_ids
        ):
            findings.append(_finding(
                template=template,
                revision=revision,
                suffix=f"variant-{component_slug}-interfaces",
                status=CompatibilityStatus.INCOMPATIBLE,
                severity=FindingSeverity.ERROR,
                code="incompatible_variant_interfaces",
                message=(
                    f"{variant.id} interface contract does not match "
                    f"{selection.component_id}."
                ),
                component_ids=(selection.component_id,),
            ))

    for component_id in sorted(expected):
        component = component_by_id.get(component_id)
        if component is None:
            continue
        missing_dependencies = sorted(set(component.dependency_ids) - expected)
        if not missing_dependencies:
            continue
        component_slug = component_id.split(":", 1)[1]
        findings.append(_finding(
            template=template,
            revision=revision,
            suffix=f"dependency-{component_slug}-missing",
            status=CompatibilityStatus.INCOMPATIBLE,
            severity=FindingSeverity.ERROR,
            code="missing_variant_dependency",
            message=(
                f"{component_id} is selected without required components "
                f"{missing_dependencies!r}."
            ),
            component_ids=tuple((component_id, *missing_dependencies)),
        ))
    return tuple(findings)


def _finding(
    *,
    template: BundleTemplate,
    revision: WorkspaceRevision,
    suffix: str,
    status: CompatibilityStatus,
    severity: FindingSeverity,
    code: str,
    message: str,
    component_ids: tuple[str, ...] = (),
    interface_id: str | None = None,
    requirement_id: str | None = None,
) -> CompatibilityFinding:
    template_slug = template.id.split(":", 1)[1]
    return CompatibilityFinding(
        finding_id=(
            f"finding:{template_slug}-r{revision.revision_number}-{suffix}"
        ),
        status=status,
        severity=severity,
        code=code,
        message=message,
        component_ids=component_ids,
        interface_id=interface_id,
        requirement_id=requirement_id,
    )


def _requirement_findings(
    template: BundleTemplate,
    revision: WorkspaceRevision,
) -> tuple[CompatibilityFinding, ...]:
    requirement_by_id = {
        item.requirement_id: item for item in revision.requirements
    }
    findings: list[CompatibilityFinding] = []
    for acceptance in template.requirement_acceptance:
        constraint = requirement_by_id.get(acceptance.requirement_id)
        requirement_slug = acceptance.requirement_id.split(":", 1)[1]
        if constraint is None or constraint.value is None:
            findings.append(_finding(
                template=template,
                revision=revision,
                suffix=f"requirement-{requirement_slug}-unknown",
                status=CompatibilityStatus.CONDITIONAL,
                severity=FindingSeverity.WARNING,
                code="requirement_unresolved",
                message=(
                    f"{acceptance.requirement_id} must be resolved before "
                    f"{template.name} can be approved."
                ),
                requirement_id=acceptance.requirement_id,
            ))
        elif constraint.value not in acceptance.accepted_values:
            findings.append(_finding(
                template=template,
                revision=revision,
                suffix=f"requirement-{requirement_slug}-rejected",
                status=CompatibilityStatus.INCOMPATIBLE,
                severity=FindingSeverity.ERROR,
                code="deployment_family_mismatch",
                message=(
                    f"{template.name} accepts "
                    f"{list(acceptance.accepted_values)!r} for "
                    f"{acceptance.requirement_id}, not "
                    f"{constraint.value!r}."
                ),
                requirement_id=acceptance.requirement_id,
            ))
    return tuple(findings)


def _interface_findings(
    template: BundleTemplate,
    revision: WorkspaceRevision,
    deployable_catalog: DeployableCatalogRelease,
    selections: tuple[BundleSelection, ...],
) -> tuple[CompatibilityFinding, ...]:
    variant_by_id = {
        variant.id: variant for variant in deployable_catalog.service_variants
    }
    providers: dict[str, set[str]] = defaultdict(set)
    for selection in selections:
        variant = variant_by_id.get(selection.service_variant_id)
        if variant is None:
            continue
        for interface_id in variant.provides_interface_ids:
            providers[interface_id].add(selection.component_id)

    findings: list[CompatibilityFinding] = []
    for selection in selections:
        variant = variant_by_id.get(selection.service_variant_id)
        if variant is None:
            continue
        for interface_id in variant.requires_interface_ids:
            if providers.get(interface_id):
                continue
            interface_slug = interface_id.split(":", 1)[1]
            component_slug = selection.component_id.split(":", 1)[1]
            findings.append(_finding(
                template=template,
                revision=revision,
                suffix=f"interface-{interface_slug}-{component_slug}",
                status=CompatibilityStatus.INCOMPATIBLE,
                severity=FindingSeverity.ERROR,
                code="missing_interface_provider",
                message=(
                    f"{variant.id} requires {interface_id}, but no selected "
                    "service variant provides that contract."
                ),
                component_ids=(selection.component_id,),
                interface_id=interface_id,
            ))
    return tuple(findings)


def _rule_matches(
    rule: RequirementCapabilityRule,
    constraint: RequirementConstraint | None,
) -> bool:
    if constraint is None or constraint.value is None:
        return False
    if rule.operator == "equals":
        return constraint.value == rule.value
    if rule.operator == "greater_than_or_equal":
        return bool(constraint.value >= rule.value)  # type: ignore[operator]
    if rule.operator == "contains":
        return (
            isinstance(constraint.value, tuple)
            and rule.value in constraint.value
        )
    raise ValueError(f"unsupported capability-rule operator: {rule.operator}")


def _capability_state(
    variant: ServiceVariant,
    provider: object,
    capability: str,
) -> CompatibilityStatus:
    variant_supported = set(variant.supported_capabilities)
    variant_unsupported = set(variant.unsupported_capabilities)
    if capability in variant_supported:
        return CompatibilityStatus.COMPATIBLE
    if capability in variant_unsupported:
        return CompatibilityStatus.INCOMPATIBLE
    provider_supported = set(getattr(provider, "supported_capabilities"))
    provider_unsupported = set(getattr(provider, "unsupported_capabilities"))
    if capability in provider_supported:
        return CompatibilityStatus.COMPATIBLE
    if capability in provider_unsupported:
        return CompatibilityStatus.INCOMPATIBLE
    return CompatibilityStatus.CONDITIONAL


def _capability_findings(
    template: BundleTemplate,
    revision: WorkspaceRevision,
    deployable_catalog: DeployableCatalogRelease,
    selections: tuple[BundleSelection, ...],
) -> tuple[CompatibilityFinding, ...]:
    requirement_by_id = {
        item.requirement_id: item for item in revision.requirements
    }
    variant_by_id = {
        variant.id: variant for variant in deployable_catalog.service_variants
    }
    provider_by_id = {
        provider.id: provider for provider in deployable_catalog.providers
    }
    selection_by_component = {
        selection.component_id: selection for selection in selections
    }
    findings: list[CompatibilityFinding] = []

    for rule in deployable_catalog.capability_rules:
        if not _rule_matches(
            rule,
            requirement_by_id.get(rule.requirement_id),
        ):
            continue
        for component_id in rule.target_component_ids:
            selection = selection_by_component.get(component_id)
            if selection is None:
                continue
            variant = variant_by_id[selection.service_variant_id]
            provider = provider_by_id.get(variant.provider_id)
            if provider is None:
                component_slug = component_id.split(":", 1)[1]
                rule_slug = rule.id.split(":", 1)[1]
                findings.append(_finding(
                    template=template,
                    revision=revision,
                    suffix=f"provider-{rule_slug}-{component_slug}",
                    status=CompatibilityStatus.INCOMPATIBLE,
                    severity=FindingSeverity.ERROR,
                    code="missing_variant_provider",
                    message=(
                        f"{variant.id} references unavailable provider "
                        f"{variant.provider_id}."
                    ),
                    component_ids=(component_id,),
                    requirement_id=rule.requirement_id,
                ))
                continue
            state = _capability_state(
                variant,
                provider,
                rule.required_capability,
            )
            if state is CompatibilityStatus.COMPATIBLE:
                continue
            component_slug = component_id.split(":", 1)[1]
            rule_slug = rule.id.split(":", 1)[1]
            is_error = state is CompatibilityStatus.INCOMPATIBLE
            findings.append(_finding(
                template=template,
                revision=revision,
                suffix=f"capability-{rule_slug}-{component_slug}",
                status=state,
                severity=(
                    FindingSeverity.ERROR
                    if is_error
                    else FindingSeverity.WARNING
                ),
                code=(
                    "required_capability_unsupported"
                    if is_error
                    else "required_capability_unverified"
                ),
                message=(
                    f"{selection.service_name} "
                    f"{'does not support' if is_error else 'has not verified'} "
                    f"{rule.required_capability}: {rule.rationale}"
                ),
                component_ids=(component_id,),
                requirement_id=rule.requirement_id,
            ))
    return tuple(findings)


def _compatibility_status(
    findings: tuple[CompatibilityFinding, ...],
) -> CompatibilityStatus:
    if any(
        finding.status is CompatibilityStatus.INCOMPATIBLE
        for finding in findings
    ):
        return CompatibilityStatus.INCOMPATIBLE
    if any(
        finding.status is CompatibilityStatus.CONDITIONAL
        for finding in findings
    ):
        return CompatibilityStatus.CONDITIONAL
    return CompatibilityStatus.COMPATIBLE


def _dimension_scores(
    template: BundleTemplate,
    deployable_catalog: DeployableCatalogRelease,
    selections: tuple[BundleSelection, ...],
) -> tuple[DimensionScore, ...]:
    variant_by_id = {
        variant.id: variant for variant in deployable_catalog.service_variants
    }
    provider_by_id = {
        provider.id: provider for provider in deployable_catalog.providers
    }
    totals = {
        dimension.id: 0.0
        for dimension in deployable_catalog.score_dimensions
    }
    for selection in selections:
        variant = variant_by_id.get(selection.service_variant_id)
        if variant is None:
            continue
        provider = provider_by_id.get(variant.provider_id)
        if provider is None:
            continue
        provider_scores = {
            item.dimension_id: item.value
            for item in provider.dimension_scores
        }
        variant_adjustments = {
            item.dimension_id: item.value
            for item in variant.score_adjustments
        }
        for dimension_id in totals:
            totals[dimension_id] += (
                provider_scores[dimension_id]
                + variant_adjustments.get(dimension_id, 0)
            )

    template_adjustments = {
        item.dimension_id: item.value
        for item in template.score_adjustments
    }
    divisor = max(len(selections), 1)
    return tuple(
        DimensionScore(
            dimension_id=dimension_id,
            score=round(
                min(
                    100,
                    max(
                        0,
                        total / divisor
                        + template_adjustments.get(dimension_id, 0),
                    ),
                ),
                3,
            ),
        )
        for dimension_id, total in sorted(totals.items())
    )


def _weighted_score(
    scores: tuple[DimensionScore, ...],
    profile: ScoreProfile,
    template: BundleTemplate,
    status: CompatibilityStatus,
) -> float:
    score_by_id = {item.dimension_id: item.score for item in scores}
    weighted = sum(
        score_by_id[item.dimension_id] * item.weight
        for item in profile.weights
    )
    weighted -= template.integration_penalty
    if status is CompatibilityStatus.CONDITIONAL:
        weighted -= profile.conditional_penalty
    if status is CompatibilityStatus.INCOMPATIBLE:
        weighted = 0
    return round(min(100, max(0, weighted)), 3)


def _tradeoffs(
    template: BundleTemplate,
    scores: tuple[DimensionScore, ...],
    selections: tuple[BundleSelection, ...],
    findings: tuple[CompatibilityFinding, ...],
) -> tuple[TradeOff, ...]:
    ordered = sorted(
        scores,
        key=lambda item: (-item.score, item.dimension_id),
    )
    strongest = ordered[0]
    weakest = sorted(
        scores,
        key=lambda item: (item.score, item.dimension_id),
    )[0]
    template_slug = template.id.split(":", 1)[1]
    tradeoffs = [
        TradeOff(
            tradeoff_id=f"tradeoff:{template_slug}-advantage",
            kind=TradeOffKind.ADVANTAGE,
            dimension_id=strongest.dimension_id,
            impact=strongest.score,
            statement=(
                f"Strongest dimension is {strongest.dimension_id} at "
                f"{strongest.score:.1f}/100."
            ),
        ),
        TradeOff(
            tradeoff_id=f"tradeoff:{template_slug}-compromise",
            kind=TradeOffKind.COMPROMISE,
            dimension_id=weakest.dimension_id,
            impact=weakest.score,
            statement=(
                f"Primary compromise is {weakest.dimension_id} at "
                f"{weakest.score:.1f}/100."
            ),
        ),
    ]
    provider_classes = sorted({
        selection.provider_class.value for selection in selections
    })
    if len(provider_classes) > 1:
        tradeoffs.append(TradeOff(
            tradeoff_id=f"tradeoff:{template_slug}-integration",
            kind=TradeOffKind.INTEGRATION,
            impact=template.integration_penalty,
            statement=(
                "Cross-provider integration spans "
                f"{', '.join(provider_classes)} and applies a "
                f"{template.integration_penalty:.1f}-point score penalty."
            ),
        ))
    constraint_count = sum(
        finding.severity in (
            FindingSeverity.ERROR,
            FindingSeverity.WARNING,
        )
        for finding in findings
    )
    if constraint_count:
        tradeoffs.append(TradeOff(
            tradeoff_id=f"tradeoff:{template_slug}-constraints",
            kind=TradeOffKind.CONSTRAINT,
            impact=float(constraint_count),
            statement=(
                f"{constraint_count} requirement or compatibility "
                "constraint(s) require resolution."
            ),
        ))
    return tuple(tradeoffs)


def _dominates(
    left: tuple[DimensionScore, ...],
    right: tuple[DimensionScore, ...],
) -> bool:
    left_by_id = {item.dimension_id: item.score for item in left}
    right_by_id = {item.dimension_id: item.score for item in right}
    return all(
        left_by_id[dimension_id] >= right_by_id[dimension_id]
        for dimension_id in left_by_id
    ) and any(
        left_by_id[dimension_id] > right_by_id[dimension_id]
        for dimension_id in left_by_id
    )


def _eligible_candidates(
    candidates: tuple[CandidateBundle, ...],
) -> tuple[CandidateBundle, ...]:
    compatible = tuple(
        candidate
        for candidate in candidates
        if (
            candidate.family_feasibility_status
            is FeasibilityStatus.FEASIBLE
            and candidate.compatibility_status
            is CompatibilityStatus.COMPATIBLE
        )
    )
    if compatible:
        return compatible
    return tuple(
        candidate
        for candidate in candidates
        if (
            candidate.family_feasibility_status
            is FeasibilityStatus.FEASIBLE
            and candidate.compatibility_status
            is CompatibilityStatus.CONDITIONAL
        )
    )


def _pareto_ids(
    candidates: tuple[CandidateBundle, ...],
) -> tuple[str, ...]:
    eligible = _eligible_candidates(candidates)
    return tuple(sorted(
        candidate.bundle_id
        for candidate in eligible
        if not any(
            other.bundle_id != candidate.bundle_id
            and _dominates(
                other.dimension_scores,
                candidate.dimension_scores,
            )
            for other in eligible
        )
    ))


def _ranking_key(candidate: CandidateBundle) -> tuple[int, int, float, str]:
    feasibility_rank = {
        FeasibilityStatus.FEASIBLE: 0,
        FeasibilityStatus.UNKNOWN: 1,
        FeasibilityStatus.REJECTED: 2,
    }
    status_rank = {
        CompatibilityStatus.COMPATIBLE: 0,
        CompatibilityStatus.CONDITIONAL: 1,
        CompatibilityStatus.INCOMPATIBLE: 2,
    }
    return (
        feasibility_rank[candidate.family_feasibility_status],
        status_rank[candidate.compatibility_status],
        -candidate.weighted_score,
        candidate.bundle_id,
    )


def _score_with_weights(
    candidate: CandidateBundle,
    weights: dict[str, float],
    baseline_weights: dict[str, float],
) -> float:
    scores = {
        item.dimension_id: item.score
        for item in candidate.dimension_scores
    }
    baseline_raw = sum(
        scores[dimension_id] * weight
        for dimension_id, weight in baseline_weights.items()
    )
    fixed_penalty = baseline_raw - candidate.weighted_score
    return sum(
        scores[dimension_id] * weight
        for dimension_id, weight in weights.items()
    ) - fixed_penalty


def _sensitivity(
    candidates: tuple[CandidateBundle, ...],
    profile: ScoreProfile,
) -> tuple[SensitivityIndicator, ...]:
    eligible = _eligible_candidates(candidates)
    if not eligible:
        return ()
    baseline = sorted(eligible, key=_ranking_key)[0]
    baseline_weights = {
        item.dimension_id: item.weight for item in profile.weights
    }
    baseline_order = sorted(
        (
            (
                _score_with_weights(
                    candidate,
                    baseline_weights,
                    baseline_weights,
                ),
                candidate.bundle_id,
            )
            for candidate in eligible
        ),
        key=lambda item: (-item[0], item[1]),
    )
    margin = (
        baseline_order[0][0] - baseline_order[1][0]
        if len(baseline_order) > 1
        else baseline_order[0][0]
    )
    indicators: list[SensitivityIndicator] = []
    for dimension_id, baseline_weight in sorted(baseline_weights.items()):
        challenger_id: str | None = None
        switch_weight: float | None = None
        step = round(baseline_weight + 0.05, 2)
        while step <= 0.95 + 1e-9:
            remaining_baseline = 1 - baseline_weight
            remaining_target = 1 - step
            weights = {
                key: (
                    step
                    if key == dimension_id
                    else (
                        weight / remaining_baseline * remaining_target
                        if remaining_baseline
                        else 0
                    )
                )
                for key, weight in baseline_weights.items()
            }
            winner = sorted(
                eligible,
                key=lambda candidate: (
                    -_score_with_weights(
                        candidate,
                        weights,
                        baseline_weights,
                    ),
                    candidate.bundle_id,
                ),
            )[0]
            if winner.bundle_id != baseline.bundle_id:
                challenger_id = winner.bundle_id
                switch_weight = step
                break
            step = round(step + 0.05, 2)
        indicators.append(SensitivityIndicator(
            dimension_id=dimension_id,
            baseline_candidate_id=baseline.bundle_id,
            challenger_candidate_id=challenger_id,
            baseline_weight=baseline_weight,
            switch_weight=switch_weight,
            winner_changes=challenger_id is not None,
            score_margin_at_baseline=round(max(0, margin), 3),
        ))
    return tuple(indicators)


def build_deployable_solution(
    revision: WorkspaceRevision,
    logical_catalog: CatalogRelease,
    deployable_catalog: DeployableCatalogRelease | None = None,
) -> DeployableDecisionMatrix:
    """Build deterministic deployable bundles and their decision matrix.

    The function is side-effect free. Callers may compile and cache the R0.2
    catalog themselves, or omit it to use the packaged coding-platform release.
    """

    _validate_revision_pin(revision, logical_catalog)
    catalog = deployable_catalog or compile_deployable_catalog(logical_catalog)
    if catalog.logical_catalog_id != logical_catalog.id:
        raise ValueError(
            "deployable catalog does not target the supplied logical catalog"
        )
    profile = catalog.score_profiles[0]
    family_evaluations = {
        evaluation.pattern_id: evaluation
        for evaluation in evaluate_revision_deployment_families(
            revision,
            logical_catalog,
        )
    }

    drafts: list[CandidateBundle] = []
    baseline_component_ids = {
        node.component_id for node in revision.architecture.nodes
    }
    for template in catalog.bundle_templates:
        evaluation = family_evaluations[template.deployment_family_id]
        component_ids = tuple(sorted(
            baseline_component_ids
            | {
                node.component_id
                for node in evaluation.architecture.nodes
            }
        ))
        selections = _select_services(
            logical_catalog,
            catalog,
            template,
            component_ids,
        )
        findings = tuple(sorted(
            (
                *_family_findings(template, revision, evaluation),
                *_requirement_findings(template, revision),
                *_selection_findings(
                    template,
                    revision,
                    logical_catalog,
                    catalog,
                    component_ids,
                    selections,
                ),
                *_interface_findings(
                    template,
                    revision,
                    catalog,
                    selections,
                ),
                *_capability_findings(
                    template,
                    revision,
                    catalog,
                    selections,
                ),
            ),
            key=lambda item: item.finding_id,
        ))
        status = _compatibility_status(findings)
        scores = _dimension_scores(template, catalog, selections)
        template_slug = template.id.split(":", 1)[1]
        drafts.append(CandidateBundle(
            bundle_id=(
                f"bundle:{template_slug}-r{revision.revision_number}"
            ),
            template_id=template.id,
            name=template.name,
            deployment_family_id=template.deployment_family_id,
            family_feasibility_status=evaluation.status,
            compatibility_status=status,
            selections=selections,
            findings=findings,
            dimension_scores=scores,
            weighted_score=_weighted_score(
                scores,
                profile,
                template,
                status,
            ),
            tradeoffs=_tradeoffs(
                template,
                scores,
                selections,
                findings,
            ),
            rank=1,
            pareto_optimal=False,
        ))

    ordered_drafts = tuple(sorted(drafts, key=_ranking_key))
    provisional = tuple(
        candidate.model_copy(update={"rank": index})
        for index, candidate in enumerate(ordered_drafts, start=1)
    )
    pareto_ids = _pareto_ids(provisional)
    candidates = tuple(
        candidate.model_copy(update={
            "pareto_optimal": candidate.bundle_id in pareto_ids,
        })
        for candidate in provisional
    )
    eligible = _eligible_candidates(candidates)
    if eligible:
        winner = sorted(eligible, key=_ranking_key)[0]
        state = (
            RecommendationState.RECOMMENDED
            if winner.compatibility_status
            is CompatibilityStatus.COMPATIBLE
            else RecommendationState.CONDITIONAL
        )
        recommendation = Recommendation(
            state=state,
            candidate_id=winner.bundle_id,
            rationale=(
                f"{winner.name} ranks first at "
                f"{winner.weighted_score:.3f}/100, satisfies the highest "
                "available compatibility tier, uses a feasible deployment "
                "family, and is evaluated against "
                f"{len(winner.selections)} family-closure components."
            ),
        )
    else:
        recommendation = Recommendation(
            state=RecommendationState.NO_VIABLE_CANDIDATE,
            rationale=(
                "No generated bundle combines a feasible deployment family "
                "with a complete, compatible variant and interface closure; "
                "no recommendation is safe."
            ),
        )

    payload = {
        "schema_version": "3.0-r0.2",
        "workspace_revision_id": revision.revision_id,
        "workspace_revision_number": revision.revision_number,
        "workspace_state_hash": revision.state_hash,
        "logical_catalog_id": logical_catalog.id,
        "logical_catalog_version": logical_catalog.version,
        "logical_catalog_hash": logical_catalog.content_hash,
        "deployable_catalog_id": catalog.id,
        "deployable_catalog_version": catalog.version,
        "deployable_catalog_hash": catalog.content_hash,
        "score_profile_id": profile.id,
        "candidates": candidates,
        "pareto_candidate_ids": pareto_ids,
        "recommendation": recommendation,
        "sensitivity": _sensitivity(candidates, profile),
    }
    def serialize(value: object) -> object:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")  # type: ignore[union-attr]
        if isinstance(value, tuple):
            return [serialize(item) for item in value]
        return value

    serialized = {
        key: serialize(value) for key, value in payload.items()
    }
    return DeployableDecisionMatrix(
        **payload,
        result_hash=content_hash(serialized),
    )
