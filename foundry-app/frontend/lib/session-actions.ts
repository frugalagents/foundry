import { nanoid } from 'nanoid'
import { getSessionHistory } from './api'
import { useStore } from '@/store'
import { normalizeArchitectureArtifact } from './architecture-artifact'
import { normalizeWorkspaceAssumptions } from './assumptions'
import { normalizeWorkspace } from './message-analysis'

/** Load a session's persisted history (messages + canvas) into the active view. */
export async function loadSessionIntoView(customerId: string, sessionId: string, moduleId?: string) {
  const store = useStore.getState()
  store.clearMessages()
  store.clearWorkspace()
  store.hideCanvas()
  store.setActiveSession(customerId, sessionId, moduleId)
  const { messages, canvas, workspace } = await getSessionHistory(customerId, sessionId)
  for (const m of messages) {
    store.appendMessage({ id: nanoid(), role: m.role, content: m.content })
  }
  if (workspace) {
    store.setWorkspace(normalizeWorkspace({
      ...workspace,
      assumptions: normalizeWorkspaceAssumptions(workspace.assumptions),
    }))
  }
  if (canvas && canvas.nodes.length > 0) {
    store.setCanvas(canvas.nodes, canvas.edges, canvas.baseline_node_ids)
  }
  store.setArchitectureArtifact(normalizeArchitectureArtifact(canvas?.architecture_artifact))
}
