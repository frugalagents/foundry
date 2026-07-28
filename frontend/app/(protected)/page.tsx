'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, Users, Plus, Clock } from 'lucide-react';
import { listCustomers, listSessions } from '@/lib/api';
import type { Customer, Session } from '@/lib/types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import {
  sessionTitle, sessionMeta, statusLabel, isComplete, relativeTime, prettyPattern,
} from '@/lib/session-format';

interface Resume { session: Session; customer: Customer }

export default function Home() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [resumable, setResumable] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const custs = await listCustomers();
        setCustomers(custs);
        // Pull sessions for the most recently-updated customers to build a resume list.
        const recent = [...custs]
          .sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at))
          .slice(0, 8);
        const sessLists = await Promise.all(
          recent.map((c) =>
            listSessions(c.customer_id)
              .then((ss) => ss.map((s) => ({ session: s, customer: c })))
              .catch(() => [] as Resume[]),
          ),
        );
        const all = sessLists.flat();
        const inProgress = all
          .filter((r) => !isComplete(r.session))
          .sort((a, b) => +new Date(b.session.updated_at) - +new Date(a.session.updated_at))
          .slice(0, 5);
        setResumable(inProgress);
      } catch {
        /* handled by empty state */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const recentCustomers = [...customers]
    .sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at))
    .slice(0, 6);

  return (
    <div style={{ padding: 'var(--space-6)', maxWidth: 1200, margin: '0 auto' }}>
      <h1 className="text-page-title" style={{ marginBottom: 4 }}>My work</h1>
      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginBottom: 'var(--space-6)' }}>
        Pick up where you left off, or jump into a customer.
      </p>

      {/* Resume in-progress engagements */}
      <section style={{ marginBottom: 'var(--space-8)' }}>
        <div className="eyebrow" style={{ marginBottom: 'var(--space-3)' }}>Continue working</div>
        {loading ? (
          <div className="skeleton" style={{ height: 72 }} />
        ) : resumable.length === 0 ? (
          <Card style={{ padding: 'var(--space-5)', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
            No engagements in progress. Start one from a customer.
          </Card>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {resumable.map(({ session, customer }) => (
              <Link
                key={session.session_id}
                href={`/customers/${customer.customer_id}/sessions/${session.session_id}`}
                style={{ textDecoration: 'none' }}
              >
                <Card hover style={{ padding: 'var(--space-4)', display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
                  <Clock size={16} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {sessionTitle(session)}
                    </div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 2 }}>
                      {customer.name} · {sessionMeta(session) || statusLabel(session.status)} · {relativeTime(session.updated_at)}
                    </div>
                  </div>
                  {session.pattern_selected && (
                    <Badge color="blue">{prettyPattern(session.pattern_selected)}</Badge>
                  )}
                  <ArrowRight size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Recent customers */}
      <section>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
          <div className="eyebrow">Recent customers</div>
          <Link href="/customers" style={{ fontSize: 'var(--text-sm)', color: 'var(--accent)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            All customers <ArrowRight size={13} />
          </Link>
        </div>
        {loading ? (
          <div className="skeleton" style={{ height: 96 }} />
        ) : recentCustomers.length === 0 ? (
          <Card style={{ padding: 'var(--space-6)', textAlign: 'center' }}>
            <Users size={24} style={{ color: 'var(--text-muted)', margin: '0 auto 8px' }} />
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
              No customers yet.
            </div>
            <Link href="/customers" style={{ color: 'var(--accent)', fontSize: 'var(--text-sm)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <Plus size={14} /> Add your first customer
            </Link>
          </Card>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 'var(--space-3)' }}>
            {recentCustomers.map((c) => (
              <Link key={c.customer_id} href={`/customers/${c.customer_id}`} style={{ textDecoration: 'none' }}>
                <Card hover style={{ padding: 'var(--space-4)' }}>
                  <div style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)' }}>{c.name}</div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 4 }}>
                    {[c.industry, c.metadata?.region].filter(Boolean).join(' · ')}
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 8 }}>
                    {c.session_count} blueprint{c.session_count === 1 ? '' : 's'} · {relativeTime(c.updated_at)}
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
