from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_simulation import _bootstrap_inventory_rows, _simulation_title, _update_session_row


class FakeTable:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], dict] = {}
        self.puts: list[dict] = []
        self.updates: list[dict] = []

    def get_item(self, *, Key: dict) -> dict:
        item = self.items.get((Key["PK"], Key["SK"]))
        return {"Item": item} if item else {}

    def put_item(self, *, Item: dict) -> None:
        self.puts.append(Item)
        self.items[(Item["PK"], Item["SK"])] = dict(Item)

    def update_item(self, **kwargs) -> None:
        self.updates.append(kwargs)


def test_bootstrap_inventory_rows_creates_customer_once_and_session_row():
    table = FakeTable()

    _bootstrap_inventory_rows(
        table,
        customer_id="sim-apex-cust",
        session_id="sim-apex-sess-1",
        actor_id="sim-apex-user",
        slug="apex-retail",
        simulation_file=Path("apex-retail-standard-enterprise.md"),
    )

    assert len(table.puts) == 2
    customer_item = table.items[("CUSTOMER#sim-apex-cust", "CUSTOMER#sim-apex-cust")]
    session_item = table.items[("CUSTOMER#sim-apex-cust", "SESSION#sim-apex-sess-1")]
    assert customer_item["name"] == _simulation_title("apex-retail")
    assert customer_item["demo_data"] is True
    assert session_item["title"] == _simulation_title("apex-retail")
    assert session_item["module_id"] == "coding-agent"
    assert session_item["status"] == "active"
    assert session_item["description"] == "Auto-generated from apex-retail-standard-enterprise.md"

    _bootstrap_inventory_rows(
        table,
        customer_id="sim-apex-cust",
        session_id="sim-apex-sess-2",
        actor_id="sim-apex-user",
        slug="apex-retail",
        simulation_file=Path("apex-retail-standard-enterprise.md"),
    )

    assert len(table.puts) == 3


def test_update_session_row_writes_progress_and_status():
    table = FakeTable()

    _update_session_row(
        table,
        customer_id="sim-apex-cust",
        session_id="sim-apex-sess-1",
        current_step=4,
        status="completed",
    )

    assert len(table.updates) == 1
    update = table.updates[0]
    assert update["Key"] == {
        "PK": "CUSTOMER#sim-apex-cust",
        "SK": "SESSION#sim-apex-sess-1",
    }
    assert update["ExpressionAttributeValues"][":current_step"] == 4
    assert update["ExpressionAttributeValues"][":status"] == "completed"
