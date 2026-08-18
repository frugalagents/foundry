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
            {data.icon}
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

// ── Main Canvas ───────────────────────────────────────────────────────────────

export default function Canvas() {
  const { canvasNodes, canvasEdges, baselineNodeIds } = useStore()
  const [viewMode, setViewMode] = useState<'single' | 'compare'>('single')
  const [annotationsOn, setAnnotationsOn] = useState(true)
  const [selected, setSelected] = useState<DrawerNode | null>(null)

  const baselineSet = useMemo(() => new Set(baselineNodeIds), [baselineNodeIds])

  const hasNodes = canvasNodes.length > 0

  const onSelect = useCallback((id: string) => {
    const n = canvasNodes.find((node) => node.id === id)
    if (!n) return
    setSelected({
      id: n.id,
      label: n.label,
      sublabel: n.sublabel ?? '',
      icon: n.icon ?? '●',
      color: n.color ?? '#6366f1',
      cost: n.cost ?? '—',
      size: n.size ?? '—',
      comments: annotationsOn ? (n.comments ?? []) : [],
    })
  }, [canvasNodes, annotationsOn])

  const laidOut = useMemo(() => autoLayout(canvasNodes), [canvasNodes])

  // A node is a "customer addition" if it wasn't in the baseline (first) update
  const rfNodes: Node[] = useMemo(() => [
    ...LAYER_BAND_NODES,
    ...laidOut.map((n) => toRFNode(n, onSelect, baselineSet.size > 0 && !baselineSet.has(n.id))),
  ], [laidOut, onSelect, baselineSet])

  const rfEdges: Edge[] = useMemo(() => canvasEdges.map(toRFEdge), [canvasEdges])

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

      {/* Canvas body */}
      {!hasNodes ? (
        <CanvasEmpty />
      ) : viewMode === 'single' ? (
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
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
        </div>
      ) : (
        <div style={{
          flex: 1, display: 'flex', alignItems: 'center',
          justifyContent: 'center', background: 'var(--bg-elevated-2)',
        }}>
          <p style={{ fontSize: 12, color: 'var(--text-faint)' }}>
            Compare mode — coming soon
          </p>
        </div>
      )}

      {selected && (
        <NodeDetailDrawer node={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}
