'use client'

import { useEffect, useMemo, useState } from 'react'
import TopBar from './TopBar'
import WorkspaceTabs from './WorkspaceTabs'
import {
  auditReviewScenario,
  buildReviewConversation,
  getReviewScenario,
  measureReviewScenario,
  reviewScenarios,
  type ReviewAuditItem,
  type ReviewScenario,
} from '@/lib/review-audit'
import { analyzeAgentMessage } from '@/lib/message-analysis'
import { renderMarkdown } from '@/lib/render-markdown'
import { useStore } from '@/store'

export default function ReviewWorkbench() {
  const [selectedId, setSelectedId] = useState(() => getReviewScenario(null).id)
  const scenario = useMemo(() => getReviewScenario(selectedId), [selectedId])
  const metrics = useMemo(() => measureReviewScenario(scenario), [scenario])
  const auditItems = useMemo(() => auditReviewScenario(scenario), [scenario])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const scenarioId = new URLSearchParams(window.location.search).get('scenario')
    if (!scenarioId) return
    const nextId = getReviewScenario(scenarioId).id
    if (nextId !== selectedId) setSelectedId(nextId)
  }, [selectedId])

  useEffect(() => {
    const row = buildReviewConversation(scenario)
    useStore.setState({
      userId: 'review-viewer',
      userName: 'Review Agent',
      isAdmin: false,
      activeCustomerId: null,
      activeSessionId: scenario.session.session_id,
      activeModule: scenario.session.module_id ?? 'coding-agent',
      messages: scenario.transcript,
      workspace: scenario.workspace,
      architectureArtifact: scenario.architectureArtifact,
      canvasVisible: scenario.canvas.nodes.length > 0,
      canvasNodes: scenario.canvas.nodes,
      canvasEdges: scenario.canvas.edges,
      baselineNodeIds: scenario.canvas.baselineNodeIds,
      conversations: [row],
      modules: [],
      streaming: false,
      showAdminView: false,
    })
  }, [scenario])

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <div>
          <span style={eyebrowStyle}>Review Agent</span>
          <h1 style={titleStyle}>Vision, UI, and workspace audit</h1>
          <p style={subtitleStyle}>
            This route runs the product in a seeded, API-free review mode so you can inspect the intended experience,
            the current gaps, and the artifact quality without logging in.
          </p>
        </div>
        <div style={metricRowStyle}>
          <MetricPill label="Stage" value={metrics.stage} />
          <MetricPill label="Open items" value={String(auditItems.length)} tone={auditItems.length > 0 ? 'warning' : 'success'} />
          <MetricPill label="Confidence" value={metrics.confidence || 'unset'} tone={metrics.confidence ? 'success' : 'neutral'} />
        </div>
      </div>

      <div style={scenarioRailStyle}>
        {reviewScenarios.map((item) => {
          const itemAudit = auditReviewScenario(item)
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => selectScenario(item.id, setSelectedId)}
              style={{
                ...scenarioButtonStyle,
                borderColor: item.id === scenario.id ? 'var(--accent)' : 'var(--border)',
                background: item.id === scenario.id ? 'rgba(180, 83, 9, 0.08)' : 'var(--bg-elevated)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                  <strong style={{ fontSize: 13, color: 'var(--text)' }}>{item.name}</strong>
                  <span style={gateBadgeStyle(item.strict_gate !== false)}>
                    {item.strict_gate !== false ? 'gate' : 'review'}
                  </span>
                </div>
                <span style={scenarioBadgeStyle(itemAudit)}>{itemAudit.length}</span>
              </div>
              <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.55, color: 'var(--text-muted)' }}>
                {item.summary}
              </p>
            </button>
          )
        })}
      </div>

      <div style={mainGridStyle}>
        <aside style={sidebarStyle}>
          <section style={cardStyle}>
            <span style={cardLabelStyle}>Product Vision</span>
            <p style={cardBodyStyle}>{scenario.vision}</p>
          </section>

          <section style={cardStyle}>
            <span style={cardLabelStyle}>Success Criteria</span>
            <ul style={listStyle}>
              {scenario.success_criteria.map((criterion) => (
                <li key={criterion}>{criterion}</li>
              ))}
            </ul>
          </section>

          <section style={cardStyle}>
            <span style={cardLabelStyle}>Open Items</span>
            {auditItems.length === 0 ? (
              <p style={cardBodyStyle}>No audit findings for this scenario.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {auditItems.map((item, index) => (
                  <AuditItemCard key={`${item.title}-${index}`} item={item} />
                ))}
              </div>
            )}
          </section>

          <section style={cardStyle}>
            <span style={cardLabelStyle}>Checks</span>
            <ul style={listStyle}>
              <li>Workspace facts: {scenario.workspace.facts.length}</li>
              <li>Decisions: {metrics.decisionCount}</li>
              <li>Risks: {metrics.riskCount}</li>
              <li>Implementation steps: {metrics.implementationCount}</li>
              <li>Assumption cards: {metrics.assumptionCount}</li>
              <li>Architecture rendered: {metrics.hasArchitecture ? 'yes' : 'no'}</li>
              <li>Blueprint mode: {metrics.blueprintMode}</li>
            </ul>
          </section>
        </aside>

        <main style={previewColumnStyle}>
          <div style={previewShellStyle}>
            <TopBar />
            <div style={previewBodyStyle}>
              <div style={workspaceFrameStyle}>
                <WorkspaceTabs key={scenario.id} />
              </div>
              <ReviewTranscript scenario={scenario} />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

