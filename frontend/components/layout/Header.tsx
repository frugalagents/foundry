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
  const displayName =
    user?.['custom:display_name'] ?? user?.['custom:amazon_alias'] ?? user?.email?.split('@')[0] ?? 'User';

  return (
    <header className="app-header">
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <div className="app-logo text-display">P</div>
        <span className="text-display" style={{ fontSize: '1.05rem', color: 'var(--text-primary)' }}>
          Platform Advisor
        </span>
      </div>

      {/* Right side */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        {isRealAdmin && !viewingAsUser && <Badge color="blue" size="sm">Admin</Badge>}
        {isRealAdmin && viewingAsUser && <Badge color="orange" size="sm">Viewing as User</Badge>}
        {isRealAdmin && (
          <button
            onClick={() => setViewingAsUser(!viewingAsUser)}
            title={viewingAsUser ? 'Switch back to Admin view' : 'View as regular user'}
            className="app-header-btn"
          >
            {viewingAsUser ? <ShieldCheck size={13} /> : <User size={13} />}
            {viewingAsUser ? 'Admin view' : 'User view'}
          </button>
        )}
        <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>{displayName}</span>
        <button onClick={logout} title="Sign out" className="app-header-icon">
          <LogOut size={15} />
        </button>
      </div>

      <style jsx global>{`
        .app-header {
          height: 56px;
          background: var(--bg-card);
          border-bottom: 1px solid var(--border-default);
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 20px;
          position: sticky;
          top: 0;
          z-index: 40;
          flex-shrink: 0;
        }
        .app-logo {
          width: 30px; height: 30px;
          background: var(--accent);
          color: #fff;
          border-radius: var(--radius-sm);
          display: flex; align-items: center; justify-content: center;
          font-size: 17px;
        }
        .app-header-btn {
          background: none; border: 1px solid var(--border-default); cursor: pointer;
          color: var(--text-secondary); display: flex; align-items: center; gap: 5px;
          padding: 4px 8px; border-radius: var(--radius-sm); font-size: var(--text-xs);
          transition: border-color 0.15s, color 0.15s;
        }
        .app-header-btn:hover { border-color: var(--border-strong); color: var(--text-primary); }
        .app-header-icon {
          background: none; border: none; cursor: pointer;
          color: var(--text-muted); display: flex; align-items: center;
          padding: 4px; border-radius: var(--radius-sm);
          transition: background 0.15s, color 0.15s;
        }
        .app-header-icon:hover { background: var(--bg-hover); color: var(--text-primary); }
      `}</style>
    </header>
  );
}

export default Header;
