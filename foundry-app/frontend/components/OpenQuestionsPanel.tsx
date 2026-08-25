'use client'

import { useMemo, useState, type CSSProperties } from 'react'
import { useStore } from '@/store'
import { useConversationSend } from '@/hooks/useConversationSend'
import { extractOpenQuestions, normalizeWorkspace } from '@/lib/message-analysis'
import { renderMarkdown } from '@/lib/render-markdown'

export default function OpenQuestionsPanel() {
  const messages = useStore((s) => s.messages)
  const workspace = useStore((s) => s.workspace)
  const { sendMessage, sending } = useConversationSend()
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [submittingId, setSubmittingId] = useState<string | null>(null)
  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])

  const openQuestions = useMemo(() => {
    const structured = view.question_state
      ?.filter((item) => item.status === 'open')
      .map((item) => ({
        id: item.id,
        text: item.text,
        whyItMatters: item.why_it_matters,
        blocking: item.blocking,
      })) ?? []

    if (structured.length > 0) return structured

    const workspaceQuestions = view.open_questions ?? []
    if (workspaceQuestions.length > 0) {
      return workspaceQuestions.map((text, index) => ({
        id: `workspace-${index}`,
        text,
        whyItMatters: '',
        blocking: true,
      }))
    }

    return extractOpenQuestions(messages).map((item) => ({
      id: item.id,
      text: item.text,
      whyItMatters: '',
      blocking: true,
    }))
  }, [messages, view.open_questions, view.question_state])

  const answeredQuestions = useMemo(
    () => openQuestions
      .map((question) => ({
        id: question.id,
        text: question.text,
        answer: drafts[question.id]?.trim() ?? '',
      }))
      .filter((question) => question.answer.length > 0),
    [drafts, openQuestions],
  )

  const agentStreaming = useMemo(
    () => messages.some((message) => message.role === 'agent' && message.streaming),
    [messages],
  )
  const busy = sending || agentStreaming || submittingId !== null

  async function handleSubmitAll() {
    if (answeredQuestions.length === 0) return
    setSubmittingId('all')
    try {
      const sent = await sendMessage(
        answeredQuestions.map((item) => `${item.text}\n${item.answer}`).join('\n\n'),
        {
          title: 'Panel answers',
          appendToTranscript: false,
          action: {
            kind: 'bulk_open_question_answers',
            answers: answeredQuestions.map((item) => ({
              question: item.text,
              answer: item.answer,
            })),
          },
        },
      )
      if (sent) {
        setDrafts((current) => {
          const next = { ...current }
          answeredQuestions.forEach((item) => {
            next[item.id] = ''
          })
          return next
        })
      }
    } finally {
      setSubmittingId(null)
    }
  }

  return (
    <div style={{
      padding: '12px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span style={eyebrowStyle}>Questions To Answer</span>
        <span style={countPillStyle(openQuestions.length > 0)}>
          {openQuestions.length}
        </span>
      </div>

      {answeredQuestions.length > 0 ? (
        <div style={batchCardStyle}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={batchTitleStyle}>Send Together</span>
            <p style={batchBodyStyle}>
              {answeredQuestions.length} answer{answeredQuestions.length === 1 ? '' : 's'} drafted. Send them in one batch so the recommendation refreshes once.
            </p>
          </div>
          <button
            onClick={handleSubmitAll}
            disabled={busy}
            style={{
              ...submitButtonStyle,
              background: submittingId === 'all' ? 'var(--accent-dim)' : 'var(--bg)',
              color: submittingId === 'all' ? 'var(--accent-strong)' : 'var(--text)',
              cursor: busy ? 'default' : 'pointer',
            }}
          >
            {submittingId === 'all'
              ? 'Sending…'
              : busy
                ? 'Wait for current response'
                : answeredQuestions.length === 1
                  ? 'Send 1 Answer'
                  : `Send ${answeredQuestions.length} Answers`}
          </button>
        </div>
      ) : null}

      {openQuestions.length === 0 ? (
        <p style={{ fontSize: 12.5, color: 'var(--text-faint)', lineHeight: 1.6 }}>
          Nothing is blocking the recommendation right now. If the advisor needs one more answer before it can commit, the question will stay visible here.
        </p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {openQuestions.map((question, index) => (
            <div
              key={question.id}
              style={{
                border: '1px solid rgba(245,158,11,0.22)',
                background: 'rgba(245,158,11,0.05)',
                borderRadius: 10,
                padding: '10px 12px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: 10,
              }}
            >
              <span style={numberBadgeStyle}>
                {index + 1}
              </span>
              <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={priorityPillStyle(question.blocking)}>
                    {question.blocking ? 'Needed now' : 'Helpful to confirm'}
                  </span>
                </div>
                <div
                  className="prose"
                  style={{ fontSize: 12.5, color: 'var(--text)', lineHeight: 1.55 }}
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(question.text) }}
                />
                {question.whyItMatters ? (
                  <p style={whyItMattersStyle}>
                    <strong style={{ color: 'var(--text)' }}>Why this matters:</strong> {question.whyItMatters}
                  </p>
                ) : null}
                <textarea
                  value={drafts[question.id] ?? ''}
                  onChange={(e) => setDrafts((current) => ({ ...current, [question.id]: e.target.value }))}
                  disabled={busy}
                  placeholder="Draft the answer here, then send it above…"
                  rows={3}
                  style={{
                    width: '100%',
                    resize: 'vertical',
                    minHeight: 72,
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 9,
                    padding: '10px 12px',
                    color: 'var(--text)',
                    fontSize: 12.5,
                    lineHeight: 1.55,
                    fontFamily: 'inherit',
                    outline: 'none',
                    opacity: busy ? 0.7 : 1,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const eyebrowStyle: CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
}

function countPillStyle(active: boolean): CSSProperties {
  return {
    minWidth: 22,
    height: 22,
    padding: '0 7px',
    borderRadius: 999,
    background: active ? 'rgba(245,158,11,0.14)' : 'var(--bg-hover)',
    border: `1px solid ${active ? 'rgba(245,158,11,0.3)' : 'var(--border)'}`,
    color: active ? 'var(--amber)' : 'var(--text-faint)',
    fontSize: 11,
    fontWeight: 700,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  }
}

const numberBadgeStyle: CSSProperties = {
  width: 18,
  height: 18,
  borderRadius: 6,
  background: 'rgba(245,158,11,0.14)',
  color: 'var(--amber)',
  fontSize: 10,
  fontWeight: 700,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
}

function priorityPillStyle(blocking: boolean): CSSProperties {
  return {
    padding: '3px 8px',
    borderRadius: 999,
    background: blocking ? 'rgba(245,158,11,0.12)' : 'rgba(15,109,119,0.08)',
    border: `1px solid ${blocking ? 'rgba(245,158,11,0.24)' : 'rgba(15,109,119,0.18)'}`,
    color: blocking ? 'var(--amber)' : 'var(--accent-strong)',
    fontSize: 10.5,
    fontWeight: 600,
  }
}

const whyItMattersStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: 'var(--text-muted)',
  lineHeight: 1.55,
}

const batchCardStyle: CSSProperties = {
  borderRadius: 10,
  border: '1px solid rgba(15,109,119,0.18)',
  background: 'rgba(15,109,119,0.05)',
  padding: '10px 12px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 12,
}

const batchTitleStyle: CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'var(--accent-strong)',
}

const batchBodyStyle: CSSProperties = {
  fontSize: 12,
  color: 'var(--text-muted)',
  lineHeight: 1.55,
}

const submitButtonStyle: CSSProperties = {
  padding: '7px 10px',
  borderRadius: 8,
  border: '1px solid var(--border)',
  fontSize: 12,
  fontWeight: 500,
}
