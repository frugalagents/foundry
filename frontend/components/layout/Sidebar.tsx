'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Users, Settings, BarChart2 } from 'lucide-react';
import { useAppStore } from '@/store';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { label: 'Home', href: '/', icon: <Home size={15} /> },
  { label: 'Customers', href: '/customers', icon: <Users size={15} /> },
];

const adminItems: NavItem[] = [
  { label: 'Analytics', href: '/admin/dashboard', icon: <BarChart2 size={15} /> },
  { label: 'Config', href: '/admin/config', icon: <Settings size={15} /> },
];

export function Sidebar() {
  const pathname = usePathname();
  const user = useAppStore((s) => s.user);
  const viewingAsUser = useAppStore((s) => s.viewingAsUser);
  const isAdmin = user?.['custom:role'] === 'admin' && !viewingAsUser;

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  const renderItem = (item: NavItem) => (
    <Link
      key={item.href}
      href={item.href}
      className={`nav-item ${isActive(item.href) ? 'nav-item--active' : ''}`}
    >
      {item.icon}
      {item.label}
    </Link>
  );

  return (
    <aside className="sidebar">
      {navItems.map(renderItem)}

      {isAdmin && (
        <>
          <div className="eyebrow" style={{ padding: '12px 12px 4px' }}>Admin</div>
          {adminItems.map(renderItem)}
        </>
      )}

      <style jsx>{`
        .sidebar {
          width: 220px;
          background: var(--bg-card);
          border-right: 1px solid var(--border-default);
          padding: 12px 8px;
          display: flex;
          flex-direction: column;
          gap: 2px;
          flex-shrink: 0;
          overflow-y: auto;
        }
      `}</style>
      <style jsx global>{`
        .nav-item {
          display: flex;
          align-items: center;
          gap: 9px;
          padding: 8px 12px;
          border-radius: var(--radius-sm);
          font-size: var(--text-sm);
          font-weight: 400;
          color: var(--text-secondary);
          text-decoration: none;
          border-left: 2px solid transparent;
          transition: background 0.12s, color 0.12s;
        }
        .nav-item:hover {
          background: var(--bg-elevated);
          color: var(--text-primary);
          text-decoration: none;
        }
        .nav-item--active {
          font-weight: 500;
          color: var(--text-primary);
          background: var(--bg-elevated);
          border-left-color: var(--accent);
        }
      `}</style>
    </aside>
  );
}

export default Sidebar;
