import { normalizeArchitectureCase } from './architecture-case'
import { dedupeTextList } from './text-normalization'
import type {
  Message,
  ConsultingWorkspace,
  OperatingModel,
  WorkspaceArtifactStatus,
  WorkspaceQuestion,
  WorkspaceRecommendationState,
} from './types'

export type AgentMsgType = 'question' | 'observation' | 'mixed'

export interface OpenQuestion {
  id: string
  text: string
}

export interface AgentMessageAnalysis {
  type: AgentMsgType
  questions: string[]
}

function normalizeLine(line: string): string {
  return line
    .trim()
    .replace(/^[-*]\s+/, '')
    .replace(/^\d+\.\s+/, '')
    .replace(/\s+/g, ' ')
}

function extractQuestions(content: string): string[] {
  const lines = content
    .trim()
    .split('\n')
    .map(normalizeLine)
    .filter(Boolean)

  return lines
    .filter((line) => line.includes('?'))
    .map((line) => {
      const withoutTrailingExplanation = line.replace(/\s*\([^)]*\)\s*$/, '').trim()
      return withoutTrailingExplanation
    })
    .map((line) => {
      const lastQuestionMark = line.lastIndexOf('?')
      return lastQuestionMark >= 0 ? line.slice(0, lastQuestionMark + 1).trim() : line
    })
    .filter(Boolean)
}

function normalizeQuestionState(value: unknown, fallbackOpenQuestions: string[] = []): WorkspaceQuestion[] {
  const raw = Array.isArray(value) ? value : []
  const questions: WorkspaceQuestion[] = []
  const seen = new Set<string>()

  for (const item of raw) {
    if (!item || typeof item !== 'object') continue
    const record = item as Record<string, unknown>
    const text = typeof record.text === 'string'
      ? normalizeLine(record.text)
      : typeof record.question === 'string'
        ? normalizeLine(record.question)
        : ''
    if (!text) continue
    const key = text.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)

    const status = record.status === 'open'
      || record.status === 'answered'
      || record.status === 'deferred'
      || record.status === 'invalidated'
      ? record.status
      : ''

    questions.push({
      id: typeof record.id === 'string' && record.id.trim() ? record.id : `question-${questions.length + 1}`,
      text,
      why_it_matters: typeof record.why_it_matters === 'string' ? normalizeLine(record.why_it_matters) : '',
      decision_domain: typeof record.decision_domain === 'string' ? record.decision_domain : '',
      status,
      blocking: typeof record.blocking === 'boolean' ? record.blocking : true,
      answer: typeof record.answer === 'string' ? normalizeLine(record.answer) : '',
      source: typeof record.source === 'string' ? record.source : '',
    })
  }

  if (questions.length > 0) return questions

  return dedupeTextList(fallbackOpenQuestions).map((text, index) => ({
    id: `question-${index + 1}`,
    text,
    why_it_matters: '',
    decision_domain: '',
    status: 'open',
    blocking: true,
    answer: '',
    source: '',
  }))
}

function normalizeOperatingModel(value: unknown): OperatingModel {
  switch (value) {
    case 'undecided':
    case 'single_standard':
    case 'multi_harness_governed':
    case 'default_plus_exceptions':
      return value
    default:
      return ''
  }
}

function normalizeCandidateOptions(value: unknown): WorkspaceRecommendationState['candidate_options'] {
  if (!Array.isArray(value)) return []
  const options: WorkspaceRecommendationState['candidate_options'] = []
  const seen = new Set<string>()

  for (const item of value) {
    if (!item || typeof item !== 'object') continue
    const record = item as Record<string, unknown>
    const title = typeof record.title === 'string' ? normalizeLine(record.title) : ''
    const path = typeof record.path === 'string' ? record.path : ''
    if (!title || !path || seen.has(path)) continue
    seen.add(path)
    const position = record.position === 'recommended' || record.position === 'viable' || record.position === 'deferred'
      ? record.position
      : ''
    options.push({
      path,
      title,
      summary: typeof record.summary === 'string' ? normalizeLine(record.summary) : '',
      decision_domain: typeof record.decision_domain === 'string' ? record.decision_domain : '',
      position,
    })
  }

  return options
}

function normalizeRecommendationState(value: unknown): WorkspaceRecommendationState | null {
  if (!value || typeof value !== 'object') return null
  const record = value as Record<string, unknown>
  const confidence = record.confidence === 'low' || record.confidence === 'medium' || record.confidence === 'high'
    ? record.confidence
    : ''

  return {
    primary_recommendation: typeof record.primary_recommendation === 'string' ? normalizeLine(record.primary_recommendation) : '',
    confidence,
    candidate_options: normalizeCandidateOptions(record.candidate_options),
    missing_evidence: dedupeTextList(Array.isArray(record.missing_evidence) ? record.missing_evidence.filter((item): item is string => typeof item === 'string') : []),
    next_best_question: typeof record.next_best_question === 'string' ? normalizeLine(record.next_best_question) : '',
    last_reasoning_change_fields: dedupeTextList(Array.isArray(record.last_reasoning_change_fields) ? record.last_reasoning_change_fields.filter((item): item is string => typeof item === 'string') : []),
  }
}

