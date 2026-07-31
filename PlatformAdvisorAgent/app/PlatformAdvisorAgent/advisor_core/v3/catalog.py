"""JSON catalog loading, compilation, and integrity validation."""
from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from .models import (
    ArchitecturePattern,
    CatalogDocument,
    CatalogManifest,
    CatalogRelease,
    ComponentDefinition,
    DecisionRule,
    EvidenceClaim,
    EvidenceReviewStatus,
    EvidenceSource,
    RequirementOperator,
    RequirementDefinition,
    RequirementValueType,
    RulePredicate,
    StableId,
    content_hash,
)


class CatalogCompilationError(ValueError):
    """Raised when catalog source is well-formed JSON but not publishable."""


def load_catalog_documents(path: str | Path) -> tuple[CatalogDocument, ...]:
    """Load one JSON document or every JSON document below a directory."""

    root = Path(path)
    if not root.exists():
        raise CatalogCompilationError(f"catalog path does not exist: {root}")
    paths = sorted(root.rglob("*.json")) if root.is_dir() else [root]
    if not paths:
        raise CatalogCompilationError(f"catalog path contains no JSON files: {root}")

    documents: list[CatalogDocument] = []
    for source_path in paths:
        try:
            raw = json.loads(source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CatalogCompilationError(
                f"invalid JSON in {source_path}: {exc.msg}"
            ) from exc
        try:
            documents.append(CatalogDocument.model_validate(raw))
        except ValidationError as exc:
            raise CatalogCompilationError(
                f"invalid catalog contract in {source_path}: {exc}"
            ) from exc
    return tuple(documents)


def _collect(
    documents: Iterable[CatalogDocument], field: str
) -> tuple[object, ...]:
    return tuple(item for document in documents for item in getattr(document, field))


def _one_manifest(documents: tuple[CatalogDocument, ...]) -> CatalogManifest:
    manifests = [document.manifest for document in documents if document.manifest]
    if len(manifests) != 1:
        raise CatalogCompilationError(
            f"catalog requires exactly one manifest; found {len(manifests)}"
        )
    return manifests[0]


def _validate_unique_ids(groups: dict[str, tuple[object, ...]]) -> None:
    seen: dict[str, str] = {}
    for group_name, records in groups.items():
        for record in records:
            record_id = str(getattr(record, "id"))
            if record_id in seen:
                raise CatalogCompilationError(
                    f"duplicate ID {record_id!r} in {seen[record_id]} and {group_name}"
                )
            seen[record_id] = group_name


def _require_references(
    owner_kind: str,
    owner_id: str,
    reference_kind: str,
    references: Iterable[StableId],
    available: set[str],
) -> None:
    for reference in references:
        if reference not in available:
            raise CatalogCompilationError(
                f"dangling {reference_kind} reference {reference!r} "
                f"from {owner_kind} {owner_id!r}"
            )


def _validate_references(
    sources: tuple[EvidenceSource, ...],
    claims: tuple[EvidenceClaim, ...],
    requirements: tuple[RequirementDefinition, ...],
    components: tuple[ComponentDefinition, ...],
    patterns: tuple[ArchitecturePattern, ...],
    rules: tuple[DecisionRule, ...],
) -> None:
    source_ids = {record.id for record in sources}
    claim_ids = {record.id for record in claims}
    requirement_ids = {record.id for record in requirements}
    component_ids = {record.id for record in components}
    pattern_ids = {record.id for record in patterns}
    rule_ids = {record.id for record in rules}

    for claim in claims:
        _require_references(
            "evidence claim", claim.id, "source", (claim.source_id,), source_ids
        )
    for requirement in requirements:
        _require_references(
            "requirement",
            requirement.id,
            "ask_when requirement",
            (
                predicate.requirement_id
                for predicate in requirement.ask_when
            ),
            requirement_ids,
        )
        _require_references(
            "requirement",
            requirement.id,
            "evidence claim",
            requirement.evidence_claim_ids,
            claim_ids,
        )
    for component in components:
        _require_references(
            "component",
            component.id,
            "component dependency",
            component.dependency_ids,
            component_ids,
        )
        _require_references(
            "component",
            component.id,
            "evidence claim",
            component.evidence_claim_ids,
            claim_ids,
        )
    for pattern in patterns:
        _require_references(
            "pattern",
            pattern.id,
            "component",
            pattern.component_ids,
            component_ids,
        )
        _require_references(
            "pattern",
            pattern.id,
            "evidence claim",
            pattern.evidence_claim_ids,
            claim_ids,
        )
    for rule in rules:
        _require_references(
            "rule",
            rule.id,
            "requirement",
            (predicate.requirement_id for predicate in rule.when),
            requirement_ids,
        )
        _require_references(
            "rule",
            rule.id,
            "component",
            rule.target_component_ids,
            component_ids,
        )
        _require_references(
            "rule", rule.id, "pattern", rule.target_pattern_ids, pattern_ids
        )
        _require_references(
            "rule",
            rule.id,
            "rule dependency",
            rule.depends_on_rule_ids,
            rule_ids,
        )
        _require_references(
            "rule",
            rule.id,
            "evidence claim",
            rule.evidence_claim_ids,
            claim_ids,
        )


def _validate_acyclic(
    kind: str, dependencies: dict[str, tuple[StableId, ...]]
) -> None:
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        if node_id in visiting:
            start = visiting.index(node_id)
            cycle = visiting[start:] + [node_id]
            raise CatalogCompilationError(
                f"{kind} dependency cycle: {' -> '.join(cycle)}"
            )
        visiting.append(node_id)
        for dependency_id in dependencies[node_id]:
            visit(dependency_id)
        visiting.pop()
        visited.add(node_id)

    for record_id in sorted(dependencies):
        visit(record_id)


def _value_matches_type(
    value: object,
    value_type: RequirementValueType,
) -> bool:
    validators = {
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
    }
    return value is not None and validators[value_type](value)


def _validate_predicate(
    owner_kind: str,
    owner_id: str,
    predicate: RulePredicate,
    definition: RequirementDefinition,
) -> None:
    operator = predicate.operator
    value_type = definition.value_type
    value = predicate.value
    comparison_operators = {
        RequirementOperator.GREATER_THAN,
        RequirementOperator.GREATER_THAN_OR_EQUAL,
        RequirementOperator.LESS_THAN,
        RequirementOperator.LESS_THAN_OR_EQUAL,
    }
    membership_operators = {
        RequirementOperator.IN,
        RequirementOperator.NOT_IN,
    }

    allowed_value_operators = {
        RequirementOperator.EQUALS,
        RequirementOperator.NOT_EQUALS,
        *membership_operators,
    }
    candidate_values = (
        value
        if operator in membership_operators and isinstance(value, tuple)
        else (value,)
    )
    if (
        operator in allowed_value_operators
        and definition.allowed_values
        and any(
            candidate not in definition.allowed_values
            for candidate in candidate_values
        )
    ):
        raise CatalogCompilationError(
            f"invalid predicate in {owner_kind} {owner_id!r}: "
            f"value must be one of {definition.allowed_values}"
        )

    if operator in comparison_operators:
        if value_type not in (
            RequirementValueType.INTEGER,
            RequirementValueType.NUMBER,
        ) or not _value_matches_type(value, value_type):
            raise CatalogCompilationError(
                f"invalid predicate in {owner_kind} {owner_id!r}: "
                f"{operator.value} requires a numeric requirement and value"
            )
        return

    if operator in membership_operators:
        if value_type is RequirementValueType.STRING_SET:
            raise CatalogCompilationError(
                f"invalid predicate in {owner_kind} {owner_id!r}: "
                f"{operator.value} does not support string_set requirements"
            )
        if (
            not isinstance(value, tuple)
            or not value
            or any(
                not _value_matches_type(member, value_type)
                for member in value
            )
        ):
            raise CatalogCompilationError(
                f"invalid predicate in {owner_kind} {owner_id!r}: "
                f"{operator.value} requires a non-empty typed value set"
            )
        return

    if operator is RequirementOperator.CONTAINS:
        if (
            value_type is not RequirementValueType.STRING_SET
            or not isinstance(value, str)
        ):
            raise CatalogCompilationError(
                f"invalid predicate in {owner_kind} {owner_id!r}: "
                "contains requires a string_set requirement and string value"
            )
        return

    if not _value_matches_type(value, value_type):
        raise CatalogCompilationError(
            f"invalid predicate in {owner_kind} {owner_id!r}: "
            f"value must match {value_type.value}"
        )


def _validate_predicates(
    requirements: tuple[RequirementDefinition, ...],
    rules: tuple[DecisionRule, ...],
) -> None:
    definitions = {
        requirement.id: requirement for requirement in requirements
    }
    for requirement in requirements:
        for predicate in requirement.ask_when:
            _validate_predicate(
                "requirement",
                requirement.id,
                predicate,
                definitions[predicate.requirement_id],
            )
    for rule in rules:
        for predicate in rule.when:
            _validate_predicate(
                "rule",
                rule.id,
                predicate,
                definitions[predicate.requirement_id],
            )


def _validate_critical_evidence(
    claims: tuple[EvidenceClaim, ...], as_of: date
) -> None:
    for claim in claims:
        if not claim.critical:
            continue
        if claim.review_status is not EvidenceReviewStatus.APPROVED:
            raise CatalogCompilationError(
                f"critical evidence {claim.id!r} is not approved"
            )
        if claim.effective_on > as_of:
            raise CatalogCompilationError(
                f"critical evidence {claim.id!r} is not effective until "
                f"{claim.effective_on}"
            )
        if claim.expires_on is not None and claim.expires_on < as_of:
            raise CatalogCompilationError(
                f"critical evidence {claim.id!r} expired on {claim.expires_on}"
            )


def _sorted(records: tuple[object, ...]) -> tuple[object, ...]:
    return tuple(sorted(records, key=lambda record: (record.id, record.version)))


def compile_catalog(
    path: str | Path, *, as_of: date | None = None
) -> CatalogRelease:
    """Compile catalog JSON files into one validated, content-addressed release."""

    documents = load_catalog_documents(path)
    manifest = _one_manifest(documents)
    validated_as_of = as_of or date.today()
    if validated_as_of < manifest.effective_on:
        raise CatalogCompilationError(
            f"catalog {manifest.id!r} is not effective until "
            f"{manifest.effective_on}"
        )

    sources = _sorted(_collect(documents, "evidence_sources"))
    claims = _sorted(_collect(documents, "evidence_claims"))
    requirements = _sorted(_collect(documents, "requirements"))
    components = _sorted(_collect(documents, "components"))
    patterns = _sorted(_collect(documents, "patterns"))
    rules = _sorted(_collect(documents, "rules"))

    groups = {
        "evidence_sources": sources,
        "evidence_claims": claims,
        "requirements": requirements,
        "components": components,
        "patterns": patterns,
        "rules": rules,
    }
    _validate_unique_ids(groups)
    _validate_references(
        sources, claims, requirements, components, patterns, rules
    )
    _validate_predicates(requirements, rules)
    _validate_acyclic(
        "requirement applicability",
        {
            requirement.id: tuple(
                predicate.requirement_id
                for predicate in requirement.ask_when
            )
            for requirement in requirements
        },
    )
    _validate_acyclic(
        "component",
        {component.id: component.dependency_ids for component in components},
    )
    _validate_acyclic(
        "rule", {rule.id: rule.depends_on_rule_ids for rule in rules}
    )
    _validate_critical_evidence(claims, validated_as_of)

    hash_payload = {
        "manifest": manifest.model_dump(mode="json", exclude_none=True),
        **{
            name: [
                record.model_dump(mode="json", exclude_none=True)
                for record in records
            ]
            for name, records in groups.items()
        },
    }
    release_hash = content_hash(hash_payload)
    return CatalogRelease(
        **manifest.model_dump(),
        content_hash=release_hash,
        validated_as_of=validated_as_of,
        evidence_sources=sources,
        evidence_claims=claims,
        requirements=requirements,
        components=components,
        patterns=patterns,
        rules=rules,
    )
