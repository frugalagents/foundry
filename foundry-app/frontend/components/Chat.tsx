'use client'

import { useEffect, useRef, useState, useCallback, KeyboardEvent } from 'react'
import { nanoid } from 'nanoid'
import { useStore } from '@/store'
import { useStream } from '@/hooks/useStream'
import { getOrCreateDefaultCustomer, createSession } from '@/lib/api'
import type { Message } from '@/lib/types'

// ── Minimal markdown renderer (no deps) ──────────────────────────────────────

function renderMarkdown(text: string): string {
  const html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/```[\s\S]*?```/g, (m) => {
      const inner = m.slice(3, -3).replace(/^[^\n]*\n/, '')
      return `<pre><code>${inner}</code></pre>`
    })
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^---+$/gm, '<hr />')
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/^(?!<[huplo]|<li|<pre|<blockquote|<hr)(.+)$/gm, '<p>$1</p>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')

  // When there are 2+ h2 sections, collapse them into accordion details blocks
  const parts = html.split(/(<h2>.*?<\/h2>)/g)
  if (parts.length < 5) return html  // fewer than 2 h2 sections — render as-is

  let result = parts[0]
  for (let i = 1; i < parts.length; i += 2) {
    const title   = parts[i].replace(/<\/?h2>/g, '')
    const content = parts[i + 1] ?? ''
    const open    = i === 1 ? ' open' : ''
    result += `<details${open}><summary>${title}</summary><div class="details-body">${content}</div></details>`
  }
  return result
}

// ── Typing cursor ─────────────────────────────────────────────────────────────

function Cursor() {
  return <span className="animate-blink" style={{ color: 'var(--accent)', marginLeft: 1 }}>▋</span>
}

// ── Message bubble ────────────────────────────────────────────────────────────

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  return (
    <div
      className="animate-fade-in"
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        padding: '4px 0',
      }}
    >
      {!isUser && (
        <div style={{
          width: 28, height: 28,
          borderRadius: '50%',
          background: 'var(--accent-dim)',
          border: '1px solid var(--accent-glow)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 13, flexShrink: 0, marginRight: 10, marginTop: 2,
        }}>⚡</div>
      )}
      <div style={{
        maxWidth: '78%',
        padding: isUser ? '10px 14px' : '12px 14px',
        background: isUser ? 'var(--accent)' : 'var(--bg-elevated)',
        border: isUser ? 'none' : '1px solid var(--border)',
        borderRadius: isUser
          ? '14px 14px 4px 14px'
          : '4px 14px 14px 14px',
        color: isUser ? '#fff' : 'var(--text)',
        fontSize: 14,
        lineHeight: 1.65,
      }}>
        {isUser ? (
          <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
        ) : (
          <>
            <div
              className="prose"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content || '') }}
            />
            {msg.streaming && <Cursor />}
          </>
        )}
      </div>
    </div>
  )
}

// ── Empty state ────────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      gap: 12, padding: '40px 24px',
    }}>
      <div style={{
        width: 52, height: 52, borderRadius: 14,
        background: 'var(--accent-dim)',
        border: '1px solid var(--accent-glow)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 24,
      }}>⚡</div>
      <h2 style={{ fontSize: 17, fontWeight: 600, color: 'var(--text)', textAlign: 'center' }}>
        Enterprise AI Foundry
      </h2>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', maxWidth: 360, lineHeight: 1.6 }}>
        Tell me about the platform you&apos;re working on — Coding Agent, Product Platform, or Fabric — and I&apos;ll help you architect and advise on the right solution.
      </p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginTop: 4 }}>
        {['Coding Agent Platform', 'Product Platform', 'Fabric'].map((m) => (
          <span key={m} style={{
            fontSize: 12, color: 'var(--text-muted)',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            padding: '4px 10px', borderRadius: 20,
          }}>{m}</span>
        ))}
      </div>
    </div>
  )
}

// ── Main Chat component ───────────────────────────────────────────────────────

export default function Chat() {
  const {
    messages,
    streaming,
    activeCustomerId,
    activeSessionId,
    setActiveSession,
    prependConversation,
    updateConversation,
  } = useStore()

  const { send, abort } = useStream()
  const [input, setInput] = useState('')
  const [creating, setCreating] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [input])

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || streaming) return
    setInput('')

    let cid = activeCustomerId
    let sid = activeSessionId

    // First message: auto-create customer + session
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

    // Update sidebar title after first message
    updateConversation(sid!, { updated_at: new Date().toISOString() })
  }, [input, streaming, activeCustomerId, activeSessionId, send, setActiveSession, prependConversation, updateConversation])

  const handleKey = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  const canSend = input.trim().length > 0 && !streaming && !creating

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      height: '100%', overflow: 'hidden', minWidth: 0,
      background: 'var(--bg)',
    }}>
      {/* Messages */}
      <div style={{
        flex: 1, overflowY: 'auto',
        padding: '24px 0',
        display: 'flex', flexDirection: 'column',
      }}>
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div style={{
            maxWidth: 760, width: '100%', margin: '0 auto',
            padding: '0 24px',
            display: 'flex', flexDirection: 'column', gap: 2,
          }}>
            {messages.map((m) => (
              <MessageBubble key={m.id} msg={m} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div style={{
        borderTop: '1px solid var(--border)',
        padding: '14px 24px 18px',
        background: 'var(--bg)',
      }}>
        <div style={{
          maxWidth: 760,
          margin: '0 auto',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: 14,
          display: 'flex',
          alignItems: 'flex-end',
          gap: 0,
          padding: '2px 4px 4px 14px',
          transition: 'border-color var(--transition)',
        }}
          onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--border-focus)')}
          onBlur={(e)  => (e.currentTarget.style.borderColor = 'var(--border)')}
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask me about your platform…"
            rows={1}
            style={{
              flex: 1,
              background: 'none',
              border: 'none',
              outline: 'none',
              color: 'var(--text)',
              fontSize: 14,
              lineHeight: 1.6,
              resize: 'none',
              padding: '10px 4px 10px 0',
              fontFamily: 'inherit',
              overflowY: 'auto',
              maxHeight: 200,
            }}
          />
          <div style={{ display: 'flex', alignItems: 'flex-end', padding: '4px 4px 4px 0', gap: 4 }}>
            {streaming && (
              <button
                onClick={abort}
                title="Stop generation"
                style={{
                  width: 34, height: 34, borderRadius: 10,
                  background: 'var(--red)',
                  border: 'none', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="white">
                  <rect x="4" y="4" width="16" height="16" rx="2" />
                </svg>
              </button>
            )}
            <button
              onClick={handleSend}
              disabled={!canSend}
              title="Send (Enter)"
              style={{
                width: 34, height: 34, borderRadius: 10,
                background: canSend ? 'var(--accent)' : 'var(--bg-hover)',
                border: 'none',
                cursor: canSend ? 'pointer' : 'default',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
                transition: 'background var(--transition)',
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                stroke={canSend ? '#fff' : 'var(--text-faint)'} strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
        <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-faint)', marginTop: 8 }}>
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
