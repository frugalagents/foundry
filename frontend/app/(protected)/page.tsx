'use client';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowRight, Plus } from 'lucide-react';
import { listCustomers, listSessions, createCustomer } from '@/lib/api';
import type { Customer, Session } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import {
  sessionTitle, statusLabel, isComplete, relativeTime, prettyPattern,
} from '@/lib/session-format';

const PIPELINE = ['Intake', 'Pattern', 'Components', 'Compliance', 'Services', 'Cost', 'Blueprint'];
const INDUSTRIES = ['Financial Services', 'Healthcare', 'Insurance', 'Retail', 'Manufacturing', 'Technology', 'Government', 'Other'];

interface Row { session: Session; customer: Customer }

export default function Home() {
  const router = useRouter();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [sessions, setSessions] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', industry: 'Technology' });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const custs = await listCustomers();
        setCustomers(custs);
        setLoading(false);
        const lists = await Promise.all(
          custs.map((c) =>
            listSessions(c.customer_id)
              .then((ss) => ss.map((s) => ({ session: s, customer: c })))
              .catch(() => [] as Row[]),
          ),
        );
        setSessions(lists.flat());
      } catch {
        setLoading(false);
      }
    })();
  }, []);

  const stats = useMemo(() => {
    const inProgress = sessions.filter((r) => !isComplete(r.session)).length;
    const blueprints = sessions.filter((r) => isComplete(r.session)).length;
    return { customers: customers.length, inProgress, blueprints };
  }, [customers, sessions]);

  const recentActivity = useMemo(
    () => [...sessions]
      .sort((a, b) => +new Date(b.session.updated_at) - +new Date(a.session.updated_at))
      .slice(0, 6),
    [sessions],
  );

  const topCustomers = useMemo(
    () => [...customers]
      .sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at))
      .slice(0, 6),
    [customers],
  );

  async function handleCreate() {
    if (!form.name.trim()) return;
    setCreating(true);
    try {
      const c = await createCustomer({ name: form.name, industry: form.industry });
      router.push(`/customers/${c.customer_id}`);
    } catch {
      setCreating(false);
    }
  }

  return (
    <div style={{ height: '100%', overflow: 'hidden', padding: 'var(--space-6)', maxWidth: 1280, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>

      {/* ── Hero: what this does ─────────────────────────────── */}
      <section className="animate-fade-up" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-6)' }}>
        <div style={{ maxWidth: 640 }}>
          <h1 className="text-page-title" style={{ marginBottom: 6 }}>Design your agentic-AI platform</h1>
          <p style={{ fontSize: 'var(--text-base)', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            From intake to a board-ready blueprint — architecture pattern, components,
            compliance, cost and roadmap — in ten guided steps.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 'var(--space-3)', flexWrap: 'wrap' }}>
            {PIPELINE.map((s, i) => (
              <span key={s} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{s}</span>
                {i < PIPELINE.length - 1 && <span style={{ color: 'var(--border-strong)', fontSize: 'var(--text-xs)' }}>›</span>}
              </span>
            ))}
          </div>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(true)} style={{ flexShrink: 0 }}>
          <Plus size={16} /> New customer
        </button>
      </section>

      {/* ── Stat strip ───────────────────────────────────────── */}
      <section className="animate-fade-up stagger-1" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-3)' }}>
        {[
          { n: stats.customers, label: 'Customers' },
          { n: stats.inProgress, label: 'In progress' },
          { n: stats.blueprints, label: 'Blueprints' },
        ].map((s) => (
          <div key={s.label} className="card" style={{ padding: 'var(--space-4) var(--space-5)' }}>
            <div className="text-display" style={{ fontSize: 'var(--text-2xl)', lineHeight: 1 }}>
              {loading ? '—' : s.n}
            </div>
            <div className="eyebrow" style={{ marginTop: 6 }}>{s.label}</div>
          </div>
        ))}
      </section>

      {/* ── Two columns: activity + customers ────────────────── */}
      <section className="animate-fade-up stagger-2" style={{ flex: 1, minHeight: 0, display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 'var(--space-5)' }}>

        {/* Recent activity (sessions) */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div className="eyebrow" style={{ marginBottom: 'var(--space-3)' }}>Recent activity</div>
          <div className="card" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            {loading ? (
              <div className="skeleton" style={{ height: 200, margin: 'var(--space-3)' }} />
            ) : recentActivity.length === 0 ? (
              <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
                No advisory sessions yet. Create a customer to begin.
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    {['Blueprint', 'Customer', 'Status', ''].map((h) => (
                      <th key={h} className="eyebrow" style={{ textAlign: 'left', padding: '10px 14px', borderBottom: '1px solid var(--border-default)', fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recentActivity.map(({ session, customer }) => (
                    <tr
                      key={session.session_id}
                      onClick={() => router.push(`/customers/${customer.customer_id}/sessions/${session.session_id}`)}
                      className="activity-row"
                    >
                      <td style={{ padding: '10px 14px' }}>
                        <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>{sessionTitle(session)}</div>
                        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{relativeTime(session.updated_at)}</div>
                      </td>
                      <td style={{ padding: '10px 14px', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>{customer.name}</td>
                      <td style={{ padding: '10px 14px' }}>
                        {isComplete(session)
                          ? <span className="badge badge-success">Complete</span>
                          : <span className="badge badge-stage">{statusLabel(session.status)}</span>}
                      </td>
                      <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                        <ArrowRight size={14} style={{ color: 'var(--text-muted)' }} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Customers (compact) */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
            <div className="eyebrow">Customers</div>
            <Link href="/customers" style={{ fontSize: 'var(--text-xs)', color: 'var(--accent)', display: 'inline-flex', alignItems: 'center', gap: 3 }}>
              All <ArrowRight size={12} />
            </Link>
          </div>
          <div className="card" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            {loading ? (
              <div className="skeleton" style={{ height: 200, margin: 'var(--space-3)' }} />
            ) : topCustomers.length === 0 ? (
              <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
                No customers yet.
              </div>
            ) : (
              topCustomers.map((c, i) => (
                <Link
                  key={c.customer_id}
                  href={`/customers/${c.customer_id}`}
                  className="cust-row"
                  style={{ borderTop: i > 0 ? '1px solid var(--border-subtle)' : 'none' }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.name}</div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{c.industry}</div>
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                    {c.session_count} bp
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </section>

      {/* Create modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="New customer">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <Input
            label="Customer / company name"
            placeholder="Acme Corp"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
          <label className="ctrl-field">
            <span>Industry</span>
            <select value={form.industry} onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))} className="input-field">
              {INDUSTRIES.map((i) => <option key={i}>{i}</option>)}
            </select>
          </label>
          <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'flex-end' }}>
            <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
            <button className="btn-primary" onClick={handleCreate} disabled={!form.name.trim() || creating}>
              {creating ? 'Creating…' : 'Create & open'}
            </button>
          </div>
        </div>
      </Modal>

      <style jsx global>{`
        .activity-row { cursor: pointer; transition: background 0.12s; }
        .activity-row:not(:last-child) td { border-bottom: 1px solid var(--border-subtle); }
        .activity-row:hover { background: var(--bg-sunken); }
        .cust-row {
          display: flex; align-items: center; justify-content: space-between; gap: 8px;
          padding: 11px 14px; text-decoration: none; transition: background 0.12s;
        }
        .cust-row:hover { background: var(--bg-sunken); text-decoration: none; }
        .ctrl-field { display: flex; flex-direction: column; gap: 6px; font-size: var(--text-sm); color: var(--text-secondary); font-weight: 500; }
      `}</style>
    </div>
  );
}
