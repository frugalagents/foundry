import type { ArchNode, ConsultingWorkspace } from './types'

export const SESSION_NORMALIZATION_MARKER = 'MAINTENANCE_REFRESH_DO_NOT_DISPLAY'

export function needsSessionRenormalization(
  _workspace: ConsultingWorkspace | null,
  _nodes: ArchNode[],
) {
  return false
}

export function isMaintenanceMessage(content: string) {
  return content.includes(SESSION_NORMALIZATION_MARKER)
}
