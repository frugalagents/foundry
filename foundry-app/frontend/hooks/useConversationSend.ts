'use client'

import { useCallback, useState } from 'react'
import { useStore } from '@/store'
import { useStream } from './useStream'
import { createSession, getOrCreateDefaultCustomer } from '@/lib/api'

export interface ConversationAction {
  kind: 'open_question_answer'
  question: string
  answer: string
}

export interface BulkOpenQuestionAnswerAction {
  kind: 'bulk_open_question_answers'
  answers: Array<{
    question: string
    answer: string
  }>
}

export interface SendMessageOptions {
  action?: ConversationAction | BulkOpenQuestionAnswerAction
  appendToTranscript?: boolean
  title?: string
  visibleText?: string
}

export function useConversationSend() {
  const {
    activeCustomerId,
    activeSessionId,
    setActiveSession,
    prependConversation,
    updateConversation,
    streaming,
  } = useStore()
  const { send, abort } = useStream()
  const [creating, setCreating] = useState(false)

  const sendMessage = useCallback(async (text: string, options?: SendMessageOptions) => {
    if (!text.trim() || streaming || creating) return false

    let customerId = activeCustomerId
    let sessionId = activeSessionId
    const titleSeed = options?.title ?? options?.visibleText ?? text

    if (!customerId || !sessionId) {
      setCreating(true)
      try {
        const customer = await getOrCreateDefaultCustomer()
        customerId = customer.customer_id
        const session = await createSession(customerId, { title: titleSeed.slice(0, 60) })
        sessionId = session.session_id
        setActiveSession(customerId, sessionId)
        prependConversation({ session, customer })
        window.history.pushState(null, '', `/sessions/${sessionId}`)
      } catch (err) {
        console.error('Failed to create session', err)
        setCreating(false)
        return false
      }
      setCreating(false)
    }

    await send(text, customerId!, sessionId!, options)
    updateConversation(sessionId!, { updated_at: new Date().toISOString() })
    return true
  }, [
    activeCustomerId,
    activeSessionId,
    creating,
    prependConversation,
    send,
    setActiveSession,
    streaming,
    updateConversation,
  ])

  return {
    abort,
    creating,
    sendMessage,
    sending: streaming || creating,
  }
}
