---
type: platform-component
title: Safety-Critical Code Evaluation
description: domain-specific model capability evaluation framework for safety-critical code — AUTOSAR/ISO 26262, IEC 62304, DO-178C — with evaluation criteria, human expert roles, and deployment decision patterns specific to functional safety domains
group: quality
tags: [quality, safety-critical, autosar, iso-26262, iec-62304, do-178c, asil, functional-safety, automotive, medical-device, aerospace, model-eval]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [autosar, iso-26262, iec-62304, do-178c, asil, functional-safety, safety-critical-code, automotive-software, medical-device-firmware, aerospace-software, certified-software, safety-standard]
decision-question: "Does your codebase include software certified or being developed for functional safety standards — AUTOSAR ISO 26262 (automotive), IEC 62304 (medical device), DO-178C (aerospace) — where model errors are not just quality issues but potential safety violations with regulatory and liability consequences?"
---

Safety-critical software operates under functional safety standards that govern
how code is written, reviewed, changed, and validated. These standards exist
because errors in safety-critical code can cause injury or death. For a coding
agent platform, this creates a qualitatively different evaluation requirement
compared to general commercial code:

- **The cost of a false positive is not just a bad suggestion** — a model
  hallucination in web code wastes a developer's time; a model hallucination
  in ASIL-D automotive code or IEC 62304 Class C medical firmware could introduce
  a safety defect that passes code review because it looks plausible but violates
  a subtle timing or memory constraint
- **Safety standards have specific coding rules** — MISRA C, AUTOSAR C++14
  guidelines, IEC 61508 coding requirements — models have minimal training data
  on these rules and routinely suggest code that violates them
- **Safety certification is affected by tool qualification** — using an AI tool
  to generate certified code may require the tool itself to be qualified under
  ISO 26262 Part 8 (software tool qualification) or DO-178C Tool Qualification;
  this is a regulatory question that must be answered before deployment

> **Critical pre-deployment requirement:** Consult your functional safety manager
> and (for DO-178C) your DER (Designated Engineering Representative) before
> deploying the agent to any safety-critical population. Tool qualification
> requirements may affect the deployment model. This is not a platform team
> determination — it is a safety engineering and regulatory determination.

## Safety Standards Quick Reference

| Standard | Domain | Levels | Key coding constraint |
|---|---|---|---|
| ISO 26262 | Automotive (road vehicles) | ASIL A/B/C/D (D = highest) | MISRA C/C++ compliance; AUTOSAR C++14 guidelines; no dynamic memory allocation at ASIL-C/D |
| IEC 62304 | Medical device software | Class A/B/C (C = highest) | IEC 61508 coding guidelines; formal software lifecycle; full traceability from requirement to code |
| DO-178C | Aerospace (airborne systems) | DAL A/B/C/D/E (A = highest) | MC/DC coverage requirements; no dead code; tool qualification for any automated tool affecting certification artifacts |
| IEC 61508 | Industrial/functional safety (generic) | SIL 1/2/3/4 | Coding standards per SIL level; formal methods at high SIL |
| EN 50128 | Rail (software for railway control) | SIL 0/1/2/3/4 | Subset of IEC 61508; specific to rail |

## What "Safety-Critical Evaluation" Adds to Model-Capability-Eval.md

The generic `model-capability-eval.md` provides the 6-step evaluation framework.
This node adds safety-domain-specific content for each step:

### Step 1 — Safety-Domain Task Definition

Tasks to evaluate differ from general code evaluation:

| General code task | Safety-critical equivalent |
|---|---|
| Autocomplete | Autocomplete that does NOT violate MISRA C / AUTOSAR C++ rules |
| Bug explanation | Explain whether this code violates a specific safety coding rule (e.g., MISRA Rule 17.3 — no variadic functions) |
| Code review | Identify ASIL/Class violations in a module: dynamic memory, banned functions, unchecked return values, missing error handling |
| Refactoring | Refactor a module while preserving ASIL compliance; verify no new rule violations introduced |
| Documentation | Generate AUTOSAR Software Component Description (ARXML) or IEC 62304 software item description |
| Test generation | Generate MC/DC-adequate test cases for DO-178C; or AUTOSAR unit tests exercising timing constraints |

**DO NOT include in the evaluation** tasks the agent should never perform
regardless of capability: direct writes to certification artifacts, modification
of requirements traceability matrices, changes to verified baseline code.

### Step 2 — Evaluation Dataset Construction

Safety-domain evaluation datasets require domain expert involvement from the start:

- Source files: real AUTOSAR modules (SWCs, RTE, BSW) or IEC 62304 firmware modules
  from the actual codebase (with appropriate IP and regulatory review)
