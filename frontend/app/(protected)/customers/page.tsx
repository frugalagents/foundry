'use client';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Building2, Search, X, Pencil, Trash2 } from 'lucide-react';
import { listCustomers, createCustomer, updateCustomer, deleteCustomer, listSessions } from '@/lib/api';
import type { Customer, Session } from '@/lib/types';
import { Badge, Button, Input, Modal } from '@/components/ui';
import { relativeTime, statusLabel, isComplete } from '@/lib/session-format';

const INDUSTRIES = ['Financial Services', 'Healthcare', 'Insurance', 'Retail', 'Manufacturing', 'Technology', 'Government', 'Other'];
const COMPANY_SIZES = ['Startup', 'Mid-market', 'Enterprise'];
const REGIONS = ['US', 'EU', 'APAC', 'Global'];

type SortKey = 'recent' | 'name' | 'sessions';
interface Engagement { label: string; color: 'green' | 'orange' | 'gray' }

function engagementFor(sessions: Session[] | undefined): Engagement {
  if (!sessions || sessions.length === 0) return { label: 'No blueprints', color: 'gray' };
  const latest = [...sessions].sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at))[0];
  if (isComplete(latest)) return { label: `${sessions.filter(isComplete).length} complete`, color: 'green' };
  return { label: `In progress · ${statusLabel(latest.status)}`, color: 'orange' };
}

const emptyForm = { name: '', industry: 'Technology', region: 'US', company_size: 'Enterprise' };

