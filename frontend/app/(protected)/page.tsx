'use client';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight } from 'lucide-react';
import { listCustomers, listSessions } from '@/lib/api';
import type { Customer, Session } from '@/lib/types';
import {
  sessionTitle, statusLabel, isComplete, relativeTime,
} from '@/lib/session-format';

interface Row { session: Session; customer: Customer }
type ActivityFilter = 'recent' | 'in_progress' | 'blueprints';

export default function Home() {
  const router = useRouter();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [sessions, setSessions] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [activityFilter, setActivityFilter] = useState<ActivityFilter>('recent');

  useEffect(() => {
    (async () => {
      try {
        const custs = await listCustomers();
        setCustomers(custs);
        const lists = await Promise.all(
          custs.map((c) =>
            listSessions(c.customer_id)
              .then((ss) => ss.map((s) => ({ session: s, customer: c })))
              .catch(() => [] as Row[]),
          ),
        );
        setSessions(lists.flat());
        setLoading(false);
      } catch {
        setLoading(false);
      }
    })();
  }, []);

  const stats = useMemo(() => ({
    customers: customers.length,
    inProgress: sessions.filter((r) => !isComplete(r.session)).length,
    blueprints: sessions.filter((r) => isComplete(r.session)).length,
  }), [customers, sessions]);

  const activityRows = useMemo(
    () => sessions
      .filter(({ session }) => {
        if (activityFilter === 'in_progress') return !isComplete(session);
        if (activityFilter === 'blueprints') return isComplete(session);
        return true;
      })
      .sort((a, b) => +new Date(b.session.updated_at) - +new Date(a.session.updated_at))
      .slice(0, activityFilter === 'recent' ? 8 : undefined),
    [activityFilter, sessions],
  );

  const statTiles = [
    { n: stats.customers, label: 'Customers', action: () => router.push('/customers'), active: false },
    { n: stats.inProgress, label: 'In progress', action: () => setActivityFilter('in_progress'), active: activityFilter === 'in_progress' },
    { n: stats.blueprints, label: 'Blueprints', action: () => setActivityFilter('blueprints'), active: activityFilter === 'blueprints' },
  ];

  const activityTitle = {
    recent: 'Recent activity',
    in_progress: 'In-progress sessions',
    blueprints: 'Completed blueprints',
  }[activityFilter];

  return (
    <div className="home-shell">

      {/* ── Hero: what this does ─────────────────────────────── */}
      <section className="animate-fade-up home-hero">
        <h1 className="text-page-title" style={{ marginBottom: 10 }}>Design your agentic-AI platform</h1>
        <p className="home-hero-copy">
          Answer a short intake and the advisor recommends an <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>architecture
          pattern</strong>, selects the <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>AWS components and services</strong> to
          build, flags <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>compliance and risks</strong>, and produces a
          costed <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>roadmap and blueprint</strong> you can take to a review.
        </p>
      </section>

      {/* ── Clickable stat tiles (also the way into Customers) ─── */}
      <section className="animate-fade-up stagger-1" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-3)' }}>
        {statTiles.map((s) => (
          <button
            key={s.label}
            onClick={s.action}
            className={s.active ? 'stat-tile active' : 'stat-tile'}
            aria-pressed={s.label === 'Customers' ? undefined : s.active}
          >
            <div>
              <div className="text-display" style={{ fontSize: 'var(--text-2xl)', lineHeight: 1 }}>
                {loading ? '—' : s.n}
              </div>
              <div className="eyebrow" style={{ marginTop: 6 }}>{s.label}</div>
            </div>
            <ArrowRight size={15} className="stat-arrow" />
          </button>
        ))}
      </section>

      {/* ── Recent activity (full width, single-row) ─────────── */}
      <section className="animate-fade-up stagger-2" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
          <div className="eyebrow">{activityTitle}</div>
          {activityFilter !== 'recent' && (
            <button className="activity-reset" onClick={() => setActivityFilter('recent')}>Show recent</button>
          )}
        </div>
        <div className="card" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          {loading ? (
            <div className="skeleton" style={{ height: 220, margin: 'var(--space-3)' }} />
          ) : activityRows.length === 0 ? (
            <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
              {activityFilter === 'recent'
                ? 'No advisory sessions yet. Create a customer to begin.'
                : `No ${activityTitle.toLowerCase()} to show.`}
            </div>
          ) : (
            <div style={{ overflowY: 'auto', minHeight: 0 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    {['Blueprint', 'Customer', 'Status', 'Updated', ''].map((h) => (
                      <th key={h} className="eyebrow" style={{ textAlign: 'left', padding: '9px 16px', borderBottom: '1px solid var(--border-default)', fontWeight: 600, position: 'sticky', top: 0, background: 'var(--bg-card)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {activityRows.map(({ session, customer }) => (
                    <tr
                      key={session.session_id}
                      onClick={() => router.push(`/customers/${customer.customer_id}/sessions/${session.session_id}`)}
                      className="activity-row"
                    >
                      <td style={{ padding: '10px 16px', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{sessionTitle(session)}</td>
                      <td style={{ padding: '10px 16px', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>{customer.name}</td>
                      <td style={{ padding: '10px 16px' }}>
                        {isComplete(session)
                          ? <span className="badge badge-success">Complete</span>
                          : <span className="badge badge-stage">{statusLabel(session.status)}</span>}
                      </td>
                      <td style={{ padding: '10px 16px', fontSize: 'var(--text-xs)', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{relativeTime(session.updated_at)}</td>
                      <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                        <ArrowRight size={14} style={{ color: 'var(--text-muted)' }} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      <style jsx global>{`
        .home-shell {
          height: 100%;
          overflow: auto;
          padding: var(--space-6);
          max-width: 1180px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: var(--space-5);
        }
        .home-hero { max-width: 1000px; }
        .home-hero-copy {
          margin: 0;
          color: var(--text-secondary);
          font-size: 20px;
          line-height: 1.5;
        }
        .stat-tile {
          display: flex; align-items: center; justify-content: space-between;
          text-align: left; width: 100%; cursor: pointer;
          background: var(--bg-card); border: 1px solid var(--border-default);
          border-radius: var(--radius-lg); padding: var(--space-4) var(--space-5);
          transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
        }
        .stat-tile:hover {
          border-color: var(--border-accent);
          box-shadow: 0 0 0 1px rgba(47,122,115,0.12), 0 4px 14px rgba(31,30,27,0.05);
          transform: translateY(-1px);
        }
        .stat-tile.active {
          border-color: var(--accent);
          background: var(--accent-soft);
          box-shadow: 0 0 0 1px rgba(47,122,115,0.12);
        }
        .stat-arrow { color: var(--text-muted); transition: color 0.15s, transform 0.15s; }
        .stat-tile:hover .stat-arrow { color: var(--accent); transform: translateX(2px); }
        .activity-row { cursor: pointer; transition: background 0.12s; }
        .activity-row:not(:last-child) td { border-bottom: 1px solid var(--border-subtle); }
        .activity-row:hover { background: var(--bg-sunken); }
        .activity-reset {
          border: 0;
          background: transparent;
          color: var(--accent-deep);
          cursor: pointer;
          font-size: var(--text-xs);
          font-weight: 600;
        }
        .activity-reset:hover { text-decoration: underline; }
        .ctrl-field { display: flex; flex-direction: column; gap: 6px; font-size: var(--text-sm); color: var(--text-secondary); font-weight: 500; }
        @media (max-width: 720px) {
          .home-shell { padding: var(--space-4); gap: var(--space-4); }
          .home-hero-copy { font-size: 17px; line-height: 1.55; }
          .home-shell > section:nth-of-type(2) { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}
