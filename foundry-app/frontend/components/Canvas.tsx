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
import type { ArchNode, ArchEdge, ArchitectureArtifact, ArchitectureCustomization } from '@/lib/types'
import NodeDetailDrawer, { type DrawerNode } from './NodeDetailDrawer'
import IconGlyph from './IconGlyph'

// ── Deterministic architecture layout ────────────────────────────────────────

const BASELINE_LAYERS = [
  { id: 'surface', label: 'Surface', color: '#6366f1' },
  { id: 'harness', label: 'Harness', color: '#8b5cf6' },
  { id: 'execution', label: 'Execution', color: '#22c55e' },
  { id: 'gateway', label: 'Gateway', color: '#06b6d4' },
  { id: 'model', label: 'Model', color: '#10b981' },
] as const

const CONTROL_PLANE_SLOTS = [
  { id: 'identity', label: 'Identity', color: '#ef4444' },
  { id: 'guardrails', label: 'Guardrails', color: '#f97316' },
  { id: 'policy', label: 'Policy', color: '#dc2626' },
  { id: 'quota', label: 'Quota', color: '#f59e0b' },
  { id: 'observability', label: 'Observability', color: '#0891b2' },
  { id: 'audit', label: 'Audit', color: '#0f766e' },
] as const

const LAYER_META: Record<string, { label: string; rationale: string }> = {
  surface: { label: 'Surface', rationale: 'Defines how developers and leaders interact with the platform day to day.' },
  harness: { label: 'Harness', rationale: 'Sets the coding environment, workflow control points, and developer operating model.' },
  execution: { label: 'Execution', rationale: 'Determines where agent work runs and the trust boundary for code execution.' },
  gateway: { label: 'Gateway', rationale: 'Controls model routing, policy enforcement, and enterprise integrations.' },
  model: { label: 'Model', rationale: 'Specifies the model tiering and reasoning capability used across the platform.' },
  ops: { label: 'Ops', rationale: 'Covers observability, reliability, and cost control required to run the platform safely.' },
  access: { label: 'Access', rationale: 'Defines the identity, governance, and compliance controls that shape enterprise rollout.' },
}

const NODE_WIDTH = 160
const NODE_GAP = 18
const BASELINE_COLS = 4
const BASELINE_X = 28
const BASELINE_WIDTH = 744
const CONTROL_X = BASELINE_X + BASELINE_WIDTH + 28
const CONTROL_WIDTH = 248
const ZONE_HEADER = 42
const LAYER_MIN_HEIGHT = 128
const LAYER_GAP = 16
const ROW_HEIGHT = 100
const SUPPORT_Y_GAP = 28
const SUPPORT_GROUP_GAP = 18
const SUPPORT_GROUP_WIDTH = 488
const SUPPORT_GROUP_COLS = 2

type ResolvedPathRole = 'primary' | 'overlay' | 'supporting'

type ResolvedCanvasNode = ArchNode & {
  resolvedKind: string
  resolvedPathRole: ResolvedPathRole
}

type ZoneCardData = {
  id: string
  type: 'zone'
  label: string
  sublabel?: string
  color: string
  x: number
  y: number
  width: number
  height: number
}

type SupportingLaneGroup = {
  id: string
  label: string
  narrative: string
  color: string
  nodes: ResolvedCanvasNode[]
}

function resolveNodeKind(node: ArchNode) {
  if (node.kind?.trim()) return node.kind.trim()

  const label = `${node.label} ${node.sublabel ?? ''}`.toLowerCase()
  if (node.layer === 'surface') return 'developer_surface'
  if (node.layer === 'model') return 'model_provider'
  if (node.layer === 'access') {
    return label.includes('identity') || label.includes('sso') || label.includes('iam')
      ? 'identity_control'
      : 'policy_control'
  }
  if (node.layer === 'ops') {
    return label.includes('cost') || label.includes('spend') || label.includes('quota')
      ? 'cost_control'
      : 'observability_control'
  }
  if (node.layer === 'execution') {
    return label.includes('runtime') ? 'agent_runtime' : 'execution_lane'
  }
  if (node.layer === 'gateway') {
    if (label.includes('model gateway') || label.includes('litellm') || label.includes('bedrock')) return 'model_gateway'
    if (label.includes('registry') || label.includes('catalog')) return 'registry_control'
    if (label.includes('github') || label.includes('gitlab') || label.includes('connector') || label.includes('tool')) return 'tool_connector'
    return 'tool_gateway'
  }
  if (node.layer === 'harness') {
    if (label.includes('strands') || label.includes('langchain') || label.includes('pydanticai') || label.includes('autogen') || label.includes('crewai')) {
      return 'framework_sdk'
    }
    if (label.includes('background agent') || label.includes('custom harness')) {
      return 'custom_harness'
    }
    return 'interactive_harness'
  }
  return 'platform_component'
}

