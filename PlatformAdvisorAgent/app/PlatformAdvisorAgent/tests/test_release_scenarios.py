from __future__ import annotations

from pathlib import Path

from advisor_core.knowledge import (
    load_legacy_migration_bundle,
    load_release_scenario_suite,
    run_release_scenarios,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SCENARIO_PATH = (
    REPOSITORY_ROOT / "knowledge" / "scenarios" / "release-safety-v1.yaml"
)
MIGRATION_PATH = (
    REPOSITORY_ROOT
    / "knowledge"
    / "migrations"
    / "coding-platform-v3.json"
)


def test_release_scenarios_cover_all_required_safety_dimensions():
    suite = load_release_scenario_suite(SCENARIO_PATH)
    migration, _, _ = load_legacy_migration_bundle(MIGRATION_PATH)

    results = run_release_scenarios(suite, migration)
    result_by_id = {result.scenario_id: result for result in results}

    assert len(results) == 6
    for scenario in suite.scenarios:
        result = result_by_id[scenario.id]
        assert result.after_valid is scenario.expected_valid
        assert set(scenario.expected_issue_codes) <= set(result.issue_codes)
        if scenario.expected_before_valid is not None:
            assert result.before_valid is scenario.expected_before_valid

    assert result_by_id["scenario:release-positive"].issue_codes == ()
