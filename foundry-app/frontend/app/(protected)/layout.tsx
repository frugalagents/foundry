'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated, getUserId, getUserName, isAdmin as getIsAdmin } from '@/lib/auth'
import { listAllSessions, listModules } from '@/lib/api'
import { useStore } from '@/store'

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const router   = useRouter()
  const setUser  = useStore((s) => s.setUser)
  const setConvs = useStore((s) => s.setConversations)
  const setMods  = useStore((s) => s.setModules)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login')
      return
    }

    const uid   = getUserId() ?? 'unknown'
    const uname = getUserName() ?? uid
    const admin = getIsAdmin()
    setUser(uid, uname, admin)

    Promise.all([listAllSessions(), listModules()])
      .then(([convs, mods]) => {
        setConvs(convs)
        setMods(mods)
      })
      .catch(() => {/* non-fatal — sidebar will be empty */})
      .finally(() => setReady(true))
  }, [router, setUser, setConvs, setMods])

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
