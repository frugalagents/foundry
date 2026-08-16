'use client'

import { useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import Sidebar from './Sidebar'
import Chat from './Chat'
import { useStore } from '@/store'

// Dynamically import Canvas (ReactFlow) to avoid SSR issues
const Canvas = dynamic(() => import('./Canvas'), { ssr: false })

export default function Shell() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const canvasVisible = useStore((s) => s.canvasVisible || s.canvasNodes.length > 0)

  const handleNewChat = useCallback(() => {
    // clearMessages and clearActiveSession are called inside Sidebar
    // Nothing extra needed here — just keep Shell re-renderable
  }, [])

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      overflow: 'hidden',
      background: 'var(--bg)',
    }}>
      {/* Sidebar */}
      {sidebarOpen && (
        <Sidebar onNewChat={handleNewChat} />
      )}

      {/* Toggle sidebar button */}
      <button
        onClick={() => setSidebarOpen((v) => !v)}
        title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        style={{
          position: 'absolute',
          top: 14,
          left: sidebarOpen ? 248 : 8,
          zIndex: 50,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: 6,
          width: 24, height: 24,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer',
          color: 'var(--text-muted)',
          transition: 'left 200ms ease',
        }}
      >
        {sidebarOpen ? (
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        ) : (
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        )}
      </button>

      {/* Chat panel */}
      <div style={{
        flex: canvasVisible ? '0 0 55%' : '1',
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        transition: 'flex 300ms ease',
      }}>
        <Chat />
      </div>

      {/* Canvas panel */}
      {canvasVisible && (
        <div
          className="animate-slide-in"
          style={{
            flex: '0 0 45%',
            borderLeft: '1px solid var(--border)',
            overflow: 'hidden',
          }}
        >
          <Canvas />
        </div>
      )}
    </div>
  )
}
