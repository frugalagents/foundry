'use client'

import { useState, useMemo, useCallback } from 'react'
import ReactFlow, {
  Background,
  Controls,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
  BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useStore } from '@/store'
import type { ArchNode, ArchEdge } from '@/lib/types'
import NodeDetailDrawer, { type DrawerNode } from './NodeDetailDrawer'
import IconGlyph from './IconGlyph'

// ── Zone layer definitions ────────────────────────────────────────────────────

const LAYERS = [
  { id: 'surface',   label: 'Surface',   color: '#6366f1', y: 0,   height: 140 },
  { id: 'harness',   label: 'Harness',   color: '#8b5cf6', y: 156, height: 140 },
  { id: 'execution', label: 'Execution', color: '#22c55e', y: 312, height: 140 },
  { id: 'gateway',   label: 'Gateway',   color: '#06b6d4', y: 468, height: 140 },
  { id: 'model',     label: 'Model',     color: '#818cf8', y: 624, height: 140 },
  { id: 'ops',       label: 'Ops',       color: '#f59e0b', y: 780, height: 140 },
  { id: 'access',    label: 'Access',    color: '#ef4444', y: 936, height: 140 },
]

const LAYER_META: Record<string, { label: string; rationale: string }> = {
  surface: { label: 'Surface', rationale: 'Defines how developers and leaders interact with the platform day to day.' },
  harness: { label: 'Harness', rationale: 'Sets the coding environment, workflow control points, and developer operating model.' },
  execution: { label: 'Execution', rationale: 'Determines where agent work runs and the trust boundary for code execution.' },
  gateway: { label: 'Gateway', rationale: 'Controls model routing, policy enforcement, and enterprise integrations.' },
  model: { label: 'Model', rationale: 'Specifies the model tiering and reasoning capability used across the platform.' },
  ops: { label: 'Ops', rationale: 'Covers observability, reliability, and cost control required to run the platform safely.' },
  access: { label: 'Access', rationale: 'Defines the identity, governance, and compliance controls that shape enterprise rollout.' },
}

// ── Auto-layout (when agent outputs identical coordinates) ────────────────────

const COL_WIDTH = 180
const COL_GAP   = 40
const COLS      = 3
const START_X   = 30
// Y offset within each zone band (leave room for the band label at top)
const BAND_PAD  = 38

// Maps layer id → the y-start of its zone band (must match LAYERS above)
const LAYER_BAND_Y: Record<string, number> = Object.fromEntries(
  LAYERS.map((l) => [l.id, l.y + BAND_PAD]),
)

function autoLayout(nodes: ArchNode[]): ArchNode[] {
  const archNodes = nodes.filter((n) => n.type !== 'zone')

  // If the agent has set real, distinct positions respect them
  const allSame =
    archNodes.length > 1 &&
    archNodes.every((n) => n.x === archNodes[0].x && n.y === archNodes[0].y)
  if (!allSame) return nodes

  // Group arch nodes by layer
  const byLayer: Record<string, ArchNode[]> = {}
  const unassigned: ArchNode[] = []
  for (const n of archNodes) {
    if (n.layer && LAYER_BAND_Y[n.layer] !== undefined) {
      if (!byLayer[n.layer]) byLayer[n.layer] = []
      byLayer[n.layer].push(n)
    } else {
      unassigned.push(n)
    }
  }

  const positioned = new Map<string, { x: number; y: number }>()

  // Place layered nodes in a horizontal row within their band
  for (const [layer, layerNodes] of Object.entries(byLayer)) {
    const bandY = LAYER_BAND_Y[layer]
    layerNodes.forEach((n, col) => {
      positioned.set(n.id, { x: START_X + col * (COL_WIDTH + COL_GAP), y: bandY })
    })
  }

  // Fallback: place unassigned nodes below all zone bands
  const lastLayer = LAYERS[LAYERS.length - 1]
  const fallbackBaseY = lastLayer.y + lastLayer.height + 40
  unassigned.forEach((n, i) => {
    const col = i % COLS
    const row = Math.floor(i / COLS)
    positioned.set(n.id, {
      x: START_X + col * (COL_WIDTH + COL_GAP),
      y: fallbackBaseY + row * 160,
    })
  })

  return nodes.map((n) => {
    const pos = positioned.get(n.id)
    return pos ? { ...n, ...pos } : n
  })
}

