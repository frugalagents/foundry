'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Plus, Play } from 'lucide-react';
import { getCustomer, listSessions, createSession } from '@/lib/api';
import type { Customer, Session } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

const STATUS_COLORS: Record<string, 'blue' | 'green' | 'orange' | 'gray'> = {
  complete: 'green', blueprint: 'blue', phasing: 'blue',
  services: 'orange', innovation: 'orange', default: 'gray',
};

const STEP_LABELS: Record<string, string> = {
  intake: '1/10', scoring: '2/10', components: '3/10', innovation: '4/10',
  compliance: '5/10', services: '6/10', antipatterns: '7/10', phasing: '8/10',
  costs: '9/10', blueprint: '10/10', complete: '✓',
};

const PATTERN_COLORS: Record<string, string> = {
  'pattern:federated':   '#10B981',
  'pattern:centralized': '#3B82F6',
  'pattern:mesh':        '#F59E0B',
  'pattern:economy':     '#8B5CF6',
};

export default function CustomerDetailPage() {
  const { id: paramId } = useParams<{ id: string }>();
  const router = useRouter();
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // With static export the RSC payload bakes in the placeholder id '_'.
  // Read the real customer ID from the browser URL on mount.
  const [id, setId] = useState(paramId ?? '');
  useEffect(() => {
    const parts = window.location.pathname.split('/').filter(Boolean);
    const idx = parts.indexOf('customers');
    const real = idx >= 0 ? parts[idx + 1] : '';
    setId(real && real !== '_' ? real : paramId ?? '');
  }, [paramId]);

  useEffect(() => {
    if (!id || id === '_') return;
    Promise.all([getCustomer(id), listSessions(id)])
      .then(([c, s]) => { setCustomer(c); setSessions(s); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  async function handleNewSession() {
    setCreating(true);
    setError(null);
    try {
      const session = await createSession(id);
      router.push(`/customers/${id}/sessions/${session.session_id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCreating(false);
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <div className="skeleton" style={{ height: 80, marginBottom: 20 }} />
        <div className="skeleton" style={{ height: 200 }} />
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 900 }}>
      <Link href="/customers" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
        <ArrowLeft size={13} /> All Customers
      </Link>

      {customer && (
        <div style={{ marginBottom: 24, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 6 }}>{customer.name}</h1>
            <Badge color="blue">{customer.industry}</Badge>
          </div>
          <Button onClick={handleNewSession} loading={creating}>
            <Plus size={14} /> New Blueprint
          </Button>
        </div>
      )}

      {error && (
        <div style={{ marginBottom: 16, padding: '10px 14px', borderRadius: 8, background: 'rgba(255,80,80,0.1)', border: '1px solid rgba(255,80,80,0.3)', color: '#ff5050', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* P5: Prior blueprint continuity banner */}
      {sessions.some((s) => s.status === 'complete') && (
        <div style={{
          marginBottom: 20,
          padding: '12px 16px',
          background: 'var(--accent-blue)0a',
          border: '1px solid var(--accent-blue)33',
          borderRadius: 10,
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-blue)', marginBottom: 2 }}>
              Returning customer
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              {(() => {
                const completed = sessions.filter((s) => s.status === 'complete');
                if (completed.length === 0) return null;
                const latest = completed[0];
                const patternName = latest.pattern_selected
                  ? latest.pattern_selected.split(':')[1]?.replace(/^\w/, (c) => c.toUpperCase()) ?? latest.pattern_selected
                  : null;
                return patternName
                  ? `Prior blueprint: ${patternName} — new sessions will build on this context.`
                  : `${completed.length} prior blueprint${completed.length !== 1 ? 's' : ''} — new sessions will reference earlier work.`;
              })()}
            </div>
          </div>
          <Button onClick={handleNewSession} loading={creating} style={{ flexShrink: 0 }}>
            <Plus size={13} /> New Blueprint
          </Button>
        </div>
      )}

      {/* Sessions */}
      <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
        Sessions ({sessions.length})
      </h2>

      {sessions.length === 0 ? (
        <Card style={{ padding: 40, textAlign: 'center' }}>
          <p style={{ color: 'var(--text-muted)', marginBottom: 16 }}>No sessions yet.</p>
          <Button onClick={handleNewSession} loading={creating}>
            <Play size={14} /> Start First Blueprint
          </Button>
        </Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {sessions.map((s) => (
            <Link key={s.session_id} href={`/customers/${id}/sessions/${s.session_id}`} style={{ textDecoration: 'none' }}>
              <Card hover style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 16, cursor: 'pointer' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 3 }}>
                    {s.name ?? new Date(s.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </div>
                  {s.pattern_selected && (
                    <span style={{
                      fontSize: 11, fontWeight: 600,
                      color: PATTERN_COLORS[s.pattern_selected] ?? 'var(--accent-blue)',
                    }}>
                      {s.pattern_selected.split(':')[1]?.replace(/^\w/, (c) => c.toUpperCase()) ?? s.pattern_selected}
                    </span>
                  )}
                </div>
                <Badge color={STATUS_COLORS[s.status] ?? 'gray'}>
                  {STEP_LABELS[s.status] ?? s.status}
                </Badge>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {new Date(s.updated_at).toLocaleDateString()}
                </span>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

