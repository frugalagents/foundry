'use client'

import { useMemo } from 'react'
import { useStore } from '@/store'
import { extractOpenQuestions } from '@/lib/message-analysis'
import { renderMarkdown } from '@/lib/render-markdown'

export default function OpenQuestionsPanel() {
  const messages = useStore((s) => s.messages)
  const workspace = useStore((s) => s.workspace)
  const openQuestions = useMemo(() => {
    const workspaceQuestions = workspace?.open_questions ?? []
    if (workspaceQuestions.length > 0) {
      return workspaceQuestions.map((text, index) => ({ id: `workspace-${index}`, text }))
    }
    return extractOpenQuestions(messages)
  }, [messages, workspace])

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
              <div
                className="prose"
                style={{ fontSize: 12.5, color: 'var(--text)', lineHeight: 1.55 }}
                dangerouslySetInnerHTML={{ __html: renderMarkdown(question.text) }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