function resolvePathRole(node: ArchNode): ResolvedPathRole {
  if (node.path_role === 'primary' || node.path_role === 'overlay' || node.path_role === 'supporting') {
    return node.path_role
  }

  const kind = resolveNodeKind(node)
  if (node.layer === 'access' || node.layer === 'ops') return 'overlay'
  if (['identity_control', 'policy_control', 'observability_control', 'cost_control', 'registry_control'].includes(kind)) return 'overlay'
  if (['custom_harness', 'framework_sdk', 'agent_runtime'].includes(kind)) return 'supporting'
  return 'primary'
}

function resolveControlSlot(node: ResolvedCanvasNode) {
  const label = `${node.label} ${node.sublabel ?? ''}`.toLowerCase()
  if (node.layer === 'access' || node.resolvedKind === 'identity_control' || label.includes('identity') || label.includes('sso') || label.includes('iam')) return 'identity'
  if (label.includes('guardrail') || label.includes('safety') || label.includes('moderation')) return 'guardrails'
  if (node.resolvedKind === 'policy_control' || label.includes('policy') || label.includes('governance') || label.includes('approval') || label.includes('compliance')) return 'policy'
  if (node.resolvedKind === 'cost_control' || label.includes('quota') || label.includes('budget') || label.includes('spend') || label.includes('cost')) return 'quota'
  if (node.layer === 'ops' || node.resolvedKind === 'observability_control' || label.includes('observe') || label.includes('trace') || label.includes('telemetry') || label.includes('monitor')) return 'observability'
  if (label.includes('audit') || label.includes('log') || label.includes('siem')) return 'audit'
  return node.resolvedPathRole === 'overlay' ? 'policy' : null
}

function baselineLayerForNode(node: ResolvedCanvasNode): typeof BASELINE_LAYERS[number]['id'] | null {
  if (node.layer === 'gateway' && node.resolvedPathRole === 'primary' && resolveControlSlot(node) === null) return 'gateway'
  if (node.layer === 'model') return 'model'
  if (node.layer === 'surface') return 'surface'
  if (node.layer === 'harness' && node.resolvedPathRole === 'primary') return 'harness'
  if (node.layer === 'execution' && node.resolvedPathRole === 'primary') return 'execution'
  return null
}

function sortNodes(nodes: ResolvedCanvasNode[]) {
  return [...nodes].sort((a, b) => a.label.localeCompare(b.label))
}

function uniqueNodes(nodes: ResolvedCanvasNode[]) {
  const seen = new Set<string>()
  return nodes.filter((node) => {
    if (seen.has(node.id)) return false
    seen.add(node.id)
    return true
  })
}

function buildSupportingLaneGroups(
  nodes: ResolvedCanvasNode[],
  artifact: ArchitectureArtifact | null,
) {
  const supportingNodes = nodes.filter((node) => node.resolvedPathRole === 'supporting')
  const groups: SupportingLaneGroup[] = []
  const assigned = new Set<string>()

  ;(artifact?.supporting_lanes ?? []).forEach((lane, index) => {
    const laneNodes = uniqueNodes(lane.component_ids
      .map((id) => supportingNodes.find((node) => node.id === id))
      .filter(Boolean) as ResolvedCanvasNode[])
    if (laneNodes.length === 0) return
    laneNodes.forEach((node) => assigned.add(node.id))
    groups.push({
      id: lane.id,
      label: lane.title,
      narrative: lane.narrative || 'Supporting lane published from the architecture artifact.',
      color: index % 2 === 0 ? '#8b5cf6' : '#7c3aed',
      nodes: sortNodes(laneNodes),
    })
  })

  const remaining = supportingNodes.filter((node) => !assigned.has(node.id))
  const harnessNodes = remaining.filter((node) => node.layer === 'harness')
  const executionNodes = remaining.filter((node) => node.layer === 'execution')
  const adjacentNodes = remaining.filter((node) => node.layer !== 'harness' && node.layer !== 'execution')

  if (harnessNodes.length > 0) {
    groups.push({
      id: 'support-harness',
      label: 'Supporting harnesses',
      narrative: 'Approved alternate harnesses or frameworks that sit beside the default developer path.',
      color: '#8b5cf6',
      nodes: sortNodes(harnessNodes),
    })
  }
  if (executionNodes.length > 0) {
    groups.push({
      id: 'support-execution',
      label: 'Exception execution lanes',
      narrative: 'Specialized runtimes or isolated execution paths that sit outside the standard request lane.',
      color: '#a855f7',
      nodes: sortNodes(executionNodes),
    })
  }
  if (adjacentNodes.length > 0) {
    groups.push({
      id: 'support-adjacent',
      label: 'Adjacent platform components',
      narrative: 'Supporting components that matter to the architecture without belonging to the primary request path.',
      color: '#4f46e5',
      nodes: sortNodes(adjacentNodes),
    })
  }

  return groups
}

