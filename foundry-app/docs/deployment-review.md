# Deployment Review Workflow

Run one command after a deploy and review the generated markdown report instead
of manually rerunning individual checks.

This repo now supports two complementary review modes:

- deterministic audit: catches obvious state and UI-surface mismatches quickly
- LLM judge: scores the outcome against the product vision and suggests missing features

## Commands

From the repo root:

```bash
make review-deploy
```

Strict mode:

```bash
make review-deploy-strict
```

LLM judge prompt/report generation:

```bash
make review-judge
python3 scripts/review-judge.py --scenario-id strategy-blueprint
```

Optional Bedrock-backed judge run:

```bash
python3 scripts/review-judge.py --scenario-id strategy-blueprint --profile your-aws-profile --bedrock-model-id your-model-id
```

Seed a deterministic review session into the real app UI:

```bash
python3 scripts/seed-review-scenario.py --scenario-id strategy-blueprint --profile your-aws-profile --app-url https://your-frontend-url
```

Direct script usage:

```bash
./scripts/deployment-review.sh --deployed-url https://your-frontend-url
./scripts/deployment-review.sh --strict --deployed-url https://your-frontend-url --api-url https://your-api-url
```

## What It Runs

- `frontend` production build
- seeded frontend review audit
- strict seeded review audit when `--strict` is used
- backend `pytest` suite if `pytest` is installed
- agent runtime `pytest` suite if `pytest` is installed
- optional `curl` probes against deployed frontend and API URLs

The deterministic audit now reviews component accuracy as well as artifact completeness:

- brief recommendation and confidence
- questions panel consistency
- assumptions coverage
- blueprint truthfulness, including derived-vs-published artifact state
- architecture visibility
- scenario-specific expectations such as `Codex` + `Bedrock`

## Output

Reports are written under:

```text
.reports/deployment-review/
```

The latest summary is copied to:

```text
.reports/deployment-review/latest.md
```

Each run also stores per-check logs so you can inspect failures without digging
through shell history.
