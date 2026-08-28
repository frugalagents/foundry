import { buildAssumptionCards } from './assumptions'
import { hasAdvisoryCaseContent } from './advisory-case'
import { normalizeWorkspace } from './message-analysis'
import { resolveBlueprintContent } from './session-export'
import rawReviewScenarios from './review-scenarios.json'
import type {
  ArchEdge,
  ArchNode,
  ArchitectureArtifact,
  ConsultingWorkspace,
  ConversationRow,
  Customer,
  Message,
  Session,
} from './types'
import { normalizeAdvisoryStage, type AdvisoryStage } from './workflow'

export type ReviewAuditSeverity = 'critical' | 'warning' | 'note'
export type ReviewAuditComponent =
  | 'brief'
  | 'questions'
  | 'assumptions'
  | 'blueprint'
  | 'architecture'
  | 'transcript'
  | 'workspace'

export interface ReviewAuditItem {
  component: ReviewAuditComponent
  severity: ReviewAuditSeverity
  title: string
  detail: string
  fix: string
}

export interface ReviewScenarioExpectation {
  required_stage?: AdvisoryStage
  required_confidence?: 'low' | 'medium' | 'high'
  require_architecture?: boolean
  require_published_blueprint?: boolean
  max_open_questions?: number
  recommendation_must_include?: string[]
  recommendation_must_exclude?: string[]
  recommended_option_must_include?: string[]
  recommended_option_must_exclude?: string[]
}

export interface ReviewScenario {
  id: string
  name: string
  strict_gate?: boolean
  summary: string
  vision: string
  success_criteria: string[]
  expectations?: ReviewScenarioExpectation
  customer: Customer
  session: Session
  transcript: Message[]
  workspace: ConsultingWorkspace
  architectureArtifact: ArchitectureArtifact | null
  canvas: {
    nodes: ArchNode[]
    edges: ArchEdge[]
    baselineNodeIds: string[]
  }
}

export interface ReviewScenarioMetrics {
  stage: AdvisoryStage
  hasArchitecture: boolean
  hasBlueprint: boolean
  blueprintMode: 'empty' | 'published' | 'derived'
  questionCount: number
  decisionCount: number
  riskCount: number
  implementationCount: number
  assumptionCount: number
  confidence: string
}

export const reviewScenarios = rawReviewScenarios as ReviewScenario[]

export function getReviewScenario(id: string | null | undefined) {
  if (!id) return reviewScenarios[0]
  return reviewScenarios.find((scenario) => scenario.id === id) ?? reviewScenarios[0]
}

export function buildReviewConversation(scenario: ReviewScenario): ConversationRow {
  return {
    customer: scenario.customer,
    session: scenario.session,
  }
}

export function measureReviewScenario(scenario: ReviewScenario): ReviewScenarioMetrics {
  const workspace = normalizeWorkspace(scenario.workspace)
  const advisoryCase = hasAdvisoryCaseContent(workspace.advisory_case) ? workspace.advisory_case : null
  const stage = normalizeAdvisoryStage(workspace.stage) ?? 'discovery'
  const hasArchitecture = scenario.canvas.nodes.length > 0 || Boolean(scenario.architectureArtifact)
  const blueprint = resolveBlueprintContent(workspace, scenario.architectureArtifact)
  const assumptions = buildAssumptionCards(workspace, scenario.architectureArtifact, scenario.canvas.nodes)
  const confidence = advisoryCase?.recommendation.confidence || workspace.recommendation_state?.confidence || ''

  return {
    stage,
    hasArchitecture,
    hasBlueprint: blueprint.mode !== 'empty',
    blueprintMode: blueprint.mode,
    questionCount: countBlockingQuestions(workspace),
    decisionCount: workspace.decisions.length,
    riskCount: workspace.risks.length,
    implementationCount: workspace.implementation_plan.length,
    assumptionCount: assumptions.length,
    confidence,
  }
}

