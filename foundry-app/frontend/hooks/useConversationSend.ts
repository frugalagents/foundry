'use client'

import { useCallback, useState } from 'react'
import { useStore } from '@/store'
import { useStream } from './useStream'
import { createSession, getOrCreateDefaultCustomer } from '@/lib/api'

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

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || streaming || creating) return false

    let customerId = activeCustomerId
    let sessionId = activeSessionId

    if (!customerId || !sessionId) {
      setCreating(true)
      try {
        const customer = await getOrCreateDefaultCustomer()
        customerId = customer.customer_id
        const session = await createSession(customerId, { title: text.slice(0, 60) })
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

    await send(text, customerId!, sessionId!)
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
