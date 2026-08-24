'use client'

import { useEffect, useState } from 'react'
import { getUserId, getUserName, isAdmin as getIsAdmin, isAuthenticated, isGuestUser, isMidwayIdentity, logout, navigateToLogin, startInternalLogin } from '@/lib/auth'
import { listAllSessions, listModules } from '@/lib/api'
import { restoreSessionFromLocation } from '@/lib/session-actions'
import { useStore } from '@/store'

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const setUser  = useStore((s) => s.setUser)
  const setConvs = useStore((s) => s.setConversations)
  const setMods  = useStore((s) => s.setModules)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!isAuthenticated()) {
      if (isGuestUser()) {
        navigateToLogin('guest')
      } else {
        void startInternalLogin()
      }
      return
    }

    if (!isGuestUser() && !isMidwayIdentity()) {
      logout()
      return
    }

    const uid   = getUserId() ?? 'unknown'
    const uname = getUserName() ?? uid
    const admin = getIsAdmin()
    setUser(uid, uname, admin)

    let cancelled = false

    Promise.all([listAllSessions(), listModules()])
      .then(async ([convs, mods]) => {
        if (cancelled) return
        setConvs(convs)
        setMods(mods)
        await restoreSessionFromLocation(convs, { fallbackToLatest: true })
      })
      .catch((err) => {
        console.error('[ProtectedLayout] Failed to initialize workspace:', err)
      })
      .finally(() => {
        if (!cancelled) setReady(true)
      })

    return () => {
      cancelled = true
    }
  }, [setUser, setConvs, setMods])

  if (!ready) {
    return (
      <div style={{
        height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'var(--bg)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-muted)', fontSize: 13,
        }}>
          <span style={{
            width: 16, height: 16, borderRadius: '50%',
            border: '2px solid var(--accent)', borderTopColor: 'transparent',
            display: 'inline-block',
            animation: 'spin 0.7s linear infinite',
          }} />
          Loading workspace…
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  return <>{children}</>
}
