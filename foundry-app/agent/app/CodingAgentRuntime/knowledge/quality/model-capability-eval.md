---
type: platform-component
title: Model Capability Evaluation
description: structured framework for evaluating whether frontier coding models are useful for domain-specific codebases — HDL/Verilog, embedded C, assembly, proprietary DSLs, and other non-standard code domains
group: quality
tags: [quality, model-eval, capability-evaluation, hdl, verilog, embedded-c, assembly, dsl, domain-specific, llm-evaluation, bedrock-evaluation]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [model-evaluation, capability-eval, hdl, verilog, embedded-c, assembly, dsl, firmware, domain-specific-code, model-fit, pre-deployment-eval, hardware-code]
decision-question: "Does your codebase contain domain-specific languages, hardware description languages, embedded firmware, or other non-standard code that requires a structured evaluation before committing to a model or deploying the platform — rather than assuming frontier models will be effective?"
decision-domain: quality_gate
priority: 8
blocking: true
requires: [quality/evals]
---

Frontier coding models are trained primarily on publicly available source code,
which skews heavily toward web technologies, Python, Java, TypeScript, and common
open-source projects. For domain-specific codebases — Verilog/SystemVerilog for
chip design, VHDL for FPGAs, embedded C for real-time systems, assembly for
firmware, or proprietary DSLs — the model's capability is an open empirical
question, not an assumption.

Deploying a coding agent platform without validating model capability on
domain-specific code is a reliability risk: developers will adopt the platform,
encounter poor-quality suggestions, and distrust the platform. The cost of a
poor initial experience is high and hard to recover from.

A model capability evaluation is a structured, measurable pre-deployment activity
that answers: **for our specific codebase and developer workflows, which model
performs well enough to deploy, and on which tasks?**

## When This Node Applies

Trigger this evaluation if your codebase includes any of the following:

| Domain | Examples | Why it's harder for models |
|---|---|---|
| Hardware description languages | Verilog, SystemVerilog, VHDL, Chisel | Timing constraints, synthesis semantics, simulation vs synthesis differences not well represented in training data |
| Embedded/real-time firmware | Bare-metal C, RTOS C, interrupt service routines, DMA drivers | Hardware-specific semantics, register maps, timing-critical code patterns |
| Assembly | x86 assembly, ARM assembly, RISC-V assembly | Low-level representations; model errors are subtle and dangerous |
| Proprietary DSLs | Internal scripting languages, custom build systems, domain-specific config languages | Model has never seen them; few/no examples in training data |
| Safety-critical code | Automotive (AUTOSAR), aerospace (DO-178C), medical device firmware | Model suggestions may be syntactically correct but violate safety coding standards |
| Legacy languages | COBOL, Fortran, Ada, PL/1 | Sparse training representation; high hallucination risk on edge cases |

## The Evaluation Framework

### Step 1 — Define Evaluation Tasks

Before running any model queries, define the specific tasks the platform will be
used for, matched to the domain:

| Platform use case | Evaluation task type |
|---|---|
| Code completion (autocomplete) | Single-line and multi-line completion accuracy in domain language |
| Bug explanation | Explain a known bug in a domain-specific file; assess accuracy |
| Code review (read-only) | Identify real defects introduced into known-good domain code |
| Refactoring | Refactor a module; verify functional equivalence |
| Test generation | Generate testbench (Verilog) or unit test (embedded C); assess compilability and coverage |
| Documentation | Generate comments for a complex routine; assess accuracy |

Prioritize the tasks your developers will actually use. Don't evaluate tasks you
won't deploy.

### Step 2 — Build an Evaluation Dataset

- Sample 20–50 real files from your domain-specific codebase (with IP clearance)
- For each evaluation task type, construct 10–20 test cases with known-good answers
- Include edge cases that are domain-specific: timing constraints in Verilog,
  memory-mapped register access in embedded C, interrupt safety patterns
- Tag each test case with difficulty: routine / moderate / expert

### Step 3 — Define Pass Criteria Before Running Evals

Decide what "good enough" means before you see the results:

