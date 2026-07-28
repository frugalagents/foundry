'use client';
import { useEffect, useRef, useState } from 'react';
import { Send, Square } from 'lucide-react';
import type { ChatMessage, ConfirmationRequestEvent } from '@/lib/types';
import { Button } from '@/components/ui/Button';

interface ChatPanelProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  awaitingConfirmation: boolean;
  confirmationRequest: ConfirmationRequestEvent | null;
  onSendMessage: (content: string) => void;
  onConfirm: (choice: string) => void;
  onStop?: () => void;
}

export function ChatPanel({
  messages,
  isStreaming,
  awaitingConfirmation,
  confirmationRequest,
  onSendMessage,
  onConfirm,
  onStop,
}: ChatPanelProps) {
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  // Auto-grow the composer up to ~5 lines.
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`;
  }, [input]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  function handleSend() {
    const text = input.trim();
    if (!text) return;
    setInput('');
    onSendMessage(text);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  // The backend emits `message` but our type uses `question` — handle both
  const confirmMessage =
    (confirmationRequest as { message?: string; question?: string } | null)?.message ??
    confirmationRequest?.question ?? '';

  const confirmOptions = confirmationRequest?.options ?? ['Confirm'];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: 'var(--bg-card)',
        borderRight: '1px solid var(--border-default)',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--border-default)',
          fontSize: 13,
          fontWeight: 600,
          color: 'var(--text-secondary)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: isStreaming ? 'var(--accent-green)' : 'var(--border-default)',
            boxShadow: isStreaming ? '0 0 6px var(--accent-green)' : 'none',
          }}
        />
        Advisor
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}
      >
        {messages.length === 0 && (
          <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', marginTop: 24 }}>
            Complete the intake form to begin your advisory session.
          </p>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <div
              style={{
                maxWidth: '85%',
                padding: '8px 12px',
                borderRadius:
                  msg.role === 'user'
                    ? '12px 12px 2px 12px'
                    : '12px 12px 12px 2px',
                background:
                  msg.role === 'user'
                    ? 'rgba(88,166,255,0.2)'
                    : 'var(--bg-elevated)',
                border:
                  msg.role === 'user'
                    ? '1px solid rgba(88,166,255,0.3)'
                    : '1px solid var(--border-default)',
                fontSize: 13,
                color: 'var(--text-primary)',
                lineHeight: 1.55,
                whiteSpace: 'pre-wrap',
              }}
            >
              <SimpleMarkdown text={msg.content} />
              {msg.streaming && <BlinkingCursor />}
            </div>
          </div>
        ))}
        {isStreaming && messages.length > 0 && messages[messages.length - 1].role !== 'assistant' && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div
              style={{
                padding: '8px 12px',
                borderRadius: '12px 12px 12px 2px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-default)',
              }}
            >
              <ThinkingDots />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Confirmation bar */}
      {awaitingConfirmation && confirmationRequest && (
        <div
          style={{
            padding: '10px 12px',
            borderTop: '1px solid var(--border-default)',
            background: 'var(--bg-elevated)',
          }}
        >
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
            {confirmMessage}
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {confirmOptions.map((option, i) => (
              <Button
                key={option}
                size="sm"
                variant={i === 0 ? 'primary' : 'ghost'}
                onClick={() => onConfirm(option)}
              >
                {option}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div
        style={{
          padding: '10px 12px',
          borderTop: '1px solid var(--border-default)',
          display: 'flex',
          gap: 8,
          alignItems: 'flex-end',
        }}
      >
        <textarea
          ref={taRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? 'Advisor is responding…' : 'Ask the advisor…'}
          rows={1}
          style={{
            flex: 1,
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-primary)',
            padding: '8px 10px',
            fontSize: 'var(--text-sm)',
            outline: 'none',
            resize: 'none',
            fontFamily: 'inherit',
            lineHeight: 1.5,
          }}
        />
        {isStreaming && onStop ? (
          <Button size="sm" variant="secondary" onClick={onStop} style={{ flexShrink: 0 }} title="Stop generating">
            <Square size={12} /> Stop
          </Button>
        ) : (
          <Button
            size="sm"
            variant="primary"
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            style={{ flexShrink: 0 }}
          >
            <Send size={13} />
          </Button>
        )}
      </div>
    </div>
  );
}

function SimpleMarkdown({ text }: { text: string }) {
  const lines = text.split('\n');
  return (
    <>
      {lines.map((line, li) => {
        const parts = line.split(/(\*\*.*?\*\*)/g);
        return (
          <span key={li}>
            {parts.map((p, i) =>
              p.startsWith('**') && p.endsWith('**') ? (
                <strong key={i}>{p.slice(2, -2)}</strong>
              ) : (
                <span key={i}>{p}</span>
              )
            )}
            {li < lines.length - 1 && <br />}
          </span>
        );
      })}
    </>
  );
}

function ThinkingDots() {
  return (
    <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          style={{
            width: 6, height: 6,
            borderRadius: '50%',
            background: 'var(--text-muted)',
            animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
      <style>{`@keyframes pulse{0%,80%,100%{opacity:0.3}40%{opacity:1}}`}</style>
    </div>
  );
}

function BlinkingCursor() {
  return (
    <span
      style={{
        display: 'inline-block',
        width: 2,
        height: '1em',
        background: 'var(--accent-blue)',
        marginLeft: 2,
        verticalAlign: 'middle',
        animation: 'blink 1s step-end infinite',
      }}
    >
      <style>{`@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}`}</style>
    </span>
  );
}
