'use client';
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LogOut, ShieldCheck, User, Search } from 'lucide-react';
import { useAppStore } from '@/store';
import { getUser, logout } from '@/lib/auth';
import { listCustomers } from '@/lib/api';
import type { Customer } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';

export function Header() {
  const router = useRouter();
  const { user, setUser, viewingAsUser, setViewingAsUser } = useAppStore();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const u = getUser();
    if (u) setUser(u);
    listCustomers().then(setCustomers).catch(() => {});
  }, [setUser]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const isRealAdmin = user?.['custom:role'] === 'admin';
  const displayName =
    user?.['custom:display_name'] ?? user?.['custom:amazon_alias'] ?? user?.email?.split('@')[0] ?? 'User';

  const matches = query.trim()
    ? customers.filter((c) => c.name.toLowerCase().includes(query.toLowerCase())).slice(0, 6)
    : [];

  const go = (id: string) => {
    setQuery(''); setOpen(false);
    router.push(`/customers/${id}`);
  };

  return (
    <header className="app-header">
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <div className="app-logo">P</div>
        <span style={{ fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--text-primary)' }}>
          Platform Advisor
        </span>
      </div>

      {/* Global customer search */}
      <div ref={boxRef} style={{ position: 'relative', flex: 1, maxWidth: 420, margin: '0 var(--space-6)' }}>
        <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
        <input
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          placeholder="Search customers…"
          className="app-search"
        />
        {open && matches.length > 0 && (
          <div className="app-search-menu">
            {matches.map((c) => (
              <button key={c.customer_id} onClick={() => go(c.customer_id)} className="app-search-item">
                <span style={{ color: 'var(--text-primary)' }}>{c.name}</span>
                <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>{c.industry}</span>
              </button>
            ))}
          </div>
        )}
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
          width: 28px; height: 28px;
          background: var(--accent);
          color: var(--accent-fg);
          border-radius: 6px;
          display: flex; align-items: center; justify-content: center;
          font-size: 14px; font-weight: 700;
        }
        .app-search {
          width: 100%;
          background: var(--bg-elevated);
          border: 1px solid var(--border-default);
          border-radius: var(--radius-sm);
          color: var(--text-primary);
          padding: 7px 10px 7px 32px;
          font-size: var(--text-sm);
          outline: none;
          transition: border-color 0.15s, box-shadow 0.15s;
        }
        .app-search::placeholder { color: var(--text-muted); }
        .app-search:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-subtle); }
        .app-search-menu {
          position: absolute; top: calc(100% + 4px); left: 0; right: 0;
          background: var(--bg-elevated);
          border: 1px solid var(--border-default);
          border-radius: var(--radius-md);
          box-shadow: var(--shadow-elevated);
          overflow: hidden;
          z-index: 50;
        }
        .app-search-item {
          display: flex; align-items: center; justify-content: space-between;
          width: 100%; padding: 8px 12px;
          background: none; border: none; cursor: pointer;
          font-size: var(--text-sm); text-align: left;
        }
        .app-search-item:hover { background: var(--bg-hover); }
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
