'use client';
import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getToken } from '@/lib/auth';
import { Header } from './Header';

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (!getToken()) {
      router.replace('/login');
    }
  }, [router]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Header />
      <main style={{ flex: 1, overflow: 'auto', background: 'var(--bg-primary)', minHeight: 0 }}>
        {children}
      </main>
    </div>
  );
}

export default AppShell;