export function auditReviewScenario(scenario: ReviewScenario): ReviewAuditItem[] {
  const workspace = normalizeWorkspace(scenario.workspace)
  const metrics = measureReviewScenario(scenario)
  const advisoryCase = hasAdvisoryCaseContent(workspace.advisory_case) ? workspace.advisory_case : null
  const blueprint = resolveBlueprintContent(workspace, scenario.architectureArtifact)
  const items: ReviewAuditItem[] = []
  const blockingQuestions = countBlockingQuestions(workspace)
  const structuredBlockingQuestions = (workspace.question_state ?? []).filter((item) => item.status === 'open' && item.blocking)
  const staleNextQuestion = Boolean(
    workspace.recommendation_state?.next_best_question
    && blockingQuestions === 0,
  )

  if (scenario.transcript.filter((message) => message.role === 'agent').length === 0) {
    items.push(makeItem(
      'transcript',
      'critical',
      'No advisor output in transcript',
      'The review scenario has no agent message to explain the current state.',
      'Seed at least one advisor response so the review surface shows the interaction model, not just the artifact panels.',
    ))
  }

  if (!workspace.recommendation.trim()) {
    items.push(makeItem(
      'brief',
      'critical',
      'Recommendation missing',
      'The brief has no primary recommendation to summarize.',
      'Publish a concise recommendation as soon as the advisor has minimum sufficient evidence.',
    ))
  }

  if (metrics.stage !== 'discovery' && !metrics.hasArchitecture) {
    items.push(makeItem(
      'architecture',
      'critical',
      'Solutioning without architecture',
      'The session advanced beyond discovery, but the architecture board still has no real diagram or architecture artifact.',
      'Emit the first target-state architecture as soon as the recommendation direction becomes coherent.',
    ))
  }

  if (metrics.hasArchitecture && !scenario.architectureArtifact) {
    items.push(makeItem(
      'architecture',
      'note',
      'Diagram has no narrative package',
      'The architecture board can render nodes, but there is no architecture artifact explaining what the user is looking at.',
      'Publish an `architectureArtifact.executive_summary`, decisions, and rollout alongside the canvas snapshot.',
    ))
  }

  if (metrics.stage === 'blueprint' && blueprint.mode === 'empty') {
    items.push(makeItem(
      'blueprint',
      'critical',
      'Blueprint stage without blueprint artifact',
      'The experience claims blueprint readiness but does not expose a structured blueprint artifact.',
      'Publish blueprint markdown or an output pack before moving the stage to blueprint.',
    ))
  }

  if (metrics.stage === 'blueprint' && blueprint.mode === 'derived') {
    items.push(makeItem(
      'blueprint',
      'critical',
      'Blueprint panel is still showing a derived draft',
      'The UI is presenting a synthesized blueprint instead of a model-published blueprint or output pack.',
      'Keep the session in solutioning until the advisor publishes a canonical blueprint artifact.',
    ))
  } else if (metrics.stage !== 'discovery' && blueprint.mode === 'derived') {
    items.push(makeItem(
      'blueprint',
      'warning',
      'Blueprint panel is showing inferred content',
      'The panel is reviewable, but it is rendering a derived draft rather than a published artifact.',
      'Label the content as draft and publish a canonical blueprint before using it as the system of record.',
    ))
  }

  if (blockingQuestions > 0 && metrics.stage === 'blueprint') {
    items.push(makeItem(
      'questions',
      'warning',
      'Blueprint still has blocking questions',
      `${blockingQuestions} blocking question(s) remain even though the session is in blueprint stage.`,
      'Either keep the engagement in solutioning or explicitly downgrade the remaining items to non-blocking assumptions.',
    ))
  }

  if (structuredBlockingQuestions.length > 0 && structuredBlockingQuestions.some((item) => !item.why_it_matters.trim())) {
    items.push(makeItem(
      'questions',
      'note',
      'Questions lack rationale',
      'At least one blocking question is visible without a `why this matters` explanation, which weakens the questions panel.',
      'Persist `why_it_matters` for blocking questions so the panel explains why the answer changes the recommendation.',
    ))
  }

  if (workspace.open_questions.length !== structuredBlockingQuestions.length && structuredBlockingQuestions.length > 0) {
    items.push(makeItem(
      'questions',
      'note',
      'Question counts are out of sync',
      'The flat `open_questions` list does not match the structured blocking question state, so badges may not match the reasoning trace.',
      'Normalize the question store so the panel, counters, and recommendation state all derive from the same source.',
    ))
  }

  if (metrics.stage !== 'discovery' && metrics.decisionCount === 0) {
    items.push(makeItem(
      'brief',
      'warning',
      'Decisions are not captured',
      'The session has a recommendation but no explicit decisions recorded for the brief to surface.',
      'Promote the key architecture decisions into the decision log instead of leaving them implicit in chat.',
    ))
  }

  if (metrics.stage !== 'discovery' && metrics.riskCount === 0) {
    items.push(makeItem(
      'brief',
      'warning',
      'Risk register is empty',
      'The recommendation is visible, but the brief cannot show tradeoffs because no risks are persisted.',
      'Persist at least the top tradeoffs and unresolved dependencies into the risk register.',
    ))
  }

  if (metrics.stage === 'blueprint' && metrics.implementationCount === 0) {
    items.push(makeItem(
      'blueprint',
      'warning',
      'No rollout plan in blueprint stage',
      'The session has blueprint-level intent but no implementation path to execute it.',
      'Publish a 30/90/180 or equivalent rollout sequence alongside the target-state recommendation.',
    ))
  }

  if (metrics.stage !== 'discovery' && workspace.facts.length < 2) {
    items.push(makeItem(
      'brief',
      'note',
      'Thin evidence trail',
      'The brief is light on confirmed facts, which weakens traceability from customer context to recommendation.',
      'Capture the key confirmed constraints and customer facts that justify the recommendation.',
    ))
  }

  if (metrics.stage !== 'discovery' && !metrics.confidence) {
    items.push(makeItem(
      'brief',
      'note',
      'Confidence signal missing',
      'The brief does not communicate how stable the recommendation is yet.',
      'Set recommendation confidence once the primary branch and blockers are clear.',
    ))
  }

  if (metrics.confidence === 'high' && blockingQuestions > 0) {
    items.push(makeItem(
      'brief',
      'warning',
      'Confidence overstates readiness',
      'The brief says high confidence even though blocking questions still remain in the workspace.',
      'Downgrade confidence or resolve the blocking questions before presenting the recommendation as stable.',
    ))
  }

  if (metrics.stage !== 'discovery' && metrics.hasArchitecture && metrics.assumptionCount === 0) {
    items.push(makeItem(
      'assumptions',
      'note',
      'Assumptions panel has no structured content',
      'The architecture exists, but the assumptions panel has nothing to inspect or adjust.',
      'Publish structured assumptions once the baseline architecture is stable enough to tune.',
    ))
  }

  if (staleNextQuestion) {
    items.push(makeItem(
      'questions',
      'note',
      'Recommendation state still points to a next question',
      'The recommendation metadata still references a next-best question even though the workspace shows no remaining blockers.',
      'Clear or refresh `recommendation_state.next_best_question` when the blocking set reaches zero.',
    ))
  }

  auditScenarioExpectations(scenario, workspace, metrics, items)

  return items
}

