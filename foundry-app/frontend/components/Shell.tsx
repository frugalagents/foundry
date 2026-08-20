'use client'

import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import dynamic from 'next/dynamic'
import Sidebar from './Sidebar'
import Chat from './Chat'
import TopBar from './TopBar'
import AdminSessionsView from './AdminSessionsView'
import WorkspacePanelStack from './WorkspacePanelStack'
import { useStore } from '@/store'
import { extractOpenQuestions, normalizeWorkspace } from '@/lib/message-analysis'

const Canvas = dynamic(() => import('./Canvas'), { ssr: false })

export default function Shell() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [rightTab, setRightTab] = useState<'workspace' | 'architecture'>('workspace')
  const showAdminView = useStore((s) => s.showAdminView)
  const workspace = useStore((s) => s.workspace)
  const messages = useStore((s) => s.messages)
  const activeSessionId = useStore((s) => s.activeSessionId)
  const hasCanvas = useStore((s) => s.canvasNodes.length > 0)

  const handleNewChat = useCallback(() => {}, [])
  const workspaceView = useMemo(() => normalizeWorkspace(workspace), [workspace])
  const derivedOpenQuestions = useMemo(() => {
    if (workspaceView.open_questions.length > 0) return workspaceView.open_questions
    return extractOpenQuestions(messages).map((q) => q.text)
  }, [messages, workspaceView])
  const prevQuestionCountRef = useRef(derivedOpenQuestions.length)
  const prevHasCanvasRef = useRef(hasCanvas)

  useEffect(() => {
    if (!activeSessionId) {
      setRightTab('workspace')
    }
  }, [activeSessionId])

  useEffect(() => {
    if (!prevHasCanvasRef.current && hasCanvas) {
      setRightTab('architecture')
    }
    prevHasCanvasRef.current = hasCanvas
  }, [hasCanvas])

  useEffect(() => {
    if (derivedOpenQuestions.length > prevQuestionCountRef.current) {
      setRightTab('workspace')
    }
    prevQuestionCountRef.current = derivedOpenQuestions.length
  }, [derivedOpenQuestions.length])

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg)' }}>
      <TopBar />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        {sidebarOpen && <Sidebar onNewChat={handleNewChat} />}

        <button
          onClick={() => setSidebarOpen((v) => !v)}
          title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          style={{
            position: 'absolute', top: 12,
            left: sidebarOpen ? 248 : 8,
            zIndex: 50, width: 22, height: 22, borderRadius: 6,
            background: 'var(--bg-elevated)', border: '1px solid var(--border)',
            color: 'var(--text-muted)', display: 'flex', alignItems: 'center',
            justifyContent: 'center', cursor: 'pointer', transition: 'left 200ms ease',
          }}
        >
          <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
            <polyline points={sidebarOpen ? '15 18 9 12 15 6' : '9 18 15 12 9 6'} />
          </svg>
        </button>

        {showAdminView ? (
          <AdminSessionsView />
        ) : (
          <>
            {/* Chat panel — always 50% */}
            <div style={{ flex: '1 1 50%', minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <Chat />
            </div>

            <div style={{ width: 1, background: 'var(--border)', flexShrink: 0 }} />

            <div style={{ flex: '1 1 50%', minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{
                minHeight: 48,
                padding: '10px 16px',
                borderBottom: '1px solid var(--border)',
                background: 'var(--bg)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 10,
                flexWrap: 'wrap',
                flexShrink: 0,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{
                    fontSize: 11,
                    fontWeight: 600,
                    letterSpacing: '0.06em',
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                  }}>
                    Session State
                  </span>
                  {workspaceView.stage && (
                    <span style={summaryChip(workspaceView.stage === 'blueprint' ? 'var(--green)' : 'var(--accent)')}>
                      {workspaceView.stage}
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={summaryChip(derivedOpenQuestions.length > 0 ? 'var(--amber)' : 'var(--text-faint)')}>
                    {derivedOpenQuestions.length} open question{derivedOpenQuestions.length === 1 ? '' : 's'}
                  </span>
                  <span style={summaryChip(workspaceView.risks.length > 0 ? 'var(--amber)' : 'var(--text-faint)')}>
                    {workspaceView.risks.length} risk{workspaceView.risks.length === 1 ? '' : 's'}
                  </span>
                  <span style={summaryChip(workspaceView.decisions.length > 0 ? 'var(--accent)' : 'var(--text-faint)')}>
                    {workspaceView.decisions.length} decision{workspaceView.decisions.length === 1 ? '' : 's'}
                  </span>
                </div>
              </div>

              <div style={{
                padding: '8px 16px',
                borderBottom: '1px solid var(--border)',
                background: 'var(--bg)',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                flexShrink: 0,
              }}>
                <button
                  onClick={() => setRightTab('workspace')}
                  style={tabButton(rightTab === 'workspace')}
                >
                  Workspace
                </button>
                <button
                  onClick={() => setRightTab('architecture')}
                  style={tabButton(rightTab === 'architecture')}
                >
                  Architecture
                </button>
              </div>

              <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
                {rightTab === 'workspace' ? <WorkspacePanelStack /> : <Canvas />}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function tabButton(active: boolean): React.CSSProperties {
  return {
    padding: '7px 12px',
    borderRadius: 8,
    border: `1px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
    background: active ? 'var(--accent-dim)' : 'var(--bg-elevated)',
    color: active ? 'var(--accent-strong)' : 'var(--text-muted)',
    fontSize: 12.5,
    fontWeight: 600,
    cursor: 'pointer',
  }
}

function summaryChip(color: string): React.CSSProperties {
  return {
    padding: '4px 8px',
    borderRadius: 999,
    border: '1px solid var(--border)',
    background: 'var(--bg-elevated)',
    color,
    fontSize: 11,
    lineHeight: 1.2,
    textTransform: 'capitalize',
  }
}