// ── Custom node: arch component ───────────────────────────────────────────────

type ArchNodeData = ArchNode & { onSelect: (id: string) => void; isNew?: boolean }

function ArchNodeComponent({ data, id }: NodeProps<ArchNodeData>) {
  return (
    <div
      onClick={() => data.onSelect?.(id)}
      style={{
        background: data.isNew ? 'rgba(99,102,241,0.07)' : 'var(--bg-elevated)',
        border: `1.5px solid ${data.isNew ? 'var(--accent)' : (data.color ?? '#333')}`,
        borderRadius: 11,
        padding: '11px 13px',
        width: 138,
        minHeight: 80,
        cursor: 'pointer',
        boxShadow: data.isNew
          ? `0 0 0 1px var(--accent)44, 0 2px 10px rgba(0,0,0,0.4)`
          : `0 0 0 1px ${data.color}22, 0 2px 10px rgba(0,0,0,0.4)`,
        position: 'relative',
      }}
    >
      {data.isNew && (
        <span style={{
          position: 'absolute', top: -5, right: -5,
          background: 'var(--accent)', borderRadius: 4,
          padding: '1px 4px', fontSize: 8, fontWeight: 700,
          color: '#fff', letterSpacing: '0.04em',
          border: '1.5px solid var(--bg-elevated)',
          lineHeight: 1.4,
        }}>
          NEW
        </span>
      )}
      <Handle type="target" position={Position.Top} style={{ opacity: 0, pointerEvents: 'none' }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
        {data.icon && (
          <span style={{
            width: 22, height: 22, borderRadius: 6, background: `${data.color}22`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 11, color: data.color, flexShrink: 0,
          }}>
            <IconGlyph icon={data.icon} color={data.color} size={12} />
          </span>
        )}
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', lineHeight: 1.3 }}>
          {data.label}
        </span>
      </div>
      {data.sublabel && (
        <p style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>
          {data.sublabel}
        </p>
      )}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
        {data.cost && (
          <span style={{
            fontSize: 10.5, fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-faint)',
          }}>
            {data.cost}
          </span>
        )}
        {(data.comments?.length ?? 0) > 0 && (
          <span style={{
            width: 16, height: 16, borderRadius: 5, background: '#3b2e12',
            border: '1px solid var(--amber)', color: 'var(--amber)',
            fontSize: 9, display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 700, marginLeft: 'auto',
          }}>
            {data.comments!.length}
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />
    </div>
  )
}

// ── Custom node: zone background rectangle ────────────────────────────────────

function ZoneNodeComponent({ data }: NodeProps<ArchNode>) {
  return (
    <div style={{
      background: `${data.color}08`,
      border: `1.5px dashed ${data.color}55`,
      borderRadius: 12,
      width: data.width ?? 220,
      height: data.height ?? 160,
      padding: '8px 12px',
      pointerEvents: 'none',
    }}>
      <span style={{
        fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
        textTransform: 'uppercase', color: data.color, opacity: 0.75,
      }}>
        {data.label}
      </span>
    </div>
  )
}

const NODE_TYPES = { arch: ArchNodeComponent, zone: ZoneNodeComponent }

// ── Static layer band nodes (injected into every RF render) ───────────────────

const LAYER_BAND_NODES: Node[] = LAYERS.map((l) => ({
  id: `__layer-${l.id}`,
  type: 'zone',
  position: { x: -20, y: l.y },
  data: {
    id: `__layer-${l.id}`, type: 'zone',
    label: l.label, color: l.color,
    x: -20, y: l.y, width: 780, height: l.height,
  },
  draggable: false,
  selectable: false,
  zIndex: -1,
  style: { zIndex: -1, pointerEvents: 'none' },
}))

// ── Type converters ───────────────────────────────────────────────────────────

function toRFNode(n: ArchNode, onSelect: (id: string) => void, isNew: boolean): Node<ArchNodeData> {
  return {
    id: n.id,
    type: n.type ?? 'arch',
    position: { x: n.x, y: n.y },
    data: { ...n, onSelect, isNew },
    style: n.type === 'zone'
      ? { width: n.width ?? 220, height: n.height ?? 160, zIndex: -1, pointerEvents: 'none' }
      : undefined,
  }
}

function toRFEdge(e: ArchEdge): Edge {
  return {
    id: e.id,
    source: e.source,
    target: e.target,
    animated: e.animated ?? false,
    style: {
      stroke: e.color ?? 'var(--border-focus)',
      strokeWidth: 1.5,
      strokeDasharray: e.dashed ? '5 3' : undefined,
    },
  }
}

// ── Empty state ───────────────────────────────────────────────────────────────

function CanvasEmpty() {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      gap: 12, background: 'var(--bg-elevated-2)',
    }}>
      <div style={{
        width: 44, height: 44, borderRadius: 12,
        border: '1.5px dashed var(--border-focus)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 20, color: 'var(--text-faint)',
      }}>
        ⬡
      </div>
      <p style={{
        fontSize: 12, color: 'var(--text-faint)',
        textAlign: 'center', maxWidth: 180, lineHeight: 1.6,
      }}>
        Architecture canvas will appear as the conversation progresses
      </p>
    </div>
  )
}