function auditScenarioExpectations(
  scenario: ReviewScenario,
  workspace: ConsultingWorkspace,
  metrics: ReviewScenarioMetrics,
  items: ReviewAuditItem[],
) {
  const expectations = scenario.expectations
  if (!expectations) return

  const recommendationCorpus = collectRecommendationCorpus(workspace, scenario.architectureArtifact)
  const recommendedOptionCorpus = collectRecommendedOptionCorpus(workspace)

  if (expectations.required_stage && metrics.stage !== expectations.required_stage) {
    items.push(makeItem(
      'workspace',
      'critical',
      'Scenario ended in the wrong stage',
      `This scenario expects \`${expectations.required_stage}\`, but the workspace ended in \`${metrics.stage}\`.`,
      'Keep the review open until the advisor reaches the intended stage for this scenario.',
    ))
  }

  if (expectations.required_confidence && metrics.confidence !== expectations.required_confidence) {
    items.push(makeItem(
      'brief',
      'critical',
      'Scenario confidence target not met',
      `This scenario expects \`${expectations.required_confidence}\` confidence, but the brief shows \`${metrics.confidence || 'unset'}\`.`,
      'Tighten the evidence or reduce unresolved blockers before declaring the scenario complete.',
    ))
  }

  if (expectations.require_architecture && !metrics.hasArchitecture) {
    items.push(makeItem(
      'architecture',
      'critical',
      'Scenario requires an architecture view',
      'This review scenario is expected to render a target-state architecture but none is available.',
      'Publish a canvas snapshot and architecture artifact before treating this scenario as review-complete.',
    ))
  }

  if (expectations.require_published_blueprint && metrics.blueprintMode !== 'published') {
    items.push(makeItem(
      'blueprint',
      'critical',
      'Scenario requires a published blueprint',
      `This scenario expects a published blueprint, but the UI is in \`${metrics.blueprintMode}\` mode.`,
      'Publish blueprint markdown or an output pack rather than relying on a derived draft.',
    ))
  }

  if (typeof expectations.max_open_questions === 'number' && metrics.questionCount > expectations.max_open_questions) {
    items.push(makeItem(
      'questions',
      'critical',
      'Scenario has too many open questions',
      `This review scenario allows at most ${expectations.max_open_questions} blocking question(s), but ${metrics.questionCount} remain.`,
      'Resolve the blocking questions or mark them as non-blocking assumptions before ending the scenario.',
    ))
  }

  for (const term of expectations.recommendation_must_include ?? []) {
    if (!recommendationCorpus.includes(term.toLowerCase())) {
      items.push(makeItem(
        'brief',
        'critical',
        'Required recommendation signal missing',
        `The recommendation and blueprint do not clearly mention "${term}".`,
        'Make the primary recommendation explicit enough that reviewers can verify the decision without inferring it from chat.',
      ))
    }
  }

  for (const term of expectations.recommendation_must_exclude ?? []) {
    if (recommendationCorpus.includes(term.toLowerCase())) {
      items.push(makeItem(
        'brief',
        'critical',
        'Disallowed recommendation signal present',
        `The recommendation path still includes "${term}" where this scenario expects it to be absent.`,
        'Move that option into a deferred alternative or rewrite the primary recommendation to remove the conflict.',
      ))
    }
  }

  for (const term of expectations.recommended_option_must_include ?? []) {
    if (!recommendedOptionCorpus.includes(term.toLowerCase())) {
      items.push(makeItem(
        'brief',
        'critical',
        'Recommended option is not explicit enough',
        `The recommended option set does not clearly include "${term}".`,
        'Expose the expected product or platform choice inside the recommended option or primary recommendation summary.',
      ))
    }
  }

  for (const term of expectations.recommended_option_must_exclude ?? []) {
    if (recommendedOptionCorpus.includes(term.toLowerCase())) {
      items.push(makeItem(
        'brief',
        'critical',
        'Recommended option includes a forbidden choice',
        `A recommended option still includes "${term}".`,
        'Demote that choice to an alternative or remove it from the recommended path for this scenario.',
      ))
    }
  }
}

