"use client";

import { useEffect, useState } from "react";
import { Users, Activity, CheckCircle, TrendingUp } from "lucide-react";
import { Card, Badge } from "@/components/ui";
import { fetchAdminMetrics } from "@/lib/api";

// Matches the shape returned by GET /admin/metrics
interface DashboardMetrics {
  total_customers: number;
  total_sessions: number;
  active_sessions: number;
  sessions_today: number;
  top_patterns: { pattern: string; count: number }[];
  top_industries: { industry: string; count: number }[];
}

const STAT_CARDS = [
  { key: "total_customers", label: "Total Customers", icon: Users,       color: "text-blue-400" },
  { key: "total_sessions",  label: "Total Sessions",  icon: Activity,    color: "text-green-400" },
  { key: "active_sessions", label: "Active Now",      icon: CheckCircle, color: "text-yellow-400" },
  { key: "sessions_today",  label: "Today",           icon: TrendingUp,  color: "text-purple-400" },
] as const;

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAdminMetrics()
      .then((data) => setMetrics(data as unknown as DashboardMetrics))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-8 space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-[var(--bg-card)] animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <Card className="border-red-500/30 bg-red-950/20 p-6">
          <p className="text-red-400">Failed to load metrics: {error}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Analytics</h1>
        <p className="text-sm text-[var(--text-muted)] mt-1">
          Platform usage metrics and system health
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STAT_CARDS.map(({ key, label, icon: Icon, color }) => (
          <Card key={key} className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">
                  {label}
                </p>
                <p className="text-3xl font-bold text-[var(--text-primary)]">
                  {(metrics?.[key as keyof DashboardMetrics] as number) ?? 0}
                </p>
              </div>
              <Icon className={`w-5 h-5 ${color}`} />
            </div>
          </Card>
        ))}
      </div>

      {/* Top Patterns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h2 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-4">
            Top Architecture Patterns
          </h2>
          {metrics?.top_patterns && metrics.top_patterns.length > 0 ? (
            <ul className="space-y-3">
              {metrics.top_patterns.map((p) => (
                <li key={p.pattern} className="flex items-center justify-between">
                  <span className="text-sm text-[var(--text-primary)]">{p.pattern}</span>
                  <Badge color="blue">{p.count}</Badge>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-[var(--text-muted)]">No sessions completed yet.</p>
          )}
        </Card>

        <Card className="p-6">
          <h2 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-4">
            Top Industries
          </h2>
          {metrics?.top_industries && metrics.top_industries.length > 0 ? (
            <ul className="space-y-3">
              {metrics.top_industries.map((ind) => (
                <li key={ind.industry} className="flex items-center justify-between">
                  <span className="text-sm text-[var(--text-primary)]">{ind.industry}</span>
                  <Badge color="green">{ind.count}</Badge>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-[var(--text-muted)]">No sessions completed yet.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
