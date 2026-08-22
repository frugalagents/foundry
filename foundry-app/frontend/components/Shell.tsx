'use client'

import { useState, useCallback, useEffect } from 'react'
import Sidebar from './Sidebar'
import Chat from './Chat'
import TopBar from './TopBar'
import AdminSessionsView from './AdminSessionsView'
import WorkspaceTabs from './WorkspaceTabs'
import WorkspaceSetupDialog from './WorkspaceSetupDialog'
import { createCustomer, createSession, deleteCustomer } from '@/lib/api'
import { restoreSessionFromLocation } from '@/lib/session-actions'
import { useStore } from '@/store'

export default function Shell() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [chatOpen, setChatOpen] = useState(true)
  const [workspaceSetupOpen, setWorkspaceSetupOpen] = useState(false)
  const showAdminView = useStore((s) => s.showAdminView)

  useEffect(() => {
    const restoreFromHistory = () => {
      const conversations = useStore.getState().conversations
      void restoreSessionFromLocation(conversations).catch((err) => {
        console.error('[Shell] Failed to restore session from browser history:', err)
      })
    }

    window.addEventListener('popstate', restoreFromHistory)
    return () => window.removeEventListener('popstate', restoreFromHistory)
  }, [])

  const handleNewChat = useCallback(() => {
    setWorkspaceSetupOpen(true)
  }, [])

  const handleCreateWorkspace = useCallback(async (project: string, purpose: string) => {
    const customer = await createCustomer(project)
    let session
    try {
      session = await createSession(customer.customer_id, {
        title: project,
        description: purpose,
      })
    } catch (error) {
      await deleteCustomer(customer.customer_id).catch((cleanupError) => {
        console.error('[Shell] Failed to clean up incomplete workspace:', cleanupError)
      })
      throw error
    }

    const store = useStore.getState()
    store.clearMessages()
    store.clearWorkspace()
    store.hideCanvas()
    store.setShowAdminView(false)
    store.setActiveSession(customer.customer_id, session.session_id)
    store.prependConversation({ customer, session })
    setChatOpen(true)
    setWorkspaceSetupOpen(false)
    window.history.pushState(null, '', `/sessions/${session.session_id}`)
  }, [])

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg)' }}>
      <TopBar />

      <div style={{ flex: 1, minHeight: 0, display: 'flex', overflow: 'hidden', position: 'relative' }}>
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

        <button
          onClick={() => setChatOpen((v) => !v)}
          title={chatOpen ? 'Collapse chat' : 'Expand chat'}
          style={{
            position: 'absolute',
            top: 12,
            right: chatOpen ? 'calc(clamp(280px, 22vw, 340px) + 8px)' : 8,
            zIndex: 50,
            width: 22,
            height: 22,
            borderRadius: 6,
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            color: 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            transition: 'right 200ms ease',
          }}
        >
          <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
            <polyline points={chatOpen ? '9 18 15 12 9 6' : '15 18 9 12 15 6'} />
          </svg>
        </button>

        {showAdminView ? (
          <AdminSessionsView />
        ) : (
          <div style={{
            flex: 1,
            minWidth: 0,
            minHeight: 0,
            display: 'grid',
            gridTemplateColumns: chatOpen ? 'minmax(0, 1fr) clamp(280px, 22vw, 340px)' : 'minmax(0, 1fr)',
            overflow: 'hidden',
          }}>
            <main style={{
              flex: 1,
              minWidth: 0,
              minHeight: 0,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              background: 'linear-gradient(180deg, #f4efe8 0%, #efe7da 100%)',
            }}>
              <div style={{
                padding: '16px 18px 18px',
                display: 'flex',
                flexDirection: 'column',
                gap: 16,
                flex: 1,
                minHeight: 0,
              }}>
                <div style={{
                  minHeight: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  overflow: 'hidden',
                  borderRadius: 22,
                  border: '1px solid var(--border)',
                  background: 'rgba(255,253,249,0.92)',
                  boxShadow: 'var(--shadow)',
                }}>
                  <WorkspaceTabs />
                </div>
              </div>
            </main>

            {chatOpen ? (
            <aside style={{
              width: '100%',
              minWidth: 0,
              minHeight: 0,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              background: 'rgba(255,253,249,0.9)',
              borderLeft: '1px solid var(--border)',
            }}>
              <div style={{
                padding: '14px 16px 12px',
                borderBottom: '1px solid var(--border)',
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
                background: 'rgba(255,253,249,0.98)',
              }}>
                <span style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: 'var(--text-muted)',
                }}>
                  Advisor Chat
                </span>
                <p style={{
                  fontSize: 12.5,
                  lineHeight: 1.55,
                  color: 'var(--text-faint)',
                }}>
                  Use chat to refine the brief, answer blockers, and pressure-test the recommendation.
                </p>
              </div>
              <div style={{ flex: 1, minHeight: 0 }}>
                <Chat onStartWorkspace={handleNewChat} />
              </div>
            </aside>
            ) : null}
          </div>
        )}
      </div>

      <WorkspaceSetupDialog
        open={workspaceSetupOpen}
        onCancel={() => setWorkspaceSetupOpen(false)}
        onCreate={handleCreateWorkspace}
      />
    </div>
  )
}
