"""Strands tools for explaining and evaluating Platform Advisor v2 inputs."""
from __future__ import annotations

import asyncio
import json

from strands import tool

from advisor_core import AssessmentInput, DecisionEngine, build_questionnaire
from advisor_core.models import OverrideRecord
from pipeline_skills.base import PipelineContext
from pipeline_skills.v2_assessment_skill import run_v2_assessment


async def _drain(gen, queue: asyncio.Queue) -> None:
    async for event in gen:
        await queue.put(event)


def make_pipeline_tools(
    ctx: PipelineContext,
    panel_queue: asyncio.Queue,
    session_manager=None,
) -> list:
    """Expose only the v2 questionnaire and atomic deterministic evaluation."""
    engine = DecisionEngine()

    @tool
    async def get_intake_questionnaire(primary_workload: str = "") -> str:
        """
        Return the v2 structured intake questionnaire. Supply one of coding,
        internal_copilot, hosting, customer_facing, process_automation, or
        marketplace to include the workload-specific branch.
        """
        try:
            questionnaire = build_questionnaire(primary_workload or None)
        except ValueError:
            return json.dumps({"error": f"Unsupported workload: {primary_workload}"})
        return json.dumps(questionnaire)

    @tool
    async def evaluate_platform_assessment(
        assessment_json: str,
        overrides_json: str = "[]",
    ) -> str:
        """
        Validate and evaluate a Platform Advisor v2 AssessmentInput. This atomic,
        deterministic operation emits decision, architecture, controls, AWS
        mapping, risks, roadmap, cost, and blueprint panels. Critical missing
        evidence blocks roadmap, cost, and blueprint generation.
        """
        try:
            assessment = AssessmentInput.model_validate_json(assessment_json)
            raw_overrides = json.loads(overrides_json)
            overrides = [OverrideRecord.model_validate(item) for item in raw_overrides]
        except Exception as exc:
            return json.dumps({
                "error": "Invalid v2 assessment input",
                "details": str(exc),
            })

        result = engine.assess(assessment, overrides)
        await _drain(run_v2_assessment(ctx, assessment, result), panel_queue)
        return json.dumps({
            "schema_version": "2.0",
            "status": result.status,
            "evidence_coverage": result.evidence_coverage,
            "operating_model": result.operating_model,
            "missing_evidence": [
                item.model_dump(mode="json") for item in result.missing_evidence
            ],
            "next_action": (
                "Ask only for the listed missing evidence."
                if result.missing_evidence
                else "Tell the user the evidence-backed blueprint is complete in the right panel."
            ),
        })

    return [get_intake_questionnaire, evaluate_platform_assessment]
