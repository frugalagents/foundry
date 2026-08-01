'use client';

// React Flow canvas for the approved coding-agent reference architecture.
// Nodes are positioned into the approved layout (governance spine left,
// surfaces top, harness heart center, registry right, execution + gateways +
// external stacked, ops band bottom). Edges auto-route (smoothstep) so they
// never dangle, and animate on the paths a fresh answer just changed. Selecting
// a node raises its block for the questions panel.

import { useMemo } from 'react';
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

export type NodeStatus = 'baseline' | 'added' | 'core' | 'group';

export interface FlowBlock {
  id: string;
  label: string;
  detail: string;
  group: string;       // color group: surface|access|harness|registry|exec|gateway|external|ops
  componentIds?: string[];
  x: number;
  y: number;
  w?: number;
  h?: number;
  active?: boolean;    // engine-added → highlight
  answerable?: boolean;
  heart?: boolean;     // the harness gets the glow
}

export interface FlowWire {
  source: string;
  target: string;
  kind: 'req' | 'sup' | 'gov';
  label?: string;
  animated?: boolean;
  sourceHandle?: string;
  targetHandle?: string;
}

const GROUP_COLOR: Record<string, string> = {
  surface: '#b98cf0', access: '#7d9bff', harness: '#37dd7d', registry: '#2dd4bf',
  exec: '#fb7185', gateway: '#4cc4f5', external: '#8b98ab', ops: '#f0a850',
  experience: '#b98cf0', orchestration: '#37dd7d', model: '#4cc4f5',
  tool: '#2dd4bf', execution: '#fb7185', knowledge: '#8b98ab',
  governance: '#7d9bff', observability: '#f0a850',
};
const WIRE_COLOR: Record<string, string> = { req: '#4cc4f5', sup: '#2dd4bf', gov: '#7d9bff' };

interface BlockNodeData extends Record<string, unknown> {
  block: FlowBlock;
  selected: boolean;
  onSelect: (id: string) => void;
}