| Criterion | Example threshold | Notes |
|---|---|---|
| Compilability | >90% of generated code compiles without modification | Non-negotiable for autocomplete use case |
| Functional correctness | >70% of refactored code passes existing testbench | Measured by running the testbench |
| Defect detection rate | >60% of introduced defects identified in code review task | Compared to expert human baseline |
| Hallucination rate | <10% of explanations contain factually incorrect domain statements | Evaluated by domain expert review |
| Expert acceptability | >80% of outputs rated acceptable by domain expert evaluator | Qualitative gate alongside quantitative metrics |

### Step 4 — Run the Evaluation Systematically

Run each task type against each candidate model. For coding agents specifically,
evaluate at three levels:

1. **Prompt-level**: Submit the task as a single prompt; measure raw model output quality
2. **Tool-call level**: Use the model in an agentic loop with file-read tools; measure
   the quality of the agent's proposed changes
3. **Session-level**: Run a realistic developer scenario end-to-end; measure whether
   the developer accepted or rejected the agent's suggestions

### Step 5 — Segment Results by Task and Difficulty

Do not aggregate to a single score. A model may excel at code explanation (high
value for HDL developers) but fail at synthesis-correct generation (unsafe to
deploy). Report results as a capability matrix:

| Task | Model A | Model B | Human baseline |
|---|---|---|---|
| Verilog completion | 62% compilable | 78% compilable | — |
| RTL bug explanation | 71% accurate | 83% accurate | 94% accurate |
| Testbench generation | 45% runs correctly | 61% runs correctly | — |
| AUTOSAR rule compliance | 38% violations caught | 52% violations caught | 89% violations caught |

### Step 6 — Make the Deployment Decision

Three outcomes:

- **Deploy with task scoping** — the model is good enough for some tasks (explanation,
  read-only review) but not others (code generation, refactoring); configure the
  platform to surface the model only for approved task types in this domain
- **Deploy with disclaimer and human-in-the-loop gate** — model quality is marginal;
  acceptable if every suggestion goes through domain expert review before use; set
  expectations explicitly with developers
- **Do not deploy for this domain** — model quality is insufficient; deploying will
  cause more harm than benefit; revisit when a new model version is available

## Decisions

**Which models do you evaluate?**
- Frontier models available on Bedrock — Claude Sonnet/Opus, GPT-4o and GPT-5.x
  variants on Bedrock, Amazon Nova; evaluate the models you intend to deploy, not
  the most capable model available; a model you can't use at scale due to cost
  doesn't need to be in the eval
- Model family evaluation — evaluate one or two members of each family (e.g., Haiku
  and Opus from Claude) to understand the capability curve vs cost tradeoff within
  the family; the T1/T2/T3 tier model (see model-tiering.md) may apply differently
  for domain-specific code
- Fine-tuned model as a candidate — if a fine-tuned model has been created for the
  domain (e.g., a Verilog-specific fine-tuned model), include it in the evaluation;
  Bedrock custom model import supports fine-tuned weights

**Who runs the evaluation?**
- Domain expert + platform team joint evaluation — the platform team builds the
  evaluation harness; domain experts (senior HDL engineers, firmware leads) evaluate
  output quality; neither team can do this alone; the platform team does not know
  what correct Verilog looks like; the domain experts do not know how to set up
  a systematic evaluation
- External eval partner — if neither team has bandwidth, engage an external partner
  who specializes in LLM evaluation for domain-specific code; provides independence
  but adds cost and timeline

**How frequently is the evaluation run?**
- On platform deployment — always; do not skip the pre-deployment eval
- On major model version release — re-run the evaluation when the model version
  changes significantly; model updates can improve or degrade domain-specific
  performance
- On codebase evolution — if the codebase adds a new domain (e.g., an acquisition
  brings FPGA firmware), run the evaluation for the new domain before enabling
  agent access

## Principles

- Default assumption is that frontier models are not adequate for specialized domains —
  prove capability before deployment, not after; the burden of proof is on the eval,
  not on optimism about model quality
- Capability is task-specific, not model-specific — a model that is poor at
  Verilog generation may be excellent at Verilog explanation; report and deploy
  at the task level
