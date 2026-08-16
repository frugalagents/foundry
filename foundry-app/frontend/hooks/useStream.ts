'use client'

import { useCallback, useRef } from 'react'
import { nanoid } from 'nanoid'
import { useStore } from '@/store'
import { getToken } from '@/lib/auth'
import { isDirectModeEnabled, buildRuntimeSessionId, invokeAgentCore, readSSEEvents } from '@/lib/agentcore'

export function useStream() {
  const abortRef = useRef<AbortController | null>(null)
  const {
    appendMessage,
    appendChunk,
    finalizeMessage,
    setCanvas,
    setActiveSession,
    setStreaming,
  } = useStore()

  const send = useCallback(
    async (text: string, customerId: string, sessionId: string) => {
      abortRef.current?.abort()
      const ctrl = new AbortController()
      abortRef.current = ctrl

      appendMessage({ id: nanoid(), role: 'user', content: text })

      const agentMsgId = nanoid()
      appendMessage({ id: agentMsgId, role: 'agent', content: '', streaming: true })
      setStreaming(true)

      try {
        const idToken          = getToken() ?? ''
        const runtimeSessionId = buildRuntimeSessionId(customerId, sessionId)
        const payload          = {
          user_message: text,
          session_id:   sessionId,
          customer_id:  customerId,
          module_id:    'coding-agent',
        }

        const stream = await invokeAgentCore(payload, runtimeSessionId, idToken, ctrl.signal)

        for await (const evt of readSSEEvents(stream)) {
          if (ctrl.signal.aborted) break

          const type = (evt as { type?: string }).type
          const data = (evt as { data?: Record<string, unknown> }).data ?? evt

          if (type === 'chat_stream') {
            appendChunk(agentMsgId, (data as { text?: string }).text ?? '')
          } else if (type === 'architecture_update') {
            const d = data as { nodes?: never[]; edges?: never[] }
            setCanvas(d.nodes ?? [], d.edges ?? [])
          } else if (type === 'module_detected') {
            const mod = (data as { module?: string }).module ?? ''
            if (mod) useStore.getState().setActiveSession(customerId, sessionId, mod)
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== 'AbortError') {
          appendChunk(agentMsgId, `\n\n_Connection error: ${err.message}_`)
        }
      } finally {
        finalizeMessage(agentMsgId)
        setStreaming(false)
      }
    },
    [appendMessage, appendChunk, finalizeMessage, setCanvas, setActiveSession, setStreaming],
  )

  const abort = useCallback(() => {
    abortRef.current?.abort()
    setStreaming(false)
  }, [setStreaming])

  return { send, abort }
}
