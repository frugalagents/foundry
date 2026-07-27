"""Shared helpers for all pipeline skills."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineContext:
    """Mutable state carried through the 8-step pipeline."""
    session_id: str
    customer_id: str
    answers: dict = field(default_factory=dict)
    industry: str = ""
    pain_points: list[str] = field(default_factory=list)
    pattern_id: str = ""
    confidence: float = 0.0
    axis_scores: list[float] = field(default_factory=list)
    components: list[dict] = field(default_factory=list)
    innovations: list[dict] = field(default_factory=list)
    compliance_notes: list[str] = field(default_factory=list)
    service_map: list[dict] = field(default_factory=list)
    antipatterns: list[dict] = field(default_factory=list)
    phases: list[dict] = field(default_factory=list)
    blueprint_md: str = ""
    current_step: int = 0
    cost_estimate: dict = field(default_factory=dict)


def make_event(event_type: str, data: Any) -> str:
    """Encode a single SSE event string."""
    payload = json.dumps({"type": event_type, "data": data, "ts": time.time()})
    return f"event: {event_type}\ndata: {payload}\n\n"


def make_panel_update(step: int, panel_type: str, data: Any) -> str:
    return make_event("panel_update", {"step": step, "panel_type": panel_type, **data})


def make_panel_complete(step: int, panel_type: str, payload: Any) -> str:
    return make_event("panel_complete", {"step": step, "panel_type": panel_type, "data": payload})


def make_card_add(card_id: str, card_type: str, payload: Any) -> str:
    return make_event("card_add", {"card_id": card_id, "card_type": card_type, "payload": payload})


def make_card_update(card_id: str, updates: dict) -> str:
    return make_event("card_update", {"card_id": card_id, "updates": updates})


def make_chat_message(role: str, content: str) -> str:
    return make_event("chat_message", {"role": role, "content": content})


def make_chat_stream(delta: str, done: bool = False) -> str:
    return make_event("chat_stream", {"delta": delta, "done": done})


def make_step_transition(from_step: int, to_step: int, label: str) -> str:
    return make_event("step_transition", {"from_step": from_step, "to_step": to_step, "label": label})


def make_confirmation_request(step: int, question: str, options: list[str]) -> str:
    return make_event("confirmation_request", {
        "step": step,
        "question": question,
        "options": options,
    })


def make_error(step: int, message: str, recoverable: bool = True) -> str:
    return make_event("error", {"step": step, "message": message, "recoverable": recoverable})


def make_complete(session_id: str) -> str:
    return make_event("complete", {"session_id": session_id})
