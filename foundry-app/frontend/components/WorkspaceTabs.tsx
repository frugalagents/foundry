'use client'

import { useEffect, useMemo, useState } from 'react'
import { useStore } from '@/store'
import { buildAssumptionCards } from '@/lib/assumptions'
import { normalizeWorkspace } from '@/lib/message-analysis'
import AssumptionsPanel from './AssumptionsPanel'
import BlueprintPanel from './BlueprintPanel'
import Canvas from './Canvas'
import OpenQuestionsPanel from './OpenQuestionsPanel'

type WorkspaceTab = 'assumptions' | 'blueprint' | 'architecture' | 'questions'

export default function WorkspaceTabs() {
  const workspace = useStore((s) => s.workspace)
  const architectureArtifact = useStore((s) => s.architectureArtifact)
  const canvasNodes = useStore((s) => s.canvasNodes)
  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])
  const blueprintReady =
    !!view.blueprint_markdown?.trim() ||
    !!view.recommendation ||
    view.decisions.length > 0 ||
    view.implementation_plan.length > 0
  const assumptions = useMemo(
    () => buildAssumptionCards(view, architectureArtifact, canvasNodes),
    [architectureArtifact, canvasNodes, view],
  )
  const questionCount = view.open_questions.length
  const architectureReady = canvasNodes.length > 0 || !!architectureArtifact
  const baselineReady = architectureReady
  const preferredReadyTab: WorkspaceTab = blueprintReady ? 'blueprint' : 'architecture'
  const [activeTab, setActiveTab] = useState<WorkspaceTab>(baselineReady ? preferredReadyTab : 'questions')

  useEffect(() => {
    if (!baselineReady) {
      if (activeTab !== 'questions' && activeTab !== 'assumptions') {
        setActiveTab('questions')
      }
      return
    }

    if (activeTab === 'questions') {
      setActiveTab(preferredReadyTab)
    }
  }, [activeTab, baselineReady, preferredReadyTab])

  return (
    <div style={{
      flex: 1,
      minHeight: 0,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      background: 'var(--bg)',
    }}>
      <div style={{
        padding: '12px 16px 10px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
          }}>
            Workspace
          </span>
          <p style={{
            fontSize: 12,
            color: 'var(--text-faint)',
            lineHeight: 1.55,
          }}>
            Blueprint and architecture artifacts live here instead of being buried in chat.
          </p>
        </div>

        <div style={{
          display: 'flex',
          gap: 4,
          padding: 3,
          borderRadius: 10,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          width: 'fit-content',
          maxWidth: '100%',
          flexWrap: 'wrap',
        }}>
          <WorkspaceTabButton
            active={activeTab === 'assumptions'}
            onClick={() => setActiveTab('assumptions')}
            badge={baselineReady ? String(assumptions.length) : 'preview'}
          >
            Assumptions
          </WorkspaceTabButton>
          <WorkspaceTabButton
            active={activeTab === 'blueprint'}
            onClick={() => setActiveTab('blueprint')}
            badge={blueprintReady ? undefined : 'pending'}
          >
            Blueprint
          </WorkspaceTabButton>
          <WorkspaceTabButton
            active={activeTab === 'architecture'}
            onClick={() => setActiveTab('architecture')}
            badge={architectureReady ? undefined : 'empty'}
          >
            Architecture
          </WorkspaceTabButton>
          <WorkspaceTabButton
            active={activeTab === 'questions'}
            onClick={() => setActiveTab('questions')}
            badge={questionCount > 0 ? String(questionCount) : undefined}
            tone={questionCount > 0 ? 'warning' : 'neutral'}
          >
            Questions
          </WorkspaceTabButton>
        </div>
      </div>

        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {activeTab === 'assumptions' ? (
          <AssumptionsPanel baselineReady={baselineReady} />
        ) : activeTab === 'blueprint' ? (
          <BlueprintPanel />
        ) : activeTab === 'architecture' ? (
          <Canvas />
        ) : (
          <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', background: 'var(--bg)' }}>
            <OpenQuestionsPanel />
          </div>
        )}
      </div>
    </div>
  )
}

function WorkspaceTabButton({
  active,
  badge,
  children,
  onClick,
  tone = 'neutral',
}: {
  active: boolean
  badge?: string
  children: React.ReactNode
  onClick: () => void
  tone?: 'neutral' | 'warning'
}) {
  const badgeStyle = tone === 'warning'
    ? {
        background: 'rgba(245,158,11,0.12)',
        border: '1px solid rgba(245,158,11,0.24)',
        color: 'var(--amber)',
      }
    : {
        background: 'var(--bg)',
        border: '1px solid var(--border)',
        color: 'var(--text-faint)',
      }

  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 12px',
        borderRadius: 8,
        border: 'none',
        background: active ? 'var(--bg)' : 'transparent',
        color: active ? 'var(--text)' : 'var(--text-muted)',
        fontSize: 12.5,
        fontWeight: active ? 600 : 500,
        cursor: 'pointer',
      }}
    >
      <span>{children}</span>
      {badge && (
        <span style={{
          ...badgeStyle,
          minWidth: 18,
          height: 18,
          padding: '0 6px',
          borderRadius: 999,
          fontSize: 10,
          fontWeight: 700,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          textTransform: 'uppercase',
        }}>
          {badge}
        </span>
      )}
    </button>
  )
}
