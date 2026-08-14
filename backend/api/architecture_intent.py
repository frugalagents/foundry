"""Pure proposal and architecture-intent validation helpers."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from advisor_core.knowledge.runtime_release import LoadedKnowledgeRelease
from advisor_core.v3.models import RequirementValue, content_hash


ComponentIntent = Literal["engine_managed", "required", "excluded"]
OperationKind = Literal[
    "set_requirement",
    "set_component_intent",
    "select_offering",
    "clear_intent",
    "record_override_request",
]


class ArchitectureChangeOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: OperationKind
    requirement_id: str | None = None
    value: RequirementValue = None
    component_id: str | None = None
    intent: ComponentIntent | None = None
    offering_id: str | None = None
    rule_id: str | None = None
    rationale: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def operation_fields_match(self) -> "ArchitectureChangeOperation":
        required = {
            "set_requirement": ("requirement_id",),
            "set_component_intent": ("component_id", "intent"),
            "select_offering": ("component_id", "offering_id"),
            "clear_intent": ("component_id",),
            "record_override_request": ("rule_id", "rationale"),
        }[self.operation]
        if any(getattr(self, field) in (None, "") for field in required):
            raise ValueError(f"{self.operation} is missing required fields")
        return self


class ArchitectureChangeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_revision_number: int = Field(ge=1)
    base_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_message: str = Field(min_length=1, max_length=2000)
    operations: list[ArchitectureChangeOperation]
    advisory_evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    unresolved_terms: list[str] = Field(default_factory=list)
    predicted_effects: list[str] = Field(default_factory=list)
    hard_conflicts: list[str] = Field(default_factory=list)
    publication_blockers: list[str] = Field(default_factory=list)
    source: str
    proposal_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def hash_matches_content(self) -> "ArchitectureChangeProposal":
        payload = self.model_dump(mode="json", exclude={"proposal_hash"})
        if self.proposal_hash != content_hash(payload):
            raise ValueError("proposal hash does not match proposal content")
        return self


class ArchitectureProposalApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal: ArchitectureChangeProposal
    idempotency_key: str = Field(min_length=8, max_length=128)


def workspace_inputs(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "answers": dict(state.get("answers") or {}),
        "component_intents": dict(state.get("component_intents") or {}),
        "offering_selections": dict(state.get("offering_selections") or {}),
        "override_requests": list(state.get("override_requests") or []),
        "accepted_proposals": list(state.get("accepted_proposals") or []),
    }


def workspace_state_hash(inputs: dict[str, Any], as_of: str) -> str:
    return content_hash({**inputs, "as_of": as_of})


def _valid_requirement_value(definition: Any, value: Any) -> bool:
    if definition.value_type.value == "boolean":
        valid_type = isinstance(value, bool)
    elif definition.value_type.value == "integer":
        valid_type = isinstance(value, int) and not isinstance(value, bool)
    elif definition.value_type.value == "number":
        valid_type = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif definition.value_type.value == "string":
        valid_type = isinstance(value, str)
    else:
        valid_type = (
            isinstance(value, (list, tuple))
            and all(isinstance(item, str) for item in value)
        )
    if not valid_type:
        return False
    return not definition.allowed_values or value in definition.allowed_values


def validate_operations(
    operations: list[ArchitectureChangeOperation],
    release: LoadedKnowledgeRelease,
) -> list[ArchitectureChangeOperation]:
    requirements = {
        item.id: item for item in release.logical_catalog.requirements
    }
    components = {item.id for item in release.logical_catalog.components}
    offerings = {
        item.id: item for item in release.deployable_catalog.service_variants
    }
    normalized: list[ArchitectureChangeOperation] = []
    seen: set[tuple[str, str]] = set()
    for operation in operations:
        if operation.operation == "set_requirement":
            definition = requirements.get(operation.requirement_id or "")
            if definition is None or not _valid_requirement_value(
                definition, operation.value
            ):
                raise ValueError("proposal contains an unknown requirement or value")
            identity = ("requirement", definition.id)
        elif operation.operation in {
            "set_component_intent",
            "clear_intent",
        }:
            if operation.component_id not in components:
                raise ValueError("proposal contains an unknown component")
            identity = ("component", operation.component_id or "")
        elif operation.operation == "select_offering":
            offering = offerings.get(operation.offering_id or "")
            if operation.component_id not in components:
                raise ValueError("proposal contains an invalid offering selection")
            if operation.offering_id != "auto" and (
                offering is None
                or offering.component_id != operation.component_id
            ):
                raise ValueError("proposal contains an invalid offering selection")
            identity = ("offering", operation.component_id or "")
        else:
            identity = ("override", operation.rule_id or "")
        if identity in seen:
            raise ValueError("proposal changes the same target more than once")
        seen.add(identity)
        normalized.append(operation)
    return normalized


def apply_operations(
    inputs: dict[str, Any],
    operations: list[ArchitectureChangeOperation],
) -> dict[str, Any]:
    updated = deepcopy(inputs)
    for operation in operations:
        if operation.operation == "set_requirement":
            updated["answers"][operation.requirement_id] = operation.value
        elif operation.operation == "set_component_intent":
            if operation.intent == "engine_managed":
                updated["component_intents"].pop(operation.component_id, None)
            else:
                updated["component_intents"][operation.component_id] = (
                    operation.intent
                )
        elif operation.operation == "select_offering":
            if operation.offering_id == "auto":
                updated["offering_selections"].pop(operation.component_id, None)
            else:
                updated["offering_selections"][operation.component_id] = (
                    operation.offering_id
                )
        elif operation.operation == "clear_intent":
            updated["component_intents"].pop(operation.component_id, None)
            updated["offering_selections"].pop(operation.component_id, None)
        else:
            updated["override_requests"].append({
                "rule_id": operation.rule_id,
                "rationale": operation.rationale,
                "status": "blocked",
            })
    return updated


def _active_component_ids(projection: dict[str, Any]) -> set[str]:
    return {
        component["component_id"]
        for plane in projection["architecture"]["planes"]
        for component in plane["components"]
    }


def apply_intent_projection(
    projection: dict[str, Any],
    inputs: dict[str, Any],
    release: LoadedKnowledgeRelease,
) -> dict[str, Any]:
    """Overlay approved catalog intent without weakening authoritative results."""

    active = _active_component_ids(projection)
    components = {
        item.id: item for item in release.logical_catalog.components
    }
    offerings = {
        item.id: item for item in release.deployable_catalog.service_variants
    }
    blockers: list[str] = []
    added: set[str] = set()

    def add_with_dependencies(component_id: str) -> None:
        if component_id in active or component_id in added:
            return
        component = components[component_id]
        for dependency_id in component.dependency_ids:
            add_with_dependencies(dependency_id)
        added.add(component_id)

    for component_id, intent in sorted(inputs["component_intents"].items()):
        if intent == "required":
            add_with_dependencies(component_id)
        elif intent == "excluded" and component_id in active:
            blockers.append(
                f"{components[component_id].name} is required by the "
                "authoritative architecture and cannot be excluded"
            )

    plane_by_id = {
        plane["plane_id"]: plane for plane in projection["architecture"]["planes"]
    }
    for component_id in sorted(added):
        component = components[component_id]
        plane_by_id[component.plane.value]["components"].append({
            "instance_id": f"intent:{component_id.split(':', 1)[1]}",
            "component_id": component_id,
            "name": component.name,
            "description": component.description,
            "kind": component.kind.value,
            "status": "added",
        })
        active.add(component_id)
    existing_edges = {
        (
            edge["source"]["component_id"],
            edge["target"]["component_id"],
        )
        for edge in projection["architecture"]["edges"]
    }
    for component_id in sorted(added):
        for dependency_id in components[component_id].dependency_ids:
            edge_key = (component_id, dependency_id)
            if dependency_id not in active or edge_key in existing_edges:
                continue
            projection["architecture"]["edges"].append({
                "edge_id": (
                    f"edge:intent-{component_id.split(':', 1)[1]}-to-"
                    f"{dependency_id.split(':', 1)[1]}"
                ),
                "source": {
                    "instance_id": f"intent:{component_id.split(':', 1)[1]}",
                    "component_id": component_id,
                    "name": components[component_id].name,
                    "plane": components[component_id].plane.value,
                },
                "target": {
                    "instance_id": f"component-instance:{dependency_id.split(':', 1)[1]}",
                    "component_id": dependency_id,
                    "name": components[dependency_id].name,
                    "plane": components[dependency_id].plane.value,
                },
                "relationship": "depends_on",
                "status": "added",
            })
            existing_edges.add(edge_key)

    selections = inputs["offering_selections"]
    for component_id, offering_id in sorted(selections.items()):
        offering = offerings.get(offering_id)
        if offering is None or offering.component_id != component_id:
            blockers.append(f"Offering {offering_id} is not valid for {component_id}")
        elif component_id not in active:
            blockers.append(
                f"{offering.name} targets a component not present in the architecture"
            )

    deployable = projection.get("deployable_solution") or {}
    candidates = deployable.get("candidates") or []
    matching = [
        candidate
        for candidate in candidates
        if all(
            any(
                selection["component_id"] == component_id
                and selection["service_variant_id"] == offering_id
                for selection in candidate.get("selections", [])
            )
            for component_id, offering_id in selections.items()
        )
    ]
    if selections and not matching:
        blockers.append(
            "No approved deployable bundle satisfies all selected offerings"
        )
    elif matching:
        candidate = matching[0]
        deployable["recommendation"] = {
            "state": (
                "recommended"
                if candidate["compatibility_status"] == "compatible"
                else "conditional"
            ),
            "candidate_id": candidate["bundle_id"],
            "rationale": "Selected by an approved user offering preference.",
        }

    for override in inputs["override_requests"]:
        if override.get("status") == "blocked":
            blockers.append(
                f"Unresolved override {override.get('rule_id')}: "
                f"{override.get('rationale')}"
            )

    projection["architecture"]["summary"]["current_component_count"] = len(active)
    projection["architecture"]["summary"]["current_edge_count"] = len(
        projection["architecture"]["edges"]
    )
    advisory_documents = (
        release.advisory_corpus.documents
        if release.advisory_corpus is not None
        else ()
    )
    projection["advisory_knowledge"] = {
        "authority": "advisory",
        "corpus_hash": (
            release.advisory_corpus.corpus_hash
            if release.advisory_corpus is not None
            else None
        ),
        "documents": [
            {
                "advisory_id": item.advisory_id,
                "title": item.title,
                "description": item.description,
                "group": item.group,
                "status": item.status,
                "component_id": item.component_id,
                "source_path": item.source_path,
                "source_count": len(item.sources),
            }
            for item in advisory_documents
            if item.document_type == "platform-component"
        ],
    }
    projection["architecture_intent"] = {
        "component_intents": inputs["component_intents"],
        "offering_selections": inputs["offering_selections"],
        "override_requests": inputs["override_requests"],
        "available_offerings": [
            {
                "offering_id": item.id,
                "component_id": item.component_id,
                "name": item.name,
                "provider_class": item.provider_class.value,
                "delivery_model": item.delivery_model.value,
            }
            for item in release.deployable_catalog.service_variants
        ],
        "publication_blockers": blockers,
        "publication_blocked": bool(blockers),
    }
    projection.pop("projection_hash", None)
    projection["projection_hash"] = content_hash(projection)
    return projection


def build_proposal(
    *,
    state: dict[str, Any],
    message: str,
    extracted: dict[str, Any],
    release: LoadedKnowledgeRelease,
    base_projection: dict[str, Any],
) -> ArchitectureChangeProposal:
    raw_operations = extracted.get("operations", [])
    operations = validate_operations(
        [
            ArchitectureChangeOperation.model_validate(item)
            for item in raw_operations
            if isinstance(item, dict)
        ],
        release,
    )
    candidate_inputs = apply_operations(workspace_inputs(state), operations)
    candidate_projection = apply_intent_projection(
        deepcopy(base_projection),
        candidate_inputs,
        release,
    )
    intent = candidate_projection["architecture_intent"]
    evidence = []
    relevant_components = {
        operation.component_id
        for operation in operations
        if operation.component_id
    }
    if release.advisory_corpus is not None:
        evidence = [
            {
                "advisory_id": item.advisory_id,
                "title": item.title,
                "status": item.status,
                "component_id": item.component_id,
                "source_path": item.source_path,
            }
            for item in release.advisory_corpus.documents
            if item.component_id in relevant_components
        ]
    effects = []
    for operation in operations:
        if operation.operation == "set_requirement":
            effects.append(f"Set {operation.requirement_id}")
        elif operation.operation == "set_component_intent":
            effects.append(f"Set {operation.component_id} to {operation.intent}")
        elif operation.operation == "select_offering":
            effects.append(f"Select {operation.offering_id}")
        elif operation.operation == "clear_intent":
            effects.append(f"Return {operation.component_id} to engine management")
        else:
            effects.append(f"Record override {operation.rule_id}")
    payload = {
        "base_revision_number": int(state["persistence_revision"]),
        "base_state_hash": state["state_hash"],
        "original_message": message,
        "operations": [item.model_dump(mode="json") for item in operations],
        "advisory_evidence": evidence,
        "confidence": float(extracted.get("confidence", 0.0)),
        "unresolved_terms": list(extracted.get("unresolved_terms", [])),
        "predicted_effects": effects,
        "hard_conflicts": list(intent["publication_blockers"]),
        "publication_blockers": list(intent["publication_blockers"]),
        "source": str(extracted.get("source", "none")),
    }
    return ArchitectureChangeProposal(
        **payload,
        proposal_hash=content_hash(payload),
    )


def accepted_proposal_record(
    proposal: ArchitectureChangeProposal,
    *,
    idempotency_key: str,
    revision_number: int,
) -> dict[str, Any]:
    return {
        "proposal_hash": proposal.proposal_hash,
        "idempotency_key": idempotency_key,
        "original_message": proposal.original_message,
        "operations": [
            item.model_dump(mode="json") for item in proposal.operations
        ],
        "advisory_evidence": proposal.advisory_evidence,
        "revision_number": revision_number,
        "accepted_at": datetime.now(timezone.utc).isoformat(),
    }