- Known violations: introduce specific MISRA/AUTOSAR violations into known-good
  code; the model must detect them; violations should span rule categories (memory,
  control flow, type safety, banned functions)
- Known-compliant code: include code that is correct and compliant; the model
  must NOT flag it as a violation (false positive rate matters — safety engineers
  who see too many false positives will stop using the tool)
- Edge cases specific to the domain: AUTOSAR timing budgets, interrupt service
  routine constraints, IEC 62304 software item boundary conditions
- Minimum dataset size: 30 test cases for each task type; at least 10 from each
  difficulty tier (routine / moderate / expert)

### Step 3 — Pass Criteria for Safety Domains

Safety domain pass criteria are stricter than general code:

| Task | General pass criterion | Safety-critical pass criterion |
|---|---|---|
| MISRA violation detection | >60% defects caught | >80% violations detected; false positive rate <15% |
| Compliant code generation | >70% compilable | >90% compilable AND >80% MISRA-clean on static analysis |
| Safety-rule explanation accuracy | >70% accurate | >85% accurate (wrong safety rule explanations are dangerous) |
| Refactoring safety preservation | >70% equivalent | >90% equivalent + static analysis confirms no new violations |
| Expert acceptability | >80% acceptable | >90% acceptable; "acceptable" means a safety engineer would not need to rework the suggestion |

**Hard stop criteria** (if these thresholds are not met, do not deploy for this task):
- Any task where the model generates code violating ASIL-D / Class C / DAL-A rules
  in more than 10% of cases — do not deploy that task type
- Any task where the model confidently explains a safety rule incorrectly — do not
  deploy explanation tasks; a wrong explanation from a confident model is worse than
  no explanation

### Step 4 — Human Expert Evaluator Role

Safety evaluations cannot be run without domain experts. The general eval framework
allows non-expert platform team members to run evaluations with metrics. Safety-critical
evaluation requires:

- **Safety engineer as primary evaluator** — at least one IEC/ISO/DO-certified
  safety engineer (FSAE, TÜV certification, or equivalent) who has worked on the
  specific standard must review every evaluation output; they determine whether
  the model's output would be acceptable in a real certification context
- **Two-person review for ambiguous outputs** — outputs in the moderate-difficulty
  tier that are borderline (would a safety engineer accept this?) must be reviewed
  by two safety engineers; disagreement logged and counted as a fail
- **Static analysis as ground truth** — for compliance-checking tasks (does this
  code violate MISRA?), run a qualified static analysis tool (PC-lint, Polyspace,
  or LDRA) as the ground truth for comparison; the model's output is compared
  against the tool's findings; discrepancies are recorded

### Step 5 — Tool Qualification Assessment

Before the evaluation results can be used to justify deployment, the functional
safety team must assess whether the agent requires tool qualification under the
applicable standard:

**ISO 26262 Part 8 — Software Tool Qualification:**
- Tool classification depends on whether incorrect behavior by the tool could
  introduce errors into the safety element without detection
- A coding agent that generates ASIL-C/D code and the developer may accept without
  exhaustive review is likely a TI3 (Tool Impact 3) tool requiring qualification
  or mitigation measures
- The functional safety manager makes this determination; document it in the
  tool qualification plan

**DO-178C Tool Qualification:**
- Any tool whose output is used without independent verification as a certification
  artifact may require qualification under DO-330 (Software Tool Qualification)
- An agent that generates MC/DC test cases that are used as certification evidence
  without independent verification is a qualification candidate
- The DER (Designated Engineering Representative) provides guidance; document
  the determination

**If tool qualification is required but not performed:**
- The agent may still be used, but its outputs cannot be used as certification artifacts
- Deployment is possible in a "read-only + suggestion" mode where the developer
  uses the agent as an assistant but all work is independently verified
- Document this explicitly in the deployment decision

### Step 6 — Deployment Decision Framework for Safety Domains

Three outcomes — more conservative than general code:

- **Deploy read-only + explanation only** — agent explains code, identifies
  potential issues, generates documentation; never writes to safety-critical files;
  requires no tool qualification; safe initial deployment for all safety populations
- **Deploy with human expert review gate** — agent can suggest code changes;
  every suggestion on safety-critical files requires review and approval by a
  certified safety engineer before commit; tool qualification may still be required
  depending on the standard and level; check with safety manager
- **Do not deploy for this task** — if evaluation results fall below the hard
  stop criteria, do not enable that task type for this population; revisit when
  a new model version is available with better domain capability

## Principles

