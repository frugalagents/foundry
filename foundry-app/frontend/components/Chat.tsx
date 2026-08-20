'use client'

import { useEffect, useRef, useState, useCallback, KeyboardEvent, useMemo } from 'react'
import { useStore } from '@/store'
import { useStream } from '@/hooks/useStream'
import { getOrCreateDefaultCustomer, createSession } from '@/lib/api'
import type { Message } from '@/lib/types'
import { analyzeAgentMessage, extractOpenQuestions } from '@/lib/message-analysis'
import { renderMarkdown } from '@/lib/render-markdown'
import {
  buildStrategicBriefPrompt,
  EMPTY_STRATEGIC_BRIEF,
  STRATEGIC_BRIEF_FIELDS,
  type StrategicBrief,
} from '@/lib/strategic-brief'

// ── Phase detection ───────────────────────────────────────────────────────────

type Phase = 'discovery' | 'solutioning' | 'blueprint'

function detectPhase(messages: Message[], hasCanvas: boolean, workspaceStage?: string | null): Phase {
  if (workspaceStage === 'discovery' || workspaceStage === 'solutioning' || workspaceStage === 'blueprint') {
    return workspaceStage
  }
  if (hasCanvas) return 'blueprint'
  const agentMsgs = messages.filter((m) => m.role === 'agent' && m.content.length > 0)
  if (agentMsgs.length >= 3) return 'solutioning'
  return 'discovery'
}

const PHASES: { id: Phase; label: string }[] = [
  { id: 'discovery',   label: 'Discovery'   },
  { id: 'solutioning', label: 'Solutioning' },
  { id: 'blueprint',   label: 'Blueprint'   },
]

// ── Phase breadcrumb ──────────────────────────────────────────────────────────

function PhaseBreadcrumb({ phase }: { phase: Phase }) {
  const phaseIndex = PHASES.findIndex((p) => p.id === phase)
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '8px 24px', borderBottom: '1px solid var(--border)',
      background: 'var(--bg)', flexShrink: 0,
    }}>
      {PHASES.map((p, i) => {
        const active  = p.id === phase
        const done    = i < phaseIndex
        return (
          <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '3px 10px', borderRadius: 20,
              background: active ? 'var(--accent-dim)' : 'transparent',
              border: `1px solid ${active ? 'var(--accent)' : 'transparent'}`,
            }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: active ? 'var(--accent)' : done ? 'var(--green)' : 'var(--border-focus)',
                flexShrink: 0,
              }} />
              <span style={{
                fontSize: 11, fontWeight: active ? 600 : 400,
                color: active ? 'var(--accent)' : done ? 'var(--text-muted)' : 'var(--text-faint)',
              }}>
                {p.label}
              </span>
            </div>
            {i < PHASES.length - 1 && (
              <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="var(--text-faint)" strokeWidth="2.5">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Typing cursor ─────────────────────────────────────────────────────────────

function Cursor() {
  return <span className="animate-blink" style={{ color: 'var(--accent)', marginLeft: 1 }}>▋</span>
}

// ── Thinking indicator (before first token arrives) ───────────────────────────

function ThinkingDots() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 0' }}>
      {[0, 1, 2].map((i) => (
        <span key={i} style={{
          width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)',
          animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
          display: 'inline-block',
        }} />
      ))}
    </div>
  )
}

