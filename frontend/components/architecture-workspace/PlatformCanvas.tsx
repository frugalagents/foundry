'use client';

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { BookOpen, ExternalLink, Loader2, ShieldCheck, X } from 'lucide-react';
import type {
  ArchitectureComponent,
  ArchitectureWorkspaceProjection,
  DecisionTraceEntry,
  EvidenceClaim,
} from '@/lib/architecture-workspace';
import {
  explainArchitectureDecision,
  type ExplainPassage,
} from '@/lib/architecture-api';

interface PlatformCanvasProps {
  projection: ArchitectureWorkspaceProjection;
}

// Wire styling by relationship class. The engine currently emits depends_on;
// runtime_call / access_policy are supported so the canvas is ready for the
// typed-edge vocabulary without a code change.
const WIRE: Record<string, { stroke: string; dash?: string }> = {
  depends_on: { stroke: '#94a7a2' },
  runtime_call: { stroke: '#2f8f7f' },
  access_policy: { stroke: '#6f86d6', dash: '5 5' },
};

interface Point {
  x: number;
  y: number;
}

export function PlatformCanvas({ projection }: PlatformCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<Map<string, HTMLElement>>(new Map());
  const [paths, setPaths] = useState<
    { id: string; d: string; stroke: string; dash?: string; hot: boolean }[]
  >([]);
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const { planes, edges } = projection.architecture;

  // Map each component to the decision(s) and evidence that introduced it.
  const traceByComponent = useMemo(() => {
    const map = new Map<string, DecisionTraceEntry[]>();
    for (const entry of projection.decision_trace) {
      for (const componentId of entry.target_component_ids) {
        const list = map.get(componentId) ?? [];
        list.push(entry);
        map.set(componentId, list);
      }
    }
    return map;
  }, [projection.decision_trace]);

  const evidenceById = useMemo(() => {
    const map = new Map<string, EvidenceClaim>();
    for (const claim of projection.evidence ?? []) map.set(claim.claim_id, claim);
    return map;
  }, [projection.evidence]);

  // Neighbours of the focused node so we can dim the rest.
  const neighbours = useMemo(() => {
    if (!hovered) return null;
    const set = new Set<string>([hovered]);
    for (const e of edges) {
      if (e.source_component_id === hovered) set.add(e.target_component_id);
      if (e.target_component_id === hovered) set.add(e.source_component_id);
    }
    return set;
  }, [hovered, edges]);

  const registerNode = useCallback((id: string, el: HTMLElement | null) => {
    if (el) nodeRefs.current.set(id, el);
    else nodeRefs.current.delete(id);
  }, []);

  const recomputeEdges = useCallback(() => {
    const host = containerRef.current;
    if (!host) return;
    const hostBox = host.getBoundingClientRect();
    const anchor = (el: HTMLElement, side: 'top' | 'bottom'): Point => {
      const r = el.getBoundingClientRect();
      return {
        x: r.left - hostBox.left + r.width / 2,
        y: r.top - hostBox.top + (side === 'top' ? 0 : r.height),
      };
    };
    const next: typeof paths = [];
    for (const e of edges) {
      const source = nodeRefs.current.get(e.source_component_id);
      const target = nodeRefs.current.get(e.target_component_id);
      if (!source || !target) continue;
      const sBox = source.getBoundingClientRect();
      const tBox = target.getBoundingClientRect();
      // Draw from the lower node's top to the upper node's bottom so wires
      // flow between plane lanes without crossing through cards.
      const sourceIsLower = sBox.top >= tBox.top;
      const a = anchor(source, sourceIsLower ? 'top' : 'bottom');
      const b = anchor(target, sourceIsLower ? 'bottom' : 'top');
      const dy = Math.max(18, Math.abs(b.y - a.y) * 0.4);
      const d = `M ${a.x} ${a.y} C ${a.x} ${a.y - dy}, ${b.x} ${b.y + dy}, ${b.x} ${b.y}`;
      const style = WIRE[e.relationship] ?? WIRE.depends_on;
      const hot = !neighbours
        || (neighbours.has(e.source_component_id) && neighbours.has(e.target_component_id));
      next.push({ id: e.id, d, stroke: style.stroke, dash: style.dash, hot });
    }
    setPaths(next);
  }, [edges, neighbours]);

  useLayoutEffect(() => {
    recomputeEdges();
  }, [recomputeEdges, planes]);

  useEffect(() => {
    const host = containerRef.current;
    if (!host || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => recomputeEdges());
    ro.observe(host);
    window.addEventListener('resize', recomputeEdges);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', recomputeEdges);
    };
  }, [recomputeEdges]);

  const selectedComponent = useMemo(() => {
    if (!selected) return null;
    for (const plane of planes) {
      const found = plane.components.find((c) => c.id === selected);
      if (found) return { component: found, planeLabel: plane.label };
    }
    return null;
  }, [selected, planes]);

  return (
    <div className="relative border-y border-[#dce2e0] bg-[#fbfcfc]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e2e7e5] bg-[#fafbfb] px-4 py-2.5">
        <div className="flex items-center gap-2">
          <ShieldCheck size={14} className="shrink-0 text-[#276b61]" />
          <span className="truncate font-mono text-[11px] text-[#43504d]">
            {projection.architecture.pattern_id}
          </span>
        </div>
        <div className="flex items-center gap-4 text-[10px] font-medium text-[#6f7976]">
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-sm border border-[#cfd7d5] bg-white" />
            Baseline
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-sm border border-[#69a49b] bg-[#dff0ed]" />
            Requirement-driven
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-0 w-4 border-t-2 border-[#94a7a2]" />
            Dependency
          </span>
        </div>
      </div>

      <div ref={containerRef} className="relative px-3 py-4 sm:px-4">
        <svg
          className="pointer-events-none absolute inset-0 h-full w-full"
          style={{ overflow: 'visible' }}
          aria-hidden
        >
          <defs>
            <marker id="pc-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
              <path d="M1 1 L7 4 L1 7" fill="none" stroke="#94a7a2" strokeWidth="1.4" strokeLinecap="round" />
            </marker>
          </defs>
          {paths.map((p) => (
            <path
              key={p.id}
              d={p.d}
              fill="none"
              stroke={p.stroke}
              strokeWidth={p.hot ? 1.9 : 1.4}
              strokeDasharray={p.dash}
              markerEnd="url(#pc-arrow)"
              opacity={p.hot ? 0.85 : 0.1}
              style={{ transition: 'opacity .18s, stroke-width .18s' }}
            />
          ))}
        </svg>

        <div className="relative z-10 flex flex-col gap-3">
          {planes.map((plane) => (
            <section
              key={plane.id}
              className="grid gap-3 md:grid-cols-[104px_minmax(0,1fr)] md:gap-4"
              aria-labelledby={`pc-plane-${plane.id}`}
            >
              <div className="flex items-center justify-between md:block">
                <h3
                  id={`pc-plane-${plane.id}`}
                  className="pt-1 text-[10px] font-semibold uppercase tracking-wide text-[#56615f]"
                >
                  {plane.label}
                </h3>
                <span className="text-[10px] tabular-nums text-[#9aa19f] md:mt-0.5 md:block">
                  {plane.components.length}
                </span>
              </div>
              <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,180px),1fr))] gap-2.5">
                {plane.components.map((component) => (
                  <CanvasNode
                    key={component.id}
                    component={component}
                    register={registerNode}
                    dimmed={Boolean(neighbours) && !neighbours?.has(component.id)}
                    hasEvidence={(traceByComponent.get(component.id) ?? []).some(
                      (t) => (t.evidence_claim_ids ?? []).length > 0,
                    )}
                    onHover={setHovered}
                    onSelect={setSelected}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>

      {selectedComponent && (
        <ComponentDrawer
          component={selectedComponent.component}
          planeLabel={selectedComponent.planeLabel}
          trace={traceByComponent.get(selectedComponent.component.id) ?? []}
          evidenceById={evidenceById}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}

function CanvasNode({
  component,
  register,
  dimmed,
  hasEvidence,
  onHover,
  onSelect,
}: {
  component: ArchitectureComponent;
  register: (id: string, el: HTMLElement | null) => void;
  dimmed: boolean;
  hasEvidence: boolean;
  onHover: (id: string | null) => void;
  onSelect: (id: string) => void;
}) {
  const added = component.status === 'added';
  return (
    <button
      ref={(el) => register(component.id, el)}
      type="button"
      onMouseEnter={() => onHover(component.id)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover(component.id)}
      onBlur={() => onHover(null)}
      onClick={() => onSelect(component.id)}
      className={[
        'group relative rounded-lg border px-3 py-2.5 text-left transition-all',
        added ? 'border-[#69a49b] bg-[#eef7f5]' : 'border-[#dfe4e3] bg-white',
        dimmed ? 'opacity-30' : 'opacity-100',
        'hover:-translate-y-0.5 hover:shadow-[0_8px_20px_-12px_rgba(0,0,0,0.4)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#276b61]',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-[12px] font-semibold leading-tight text-[#26312f]">
          {component.name}
        </span>
        {hasEvidence && (
          <span
            title="Cited evidence available"
            className="mt-0.5 shrink-0 rounded bg-[#dff0ed] px-1 py-0.5 text-[8px] font-bold uppercase tracking-wide text-[#276b61]"
          >
            cited
          </span>
        )}
      </div>
      <p className="mt-1 line-clamp-2 text-[10px] leading-4 text-[#737d7a]">
        {component.description}
      </p>
    </button>
  );
}

function ComponentDrawer({
  component,
  planeLabel,
  trace,
  evidenceById,
  onClose,
}: {
  component: ArchitectureComponent;
  planeLabel: string;
  trace: DecisionTraceEntry[];
  evidenceById: Map<string, EvidenceClaim>;
  onClose: () => void;
}) {
  const claims = useMemo(() => {
    const ids = new Set<string>();
    for (const t of trace) for (const id of t.evidence_claim_ids ?? []) ids.add(id);
    return [...ids].map((id) => evidenceById.get(id)).filter(Boolean) as EvidenceClaim[];
  }, [trace, evidenceById]);

  const explainQuery = `${component.name}: ${component.description}`;

  return (
    <div className="absolute inset-y-0 right-0 z-20 flex w-full max-w-md flex-col border-l border-[#dce2e0] bg-white shadow-[-12px_0_30px_-20px_rgba(0,0,0,0.5)]">
      <div className="flex items-start justify-between gap-3 border-b border-[#e7ebe9] px-5 py-4">
        <div>
          <span className="text-[9px] font-bold uppercase tracking-wide text-[#8a938f]">
            {planeLabel}
            {component.status === 'added' ? ' · requirement-driven' : ' · baseline'}
          </span>
          <h3 className="mt-1 text-[15px] font-semibold text-[#26312f]">{component.name}</h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1 text-[#8a938f] hover:bg-[#f0f3f2] hover:text-[#26312f]"
          aria-label="Close"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        <p className="text-[12.5px] leading-5 text-[#4b5551]">{component.description}</p>

        {trace.length > 0 && (
          <section className="mt-5">
            <h4 className="text-[10px] font-bold uppercase tracking-wide text-[#8a938f]">
              Why it&apos;s here
            </h4>
            <ul className="mt-2 space-y-2">
              {trace.map((t) => (
                <li
                  key={t.evaluation_id}
                  className="rounded-md border border-[#e7ebe9] bg-[#fafbfb] px-3 py-2"
                >
                  <div className="font-mono text-[10px] text-[#6f7976]">{t.rule_id}</div>
                  <p className="mt-0.5 text-[11.5px] leading-4 text-[#4b5551]">{t.rationale}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        {claims.length > 0 && (
          <section className="mt-5">
            <h4 className="text-[10px] font-bold uppercase tracking-wide text-[#276b61]">
              Cited evidence
            </h4>
            <ul className="mt-2 space-y-2">
              {claims.map((claim) => (
                <li
                  key={claim.claim_id}
                  className="rounded-md border border-[#c8e4dd] bg-[#f2faf8] px-3 py-2.5"
                >
                  <p className="text-[11.5px] leading-4 text-[#33403d]">{claim.statement}</p>
                  <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-[#5c827a]">
                    <ShieldCheck size={11} className="shrink-0" />
                    <span className="font-medium">{claim.source_title ?? claim.source_id}</span>
                    <span className="text-[#9aa19f]">· {claim.source_locator}</span>
                    {claim.source_uri && (
                      <a
                        href={claim.source_uri}
                        target="_blank"
                        rel="noreferrer"
                        className="ml-auto inline-flex items-center gap-0.5 text-[#276b61] hover:underline"
                      >
                        source <ExternalLink size={9} />
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        <LearnMore query={explainQuery} />
      </div>
    </div>
  );
}

// Reference-only retrieval. Clearly separated from the cited evidence above so
// retrieved passages never read as decision authority.
function LearnMore({ query }: { query: string }) {
  const [state, setState] = useState<'idle' | 'loading' | 'done' | 'empty' | 'error'>('idle');
  const [passages, setPassages] = useState<ExplainPassage[]>([]);

  const run = async () => {
    setState('loading');
    try {
      const result = await explainArchitectureDecision(query);
      if (!result.configured || result.passages.length === 0) {
        setState('empty');
        return;
      }
      setPassages(result.passages);
      setState('done');
    } catch {
      setState('error');
    }
  };

  return (
    <section className="mt-5 border-t border-[#eef1f0] pt-4">
      <div className="flex items-center justify-between">
        <h4 className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-[#8a938f]">
          <BookOpen size={11} /> Learn more
        </h4>
        {state === 'idle' && (
          <button
            type="button"
            onClick={run}
            className="rounded-md border border-[#d6dedc] px-2.5 py-1 text-[10px] font-medium text-[#43504d] hover:bg-[#f0f3f2]"
          >
            Search knowledge base
          </button>
        )}
        {state === 'loading' && (
          <Loader2 size={13} className="animate-spin text-[#8a938f]" />
        )}
      </div>
      <p className="mt-1 text-[9.5px] italic leading-4 text-[#9aa19f]">
        Reference material from the knowledge base — context only, not the basis for the decision.
      </p>
      {state === 'empty' && (
        <p className="mt-2 text-[11px] text-[#8a938f]">No reference material found for this decision.</p>
      )}
      {state === 'error' && (
        <p className="mt-2 text-[11px] text-[#a64539]">Knowledge base is unavailable right now.</p>
      )}
      {state === 'done' && (
        <ul className="mt-2 space-y-2">
          {passages.map((p, i) => (
            <li key={i} className="rounded-md border border-[#e7ebe9] bg-[#fafbfb] px-3 py-2">
              <p className="text-[11px] leading-4 text-[#4b5551]">{p.text.slice(0, 320)}</p>
              <div className="mt-1 flex items-center gap-2 text-[9px] text-[#9aa19f]">
                <span className="font-mono">{p.source.split('/').pop()}</span>
                <span className="tabular-nums">score {p.score.toFixed(2)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
