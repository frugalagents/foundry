"""Explicit authority boundaries for deterministic architecture decisions."""
from __future__ import annotations

from .models import DecisionRule, RuleAuthority


DECISION_AUTHORITY_SCHEMA_VERSION = "1.0"
AUTHORITATIVE_OPERATIONS = (
    "catalog_lifecycle",
    "component_requirements",
    "dependency_closure",
    "deployment_eligibility",
    "required_controls",
)
ADVISORY_OUTPUTS = (
    "candidate_ranking",
    "pareto_analysis",
    "preference_rules",
    "sensitivity_analysis",
)


class DecisionAuthorityError(ValueError):
    """Raised when rule dependencies cross an authority boundary."""


def is_architecture_authority(rule: DecisionRule) -> bool:
    return rule.authority is RuleAuthority.HARD_CONSTRAINT


def is_eligibility_authority(rule: DecisionRule) -> bool:
    return rule.authority is RuleAuthority.COMPATIBILITY


def is_advisory_rule(rule: DecisionRule) -> bool:
    return rule.authority in {
        RuleAuthority.PREFERENCE,
        RuleAuthority.EXPLANATION,
    }


def validate_decision_authority(
    rules: tuple[DecisionRule, ...],
) -> None:
    """Prevent advisory rules from becoming hidden deterministic dependencies."""

    rules_by_id = {rule.id: rule for rule in rules}
    for rule in rules:
        if is_architecture_authority(rule):
            allowed = {RuleAuthority.HARD_CONSTRAINT}
            surface = "architecture"
        elif is_eligibility_authority(rule):
            allowed = {RuleAuthority.COMPATIBILITY}
            surface = "eligibility"
        else:
            continue
        invalid_dependencies = tuple(
            dependency_id
            for dependency_id in rule.depends_on_rule_ids
            if rules_by_id[dependency_id].authority not in allowed
        )
        if invalid_dependencies:
            raise DecisionAuthorityError(
                f"{surface} rule {rule.id} depends on rules outside its "
                f"authority surface: {invalid_dependencies}"
            )


def decision_authority_projection() -> dict[str, object]:
    return {
        "schema_version": DECISION_AUTHORITY_SCHEMA_VERSION,
        "authoritative_operations": list(AUTHORITATIVE_OPERATIONS),
        "advisory_outputs": list(ADVISORY_OUTPUTS),
        "automatic_bundle_selection": False,
    }
