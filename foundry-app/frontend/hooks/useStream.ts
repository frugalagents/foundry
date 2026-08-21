'use client'

import { useCallback, useRef } from 'react'
import { nanoid } from 'nanoid'
import { useStore } from '@/store'
import {
  buildRuntimeSessionId,
  invokeAgentCore,
  isDirectModeEnabled,
  readSSEEvents,
} from '@/lib/agentcore'
import { streamSession } from '@/lib/api'
import { getToken } from '@/lib/auth'
import { normalizeArchitectureArtifact } from '@/lib/architecture-artifact'
import { normalizeWorkspaceAssumptions } from '@/lib/assumptions'

export function useStream() {
  const abortRef = useRef<AbortController | null>(null)
  const {
    appendMessage,
    appendChunk,
    finalizeMessage,
    setCanvas,
    setArchitectureArtifact,
    setWorkspace,
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
        const stream = await openStream(customerId, sessionId, text, ctrl.signal)

        for await (const evt of readSSEEvents(stream)) {
          if (ctrl.signal.aborted) break

          const type = (evt as { type?: string }).type
          const data = (evt as { data?: Record<string, unknown> }).data ?? evt

          if (type === 'chat_stream') {
            appendChunk(agentMsgId, (data as { text?: string }).text ?? '')
          } else if (type === 'architecture_update') {
            const d = data as {
              nodes?: never[]
              edges?: never[]
              baseline_node_ids?: string[]
              architecture_artifact?: unknown
            }
            setCanvas(d.nodes ?? [], d.edges ?? [], Array.isArray(d.baseline_node_ids) ? d.baseline_node_ids : undefined)
            setArchitectureArtifact(normalizeArchitectureArtifact(d.architecture_artifact))
          } else if (type === 'workspace_update') {
            setWorkspace({
              stage: typeof data.stage === 'string' ? data.stage : '',
              recommendation: typeof data.recommendation === 'string' ? data.recommendation : '',
              blueprint_markdown: typeof data.blueprint_markdown === 'string' ? data.blueprint_markdown : '',
              assumptions: normalizeWorkspaceAssumptions(data.assumptions),
              facts: Array.isArray(data.facts) ? data.facts.filter((v): v is string => typeof v === 'string') : [],
              open_questions: Array.isArray(data.open_questions)
                ? data.open_questions.filter((v): v is string => typeof v === 'string')
                : [],
              decisions: Array.isArray(data.decisions)
                ? data.decisions.filter((v): v is string => typeof v === 'string')
                : [],
              risks: Array.isArray(data.risks) ? data.risks.filter((v): v is string => typeof v === 'string') : [],
              implementation_plan: Array.isArray(data.implementation_plan)
                ? data.implementation_plan.filter((v): v is string => typeof v === 'string')
                : [],
              updated_at: typeof data.updated_at === 'string' ? data.updated_at : undefined,
            })
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
    [appendMessage, appendChunk, finalizeMessage, setCanvas, setArchitectureArtifact, setWorkspace, setStreaming],
  )

  const abort = useCallback(() => {
    abortRef.current?.abort()
    setStreaming(false)
  }, [setStreaming])

  return { send, abort }
}

async function openStream(
  customerId: string,
  sessionId: string,
  text: string,
  signal?: AbortSignal,
): Promise<ReadableStream<Uint8Array>> {
  if (isDirectModeEnabled()) {
    try {
      const idToken = getToken() ?? ''
      if (!idToken) throw new Error('Missing id token for direct AgentCore invocation')

      const runtimeSessionId = buildRuntimeSessionId(customerId, sessionId)
      return await invokeAgentCore(
        {
          user_message: text,
          session_id: sessionId,
          customer_id: customerId,
          module_id: 'coding-agent',
        },
        runtimeSessionId,
        idToken,
        signal,
      )
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') throw err
      // Fallback path for local/dev deployments that still rely on the backend proxy.
      return streamSession(customerId, sessionId, text, signal)
    }
  }

  return streamSession(customerId, sessionId, text, signal)
}
