'use client'

import { useEffect, useRef, useState, useCallback, KeyboardEvent, useMemo, type CSSProperties } from 'react'
import { useStore } from '@/store'
import { useConversationSend } from '@/hooks/useConversationSend'
import { analyzeAgentMessage, type AgentMsgType } from '@/lib/message-analysis'
import { renderMarkdown } from '@/lib/render-markdown'
import { isMaintenanceMessage } from '@/lib/session-normalization'
import { resolveAdvisoryStage, type AdvisoryStage } from '@/lib/workflow'
import type { Message } from '@/lib/types'

// ── Phase detection ───────────────────────────────────────────────────────────

const PHASES: { id: AdvisoryStage; label: string }[] = [
  { id: 'discovery', label: 'Discovery' },
  { id: 'solutioning', label: 'Solutioning' },
  { id: 'blueprint', label: 'Blueprint' },
]

// ── Phase breadcrumb ──────────────────────────────────────────────────────────

function PhaseBreadcrumb({ phase }: { phase: AdvisoryStage }) {
  const phaseIndex = PHASES.findIndex((p) => p.id === phase)
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '8px 24px', borderBottom: '1px solid var(--border)',
      background: 'var(--bg)', flexShrink: 0,
    }}>
      {PHASES.map((p, i) => {
        const active = p.id === phase
        const done = i < phaseIndex
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

function normalizeQuestionKey(text: string) {
  return text
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/[?]+$/, '')
    .toLowerCase()
}

function normalizeQuestionLine(text: string) {
  return text
    .trim()
    .replace(/^[-*]\s+/, '')
    .replace(/^\d+\.\s+/, '')
    .replace(/\s+/g, ' ')
}

function questionKeyFromLine(line: string) {
  const normalized = normalizeQuestionLine(line)
  if (!normalized.includes('?')) return null
  const withoutTrailingExplanation = normalized.replace(/\s*\([^)]*\)\s*$/, '').trim()
  const lastQuestionMark = withoutTrailingExplanation.lastIndexOf('?')
  const question = lastQuestionMark >= 0
    ? withoutTrailingExplanation.slice(0, lastQuestionMark + 1).trim()
    : withoutTrailingExplanation
  return question ? normalizeQuestionKey(question) : null
}

function stripDuplicatedOpenQuestions(content: string, openQuestionKeys: Set<string>) {
  const keptLines: string[] = []

  for (const line of content.split('\n')) {
    const questionKey = questionKeyFromLine(line)
    if (questionKey && openQuestionKeys.has(questionKey)) {
      continue
    }
    keptLines.push(line)
  }

  return keptLines
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function isResidualQuestionPrompt(content: string) {
  const normalized = content
    .trim()
    .replace(/\s+/g, ' ')
    .toLowerCase()

  if (!normalized) return true

  const boilerplatePrefixes = [
    'answer this open question',
    'please answer this open question',
    'to proceed, answer this open question',
    'i need your input',
    'i need an answer to',
    'this question affects the recommendation',
    'this question affects the architecture',
    'we still need your input',
    'open question',
    'needs your input',
  ]

  if (boilerplatePrefixes.some((prefix) => normalized === prefix || normalized.startsWith(`${prefix}:`))) {
    return true
  }

  const lines = content
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  if (lines.length === 1 && normalized.length < 120) {
    return boilerplatePrefixes.some((prefix) => normalized.includes(prefix))
  }

  return false
}

function normalizeArtifactText(text: string) {
  return text
    .toLowerCase()
    .replace(/[`*_>#-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function collectArtifactBodies(workspace: ReturnType<typeof useStore.getState>['workspace']) {
  if (!workspace) return []

  const advisoryCase = workspace.advisory_case
  const outputPack = advisoryCase?.output_pack
  const sections = [
    workspace.recommendation,
    workspace.blueprint_markdown,
    advisoryCase?.recommendation.summary,
    advisoryCase?.recommendation.why_this,
    advisoryCase?.readout.current_recommendation,
    advisoryCase?.readout.rollout_summary,
    advisoryCase?.readout.architecture_snapshot,
    outputPack?.executive_summary,
    outputPack?.recommendation_memo,
    outputPack?.architecture_narrative,
    outputPack?.key_decisions.join(' '),
    outputPack?.open_questions.join(' '),
    outputPack?.operating_principles.join(' '),
    outputPack?.control_checklist.join(' '),
    outputPack?.risks_and_mitigations.map((item) => `${item.risk} ${item.mitigation}`).join(' '),
    outputPack?.rollout_30_90_180.map((item) => `${item.horizon} ${item.outcome}`).join(' '),
  ]

  return sections
    .filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
    .map(normalizeArtifactText)
}

function isRedundantArtifactReply(content: string, artifactBodies: string[]) {
  if (artifactBodies.length === 0) return false

  const normalized = normalizeArtifactText(content)
  if (normalized.length < 280) return false

  let bodyMatches = 0
  for (const body of artifactBodies) {
    if (body.length < 140) continue
    const probe = body.slice(0, Math.min(180, body.length))
    if (normalized.includes(probe) || body.includes(normalized.slice(0, 140))) {
      bodyMatches += 1
    }
    if (bodyMatches >= 1) {
      return true
    }
  }

  const artifactHeadings = [
    'executive summary',
    'recommendation memo',
    'architecture narrative',
    'key decisions',
    'risks and mitigations',
    '30 / 90 / 180',
    'operating principles',
    'control checklist',
  ]
  const headingMatches = artifactHeadings.filter((heading) => normalized.includes(heading)).length

  return headingMatches >= 3
}

// ── Message bubble ────────────────────────────────────────────────────────────

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  const isEmpty = !msg.content.trim()
  const analysis = !isUser && !isEmpty ? analyzeAgentMessage(msg.content) : { type: 'observation' as AgentMsgType, questions: [] }
  const msgType = analysis.type
  const isQuestion = !isUser && msgType === 'question'
  const isMixed = !isUser && msgType === 'mixed'
  const shouldCollapse = !isUser && !isQuestion && !isMixed && !msg.streaming && msg.content.trim().length > 900
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className="animate-fade-in"
      style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', padding: '4px 0' }}
    >
      {!isUser && (
        <div style={{
          width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
          marginRight: 10, marginTop: 2,
          background: isQuestion || isMixed ? 'rgba(245,158,11,0.15)' : 'var(--accent-dim)',
          border: `1px solid ${isQuestion || isMixed ? 'rgba(245,158,11,0.4)' : 'var(--accent-glow)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 13,
          color: isQuestion || isMixed ? 'var(--amber)' : 'var(--accent)',
          fontWeight: 700,
        }}>
          {isQuestion || isMixed ? '?' : '⚡'}
        </div>
      )}

      <div style={{
        maxWidth: '78%',
        background: isUser
          ? 'var(--accent)'
          : isQuestion || isMixed
            ? 'rgba(245,158,11,0.06)'
            : 'var(--bg-elevated)',
        border: isUser
          ? 'none'
          : isQuestion || isMixed
            ? '1px solid rgba(245,158,11,0.3)'
            : '1px solid var(--border)',
        borderRadius: isUser ? '14px 14px 4px 14px' : '4px 14px 14px 14px',
        padding: isUser ? '10px 14px' : '12px 14px',
        color: isUser ? '#fff' : 'var(--text)',
        fontSize: 14,
        lineHeight: 1.65,
      }}>
        {(isQuestion || isMixed) && (
          <div style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
            color: 'var(--amber)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 5,
          }}>
            <span style={{
              width: 14, height: 14, borderRadius: 4, background: 'rgba(245,158,11,0.15)',
              border: '1px solid rgba(245,158,11,0.3)',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 9,
            }}>?</span>
            {isMixed ? 'Observation + input needed' : 'Needs your input'}
          </div>
        )}

        {isUser ? (
          <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
        ) : isEmpty && msg.streaming ? (
          <ThinkingDots />
        ) : (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {shouldCollapse && !expanded ? (
                <div style={{
                  fontSize: 11,
                  color: 'var(--text-faint)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}>
                  Detailed advisory content lives in the workspace panels.
                </div>
              ) : null}
              <div style={{ position: 'relative' }}>
                <div
                  className="prose"
                  style={shouldCollapse && !expanded ? collapsedMessageStyle : undefined}
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content || '') }}
                />
                {shouldCollapse && !expanded ? <div style={collapsedOverlayStyle} /> : null}
              </div>
              {shouldCollapse ? (
                <button
                  onClick={() => setExpanded((current) => !current)}
                  style={collapseButtonStyle}
                >
                  {expanded ? 'Show less' : 'Show full response'}
                </button>
              ) : null}
            </div>
            {msg.streaming && <Cursor />}
          </>
        )}
      </div>
    </div>
  )
}

