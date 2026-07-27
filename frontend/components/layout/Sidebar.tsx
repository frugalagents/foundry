'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Users, Settings, BarChart2, ChevronRight } from 'lucide-react';
import { useAppStore } from '@/store';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/', icon: <LayoutDashboard size={15} /> },
  { label: 'Customers', href: '/customers', icon: <Users size={15} /> },
];

const adminItems: NavItem[] = [
  { label: 'Analytics', href: '/admin/dashboard', icon: <BarChart2 size={15} />, adminOnly: true },
  { label: 'Config', href: '/admin/config', icon: <Settings size={15} />, adminOnly: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const user = useAppStore((s) => s.user);
  const viewingAsUser = useAppStore((s) => s.viewingAsUser);
  const isAdmin = user?.['custom:role'] === 'admin' && !viewingAsUser;

  const itemStyle = (active: boolean) => ({
    display: 'flex',
    alignItems: 'center',
    gap: 9,
    padding: '7px 12px',
    borderRadius: 'var(--radius-sm)',
    fontSize: 13,
    fontWeight: active ? 500 : 400,
    color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
    background: active ? 'var(--bg-elevated)' : 'transparent',
    cursor: 'pointer',
    textDecoration: 'none',
    transition: 'all 0.12s',
    borderLeft: active ? '2px solid var(--accent-blue)' : '2px solid transparent',
  });

  return (
    <aside
      style={{
        width: 220,
        background: 'var(--bg-card)',
        borderRight: '1px solid var(--border-default)',
        padding: '12px 8px',
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        flexShrink: 0,
        overflowY: 'auto',
      }}
    >
      {navItems.map((item) => {
        const active =
          item.href === '/'
            ? pathname === '/'
            : pathname.startsWith(item.href);
        return (
          <Link key={item.href} href={item.href} style={itemStyle(active)}>
            {item.icon}
            {item.label}
          </Link>
        );
      })}

      {isAdmin && (
        <>
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.07em',
              padding: '12px 12px 4px',
            }}
          >
            Admin
          </div>
          {adminItems.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href} style={itemStyle(active)}>
                {item.icon}
                {item.label}
              </Link>
            );
          })}
        </>
      )}
    </aside>
  );
}

export default Sidebar;
