import type {
  ArchNode,
  ArchitectureArtifact,
  ConsultingWorkspace,
  WorkspaceAssumption,
  WorkspaceAssumptionOption,
} from './types'

function normalizeAssumptionOption(value: unknown): WorkspaceAssumptionOption | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.id !== 'string' || typeof raw.label !== 'string' || typeof raw.prompt !== 'string') {
    return null
  }
  return {
    id: raw.id,
    label: raw.label,
    prompt: raw.prompt,
  }
}

function normalizeAssumption(value: unknown): WorkspaceAssumption | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.id !== 'string' || typeof raw.title !== 'string' || typeof raw.assumed !== 'string') {
    return null
  }

  return {
    id: raw.id,
    title: raw.title,
    assumed: raw.assumed,
    why: typeof raw.why === 'string' ? raw.why : '',
    impact: typeof raw.impact === 'string' ? raw.impact : '',
    confidence: raw.confidence === 'inferred' || raw.confidence === 'confirmed' ? raw.confidence : 'default',
    impact_level: raw.impact_level === 'low' || raw.impact_level === 'medium' || raw.impact_level === 'high'
      ? raw.impact_level
      : '',
    drives_architecture: raw.drives_architecture === true,
    validation_priority: raw.validation_priority === 'now' || raw.validation_priority === 'soon' || raw.validation_priority === 'later'
      ? raw.validation_priority
      : '',
    options: Array.isArray(raw.options)
      ? raw.options.map(normalizeAssumptionOption).filter((item): item is WorkspaceAssumptionOption => Boolean(item))
      : [],
  }
}

export function normalizeWorkspaceAssumptions(value: unknown): WorkspaceAssumption[] {
  return Array.isArray(value)
    ? value.map(normalizeAssumption).filter((item): item is WorkspaceAssumption => Boolean(item))
    : []
}

export function buildAssumptionCards(
  workspace: ConsultingWorkspace | null,
  _architectureArtifact: ArchitectureArtifact | null,
  _canvasNodes: ArchNode[],
): WorkspaceAssumption[] {
  return normalizeWorkspaceAssumptions(workspace?.assumptions)
}
