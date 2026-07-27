"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Database, GitBranch } from "lucide-react";
import { Card, Button, Badge } from "@/components/ui";
import { fetchGraphStats, reloadGraph } from "@/lib/api";

interface GraphStats {
  total_nodes: number;
  total_edges: number;
  node_types: Record<string, number>;
  edge_types: Record<string, number>;
}

export default function AdminConfig() {
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloading, setReloading] = useState(false);
  const [reloadMsg, setReloadMsg] = useState("");

  const loadStats = () => {
    setLoading(true);
    fetchGraphStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadStats(); }, []);

  const handleReload = async () => {
    setReloading(true);
    setReloadMsg("");
    try {
      const result = await reloadGraph();
      setReloadMsg(`Graph reloaded — ${result.nodes} nodes, ${result.edges} edges`);
      loadStats();
    } catch (e: unknown) {
      setReloadMsg(`Error: ${(e as Error).message}`);
    } finally {
      setReloading(false);
    }
  };

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Configuration</h1>
        <p className="text-sm text-[var(--text-muted)] mt-1">Knowledge graph and system settings</p>
      </div>

      {/* Knowledge Graph card */}
      <Card className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <GitBranch className="w-5 h-5 text-blue-400" />
            <h2 className="font-semibold text-[var(--text-primary)]">Knowledge Graph</h2>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleReload}
            loading={reloading}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Hot Reload
          </Button>
        </div>

        {reloadMsg && (
          <p className="text-sm text-green-400 bg-green-950/30 border border-green-500/20 rounded px-3 py-2">
            {reloadMsg}
          </p>
        )}

        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-8 rounded bg-[var(--bg-elevated)] animate-pulse" />
            ))}
          </div>
        ) : stats ? (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-[var(--bg-elevated)] rounded-lg p-4">
                <p className="text-xs text-[var(--text-muted)] mb-1">Total Nodes</p>
                <p className="text-2xl font-bold text-[var(--text-primary)]">{stats.total_nodes}</p>
              </div>
              <div className="bg-[var(--bg-elevated)] rounded-lg p-4">
                <p className="text-xs text-[var(--text-muted)] mb-1">Total Edges</p>
                <p className="text-2xl font-bold text-[var(--text-primary)]">{stats.total_edges}</p>
              </div>
            </div>

            <div>
              <p className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider mb-3">
                Node Types
              </p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(stats.node_types).map(([type, count]) => (
                  <div
                    key={type}
                    className="flex items-center gap-2 bg-[var(--bg-elevated)] rounded px-3 py-1.5"
                  >
                    <span className="text-sm text-[var(--text-primary)]">{type}</span>
                    <Badge color="blue" className="text-xs">{count}</Badge>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider mb-3">
                Edge Types
              </p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(stats.edge_types).map(([type, count]) => (
                  <div
                    key={type}
                    className="flex items-center gap-2 bg-[var(--bg-elevated)] rounded px-3 py-1.5"
                  >
                    <span className="text-xs text-[var(--text-secondary)] font-mono">{type}</span>
                    <Badge color="gray" className="text-xs">{count}</Badge>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-[var(--text-muted)]">Failed to load graph stats.</p>
        )}
      </Card>

      {/* Local Dev Info */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Database className="w-5 h-5 text-purple-400" />
          <h2 className="font-semibold text-[var(--text-primary)]">Local Environment</h2>
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-[var(--text-muted)]">DynamoDB Local</span>
            <span className="text-[var(--text-secondary)] font-mono">localhost:8000</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[var(--text-muted)]">DynamoDB Admin UI</span>
            <span className="text-[var(--text-secondary)] font-mono">localhost:8001</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[var(--text-muted)]">API Server</span>
            <span className="text-[var(--text-secondary)] font-mono">localhost:8080</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[var(--text-muted)]">Frontend</span>
            <span className="text-[var(--text-secondary)] font-mono">localhost:3000</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
