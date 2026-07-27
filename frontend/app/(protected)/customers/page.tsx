'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, Building2, Calendar } from 'lucide-react';
import { listCustomers, createCustomer } from '@/lib/api';
import type { Customer } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', industry: 'Technology' });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    listCustomers()
      .then(setCustomers)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate() {
    setCreating(true);
    setCreateError(null);
    try {
      const c = await createCustomer(form);
      setCustomers((prev) => [c, ...prev]);
      setShowCreate(false);
      setForm({ name: '', industry: 'Technology' });
    } catch (err) {
      setCreateError((err as Error).message);
    } finally {
      setCreating(false);
    }
  }

  const INDUSTRIES = ['Financial Services', 'Healthcare', 'Insurance', 'Retail', 'Manufacturing', 'Technology', 'Government', 'Other'];
  const industryColor = (ind: string) => {
    const map: Record<string, 'blue' | 'green' | 'orange' | 'purple' | 'cyan' | 'gray'> = {
      'Financial Services': 'green', 'Healthcare': 'blue', 'Insurance': 'orange',
      'Technology': 'purple', 'Retail': 'cyan', default: 'gray',
    } as const;
    return map[ind] ?? 'gray';
  };

  return (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)' }}>Customers</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
            {loading ? '…' : `${customers.length} customer${customers.length !== 1 ? 's' : ''}`}
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus size={14} /> New Customer
        </Button>
      </div>

      {/* Grid */}
      {loading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))', gap: 14 }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton" style={{ height: 140, borderRadius: 12 }} />
          ))}
        </div>
      ) : customers.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 64, color: 'var(--text-muted)' }}>
          <Building2 size={40} style={{ margin: '0 auto 12px', opacity: 0.3 }} />
          <p style={{ fontSize: 14 }}>No customers yet. Create your first one.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))', gap: 14 }}>
          {customers.map((c) => (
            <Link key={c.customer_id} href={`/customers/${c.customer_id}`} style={{ textDecoration: 'none' }}>
              <Card
                hover
                style={{ padding: 18, cursor: 'pointer', height: '100%', display: 'flex', flexDirection: 'column', gap: 12 }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>{c.name}</div>
                    <Badge color={industryColor(c.industry)} size="sm">{c.industry}</Badge>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-muted)', marginTop: 'auto' }}>
                  <span>{c.session_count ?? 0} session{c.session_count !== 1 ? 's' : ''}</span>
                  <span>{new Date(c.updated_at).toLocaleDateString()}</span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {/* Create modal */}
      <Modal open={showCreate} onClose={() => { setShowCreate(false); setCreateError(null); }} title="New Customer">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {createError && (
            <div style={{ padding: '8px 12px', borderRadius: 6, background: 'rgba(255,80,80,0.1)', border: '1px solid rgba(255,80,80,0.3)', color: '#ff5050', fontSize: 13 }}>
              {createError}
            </div>
          )}
          <Input
            label="Customer / Company Name"
            placeholder="Acme Corp"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500 }}>Industry</label>
            <select
              value={form.industry}
              onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))}
              style={{
                background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
                padding: '8px 12px', fontSize: 14, outline: 'none',
              }}
            >
              {INDUSTRIES.map((i) => <option key={i}>{i}</option>)}
            </select>
          </div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
            <Button variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button
              variant="primary"
              onClick={handleCreate}
              loading={creating}
              disabled={!form.name.trim()}
            >
              Create Customer
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