// ── Segment button style ──────────────────────────────────────────────────────

function segBtn(active: boolean): React.CSSProperties {
  return {
    padding: '6px 12px', borderRadius: 6, border: 'none', fontSize: 11.5,
    fontWeight: 500, cursor: 'pointer',
    background: active ? 'var(--bg-hover)' : 'none',
    color: active ? 'var(--text)' : 'var(--text-muted)',
  }
}

function inferNodeReason(node: ArchNode): string {
  if (node.sublabel?.trim()) return node.sublabel.trim()
  if (node.comments?.[0]?.text?.trim()) return node.comments[0].text.trim()
  if (node.layer && LAYER_META[node.layer]) return LAYER_META[node.layer].rationale
  return 'Included to complete the platform architecture for this operating model.'
}

function summarizeByLayer(nodes: ArchNode[]) {
  return LAYERS
    .map((layer) => ({
      ...layer,
      nodes: nodes.filter((node) => node.layer === layer.id),
    }))
    .filter((group) => group.nodes.length > 0)
}

function SummaryCard({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <div style={{
      border: '1px solid var(--border)',
      background: 'var(--bg-elevated)',
      borderRadius: 12,
      padding: 14,
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      minHeight: 0,
    }}>
      <div>
        <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>{title}</div>
        <p style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.5 }}>
          {subtitle}
        </p>
      </div>
      {children}
    </div>
  )
}

function CanvasFlow({
  nodes,
  edges,
}: {
  nodes: Node[]
  edges: Edge[]
}) {
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={NODE_TYPES}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      proOptions={{ hideAttribution: true }}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      panOnDrag
      zoomOnScroll
      minZoom={0.25}
      maxZoom={2}
      style={{ background: 'var(--bg-elevated-2)' }}
    >
      <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#1c1c20" />
      <Controls showInteractive={false} />
    </ReactFlow>
  )
}

// ── Main Canvas ───────────────────────────────────────────────────────────────