function buildZoneNode(zone: ZoneCardData): Node<ZoneCardData> {
  return {
    id: zone.id,
    type: 'zone',
    position: { x: zone.x, y: zone.y },
    data: zone,
    draggable: false,
    selectable: false,
    zIndex: -1,
    style: { zIndex: -1, pointerEvents: 'none' },
  }
}

function autoLayout(nodes: ArchNode[], artifact: ArchitectureArtifact | null) {
  const resolvedNodes: ResolvedCanvasNode[] = nodes
    .filter((node) => node.type !== 'zone')
    .map((node) => ({
      ...node,
      resolvedKind: resolveNodeKind(node),
      resolvedPathRole: resolvePathRole(node),
    }))

  const positioned = new Map<string, { x: number; y: number }>()
  const zoneNodes: Node<ZoneCardData>[] = []
  let currentY = 0

  BASELINE_LAYERS.forEach((layer) => {
    const layerNodes = sortNodes(resolvedNodes.filter((node) => baselineLayerForNode(node) === layer.id))
    const rowCount = Math.max(1, Math.ceil(layerNodes.length / BASELINE_COLS))
    const zoneHeight = Math.max(LAYER_MIN_HEIGHT, ZONE_HEADER + rowCount * ROW_HEIGHT)

    zoneNodes.push(buildZoneNode({
      id: `__layer-${layer.id}`,
      type: 'zone',
      label: layer.label,
      sublabel: `${layerNodes.length} component${layerNodes.length === 1 ? '' : 's'} in the shared baseline`,
      color: layer.color,
      x: 0,
      y: currentY,
      width: BASELINE_WIDTH,
      height: zoneHeight,
    }))

    layerNodes.forEach((node, index) => {
      const col = index % BASELINE_COLS
      const row = Math.floor(index / BASELINE_COLS)
      positioned.set(node.id, {
        x: BASELINE_X + col * (NODE_WIDTH + NODE_GAP),
        y: currentY + ZONE_HEADER + row * ROW_HEIGHT,
      })
    })

    currentY += zoneHeight + LAYER_GAP
  })

  const baselineBottom = currentY - LAYER_GAP
  const controlNodes = resolvedNodes.filter((node) => resolveControlSlot(node) !== null)
  let controlY = 18

  zoneNodes.push(buildZoneNode({
    id: '__control-plane',
    type: 'zone',
    label: 'Shared Control Plane',
    sublabel: 'Identity, guardrails, policy, quota, observability, and audit',
    color: '#111827',
    x: CONTROL_X,
    y: 0,
    width: CONTROL_WIDTH,
    height: Math.max(baselineBottom, 540),
  }))

  CONTROL_PLANE_SLOTS.forEach((slot) => {
    const slotNodes = sortNodes(controlNodes.filter((node) => resolveControlSlot(node) === slot.id))
    const rowCount = Math.max(1, slotNodes.length)
    const slotHeight = Math.max(78, 30 + rowCount * 88)

    zoneNodes.push(buildZoneNode({
      id: `__control-${slot.id}`,
      type: 'zone',
      label: slot.label,
      sublabel: slotNodes.length > 0 ? `${slotNodes.length} mapped control${slotNodes.length === 1 ? '' : 's'}` : 'No explicit node tagged yet',
      color: slot.color,
      x: CONTROL_X + 12,
      y: controlY,
      width: CONTROL_WIDTH - 24,
      height: slotHeight,
    }))

    slotNodes.forEach((node, index) => {
      positioned.set(node.id, {
        x: CONTROL_X + 26,
        y: controlY + 28 + index * 88,
      })
    })

    controlY += slotHeight + 10
  })

  const supportingGroups = buildSupportingLaneGroups(resolvedNodes, artifact)
  const supportHeaderY = Math.max(baselineBottom, controlY - 10) + SUPPORT_Y_GAP
  let supportY = supportHeaderY

  if (supportingGroups.length > 0) {
    zoneNodes.push(buildZoneNode({
      id: '__supporting-root',
      type: 'zone',
      label: 'Supporting And Exception Lanes',
      sublabel: 'Specialized or customer-specific paths kept separate from the shared baseline',
      color: '#6d28d9',
      x: 0,
      y: supportHeaderY,
      width: CONTROL_X + CONTROL_WIDTH,
      height: 58,
    }))
    supportY += 74
  }

  supportingGroups.forEach((group, index) => {
    const x = index % SUPPORT_GROUP_COLS === 0 ? 0 : SUPPORT_GROUP_WIDTH + SUPPORT_GROUP_GAP
    const y = supportY + Math.floor(index / SUPPORT_GROUP_COLS) * 220
    const rowCount = Math.max(1, Math.ceil(group.nodes.length / 2))
    const zoneHeight = Math.max(128, ZONE_HEADER + rowCount * 96)

    zoneNodes.push(buildZoneNode({
      id: `__support-${group.id}`,
      type: 'zone',
      label: group.label,
      sublabel: group.narrative,
      color: group.color,
      x,
      y,
      width: SUPPORT_GROUP_WIDTH,
      height: zoneHeight,
    }))

    group.nodes.forEach((node, nodeIndex) => {
      const col = nodeIndex % 2
      const row = Math.floor(nodeIndex / 2)
      positioned.set(node.id, {
        x: x + BASELINE_X + col * (NODE_WIDTH + NODE_GAP),
        y: y + ZONE_HEADER + row * 96,
      })
    })
  })

  const unassigned = resolvedNodes.filter((node) => !positioned.has(node.id))
  if (unassigned.length > 0) {
    const x = 0
    const y = supportY + Math.ceil(supportingGroups.length / SUPPORT_GROUP_COLS) * 220
    const rowCount = Math.max(1, Math.ceil(unassigned.length / 3))
    zoneNodes.push(buildZoneNode({
      id: '__support-overflow',
      type: 'zone',
      label: 'Other Components',
      sublabel: 'Components that were not clearly assigned to the baseline or shared control plane',
      color: '#475569',
      x,
      y,
      width: CONTROL_X + CONTROL_WIDTH,
      height: Math.max(128, ZONE_HEADER + rowCount * 96),
    }))

    unassigned.forEach((node, index) => {
      const col = index % 3
      const row = Math.floor(index / 3)
      positioned.set(node.id, {
        x: BASELINE_X + col * (NODE_WIDTH + NODE_GAP),
        y: y + ZONE_HEADER + row * 96,
      })
    })
  }

  return {
    nodes: resolvedNodes.map((node) => {
      const position = positioned.get(node.id)
      return position ? { ...node, ...position } : node
    }),
    zoneNodes,
  }
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

function ZoneNodeComponent({ data }: NodeProps<ZoneCardData>) {
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
      {data.sublabel ? (
        <div style={{
          marginTop: 6,
          maxWidth: '100%',
          fontSize: 11,
          lineHeight: 1.45,
          color: 'var(--text-muted)',
          whiteSpace: 'normal',
        }}>
          {data.sublabel}
        </div>
      ) : null}
    </div>
  )
}

