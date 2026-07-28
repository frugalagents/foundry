'use client';
import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Plus, Play, Pencil, Trash2, Check, X } from 'lucide-react';
import { getCustomer, listSessions, createSession, updateSession, deleteSession } from '@/lib/api';
import type { Customer, Session } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import {
  sessionTitle, sessionMeta, suggestedTitle, statusLabel, isComplete,
  isStaleDraft, relativeTime, prettyPattern,
} from '@/lib/session-format';

export default function CustomerDetailPage() {
  const { id: paramId } = useParams<{ id: string }>();
  const router = useRouter();
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  // Static export bakes placeholder '_'; read real id from the URL.
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
      const title = customer ? suggestedTitle(customer) : undefined;
      const session = await createSession(id, title);
      router.push(`/customers/${id}/sessions/${session.session_id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCreating(false);
    }
  }

  async function saveRename(s: Session) {
    const title = editTitle.trim();
    setEditingId(null);
    if (!title || title === s.name) return;
    setSessions((prev) => prev.map((x) => (x.session_id === s.session_id ? { ...x, name: title } : x)));
    try { await updateSession(id, s.session_id, { title }); }
    catch { /* optimistic; ignore */ }
  }

  async function handleDelete(s: Session) {
    if (!confirm(`Delete "${sessionTitle(s)}"? This cannot be undone.`)) return;
    setSessions((prev) => prev.filter((x) => x.session_id !== s.session_id));
    try { await deleteSession(id, s.session_id); }
    catch { /* ignore */ }
  }

  const { completed, inProgress } = useMemo(() => {
    const byRecent = [...sessions].sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at));
    return {
      completed: byRecent.filter(isComplete),
      inProgress: byRecent.filter((s) => !isComplete(s)),
    };
  }, [sessions]);

  if (loading) {
    return (
      <div style={{ padding: 'var(--space-6)' }}>
        <div className="skeleton" style={{ height: 80, marginBottom: 20 }} />
        <div className="skeleton" style={{ height: 200 }} />
      </div>
    );
  }

  const renderSession = (s: Session) => {
    const editing = editingId === s.session_id;
    const stale = isStaleDraft(s);
    return (
      <Card key={s.session_id} hover={!editing} style={{ padding: 'var(--space-4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            {editing ? (
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input
                  autoFocus
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') saveRename(s); if (e.key === 'Escape') setEditingId(null); }}
                  className="rename-input"
                />
                <button className="icon-btn" onClick={() => saveRename(s)} aria-label="Save"><Check size={15} /></button>
                <button className="icon-btn" onClick={() => setEditingId(null)} aria-label="Cancel"><X size={15} /></button>
              </div>
            ) : (
              <Link href={`/customers/${id}/sessions/${s.session_id}`} style={{ textDecoration: 'none' }}>
                <div style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {sessionTitle(s)}
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 3 }}>
                  {[sessionMeta(s), `Updated ${relativeTime(s.updated_at)}`].filter(Boolean).join(' · ')}
                </div>
              </Link>
            )}
          </div>

          {!editing && (
            <>
              {stale && <Badge color="gray">Paused</Badge>}
              {s.pattern_selected && isComplete(s) && (
                <Badge color="blue">{prettyPattern(s.pattern_selected)}</Badge>
              )}
              {isComplete(s)
                ? <Badge color="green">Complete</Badge>
                : <Badge color="orange">{statusLabel(s.status)}</Badge>}
              <button className="icon-btn" onClick={() => { setEditingId(s.session_id); setEditTitle(s.name ?? sessionTitle(s)); }} aria-label="Rename">
                <Pencil size={14} />
              </button>
              <button className="icon-btn icon-btn--danger" onClick={() => handleDelete(s)} aria-label="Delete">
                <Trash2 size={14} />
              </button>
            </>
          )}
        </div>
      </Card>
    );
  };

  return (
    <div style={{ padding: 'var(--space-6)', maxWidth: 960, margin: '0 auto' }}>
      <Link href="/customers" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginBottom: 'var(--space-5)' }}>
        <ArrowLeft size={14} /> All customers
      </Link>

      {customer && (
        <div style={{ marginBottom: 'var(--space-6)', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-4)' }}>
          <div>
            <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, marginBottom: 8 }}>{customer.name}</h1>
            <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', flexWrap: 'wrap' }}>
              <Badge color="blue">{customer.industry}</Badge>
              {customer.metadata?.region && <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{customer.metadata.region}</span>}
              {customer.metadata?.company_size && <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>· {customer.metadata.company_size}</span>}
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>· {sessions.length} blueprint{sessions.length === 1 ? '' : 's'}</span>
            </div>
            {customer.metadata?.notes && (
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginTop: 'var(--space-3)', maxWidth: 640 }}>
                {customer.metadata.notes}
              </p>
            )}
          </div>
          <Button size="lg" onClick={handleNewSession} loading={creating} style={{ flexShrink: 0 }}>
            <Plus size={16} /> New blueprint
          </Button>
        </div>
      )}

      {error && (
        <div style={{ marginBottom: 'var(--space-4)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', background: 'var(--danger-subtle)', border: '1px solid var(--danger)', color: 'var(--danger)', fontSize: 'var(--text-sm)' }}>
          {error}
        </div>
      )}

      {sessions.length === 0 ? (
        <Card style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-4)', fontSize: 'var(--text-sm)' }}>No blueprints yet.</p>
          <Button onClick={handleNewSession} loading={creating}>
            <Play size={16} /> Start first blueprint
          </Button>
        </Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          {completed.length > 0 && (
            <section>
              <div className="eyebrow" style={{ marginBottom: 'var(--space-3)' }}>Completed blueprints ({completed.length})</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>{completed.map(renderSession)}</div>
            </section>
          )}
          {inProgress.length > 0 && (
            <section>
              <div className="eyebrow" style={{ marginBottom: 'var(--space-3)' }}>In progress ({inProgress.length})</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>{inProgress.map(renderSession)}</div>
            </section>
          )}
        </div>
      )}

      <style jsx global>{`
        .icon-btn {
          display: inline-flex; align-items: center; justify-content: center;
          width: 28px; height: 28px; flex-shrink: 0;
          background: none; border: 1px solid transparent; border-radius: var(--radius-sm);
          color: var(--text-muted); cursor: pointer;
          transition: background 0.15s, color 0.15s, border-color 0.15s;
        }
        .icon-btn:hover { background: var(--bg-hover); color: var(--text-primary); border-color: var(--border-default); }
        .icon-btn--danger:hover { color: var(--danger); }
        .rename-input {
          flex: 1; background: var(--bg-elevated); border: 1px solid var(--accent);
          border-radius: var(--radius-sm); color: var(--text-primary);
          padding: 6px 10px; font-size: var(--text-base); outline: none;
          box-shadow: 0 0 0 3px var(--accent-subtle);
        }
      `}</style>
    </div>
  );
}