- The evaluation dataset is a platform asset — maintain it in a repository, version
  it, and add cases as new domain patterns emerge; it becomes the regression suite
  for model updates
- Human baseline is essential for calibration — always include a human expert
  baseline in the evaluation; it sets the ceiling and helps interpret whether
  model scores are acceptable or just the best available option
- Do not evaluate features you won't deploy — keep the evaluation scoped to the
  actual platform use cases; a comprehensive academic benchmark is not the goal;
  a deployment decision is the goal

## Stack Options

**Evaluation harness**
- Amazon Bedrock Model Evaluation — managed evaluation service; supports custom
  datasets; built-in metrics (accuracy, robustness, toxicity); human evaluation
  workflow via Amazon Mechanical Turk or private reviewer pool; results in a
  structured report; recommended for standard evaluation tasks
- Bedrock Knowledge Bases + custom eval Lambda — for task-level evaluation where
  you need to test retrieval-augmented generation quality; Lambda invokes Bedrock
  with a retrieved code context; compares output against ground truth; results
  logged to S3 for analysis
- LangSmith (LangChain) — open-source evaluation framework; supports custom
  evaluators, dataset management, and run tracking; deploy as a container on ECS
  or App Runner; integrates with LangChain agent harnesses; good fit if the
  platform uses LangChain
- RAGAS — open-source RAG evaluation framework; useful for evaluating code
  retrieval quality from the knowledge layer (code-intelligence.md); measures
  context precision, context recall, answer relevance; runs as a Python package

**Evaluation dataset management**
- S3 with versioned prefix per eval run — store evaluation datasets and results
  in S3; prefix by `eval-run-id`; retain all historical runs for trend analysis;
  accessible to both domain expert reviewers and the platform team
- AWS Glue + Athena — for querying evaluation results across runs; build a
  capability trend dashboard in QuickSight; track metric improvement across model
  versions over time

**Domain expert review workflow**
- Amazon A2I (Augmented AI) — human review workflow managed by AWS; domain experts
  complete review tasks in a structured UI; results flow back to the evaluation
  pipeline; audit trail of who reviewed what and when
- Custom review app on Amplify — simpler alternative if A2I overhead is too high;
  a simple web form where domain experts rate model outputs; results stored in
  DynamoDB; sufficient for small-scale evaluations (< 500 items)

**Fine-tuned model hosting**
- Bedrock custom model import — import a fine-tuned model (LoRA or full fine-tune)
  into Bedrock; invoke via the same Bedrock API as foundation models; no separate
  inference infrastructure; fine-tuned model becomes a Bedrock model ID; evaluate
  alongside foundation models in the same harness

## Connects to

- [Model Tiering](../gateway/model-tiering.md) — evaluation results inform tier
  assignment for domain-specific code; a model that excels at HDL explanation
  but fails at HDL generation maps to T1 (explanation tasks) not T2/T3
- [Code Intelligence](../knowledge-layer/code-intelligence.md) — RAG retrieval
  quality for domain-specific code is a separate evaluation axis; the model may
  be capable but retrieval may surface the wrong context; evaluate retrieval
  quality independently
- [Guardrails & Policy](guardrails.md) — safety-critical code domains (AUTOSAR,
  DO-178C) require guardrail rules that block the agent from suggesting code
  patterns that violate domain safety standards; guardrails complement model
  capability evaluation — a capable model with no safety guardrails is still a risk
- [Security Posture](security-posture.md) — model hallucinations in
  safety-critical domains (firmware, hardware) have a different risk profile
  than hallucinations in web code; security posture assessment must account
  for domain-specific failure modes

## Sources

- [Amazon Bedrock Model Evaluation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation.html) — to verify on first use — managed evaluation service; custom dataset support; human review integration
- [RAGAS — RAG evaluation framework](https://docs.ragas.io/) — to verify on first use — open-source; context precision, recall, answer relevance metrics
- [LangSmith — LLM evaluation](https://docs.smith.langchain.com/) — to verify on first use — dataset management, custom evaluators, run tracking
- [Bedrock custom model import](https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-import-model.html) — to verify on first use — hosting fine-tuned models alongside foundation models
