# ArchitectureCase Migration Note

`ArchitectureCase` is a shadow contract for converging the current advisory state
without a big-bang runtime rewrite. The adapter lives in
`architecture_case.py` and reads the existing workspace plus the latest canvas
snapshot.

## Current overlap

| Current artifact | What it currently holds | Problem |
| --- | --- | --- |
| `workspace` | facts, assumptions, questions, recommendation, decisions, risks, blueprint text | already carries the advisory state, but mixes working memory with rendered artifacts |
| `workspace.advisory_case` | structured executive recommendation, alternatives, decisions, risks, readout, output pack | duplicates `workspace` decisions/risks/recommendation with a different shape |
| `workspace.blueprint_markdown` | technical blueprint body | separate document that can drift from current decisions |
| canvas `nodes` / `edges` | rendered architecture topology | shape is separate from the recommendation state |
| canvas `architecture_artifact` | executive summary, decisions, risks, rollout, lanes | duplicates decision/risk summaries again, but attached to the diagram payload |

## Adapter precedence

`ArchitectureCase` resolves the current overlap with these rules:

1. Reconcile `workspace` first with `reconcile_workspace_state(...)`.
2. Treat `question_state` as authoritative for open questions.
3. Treat `workspace` as the authoritative current recommendation, stage, facts,
   assumptions, and operating model.
4. Use `workspace.advisory_case` as the primary structured source for decisions,
   risks, and executive outputs when present.
5. Use canvas `nodes` / `edges` as the primary source for architecture
   components and relationships.
6. Use canvas `architecture_artifact` only as a supplement for diagram summary,
   rollout, and any decision/risk entries not already present in the reconciled
   workspace state.

## Field mapping

| Legacy field | ArchitectureCase field |
| --- | --- |
| `workspace.stage` | `stage` |
| `workspace.recommendation` | `current_recommendation` |
| `workspace.operating_model` | `operating_model` |
| `workspace.facts` + `workspace.traversal_state.structured_facts` | `facts[]` |
| `workspace.assumptions` | `assumptions[]` |
| `workspace.question_state` | `open_questions[]` |
| `workspace.decisions` + `workspace.advisory_case.decisions` + `canvas.architecture_artifact.decisions` | `decisions[]` |
| `workspace.risks` + `workspace.advisory_case.risks` + `canvas.architecture_artifact.risks` | `risks[]` |
| canvas `nodes` | `architecture_components[]` |
| canvas `edges` | `relationships[]` |
| `workspace.blueprint_markdown` | `artifacts.blueprint_markdown` |
| `workspace.advisory_case.output_pack.executive_summary` | `artifacts.executive_summary` |
| `workspace.advisory_case.output_pack.recommendation_memo` | `artifacts.recommendation_memo` |
| `workspace.advisory_case.output_pack.architecture_narrative` | `artifacts.architecture_narrative` |
| `canvas.architecture_artifact.executive_summary` | `artifacts.diagram_summary` |
| `workspace.artifact_status` + `workspace.traversal_state.*` | `observability.*` and `evaluation.*` |

## Minimum observability / eval contract

The case carries only the fields needed for deterministic review and later
integration:

- `revision`
- `okf_release_id`
- `evidence_refs[]`
- `observability.active_decision_path`
- `observability.decision_focus`
- `observability.candidate_option_paths`
- `observability.missing_evidence`
- `observability.artifact_status`
- `evaluation.blocking_question_count`
- `evaluation.decision_count`
- `evaluation.evidence_ref_count`
- `evaluation.has_blueprint`
- `evaluation.has_architecture_snapshot`

## Recommended migration path

1. Build and persist `ArchitectureCase` alongside the current workspace write,
   without changing any frontend or prompt contracts yet.
2. Switch blueprint, executive brief, and architecture compilation to derive
   from `ArchitectureCase` instead of directly from `workspace` and canvas
   payloads.
3. Move decision/evidence persistence to first-class case fields.
4. Remove duplicated decision/risk/document payloads from legacy artifacts once
   downstream consumers read the case directly.
