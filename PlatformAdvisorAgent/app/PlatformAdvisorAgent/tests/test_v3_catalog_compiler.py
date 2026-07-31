from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from advisor_core.v3 import (
    ArchitectureNode,
    ArchitectureState,
    ArchitectureWorkspace,
    CatalogCompilationError,
    RequirementConstraint,
    WorkspaceRevision,
    canonical_json,
    compile_catalog,
    content_hash,
)


AS_OF = date(2026, 7, 30)


def valid_catalog() -> dict[str, object]:
    return {
        "manifest": {
            "id": "catalog:coding-platform",
            "version": "3.0.0",
            "schema_version": "3.0",
            "title": "Coding Agent Platform",
            "effective_on": "2026-07-01",
        },
        "evidence_sources": [
            {
                "id": "source:provider-docs",
                "version": "1.0.0",
                "title": "Provider documentation",
                "uri": "https://example.test/provider",
                "publisher": "Example Provider",
                "retrieved_at": "2026-07-20T10:00:00Z",
                "snapshot_hash": f"sha256:{'a' * 64}",
            }
        ],
        "evidence_claims": [
            {
                "id": "claim:gateway-routing",
                "version": "1.0.0",
                "source_id": "source:provider-docs",
                "statement": "The gateway supports policy-based model routing.",
                "critical": True,
                "review_status": "approved",
                "effective_on": "2026-07-01",
                "expires_on": "2026-12-31",
                "source_locator": "section-routing",
                "reviewer": "architect@example.test",
            }
        ],
        "requirements": [
            {
                "id": "requirement:multi-provider",
                "version": "1.0.0",
                "name": "Multiple model providers",
                "description": "Use more than one approved model provider.",
                "value_type": "boolean",
                "required": True,
                "evidence_claim_ids": [],
            }
        ],
        "components": [
            {
                "id": "component:identity",
                "version": "1.0.0",
                "name": "Workforce identity",
                "description": "Authenticates developers.",
                "plane": "access",
            },
            {
                "id": "component:model-gateway",
                "version": "1.0.0",
                "name": "Model gateway",
                "description": "Routes requests to approved models.",
                "plane": "model",
                "dependency_ids": ["component:identity"],
                "evidence_claim_ids": ["claim:gateway-routing"],
            },
        ],
        "patterns": [
            {
                "id": "pattern:shared-control-plane",
                "version": "1.0.0",
                "name": "Shared control plane",
                "description": "A shared control plane with team execution boundaries.",
                "role": "deployment_family",
                "component_ids": [
                    "component:model-gateway",
                    "component:identity",
                ],
                "evidence_claim_ids": ["claim:gateway-routing"],
            }
        ],
        "rules": [
            {
                "id": "rule:require-model-gateway",
                "version": "1.0.0",
                "name": "Require model gateway",
                "description": "Multi-provider use requires governed routing.",
                "when": [
                    {
                        "requirement_id": "requirement:multi-provider",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "effect": "require",
                "target_component_ids": ["component:model-gateway"],
                "evidence_claim_ids": ["claim:gateway-routing"],
            }
        ],
    }


def write_catalog(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_compiles_release_with_deterministic_hash_and_replay_json(
    tmp_path: Path,
) -> None:
    payload = valid_catalog()
    first_path = write_catalog(tmp_path / "first.json", payload)
    first = compile_catalog(first_path, as_of=AS_OF)

    reordered = deepcopy(payload)
    reordered["components"] = list(reversed(reordered["components"]))
    reordered["patterns"][0]["component_ids"] = list(
        reversed(reordered["patterns"][0]["component_ids"])
    )
    second_path = write_catalog(tmp_path / "second.json", reordered)
    second = compile_catalog(second_path, as_of=AS_OF)

    assert first.content_hash == second.content_hash
    assert first.replay_json() == second.replay_json()
    assert json.loads(first.replay_json())["content_hash"].startswith("sha256:")


def test_loads_and_compiles_catalog_fragments(tmp_path: Path) -> None:
    payload = valid_catalog()
    manifest = {"manifest": payload.pop("manifest")}
    write_catalog(tmp_path / "00-manifest.json", manifest)
    write_catalog(tmp_path / "10-definitions.json", payload)

    release = compile_catalog(tmp_path, as_of=AS_OF)

    assert release.id == "catalog:coding-platform"
    assert [component.id for component in release.components] == [
        "component:identity",
        "component:model-gateway",
    ]


def test_rejects_duplicate_ids(tmp_path: Path) -> None:
    payload = valid_catalog()
    payload["components"].append(deepcopy(payload["components"][0]))
    path = write_catalog(tmp_path / "catalog.json", payload)

    with pytest.raises(CatalogCompilationError, match="duplicate ID"):
        compile_catalog(path, as_of=AS_OF)


def test_rejects_dangling_references(tmp_path: Path) -> None:
    payload = valid_catalog()
    payload["components"][1]["dependency_ids"] = ["component:missing"]
    path = write_catalog(tmp_path / "catalog.json", payload)

    with pytest.raises(CatalogCompilationError, match="dangling.*component:missing"):
        compile_catalog(path, as_of=AS_OF)


def test_rejects_dangling_ask_when_requirement_reference(tmp_path: Path) -> None:
    payload = valid_catalog()
    payload["requirements"][0]["ask_when"] = [
        {
            "requirement_id": "requirement:missing",
            "operator": "equals",
            "value": True,
        }
    ]
    path = write_catalog(tmp_path / "catalog.json", payload)

    with pytest.raises(
        CatalogCompilationError,
        match="dangling ask_when requirement reference 'requirement:missing'",
    ):
        compile_catalog(path, as_of=AS_OF)


@pytest.mark.parametrize(
    ("allowed_values", "message"),
    [
        ([True, True], "allowed requirement values must be unique"),
        (["yes", "no"], "allowed values must match boolean"),
    ],
)
def test_rejects_invalid_or_duplicate_allowed_values(
    tmp_path: Path,
    allowed_values: list[object],
    message: str,
) -> None:
    payload = valid_catalog()
    payload["requirements"][0]["allowed_values"] = allowed_values
    path = write_catalog(tmp_path / "catalog.json", payload)

    with pytest.raises(CatalogCompilationError, match=message):
        compile_catalog(path, as_of=AS_OF)


def test_rejects_component_dependency_cycles(tmp_path: Path) -> None:
    payload = valid_catalog()
    payload["components"][0]["dependency_ids"] = ["component:model-gateway"]
    path = write_catalog(tmp_path / "catalog.json", payload)

    with pytest.raises(CatalogCompilationError, match="component dependency cycle"):
        compile_catalog(path, as_of=AS_OF)


def test_rejects_rule_dependency_cycles(tmp_path: Path) -> None:
    payload = valid_catalog()
    second_rule = deepcopy(payload["rules"][0])
    second_rule["id"] = "rule:route-approved-models"
    second_rule["depends_on_rule_ids"] = ["rule:require-model-gateway"]
    payload["rules"][0]["depends_on_rule_ids"] = ["rule:route-approved-models"]
    payload["rules"].append(second_rule)
    path = write_catalog(tmp_path / "catalog.json", payload)

    with pytest.raises(CatalogCompilationError, match="rule dependency cycle"):
        compile_catalog(path, as_of=AS_OF)


def test_rejects_requirement_applicability_cycles(tmp_path: Path) -> None:
    payload = valid_catalog()
    second = deepcopy(payload["requirements"][0])
    second["id"] = "requirement:model-fallback"
    payload["requirements"][0]["ask_when"] = [
        {
            "requirement_id": second["id"],
            "operator": "equals",
            "value": True,
        }
    ]
    second["ask_when"] = [
        {
            "requirement_id": payload["requirements"][0]["id"],
            "operator": "equals",
            "value": True,
        }
    ]
    payload["requirements"].append(second)
    path = write_catalog(tmp_path / "catalog.json", payload)

    with pytest.raises(
        CatalogCompilationError,
        match="requirement applicability dependency cycle",
    ):
        compile_catalog(path, as_of=AS_OF)


@pytest.mark.parametrize(
    ("operator", "value", "message"),
    [
        ("greater_than", True, "requires a numeric requirement"),
        ("in", True, "requires a non-empty typed value set"),
    ],
)
def test_rejects_predicate_operator_and_type_mismatches(
    tmp_path: Path,
    operator: str,
    value: object,
    message: str,
) -> None:
    payload = valid_catalog()
    payload["rules"][0]["when"][0].update({
        "operator": operator,
        "value": value,
    })
    path = write_catalog(tmp_path / "catalog.json", payload)

    with pytest.raises(CatalogCompilationError, match=message):
        compile_catalog(path, as_of=AS_OF)


@pytest.mark.parametrize(
    ("operator", "value"),
    [
        ("equals", "unsupported"),
        ("not_in", ["supported", "unsupported"]),
    ],
)
def test_rejects_predicate_values_outside_requirement_allowed_values(
    tmp_path: Path,
    operator: str,
    value: object,
) -> None:
    payload = valid_catalog()
    payload["requirements"][0].update({
        "value_type": "string",
        "allowed_values": ["supported", "managed"],
    })
    payload["rules"][0]["when"][0].update({
        "operator": operator,
        "value": value,
    })
    path = write_catalog(tmp_path / "catalog.json", payload)

    with pytest.raises(
        CatalogCompilationError,
        match="value must be one of",
    ):
        compile_catalog(path, as_of=AS_OF)


def test_rejects_mixed_component_and_pattern_rule_targets(
    tmp_path: Path,
) -> None:
    payload = valid_catalog()
    payload["rules"][0]["target_pattern_ids"] = [
        "pattern:shared-control-plane"
    ]
    path = write_catalog(tmp_path / "catalog.json", payload)

    with pytest.raises(
        CatalogCompilationError,
        match="cannot mix component and pattern targets",
    ):
        compile_catalog(path, as_of=AS_OF)


def test_rejects_unapproved_critical_evidence(tmp_path: Path) -> None:
    payload = valid_catalog()
    payload["evidence_claims"][0]["review_status"] = "in_review"
    payload["evidence_claims"][0]["reviewer"] = None
    path = write_catalog(tmp_path / "catalog.json", payload)

    with pytest.raises(CatalogCompilationError, match="critical evidence.*not approved"):
        compile_catalog(path, as_of=AS_OF)


def test_rejects_expired_critical_evidence(tmp_path: Path) -> None:
    payload = valid_catalog()
    payload["evidence_claims"][0]["expires_on"] = "2026-07-29"
    path = write_catalog(tmp_path / "catalog.json", payload)

    with pytest.raises(CatalogCompilationError, match="critical evidence.*expired"):
        compile_catalog(path, as_of=AS_OF)


def test_rejects_catalog_or_critical_evidence_not_yet_effective(
    tmp_path: Path,
) -> None:
    payload = valid_catalog()
    payload["manifest"]["effective_on"] = "2026-07-31"
    path = write_catalog(tmp_path / "future-catalog.json", payload)
    with pytest.raises(CatalogCompilationError, match="catalog.*not effective"):
        compile_catalog(path, as_of=AS_OF)

    payload["manifest"]["effective_on"] = "2026-07-01"
    payload["evidence_claims"][0]["effective_on"] = "2026-07-31"
    path = write_catalog(tmp_path / "future-evidence.json", payload)
    with pytest.raises(
        CatalogCompilationError,
        match="critical evidence.*not effective",
    ):
        compile_catalog(path, as_of=AS_OF)


def test_contracts_are_frozen_and_workspace_chain_is_validated() -> None:
    catalog_content_hash = f"sha256:{'b' * 64}"
    state = ArchitectureState(
        pattern_id="pattern:shared-control-plane",
        nodes=(
            ArchitectureNode(
                instance_id="node:model-gateway",
                component_id="component:model-gateway",
            ),
        ),
    )
    requirements = (
        RequirementConstraint(
            requirement_id="requirement:multi-provider",
            value=True,
            source="user",
            recorded_at="2026-07-30T10:00:00Z",
        ),
    )
    state_digest = content_hash({
        "catalog_content_hash": catalog_content_hash,
        "requirements": [
            {
                "requirement_id": item.requirement_id,
                "value": item.value,
                "source": item.source,
            }
            for item in requirements
        ],
        "architecture": state.model_dump(mode="json"),
    })
    revision = WorkspaceRevision(
        revision_id="revision:one",
        revision_number=1,
        catalog_release_id="catalog:coding-platform",
        catalog_release_version="3.0.0",
        catalog_content_hash=catalog_content_hash,
        requirements=requirements,
        architecture=state,
        created_at="2026-07-30T10:00:00Z",
        state_hash=state_digest,
    )
    workspace = ArchitectureWorkspace(
        workspace_id="workspace:example",
        current_revision_id="revision:one",
        revisions=(revision,),
    )

    assert canonical_json(workspace) == canonical_json(workspace)
    with pytest.raises(ValidationError):
        workspace.current_revision_id = "revision:other"


def test_rejects_unstable_ids_and_versions() -> None:
    with pytest.raises(ValidationError):
        ArchitectureNode(instance_id="not-namespaced", component_id="component:x")
    with pytest.raises(ValidationError):
        WorkspaceRevision(
            revision_id="revision:one",
            revision_number=1,
            catalog_release_id="catalog:x",
            catalog_release_version="latest",
            catalog_content_hash=f"sha256:{'b' * 64}",
            requirements=(),
            architecture={
                "pattern_id": "pattern:x",
                "nodes": (),
            },
            created_at="2026-07-30T10:00:00Z",
            state_hash=f"sha256:{'a' * 64}",
        )
