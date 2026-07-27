'use client';
import { useEffect } from 'react';
import { LogOut, ShieldCheck, User } from 'lucide-react';
import { useAppStore } from '@/store';
import { getUser, logout } from '@/lib/auth';
import { Badge } from '@/components/ui/Badge';

export function Header() {
  const { user, setUser, viewingAsUser, setViewingAsUser } = useAppStore();

  useEffect(() => {
    const u = getUser();
    if (u) setUser(u);
  }, [setUser]);

  const isRealAdmin = user?.['custom:role'] === 'admin';
  const displayName = user?.['custom:display_name'] ?? user?.['custom:amazon_alias'] ?? user?.email?.split('@')[0] ?? 'User';

  return (
    <header
      style={{
        height: '56px',
        background: 'var(--bg-card)',
        borderBottom: '1px solid var(--border-default)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        position: 'sticky',
        top: 0,
        zIndex: 40,
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div
          style={{
            width: 28, height: 28,
            background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))',
            borderRadius: 6,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 14, fontWeight: 700, color: '#fff',
          }}
        >
          P
        </div>
        <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>
          Platform Advisor
        </span>
      </div>

      {/* Right side */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {isRealAdmin && !viewingAsUser && <Badge color="purple" size="sm">Admin</Badge>}
        {isRealAdmin && viewingAsUser && <Badge color="orange" size="sm">Viewing as User</Badge>}
        {isRealAdmin && (
          <button
            onClick={() => setViewingAsUser(!viewingAsUser)}
            title={viewingAsUser ? 'Switch back to Admin view' : 'View as regular user'}
            style={{
              background: 'none', border: '1px solid var(--border-default)', cursor: 'pointer',
              color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 5,
              padding: '3px 8px', borderRadius: 4, fontSize: 12,
            }}
          >
            {viewingAsUser ? <ShieldCheck size={13} /> : <User size={13} />}
            {viewingAsUser ? 'Admin view' : 'User view'}
          </button>
        )}
        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{displayName}</span>
        <button
          onClick={logout}
          title="Sign out"
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-muted)', display: 'flex', alignItems: 'center',
            padding: 4, borderRadius: 4,
          }}
        >
          <LogOut size={15} />
        </button>
      </div>
    </header>
  );
}

export default Header;