function normalizeArtifactStatus(value: unknown): WorkspaceArtifactStatus | null {
  if (!value || typeof value !== 'object') return null
  const record = value as Record<string, unknown>
  const readiness = (input: unknown): WorkspaceArtifactStatus['recommendation'] => (
    input === 'missing' || input === 'draft' || input === 'ready' || input === 'stale' ? input : ''
  )

  return {
    recommendation: readiness(record.recommendation),
    question_state: readiness(record.question_state),
    advisory_case: readiness(record.advisory_case),
    blueprint: readiness(record.blueprint),
    blocking_question_count: typeof record.blocking_question_count === 'number' ? record.blocking_question_count : 0,
    stale_fields: dedupeTextList(Array.isArray(record.stale_fields) ? record.stale_fields.filter((item): item is string => typeof item === 'string') : []),
    reasoning_changes: dedupeTextList(Array.isArray(record.reasoning_changes) ? record.reasoning_changes.filter((item): item is string => typeof item === 'string') : []),
  }
}

export function analyzeAgentMessage(content: string): AgentMessageAnalysis {
  if (!content.trim()) return { type: 'observation', questions: [] }

  const lines = content
    .trim()
    .split('\n')
    .map(normalizeLine)
    .filter(Boolean)
  const questions = extractQuestions(content)

  if (questions.length === 0) {
    return { type: 'observation', questions: [] }
  }

  const hasNarrative = lines.some((line) => !line.includes('?'))
  return {
    type: hasNarrative ? 'mixed' : 'question',
    questions,
  }
}

export function detectAgentMsgType(content: string): AgentMsgType {
  return analyzeAgentMessage(content).type
}

export function extractOpenQuestions(messages: Message[]): OpenQuestion[] {
  let sawUserAfterLastAgentQuestion = false

  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index]

    if (message.role === 'user') {
      sawUserAfterLastAgentQuestion = true
      continue
    }

    if (message.role !== 'agent') {
      continue
    }

    const analysis = analyzeAgentMessage(message.content)
    if (analysis.questions.length === 0) {
      continue
    }

    if (sawUserAfterLastAgentQuestion) {
      return []
    }

    return analysis.questions.map((question, questionIndex) => ({
      id: `${message.id}-${questionIndex}`,
      text: question,
    }))
  }

  return []
}

export function normalizeWorkspace(workspace?: ConsultingWorkspace | null): ConsultingWorkspace {
  const architectureCase = normalizeArchitectureCase(workspace?.architecture_case)
  const canonicalFacts = architectureCase?.facts.map((item) => item.statement) ?? []
  const canonicalQuestions = architectureCase?.open_questions.map((item) => ({
    id: item.id,
    text: item.text,
    why_it_matters: item.why_it_matters,
    decision_domain: item.decision_domain,
    status: item.status || 'open',
    blocking: item.blocking,
    answer: item.answer,
    source: item.source,
  })) ?? []
  const canonicalOpenQuestions = architectureCase?.open_questions.map((item) => item.text) ?? []
  const canonicalDecisions = architectureCase?.decisions.map((item) => item.statement) ?? []
  const canonicalRisks = architectureCase?.risks.map((item) => item.risk) ?? []
  const openQuestions = dedupeTextList(
    canonicalOpenQuestions.length > 0
      ? canonicalOpenQuestions
      : (workspace?.open_questions ?? []),
  )
  const questionState = normalizeQuestionState(
    canonicalQuestions.length > 0 ? canonicalQuestions : workspace?.question_state,
    openQuestions,
  )
  const derivedOpenQuestions = dedupeTextList(
    questionState
      .filter((item) => item.status === 'open')
      .map((item) => item.text),
  )

  return {
    stage: architectureCase?.stage || workspace?.stage || '',
    recommendation: architectureCase?.current_recommendation || workspace?.recommendation || '',
    blueprint_markdown: architectureCase?.artifacts.blueprint_markdown || workspace?.blueprint_markdown || '',
    assumptions: workspace?.assumptions ?? [],
    facts: dedupeTextList(canonicalFacts.length > 0 ? canonicalFacts : (workspace?.facts ?? [])),
    operating_model: normalizeOperatingModel(architectureCase?.operating_model || workspace?.operating_model),
    question_state: questionState,
    open_questions: derivedOpenQuestions.length > 0 ? derivedOpenQuestions : openQuestions,
    decisions: dedupeTextList(canonicalDecisions.length > 0 ? canonicalDecisions : (workspace?.decisions ?? [])),
    risks: dedupeTextList(canonicalRisks.length > 0 ? canonicalRisks : (workspace?.risks ?? [])),
    implementation_plan: dedupeTextList(workspace?.implementation_plan ?? []),
    advisory_case: workspace?.advisory_case ?? null,
    architecture_case: architectureCase,
    recommendation_state: normalizeRecommendationState(workspace?.recommendation_state),
    artifact_status: normalizeArtifactStatus(workspace?.artifact_status),
    updated_at: workspace?.updated_at,
  }
}