// ── Starter prompts ───────────────────────────────────────────────────────────

const STARTERS = [
  'Recommend the right coding agent platform for 500 engineers on AWS',
  'Design a regulated enterprise architecture and call out the key tradeoffs',
  'Summarize the recommendation, risks, and rollout plan for a brownfield platform',
  'What target operating model should we adopt for an internal coding agent advisory?',
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
          Advisory Chat
        </h2>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Use chat to refine the recommendation, answer open questions, or challenge specific decisions. The primary brief lives in the workspace.
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

// ── Main Chat ─────────────────────────────────────────────────────────────────

export default function Chat() {
  const {
    messages,
    canvasNodes,
    workspace,
  } = useStore()

  const { abort, sendMessage, sending } = useConversationSend()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const hasCanvas = canvasNodes.length > 0
  const openQuestionKeys = useMemo(
    () => new Set((workspace?.open_questions ?? []).map(normalizeQuestionKey)),
    [workspace],
  )
  const artifactBodies = useMemo(() => collectArtifactBodies(workspace), [workspace])
  const hasWorkspaceArtifacts = artifactBodies.length > 0
  const visibleMessages = useMemo(() => {
    return messages
      .map((message) => {
        if (isMaintenanceMessage(message.content)) return message
        if (message.role !== 'agent' || !message.content.trim() || message.streaming) return message

        const content = openQuestionKeys.size > 0
          ? stripDuplicatedOpenQuestions(message.content, openQuestionKeys)
          : message.content
        return { ...message, content }
      })
      .filter((message) => {
        if (isMaintenanceMessage(message.content)) return false
        if (message.role === 'user' || message.streaming) return true
        if (!message.content.trim()) return false
        if (isRedundantArtifactReply(message.content, artifactBodies)) return false
        return !isResidualQuestionPrompt(message.content)
      })
  }, [artifactBodies, messages, openQuestionKeys])
  const phase = resolveAdvisoryStage(workspace?.stage, visibleMessages, hasCanvas)
  const hasMessages = visibleMessages.length > 0

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [visibleMessages])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [input])

  const doSend = useCallback(async (text: string) => {
    if (!text.trim() || sending) return
    setInput('')
    await sendMessage(text)
  }, [sendMessage, sending])

  const handleSend = useCallback(() => doSend(input.trim()), [doSend, input])

  const handleKey = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend])

  const canSend = input.trim().length > 0 && !sending

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--bg)' }}>
      {hasMessages && <PhaseBreadcrumb phase={phase} />}

      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 0', display: 'flex', flexDirection: 'column' }}>
        {hasWorkspaceArtifacts ? (
          <div style={{
            maxWidth: 720,
            width: '100%',
            margin: '0 auto 12px',
            padding: '0 20px',
          }}>
            <div style={{
              borderRadius: 10,
              border: '1px solid rgba(15,109,119,0.18)',
              background: 'rgba(15,109,119,0.05)',
              padding: '9px 12px',
              color: 'var(--text-muted)',
              fontSize: 12,
              lineHeight: 1.5,
            }}>
              Recommendation detail, blueprint updates, risks, and rollout belong in the workspace panels. Use chat for follow-ups, challenges, and clarifications.
            </div>
          </div>
        ) : null}
        {!hasMessages ? (
          <EmptyState onStarter={(s) => doSend(s)} />
        ) : (
          <div style={{
            maxWidth: 720, width: '100%', margin: '0 auto', padding: '0 20px',
            display: 'flex', flexDirection: 'column', gap: 2,
          }}>
            {visibleMessages.map((m) => <MessageBubble key={m.id} msg={m} />)}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{ borderTop: '1px solid var(--border)', padding: '12px 20px 16px', background: 'var(--bg)' }}>
        {openQuestionKeys.size > 0 ? (
          <div style={{
            maxWidth: 720,
            margin: '0 auto 10px',
            padding: '9px 12px',
            borderRadius: 10,
            background: 'rgba(245,158,11,0.08)',
            border: '1px solid rgba(245,158,11,0.22)',
            color: 'var(--amber)',
            fontSize: 12,
            lineHeight: 1.5,
          }}>
            Open questions are tracked in the `Questions` tab. Use chat for follow-ups or to challenge the recommendation after answering there.
          </div>
        ) : null}
        <div
          style={{
            maxWidth: 720, margin: '0 auto',
            background: 'var(--bg-elevated)', border: '1px solid var(--border)',
            borderRadius: 14, display: 'flex', alignItems: 'flex-end',
            padding: '2px 4px 4px 14px', transition: 'border-color var(--transition)',
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--border-focus)')}
          onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={sending ? 'Responding…' : 'Ask or reply…'}
            disabled={sending}
            rows={1}
            style={{
              flex: 1, background: 'none', border: 'none', outline: 'none',
              color: 'var(--text)', fontSize: 14, lineHeight: 1.6,
              resize: 'none', padding: '10px 4px 10px 0', fontFamily: 'inherit',
              overflowY: 'auto', maxHeight: 200,
              opacity: sending ? 0.5 : 1,
            }}
          />
          <div style={{ display: 'flex', alignItems: 'flex-end', padding: '4px 4px 4px 0', gap: 4 }}>
            {sending ? (
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
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={canSend ? '#fff' : 'var(--text-faint)'} strokeWidth="2.5">
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

const collapsedMessageStyle: CSSProperties = {
  maxHeight: 168,
  overflow: 'hidden',
}

const collapsedOverlayStyle: CSSProperties = {
  position: 'absolute',
  left: 0,
  right: 0,
  bottom: 0,
  height: 72,
  background: 'linear-gradient(to bottom, rgba(255,253,249,0), var(--bg-elevated))',
  pointerEvents: 'none',
}

const collapseButtonStyle: CSSProperties = {
  alignSelf: 'flex-start',
  padding: '6px 10px',
  borderRadius: 999,
  border: '1px solid var(--border)',
  background: 'var(--bg)',
  color: 'var(--text-muted)',
  fontSize: 12,
  fontWeight: 600,
  cursor: 'pointer',
}
