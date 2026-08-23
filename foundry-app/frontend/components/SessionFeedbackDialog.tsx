'use client'

import { useEffect, useState } from 'react'
import { getSessionFeedback, submitSessionFeedback } from '@/lib/api'
import type { SessionFeedbackInput } from '@/lib/types'

const DEFAULT_FORM: SessionFeedbackInput = {
  rating: 4,
  most_useful: '',
  missing: '',
  additional_comments: '',
  reused_in_doc_or_meeting: null,
  agreed_with_recommendation: null,
  would_reuse: null,
}

export default function SessionFeedbackDialog({
  open,
  customerId,
  sessionId,
  sessionTitle,
  onClose,
}: {
  open: boolean
  customerId: string | null
  sessionId: string | null
  sessionTitle?: string | null
  onClose: () => void
}) {
  const [form, setForm] = useState<SessionFeedbackInput>(DEFAULT_FORM)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [savedAt, setSavedAt] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !customerId || !sessionId) return

    let cancelled = false
    setLoading(true)
    setError(null)
    setSavedAt(null)

    void getSessionFeedback(customerId, sessionId)
      .then((feedback) => {
        if (cancelled) return
        if (feedback) {
          setForm({
            rating: feedback.rating,
            most_useful: feedback.most_useful,
            missing: feedback.missing,
            additional_comments: feedback.additional_comments,
            reused_in_doc_or_meeting: feedback.reused_in_doc_or_meeting ?? null,
            agreed_with_recommendation: feedback.agreed_with_recommendation ?? null,
            would_reuse: feedback.would_reuse ?? null,
          })
          setSavedAt(feedback.updated_at)
        } else {
          setForm(DEFAULT_FORM)
        }
      })
      .catch((err) => {
        console.error('[SessionFeedbackDialog] Failed to load feedback:', err)
        if (!cancelled) setError('Could not load feedback for this session.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [open, customerId, sessionId])

  if (!open) return null

  async function handleSave() {
    if (!customerId || !sessionId || saving) return
    setSaving(true)
    setError(null)
    try {
      const saved = await submitSessionFeedback(customerId, sessionId, form)
      setSavedAt(saved.updated_at)
    } catch (err) {
      console.error('[SessionFeedbackDialog] Failed to save feedback:', err)
      setError('Could not save feedback right now.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={overlayStyle}>
      <div style={dialogStyle}>
        <div style={headerStyle}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>Session Feedback</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              {sessionTitle || 'Current session'}
            </div>
          </div>
          <button onClick={onClose} style={closeButtonStyle}>Close</button>
        </div>

        <div style={bodyStyle}>
          <Field label="Overall usefulness">
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {[1, 2, 3, 4, 5].map((rating) => (
                <button
                  key={rating}
                  onClick={() => setForm((current) => ({ ...current, rating }))}
                  style={choiceButtonStyle(form.rating === rating)}
                >
                  {rating}
                </button>
              ))}
            </div>
          </Field>

          <Field label="Would you reuse this recommendation flow?">
            <BooleanChoice
              value={form.would_reuse}
              onChange={(value) => setForm((current) => ({ ...current, would_reuse: value }))}
            />
          </Field>

          <Field label="Did you agree with the recommendation?">
            <BooleanChoice
              value={form.agreed_with_recommendation}
              onChange={(value) => setForm((current) => ({ ...current, agreed_with_recommendation: value }))}
            />
          </Field>

          <Field label="Was any output reused in a meeting or document?">
            <BooleanChoice
              value={form.reused_in_doc_or_meeting}
              onChange={(value) => setForm((current) => ({ ...current, reused_in_doc_or_meeting: value }))}
            />
          </Field>

          <Field label="Most useful part">
            <textarea
              value={form.most_useful}
              onChange={(event) => setForm((current) => ({ ...current, most_useful: event.target.value }))}
              placeholder="What helped most?"
              rows={3}
              style={textareaStyle}
            />
          </Field>

          <Field label="What was missing or weak?">
            <textarea
              value={form.missing}
              onChange={(event) => setForm((current) => ({ ...current, missing: event.target.value }))}
              placeholder="What should improve next?"
              rows={3}
              style={textareaStyle}
            />
          </Field>

          <Field label="Additional comments">
            <textarea
              value={form.additional_comments}
              onChange={(event) => setForm((current) => ({ ...current, additional_comments: event.target.value }))}
              placeholder="Anything else worth capturing?"
              rows={4}
              style={textareaStyle}
            />
          </Field>

          {loading ? <div style={metaStyle}>Loading existing feedback…</div> : null}
          {savedAt ? <div style={metaStyle}>Last saved {new Date(savedAt).toLocaleString()}</div> : null}
          {error ? <div style={{ ...metaStyle, color: 'var(--red)' }}>{error}</div> : null}
        </div>

        <div style={footerStyle}>
          <button onClick={onClose} style={secondaryButtonStyle}>Cancel</button>
          <button onClick={() => void handleSave()} disabled={saving || loading} style={primaryButtonStyle(saving || loading)}>
            {saving ? 'Saving…' : 'Save Feedback'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{label}</span>
      {children}
    </label>
  )
}

function BooleanChoice({
  value,
  onChange,
}: {
  value: boolean | null | undefined
  onChange: (next: boolean | null) => void
}) {
  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      <button onClick={() => onChange(true)} style={choiceButtonStyle(value === true)}>Yes</button>
      <button onClick={() => onChange(false)} style={choiceButtonStyle(value === false)}>No</button>
      <button onClick={() => onChange(null)} style={choiceButtonStyle(value == null)}>Unset</button>
    </div>
  )
}

const overlayStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(28, 25, 23, 0.38)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 20,
  zIndex: 120,
}

const dialogStyle: React.CSSProperties = {
  width: 'min(760px, 100%)',
  maxHeight: 'min(88vh, 900px)',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
  borderRadius: 18,
  background: 'rgba(255,253,249,0.98)',
  border: '1px solid var(--border)',
  boxShadow: '0 18px 50px rgba(15, 23, 42, 0.18)',
}

const headerStyle: React.CSSProperties = {
  padding: '16px 18px',
  borderBottom: '1px solid var(--border)',
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: 12,
}

const bodyStyle: React.CSSProperties = {
  padding: 18,
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
  overflowY: 'auto',
}

const footerStyle: React.CSSProperties = {
  padding: '14px 18px 18px',
  borderTop: '1px solid var(--border)',
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 10,
}

const metaStyle: React.CSSProperties = {
  fontSize: 12,
  color: 'var(--text-muted)',
}

const closeButtonStyle: React.CSSProperties = {
  border: '1px solid var(--border)',
  background: 'var(--bg-elevated)',
  color: 'var(--text)',
  borderRadius: 8,
  padding: '7px 11px',
  fontSize: 12.5,
  cursor: 'pointer',
}

const secondaryButtonStyle: React.CSSProperties = {
  border: '1px solid var(--border)',
  background: 'var(--bg-elevated)',
  color: 'var(--text)',
  borderRadius: 10,
  padding: '9px 14px',
  fontSize: 12.5,
  fontWeight: 600,
  cursor: 'pointer',
}

function primaryButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    border: '1px solid var(--accent)',
    background: disabled ? 'var(--accent-dim)' : 'var(--accent)',
    color: disabled ? 'var(--text-muted)' : '#fff',
    borderRadius: 10,
    padding: '9px 14px',
    fontSize: 12.5,
    fontWeight: 600,
    cursor: disabled ? 'default' : 'pointer',
    opacity: disabled ? 0.72 : 1,
  }
}

function choiceButtonStyle(active: boolean): React.CSSProperties {
  return {
    border: `1px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
    background: active ? 'var(--accent-glow)' : 'var(--bg-elevated)',
    color: active ? 'var(--accent)' : 'var(--text)',
    borderRadius: 999,
    padding: '7px 12px',
    fontSize: 12.5,
    fontWeight: 600,
    cursor: 'pointer',
  }
}

const textareaStyle: React.CSSProperties = {
  width: '100%',
  resize: 'vertical',
  borderRadius: 12,
  border: '1px solid var(--border)',
  background: 'var(--bg)',
  color: 'var(--text)',
  padding: '10px 12px',
  fontSize: 13,
  lineHeight: 1.55,
  outline: 'none',
}
