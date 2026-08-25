import type {
  ArchitectureCase,
  ArchitectureCaseArtifacts,
  ArchitectureCaseDecision,
  ArchitectureCaseFact,
  ArchitectureCaseQuestion,
  ArchitectureCaseRisk,
  ArchitectureCaseRolloutItem,
} from './types'

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : ''
}

function normalizeFacts(value: unknown): ArchitectureCaseFact[] {
  if (!Array.isArray(value)) return []
  const facts: ArchitectureCaseFact[] = []
  value.forEach((item, index) => {
    const record = asRecord(item)
    if (!record) return
    const statement = text(record.statement)
    if (!statement) return
    facts.push({
      id: text(record.id) || `fact-${index + 1}`,
      statement,
      value: record.value,
      status: text(record.status),
      source: text(record.source),
    })
  })
  return facts
}

function normalizeQuestions(value: unknown): ArchitectureCaseQuestion[] {
  if (!Array.isArray(value)) return []
  const questions: ArchitectureCaseQuestion[] = []
  value.forEach((item, index) => {
    const record = asRecord(item)
    if (!record) return
    const question = text(record.text)
    if (!question) return
    questions.push({
      id: text(record.id) || `question-${index + 1}`,
      text: question,
      why_it_matters: text(record.why_it_matters),
      blocking: typeof record.blocking === 'boolean' ? record.blocking : true,
      decision_domain: text(record.decision_domain),
      status: text(record.status),
      answer: text(record.answer),
      source: text(record.source),
    })
  })
  return questions
}

function normalizeDecisions(value: unknown): ArchitectureCaseDecision[] {
  if (!Array.isArray(value)) return []
  const decisions: ArchitectureCaseDecision[] = []
  value.forEach((item, index) => {
    const record = asRecord(item)
    if (!record) return
    const statement = text(record.statement)
    if (!statement) return
    decisions.push({
      id: text(record.id) || `decision-${index + 1}`,
      statement,
      rationale: text(record.rationale),
      status: text(record.status),
      source: text(record.source),
      alternatives_considered: Array.isArray(record.alternatives_considered)
        ? record.alternatives_considered.filter((entry): entry is string => typeof entry === 'string')
        : [],
      evidence_refs: Array.isArray(record.evidence_refs)
        ? record.evidence_refs.filter((entry): entry is string => typeof entry === 'string')
        : [],
      owner: text(record.owner),
      open_dependency: text(record.open_dependency),
    })
  })
  return decisions
}

function normalizeRisks(value: unknown): ArchitectureCaseRisk[] {
  if (!Array.isArray(value)) return []
  const risks: ArchitectureCaseRisk[] = []
  value.forEach((item, index) => {
    const record = asRecord(item)
    if (!record) return
    const risk = text(record.risk)
    if (!risk) return
    risks.push({
      id: text(record.id) || `risk-${index + 1}`,
      risk,
      mitigation: text(record.mitigation),
      severity: text(record.severity),
      category: text(record.category),
      source: text(record.source),
    })
  })
  return risks
}

function normalizeRollout(value: unknown): ArchitectureCaseRolloutItem[] {
  if (!Array.isArray(value)) return []
  const rollout: ArchitectureCaseRolloutItem[] = []
  value.forEach((item) => {
    const record = asRecord(item)
    if (!record) return
    const phase = text(record.phase)
    const outcome = text(record.outcome)
    if (!phase && !outcome) return
    rollout.push({
      phase,
      outcome,
    })
  })
  return rollout
}

function normalizeArtifacts(value: unknown): ArchitectureCaseArtifacts {
  const record = asRecord(value)
  return {
    blueprint_markdown: text(record?.blueprint_markdown),
    executive_summary: text(record?.executive_summary),
    recommendation_memo: text(record?.recommendation_memo),
    architecture_narrative: text(record?.architecture_narrative),
    diagram_summary: text(record?.diagram_summary),
    rollout: normalizeRollout(record?.rollout),
  }
}

export function normalizeArchitectureCase(value: unknown): ArchitectureCase | null {
  const record = asRecord(value)
  if (!record) return null

  const caseId = text(record.case_id)
  const stage = text(record.stage)
  const recommendation = text(record.current_recommendation)
  const artifacts = normalizeArtifacts(record.artifacts)
  const facts = normalizeFacts(record.facts)
  const decisions = normalizeDecisions(record.decisions)
  const risks = normalizeRisks(record.risks)
  const openQuestions = normalizeQuestions(record.open_questions)

  if (!caseId && !recommendation && facts.length === 0 && decisions.length === 0 && risks.length === 0 && openQuestions.length === 0 && !artifacts.blueprint_markdown) {
    return null
  }

  return {
    schema_version: text(record.schema_version),
    case_id: caseId,
    revision: typeof record.revision === 'number' ? record.revision : Number(record.revision || 1) || 1,
    okf_release_id: text(record.okf_release_id),
    stage,
    current_recommendation: recommendation,
    operating_model: text(record.operating_model),
    facts,
    open_questions: openQuestions,
    decisions,
    risks,
    artifacts,
  }
}
