'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  ArrowUpDown,
  ExternalLink,
  FileText,
  MoreHorizontal,
  Pencil,
  Plus,
  Trash2,
} from 'lucide-react';
import {
  createSession,
  deleteSession,
  getCustomer,
  listSessions,
  updateSession,
} from '@/lib/api';
import type { Customer, EvidenceState, Session } from '@/lib/types';
import { Badge, Button, Input, Modal, Textarea } from '@/components/ui';
import {
  evidenceLabel,
  isComplete,
  prettyPattern,
  relativeTime,
  sessionTitle,
  statusLabel,
  suggestedTitle,
  workloadLabel,
} from '@/lib/session-format';

type Filter = 'all' | 'in_progress' | 'complete';
type Sort = 'updated' | 'title' | 'status';

const EMPTY_FORM = { title: '', description: '', blueprintType: 'coding' };

const BLUEPRINT_TYPES: { value: string; label: string; available: boolean }[] = [
  { value: 'coding', label: 'Agentic Coding Platform', available: true },
  { value: 'internal', label: 'Internal-Facing Platform', available: false },
  { value: 'customer-facing', label: 'Customer-Facing Agentic Platform', available: false },
  { value: 'saas', label: 'SaaS Decomposition', available: false },
  { value: 'marketplace', label: 'Marketplace', available: false },
];