function selectScenario(id: string, setSelectedId: (id: string) => void) {
  setSelectedId(id)
  if (typeof window === 'undefined') return
  const url = new URL(window.location.href)
  url.searchParams.set('scenario', id)
  window.history.replaceState(null, '', url.toString())
}

function ReviewTranscript({ scenario }: { scenario: ReviewScenario }) {
  return (
    <aside style={transcriptShellStyle}>
      <div style={transcriptHeaderStyle}>
        <span style={cardLabelStyle}>Read-Only Chat Simulation</span>
        <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.5, color: 'var(--text-muted)' }}>
          The chat is intentionally frozen here. The goal is to inspect the artifact flow and message discipline.
        </p>
      </div>
      <div style={transcriptBodyStyle}>
        {scenario.transcript.map((message) => (
          <TranscriptBubble key={message.id} role={message.role} content={message.content} />
        ))}
      </div>
      <div style={composerStyle}>
        <div style={composerLabelStyle}>Composer disabled in review mode</div>
        <div style={composerInputStyle}>
          This preview is for UI and artifact review. Use the live app for agent interaction.
        </div>
      </div>
    </aside>
  )
}

function TranscriptBubble({ role, content }: { role: 'user' | 'agent'; content: string }) {
  const analysis = role === 'agent' ? analyzeAgentMessage(content) : { type: 'observation', questions: [] }
  const isQuestioning = role === 'agent' && analysis.type !== 'observation'

  return (
    <div style={{
      display: 'flex',
      justifyContent: role === 'user' ? 'flex-end' : 'flex-start',
    }}>
      <div style={{
        maxWidth: '85%',
        padding: role === 'user' ? '10px 14px' : '12px 14px',
        borderRadius: role === 'user' ? '16px 16px 6px 16px' : '6px 16px 16px 16px',
        background: role === 'user'
          ? 'var(--accent)'
          : isQuestioning
            ? 'rgba(245,158,11,0.08)'
            : 'var(--bg-elevated)',
        border: role === 'user'
          ? 'none'
          : isQuestioning
            ? '1px solid rgba(245,158,11,0.3)'
            : '1px solid var(--border)',
        color: role === 'user' ? '#fff' : 'var(--text)',
        lineHeight: 1.65,
        fontSize: 13.5,
      }}>
        {role === 'agent' && isQuestioning ? (
          <div style={{
            marginBottom: 8,
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'var(--amber)',
          }}>
            Needs user input
          </div>
        ) : null}
        {role === 'user' ? (
          <span style={{ whiteSpace: 'pre-wrap' }}>{content}</span>
        ) : (
          <div className="prose" dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }} />
        )}
      </div>
    </div>
  )
}

function AuditItemCard({ item }: { item: ReviewAuditItem }) {
  return (
    <div style={{
      border: '1px solid var(--border)',
      borderLeft: `4px solid ${severityColor(item.severity)}`,
      borderRadius: 12,
      padding: '12px 12px 12px 14px',
      background: 'var(--bg-elevated)',
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <strong style={{ fontSize: 12.5, color: 'var(--text)' }}>{item.title}</strong>
        <span style={{
          fontSize: 10,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: severityColor(item.severity),
          fontWeight: 700,
        }}>
          {componentLabel(item.component)} · {item.severity}
        </span>
      </div>
      <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.55, color: 'var(--text-muted)' }}>{item.detail}</p>
      <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.55, color: 'var(--text)' }}>{item.fix}</p>
    </div>
  )
}

function componentLabel(component: ReviewAuditItem['component']) {
  switch (component) {
    case 'brief':
      return 'brief'
    case 'questions':
      return 'questions'
    case 'assumptions':
      return 'assumptions'
    case 'blueprint':
      return 'blueprint'
    case 'architecture':
      return 'architecture'
    case 'transcript':
      return 'transcript'
    default:
      return 'workspace'
  }
}

