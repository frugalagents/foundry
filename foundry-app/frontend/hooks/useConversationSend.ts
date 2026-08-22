'use client'

import { useCallback } from 'react'
import { useStore } from '@/store'
import { useStream } from './useStream'

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

export interface NormalizeSessionAction {
  kind: 'normalize_session'
}

export interface SendMessageOptions {
  action?: ConversationAction | BulkOpenQuestionAnswerAction | NormalizeSessionAction
  appendToTranscript?: boolean
  appendResponseToTranscript?: boolean
  title?: string
  visibleText?: string
}

export function useConversationSend() {
  const {
    activeCustomerId,
    activeSessionId,
    conversations,
    userId,
    updateConversation,
    streaming,
  } = useStore()
  const { send, abort } = useStream()
  const activeConversation = activeSessionId
    ? conversations.find((row) => row.session.session_id === activeSessionId)
    : undefined
  const readOnly = Boolean(
    activeConversation
    && userId
    && (
      activeConversation.session.created_by !== userId
      || activeConversation.customer.created_by !== userId
    ),
  )

  const sendMessage = useCallback(async (text: string, options?: SendMessageOptions) => {
    if (
      !text.trim()
      || streaming
      || readOnly
      || !activeCustomerId
      || !activeSessionId
    ) return false

    await send(text, activeCustomerId, activeSessionId, options)
    updateConversation(activeSessionId, { updated_at: new Date().toISOString() })
    return true
  }, [
    activeCustomerId,
    activeSessionId,
    readOnly,
    send,
    streaming,
    updateConversation,
  ])

  return {
    abort,
    readOnly,
    sendMessage,
    sending: streaming,
  }
}