- Default to read-only for all safety-critical populations until evaluation is
  complete — the cost of a missed evaluation is a safety defect in certified code;
  the cost of delaying deployment by 4-6 weeks for the evaluation is low
- Tool qualification is a safety engineering question, not a platform question —
  the platform team does not determine whether the agent requires ISO 26262 or
  DO-178C tool qualification; the functional safety manager and DER do; do not
  proceed to code-writing deployment without their determination in writing
- A capable model with wrong safety knowledge is more dangerous than a less
  capable model — a model that confidently explains an AUTOSAR rule incorrectly
  will mislead a developer who trusts it; measure and gate on explanation accuracy,
  not just code generation quality
- Safety engineers are the evaluator, not the platform team — the platform team
  builds the evaluation harness and runs the logistics; safety engineers provide
  the ground truth for every evaluation outcome; no safety evaluation is valid
  without safety engineer sign-off on the results
- Static analysis is the objective benchmark, not human preference — for
  compliance-checking tasks, the qualified static analysis tool is the ground
  truth; model output that matches static analysis findings is correct; model
  output that contradicts static analysis is a failure, regardless of how
  plausible it looks

## Stack Options

**Evaluation harness**
- Amazon Bedrock Model Evaluation + custom safety evaluator — Bedrock Model
  Evaluation handles the task batching and result collection; a custom Lambda
  evaluator calls the static analysis tool API (PC-lint, Polyspace) to score
  model outputs against the ground truth; results aggregated in S3 for safety
  engineer review
- GitHub Actions evaluation pipeline — run the safety evaluation as a CI
  workflow; each evaluation dataset item is a test case; model output is compared
  against static analysis ground truth; results reported as a GitHub Actions
  artifact; safety engineers review the artifact before deployment approval

**Static analysis integration (ground truth)**
- PC-lint Plus (LDRA) — MISRA C/C++ checker; command-line invocable; wrap in a
  Lambda that takes a code snippet and returns MISRA violations; use as the
  ground-truth evaluator for compliance-checking tasks
- Polyspace Code Prover / Bug Finder (MathWorks) — formal verification and MISRA
  checking for C/C++; requires license; suitable for organizations already using
  MathWorks tools in their safety workflow
- CodeSonar (GrammaTech) — static analysis for C/C++; MISRA and AUTOSAR rule
  checking; CI-integrable; wrap as a ground-truth tool in the evaluation pipeline

**Safety engineer review workflow**
- Amazon A2I (Augmented AI) — human review tasks assigned to named safety
  engineers; structured review form (compliant / non-compliant / uncertain);
  results stored in S3; audit trail of who reviewed what and when
- GitHub PR-based review — evaluation results posted as a GitHub PR comment;
  safety engineers review in GitHub; approval closes the PR and records the
  reviewer identity; lower setup overhead than A2I

**Tool qualification documentation**
- Confluence safety tool qualification plan template — document the tool
  classification assessment (TI class, TD class for ISO 26262; Tool Qualification
  Level for DO-178C); link to evaluation results as qualification evidence;
  reviewed by functional safety manager and (for DO-178C) DER

## Connects to

- [Model Capability Evaluation](model-capability-eval.md) — this node extends
  the generic 6-step evaluation framework with safety-domain-specific criteria;
  run the generic framework first to establish the baseline, then apply the
  safety-specific criteria from this node
- [Permission Engine](../harness/perms.md) — safety-critical repos get a
  permission override: write tools removed from the allowlist regardless of
  developer role; this is enforced at the registry level, not as a guardrail
- [Legal Hold & E-Discovery](../access/legal-hold.md) — safety certification
  records (test results, evaluation artifacts, tool qualification plans) may
  have retention requirements similar to legal hold; design the retention policy
  to cover both regulatory and legal scenarios

## Sources

- [ISO 26262 Road vehicles — Functional safety](https://www.iso.org/standard/68383.html) — consult functional safety manager; do not interpret directly for platform design
- [IEC 62304 Medical device software — Software life cycle processes](https://www.iec.ch/store/publish/mwh_6.htm) — consult medical device safety engineer and regulatory affairs
- [DO-178C Software Considerations in Airborne Systems and Equipment Certification](https://www.rtca.org/content/do-178c) — consult DER and aerospace safety engineer
- [MISRA C:2012 Guidelines for the use of the C language in critical systems](https://www.misra.org.uk/) — to verify on first use — coding rules; basis for safety-critical C evaluation criteria
- [ISO 26262-8 §11 — Software tool qualification](https://www.iso.org/standard/68387.html) — tool qualification criteria; TI/TD classification methodology
