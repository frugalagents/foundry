# Platform Advisor V3 Foundation

This isolated package is the first architecture-first build slice. It does not
replace or import into the v1/v2 runtime.

Implemented:

- Immutable v3 records with stable IDs and deterministic serialization.
- A fail-closed JSON catalog compiler with reference, cycle, evidence-review,
  and critical-evidence freshness checks.
- A provider-neutral coding-platform catalog spanning nine planes, six
  deployment families, ten overlays, and the logical reference architecture.
- Progressive requirement patches with optimistic revision checks, typed
  values, unknown preservation, dependency closure, architecture deltas, and
  deterministic state hashes.
- Exact catalog-content pinning on every revision, dormant dependent answers,
  compile-time predicate validation, and fail-closed component conflicts.
- Explicit dependency edges and active rule evaluations for rendering and
  explaining the single evolving baseline.
- Focused question ranking with catalog-driven applicability and deterministic
  answer-by-answer component, edge, rule, and feasibility impact previews.
- A separate deployment-family assessment with stable feasible, rejected, and
  unknown outcomes; it never replaces the logical reference architecture.
- A versioned 24-scenario R0.1 suite covering positive, rejection, unknown, and
  one-variable-flip cases for every deployment family.

Run the headless proof:

```bash
PYTHONPATH=PlatformAdvisorAgent/app/PlatformAdvisorAgent \
python3 -m advisor_core.v3.demo --as-of 2026-07-30
```

The next slices add offering variants, compatibility, evidence-backed provider
adapters, controls, economics, outcome plans, and decision packets. The
production canvas and chat-to-patch translation remain deferred.
