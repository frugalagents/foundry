'use client'

import { useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import Sidebar from './Sidebar'
import Chat from './Chat'
import TopBar from './TopBar'
import AdminSessionsView from './AdminSessionsView'
import { useStore } from '@/store'

const Canvas = dynamic(() => import('./Canvas'), { ssr: false })

export default function Shell() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const showAdminView = useStore((s) => s.showAdminView)

  const handleNewChat = useCallback(() => {}, [])

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

            {/* Canvas panel — always 50%, shows placeholder when empty */}
            <Canvas />
          </>
        )}
      </div>
    </div>
  )
}
