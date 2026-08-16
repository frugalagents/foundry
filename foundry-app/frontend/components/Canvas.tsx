'use client'

import { useCallback, useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
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

// ── Custom node: arch (service / component) ───────────────────────────────────

function ArchNodeComponent({ data }: NodeProps<ArchNode>) {
  return (
    <div style={{
      background: 'var(--bg-elevated)',
      border: `1.5px solid ${data.color ?? '#333'}`,
      borderRadius: 10,
      padding: '10px 14px',
      minWidth: 130,
      maxWidth: 180,
      boxShadow: `0 0 0 1px ${data.color}22, 0 2px 8px rgba(0,0,0,0.5)`,
    }}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0, pointerEvents: 'none' }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: data.sublabel ? 4 : 0 }}>
        {data.icon && (
          <span style={{
            width: 24, height: 24,
            borderRadius: 6,
            background: `${data.color}22`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 12, flexShrink: 0,
          }}>
            {data.icon}
          </span>
        )}
        <span style={{
          fontSize: 12, fontWeight: 600,
          color: 'var(--text)',
          lineHeight: 1.3,
        }}>
          {data.label}
        </span>
      </div>
      {data.sublabel && (
        <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, lineHeight: 1.4 }}>
          {data.sublabel}
        </p>
      )}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />
    </div>
  )
}

// ── Custom node: zone (dashed boundary) ───────────────────────────────────────

function ZoneNodeComponent({ data }: NodeProps<ArchNode>) {
  return (
    <div style={{
      background: `${data.color}08`,
      border: `1.5px dashed ${data.color}55`,
      borderRadius: 12,
      width: data.width ?? 220,
      height: data.height ?? 160,
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'flex-start',
      padding: '8px 12px',
      pointerEvents: 'none',
    }}>
      <span style={{
        fontSize: 10, fontWeight: 700,
        color: data.color,
        opacity: 0.7,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
      }}>
        {data.label}
      </span>
    </div>
  )
}

const NODE_TYPES = { arch: ArchNodeComponent, zone: ZoneNodeComponent }

// ── Convert app types to ReactFlow types ─────────────────────────────────────

const COL_WIDTH  = 220
const ROW_HEIGHT = 120
const COLS       = 3

/** Auto-layout nodes that all share the same position (agent didn't set coordinates). */
function autoLayout(nodes: ArchNode[]): ArchNode[] {
  const archNodes = nodes.filter(n => n.type !== 'zone')
  const allSame   = archNodes.length > 1 &&
    archNodes.every(n => n.x === archNodes[0].x && n.y === archNodes[0].y)
  if (!allSame) return nodes

  let col = 0, row = 0
  return nodes.map(n => {
    if (n.type === 'zone') return n
    const x = col * (COL_WIDTH + 40) + 40
    const y = row * (ROW_HEIGHT + 20) + 40
    col++
    if (col >= COLS) { col = 0; row++ }
    return { ...n, x, y }
  })
}

function toRFNode(n: ArchNode): Node<ArchNode> {
  return {
    id: n.id,
    type: n.type,
    position: { x: n.x, y: n.y },
    data: n,
    style: n.type === 'zone'
      ? { width: n.width ?? 220, height: n.height ?? 160, zIndex: -1 }
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
      strokeDasharray: e.dashed ? '5 3' : undefined,
    },
  }
}

// ── Empty canvas placeholder ─────────────────────────────────────────────────

function CanvasPlaceholder() {
  return (
    <div style={{
      height: '100%', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      gap: 12, padding: 24,
      background: 'var(--bg-elevated)',
    }}>
      <div style={{
        width: 44, height: 44, borderRadius: 12,
        border: '1.5px dashed var(--border-focus)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 20, color: 'var(--text-faint)',
      }}>⬡</div>
      <p style={{
        fontSize: 12, color: 'var(--text-faint)',
        textAlign: 'center', maxWidth: 180, lineHeight: 1.6,
      }}>
        Architecture canvas will appear as the conversation progresses
      </p>
    </div>
  )
}

// ── Main Canvas ───────────────────────────────────────────────────────────────

export default function Canvas() {
  const { canvasNodes, canvasEdges, canvasVisible } = useStore()

  const rfNodes = useMemo(() => canvasNodes.map(toRFNode), [canvasNodes])
  const rfEdges = useMemo(() => canvasEdges.map(toRFEdge), [canvasEdges])

  if (!canvasVisible || canvasNodes.length === 0) {
    return <CanvasPlaceholder />
  }

  return (
    <div
      className="animate-slide-in"
      style={{ height: '100%', width: '100%', position: 'relative' }}
    >
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag
        zoomOnScroll
        minZoom={0.25}
        maxZoom={2}
        style={{ background: 'var(--bg-elevated)' }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="var(--text-faint)"
        />
        <Controls showInteractive={false} />
      </ReactFlow>

      {/* Stage label */}
      <div style={{
        position: 'absolute', top: 12, left: 12,
        background: 'var(--bg)',
        border: '1px solid var(--border)',
        borderRadius: 6,
        padding: '4px 10px',
        fontSize: 11, fontWeight: 600,
        color: 'var(--text-muted)',
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        pointerEvents: 'none',
      }}>
        Architecture
      </div>
    </div>
  )
}
