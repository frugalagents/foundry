"""
AdvisorPipeline — orchestrates the 8-step deterministic pipeline.

Each step emits SSE events. The pipeline pauses at step 2 (scoring)
awaiting a user confirmation before continuing.
"""
from __future__ import annotations
import asyncio
import json
from typing import AsyncIterator

from skills.base import PipelineContext, make_error
from skills import (
    run_intake,
    run_scoring,
    run_component_selection,
    run_innovation,
    run_compliance,
    run_service_mapping,
    run_antipattern_check,
    run_phasing,
    run_blueprint,
)


class AdvisorPipeline:
    """
    Async generator pipeline.  Call `run()` to get an event stream.
    Internally uses asyncio.Queue so confirmation responses can be
    injected mid-stream via `confirm(choice)`.
    """

    def __init__(self, session_id: str, customer_id: str) -> None:
        self.ctx = PipelineContext(session_id=session_id, customer_id=customer_id)
        self._confirm_queue: asyncio.Queue[str] = asyncio.Queue()

    def confirm(self, choice: str) -> None:
        """Called externally when the user responds to a confirmation_request."""
        self._confirm_queue.put_nowait(choice)

    async def run(self, user_message: str = "{}") -> AsyncIterator[str]:
        """
        Full pipeline run.  Yields SSE event strings.
        Pauses after step 2 until confirm() is called.
        """
        ctx = self.ctx

        # ── Step 1: Intake ────────────────────────────────────────
        try:
            async for event in run_intake(ctx, user_message):
                yield event
        except Exception as exc:
            yield make_error(1, f"Intake failed: {exc}")
            return

        # ── Step 2: Scoring ───────────────────────────────────────
        try:
            async for event in run_scoring(ctx):
                yield event
        except Exception as exc:
            yield make_error(2, f"Scoring failed: {exc}")
            return

        # Wait for confirmation (or timeout after 5 minutes)
        try:
            choice = await asyncio.wait_for(self._confirm_queue.get(), timeout=300)
        except asyncio.TimeoutError:
            choice = "Confirm"  # auto-confirm on timeout

        # Allow user to override pattern
        if choice and choice.lower().startswith("choose "):
            override = choice.lower().replace("choose ", "").strip()
            pattern_map = {
                "federated":    "pattern:federated",
                "centralized":  "pattern:centralized",
                "mesh":         "pattern:mesh",
                "economy":      "pattern:economy",
            }
            if override in pattern_map:
                ctx.pattern_id = pattern_map[override]
                ctx.confidence = 0.8  # manual override confidence

        # ── Step 3: Component Selection ───────────────────────────
        try:
            async for event in run_component_selection(ctx):
                yield event
        except Exception as exc:
            yield make_error(3, f"Component selection failed: {exc}")
            return

        # ── Step 4: Innovation ────────────────────────────────────
        try:
            async for event in run_innovation(ctx):
                yield event
        except Exception as exc:
            yield make_error(4, f"Innovation overlay failed: {exc}")
            return

        # ── Step 5: Compliance ────────────────────────────────────
        try:
            async for event in run_compliance(ctx):
                yield event
        except Exception as exc:
            yield make_error(5, f"Compliance check failed: {exc}")
            return

        # ── Step 6: Service Mapping ───────────────────────────────
        try:
            async for event in run_service_mapping(ctx):
                yield event
        except Exception as exc:
            yield make_error(6, f"Service mapping failed: {exc}")
            return

        # ── Step 7: Anti-pattern Detection ───────────────────────
        try:
            async for event in run_antipattern_check(ctx):
                yield event
        except Exception as exc:
            yield make_error(7, f"Anti-pattern check failed: {exc}")
            return

        # ── Step 8: Phasing ───────────────────────────────────────
        try:
            async for event in run_phasing(ctx):
                yield event
        except Exception as exc:
            yield make_error(8, f"Phasing failed: {exc}")
            return

        # ── Step 9: Blueprint ─────────────────────────────────────
        try:
            async for event in run_blueprint(ctx):
                yield event
        except Exception as exc:
            yield make_error(9, f"Blueprint generation failed: {exc}")
            return
