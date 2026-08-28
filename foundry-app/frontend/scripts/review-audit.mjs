import fs from 'node:fs/promises'

const raw = await fs.readFile(new URL('../lib/review-scenarios.json', import.meta.url), 'utf8')
const scenarios = JSON.parse(raw)
const strictMode = process.argv.includes('--strict')

function hasOutputPackContent(pack) {
  return Boolean(
    pack?.executive_summary
    || pack?.recommendation_memo
    || pack?.architecture_narrative
    || (Array.isArray(pack?.key_decisions) && pack.key_decisions.length > 0)
    || (Array.isArray(pack?.risks_and_mitigations) && pack.risks_and_mitigations.length > 0)
    || (Array.isArray(pack?.rollout_30_90_180) && pack.rollout_30_90_180.length > 0)
    || (Array.isArray(pack?.operating_principles) && pack.operating_principles.length > 0)
    || (Array.isArray(pack?.control_checklist) && pack.control_checklist.length > 0)
  )
}

function normalizeText(value) {
  return String(value ?? '').toLowerCase().replace(/\s+/g, ' ').trim()
}

function stageOf(workspace) {
  const value = String(workspace?.stage ?? '').trim().toLowerCase()
  if (value === 'solutioning' || value === 'blueprint') return value
  return 'discovery'
}

function countBlockingQuestions(workspace) {
  const structured = Array.isArray(workspace?.question_state)
    ? workspace.question_state.filter((item) => item?.status === 'open' && item?.blocking)
    : []
  return structured.length > 0 ? structured.length : (workspace?.open_questions?.length ?? 0)
}

function hasDerivedBlueprint(workspace, architectureArtifact) {
  return Boolean(
    String(workspace?.recommendation ?? '').trim()
    || String(workspace?.blueprint_markdown ?? '').trim()
    || String(workspace?.architecture_case?.artifacts?.blueprint_markdown ?? '').trim()
    || String(architectureArtifact?.executive_summary ?? '').trim()
    || (workspace?.decisions?.length ?? 0) > 0
    || (workspace?.implementation_plan?.length ?? 0) > 0
  )
}

function resolveBlueprintMode(workspace, architectureArtifact) {
  if (String(workspace?.architecture_case?.artifacts?.blueprint_markdown ?? '').trim()) return 'published'
  if (String(workspace?.blueprint_markdown ?? '').trim()) return 'published'
  if (hasOutputPackContent(workspace?.advisory_case?.output_pack)) return 'published'
  return hasDerivedBlueprint(workspace, architectureArtifact) ? 'derived' : 'empty'
}

function recommendationCorpus(workspace, scenario) {
  return normalizeText([
    workspace?.recommendation,
    workspace?.recommendation_state?.primary_recommendation,
    workspace?.advisory_case?.recommendation?.summary,
    workspace?.advisory_case?.recommendation?.why_this,
    workspace?.advisory_case?.readout?.current_recommendation,
    workspace?.advisory_case?.output_pack?.executive_summary,
    workspace?.advisory_case?.output_pack?.recommendation_memo,
    scenario?.architectureArtifact?.executive_summary,
    workspace?.blueprint_markdown,
    workspace?.architecture_case?.artifacts?.blueprint_markdown,
  ].join('\n'))
}

function recommendedOptionCorpus(workspace) {
  const recommended = Array.isArray(workspace?.recommendation_state?.candidate_options)
    ? workspace.recommendation_state.candidate_options
      .filter((item) => item?.position === 'recommended')
      .map((item) => `${item?.title ?? ''} ${item?.summary ?? ''}`)
    : []
  return normalizeText(recommended.join('\n'))
}

function push(items, component, severity, title) {
  items.push([component, severity, title])
}

