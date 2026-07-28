from __future__ import annotations

from decimal import Decimal

import pytest

from demo.portfolio import DEMO_CUSTOMER_ID, DEMO_CUSTOMER_NAME
from demo.seed import (
    EXPECTED_PANEL_TYPES,
    build_demo_portfolio,
    build_seed_items,
    normalize_for_dynamodb,
    write_seed_items,
)


@pytest.fixture(scope="module")
def artifacts():
    return build_demo_portfolio()


def _contains_float(value) -> bool:
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(_contains_float(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_float(item) for item in value)
    return False


def _contains_decimal(value) -> bool:
    if isinstance(value, Decimal):
        return True
    if isinstance(value, dict):
        return any(_contains_decimal(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_decimal(item) for item in value)
    return False


def test_demo_portfolio_covers_three_decision_ready_operating_models(artifacts):
    assert DEMO_CUSTOMER_ID == "cust_demo_northwind"
    assert DEMO_CUSTOMER_NAME == "Northwind Finance (Demo)"
    assert len(artifacts) == 3
    assert {item.result.operating_model for item in artifacts} == {
        "centralized",
        "federated",
        "decentralized",
    }
    assert all(item.result.status == "complete" for item in artifacts)
    assert all(item.result.evidence_coverage == 1 for item in artifacts)
    assert all(not item.result.missing_evidence for item in artifacts)


def test_each_blueprint_emits_the_complete_ten_panel_contract(artifacts):
    for artifact in artifacts:
        assert tuple(panel["panel_type"] for panel in artifact.panels) == (
            EXPECTED_PANEL_TYPES
        )
        assert [panel["step"] for panel in artifact.panels] == list(range(1, 11))
        assert artifact.panels[-1]["data"]["export_ready"] is True
        assert artifact.pipeline_ctx["current_step"] == 10
        assert artifact.pipeline_ctx["assessment_result"]["trace"]


def test_dynamodb_normalization_removes_python_floats(artifacts):
    items = build_seed_items(artifacts)
    normalized = normalize_for_dynamodb(items)

    assert _contains_float(items)
    assert not _contains_float(normalized)
    assert _contains_decimal(normalized)


def test_seed_uses_only_deterministic_demo_keys_and_is_idempotent(artifacts):
    normalized = normalize_for_dynamodb(build_seed_items(artifacts))
    expected_keys = {
        (f"CUSTOMER#{DEMO_CUSTOMER_ID}", "METADATA"),
        *{
            (
                f"CUSTOMER#{DEMO_CUSTOMER_ID}",
                f"SESSION#{artifact.definition.session_id}",
            )
            for artifact in artifacts
        },
        *{
            (f"SESSION#{artifact.definition.session_id}", f"PANEL#{step:02d}")
            for artifact in artifacts
            for step in range(1, 11)
        },
    }

    class FakeTable:
        def __init__(self):
            self.items = {}

        def put_item(self, *, Item, **_kwargs):
            self.items[(Item["PK"], Item["SK"])] = Item

    table = FakeTable()
    assert write_seed_items(table, normalized) == 34
    assert write_seed_items(table, normalized) == 34
    assert set(table.items) == expected_keys
    assert len(table.items) == 34
    customer = table.items[(f"CUSTOMER#{DEMO_CUSTOMER_ID}", "METADATA")]
    assert customer["session_count"] == 3