export default function Canvas() {
  const { canvasNodes, canvasEdges, baselineNodeIds, workspace } = useStore()
  const [viewMode, setViewMode] = useState<'single' | 'compare'>('single')
  const [annotationsOn, setAnnotationsOn] = useState(true)
  const [selected, setSelected] = useState<DrawerNode | null>(null)

  const baselineSet = useMemo(() => new Set(baselineNodeIds), [baselineNodeIds])

  const hasNodes = canvasNodes.length > 0

  const onSelect = useCallback((id: string) => {
    const n = canvasNodes.find((node) => node.id === id)
    if (!n) return
    const isNew = baselineSet.size > 0 && !baselineSet.has(n.id)
    setSelected({
      id: n.id,
      label: n.label,
      sublabel: n.sublabel ?? '',
      icon: n.icon ?? '●',
      color: n.color ?? '#6366f1',
      cost: n.cost ?? '—',
      size: n.size ?? '—',
      layerLabel: n.layer ? (LAYER_META[n.layer]?.label ?? n.layer) : undefined,
      rationale: inferNodeReason(n),
      isNew,
      comments: annotationsOn ? (n.comments ?? []) : [],
    })
  }, [canvasNodes, annotationsOn, baselineSet])

  const laidOut = useMemo(() => autoLayout(canvasNodes), [canvasNodes])
  const baselineNodes = useMemo(
    () => laidOut.filter((node) => baselineSet.size === 0 || baselineSet.has(node.id)),
    [laidOut, baselineSet],
  )
  const customNodes = useMemo(
    () => laidOut.filter((node) => baselineSet.size > 0 && !baselineSet.has(node.id)),
    [laidOut, baselineSet],
  )
  const baselineNodeIdsMemo = useMemo(() => new Set(baselineNodes.map((node) => node.id)), [baselineNodes])
  const baselineEdges = useMemo(
    () => canvasEdges.filter((edge) => baselineNodeIdsMemo.has(edge.source) && baselineNodeIdsMemo.has(edge.target)),
    [canvasEdges, baselineNodeIdsMemo],
  )
  const baselineLayerGroups = useMemo(() => summarizeByLayer(baselineNodes), [baselineNodes])
  const rationaleLines = useMemo(() => {
    if (workspace?.decisions?.length) return workspace.decisions.slice(0, 3)
    if (workspace?.risks?.length) return workspace.risks.slice(0, 3)
    return customNodes.slice(0, 3).map((node) => `${node.label}: ${inferNodeReason(node)}`)
  }, [workspace, customNodes])

  // A node is a "customer addition" if it wasn't in the baseline (first) update
  const rfNodes: Node[] = useMemo(() => [
    ...LAYER_BAND_NODES,
    ...laidOut.map((n) => toRFNode(n, onSelect, baselineSet.size > 0 && !baselineSet.has(n.id))),
  ], [laidOut, onSelect, baselineSet])
  const baselineRfNodes: Node[] = useMemo(() => [
    ...LAYER_BAND_NODES,
    ...baselineNodes.map((n) => toRFNode(n, onSelect, false)),
  ], [baselineNodes, onSelect])

  const rfEdges: Edge[] = useMemo(() => canvasEdges.map(toRFEdge), [canvasEdges])
  const baselineRfEdges: Edge[] = useMemo(() => baselineEdges.map(toRFEdge), [baselineEdges])

  const totalCostLabel = useMemo(() => {
    const amounts = canvasNodes
      .map((n) => n.cost)
      .filter(Boolean)
      .map((c) => parseFloat((c ?? '').replace(/[^0-9.]/g, '')))
      .filter((v) => !isNaN(v))
    if (amounts.length === 0) return '—'
    return `$${Math.round(amounts.reduce((a, b) => a + b, 0)).toLocaleString()}/mo`
  }, [canvasNodes])

  return (
    <div style={{
      flex: '1 1 50%', minWidth: 0, display: 'flex', flexDirection: 'column',
      overflow: 'hidden', background: 'var(--bg-elevated-2)', position: 'relative',
    }}>
      {/* Toolbar */}
      <div style={{
        minHeight: 48, flexShrink: 0, display: 'flex', flexWrap: 'wrap',
        alignItems: 'center', justifyContent: 'space-between', gap: 8,
        padding: '8px 16px', borderBottom: '1px solid var(--border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
          <span style={{
            fontSize: 11, fontWeight: 600, letterSpacing: '0.06em',
            textTransform: 'uppercase', color: 'var(--text-muted)',
          }}>
            Architecture
          </span>
          <div style={{
            display: 'flex', gap: 2, background: 'var(--bg-elevated)',
            border: '1px solid var(--border)', borderRadius: 8, padding: 2,
          }}>
            <button onClick={() => setViewMode('single')} style={segBtn(viewMode === 'single')}>
              Single
            </button>
            <button onClick={() => setViewMode('compare')} style={segBtn(viewMode === 'compare')}>
              Compare
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0, marginLeft: 'auto' }}>
          <button
            onClick={() => setAnnotationsOn((v) => !v)}
            title="Toggle comments"
            style={{
              width: 26, height: 26, borderRadius: 7, display: 'flex',
              alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
              background: annotationsOn ? '#191b2e' : 'var(--bg-elevated)',
              border: `1px solid ${annotationsOn ? '#34386b' : 'var(--border)'}`,
              color: annotationsOn ? 'var(--accent-strong)' : 'var(--text-muted)',
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </button>

          <span style={{
            fontSize: 12, fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-muted)',
            padding: '5px 9px', background: 'var(--bg-elevated)',
            border: '1px solid var(--border)', borderRadius: 7, whiteSpace: 'nowrap',
          }}>
            {totalCostLabel}
          </span>
        </div>
      </div>

      {hasNodes && (
        <div style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--border)',
          display: 'grid',
          gridTemplateColumns: '1.15fr 1fr 1fr',
          gap: 10,
          background: 'var(--bg-elevated-2)',
          flexShrink: 0,
        }}>
          <SummaryCard
            title="Standard Baseline"
            subtitle={`${baselineNodes.length} standard component${baselineNodes.length === 1 ? '' : 's'} across ${baselineLayerGroups.length} layer${baselineLayerGroups.length === 1 ? '' : 's'}`}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {baselineLayerGroups.map((group) => (
                <div key={group.id} style={{ display: 'grid', gridTemplateColumns: '82px 1fr', gap: 8, alignItems: 'start' }}>
                  <span style={{ fontSize: 10.5, fontWeight: 700, color: group.color, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {group.label}
                  </span>
                  <span style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.5 }}>
                    {group.nodes.map((node) => node.label).join(' · ')}
                  </span>
                </div>
              ))}
            </div>
          </SummaryCard>

          <SummaryCard
            title="Added For This Org"
            subtitle={customNodes.length > 0
              ? `${customNodes.length} component${customNodes.length === 1 ? '' : 's'} were added beyond the baseline`
              : 'No org-specific additions have been introduced yet'}
          >
            {customNodes.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--text-faint)', lineHeight: 1.6 }}>
                The current architecture is still the standard baseline.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {customNodes.slice(0, 4).map((node) => (
                  <div key={node.id} style={{
                    padding: '9px 10px',
                    borderRadius: 9,
                    border: '1px solid var(--border)',
                    background: 'rgba(99,102,241,0.06)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                      <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>{node.label}</span>
                      <span style={{ fontSize: 10.5, color: 'var(--accent-strong)' }}>
                        {node.layer ? (LAYER_META[node.layer]?.label ?? node.layer) : 'Custom'}
                      </span>
                    </div>
                    <p style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.5, marginTop: 4 }}>
                      {inferNodeReason(node)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </SummaryCard>

          <SummaryCard
            title="Why It Changed"
            subtitle="Executive rationale for the current architecture direction"
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {rationaleLines.length > 0 ? rationaleLines.map((line, index) => (
                <div key={`${line}-${index}`} style={{
                  padding: '8px 10px',
                  borderRadius: 9,
                  border: '1px solid var(--border)',
                  background: 'var(--bg)',
                  fontSize: 12,
                  color: 'var(--text-2)',
                  lineHeight: 1.55,
                }}>
                  {line}
                </div>
              )) : (
                <p style={{ fontSize: 12, color: 'var(--text-faint)', lineHeight: 1.6 }}>
                  Once the advisor introduces tailored architecture changes, the rationale will be summarized here.
                </p>
              )}
            </div>
          </SummaryCard>
        </div>
      )}

      {/* Canvas body */}
      {!hasNodes ? (
        <CanvasEmpty />
      ) : viewMode === 'single' ? (
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <CanvasFlow nodes={rfNodes} edges={rfEdges} />
        </div>
      ) : (
        <div style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 1,
          background: 'var(--border)',
          minHeight: 0,
        }}>
          <div style={{ minWidth: 0, background: 'var(--bg-elevated-2)', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border)' }}>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>Standard baseline</div>
              <p style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.5 }}>
                The reference architecture before any organization-specific tailoring.
              </p>
            </div>
            <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
              <CanvasFlow nodes={baselineRfNodes} edges={baselineRfEdges} />
            </div>
          </div>

          <div style={{ minWidth: 0, background: 'var(--bg-elevated-2)', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border)' }}>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>Tailored for this organization</div>
              <p style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.5 }}>
                Full architecture with org-specific additions highlighted in blue.
              </p>
            </div>
            <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
              <CanvasFlow nodes={rfNodes} edges={rfEdges} />
            </div>
          </div>
        </div>
      )}

      {selected && (
        <NodeDetailDrawer node={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}
