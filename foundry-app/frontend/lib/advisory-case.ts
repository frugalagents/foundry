import type {
  AdvisoryAlternative,
  AdvisoryCase,
  AdvisoryDecision,
  AdvisoryDelta,
  AdvisoryMaturityDomain,
  AdvisoryNextBestQuestion,
  AdvisoryOutputPack,
  AdvisoryPackRisk,
  AdvisoryPackRolloutPhase,
  AdvisoryReadout,
  AdvisoryRecommendation,
  AdvisoryRisk,
} from './types'

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function normalizeConfidence(value: unknown): AdvisoryRecommendation['confidence'] {
  return value === 'low' || value === 'medium' || value === 'high' ? value : ''
}

function normalizeSeverity(value: unknown): AdvisoryRisk['severity'] {
  return value === 'low' || value === 'medium' || value === 'high' ? value : ''
}

function normalizePosition(value: unknown): AdvisoryAlternative['position'] {
  return value === 'recommended' || value === 'viable' || value === 'deferred' ? value : ''
}

function normalizeRecommendation(value: unknown): AdvisoryRecommendation {
  const raw = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  return {
    summary: typeof raw.summary === 'string' ? raw.summary : '',
    why_this: typeof raw.why_this === 'string' ? raw.why_this : '',
    why_not: typeof raw.why_not === 'string' ? raw.why_not : '',
    confidence: normalizeConfidence(raw.confidence),
    confidence_reason: typeof raw.confidence_reason === 'string' ? raw.confidence_reason : '',
    change_triggers: stringList(raw.change_triggers),
  }
}

function normalizeAlternative(value: unknown): AdvisoryAlternative | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.id !== 'string' || typeof raw.title !== 'string') return null
  return {
    id: raw.id,
    title: raw.title,
    position: normalizePosition(raw.position),
    summary: typeof raw.summary === 'string' ? raw.summary : '',
    benefits: stringList(raw.benefits),
    risks: stringList(raw.risks),
    operational_burden: typeof raw.operational_burden === 'string' ? raw.operational_burden : '',
    governance_implications: typeof raw.governance_implications === 'string' ? raw.governance_implications : '',
    best_fit_conditions: stringList(raw.best_fit_conditions),
  }
}

function normalizeDecision(value: unknown): AdvisoryDecision | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.statement !== 'string') return null
  return {
    statement: raw.statement,
    options_considered: stringList(raw.options_considered),
    recommendation: typeof raw.recommendation === 'string' ? raw.recommendation : '',
    why: typeof raw.why === 'string' ? raw.why : '',
    tradeoffs_accepted: stringList(raw.tradeoffs_accepted),
    owner: typeof raw.owner === 'string' ? raw.owner : '',
    open_dependency: typeof raw.open_dependency === 'string' ? raw.open_dependency : '',
  }
}

function normalizeRisk(value: unknown): AdvisoryRisk | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.risk !== 'string') return null
  return {
    category: typeof raw.category === 'string' ? raw.category : '',
    severity: normalizeSeverity(raw.severity),
    risk: raw.risk,
    mitigation: typeof raw.mitigation === 'string' ? raw.mitigation : '',
  }
}

function normalizeMaturity(value: unknown): AdvisoryMaturityDomain | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.domain !== 'string') return null
  return {
    domain: raw.domain,
    current_state: typeof raw.current_state === 'string' ? raw.current_state : '',
    target_state: typeof raw.target_state === 'string' ? raw.target_state : '',
    gap: typeof raw.gap === 'string' ? raw.gap : '',
  }
}

function normalizeReadout(value: unknown): AdvisoryReadout {
  const raw = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  return {
    current_recommendation: typeof raw.current_recommendation === 'string' ? raw.current_recommendation : '',
    important_decisions: stringList(raw.important_decisions),
    biggest_risks: stringList(raw.biggest_risks),
    open_questions: stringList(raw.open_questions),
    rollout_summary: typeof raw.rollout_summary === 'string' ? raw.rollout_summary : '',
    architecture_snapshot: typeof raw.architecture_snapshot === 'string' ? raw.architecture_snapshot : '',
  }
}

function normalizeNextBestQuestion(value: unknown): AdvisoryNextBestQuestion | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.question !== 'string' || typeof raw.why_it_matters !== 'string') return null
  return {
    question: raw.question,
    why_it_matters: raw.why_it_matters,
  }
}

