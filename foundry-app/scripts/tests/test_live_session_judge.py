from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "live-session-judge.py"
SPEC = importlib.util.spec_from_file_location("live_session_judge", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_extract_review_payload_falls_back_to_scalar_fields_when_json_is_truncated():
    response = """
    {
      "overall_verdict": "mixed",
      "judge_confidence": "medium",
      "summary": "The architecture is directionally right but the blueprint is incomplete."
    """

    parsed = MODULE.extract_review_payload(response)

    assert parsed["overall_verdict"] == "mixed"
    assert parsed["judge_confidence"] == "medium"
    assert "blueprint is incomplete" in parsed["summary"]


def test_build_transcript_summary_message_uses_fallback_fields():
    message = MODULE.build_transcript_summary_message(
        """
        {
          "overall_verdict": "pass",
          "judge_confidence": "high",
          "summary": "The session converged on a complete architecture and blueprint."
        """,
        {"deterministic_findings": []},
    )

    assert "Verdict: `pass`" in message
    assert "Judge confidence: `high`" in message
    assert "complete architecture and blueprint" in message


def test_normalize_review_payload_downgrades_pass_when_session_is_not_finalized():
    parsed = {
        "overall_verdict": "pass",
        "judge_confidence": "high",
        "summary": "Directionally strong recommendation.",
    }
    packet = {
        "outcome": {
            "stage": "solutioning",
            "confidence": "low",
            "blocking_question_count": 1,
            "implementation_count": 0,
        },
        "deterministic_findings": [
            {"severity": "critical", "title": "Session did not finalize"},
            {"severity": "critical", "title": "Blocking questions remain open"},
        ],
    }

    normalized = MODULE.normalize_review_payload(parsed, packet)

    assert normalized["overall_verdict"] == "fail"
    assert normalized["judge_confidence"] == "high"
    assert "Deterministic completion guardrails downgraded the verdict" in normalized["summary"]
