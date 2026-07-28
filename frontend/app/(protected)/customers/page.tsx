'use client';
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Plus, Building2, Search, X } from 'lucide-react';
import { listCustomers, createCustomer, listSessions } from '@/lib/api';
import type { Customer, Session } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { relativeTime, statusLabel, isComplete } from '@/lib/session-format';

const INDUSTRIES = ['Financial Services', 'Healthcare', 'Insurance', 'Retail', 'Manufacturing', 'Technology', 'Government', 'Other'];
const COMPANY_SIZES = ['Startup', 'Mid-market', 'Enterprise'];
const REGIONS = ['US', 'EU', 'APAC', 'Global'];

type SortKey = 'recent' | 'name' | 'sessions';

// Latest-session-derived engagement status for a customer.
interface Engagement { label: string; color: 'green' | 'orange' | 'gray' }

function engagementFor(sessions: Session[] | undefined): Engagement {
  if (!sessions || sessions.length === 0) return { label: 'No blueprints', color: 'gray' };
  const latest = [...sessions].sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at))[0];
  if (isComplete(latest)) {
    const done = sessions.filter(isComplete).length;
    return { label: `${done} complete`, color: 'green' };
  }
  return { label: `In progress · ${statusLabel(latest.status)}`, color: 'orange' };
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [sessionsByCust, setSessionsByCust] = useState<Record<string, Session[]>>({});
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', industry: 'Technology', region: 'US', company_size: 'Enterprise' });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Controls
  const [query, setQuery] = useState('');
  const [industryFilter, setIndustryFilter] = useState('All');
  const [sort, setSort] = useState<SortKey>('recent');

  useEffect(() => {
    listCustomers()
      .then(async (custs) => {
        setCustomers(custs);
        setLoading(false);
        // Fetch sessions in the background to derive status pills.
        const entries = await Promise.all(
          custs.map((c) =>
            listSessions(c.customer_id).then((s) => [c.customer_id, s] as const).catch(() => [c.customer_id, []] as const),
          ),
        );
        setSessionsByCust(Object.fromEntries(entries));
      })
      .catch((e) => { console.error(e); setLoading(false); });
  }, []);

  async function handleCreate() {
    setCreating(true);
    setCreateError(null);
    try {
      const c = await createCustomer({
        name: form.name,
        industry: form.industry,
        metadata: { region: form.region, company_size: form.company_size },
      });
      setCustomers((prev) => [c, ...prev]);
      setShowCreate(false);
      setForm({ name: '', industry: 'Technology', region: 'US', company_size: 'Enterprise' });
    } catch (err) {
      setCreateError((err as Error).message);
    } finally {
      setCreating(false);
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
      <Link key={c.customer_id} href={`/customers/${c.customer_id}`} style={{ textDecoration: 'none' }}>
        <Card hover style={{ padding: 'var(--space-4)', height: '100%', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
            <div style={{ fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--text-primary)' }}>{c.name}</div>
            <Badge color={eng.color}>{eng.label}</Badge>
          </div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
            {[c.industry, c.metadata?.region, c.metadata?.company_size].filter(Boolean).join(' · ')}
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-4)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 'auto' }}>
            <span>{c.session_count ?? 0} blueprint{c.session_count === 1 ? '' : 's'}</span>
            <span>Updated {relativeTime(c.updated_at)}</span>
          </div>
        </Card>
      </Link>
    );
  };

  return (
    <div style={{ padding: 'var(--space-6)', maxWidth: 1400, margin: '0 auto' }}>
      {/* Title */}
      <div style={{ marginBottom: 'var(--space-5)' }}>
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)' }}>Customers</h1>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginTop: 2 }}>
          {loading ? '…' : `${customers.length} customer${customers.length !== 1 ? 's' : ''}`}
          {!loading && (query || industryFilter !== 'All') && visible.length !== customers.length
            ? ` · ${visible.length} shown` : ''}
        </p>
      </div>

      {/* Single toolbar: search · filters · new customer */}
      {!loading && customers.length > 0 && (
        <div className="cust-toolbar">
          <div className="cust-search">
            <Search size={15} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search customers"
            />
            {query && (
              <button className="cust-search-clear" onClick={() => setQuery('')} aria-label="Clear search">
                <X size={13} />
              </button>
            )}
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
          <Button size="md" onClick={() => setShowCreate(true)}>
            <Plus size={16} /> New customer
          </Button>
        </div>
      )}

      {/* Grid */}
      {loading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(260px,1fr))', gap: 'var(--space-3)' }}>
          {[1, 2, 3, 4].map((i) => <div key={i} className="skeleton" style={{ height: 120 }} />)}
        </div>
      ) : customers.length === 0 ? (
        <Card style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
          <Building2 size={40} style={{ margin: '0 auto var(--space-3)', color: 'var(--text-muted)', opacity: 0.4 }} />
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
            No customers yet.
          </p>
          <Button onClick={() => setShowCreate(true)}><Plus size={16} /> Add your first customer</Button>
        </Card>
      ) : visible.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
          No customers match your filters.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(260px,1fr))', gap: 'var(--space-3)' }}>
          {visible.map(renderCard)}
        </div>
      )}

      {/* Create modal */}
      <Modal open={showCreate} onClose={() => { setShowCreate(false); setCreateError(null); }} title="New customer">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {createError && (
            <div style={{ padding: '8px 12px', borderRadius: 'var(--radius-sm)', background: 'var(--danger-subtle)', border: '1px solid var(--danger)', color: 'var(--danger)', fontSize: 'var(--text-sm)' }}>
              {createError}
            </div>
          )}
          <Input
            label="Customer / company name"
            placeholder="Acme Corp"
            value={form.name}
            error={!form.name.trim() && createError ? 'Name is required' : undefined}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <label className="ctrl-field">
              <span>Industry</span>
              <select value={form.industry} onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))} className="ctrl-input">
                {INDUSTRIES.map((i) => <option key={i}>{i}</option>)}
              </select>
            </label>
            <label className="ctrl-field">
              <span>Region</span>
              <select value={form.region} onChange={(e) => setForm((f) => ({ ...f, region: e.target.value }))} className="ctrl-input">
                {REGIONS.map((r) => <option key={r}>{r}</option>)}
              </select>
            </label>
          </div>
          <label className="ctrl-field">
            <span>Company size</span>
            <select value={form.company_size} onChange={(e) => setForm((f) => ({ ...f, company_size: e.target.value }))} className="ctrl-input">
              {COMPANY_SIZES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
          <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'flex-end', marginTop: 4 }}>
            <Button variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button variant="primary" onClick={handleCreate} loading={creating} disabled={!form.name.trim()}>
              Create customer
            </Button>
          </div>
        </div>
      </Modal>

      <style jsx global>{`
        /* Toolbar */
        .cust-toolbar {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          margin-bottom: var(--space-5);
          flex-wrap: wrap;
        }
        .cust-search {
          display: flex;
          align-items: center;
          gap: 8px;
          flex: 1;
          min-width: 240px;
          max-width: 380px;
          height: 38px;
          padding: 0 10px;
          background: var(--bg-card);
          border: 1px solid var(--border-default);
          border-radius: var(--radius-sm);
          color: var(--text-muted);
          transition: border-color 0.15s, box-shadow 0.15s;
        }
        .cust-search:focus-within {
          border-color: var(--accent);
          box-shadow: 0 0 0 3px var(--accent-subtle);
          color: var(--text-secondary);
        }
        .cust-search input {
          flex: 1;
          background: none;
          border: none;
          outline: none;
          color: var(--text-primary);
          font-size: var(--text-sm);
        }
        .cust-search input::placeholder { color: var(--text-muted); }
        .cust-search-clear {
          display: inline-flex; align-items: center; justify-content: center;
          background: none; border: none; cursor: pointer;
          color: var(--text-muted); padding: 2px; border-radius: var(--radius-sm);
        }
        .cust-search-clear:hover { color: var(--text-primary); background: var(--bg-hover); }
        /* Segmented select: label + native select styled as one pill */
        .cust-select {
          display: flex;
          align-items: center;
          height: 38px;
          background: var(--bg-card);
          border: 1px solid var(--border-default);
          border-radius: var(--radius-sm);
          overflow: hidden;
          transition: border-color 0.15s;
        }
        .cust-select:hover { border-color: var(--border-strong); }
        .cust-select > span {
          font-size: var(--text-xs);
          color: var(--text-muted);
          padding: 0 4px 0 12px;
          white-space: nowrap;
        }
        .cust-select select {
          height: 100%;
          background: none;
          border: none;
          outline: none;
          color: var(--text-primary);
          font-size: var(--text-sm);
          padding: 0 12px 0 4px;
          cursor: pointer;
          appearance: none;
        }
        .cust-select select option { background: var(--bg-elevated); }
        /* Modal form controls */
        .ctrl-input {
          background: var(--bg-elevated);
          border: 1px solid var(--border-default);
          border-radius: var(--radius-sm);
          color: var(--text-primary);
          padding: 8px 12px;
          font-size: var(--text-sm);
          outline: none;
          width: 100%;
          transition: border-color 0.15s, box-shadow 0.15s;
        }
        .ctrl-input::placeholder { color: var(--text-muted); }
        .ctrl-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-subtle); }
        .ctrl-field { display: flex; flex-direction: column; gap: 6px; font-size: var(--text-sm); color: var(--text-secondary); font-weight: 500; }
      `}</style>
    </div>
  );
}
