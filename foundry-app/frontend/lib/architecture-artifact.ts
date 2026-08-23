import { dedupeTextList } from './text-normalization'
import type {
  ArchitectureArtifact,
  ArchitectureCustomization,
  ArchitectureDecisionRationale,
  ArchitectureFlowSegment,
  ArchitectureLayerSummary,
  ArchitectureOverlayGroup,
  ArchitectureRiskItem,
  ArchitectureRolloutPhase,
} from './types'

function stringList(value: unknown): string[] {
  return dedupeTextList(Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [])
}

function normalizeLayer(value: unknown): ArchitectureLayerSummary | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.id !== 'string' || typeof raw.label !== 'string') return null
  return {
    id: raw.id,
    label: raw.label,
    purpose: typeof raw.purpose === 'string' ? raw.purpose : '',
    component_ids: stringList(raw.component_ids),
    component_labels: stringList(raw.component_labels),
  }
}

function normalizeCustomization(value: unknown): ArchitectureCustomization | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.id !== 'string' || typeof raw.title !== 'string') return null
  return {
    id: raw.id,
    title: raw.title,
    layer: typeof raw.layer === 'string' ? raw.layer : '',
    added_component_ids: stringList(raw.added_component_ids),
    reason: typeof raw.reason === 'string' ? raw.reason : '',
    tradeoff: typeof raw.tradeoff === 'string' ? raw.tradeoff : '',
    triggered_by: stringList(raw.triggered_by),
  }
}

function normalizeDecision(value: unknown): ArchitectureDecisionRationale | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.decision !== 'string') return null
  return {
    decision: raw.decision,
    why: typeof raw.why === 'string' ? raw.why : '',
    alternatives_rejected: stringList(raw.alternatives_rejected),
  }
}

function normalizeRisk(value: unknown): ArchitectureRiskItem | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.risk !== 'string') return null
  return {
    risk: raw.risk,
    mitigation: typeof raw.mitigation === 'string' ? raw.mitigation : '',
  }
}

function normalizeRollout(value: unknown): ArchitectureRolloutPhase | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.phase !== 'string') return null
  return {
    phase: raw.phase,
    outcome: typeof raw.outcome === 'string' ? raw.outcome : '',
  }
}

function normalizeFlowSegment(value: unknown): ArchitectureFlowSegment | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.id !== 'string' || typeof raw.title !== 'string') return null
  return {
    id: raw.id,
    title: raw.title,
    narrative: typeof raw.narrative === 'string' ? raw.narrative : '',
    component_ids: stringList(raw.component_ids),
  }
}

function normalizeOverlayGroup(value: unknown): ArchitectureOverlayGroup | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.id !== 'string' || typeof raw.title !== 'string') return null
  return {
    id: raw.id,
    title: raw.title,
    narrative: typeof raw.narrative === 'string' ? raw.narrative : '',
    component_ids: stringList(raw.component_ids),
  }
}

export function normalizeArchitectureArtifact(value: unknown): ArchitectureArtifact | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  const baselineRaw = raw.baseline && typeof raw.baseline === 'object'
    ? raw.baseline as Record<string, unknown>
    : null

  return {
    executive_summary: typeof raw.executive_summary === 'string' ? raw.executive_summary : '',
    baseline: {
      name: baselineRaw && typeof baselineRaw.name === 'string' ? baselineRaw.name : '',
      layers: baselineRaw && Array.isArray(baselineRaw.layers)
        ? baselineRaw.layers.map(normalizeLayer).filter((item): item is ArchitectureLayerSummary => Boolean(item))
        : [],
    },
    customizations: Array.isArray(raw.customizations)
      ? raw.customizations.map(normalizeCustomization).filter((item): item is ArchitectureCustomization => Boolean(item))
      : [],
    decisions: Array.isArray(raw.decisions)
      ? raw.decisions.map(normalizeDecision).filter((item): item is ArchitectureDecisionRationale => Boolean(item))
      : [],
    risks: Array.isArray(raw.risks)
      ? raw.risks.map(normalizeRisk).filter((item): item is ArchitectureRiskItem => Boolean(item))
      : [],
    rollout: Array.isArray(raw.rollout)
      ? raw.rollout.map(normalizeRollout).filter((item): item is ArchitectureRolloutPhase => Boolean(item))
      : [],
    primary_flow: Array.isArray(raw.primary_flow)
      ? raw.primary_flow.map(normalizeFlowSegment).filter((item): item is ArchitectureFlowSegment => Boolean(item))
      : [],
    cross_cutting_controls: Array.isArray(raw.cross_cutting_controls)
      ? raw.cross_cutting_controls.map(normalizeOverlayGroup).filter((item): item is ArchitectureOverlayGroup => Boolean(item))
      : [],
    supporting_lanes: Array.isArray(raw.supporting_lanes)
      ? raw.supporting_lanes.map(normalizeOverlayGroup).filter((item): item is ArchitectureOverlayGroup => Boolean(item))
      : [],
  }
}
