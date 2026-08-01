'use client';

import { useEffect, useMemo, useState } from 'react';
import snapshot from '@/data/architecture-workspace.json';
import {
  ArchitectureApiError,
  evaluateArchitectureWorkspace,
  getArchitectureWorkspace,
  normalizeArchitectureProjection,
  type ArchitectureWorkspaceScope,
} from '@/lib/architecture-api';
import type { RequirementValue } from '@/lib/architecture-workspace';
import { FlowWorkspace } from './FlowWorkspace';
import { PlatformTypeGate } from './PlatformTypeGate';

const initialProjection = normalizeArchitectureProjection(snapshot);
export type WorkspaceConnectionState = 'loading' | 'live' | 'snapshot' | 'stale';

export interface BlueprintContext {
  name: string;
  description: string;
  type: string;
}

export function ArchitectureWorkspaceLive() {
  const [platformType, setPlatformType] = useState<string | null>(null);
  const [blueprint, setBlueprint] = useState<BlueprintContext | null>(null);
  const [projection, setProjection] = useState(initialProjection);
  const [scope, setScope] = useState<ArchitectureWorkspaceScope | null | undefined>(undefined);
  const [applying, setApplying] = useState(false);
  const [connectionState, setConnectionState] = useState<WorkspaceConnectionState>('loading');

  // If the user arrived from "New blueprint" (agentic coding), the blueprint
  // name/description/type ride in the query string — skip the picker and open
  // straight into the canvas with that blueprint as context.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const type = params.get('type');
    const customerId = params.get('customer');
    const sessionId = params.get('session');
    setScope(customerId && sessionId
      ? { customer_id: customerId, session_id: sessionId }
      : null);
    if (type) {
      setBlueprint({
        name: params.get('bp') ?? 'Untitled blueprint',
        description: params.get('desc') ?? '',
        type,
      });
      setPlatformType(type);
    }
  }, []);
  const answers = useMemo(
    () => Object.fromEntries(
      projection.requirements
        .filter((requirement) => requirement.source === 'user')
        .map((requirement) => [requirement.id, requirement.value]),
    ),
    [projection.requirements],
  );

  async function reloadWorkspace() {
    if (!platformType || scope === undefined) return;
    setConnectionState('loading');
    try {
      const value = await getArchitectureWorkspace(scope ?? undefined);
      setProjection(value);
      setConnectionState('live');
    } catch {
      setProjection(initialProjection);
      setConnectionState('snapshot');
    }
  }

  useEffect(() => {
    if (!platformType || scope === undefined) return;
    getArchitectureWorkspace(scope ?? undefined)
      .then((value) => {
        setProjection(value);
        setConnectionState('live');
      })
      .catch(() => {
        setProjection(initialProjection);
        setConnectionState('snapshot');
      });
  }, [platformType, scope]);

  async function applyAnswers(
    nextAnswers: Record<string, RequirementValue>,
  ): Promise<boolean> {
    if (connectionState !== 'live') return false;
    setApplying(true);
    try {
      setProjection(await evaluateArchitectureWorkspace({
        answers: {
          ...answers,
          ...nextAnswers,
        },
        base_revision_number: projection.meta.persistence_revision,
        base_state_hash: projection.meta.persistence_hash,
      }, scope ?? undefined));
      setConnectionState('live');
      return true;
    } catch (error) {
      setConnectionState(
        error instanceof ArchitectureApiError && error.status === 409
          ? 'stale'
          : 'snapshot',
      );
      return false;
    } finally {
      setApplying(false);
    }
  }

  if (!platformType) {
    return (
      <PlatformTypeGate
        onSelect={(id) => {
          setBlueprint({ name: 'Untitled blueprint', description: '', type: id });
          setPlatformType(id);
        }}
      />
    );
  }

  if (connectionState === 'loading') {
    return (
      <div className="flex h-full min-h-[360px] items-center justify-center bg-[#0e1116] text-sm text-[#8b98ab]" role="status">
        Loading the current architecture revision...
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      {connectionState !== 'live' && (
        <div className="flex items-center justify-center gap-3 bg-[#241c0f] px-4 py-2 text-center text-[11px] text-[#f0a850]" role="alert">
          <span>
            {connectionState === 'stale'
              ? 'This revision is stale. Reload before making or publishing changes.'
              : 'Read-only snapshot. The live engine is unreachable; changes and package export are disabled.'}
          </span>
          <button
            type="button"
            className="rounded border border-[#f0a85066] px-2 py-0.5 font-semibold"
            onClick={reloadWorkspace}
          >
            Reload
          </button>
        </div>
      )}
      <FlowWorkspace
        projection={projection}
        blueprint={blueprint}
        onApplyPatch={applyAnswers}
        scope={scope ?? undefined}
        applying={applying}
        connectionState={connectionState}
        onReload={reloadWorkspace}
      />
    </div>
  );
}
