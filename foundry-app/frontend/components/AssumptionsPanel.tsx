'use client'

import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { useStore } from '@/store'
import { buildAssumptionCards } from '@/lib/assumptions'
import { useConversationSend } from '@/hooks/useConversationSend'
import type { WorkspaceAssumptionOption } from '@/lib/types'

export default function AssumptionsPanel({ baselineReady }: { baselineReady: boolean }) {
  const workspace = useStore((s) => s.workspace)
  const architectureArtifact = useStore((s) => s.architectureArtifact)
  const canvasNodes = useStore((s) => s.canvasNodes)
  const { sendMessage, sending } = useConversationSend()
  const [draftSelections, setDraftSelections] = useState<Record<string, WorkspaceAssumptionOption>>({})

  const assumptions = useMemo(
    () => buildAssumptionCards(workspace, architectureArtifact, canvasNodes),
    [architectureArtifact, canvasNodes, workspace],
  )

  useEffect(() => {
    setDraftSelections((current) => {
      const validIds = new Set(assumptions.map((assumption) => assumption.id))
      const nextEntries = Object.entries(current).filter(([id]) => validIds.has(id))
      return nextEntries.length === Object.keys(current).length ? current : Object.fromEntries(nextEntries)
    })
  }, [assumptions])

  function handleSelect(assumptionId: string, option: WorkspaceAssumptionOption) {
    setDraftSelections((current) => ({ ...current, [assumptionId]: option }))
  }

  function clearDrafts() {
    setDraftSelections({})
  }

  async function handleApplyBatch() {
    const selectedEntries = assumptions
      .map((assumption) => ({
        assumption,
        option: draftSelections[assumption.id],
      }))
      .filter((item): item is { assumption: typeof assumptions[number]; option: WorkspaceAssumptionOption } => Boolean(item.option))

    if (!baselineReady || selectedEntries.length === 0) return

    const prompt = [
      'Apply these assumption updates as one batch to the current baseline architecture.',
      'Refresh the architecture artifact, blueprint, and assumptions.',
      'Keep the chat response concise and focus on what changed, tradeoffs introduced, and any new open questions.',
      '',
      'Selected assumption updates:',
      ...selectedEntries.map(({ assumption, option }) => `- ${assumption.title}: ${option.label}\n  Instruction: ${option.prompt}`),
    ].join('\n')

    const sent = await sendMessage(prompt)
    if (sent) clearDrafts()
  }

  const draftCount = Object.keys(draftSelections).length

  return (
    <div style={{
      flex: 1,
      height: '100%',
      minHeight: 0,
      overflowY: 'auto',
      background: 'var(--bg)',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{
        padding: '14px 16px 12px',
        borderBottom: '1px solid var(--border)',
        position: 'sticky',
        top: 0,
        background: 'var(--bg)',
        zIndex: 2,
      }}>
        <span style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: 'var(--text-muted)',
        }}>
          Assumptions
        </span>
        <p style={{
          marginTop: 4,
          fontSize: 12,
          color: 'var(--text-faint)',
          lineHeight: 1.55,
        }}>
          {baselineReady
            ? 'Adjust assumptions here, then rebuild the recommendation in one batch instead of triggering one architecture refresh per click.'
            : 'These are working defaults only. The advisor should establish a baseline architecture first, then you can refine it here.'}
        </p>
        {baselineReady && draftCount > 0 ? (
          <div style={{
            marginTop: 10,
            padding: '10px 12px',
            borderRadius: 10,
            border: '1px solid var(--accent-glow)',
            background: 'var(--accent-dim)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
          }}>
            <span style={{ fontSize: 12.5, color: 'var(--text)', lineHeight: 1.5 }}>
              {draftCount} assumption change{draftCount === 1 ? '' : 's'} pending.
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button
                onClick={clearDrafts}
                disabled={sending}
                style={secondaryActionButtonStyle(sending)}
              >
                Clear
              </button>
              <button
                onClick={handleApplyBatch}
                disabled={sending}
                style={primaryActionButtonStyle(sending)}
              >
                {sending ? 'Rebuilding…' : 'Rebuild Architecture'}
              </button>
            </div>
          </div>
        ) : null}
      </div>

      <div style={{ padding: '14px 16px 24px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {assumptions.length === 0 ? (
          <section style={{
            border: '1px solid var(--border)',
            background: 'var(--bg-elevated)',
            borderRadius: 14,
            padding: '14px 14px 12px',
          }}>
            <p style={{ fontSize: 12.5, color: 'var(--text-faint)', lineHeight: 1.6 }}>
              No structured assumptions have been published by the engine yet. Once the recommendation takes shape, the assumption register will appear here with confidence and validation priority.
            </p>
          </section>
        ) : null}
        {assumptions.map((assumption) => (
          <section
            key={assumption.id}
            style={{
              border: '1px solid var(--border)',
              background: 'var(--bg-elevated)',
              borderRadius: 14,
              padding: '14px 14px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{assumption.title}</h3>
                <p style={{ marginTop: 4, fontSize: 12.5, color: 'var(--text)', lineHeight: 1.55 }}>
                  {assumption.assumed}
                </p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                <span style={confidencePillStyle(assumption.confidence)}>
                  {assumption.confidence === 'confirmed'
                    ? 'Confirmed'
                    : assumption.confidence === 'inferred'
                      ? 'Inferred'
                      : 'Default'}
                </span>
                {assumption.impact_level ? (
                  <span style={metaPillStyle(assumption.impact_level === 'high' ? 'warning' : 'neutral')}>
                    {assumption.impact_level} impact
                  </span>
                ) : null}
                {assumption.validation_priority ? (
                  <span style={metaPillStyle(assumption.validation_priority === 'now' ? 'warning' : 'neutral')}>
                    validate {assumption.validation_priority}
                  </span>
                ) : null}
                {assumption.drives_architecture ? (
                  <span style={metaPillStyle('success')}>
                    architecture driver
                  </span>
                ) : null}
              </div>
            </div>

            <AssumptionBlock label="Why this is assumed" text={assumption.why} />
            <AssumptionBlock label="What changes if this is wrong" text={assumption.impact} />

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {assumption.options.map((option) => {
                const selected = draftSelections[assumption.id]?.id === option.id
                return (
                  <button
                    key={option.id}
                    onClick={() => handleSelect(assumption.id, option)}
                    disabled={sending || !baselineReady}
                    style={{
                      padding: '8px 10px',
                      borderRadius: 9,
                      border: selected ? '1px solid var(--accent)' : '1px solid var(--border)',
                      background: selected ? 'var(--accent-dim)' : 'var(--bg)',
                      color: selected ? 'var(--accent-strong)' : 'var(--text)',
                      fontSize: 12.5,
                      fontWeight: 500,
                      cursor: sending || !baselineReady ? 'default' : 'pointer',
                      opacity: baselineReady ? 1 : 0.6,
                    }}
                    title={baselineReady ? option.prompt : 'Available after the baseline architecture is created'}
                  >
                    {selected ? `${option.label} Pending` : option.label}
                  </button>
                )
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}

function primaryActionButtonStyle(disabled: boolean) {
  return {
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--accent)',
    background: disabled ? 'var(--accent-dim)' : 'var(--accent)',
    color: disabled ? 'var(--accent-strong)' : '#fff',
    fontSize: 12,
    fontWeight: 600,
    cursor: disabled ? 'default' : 'pointer',
  } satisfies CSSProperties
}

function secondaryActionButtonStyle(disabled: boolean) {
  return {
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--border)',
    background: 'var(--bg)',
    color: disabled ? 'var(--text-faint)' : 'var(--text)',
    fontSize: 12,
    fontWeight: 500,
    cursor: disabled ? 'default' : 'pointer',
  } satisfies CSSProperties
}

function AssumptionBlock({ label, text }: { label: string; text: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{
        fontSize: 10.5,
        fontWeight: 700,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        color: 'var(--text-muted)',
      }}>
        {label}
      </span>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
        {text}
      </p>
    </div>
  )
}

function confidencePillStyle(confidence: 'default' | 'inferred' | 'confirmed') {
  return {
    padding: '5px 8px',
    borderRadius: 999,
    fontSize: 10.5,
    fontWeight: 700,
    textTransform: 'uppercase',
    whiteSpace: 'nowrap',
    background: confidence === 'confirmed'
      ? 'rgba(34,197,94,0.12)'
      : confidence === 'inferred'
        ? 'rgba(99,102,241,0.12)'
        : 'var(--bg)',
    border: `1px solid ${confidence === 'confirmed'
      ? 'rgba(34,197,94,0.24)'
      : confidence === 'inferred'
        ? 'rgba(99,102,241,0.24)'
        : 'var(--border)'}`,
    color: confidence === 'confirmed'
      ? 'var(--green)'
      : confidence === 'inferred'
        ? 'var(--accent-strong)'
        : 'var(--text-faint)',
  } satisfies CSSProperties
}

function metaPillStyle(tone: 'neutral' | 'warning' | 'success') {
  const palette = tone === 'warning'
    ? { background: 'rgba(183,121,31,0.12)', border: 'rgba(183,121,31,0.22)', color: 'var(--amber)' }
    : tone === 'success'
      ? { background: 'rgba(15,159,110,0.12)', border: 'rgba(15,159,110,0.2)', color: 'var(--green)' }
      : { background: 'var(--bg)', border: 'var(--border)', color: 'var(--text-faint)' }

  return {
    padding: '4px 8px',
    borderRadius: 999,
    fontSize: 10.5,
    fontWeight: 700,
    textTransform: 'uppercase',
    whiteSpace: 'nowrap',
    background: palette.background,
    border: `1px solid ${palette.border}`,
    color: palette.color,
  } satisfies CSSProperties
}
