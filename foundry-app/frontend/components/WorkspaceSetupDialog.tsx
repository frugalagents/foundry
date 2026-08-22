'use client'

import { FormEvent, useEffect, useRef, useState } from 'react'
import { ApiError } from '@/lib/api'

interface WorkspaceSetupDialogProps {
  open: boolean
  onCancel: () => void
  onCreate: (project: string, purpose: string) => Promise<void>
}

function workspaceErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'Your sign-in has expired. Sign out, sign in again, and retry.'
    }
    if (error.status === 403) {
      return `You do not have permission to create this workspace. ${error.detail ?? ''}`.trim()
    }
    if (error.detail) {
      return `Could not create the workspace. ${error.detail}`
    }
  }
  return 'Could not create the workspace. Please try again.'
}

export default function WorkspaceSetupDialog({
  open,
  onCancel,
  onCreate,
}: WorkspaceSetupDialogProps) {
  const [project, setProject] = useState('')
  const [purpose, setPurpose] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const projectRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!open) return
    setProject('')
    setPurpose('')
    setError(null)
    setSubmitting(false)
    window.setTimeout(() => projectRef.current?.focus(), 0)
  }, [open])

  useEffect(() => {
    if (!open) return
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !submitting) onCancel()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onCancel, open, submitting])

  if (!open) return null

  const canCreate = project.trim().length > 0 && purpose.trim().length > 0 && !submitting

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canCreate) return

    setSubmitting(true)
    setError(null)
    try {
      await onCreate(project.trim(), purpose.trim())
    } catch (err) {
      console.error('[WorkspaceSetupDialog] Failed to create workspace:', err)
      setError(workspaceErrorMessage(err))
      setSubmitting(false)
    }
  }

  return (
    <div
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !submitting) onCancel()
      }}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
        background: 'rgba(36,28,22,0.38)',
        backdropFilter: 'blur(5px)',
      }}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="workspace-setup-title"
        onSubmit={handleSubmit}
        style={{
          width: 'min(520px, 100%)',
          borderRadius: 18,
          border: '1px solid var(--border)',
          background: 'var(--bg-elevated)',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden',
        }}
      >
        <div style={{
          padding: '22px 24px 18px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 20,
        }}>
          <div>
            <div style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--accent)',
              marginBottom: 5,
            }}>
              New workspace
            </div>
            <h2 id="workspace-setup-title" style={{
              fontSize: 20,
              lineHeight: 1.3,
              color: 'var(--text)',
              marginBottom: 6,
            }}>
              What are we working on?
            </h2>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
              The project becomes the workspace name. The purpose gives the advisor context before the first message.
            </p>
          </div>
          <button
            type="button"
            aria-label="Close"
            onClick={onCancel}
            disabled={submitting}
            style={{
              width: 30,
              height: 30,
              flexShrink: 0,
              borderRadius: 8,
              border: '1px solid var(--border)',
              background: 'var(--bg)',
              color: 'var(--text-muted)',
              cursor: submitting ? 'default' : 'pointer',
              fontSize: 18,
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        <div style={{ padding: '20px 24px 24px', display: 'flex', flexDirection: 'column', gap: 18 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>
              Project
            </span>
            <input
              ref={projectRef}
              value={project}
              onChange={(event) => setProject(event.target.value)}
              maxLength={120}
              disabled={submitting}
              placeholder="Example: Enterprise coding agent platform"
              style={{
                width: '100%',
                border: '1px solid var(--border)',
                borderRadius: 10,
                background: 'var(--bg)',
                color: 'var(--text)',
                padding: '11px 12px',
                font: 'inherit',
                outline: 'none',
              }}
            />
            <span style={{ alignSelf: 'flex-end', fontSize: 10.5, color: 'var(--text-faint)' }}>
              {project.length}/120
            </span>
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>
              Purpose
            </span>
            <textarea
              value={purpose}
              onChange={(event) => setPurpose(event.target.value)}
              maxLength={500}
              disabled={submitting}
              rows={4}
              placeholder="What decision, outcome, or problem should this workspace address?"
              style={{
                width: '100%',
                border: '1px solid var(--border)',
                borderRadius: 10,
                background: 'var(--bg)',
                color: 'var(--text)',
                padding: '11px 12px',
                font: 'inherit',
                lineHeight: 1.55,
                resize: 'vertical',
                outline: 'none',
              }}
            />
            <span style={{ alignSelf: 'flex-end', fontSize: 10.5, color: 'var(--text-faint)' }}>
              {purpose.length}/500
            </span>
          </label>

          {error ? (
            <div style={{
              padding: '9px 11px',
              borderRadius: 9,
              border: '1px solid rgba(194,65,56,0.24)',
              background: 'rgba(194,65,56,0.08)',
              color: 'var(--red)',
              fontSize: 12,
            }}>
              {error}
            </div>
          ) : null}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 9, paddingTop: 2 }}>
            <button
              type="button"
              onClick={onCancel}
              disabled={submitting}
              style={{
                border: '1px solid var(--border)',
                borderRadius: 9,
                background: 'transparent',
                color: 'var(--text-muted)',
                padding: '9px 14px',
                fontSize: 12.5,
                fontWeight: 600,
                cursor: submitting ? 'default' : 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canCreate}
              style={{
                border: 'none',
                borderRadius: 9,
                background: canCreate ? 'var(--accent)' : 'var(--bg-hover)',
                color: canCreate ? '#fff' : 'var(--text-faint)',
                padding: '9px 16px',
                fontSize: 12.5,
                fontWeight: 700,
                cursor: canCreate ? 'pointer' : 'default',
                minWidth: 128,
              }}
            >
              {submitting ? 'Creating…' : 'Create workspace'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