function auditScenario(scenario) {
  const workspace = scenario.workspace ?? {}
  const stage = stageOf(workspace)
  const hasArchitecture = (scenario.canvas?.nodes?.length ?? 0) > 0 || Boolean(scenario.architectureArtifact)
  const blueprintMode = resolveBlueprintMode(workspace, scenario.architectureArtifact)
  const confidence = workspace?.advisory_case?.recommendation?.confidence || workspace?.recommendation_state?.confidence || ''
  const blockingQuestions = countBlockingQuestions(workspace)
  const items = []

  if (!Array.isArray(scenario.transcript) || scenario.transcript.filter((message) => message.role === 'agent').length === 0) {
    push(items, 'transcript', 'critical', 'No advisor output in transcript')
  }

  if (!String(workspace?.recommendation ?? '').trim()) {
    push(items, 'brief', 'critical', 'Recommendation missing')
  }

  if (stage !== 'discovery' && !hasArchitecture) {
    push(items, 'architecture', 'critical', 'Solutioning without architecture')
  }

  if (stage === 'blueprint' && blueprintMode === 'empty') {
    push(items, 'blueprint', 'critical', 'Blueprint stage without blueprint artifact')
  }

  if (stage === 'blueprint' && blueprintMode === 'derived') {
    push(items, 'blueprint', 'critical', 'Blueprint panel is still showing a derived draft')
  } else if (stage !== 'discovery' && blueprintMode === 'derived') {
    push(items, 'blueprint', 'warning', 'Blueprint panel is showing inferred content')
  }

  if (stage === 'blueprint' && blockingQuestions > 0) {
    push(items, 'questions', 'warning', 'Blueprint still has blocking questions')
  }

  if (stage !== 'discovery' && (workspace?.decisions?.length ?? 0) === 0) {
    push(items, 'brief', 'warning', 'Decisions are not captured')
  }

  if (stage !== 'discovery' && (workspace?.risks?.length ?? 0) === 0) {
    push(items, 'brief', 'warning', 'Risk register is empty')
  }

  if (stage === 'blueprint' && (workspace?.implementation_plan?.length ?? 0) === 0) {
    push(items, 'blueprint', 'warning', 'No rollout plan in blueprint stage')
  }

  if (stage !== 'discovery' && (workspace?.facts?.length ?? 0) < 2) {
    push(items, 'brief', 'note', 'Thin evidence trail')
  }

  if (stage !== 'discovery' && !confidence) {
    push(items, 'brief', 'note', 'Confidence signal missing')
  }

  if (confidence === 'high' && blockingQuestions > 0) {
    push(items, 'brief', 'warning', 'Confidence overstates readiness')
  }

  const expectations = scenario.expectations ?? {}
  const recCorpus = recommendationCorpus(workspace, scenario)
  const optionCorpus = recommendedOptionCorpus(workspace)

  if (expectations.required_stage && stage !== expectations.required_stage) {
    push(items, 'workspace', 'critical', 'Scenario ended in the wrong stage')
  }

  if (expectations.required_confidence && confidence !== expectations.required_confidence) {
    push(items, 'brief', 'critical', 'Scenario confidence target not met')
  }

  if (expectations.require_architecture && !hasArchitecture) {
    push(items, 'architecture', 'critical', 'Scenario requires an architecture view')
  }

  if (expectations.require_published_blueprint && blueprintMode !== 'published') {
    push(items, 'blueprint', 'critical', 'Scenario requires a published blueprint')
  }

  if (typeof expectations.max_open_questions === 'number' && blockingQuestions > expectations.max_open_questions) {
    push(items, 'questions', 'critical', 'Scenario has too many open questions')
  }

  for (const term of expectations.recommendation_must_include ?? []) {
    if (!recCorpus.includes(normalizeText(term))) {
      push(items, 'brief', 'critical', `Required recommendation signal missing: ${term}`)
    }
  }

  for (const term of expectations.recommendation_must_exclude ?? []) {
    if (recCorpus.includes(normalizeText(term))) {
      push(items, 'brief', 'critical', `Disallowed recommendation signal present: ${term}`)
    }
  }

  for (const term of expectations.recommended_option_must_include ?? []) {
    if (!optionCorpus.includes(normalizeText(term))) {
      push(items, 'brief', 'critical', `Recommended option is not explicit enough: ${term}`)
    }
  }

  for (const term of expectations.recommended_option_must_exclude ?? []) {
    if (optionCorpus.includes(normalizeText(term))) {
      push(items, 'brief', 'critical', `Recommended option includes a forbidden choice: ${term}`)
    }
  }

  return { items, blueprintMode, stage, confidence, blockingQuestions }
}

let criticalCount = 0

for (const scenario of scenarios) {
  const { items, blueprintMode, stage, confidence, blockingQuestions } = auditScenario(scenario)
  const isStrictGate = scenario.strict_gate !== false
  console.log(`${scenario.name} (${scenario.id})`)
  console.log(`  Stage: ${stage} | Confidence: ${confidence || 'unset'} | Blueprint: ${blueprintMode} | Blocking questions: ${blockingQuestions}`)
  if (!isStrictGate) {
    console.log('  INFO: advisory-only review scenario')
  }
  if (items.length === 0) {
    console.log('  PASS: no open items')
    console.log('')
    continue
  }

  for (const [component, severity, title] of items) {
    if (severity === 'critical' && (!strictMode || isStrictGate)) criticalCount += 1
    console.log(`  ${severity.toUpperCase()} [${component}]: ${title}`)
  }
  console.log('')
}

if (strictMode && criticalCount > 0) {
  process.exitCode = 1
}
