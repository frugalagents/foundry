'use client';

import { useEffect, useMemo, useState } from 'react';
import snapshot from '@/data/architecture-workspace.json';
import {
  evaluateArchitectureWorkspace,
  getArchitectureWorkspace,
  normalizeArchitectureProjection,
} from '@/lib/architecture-api';
import type { RequirementValue } from '@/lib/architecture-workspace';
import { FlowWorkspace } from './FlowWorkspace';
import { PlatformTypeGate } from './PlatformTypeGate';

const initialProjection = normalizeArchitectureProjection(snapshot);

export interface BlueprintContext {
  name: string;
  description: string;
  type: string;
}

export function ArchitectureWorkspaceLive() {
  const [platformType, setPlatformType] = useState<string | null>(null);
  const [blueprint, setBlueprint] = useState<BlueprintContext | null>(null);
  const [projection, setProjection] = useState(initialProjection);
  const [applying, setApplying] = useState(false);
  const [offline, setOffline] = useState(false);

  // If the user arrived from "New blueprint" (agentic coding), the blueprint
  // name/description/type ride in the query string — skip the picker and open
  // straight into the canvas with that blueprint as context.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const type = params.get('type');
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

  useEffect(() => {
    if (!platformType) return;
    getArchitectureWorkspace()
      .then((value) => {
        setProjection(value);
        setOffline(false);
      })
      .catch(() => setOffline(true));
  }, [platformType]);

  async function applyAnswer(requirementId: string, answer: RequirementValue) {
    setApplying(true);
    try {
      setProjection(await evaluateArchitectureWorkspace({
        answers: {
          ...answers,
          [requirementId]: answer,
        },
        base_revision_number: projection.meta.persistence_revision,
        base_state_hash: projection.meta.persistence_hash,
      }));
      setOffline(false);
    } catch {
      setOffline(true);
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

  return (
    <div className="min-h-screen">
      {offline && (
        <div className="bg-[#241c0f] px-4 py-1.5 text-center text-[11px] text-[#f0a850]">
          Snapshot mode — showing the reference architecture; live engine unreachable.
        </div>
      )}
      <FlowWorkspace
        projection={projection}
        blueprint={blueprint}
        onAnswer={applyAnswer}
        applying={applying}
      />
    </div>
  );
}