function collectRecommendationCorpus(
  workspace: ConsultingWorkspace,
  architectureArtifact: ArchitectureArtifact | null,
) {
  const advisoryCase = hasAdvisoryCaseContent(workspace.advisory_case) ? workspace.advisory_case : null
  const blueprint = resolveBlueprintContent(workspace, architectureArtifact)
  return normalizeText([
    workspace.recommendation,
    workspace.recommendation_state?.primary_recommendation,
    advisoryCase?.recommendation.summary,
    advisoryCase?.recommendation.why_this,
    advisoryCase?.readout?.current_recommendation,
    advisoryCase?.output_pack?.executive_summary,
    advisoryCase?.output_pack?.recommendation_memo,
    architectureArtifact?.executive_summary,
    blueprint.markdown,
  ].join('\n'))
}

function collectRecommendedOptionCorpus(workspace: ConsultingWorkspace) {
  const recommendedCandidates = (workspace.recommendation_state?.candidate_options ?? [])
    .filter((item) => item.position === 'recommended')
    .map((item) => `${item.title} ${item.summary}`)
  return normalizeText(recommendedCandidates.join('\n'))
}

function countBlockingQuestions(workspace: ConsultingWorkspace) {
  const structuredBlockingCount = (workspace.question_state ?? []).filter((item) => item.status === 'open' && item.blocking).length
  return structuredBlockingCount > 0 ? structuredBlockingCount : workspace.open_questions.length
}

function normalizeText(value: string) {
  return value.toLowerCase().replace(/\s+/g, ' ').trim()
}

function makeItem(
  component: ReviewAuditComponent,
  severity: ReviewAuditSeverity,
  title: string,
  detail: string,
  fix: string,
): ReviewAuditItem {
  return {
    component,
    severity,
    title,
    detail,
    fix,
  }
}
