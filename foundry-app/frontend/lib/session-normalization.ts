import type { ArchNode, ConsultingWorkspace } from './types'

export const SESSION_NORMALIZATION_MARKER = 'MAINTENANCE_REFRESH_DO_NOT_DISPLAY'

function normalizeLabel(text: string) {
  return text.trim().replace(/\s+/g, ' ').toLowerCase()
}

export function hasMultipleHarnessPaths(nodes: ArchNode[]) {
  const harnessLabels = new Set(
    nodes
      .filter((node) => node.type === 'arch' && node.layer === 'harness')
      .map((node) => normalizeLabel(node.label)),
  )

  return harnessLabels.size > 1
}

export function needsSessionRenormalization(
  workspace: ConsultingWorkspace | null,
  nodes: ArchNode[],
) {
  if (!workspace && nodes.length === 0) return false
  return hasMultipleHarnessPaths(nodes)
}

export function isMaintenanceMessage(content: string) {
  return content.includes(SESSION_NORMALIZATION_MARKER)
}