function BlockNode({ data }: NodeProps<Node<BlockNodeData>>) {
  const { block, selected, onSelect } = data;
  const color = GROUP_COLOR[block.group] ?? '#8b98ab';
  return (
    <div className="fc-node-shell" style={{ width: block.w ?? 210, minHeight: block.h ?? 62 }}>
      <Handle id="target-top" type="target" position={Position.Top} style={{ opacity: 0 }} />
      <Handle id="target-left" type="target" position={Position.Left} style={{ opacity: 0 }} />
      <Handle id="target-right" type="target" position={Position.Right} style={{ opacity: 0 }} />
      <Handle id="target-bottom" type="target" position={Position.Bottom} style={{ opacity: 0 }} />
      <button
        type="button"
        aria-label={`${block.label}: ${block.detail}`}
        aria-pressed={selected}
        onClick={() => onSelect(block.id)}
        className={`fc-node${block.active ? ' fc-active' : ''}${selected ? ' fc-sel' : ''}${block.heart ? ' fc-heart' : ''}`}
        style={{ ['--fc-ac' as string]: color }}
      >
        <div className="fc-node-body">
          <div className="fc-node-title">
            {block.label}
            {block.active && <span className="fc-badge">added</span>}
            {block.answerable && <span className="fc-q" aria-hidden="true">?</span>}
          </div>
          <div className="fc-node-detail">{block.detail}</div>
        </div>
      </button>
      <Handle id="source-top" type="source" position={Position.Top} style={{ opacity: 0 }} />
      <Handle id="source-left" type="source" position={Position.Left} style={{ opacity: 0 }} />
      <Handle id="source-bottom" type="source" position={Position.Bottom} style={{ opacity: 0 }} />
      <Handle id="source-right" type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

function GroupNode({ data }: NodeProps<Node<{ label: string; group: string }>>) {
  const color = GROUP_COLOR[data.group] ?? '#8b98ab';
  return (
    <div className="fc-group" style={{ ['--fc-ac' as string]: color, width: '100%', height: '100%' }}>
      <span className="fc-group-tag" style={{ background: color }}>{data.label}</span>
    </div>
  );
}

const nodeTypes = { block: BlockNode, group: GroupNode };

interface Props {
  blocks: FlowBlock[];
  wires: FlowWire[];
  groups: { id: string; label: string; group: string; x: number; y: number; w: number; h: number }[];
  selected: string | null;
  onSelect: (id: string) => void;
}

export function FlowCanvas({ blocks, wires, groups, selected, onSelect }: Props) {
  const nodes = useMemo<Node[]>(() => {
    const groupNodes: Node[] = groups.map((g) => ({
      id: g.id,
      type: 'group',
      position: { x: g.x, y: g.y },
      data: { label: g.label, group: g.group },
      draggable: false, selectable: false, connectable: false,
      style: { width: g.w, height: g.h, zIndex: 0 },
    }));
    const blockNodes: Node[] = blocks.map((b) => ({
      id: b.id,
      type: 'block',
      position: { x: b.x, y: b.y },
      data: { block: b, selected: selected === b.id, onSelect },
      draggable: false,
      style: { zIndex: 1 },
    }));
    return [...groupNodes, ...blockNodes];
  }, [blocks, groups, selected, onSelect]);

  const edges = useMemo<Edge[]>(() =>
    wires.map((w, i) => {
      const color = WIRE_COLOR[w.kind];
      return {
        id: `${w.source}-${w.target}-${i}`,
        source: w.source,
        target: w.target,
        sourceHandle: w.sourceHandle,
        targetHandle: w.targetHandle,
        type: 'smoothstep',
        animated: Boolean(w.animated),
        label: w.label,
        labelStyle: { fill: '#7c8899', fontSize: 9, fontFamily: 'var(--font-mono, monospace)' },
        labelBgStyle: { fill: '#0e1116', fillOpacity: 0.9 },
        markerEnd: { type: MarkerType.ArrowClosed, width: 13, height: 13, color },
        style: {
          stroke: color,
          strokeWidth: w.animated ? 2.4 : 1.6,
          strokeDasharray: w.kind === 'sup' ? '6 5' : w.kind === 'gov' ? '3 5' : undefined,
          opacity: w.kind === 'gov' ? 0.55 : 0.8,
        },
      } as Edge;
    }), [wires]);

  return (
    <div className="fc-shell">
      <FlowStyles />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        minZoom={0.2}
        maxZoom={1.5}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1c2531" gap={26} size={1} />
        <Controls showInteractive={false} position="bottom-right" />
      </ReactFlow>
    </div>
  );
}

function FlowStyles() {
  return (
    <style>{`
.fc-shell{position:absolute;inset:0}
.fc-shell .react-flow{background:transparent}
.fc-shell .react-flow__controls{box-shadow:none;border:1px solid #242e3b;border-radius:8px;overflow:hidden}
.fc-shell .react-flow__controls-button{background:#171d27;border-bottom:1px solid #242e3b;color:#a7b2c2}
.fc-shell .react-flow__controls-button:hover{background:#1d2530}
.fc-shell .react-flow__controls-button svg{fill:#a7b2c2}
.fc-node-shell{position:relative}
.fc-node{position:relative;display:flex;flex-direction:column;justify-content:center;width:100%;min-height:inherit;text-align:left;font-family:inherit;background:linear-gradient(180deg,#1d2530,#131922);border:1px solid #242e3b;border-radius:8px;padding:9px 12px;cursor:pointer;transition:transform .16s,border-color .16s,box-shadow .16s}
.fc-node::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--fc-ac)}
.fc-node:hover{transform:translateY(-2px);border-color:var(--fc-ac);box-shadow:0 12px 26px -14px #000}
.fc-node:focus-visible{outline:2px solid var(--fc-ac);outline-offset:3px}
.fc-node.fc-sel{border-color:var(--fc-ac);box-shadow:0 0 0 1px var(--fc-ac),0 12px 26px -14px #000}
.fc-node.fc-active{background:linear-gradient(180deg,#12251c,#0f1f18)}
.fc-node.fc-heart{border-color:#37dd7d88;background:linear-gradient(180deg,#0f2318,#0d1a13);box-shadow:0 0 0 1px #37dd7d22,0 0 70px -30px #37dd7d}
.fc-node-title{font-size:12.5px;font-weight:650;color:#e6e9ef;letter-spacing:-.1px;display:flex;align-items:center;gap:6px}
.fc-node-detail{font-size:10px;color:#7c8899;margin-top:2px;line-height:1.35;white-space:normal}
.fc-badge{font-size:8px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:#0e1a13;background:#37dd7d;padding:2px 5px;border-radius:5px}
.fc-q{margin-left:auto;font-size:11px;font-weight:800;color:#4cc4f5;background:#4cc4f51f;width:16px;height:16px;border-radius:5px;display:grid;place-items:center}
.fc-group{border:1px solid color-mix(in srgb,var(--fc-ac) 30%,transparent);border-radius:16px;background:color-mix(in srgb,var(--fc-ac) 5%,transparent)}
.fc-group-tag{position:absolute;top:10px;left:12px;font-size:9px;font-weight:800;letter-spacing:.11em;text-transform:uppercase;padding:3px 8px;border-radius:6px;color:#07100a}
    `}</style>
  );
}