function MetricPill({
  label,
  value,
  tone = 'neutral',
}: {
  label: string
  value: string
  tone?: 'neutral' | 'warning' | 'success'
}) {
  const color = tone === 'warning' ? 'var(--amber)' : tone === 'success' ? 'var(--green)' : 'var(--text-muted)'
  const background = tone === 'warning'
    ? 'rgba(245,158,11,0.08)'
    : tone === 'success'
      ? 'rgba(34,197,94,0.08)'
      : 'var(--bg-elevated)'

  return (
    <div style={{
      border: '1px solid var(--border)',
      borderRadius: 999,
      padding: '8px 12px',
      background,
      display: 'flex',
      alignItems: 'center',
      gap: 8,
    }}>
      <span style={{ fontSize: 11, color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {label}
      </span>
      <strong style={{ fontSize: 12.5, color }}>{value}</strong>
    </div>
  )
}

function severityColor(severity: ReviewAuditItem['severity']) {
  switch (severity) {
    case 'critical':
      return '#b91c1c'
    case 'warning':
      return '#b45309'
    default:
      return '#475569'
  }
}

function scenarioBadgeStyle(items: ReviewAuditItem[]) {
  const hasCritical = items.some((item) => item.severity === 'critical')
  const hasWarning = items.some((item) => item.severity === 'warning')
  return {
    minWidth: 24,
    height: 24,
    borderRadius: 999,
    padding: '0 8px',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 11,
    fontWeight: 700,
    color: hasCritical ? '#fff' : hasWarning ? 'var(--amber)' : 'var(--text-muted)',
    background: hasCritical ? '#b91c1c' : hasWarning ? 'rgba(245,158,11,0.12)' : 'var(--bg)',
    border: '1px solid var(--border)',
  } as const
}

function gateBadgeStyle(strictGate: boolean) {
  return {
    borderRadius: 999,
    padding: '3px 8px',
    border: '1px solid var(--border)',
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    color: strictGate ? 'var(--green)' : 'var(--text-muted)',
    background: strictGate ? 'rgba(34,197,94,0.08)' : 'var(--bg)',
    flexShrink: 0,
  } as const
}

const pageStyle = {
  minHeight: '100vh',
  background: 'linear-gradient(180deg, #f4efe8 0%, #efe7da 100%)',
  color: 'var(--text)',
  padding: '24px',
  display: 'flex',
  flexDirection: 'column',
  gap: 18,
} as const

const headerStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 18,
  flexWrap: 'wrap',
} as const

const eyebrowStyle = {
  display: 'inline-block',
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  marginBottom: 8,
} as const

const titleStyle = {
  margin: 0,
  fontSize: 30,
  letterSpacing: '-0.03em',
} as const

const subtitleStyle = {
  margin: '8px 0 0',
  maxWidth: 760,
  fontSize: 14,
  lineHeight: 1.65,
  color: 'var(--text-muted)',
} as const

const metricRowStyle = {
  display: 'flex',
  gap: 10,
  flexWrap: 'wrap',
} as const

const scenarioRailStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 12,
} as const

const scenarioButtonStyle = {
  textAlign: 'left',
  padding: '14px',
  borderRadius: 14,
  border: '1px solid var(--border)',
  cursor: 'pointer',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  boxShadow: 'var(--shadow)',
} as const

const mainGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'minmax(280px, 360px) minmax(0, 1fr)',
  gap: 18,
  alignItems: 'start',
} as const

const sidebarStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
} as const

const previewColumnStyle = {
  minWidth: 0,
} as const

const cardStyle = {
  border: '1px solid var(--border)',
  borderRadius: 18,
  background: 'rgba(255,253,249,0.94)',
  boxShadow: 'var(--shadow)',
  padding: 16,
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
} as const

const cardLabelStyle = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
} as const

const cardBodyStyle = {
  margin: 0,
  fontSize: 13,
  lineHeight: 1.65,
  color: 'var(--text)',
} as const

const listStyle = {
  margin: 0,
  paddingLeft: 18,
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  fontSize: 12.5,
  lineHeight: 1.55,
  color: 'var(--text)',
} as const

const previewShellStyle = {
  border: '1px solid var(--border)',
  borderRadius: 24,
  overflow: 'hidden',
  background: 'rgba(255,253,249,0.95)',
  boxShadow: 'var(--shadow)',
} as const

const previewBodyStyle = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) 360px',
  minHeight: 780,
} as const

const workspaceFrameStyle = {
  minWidth: 0,
  borderRight: '1px solid var(--border)',
  background: 'linear-gradient(180deg, #f4efe8 0%, #efe7da 100%)',
  padding: 16,
} as const

const transcriptShellStyle = {
  minWidth: 0,
  display: 'flex',
  flexDirection: 'column',
  background: 'rgba(255,253,249,0.9)',
} as const

const transcriptHeaderStyle = {
  padding: '16px 16px 12px',
  borderBottom: '1px solid var(--border)',
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
} as const

const transcriptBodyStyle = {
  flex: 1,
  minHeight: 0,
  overflowY: 'auto',
  padding: 16,
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
} as const

const composerStyle = {
  borderTop: '1px solid var(--border)',
  padding: 16,
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  background: 'rgba(255,253,249,0.98)',
} as const

const composerLabelStyle = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
} as const

const composerInputStyle = {
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: '12px 14px',
  fontSize: 12.5,
  lineHeight: 1.55,
  color: 'var(--text-faint)',
  background: 'var(--bg)',
} as const
