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
} from "@xyflow/react";
import {
  Activity,
  Archive,
  Blocks,
  Bot,
  ChartNoAxesCombined,
  CheckCircle2,
  CircleDollarSign,
  CloudCog,
  Database,
  Gauge,
  GitBranch,
  KeyRound,
  Laptop,
  Network,
  PlugZap,
  Route,
  ScrollText,
  ServerCog,
  ShieldCheck,
  TerminalSquare,
  TimerReset,
  UsersRound,
  Workflow,
} from "lucide-react";
import { useMemo } from "react";
import type {
  ArchitectureComponent,
  ArchitectureEdge,
  NodeStatus,
} from "./types";

const icons = {
  activity: Activity,
  archive: Archive,
  blocks: Blocks,
  bot: Bot,
  chart: ChartNoAxesCombined,
  check: CheckCircle2,
  cloud: CloudCog,
  coins: CircleDollarSign,
  database: Database,
  gauge: Gauge,
  git: GitBranch,
  key: KeyRound,
  laptop: Laptop,
  network: Network,
  plug: PlugZap,
  pulse: Activity,
  route: Route,
  scroll: ScrollText,
  server: ServerCog,
  shield: ShieldCheck,
  terminal: TerminalSquare,
  timer: TimerReset,
  users: UsersRound,
  workflow: Workflow,
} as const;

type ArchitectureNodeData = {
  label: string;
  detail: string;
  icon: keyof typeof icons;
  status: NodeStatus;
  isLatest: boolean;
};

type LaneNodeData = {
  label: string;
};

function ArchitectureNode({ data }: NodeProps<Node<ArchitectureNodeData>>) {
  const Icon = icons[data.icon] ?? Bot;
  return (
    <div
      className={`architecture-node status-${data.status} ${data.isLatest ? "is-latest" : ""}`}
    >
      <Handle type="target" position={Position.Left} />
      <div className="node-icon">
        <Icon size={17} strokeWidth={1.8} />
      </div>
      <div className="node-copy">
        <strong>{data.label}</strong>
        <span>{data.detail}</span>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

function LaneNode({ data }: NodeProps<Node<LaneNodeData>>) {
  return (
    <div className="lane-node">
      <span>{data.label}</span>
    </div>
  );
}

const nodeTypes = {
  architecture: ArchitectureNode,
  lane: LaneNode,
};

interface ArchitectureCanvasProps {
  components: ArchitectureComponent[];
  edges: ArchitectureEdge[];
  latestIds: Set<string>;
}

export function ArchitectureCanvas({
  components,
  edges,
  latestIds,
}: ArchitectureCanvasProps) {
  const flowNodes = useMemo<Node[]>(() => {
    const laneNodes: Node[] = [
      ["lane-experience", "Experience", 16, 106],
      ["lane-control", "Control plane", 138, 126],
      ["lane-execution", "Execution", 280, 126],
      ["lane-integrations", "Integrations", 422, 110],
      ["lane-agentops", "AgentOps", 548, 126],
    ].map(([id, label, y, height]) => ({
      id: String(id),
      type: "lane",
      position: { x: 0, y: Number(y) },
      data: { label: String(label) },
      draggable: false,
      selectable: false,
      connectable: false,
      style: { width: 1370, height: Number(height), zIndex: -1 },
    }));

    const componentNodes: Node[] = components.map((item) => ({
      id: item.id,
      type: "architecture",
      position: { x: item.x, y: item.y },
      data: {
        label: item.label,
        detail: item.detail,
        icon: item.icon,
        status: item.status,
        isLatest: latestIds.has(item.id),
      },
      draggable: false,
      style: { width: 214, height: 66 },
    }));

    return [...laneNodes, ...componentNodes];
  }, [components, latestIds]);

  const flowEdges = useMemo<Edge[]>(
    () =>
      edges.map((edge, index) => ({
        id: `${edge.source}-${edge.target}-${index}`,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        animated: latestIds.has(edge.source) || latestIds.has(edge.target),
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 14,
          height: 14,
          color: "#7b8584",
        },
        style: {
          stroke: latestIds.has(edge.source) || latestIds.has(edge.target)
            ? "#147d64"
            : "#9aa2a1",
          strokeWidth: latestIds.has(edge.source) || latestIds.has(edge.target)
            ? 2
            : 1.2,
        },
      })),
    [edges, latestIds],
  );

  return (
    <div className="canvas-shell">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.08 }}
        minZoom={0.42}
        maxZoom={1.25}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#d9ddda" gap={22} size={1} />
        <Controls showInteractive={false} position="bottom-right" />
      </ReactFlow>
    </div>
  );
}
