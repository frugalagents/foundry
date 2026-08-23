'use client'

import { useEffect, useMemo, useState } from 'react'
import { Download } from 'lucide-react'
import { useStore } from '@/store'
import { buildAssumptionCards } from '@/lib/assumptions'
import { normalizeWorkspace } from '@/lib/message-analysis'
import { hasAdvisoryCaseContent } from '@/lib/advisory-case'
import { downloadSessionBrief, hasOutputPackContent, hasSessionExportContent } from '@/lib/session-export'
import { normalizeAdvisoryStage, preferredWorkspaceTab, type AdvisoryWorkspaceTab } from '@/lib/workflow'
import AdvisoryBrief from './AdvisoryBrief'
import AssumptionsPanel from './AssumptionsPanel'
import ArchitectureBoard from './ArchitectureBoard'
import BlueprintPanel from './BlueprintPanel'
import OpenQuestionsPanel from './OpenQuestionsPanel'

type WorkspaceTab = 'brief' | AdvisoryWorkspaceTab

export default function WorkspaceTabs() {
  const activeSessionId = useStore((s) => s.activeSessionId)
  const conversations = useStore((s) => s.conversations)
  const messages = useStore((s) => s.messages)
  const workspace = useStore((s) => s.workspace)
  const architectureArtifact = useStore((s) => s.architectureArtifact)
  const canvasNodes = useStore((s) => s.canvasNodes)
  const canvasEdges = useStore((s) => s.canvasEdges)
  const baselineNodeIds = useStore((s) => s.baselineNodeIds)
  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])
  const advisoryCase = hasAdvisoryCaseContent(view.advisory_case) ? view.advisory_case : null
  const blueprintReady =
    !!view.blueprint_markdown?.trim() ||
    Boolean(advisoryCase?.output_pack && hasOutputPackContent(advisoryCase.output_pack))
  const assumptions = useMemo(
    () => buildAssumptionCards(view, architectureArtifact, canvasNodes),
    [architectureArtifact, canvasNodes, view],
  )
  const questionCount = view.open_questions.length
  const stage = normalizeAdvisoryStage(view.stage)
  const isDiscovery = stage === 'discovery'
  const architectureReady = !isDiscovery && (canvasNodes.length > 0 || !!architectureArtifact)
  const baselineReady = architectureReady
  const preferredTab = preferredWorkspaceTab(stage, {
    questionCount,
    blueprintReady,
    architectureReady,
  })
  const sessionTitle = useMemo(
    () => conversations.find((item) => item.session.session_id === activeSessionId)?.session.title ?? null,
    [activeSessionId, conversations],
  )
  const canExport = useMemo(
    () => hasSessionExportContent({
      activeSessionId,
      sessionTitle,
      workspace,
      architectureArtifact,
      canvasNodes,
      canvasEdges,
      baselineNodeIds,
      messages,
    }),
    [
      activeSessionId,
      architectureArtifact,
      baselineNodeIds,
      canvasEdges,
      canvasNodes,
      messages,
      sessionTitle,
      workspace,
    ],
  )
  const showExport = blueprintReady && canExport
  const [exporting, setExporting] = useState(false)
  const [activeTab, setActiveTab] = useState<WorkspaceTab>(
    questionCount > 0 && isDiscovery ? 'questions' : 'brief',
  )

  useEffect(() => {
    if (!baselineReady) {
      if (activeTab === 'blueprint' || activeTab === 'architecture') {
        setActiveTab(questionCount > 0 && isDiscovery ? 'questions' : 'brief')
      }
      return
    }

    if (questionCount > 0 && isDiscovery && activeTab !== 'questions') {
      setActiveTab('questions')
      return
    }

    if (activeTab === 'questions' && questionCount === 0) {
      setActiveTab('brief')
    }
  }, [activeTab, baselineReady, isDiscovery, preferredTab, questionCount])

  async function handleDownloadBrief() {
    if (!canExport || exporting) return
    try {
      setExporting(true)
      await downloadSessionBrief({
        activeSessionId,
        sessionTitle,
        workspace,
        architectureArtifact,
        canvasNodes,
        canvasEdges,
        baselineNodeIds,
        messages,
      })
    } catch (err) {
      console.error('Failed to export session brief', err)
    } finally {
      setExporting(false)
    }
  }

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
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 12,
          flexWrap: 'wrap',
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

          {showExport ? (
            <button
              onClick={handleDownloadBrief}
              disabled={exporting}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 12px',
                borderRadius: 10,
                border: '1px solid var(--border)',
                background: exporting ? 'var(--bg-hover)' : 'var(--bg-elevated)',
                color: exporting ? 'var(--text-faint)' : 'var(--text)',
                fontSize: 12.5,
                fontWeight: 600,
                cursor: exporting ? 'default' : 'pointer',
              }}
            >
              <Download size={14} />
              {exporting ? 'Preparing…' : 'Download Brief'}
            </button>
          ) : null}
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
            active={activeTab === 'brief'}
            onClick={() => setActiveTab('brief')}
          >
            Brief
          </WorkspaceTabButton>
          <WorkspaceTabButton
            active={activeTab === 'questions'}
            onClick={() => setActiveTab('questions')}
            badge={questionCount > 0 ? String(questionCount) : undefined}
            tone={questionCount > 0 ? 'warning' : 'neutral'}
          >
            Questions
          </WorkspaceTabButton>
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
        </div>
      </div>

        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {activeTab === 'brief' ? (
          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', padding: 16, background: 'linear-gradient(180deg, #f4efe8 0%, #efe7da 100%)' }}>
            <AdvisoryBrief />
          </div>
        ) : activeTab === 'assumptions' ? (
          <AssumptionsPanel baselineReady={baselineReady} />
        ) : activeTab === 'blueprint' ? (
          <BlueprintPanel />
        ) : activeTab === 'architecture' ? (
          <ArchitectureBoard />
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