// ── Message bubble ────────────────────────────────────────────────────────────

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  const isEmpty = !msg.content.trim()
  const analysis = (!isUser && !isEmpty)
    ? analyzeAgentMessage(msg.content)
    : { type: 'observation' as const, questions: [] }
  const msgType = analysis.type
  const isQuestion = !isUser && msgType === 'question'
  const isMixed = !isUser && msgType === 'mixed'

  return (
    <div
      className="animate-fade-in"
      style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', padding: '4px 0' }}
    >
      {!isUser && (
        <div style={{
          width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
          marginRight: 10, marginTop: 2,
          background: (isQuestion || isMixed) ? 'rgba(245,158,11,0.15)' : 'var(--accent-dim)',
          border: `1px solid ${(isQuestion || isMixed) ? 'rgba(245,158,11,0.4)' : 'var(--accent-glow)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: isQuestion ? 13 : 13,
          color: (isQuestion || isMixed) ? 'var(--amber)' : 'var(--accent)',
          fontWeight: 700,
        }}>
          {(isQuestion || isMixed) ? '?' : '⚡'}
        </div>
      )}

      <div style={{
        maxWidth: '78%',
        background: isUser
          ? 'var(--accent)'
          : isQuestion
            ? 'rgba(245,158,11,0.06)'
            : isMixed
              ? 'rgba(245,158,11,0.03)'
              : 'var(--bg-elevated)',
        border: isUser
          ? 'none'
          : isQuestion
            ? '1px solid rgba(245,158,11,0.3)'
            : isMixed
              ? '1px solid rgba(245,158,11,0.18)'
              : '1px solid var(--border)',
        borderRadius: isUser ? '14px 14px 4px 14px' : '4px 14px 14px 14px',
        padding: isUser ? '10px 14px' : '12px 14px',
        color: isUser ? '#fff' : 'var(--text)',
        fontSize: 14,
        lineHeight: 1.65,
      }}>
        {!isUser && !isEmpty && (
          <div style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
            color: (isQuestion || isMixed) ? 'var(--amber)' : 'var(--text-faint)',
            marginBottom: 8, display: 'flex', alignItems: 'center', gap: 5,
          }}>
            <span style={{
              width: 14, height: 14, borderRadius: 4,
              background: (isQuestion || isMixed) ? 'rgba(245,158,11,0.15)' : 'var(--bg-hover)',
              border: `1px solid ${(isQuestion || isMixed) ? 'rgba(245,158,11,0.3)' : 'var(--border)'}`,
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 9,
            }}>{(isQuestion || isMixed) ? '?' : 'i'}</span>
            {isQuestion ? 'Needs your input' : isMixed ? 'Observation + open questions' : 'Observation'}
          </div>
        )}

        {isUser ? (
          <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
        ) : isEmpty && msg.streaming ? (
          <ThinkingDots />
        ) : (
          <>
            <div className="prose" dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content || '') }} />
            {msg.streaming && <Cursor />}
          </>
        )}
      </div>
    </div>
  )
}

// ── Starter prompts ───────────────────────────────────────────────────────────

const STARTERS = [
  'Help me design a coding agent platform for my engineering team',
  'What harness should I use for a highly regulated environment?',
  'We need a coding agent platform for ~500 engineers on AWS',
  'Walk me through the tradeoffs between managed and self-hosted runtimes',
]

function EmptyState({ onStarter }: { onStarter: (text: string) => void }) {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      gap: 20, padding: '40px 24px',
    }}>
      <div style={{
        width: 52, height: 52, borderRadius: 14,
        background: 'var(--accent-dim)', border: '1px solid var(--accent-glow)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24,
      }}>⚡</div>
      <div style={{ textAlign: 'center', maxWidth: 380 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, color: 'var(--text)', marginBottom: 8 }}>
          Platform Advisor
        </h2>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
          I&apos;ll ask you a few questions to understand your scale, compliance needs, and team — then design an architecture and visualize it on the canvas.
        </p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%', maxWidth: 420 }}>
        {STARTERS.map((s) => (
          <button
            key={s}
            onClick={() => onStarter(s)}
            style={{
              background: 'var(--bg-elevated)', border: '1px solid var(--border)',
              borderRadius: 10, padding: '10px 14px', color: 'var(--text-muted)',
              fontSize: 13, textAlign: 'left', cursor: 'pointer', lineHeight: 1.5,
              transition: 'border-color var(--transition), color var(--transition)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-focus)'
              e.currentTarget.style.color = 'var(--text)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border)'
              e.currentTarget.style.color = 'var(--text-muted)'
            }}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

function StrategicBriefBuilder({
  brief,
  openQuestionCount,
  onPick,
  onAdditionalContextChange,
  onDraft,
  onSend,
}: {
  brief: StrategicBrief
  openQuestionCount: number
  onPick: (key: keyof Omit<StrategicBrief, 'additionalContext'>, value: string) => void
  onAdditionalContextChange: (value: string) => void
  onDraft: () => void
  onSend: () => void
}) {
  const selectedCount = STRATEGIC_BRIEF_FIELDS.filter((field) => brief[field.key]).length

  return (
    <div style={{
      maxWidth: 720,
      margin: '0 auto 10px',
      border: '1px solid rgba(99,102,241,0.28)',
      background: 'linear-gradient(180deg, rgba(99,102,241,0.1), rgba(99,102,241,0.04))',
      borderRadius: 14,
      padding: 14,
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{
            fontSize: 10.5,
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--accent-strong)',
          }}>
            Strategic Brief
          </span>
          <span style={{
            padding: '3px 8px',
            borderRadius: 999,
            background: 'var(--accent-dim)',
            border: '1px solid var(--accent-glow)',
            color: 'var(--accent-strong)',
            fontSize: 11,
          }}>
            {selectedCount} of {STRATEGIC_BRIEF_FIELDS.length} set
          </span>
          {openQuestionCount > 0 && (
            <span style={{
              padding: '3px 8px',
              borderRadius: 999,
              background: 'rgba(245,158,11,0.12)',
              border: '1px solid rgba(245,158,11,0.24)',
              color: 'var(--amber)',
              fontSize: 11,
            }}>
              {openQuestionCount} open question{openQuestionCount === 1 ? '' : 's'}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={onDraft} style={secondaryBriefButton}>
            Draft recommendation brief
          </button>
          <button onClick={onSend} style={primaryBriefButton}>
            Send brief now
          </button>
        </div>
      </div>

      <p style={{ fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.6 }}>
        Fill the operating brief once. The advisor should use this to produce a recommendation, not keep drilling into generic setup questions.
      </p>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
        gap: 10,
      }}>
        {STRATEGIC_BRIEF_FIELDS.map((field) => (
          <div
            key={field.key}
            style={{
              padding: 10,
              borderRadius: 10,
              border: '1px solid var(--border)',
              background: 'rgba(10,10,10,0.24)',
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)' }}>
              {field.label}
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {field.options.map((option) => {
                const selected = brief[field.key] === option.value
                return (
                  <button
                    key={option.label}
                    onClick={() => onPick(field.key, option.value)}
                    style={{
                      padding: '7px 9px',
                      borderRadius: 999,
                      border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`,
                      background: selected ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                      color: selected ? 'var(--accent-strong)' : 'var(--text-muted)',
                      fontSize: 11.5,
                      cursor: 'pointer',
                    }}
                  >
                    {option.label}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      <div style={{
        padding: 10,
        borderRadius: 10,
        border: '1px solid var(--border)',
        background: 'rgba(10,10,10,0.24)',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)' }}>
          Additional context
        </span>
        <textarea
          rows={3}
          value={brief.additionalContext}
          onChange={(e) => onAdditionalContextChange(e.target.value)}
          placeholder="Anything the advisor should assume or optimize for?"
          style={{
            width: '100%',
            resize: 'vertical',
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            color: 'var(--text)',
            fontSize: 12.5,
            lineHeight: 1.55,
            padding: '10px 12px',
            outline: 'none',
            fontFamily: 'inherit',
            minHeight: 88,
          }}
        />
      </div>
    </div>
  )
}

// ── Main Chat ─────────────────────────────────────────────────────────────────

export default function Chat() {
  const {
    messages, streaming,
    activeCustomerId, activeSessionId,
    setActiveSession, prependConversation, updateConversation,
    canvasNodes,
    workspace,
  } = useStore()

  const { send, abort } = useStream()
  const [input, setInput] = useState('')
  const [creating, setCreating] = useState(false)
  const [brief, setBrief] = useState<StrategicBrief>(EMPTY_STRATEGIC_BRIEF)
  const bottomRef   = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const hasCanvas = canvasNodes.length > 0
  const phase = detectPhase(messages, hasCanvas, workspace?.stage)
  const hasMessages = messages.length > 0
  const openQuestions = useMemo(() => {
    const workspaceQuestions = workspace?.open_questions ?? []
    if (workspaceQuestions.length > 0) return workspaceQuestions
    return extractOpenQuestions(messages).map((q) => q.text)
  }, [messages, workspace])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [input])

  const doSend = useCallback(async (text: string) => {
    if (!text.trim() || streaming) return
    setInput('')

    let cid = activeCustomerId
    let sid = activeSessionId

    if (!cid || !sid) {
      setCreating(true)
      try {
        const customer = await getOrCreateDefaultCustomer()
        cid = customer.customer_id
        const session = await createSession(cid, { title: text.slice(0, 60) })
        sid = session.session_id
        setActiveSession(cid, sid)
        prependConversation({ session, customer })
        history.pushState(null, '', `/sessions/${sid}`)
      } catch (err) {
        console.error('Failed to create session', err)
        setCreating(false)
        return
      }
      setCreating(false)
    }

    await send(text, cid!, sid!)
    updateConversation(sid!, { updated_at: new Date().toISOString() })
  }, [streaming, activeCustomerId, activeSessionId, send, setActiveSession, prependConversation, updateConversation])

  const handleSend = useCallback(() => doSend(input.trim()), [doSend, input])
  const setBriefField = useCallback((key: keyof Omit<StrategicBrief, 'additionalContext'>, value: string) => {
    setBrief((current) => ({ ...current, [key]: current[key] === value ? '' : value }))
  }, [])
  const draftBrief = useCallback(() => {
    const template = buildStrategicBriefPrompt(brief, openQuestions)
    setInput(template)
    requestAnimationFrame(() => textareaRef.current?.focus())
  }, [brief, openQuestions])
  const sendBrief = useCallback(() => {
    const template = buildStrategicBriefPrompt(brief, openQuestions)
    void doSend(template)
  }, [brief, doSend, openQuestions])

  const handleKey = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }, [handleSend])

  const canSend = input.trim().length > 0 && !streaming && !creating

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--bg)' }}>
      {/* Phase breadcrumb — only show once conversation has started */}
      {hasMessages && <PhaseBreadcrumb phase={phase} />}

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 0', display: 'flex', flexDirection: 'column' }}>
        {!hasMessages ? (
          <EmptyState onStarter={(s) => doSend(s)} />
        ) : (
          <div style={{
            maxWidth: 720, width: '100%', margin: '0 auto', padding: '0 20px',
            display: 'flex', flexDirection: 'column', gap: 2,
          }}>
            {messages.map((m) => <MessageBubble key={m.id} msg={m} />)}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div style={{ borderTop: '1px solid var(--border)', padding: '12px 20px 16px', background: 'var(--bg)' }}>
        {!streaming && (
          <StrategicBriefBuilder
            brief={brief}
            openQuestionCount={openQuestions.length}
            onPick={setBriefField}
            onAdditionalContextChange={(value) => setBrief((current) => ({ ...current, additionalContext: value }))}
            onDraft={draftBrief}
            onSend={sendBrief}
          />
        )}

        <div
          style={{
            maxWidth: 720, margin: '0 auto',
            background: 'var(--bg-elevated)', border: '1px solid var(--border)',
            borderRadius: 14, display: 'flex', alignItems: 'flex-end',
            padding: '2px 4px 4px 14px', transition: 'border-color var(--transition)',
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--border-focus)')}
          onBlur={(e)  => (e.currentTarget.style.borderColor = 'var(--border)')}
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={streaming ? 'Responding…' : 'Ask or reply…'}
            disabled={streaming}
            rows={1}
            style={{
              flex: 1, background: 'none', border: 'none', outline: 'none',
              color: 'var(--text)', fontSize: 14, lineHeight: 1.6,
              resize: 'none', padding: '10px 4px 10px 0', fontFamily: 'inherit',
              overflowY: 'auto', maxHeight: 200,
              opacity: streaming ? 0.5 : 1,
            }}
          />
          <div style={{ display: 'flex', alignItems: 'flex-end', padding: '4px 4px 4px 0', gap: 4 }}>
            {streaming ? (
              <button
                onClick={abort}
                title="Stop"
                style={{
                  width: 34, height: 34, borderRadius: 10, background: 'var(--red)',
                  border: 'none', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="white">
                  <rect x="4" y="4" width="16" height="16" rx="2" />
                </svg>
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!canSend}
                title="Send (Enter)"
                style={{
                  width: 34, height: 34, borderRadius: 10,
                  background: canSend ? 'var(--accent)' : 'var(--bg-hover)',
                  border: 'none', cursor: canSend ? 'pointer' : 'default',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'background var(--transition)',
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                  stroke={canSend ? '#fff' : 'var(--text-faint)'} strokeWidth="2.5">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            )}
          </div>
        </div>
        <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-faint)', marginTop: 6 }}>
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}

const primaryBriefButton: React.CSSProperties = {
  padding: '7px 10px',
  borderRadius: 8,
  border: '1px solid var(--accent)',
  background: 'var(--accent)',
  color: '#fff',
  fontSize: 12,
  fontWeight: 600,
  cursor: 'pointer',
}

const secondaryBriefButton: React.CSSProperties = {
  padding: '7px 10px',
  borderRadius: 8,
  border: '1px solid var(--border)',
  background: 'var(--bg-elevated)',
  color: 'var(--text)',
  fontSize: 12,
  fontWeight: 600,
  cursor: 'pointer',
}
