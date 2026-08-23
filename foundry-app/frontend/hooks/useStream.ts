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
import { normalizeAdvisoryCase } from '@/lib/advisory-case'
import { getToken } from '@/lib/auth'
import { normalizeArchitectureArtifact } from '@/lib/architecture-artifact'
import { normalizeWorkspaceAssumptions } from '@/lib/assumptions'
import { normalizeWorkspace } from '@/lib/message-analysis'
import { SESSION_NORMALIZATION_MARKER } from '@/lib/session-normalization'
import type { OperatingModel } from '@/lib/types'
import type { SendMessageOptions } from './useConversationSend'

function buildOutboundMessage(text: string, options?: SendMessageOptions) {
  const action = options?.action
  if (!action) return text

  if (action.kind === 'open_question_answer') {
    return [
      'An open question has been answered.',
      `Question: ${action.question}`,
      `Answer: ${action.answer}`,
      'Refresh the recommendation, assumptions, blueprint, architecture, and open questions only if this answer materially changes them.',
      'Publish detailed changes in the workspace panels and keep the chat response to at most two short sentences.',
    ].join('\n')
  }

  if (action.kind === 'bulk_open_question_answers') {
    return [
      'Several open questions have been answered together.',
      ...action.answers.flatMap((item, index) => [
        `${index + 1}. Question: ${item.question}`,
        `   Answer: ${item.answer}`,
      ]),
      'Refresh the recommendation, assumptions, blueprint, architecture, and open questions only if these answers materially change them.',
      'Publish detailed changes in the workspace panels and keep the chat response to at most two short sentences.',
    ].join('\n')
  }

  if (action.kind === 'normalize_session') {
    return [
      `${SESSION_NORMALIZATION_MARKER}`,
      'Re-normalize the current session artifacts under the latest advisory rules.',
      'Refresh the recommendation, advisory brief, architecture, blueprint, assumptions, and open questions as needed.',
      'Preserve the actual target-state operating model. If the target state is governed multi-harness coexistence, keep the approved harness portfolio in the architecture and make the governance model explicit.',
      'Only move a harness into alternatives if it is rejected, deferred, or part of a true scenario comparison rather than the recommended target-state stack.',
      `If you emit any chat reply, make it exactly: ${SESSION_NORMALIZATION_MARKER} session artifacts refreshed.`,
    ].join('\n')
  }

  return text
}

function addWorkspaceContext(text: string, customerId: string, sessionId: string) {
  const state = useStore.getState()
  if (state.messages.length > 0) return text

  const conversation = state.conversations.find(
    (row) => (
      row.customer.customer_id === customerId
      && row.session.session_id === sessionId
    ),
  )
  if (!conversation) return text

  const project = conversation.session.title.trim()
  const purpose = conversation.session.description?.trim() ?? ''
  if (!project && !purpose) return text

  return [
    'Workspace context supplied by the user before the conversation began:',
    project ? `Project: ${project}` : '',
    purpose ? `Purpose: ${purpose}` : '',
    '',
    'User message:',
    text,
  ].filter((line, index) => line || index === 3).join('\n')
}

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
    async (text: string, customerId: string, sessionId: string, options?: SendMessageOptions) => {
      abortRef.current?.abort()
      const ctrl = new AbortController()
      abortRef.current = ctrl
      const outboundMessage = addWorkspaceContext(
        buildOutboundMessage(text, options),
        customerId,
        sessionId,
      )
      const shouldAppendAgentMessage = options?.appendResponseToTranscript !== false

      if (options?.appendToTranscript !== false) {
        appendMessage({ id: nanoid(), role: 'user', content: options?.visibleText ?? text })
      }

      const agentMsgId = shouldAppendAgentMessage ? nanoid() : null
      if (agentMsgId) {
        appendMessage({ id: agentMsgId, role: 'agent', content: '', streaming: true })
      }
      setStreaming(true)

      try {
        const stream = await openStream(customerId, sessionId, outboundMessage, ctrl.signal)

        for await (const evt of readSSEEvents(stream)) {
          if (ctrl.signal.aborted) break

          const type = (evt as { type?: string }).type
          const data = (evt as { data?: Record<string, unknown> }).data ?? evt

          if (type === 'chat_stream') {
            if (agentMsgId) {
              appendChunk(agentMsgId, (data as { text?: string }).text ?? '')
            }
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
            setWorkspace(normalizeWorkspace({
              stage: typeof data.stage === 'string' ? data.stage : '',
              recommendation: typeof data.recommendation === 'string' ? data.recommendation : '',
              blueprint_markdown: typeof data.blueprint_markdown === 'string' ? data.blueprint_markdown : '',
              assumptions: normalizeWorkspaceAssumptions(data.assumptions),
              facts: Array.isArray(data.facts) ? data.facts.filter((v): v is string => typeof v === 'string') : [],
              operating_model: normalizeOperatingModel(data.operating_model),
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
              advisory_case: normalizeAdvisoryCase(data.advisory_case),
              updated_at: typeof data.updated_at === 'string' ? data.updated_at : undefined,
            }))
          } else if (type === 'module_detected') {
            const mod = (data as { module?: string }).module ?? ''
            if (mod) useStore.getState().setActiveSession(customerId, sessionId, mod)
          }
        }
      } catch (err: unknown) {
        if (agentMsgId && err instanceof Error && err.name !== 'AbortError') {
          appendChunk(agentMsgId, `\n\n_Connection error: ${err.message}_`)
        }
      } finally {
        if (agentMsgId) {
          finalizeMessage(agentMsgId)
        }
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

function normalizeOperatingModel(value: unknown): OperatingModel {
  switch (value) {
    case 'undecided':
    case 'single_standard':
    case 'multi_harness_governed':
    case 'default_plus_exceptions':
      return value
    default:
      return ''
  }
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
