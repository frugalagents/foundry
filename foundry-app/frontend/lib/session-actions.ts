import { nanoid } from 'nanoid'
import { getSessionHistory } from './api'
import { useStore } from '@/store'

/** Load a session's persisted history (messages + canvas) into the active view. */
export async function loadSessionIntoView(customerId: string, sessionId: string, moduleId?: string) {
  const store = useStore.getState()
  store.clearMessages()
  store.hideCanvas()
  store.setActiveSession(customerId, sessionId, moduleId)
  const { messages, canvas } = await getSessionHistory(customerId, sessionId)
  for (const m of messages) {
    store.appendMessage({ id: nanoid(), role: m.role, content: m.content })
  }
  if (canvas && canvas.nodes.length > 0) {
    store.setCanvas(canvas.nodes, canvas.edges)
  }
}
