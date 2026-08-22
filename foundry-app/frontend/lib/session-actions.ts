import { nanoid } from 'nanoid'
import { getSessionHistory } from './api'
import { normalizeAdvisoryCase } from './advisory-case'
import { useStore } from '@/store'
import { normalizeArchitectureArtifact } from './architecture-artifact'
import { normalizeWorkspaceAssumptions } from './assumptions'
import { normalizeWorkspace } from './message-analysis'
import type { ConversationRow } from './types'

const SESSION_PATH_PATTERN = /^\/sessions\/([^/]+)\/?$/

export function sessionIdFromPathname(pathname: string) {
  const match = pathname.match(SESSION_PATH_PATTERN)
  if (!match) return null

  try {
    return decodeURIComponent(match[1])
  } catch {
    return match[1]
  }
}

/** Load a session's persisted history (messages + canvas) into the active view. */
export async function loadSessionIntoView(customerId: string, sessionId: string, moduleId?: string) {
  const { messages, canvas, workspace } = await getSessionHistory(customerId, sessionId)
  const normalizedWorkspace = workspace
    ? normalizeWorkspace({
      ...workspace,
      assumptions: normalizeWorkspaceAssumptions(workspace.assumptions),
      advisory_case: normalizeAdvisoryCase(workspace.advisory_case),
    })
    : null

  // Do not clear the current view until history has been fetched successfully.
  // A failed refresh must leave the user's saved workspace visible.
  useStore.getState().hydrateSession({
    customerId,
    sessionId,
    moduleId,
    messages: messages.map((message) => ({
      id: nanoid(),
      role: message.role,
      content: message.content,
    })),
    workspace: normalizedWorkspace,
    canvasNodes: canvas?.nodes ?? [],
    canvasEdges: canvas?.edges ?? [],
    baselineNodeIds: canvas?.baseline_node_ids ?? [],
    architectureArtifact: normalizeArchitectureArtifact(canvas?.architecture_artifact),
  })
}

/**
 * Restore the session represented by the browser URL. When the app is opened at
 * the root, optionally fall back to the most recently active owned workspace.
 */
export async function restoreSessionFromLocation(
  conversations: ConversationRow[],
  options: { fallbackToLatest?: boolean } = {},
) {
  if (typeof window === 'undefined') return false

  const store = useStore.getState()
  const requestedSessionId = sessionIdFromPathname(window.location.pathname)
  const requested = requestedSessionId
    ? conversations.find((row) => row.session.session_id === requestedSessionId)
    : undefined
  const owned = conversations.find((row) => (
    !!store.userId
    && row.customer.created_by === store.userId
    && row.session.created_by === store.userId
  ))
  const target = requested ?? (options.fallbackToLatest ? owned : undefined)

  if (!target) return false

  if (!requested) {
    window.history.replaceState(null, '', `/sessions/${target.session.session_id}`)
  }

  if (store.activeSessionId === target.session.session_id) return true

  await loadSessionIntoView(
    target.customer.customer_id,
    target.session.session_id,
    target.session.module_id,
  )
  return true
}
