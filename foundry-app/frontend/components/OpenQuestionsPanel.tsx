'use client'

import { useMemo, useState, type CSSProperties } from 'react'
import { useStore } from '@/store'
import { useConversationSend } from '@/hooks/useConversationSend'
import { extractOpenQuestions } from '@/lib/message-analysis'
import { renderMarkdown } from '@/lib/render-markdown'

export default function OpenQuestionsPanel() {
  const messages = useStore((s) => s.messages)
  const workspace = useStore((s) => s.workspace)
  const { sendMessage, sending } = useConversationSend()
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [submittingId, setSubmittingId] = useState<string | null>(null)
  const openQuestions = useMemo(() => {
    const workspaceQuestions = workspace?.open_questions ?? []
    if (workspaceQuestions.length > 0) {
      return workspaceQuestions.map((text, index) => ({ id: `workspace-${index}`, text }))
    }
    return extractOpenQuestions(messages)
  }, [messages, workspace])
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

  async function handleSubmit(questionId: string, questionText: string) {
    const answer = drafts[questionId]?.trim()
    if (!answer) return
    setSubmittingId(questionId)
    try {
      const sent = await sendMessage(answer, {
        title: 'Panel answer',
        appendToTranscript: false,
        action: {
          kind: 'open_question_answer',
          question: questionText,
          answer,
        },
      })
      if (sent) {
        setDrafts((current) => ({ ...current, [questionId]: '' }))
      }
    } finally {
      setSubmittingId(null)
    }
  }

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
        <span style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: 'var(--text-muted)',
        }}>
          Open Questions
        </span>
        <span style={{
          minWidth: 22,
          height: 22,
          padding: '0 7px',
          borderRadius: 999,
          background: openQuestions.length > 0 ? 'rgba(245,158,11,0.14)' : 'var(--bg-hover)',
          border: `1px solid ${openQuestions.length > 0 ? 'rgba(245,158,11,0.3)' : 'var(--border)'}`,
          color: openQuestions.length > 0 ? 'var(--amber)' : 'var(--text-faint)',
          fontSize: 11,
          fontWeight: 700,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          {openQuestions.length}
        </span>
      </div>

      {answeredQuestions.length > 1 ? (
        <div style={batchCardStyle}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={batchTitleStyle}>Batch Send</span>
            <p style={batchBodyStyle}>
              {answeredQuestions.length} question answers are drafted. Send them together so the engine refreshes the recommendation once.
            </p>
          </div>
          <button
            onClick={handleSubmitAll}
            disabled={sending}
            style={{
              ...submitButtonStyle,
              background: submittingId === 'all' ? 'var(--accent-dim)' : 'var(--bg)',
              color: submittingId === 'all' ? 'var(--accent-strong)' : 'var(--text)',
              cursor: sending ? 'default' : 'pointer',
            }}
          >
            {submittingId === 'all' ? 'Sending…' : `Send ${answeredQuestions.length} Answers`}
          </button>
        </div>
      ) : null}

      {openQuestions.length === 0 ? (
        <p style={{ fontSize: 12.5, color: 'var(--text-faint)', lineHeight: 1.6 }}>
          No unanswered questions right now. When the advisor needs input, the prompt will stay visible here.
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
              <span style={{
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
              }}>
                {index + 1}
              </span>
              <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div
                  className="prose"
                  style={{ fontSize: 12.5, color: 'var(--text)', lineHeight: 1.55 }}
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(question.text) }}
                />
                <textarea
                  value={drafts[question.id] ?? ''}
                  onChange={(e) => setDrafts((current) => ({ ...current, [question.id]: e.target.value }))}
                  placeholder="Answer here without typing in the main chat…"
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
                  }}
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    onClick={() => handleSubmit(question.id, question.text)}
                    disabled={sending || !(drafts[question.id] ?? '').trim()}
                    style={{
                      ...submitButtonStyle,
                      background: submittingId === question.id ? 'var(--accent-dim)' : 'var(--bg)',
                      color: submittingId === question.id ? 'var(--accent-strong)' : 'var(--text)',
                      cursor: sending || !(drafts[question.id] ?? '').trim() ? 'default' : 'pointer',
                    }}
                  >
                    {submittingId === question.id ? 'Sending…' : 'Send Answer'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
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
