# Platform Architecture Studio Demo

Standalone architecture-first demo for an enterprise coding-agent platform
advisor. It does not import or modify the existing Platform Advisor runtime.

## Run

```bash
npm install
npm run dev
```

Open `http://localhost:4173/`.

## What It Demonstrates

- Starts with a logical architecture instead of an empty questionnaire.
- Asks five high-impact architecture decisions.
- Updates the architecture after every answer.
- Introduces AWS, open-source, SaaS, and provider implementation candidates.
- Shows illustrative token economics and cost per successful task.
- Defines outcome SLOs such as accepted changes, rework, intervention, cycle
  time, and unit economics.
- Exports the current state as a JSON decision packet.

All recommendation behavior is deterministic and lives in `src/catalog.ts` and
`src/engine.ts`. The planning economics are explicitly illustrative.

## Validate

```bash
npm test
npm run build
```