const NODE_TYPES = { arch: ArchNodeComponent, zone: ZoneNodeComponent }

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

function layerLabel(layerId: string): string {
  return LAYER_META[layerId]?.label ?? layerId
}

function findCustomizationForNode(
  artifact: ArchitectureArtifact | null,
  nodeId: string,
): ArchitectureCustomization | null {
  if (!artifact) return null
  return artifact.customizations.find((item) => item.added_component_ids.includes(nodeId)) ?? null
}

function inferNodeReason(node: ArchNode, artifact?: ArchitectureArtifact | null): string {
  const customization = findCustomizationForNode(artifact ?? null, node.id)
  if (customization?.reason) {
    return customization.tradeoff
      ? `${customization.reason} Tradeoff: ${customization.tradeoff}`
      : customization.reason
  }
  if (node.sublabel?.trim()) return node.sublabel.trim()
  if (node.comments?.[0]?.text?.trim()) return node.comments[0].text.trim()
  if (node.layer && LAYER_META[node.layer]) return LAYER_META[node.layer].rationale
  return 'Included to complete the platform architecture for this operating model.'
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
  const {
    canvasNodes,
    canvasEdges,
    baselineNodeIds,
    workspace,
    architectureArtifact,
  } = useStore()
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
      layerLabel: n.layer ? layerLabel(n.layer) : undefined,
      rationale: inferNodeReason(n, architectureArtifact),
      isNew,
      comments: annotationsOn ? (n.comments ?? []) : [],
    })
  }, [canvasNodes, annotationsOn, baselineSet, architectureArtifact])

  const layout = useMemo(() => autoLayout(canvasNodes, architectureArtifact), [canvasNodes, architectureArtifact])
  const laidOut = layout.nodes
  const baselineNodes = useMemo(
    () => laidOut.filter((node) => baselineSet.size === 0 || baselineSet.has(node.id)),
    [laidOut, baselineSet],
  )
  const customNodes = useMemo(
    () => laidOut.filter((node) => baselineSet.size > 0 && !baselineSet.has(node.id)),
    [laidOut, baselineSet],
  )

  // A node is a "customer addition" if it wasn't in the baseline (first) update
  const rfNodes: Node[] = useMemo(() => [
    ...layout.zoneNodes,
    ...laidOut.map((n) => toRFNode(n, onSelect, baselineSet.size > 0 && !baselineSet.has(n.id))),
  ], [layout.zoneNodes, laidOut, onSelect, baselineSet])

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
  const stageLabel = workspace?.stage?.trim() || (hasNodes ? 'blueprint' : '')
  const baselineLabel = architectureArtifact?.baseline.name || (baselineNodes.length > 0 ? 'Working baseline' : '')
  const riskCount = architectureArtifact?.risks.length ?? workspace?.risks?.length ?? 0
  const openQuestionCount = workspace?.open_questions.length ?? 0

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
            Architecture Canvas
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0, marginLeft: 'auto', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
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
          padding: '10px 16px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: 8,
          background: 'var(--bg-elevated)',
          flexShrink: 0,
        }}>
          {baselineLabel && (
            <StatusChip tone="neutral">{baselineLabel}</StatusChip>
          )}
          <StatusChip tone="accent">
            {customNodes.length} org addition{customNodes.length === 1 ? '' : 's'}
          </StatusChip>
          {stageLabel && (
            <StatusChip tone="neutral">{stageLabel}</StatusChip>
          )}
          {openQuestionCount > 0 && (
            <StatusChip tone="warning">
              {openQuestionCount} open question{openQuestionCount === 1 ? '' : 's'}
            </StatusChip>
          )}
          {riskCount > 0 && (
            <StatusChip tone="warning">
              {riskCount} active risk{riskCount === 1 ? '' : 's'}
            </StatusChip>
          )}
        </div>
      )}

      {/* Canvas body */}
      {!hasNodes ? (
        <CanvasEmpty />
      ) : (
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <CanvasFlow nodes={rfNodes} edges={rfEdges} />
        </div>
      )}

      {selected && (
        <NodeDetailDrawer node={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}

function StatusChip({
  children,
  tone,
}: {
  children: React.ReactNode
  tone: 'neutral' | 'accent' | 'warning'
}) {
  const palette = tone === 'accent'
    ? {
        background: 'rgba(99,102,241,0.12)',
        border: 'rgba(99,102,241,0.24)',
        color: 'var(--accent-strong)',
      }
    : tone === 'warning'
      ? {
          background: 'rgba(245,158,11,0.12)',
          border: 'rgba(245,158,11,0.24)',
          color: 'var(--amber)',
        }
      : {
          background: 'var(--bg)',
          border: 'var(--border)',
          color: 'var(--text-muted)',
        }

  return (
    <span style={{
      padding: '6px 10px',
      borderRadius: 999,
      background: palette.background,
      border: `1px solid ${palette.border}`,
      color: palette.color,
      fontSize: 11,
      fontWeight: 600,
      lineHeight: 1.3,
      whiteSpace: 'nowrap',
    }}>
      {children}
    </span>
  )
}
