'use client';
import { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LogOut, ShieldCheck, User } from 'lucide-react';
import { useAppStore } from '@/store';
import { getUser, logout } from '@/lib/auth';
import { Badge, Button } from '@/components/ui';

interface NavItem { label: string; href: string }

export function Header() {
  const pathname = usePathname();
  const { user, setUser, viewingAsUser, setViewingAsUser } = useAppStore();

  useEffect(() => {
    const u = getUser();
    if (u) setUser(u);
  }, [setUser]);

  const isRealAdmin = user?.['custom:role'] === 'admin';
  const displayName =
    user?.['custom:display_name'] ?? user?.['custom:amazon_alias'] ?? user?.email?.split('@')[0] ?? 'User';

  const nav: NavItem[] = [
    { label: 'Home', href: '/' },
    { label: 'Customers', href: '/customers' },
    { label: 'Architecture', href: '/architecture' },
  ];
  const isActive = (href: string) => (href === '/' ? pathname === '/' : pathname.startsWith(href));

  return (
    <header className="app-header">
      {/* Logo + nav */}
      <div className="app-header-left">
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
          <div className="app-logo text-display">P</div>
          <span className="app-brand-label text-display" style={{ fontSize: '1.05rem', color: 'var(--text-primary)' }}>
            Platform Advisor
          </span>
        </Link>
        <nav className="app-header-nav">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`hdr-nav ${isActive(item.href) ? 'hdr-nav--active' : ''}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Right side */}
      <div className="app-header-actions">
        {isRealAdmin && !viewingAsUser && <span className="app-admin-context"><Badge color="blue" size="sm">Admin</Badge></span>}
        {isRealAdmin && viewingAsUser && <span className="app-admin-context"><Badge color="orange" size="sm">Viewing as User</Badge></span>}
        {isRealAdmin && (
          <span className="app-admin-context">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setViewingAsUser(!viewingAsUser)}
              title={viewingAsUser ? 'Switch back to Admin view' : 'View as regular user'}
            >
              {viewingAsUser ? <ShieldCheck size={13} /> : <User size={13} />}
              {viewingAsUser ? 'Admin view' : 'User view'}
            </Button>
          </span>
        )}
        <span className="app-user-name" style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>{displayName}</span>
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
        .app-header-left {
          display: flex;
          align-items: center;
          gap: 20px;
          min-width: 0;
          flex: 1;
        }
        .app-header-nav {
          display: flex;
          align-items: center;
          gap: 2px;
          min-width: 0;
          overflow-x: auto;
          scrollbar-width: none;
        }
        .app-header-nav::-webkit-scrollbar { display: none; }
        .app-header-actions {
          display: flex;
          align-items: center;
          gap: 12px;
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
        .hdr-nav {
          padding: 6px 12px; border-radius: var(--radius-sm);
          font-size: var(--text-sm); font-weight: 500;
          color: var(--text-secondary); text-decoration: none;
          transition: background 0.12s, color 0.12s;
        }
        .hdr-nav:hover { background: var(--bg-hover); color: var(--text-primary); text-decoration: none; }
        .hdr-nav--active { background: var(--accent-soft); color: var(--accent-deep); font-weight: 600; }
        .app-header-icon {
          background: none; border: none; cursor: pointer;
          color: var(--text-muted); display: flex; align-items: center;
          padding: 4px; border-radius: var(--radius-sm);
          transition: background 0.15s, color 0.15s;
        }
        .app-header-icon:hover { background: var(--bg-hover); color: var(--text-primary); }
        @media (max-width: 900px) {
          .app-header { padding: 0 12px; gap: 8px; }
          .app-header-left { gap: 8px; }
          .app-brand-label, .app-user-name, .app-admin-context { display: none; }
          .hdr-nav { padding: 6px 9px; white-space: nowrap; }
          .app-header-actions { gap: 4px; }
        }
      `}</style>
    </header>
  );
}

export default Header;
