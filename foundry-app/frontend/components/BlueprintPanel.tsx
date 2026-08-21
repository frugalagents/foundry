'use client'

import { useMemo, useState } from 'react'
import { useStore } from '@/store'
import { normalizeWorkspace } from '@/lib/message-analysis'
import { renderMarkdown } from '@/lib/render-markdown'
import type { ArchitectureArtifact, ConsultingWorkspace } from '@/lib/types'

export default function BlueprintPanel() {
  const workspace = useStore((s) => s.workspace)
  const architectureArtifact = useStore((s) => s.architectureArtifact)
  const activeSessionId = useStore((s) => s.activeSessionId)
  const [copied, setCopied] = useState(false)

  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])
  const blueprintMarkdown = useMemo(
    () => (view.blueprint_markdown?.trim() || buildFallbackBlueprint(view, architectureArtifact)).trim(),
    [view, architectureArtifact],
  )

  const hasBlueprint = blueprintMarkdown.length > 0

  async function handleCopy() {
    if (!hasBlueprint) return
    try {
      await navigator.clipboard.writeText(blueprintMarkdown)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch (err) {
      console.error('Failed to copy blueprint', err)
    }
  }

  function handleDownload() {
    if (!hasBlueprint) return
    downloadTextFile(
      `${activeSessionId ?? 'foundry-blueprint'}.md`,
      blueprintMarkdown,
      'text/markdown;charset=utf-8',
    )
  }

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
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 12,
        position: 'sticky',
        top: 0,
        background: 'var(--bg)',
        zIndex: 2,
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
          }}>
            Blueprint
          </span>
          <p style={{
            fontSize: 12,
            color: 'var(--text-faint)',
            lineHeight: 1.55,
          }}>
            The technical artifact lives here. Chat should only acknowledge when this updates.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <ArtifactButton onClick={handleCopy} disabled={!hasBlueprint}>
            {copied ? 'Copied' : 'Copy'}
          </ArtifactButton>
          <ArtifactButton onClick={handleDownload} disabled={!hasBlueprint}>
            Download MD
          </ArtifactButton>
        </div>
      </div>

      {!hasBlueprint ? (
        <div style={{ padding: '18px 16px' }}>
          <p style={{ fontSize: 12.5, color: 'var(--text-faint)', lineHeight: 1.65 }}>
            The blueprint will appear here once the advisor has enough context to produce a coherent recommendation,
            decisions, and rollout plan.
          </p>
        </div>
      ) : (
        <div style={{ padding: '16px 18px 24px' }}>
          <div
            className="prose"
            style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.7 }}
            dangerouslySetInnerHTML={{ __html: renderMarkdown(blueprintMarkdown) }}
          />
        </div>
      )}
    </div>
  )
}

function buildFallbackBlueprint(
  workspace: ConsultingWorkspace,
  architectureArtifact: ArchitectureArtifact | null,
): string {
  const lines: string[] = []
  const baselineName = architectureArtifact?.baseline.name || 'Working baseline'

  if (
    !workspace.recommendation &&
    !workspace.blueprint_markdown &&
    !architectureArtifact?.executive_summary &&
    workspace.decisions.length === 0 &&
    workspace.implementation_plan.length === 0
  ) {
    return ''
  }

  lines.push('## Technical Blueprint')
  lines.push('')

  if (workspace.recommendation) {
    lines.push('### Current Direction')
    lines.push(workspace.recommendation)
    lines.push('')
  }

  if (architectureArtifact?.executive_summary) {
    lines.push('### Executive Summary')
    lines.push(architectureArtifact.executive_summary)
    lines.push('')
  }

  lines.push('### Baseline')
  lines.push(`**${baselineName}**`)
  lines.push('')

  if (architectureArtifact?.baseline.layers.length) {
    for (const layer of architectureArtifact.baseline.layers) {
      const components = layer.component_labels.join(', ')
      lines.push(`- **${layer.label}**: ${components || 'TBD'}`)
      if (layer.purpose) lines.push(`  ${layer.purpose}`)
    }
    lines.push('')
  }

  if ((architectureArtifact?.customizations.length ?? 0) > 0) {
    lines.push('### Added For This Organization')
    lines.push('')
    for (const item of architectureArtifact?.customizations ?? []) {
      lines.push(`- **${item.title}** (${item.layer})`)
      lines.push(`  Reason: ${item.reason}`)
      if (item.tradeoff) lines.push(`  Tradeoff: ${item.tradeoff}`)
    }
    lines.push('')
  }

  if (workspace.facts.length > 0) {
    lines.push('### Confirmed Facts')
    lines.push(...workspace.facts.map((fact) => `- ${fact}`))
    lines.push('')
  }

  if (workspace.decisions.length > 0 || (architectureArtifact?.decisions.length ?? 0) > 0) {
    lines.push('### Key Decisions')
    lines.push(
      ...(architectureArtifact?.decisions.length
        ? architectureArtifact.decisions.map((item) =>
            `- **${item.decision}**${item.why ? `: ${item.why}` : ''}`,
          )
        : workspace.decisions.map((decision) => `- ${decision}`)),
    )
    lines.push('')
  }

  if (workspace.risks.length > 0 || (architectureArtifact?.risks.length ?? 0) > 0) {
    lines.push('### Risks And Tradeoffs')
    lines.push(
      ...(architectureArtifact?.risks.length
        ? architectureArtifact.risks.map((item) =>
            `- **${item.risk}**${item.mitigation ? `: ${item.mitigation}` : ''}`,
          )
        : workspace.risks.map((risk) => `- ${risk}`)),
    )
    lines.push('')
  }

  if (workspace.implementation_plan.length > 0 || (architectureArtifact?.rollout.length ?? 0) > 0) {
    lines.push('### Rollout Plan')
    lines.push(
      ...(architectureArtifact?.rollout.length
        ? architectureArtifact.rollout.map((phase, index) => `${index + 1}. **${phase.phase}**: ${phase.outcome}`)
        : workspace.implementation_plan.map((step, index) => `${index + 1}. ${step}`)),
    )
    lines.push('')
  }

  if (workspace.open_questions.length > 0) {
    lines.push('### Open Questions')
    lines.push(...workspace.open_questions.map((question) => `- ${question}`))
    lines.push('')
  }

  return lines.join('\n').trim()
}

function ArtifactButton({
  children,
  disabled,
  onClick,
}: {
  children: React.ReactNode
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: '7px 10px',
        borderRadius: 8,
        border: '1px solid var(--border)',
        background: disabled ? 'var(--bg-hover)' : 'var(--bg-elevated)',
        color: disabled ? 'var(--text-faint)' : 'var(--text)',
        fontSize: 12,
        fontWeight: 500,
        cursor: disabled ? 'default' : 'pointer',
      }}
    >
      {children}
    </button>
  )
}

function downloadTextFile(filename: string, text: string, mimeType: string) {
  const blob = new Blob([text], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
