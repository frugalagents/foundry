export type DecisionId =
  | "execution"
  | "boundaries"
  | "routing"
  | "tools"
  | "outcomes";

export type NodeStatus = "confirmed" | "proposed" | "unresolved";

export interface ArchitectureComponent {
  id: string;
  label: string;
  detail: string;
  lane: "Experience" | "Control plane" | "Execution" | "Integrations" | "AgentOps";
  icon: string;
  status: NodeStatus;
  x: number;
  y: number;
}

export interface ArchitectureEdge {
  source: string;
  target: string;
}

export interface ServiceCandidate {
  component: string;
  purpose: string;
  recommended: string[];
  alternatives: string[];
}

export interface DecisionOption {
  id: string;
  label: string;
  description: string;
  consequence: string;
  recommended?: boolean;
  components: ArchitectureComponent[];
  removeComponents?: string[];
  edges: ArchitectureEdge[];
  services: ServiceCandidate[];
}

export interface DecisionDefinition {
  id: DecisionId;
  number: string;
  category: string;
  title: string;
  recommendation: string;
  whyNow: string;
  options: DecisionOption[];
}

export interface AdvisorState {
  answers: Partial<Record<DecisionId, string>>;
  lastDecision?: DecisionId;
}

export interface Economics {
  monthlyTasks: number;
  effectiveTokensBillions: number;
  modelSpend: number;
  platformSpend: number;
  costPerSuccessfulTask: number;
  cacheHitRate: number;
  note: string;
}

export interface OutcomeMetric {
  label: string;
  value: string;
  target: string;
  tone: "positive" | "warning" | "neutral";
}

export interface DerivedArchitecture {
  components: ArchitectureComponent[];
  edges: ArchitectureEdge[];
  services: ServiceCandidate[];
  economics: Economics;
  outcomes: OutcomeMetric[];
}