function normalizePackRisk(value: unknown): AdvisoryPackRisk | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.risk !== 'string') return null
  return {
    risk: raw.risk,
    mitigation: typeof raw.mitigation === 'string' ? raw.mitigation : '',
  }
}

function normalizePackRollout(value: unknown): AdvisoryPackRolloutPhase | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.horizon !== 'string') return null
  return {
    horizon: raw.horizon,
    outcome: typeof raw.outcome === 'string' ? raw.outcome : '',
  }
}

function normalizeOutputPack(value: unknown): AdvisoryOutputPack {
  const raw = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  return {
    executive_summary: typeof raw.executive_summary === 'string' ? raw.executive_summary : '',
    recommendation_memo: typeof raw.recommendation_memo === 'string' ? raw.recommendation_memo : '',
    architecture_narrative: typeof raw.architecture_narrative === 'string' ? raw.architecture_narrative : '',
    key_decisions: stringList(raw.key_decisions),
    risks_and_mitigations: Array.isArray(raw.risks_and_mitigations)
      ? raw.risks_and_mitigations.map(normalizePackRisk).filter((item): item is AdvisoryPackRisk => Boolean(item))
      : [],
    open_questions: stringList(raw.open_questions),
    rollout_30_90_180: Array.isArray(raw.rollout_30_90_180)
      ? raw.rollout_30_90_180.map(normalizePackRollout).filter((item): item is AdvisoryPackRolloutPhase => Boolean(item))
      : [],
    operating_principles: stringList(raw.operating_principles),
    control_checklist: stringList(raw.control_checklist),
  }
}

function normalizeDelta(value: unknown): AdvisoryDelta | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  return {
    summary: typeof raw.summary === 'string' ? raw.summary : '',
    recommendation_change: typeof raw.recommendation_change === 'string' ? raw.recommendation_change : '',
    new_risks: stringList(raw.new_risks),
    added_controls: stringList(raw.added_controls),
    removed_controls: stringList(raw.removed_controls),
    cost_or_complexity_impact: typeof raw.cost_or_complexity_impact === 'string' ? raw.cost_or_complexity_impact : '',
    changed_assumptions: stringList(raw.changed_assumptions),
  }
}

export function normalizeAdvisoryCase(value: unknown): AdvisoryCase | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  return {
    recommendation: normalizeRecommendation(raw.recommendation),
    alternatives: Array.isArray(raw.alternatives)
      ? raw.alternatives.map(normalizeAlternative).filter((item): item is AdvisoryAlternative => Boolean(item))
      : [],
    decisions: Array.isArray(raw.decisions)
      ? raw.decisions.map(normalizeDecision).filter((item): item is AdvisoryDecision => Boolean(item))
      : [],
    risks: Array.isArray(raw.risks)
      ? raw.risks.map(normalizeRisk).filter((item): item is AdvisoryRisk => Boolean(item))
      : [],
    maturity: Array.isArray(raw.maturity)
      ? raw.maturity.map(normalizeMaturity).filter((item): item is AdvisoryMaturityDomain => Boolean(item))
      : [],
    readout: normalizeReadout(raw.readout),
    next_best_question: normalizeNextBestQuestion(raw.next_best_question),
    output_pack: normalizeOutputPack(raw.output_pack),
    delta: normalizeDelta(raw.delta),
  }
}

export function hasAdvisoryCaseContent(value: AdvisoryCase | null | undefined) {
  if (!value) return false
  return Boolean(
    value.recommendation.summary ||
    value.recommendation.why_this ||
    value.recommendation.why_not ||
    value.alternatives.length > 0 ||
    value.decisions.length > 0 ||
    value.risks.length > 0 ||
    value.maturity.length > 0 ||
    value.readout.current_recommendation ||
    value.readout.important_decisions.length > 0 ||
    value.readout.biggest_risks.length > 0 ||
    value.readout.open_questions.length > 0 ||
    value.readout.rollout_summary ||
    value.readout.architecture_snapshot ||
    Boolean(value.next_best_question?.question) ||
    value.output_pack.executive_summary ||
    value.output_pack.recommendation_memo ||
    value.output_pack.architecture_narrative ||
    value.output_pack.key_decisions.length > 0 ||
    value.output_pack.risks_and_mitigations.length > 0 ||
    value.output_pack.open_questions.length > 0 ||
    value.output_pack.rollout_30_90_180.length > 0 ||
    value.output_pack.operating_principles.length > 0 ||
    value.output_pack.control_checklist.length > 0,
  )
}