export default function CustomerDetailPage() {
  const { id: paramId } = useParams<{ id: string }>();
  const router = useRouter();
  const [id, setId] = useState(paramId ?? '');
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filter, setFilter] = useState<Filter>('all');
  const [sort, setSort] = useState<Sort>('updated');
  const [menuId, setMenuId] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState(EMPTY_FORM);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [editTarget, setEditTarget] = useState<Session | null>(null);
  const [editForm, setEditForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<Session | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    const parts = window.location.pathname.split('/').filter(Boolean);
    const idx = parts.indexOf('customers');
    const real = idx >= 0 ? parts[idx + 1] : '';
    setId(real && real !== '_' ? real : paramId ?? '');
  }, [paramId]);

  useEffect(() => {
    if (!id || id === '_') return;
    setLoading(true);
    Promise.all([getCustomer(id), listSessions(id)])
      .then(([nextCustomer, nextSessions]) => {
        setCustomer(nextCustomer);
        setSessions(nextSessions);
        setError(null);
      })
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!menuId) return;
    const close = () => setMenuId(null);
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close();
    };
    document.addEventListener('click', close);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('click', close);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [menuId]);

  const counts = useMemo(() => ({
    all: sessions.length,
    in_progress: sessions.filter((session) => !isComplete(session)).length,
    complete: sessions.filter(isComplete).length,
  }), [sessions]);

  const visibleSessions = useMemo(() => {
    const filtered = sessions.filter((session) => {
      if (filter === 'complete') return isComplete(session);
      if (filter === 'in_progress') return !isComplete(session);
      return true;
    });
    return [...filtered].sort((a, b) => {
      if (sort === 'title') return sessionTitle(a).localeCompare(sessionTitle(b));
      if (sort === 'status') return statusLabel(a.status).localeCompare(statusLabel(b.status));
      return +new Date(b.updated_at) - +new Date(a.updated_at);
    });
  }, [filter, sessions, sort]);

  function openCreate() {
    setCreateForm({
      title: customer ? suggestedTitle(customer) : '',
      description: '',
      blueprintType: 'coding',
    });
    setCreateError(null);
    setCreateOpen(true);
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    const title = createForm.title.trim();
    if (!title) {
      setCreateError('Blueprint name is required.');
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      const description = createForm.description.trim();
      const blueprintType = createForm.blueprintType;
      const session = await createSession(id, { title, description });
      setSessions((current) => [session, ...current]);
      setCreateOpen(false);
      // Agentic coding platform → the architecture-first canvas. The blueprint
      // (name · description · type) is carried as context and shown on both
      // panels; the questions are specific to the coding platform.
      if (blueprintType === 'coding') {
        const q = new URLSearchParams({
          bp: title,
          desc: description,
          type: blueprintType,
          customer: id,
          session: session.session_id,
        });
        router.push(`/architecture?${q.toString()}`);
      } else {
        router.push(`/customers/${id}/sessions/${session.session_id}`);
      }
    } catch (err) {
      setCreateError((err as Error).message);
    } finally {
      setCreating(false);
    }
  }

  function openEdit(session: Session) {
    setMenuId(null);
    setEditTarget(session);
    setEditForm({
      title: sessionTitle(session),
      description: session.description || session.notes || '',
      blueprintType: 'coding',
    });
    setEditError(null);
  }

  async function handleEdit(event: React.FormEvent) {
    event.preventDefault();
    if (!editTarget) return;
    const title = editForm.title.trim();
    if (!title) {
      setEditError('Blueprint name is required.');
      return;
    }
    setSaving(true);
    setEditError(null);
    try {
      const updated = await updateSession(id, editTarget.session_id, {
        title,
        description: editForm.description.trim(),
      });
      setSessions((current) =>
        current.map((session) => session.session_id === updated.session_id ? updated : session),
      );
      setEditTarget(null);
    } catch (err) {
      setEditError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  function openDelete(session: Session) {
    setMenuId(null);
    setDeleteTarget(session);
    setDeleteError(null);
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteSession(id, deleteTarget.session_id);
      setSessions((current) =>
        current.filter((session) => session.session_id !== deleteTarget.session_id),
      );
      setDeleteTarget(null);
    } catch (err) {
      setDeleteError((err as Error).message);
    } finally {
      setDeleting(false);
    }
  }

  function openSession(session: Session) {
    // Reopen a blueprint in the architecture-first canvas (not the legacy
    // session flow), carrying its name/description as context.
    const q = new URLSearchParams({
      bp: sessionTitle(session),
      desc: session.description || session.notes || '',
      type: 'coding',
      customer: id,
      session: session.session_id,
    });
    router.push(`/architecture?${q.toString()}`);
  }

  if (loading) {
    return (
      <div style={{ padding: 'var(--space-6)', maxWidth: 1180, margin: '0 auto' }}>
        <div className="skeleton" style={{ height: 88, marginBottom: 20 }} />
        <div className="skeleton" style={{ height: 260 }} />
      </div>
    );
  }

  return (
    <div className="blueprint-page">
      <Link href="/customers" className="blueprint-back">
        <ArrowLeft size={14} /> All customers
      </Link>

      {customer && (
        <header className="blueprint-header">
          <div style={{ minWidth: 0 }}>
            <h1 className="text-page-title">{customer.name}</h1>
            <div className="blueprint-customer-meta">
              <span>{customer.industry}</span>
              {customer.metadata?.region && <span>{customer.metadata.region}</span>}
              {customer.metadata?.company_size && <span>{customer.metadata.company_size}</span>}
              <span>{sessions.length} blueprint{sessions.length === 1 ? '' : 's'}</span>
            </div>
          </div>
          <Button size="md" onClick={openCreate}>
            <Plus size={15} /> New blueprint
          </Button>
        </header>
      )}

      {error && <div className="blueprint-error">{error}</div>}

      {sessions.length === 0 ? (
        <div className="card empty-state blueprint-empty">
          <div className="empty-state-icon"><FileText size={25} /></div>
          <div className="empty-state-title">No blueprints yet</div>
          <div className="empty-state-description">
            Create a named architecture assessment for this customer.
          </div>
          <Button onClick={openCreate}><Plus size={15} /> New blueprint</Button>
        </div>
      ) : (
        <section className="blueprint-list">
          <div className="blueprint-toolbar">
            <div className="blueprint-filters" aria-label="Filter blueprints">
              {([
                ['all', 'All'],
                ['in_progress', 'In progress'],
                ['complete', 'Complete'],
              ] as const).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  className={filter === value ? 'blueprint-filter active' : 'blueprint-filter'}
                  aria-pressed={filter === value}
                  onClick={() => setFilter(value)}
                >
                  {label} <span>{counts[value]}</span>
                </button>
              ))}
            </div>
            <label className="blueprint-sort">
              <span>Sort</span>
              <select value={sort} onChange={(event) => setSort(event.target.value as Sort)}>
                <option value="updated">Recently updated</option>
                <option value="title">Name</option>
                <option value="status">Status</option>
              </select>
            </label>
          </div>

          <div className="card blueprint-table-wrap">
            <table className="blueprint-table">
              <thead>
                <tr>
                  <th>
                    <button type="button" onClick={() => setSort('title')}>
                      Blueprint <ArrowUpDown size={12} />
                    </button>
                  </th>
                  <th className="col-workload">Workload</th>
                  <th>Status</th>
                  <th className="col-recommendation">Recommendation</th>
                  <th className="col-evidence">Evidence</th>
                  <th>
                    <button type="button" onClick={() => setSort('updated')}>
                      Updated <ArrowUpDown size={12} />
                    </button>
                  </th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {visibleSessions.map((session) => (
                  <tr
                    key={session.session_id}
                    tabIndex={0}
                    onClick={() => openSession(session)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        openSession(session);
                      }
                    }}
                  >
                    <td className="blueprint-name-cell">
                      <div className="blueprint-name">{sessionTitle(session)}</div>
                      <div className="blueprint-description">
                        {session.description || session.notes || 'No description'}
                      </div>
                    </td>
                    <td className="col-workload">
                      {workloadLabel(session.primary_workload)}
                    </td>
                    <td>
                      <div className="blueprint-status">
                        <Badge color={isComplete(session) ? 'green' : 'blue'}>
                          {statusLabel(session.status)}
                        </Badge>
                        {!isComplete(session) && (
                          <span>Step {Math.max(session.current_step, 1)} of 10</span>
                        )}
                      </div>
                    </td>
                    <td className="col-recommendation">
                      {session.recommendation
                        ? prettyPattern(session.recommendation)
                        : 'Not evaluated'}
                    </td>
                    <td className="col-evidence">
                      <EvidenceBadge state={session.evidence_state} />
                    </td>
                    <td className="blueprint-updated">{relativeTime(session.updated_at)}</td>
                    <td className="blueprint-actions-cell" onClick={(event) => event.stopPropagation()}>
                      <button
                        type="button"
                        className="blueprint-menu-trigger"
                        aria-label={`Actions for ${sessionTitle(session)}`}
                        aria-haspopup="menu"
                        aria-expanded={menuId === session.session_id}
                        onClick={(event) => {
                          event.stopPropagation();
                          setMenuId((current) =>
                            current === session.session_id ? null : session.session_id,
                          );
                        }}
                      >
                        <MoreHorizontal size={17} />
                      </button>
                      {menuId === session.session_id && (
                        <div
                          className="blueprint-menu"
                          role="menu"
                          onClick={(event) => event.stopPropagation()}
                        >
                          <button type="button" role="menuitem" onClick={() => openSession(session)}>
                            <ExternalLink size={14} /> Open
                          </button>
                          <button type="button" role="menuitem" onClick={() => openEdit(session)}>
                            <Pencil size={14} /> Edit details
                          </button>
                          <button type="button" role="menuitem" className="danger" onClick={() => openDelete(session)}>
                            <Trash2 size={14} /> Delete
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {visibleSessions.length === 0 && (
              <div className="blueprint-no-results">No blueprints match this filter.</div>
            )}
          </div>
        </section>
      )}

      <Modal open={createOpen} onClose={() => !creating && setCreateOpen(false)} title="New blueprint">
        <BlueprintForm
          form={createForm}
          setForm={setCreateForm}
          error={createError}
          submitting={creating}
          submitLabel="Create & open"
          onSubmit={handleCreate}
          onCancel={() => setCreateOpen(false)}
        />
      </Modal>

      <Modal open={!!editTarget} onClose={() => !saving && setEditTarget(null)} title="Edit blueprint details">
        <BlueprintForm
          form={editForm}
          setForm={setEditForm}
          error={editError}
          submitting={saving}
          submitLabel="Save changes"
          onSubmit={handleEdit}
          onCancel={() => setEditTarget(null)}
        />
      </Modal>

      <Modal open={!!deleteTarget} onClose={() => !deleting && setDeleteTarget(null)} title="Delete blueprint" size="sm">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Delete <strong style={{ color: 'var(--text-primary)' }}>{deleteTarget ? sessionTitle(deleteTarget) : ''}</strong>?
            This removes the intake and generated architecture and cannot be undone.
          </p>
          {deleteError && <div className="blueprint-error">{deleteError}</div>}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button variant="secondary" onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</Button>
            <Button variant="danger" onClick={handleDelete} loading={deleting}>Delete</Button>
          </div>
        </div>
      </Modal>

      <style jsx global>{`
        .blueprint-page {
          padding: var(--space-6);
          max-width: 1180px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: var(--space-5);
        }
        .blueprint-back {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          width: fit-content;
          font-size: var(--text-sm);
          color: var(--text-muted);
        }
        .blueprint-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: var(--space-4);
        }
        .blueprint-customer-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 6px 14px;
          margin-top: 6px;
          color: var(--text-muted);
          font-size: var(--text-xs);
        }
        .blueprint-customer-meta span:not(:first-child)::before {
          content: '·';
          margin-right: 14px;
          color: var(--border-strong);
        }
        .blueprint-list { display: flex; flex-direction: column; gap: var(--space-3); }
        .blueprint-toolbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: var(--space-3);
        }
        .blueprint-filters {
          display: inline-flex;
          padding: 3px;
          border: 1px solid var(--border-default);
          border-radius: var(--radius-sm);
          background: var(--bg-card);
        }
        .blueprint-filter {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          min-height: 32px;
          padding: 5px 10px;
          border: 0;
          border-radius: 6px;
          background: transparent;
          color: var(--text-secondary);
          font: inherit;
          font-size: var(--text-xs);
          cursor: pointer;
        }
        .blueprint-filter span {
          color: var(--text-muted);
          font-variant-numeric: tabular-nums;
        }
        .blueprint-filter.active {
          background: var(--accent-soft);
          color: var(--accent-deep);
          font-weight: 600;
        }
        .blueprint-sort {
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--text-muted);
          font-size: var(--text-xs);
        }
        .blueprint-sort select {
          min-height: 36px;
          padding: 5px 30px 5px 10px;
          border: 1px solid var(--border-default);
          border-radius: var(--radius-sm);
          background: var(--bg-card);
          color: var(--text-primary);
          font: inherit;
          cursor: pointer;
        }
        .blueprint-table-wrap { overflow: visible; }
        .blueprint-table {
          width: 100%;
          border-collapse: collapse;
          table-layout: fixed;
        }
        .blueprint-table th {
          padding: 9px 14px;
          border-bottom: 1px solid var(--border-default);
          color: var(--text-muted);
          font-size: 10px;
          font-weight: 600;
          letter-spacing: 0.06em;
          text-align: left;
          text-transform: uppercase;
        }
        .blueprint-table th:first-child { width: 30%; }
        .blueprint-table th:nth-child(2) { width: 15%; }
        .blueprint-table th:nth-child(3) { width: 15%; }
        .blueprint-table th:nth-child(4) { width: 14%; }
        .blueprint-table th:nth-child(5) { width: 13%; }
        .blueprint-table th:nth-child(6) { width: 9%; }
        .blueprint-table th:last-child { width: 44px; }
        .blueprint-table th button {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          border: 0;
          background: transparent;
          color: inherit;
          font: inherit;
          letter-spacing: inherit;
          text-transform: inherit;
          cursor: pointer;
        }
        .blueprint-table tbody tr {
          cursor: pointer;
          transition: background 0.12s;
        }
        .blueprint-table tbody tr:not(:last-child) td {
          border-bottom: 1px solid var(--border-subtle);
        }
        .blueprint-table tbody tr:hover,
        .blueprint-table tbody tr:focus-visible {
          background: var(--bg-sunken);
          outline: none;
        }
        .blueprint-table td {
          padding: 12px 14px;
          color: var(--text-secondary);
          font-size: var(--text-xs);
          vertical-align: middle;
        }
        .blueprint-name {
          overflow: hidden;
          color: var(--text-primary);
          font-size: var(--text-sm);
          font-weight: 600;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .blueprint-description {
          overflow: hidden;
          margin-top: 2px;
          color: var(--text-muted);
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .blueprint-status { display: flex; flex-direction: column; align-items: flex-start; gap: 3px; }
        .blueprint-status > span:last-child { color: var(--text-muted); font-size: 10px; }
        .blueprint-updated { white-space: nowrap; font-variant-numeric: tabular-nums; }
        .blueprint-actions-cell { position: relative; padding: 8px !important; text-align: right; }
        .blueprint-menu-trigger {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 30px;
          height: 30px;
          border: 1px solid transparent;
          border-radius: 6px;
          background: transparent;
          color: var(--text-muted);
          cursor: pointer;
        }
        .blueprint-menu-trigger:hover,
        .blueprint-menu-trigger[aria-expanded='true'] {
          border-color: var(--border-default);
          background: var(--bg-hover);
          color: var(--text-primary);
        }
        .blueprint-menu {
          position: absolute;
          z-index: 20;
          top: 38px;
          right: 8px;
          width: 158px;
          padding: 5px;
          border: 1px solid var(--border-default);
          border-radius: var(--radius-sm);
          background: var(--bg-elevated);
          box-shadow: var(--shadow-elevated);
        }
        .blueprint-menu button {
          display: flex;
          align-items: center;
          gap: 8px;
          width: 100%;
          padding: 8px 9px;
          border: 0;
          border-radius: 6px;
          background: transparent;
          color: var(--text-secondary);
          font: inherit;
          font-size: var(--text-xs);
          text-align: left;
          cursor: pointer;
        }
        .blueprint-menu button:hover { background: var(--bg-hover); color: var(--text-primary); }
        .blueprint-menu button.danger { color: var(--danger); }
        .blueprint-no-results {
          padding: var(--space-8);
          color: var(--text-muted);
          font-size: var(--text-sm);
          text-align: center;
        }
        .blueprint-error {
          padding: 9px 12px;
          border: 1px solid var(--danger);
          border-radius: var(--radius-sm);
          background: var(--danger-subtle);
          color: var(--danger);
          font-size: var(--text-sm);
        }
        .blueprint-empty { min-height: 300px; }
        @media (max-width: 900px) {
          .blueprint-table-wrap { overflow-x: auto; }
          .blueprint-table { min-width: 760px; }
          .col-recommendation { display: none; }
          .blueprint-table th:first-child { width: 34%; }
        }
        @media (max-width: 700px) {
          .blueprint-page { padding: var(--space-4); }
          .blueprint-header { align-items: stretch; flex-direction: column; }
          .blueprint-header > button { align-self: flex-start; }
          .blueprint-toolbar { align-items: stretch; flex-direction: column; }
          .blueprint-filters { width: 100%; }
          .blueprint-filter { flex: 1; justify-content: center; }
          .blueprint-sort { justify-content: space-between; }
          .blueprint-sort select { flex: 1; }
          .blueprint-table { min-width: 610px; }
          .col-workload, .col-evidence { display: none; }
        }
      `}</style>
    </div>
  );
}

function BlueprintForm({
  form,
  setForm,
  error,
  submitting,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  form: typeof EMPTY_FORM;
  setForm: React.Dispatch<React.SetStateAction<typeof EMPTY_FORM>>;
  error: string | null;
  submitting: boolean;
  submitLabel: string;
  onSubmit: (event: React.FormEvent) => void;
  onCancel: () => void;
}) {
  return (
    <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {error && <div className="blueprint-error">{error}</div>}
      <Input
        data-autofocus
        label="Blueprint name"
        placeholder="Customer service agent platform"
        value={form.title}
        maxLength={120}
        onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
      />
      <div>
        <Textarea
          label="Description"
          placeholder="What decision or platform scope should this blueprint address?"
          value={form.description}
          maxLength={500}
          onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
        />
        <div style={{ marginTop: 4, color: 'var(--text-muted)', fontSize: 10, textAlign: 'right' }}>
          {form.description.length}/500
        </div>
      </div>
      <div>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6, color: 'var(--text)' }}>
          Blueprint type
        </label>
        <select
          value={form.blueprintType}
          onChange={(event) => setForm((current) => ({ ...current, blueprintType: event.target.value }))}
          style={{
            width: '100%', padding: '10px 12px', borderRadius: 8,
            border: '1px solid var(--border)', background: 'var(--surface)',
            color: 'var(--text)', fontSize: 14, fontFamily: 'inherit',
          }}
        >
          {BLUEPRINT_TYPES.map((t) => (
            <option key={t.value} value={t.value} disabled={!t.available}>
              {t.label}{t.available ? '' : ' — coming soon'}
            </option>
          ))}
        </select>
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 2 }}>
        <Button type="button" variant="secondary" onClick={onCancel} disabled={submitting}>Cancel</Button>
        <Button type="submit" loading={submitting} disabled={!form.title.trim()}>{submitLabel}</Button>
      </div>
    </form>
  );
}

function EvidenceBadge({ state }: { state: EvidenceState }) {
  const color = {
    not_started: 'gray',
    provisional: 'orange',
    decision_ready: 'green',
    overridden: 'blue',
  }[state] as 'gray' | 'orange' | 'green' | 'blue';
  return <Badge color={color}>{evidenceLabel(state)}</Badge>;
}