export default function CustomersPage() {
  const router = useRouter();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [sessionsByCust, setSessionsByCust] = useState<Record<string, Session[]>>({});
  const [loading, setLoading] = useState(true);

  // Create / edit modal (edit when editing != null)
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Customer | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<Customer | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Controls
  const [query, setQuery] = useState('');
  const [industryFilter, setIndustryFilter] = useState('All');
  const [sort, setSort] = useState<SortKey>('recent');

  useEffect(() => {
    listCustomers()
      .then(async (custs) => {
        setCustomers(custs);
        setLoading(false);
        const entries = await Promise.all(
          custs.map((c) =>
            listSessions(c.customer_id).then((s) => [c.customer_id, s] as const).catch(() => [c.customer_id, []] as const),
          ),
        );
        setSessionsByCust(Object.fromEntries(entries));
      })
      .catch(() => setLoading(false));
  }, []);

  function openCreate() {
    setEditing(null); setForm(emptyForm); setFormError(null); setShowForm(true);
  }
  function openEdit(c: Customer, e: React.MouseEvent) {
    e.preventDefault(); e.stopPropagation();
    setEditing(c);
    setForm({ name: c.name, industry: c.industry, region: c.metadata?.region || 'US', company_size: c.metadata?.company_size || 'Enterprise' });
    setFormError(null); setShowForm(true);
  }

  async function handleSave() {
    if (!form.name.trim()) { setFormError('Name is required'); return; }
    setSaving(true); setFormError(null);
    try {
      if (editing) {
        const updated = await updateCustomer(editing.customer_id, {
          name: form.name, industry: form.industry,
          metadata: { ...editing.metadata, region: form.region, company_size: form.company_size },
        });
        setCustomers((prev) => prev.map((c) => (c.customer_id === editing.customer_id ? updated : c)));
        setShowForm(false);
      } else {
        const c = await createCustomer({
          name: form.name, industry: form.industry,
          metadata: { region: form.region, company_size: form.company_size },
        });
        router.push(`/customers/${c.customer_id}`);
      }
    } catch (err) {
      setFormError((err as Error).message);
      setSaving(false);
    }
  }

  function openDelete(c: Customer, e: React.MouseEvent) {
    e.preventDefault(); e.stopPropagation();
    setDeleteTarget(c);
    setDeleteError(null);
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteCustomer(deleteTarget.customer_id);
      setCustomers((prev) => prev.filter((c) => c.customer_id !== deleteTarget.customer_id));
      setSessionsByCust((prev) => {
        const next = { ...prev };
        delete next[deleteTarget.customer_id];
        return next;
      });
      setDeleteTarget(null);
    } catch (err) {
      setDeleteError((err as Error).message);
    } finally {
      setDeleting(false);
    }
  }

  const visible = useMemo(() => {
    let list = customers;
    if (query.trim()) list = list.filter((c) => c.name.toLowerCase().includes(query.toLowerCase()));
    if (industryFilter !== 'All') list = list.filter((c) => c.industry === industryFilter);
    const sorted = [...list];
    if (sort === 'recent') sorted.sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at));
    else if (sort === 'name') sorted.sort((a, b) => a.name.localeCompare(b.name));
    else sorted.sort((a, b) => (b.session_count ?? 0) - (a.session_count ?? 0));
    return sorted;
  }, [customers, query, industryFilter, sort]);

  const renderCard = (c: Customer) => {
    const eng = engagementFor(sessionsByCust[c.customer_id]);
    return (
      <div key={c.customer_id} className="cust-card" onClick={() => router.push(`/customers/${c.customer_id}`)}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
          <div style={{ minWidth: 0 }}>
            <div className="text-display" style={{ fontSize: 'var(--text-lg)', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.name}</div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 2 }}>
              {[c.industry, c.metadata?.region, c.metadata?.company_size].filter(Boolean).join(' · ')}
            </div>
          </div>
          <div className="cust-actions">
            <button className="icon-btn" onClick={(e) => openEdit(c, e)} aria-label="Edit"><Pencil size={14} /></button>
            <button className="icon-btn icon-btn--danger" onClick={(e) => openDelete(c, e)} aria-label="Delete"><Trash2 size={14} /></button>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 'var(--space-4)' }}>
          <Badge color={eng.color}>{eng.label}</Badge>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
            {c.session_count ?? 0} bp · {relativeTime(c.updated_at)}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: 'var(--space-6)', maxWidth: 1180, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
      {/* Title */}
      <div className="animate-fade-up">
        <h1 className="text-page-title">Customers</h1>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginTop: 4 }}>
          {loading ? '…' : `${customers.length} customer${customers.length !== 1 ? 's' : ''}`}
          {!loading && (query || industryFilter !== 'All') && visible.length !== customers.length ? ` · ${visible.length} shown` : ''}
        </p>
      </div>

      {/* Toolbar */}
      {!loading && customers.length > 0 && (
        <div className="animate-fade-up stagger-1 cust-toolbar">
          <div className="cust-search">
            <Search size={15} />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search customers" />
            {query && <button className="cust-search-clear" onClick={() => setQuery('')} aria-label="Clear"><X size={13} /></button>}
          </div>
          <div className="cust-select">
            <span>Industry</span>
            <select value={industryFilter} onChange={(e) => setIndustryFilter(e.target.value)}>
              <option>All</option>
              {INDUSTRIES.map((i) => <option key={i}>{i}</option>)}
            </select>
          </div>
          <div className="cust-select">
            <span>Sort</span>
            <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
              <option value="recent">Recently active</option>
              <option value="name">Name (A–Z)</option>
              <option value="sessions">Most blueprints</option>
            </select>
          </div>
          <div style={{ flex: 1 }} />
          <Button onClick={openCreate}><Plus size={16} /> New customer</Button>
        </div>
      )}

      {/* Grid */}
      {loading ? (
        <div className="cust-grid">{[1, 2, 3, 4].map((i) => <div key={i} className="skeleton" style={{ height: 128 }} />)}</div>
      ) : customers.length === 0 ? (
        <div className="card empty-state">
          <div className="empty-state-icon"><Building2 size={26} /></div>
          <div className="empty-state-title">No customers yet</div>
          <div className="empty-state-description">Add your first customer to start an advisory engagement.</div>
          <Button onClick={openCreate}><Plus size={16} /> New customer</Button>
        </div>
      ) : visible.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
          No customers match your filters.
        </div>
      ) : (
        <div className="cust-grid animate-fade-up stagger-2">{visible.map(renderCard)}</div>
      )}

      {/* Create / edit modal */}
      <Modal open={showForm} onClose={() => setShowForm(false)} title={editing ? 'Edit customer' : 'New customer'}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {formError && (
            <div style={{ padding: '8px 12px', borderRadius: 'var(--radius-sm)', background: 'var(--danger-subtle)', border: '1px solid var(--danger)', color: 'var(--danger)', fontSize: 'var(--text-sm)' }}>
              {formError}
            </div>
          )}
          <Input
            data-autofocus
            label="Customer / company name"
            placeholder="Acme Corp"
            autoComplete="organization"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <label className="ctrl-field"><span>Industry</span>
              <select value={form.industry} onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))} className="input-field">
                {INDUSTRIES.map((i) => <option key={i}>{i}</option>)}
              </select>
            </label>
            <label className="ctrl-field"><span>Region</span>
              <select value={form.region} onChange={(e) => setForm((f) => ({ ...f, region: e.target.value }))} className="input-field">
                {REGIONS.map((r) => <option key={r}>{r}</option>)}
              </select>
            </label>
          </div>
          <label className="ctrl-field"><span>Company size</span>
            <select value={form.company_size} onChange={(e) => setForm((f) => ({ ...f, company_size: e.target.value }))} className="input-field">
              {COMPANY_SIZES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
          <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'flex-end', marginTop: 4 }}>
            <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button type="button" onClick={handleSave} disabled={!form.name.trim()} loading={saving}>
              {saving ? 'Saving…' : editing ? 'Save changes' : 'Create & open'}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        open={!!deleteTarget}
        onClose={() => !deleting && setDeleteTarget(null)}
        title="Delete customer"
        size="sm"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Delete <strong style={{ color: 'var(--text-primary)' }}>{deleteTarget?.name}</strong>?
            This permanently removes the customer,{' '}
            {sessionsByCust[deleteTarget?.customer_id ?? '']?.length ?? deleteTarget?.session_count ?? 0}
            {' '}associated blueprint(s), and all generated panels.
          </p>
          {deleteError && (
            <div style={{ padding: '8px 12px', borderRadius: 'var(--radius-sm)', background: 'var(--danger-subtle)', border: '1px solid var(--danger)', color: 'var(--danger)', fontSize: 'var(--text-sm)' }}>
              {deleteError}
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button variant="secondary" onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</Button>
            <Button variant="danger" onClick={handleDelete} loading={deleting}>
              <Trash2 size={15} /> Delete customer
            </Button>
          </div>
        </div>
      </Modal>

      <style jsx global>{`
        .cust-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--space-4); }
        .cust-card {
          background: var(--bg-card); border: 1px solid var(--border-default);
          border-radius: var(--radius-lg); padding: var(--space-5);
          cursor: pointer; transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
        }
        .cust-card:hover {
          border-color: var(--border-accent);
          box-shadow: 0 0 0 1px rgba(47,122,115,0.12), 0 6px 20px rgba(31,30,27,0.06);
          transform: translateY(-1px);
        }
        .cust-actions { display: flex; gap: 4px; opacity: 0; transition: opacity 0.15s; flex-shrink: 0; }
        .cust-card:hover .cust-actions { opacity: 1; }
        .icon-btn {
          display: inline-flex; align-items: center; justify-content: center;
          width: 28px; height: 28px; background: none; border: 1px solid transparent;
          border-radius: var(--radius-sm); color: var(--text-muted); cursor: pointer;
          transition: background 0.15s, color 0.15s, border-color 0.15s;
        }
        .icon-btn:hover { background: var(--bg-hover); color: var(--text-primary); border-color: var(--border-default); }
        .icon-btn--danger:hover { color: var(--danger); }
        .cust-toolbar { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
        .cust-search {
          display: flex; align-items: center; gap: 8px; flex: 1; min-width: 240px; max-width: 380px;
          height: 40px; padding: 0 12px; background: var(--bg-card);
          border: 1px solid var(--border-default); border-radius: var(--radius-sm);
          color: var(--text-muted); transition: border-color 0.15s, box-shadow 0.15s;
        }
        .cust-search:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-subtle); color: var(--text-secondary); }
        .cust-search input { flex: 1; background: none; border: none; outline: none; color: var(--text-primary); font-size: var(--text-sm); }
        .cust-search input::placeholder { color: var(--text-muted); }
        .cust-search-clear { display: inline-flex; align-items: center; justify-content: center; background: none; border: none; cursor: pointer; color: var(--text-muted); padding: 2px; border-radius: var(--radius-sm); }
        .cust-search-clear:hover { color: var(--text-primary); background: var(--bg-hover); }
        .cust-select {
          display: flex; align-items: center; height: 40px;
          background: var(--bg-card); border: 1px solid var(--border-default);
          border-radius: var(--radius-sm); overflow: hidden; transition: border-color 0.15s;
        }
        .cust-select:hover { border-color: var(--border-strong); }
        .cust-select > span { font-size: var(--text-xs); color: var(--text-muted); padding: 0 4px 0 12px; white-space: nowrap; }
        .cust-select select { height: 100%; background: none; border: none; outline: none; color: var(--text-primary); font-size: var(--text-sm); padding: 0 12px 0 4px; cursor: pointer; appearance: none; }
        .cust-select select option { background: var(--bg-elevated); }
        .ctrl-field { display: flex; flex-direction: column; gap: 6px; font-size: var(--text-sm); color: var(--text-secondary); font-weight: 500; }
      `}</style>
    </div>
  );
}
