import {
  baseComponents,
  baseEdges,
  baseServices,
  decisions,
} from "./catalog";
import type {
  AdvisorState,
  ArchitectureComponent,
  ArchitectureEdge,
  DecisionDefinition,
  DerivedArchitecture,
  Economics,
  OutcomeMetric,
  ServiceCandidate,
} from "./types";

const uniqueById = <T extends { id: string }>(items: T[]): T[] =>
  Array.from(new Map(items.map((item) => [item.id, item])).values());

const uniqueEdges = (edges: ArchitectureEdge[]): ArchitectureEdge[] =>
  Array.from(
    new Map(edges.map((edge) => [`${edge.source}:${edge.target}`, edge])).values(),
  );

const uniqueServices = (services: ServiceCandidate[]): ServiceCandidate[] =>
  Array.from(
    new Map(
      services.map((service) => [
        `${service.component}:${service.purpose}`,
        service,
      ]),
    ).values(),
  );

export const getDecision = (id: string): DecisionDefinition | undefined =>
  decisions.find((decision) => decision.id === id);

export const getNextDecision = (
  state: AdvisorState,
): DecisionDefinition | undefined =>
  decisions.find((decision) => state.answers[decision.id] === undefined);

export const getSelectedOption = (
  state: AdvisorState,
  decision: DecisionDefinition,
) => {
  const optionId = state.answers[decision.id];
  return decision.options.find((option) => option.id === optionId);
};

const deriveEconomics = (state: AdvisorState): Economics => {
  const routing = state.answers.routing;
  const execution = state.answers.execution;
  const outcomes = state.answers.outcomes;

  const profiles = {
    adaptive: { blendedRate: 5.9, cacheHitRate: 18, successRate: 0.74 },
    manual: { blendedRate: 8.4, cacheHitRate: 0, successRate: 0.69 },
    premium: { blendedRate: 12.5, cacheHitRate: 4, successRate: 0.78 },
    unresolved: { blendedRate: 8.4, cacheHitRate: 0, successRate: 0.68 },
  };
  const profile =
    profiles[routing as keyof typeof profiles] ?? profiles.unresolved;
  const monthlyTasks = 350_000;
  const rawTokensBillions = monthlyTasks * 32_000 / 1_000_000_000;
  const effectiveTokensBillions =
    rawTokensBillions * (1 - profile.cacheHitRate / 100);
  const modelSpend = effectiveTokensBillions * 1000 * profile.blendedRate;
  const executionSpend =
    execution === "cloud" ? 48_000 : execution === "hybrid" ? 31_000 : 12_000;
  const outcomeSpend = outcomes === "balanced" ? 14_000 : 8_000;
  const platformSpend = executionSpend + outcomeSpend;
  const successfulTasks = monthlyTasks * profile.successRate;

  return {
    monthlyTasks,
    effectiveTokensBillions: Number(effectiveTokensBillions.toFixed(1)),
    modelSpend: Math.round(modelSpend),
    platformSpend,
    costPerSuccessfulTask: Number(
      ((modelSpend + platformSpend) / successfulTasks).toFixed(2),
    ),
    cacheHitRate: profile.cacheHitRate,
    note: "Illustrative planning model: 350k tasks/month, 32k tokens/task. Replace with measured workload data.",
  };
};

const deriveOutcomes = (state: AdvisorState): OutcomeMetric[] => {
  const routing = state.answers.routing;
  const tools = state.answers.tools;
  const outcomes = state.answers.outcomes;
  const acceptance =
    routing === "premium" ? 78 : routing === "adaptive" ? 74 : 69;
  const intervention = tools === "governed" ? 16 : 22;

  return [
    {
      label: "Accepted change rate",
      value: outcomes ? `${acceptance}%` : "Not instrumented",
      target: "Target >= 75%",
      tone: acceptance >= 75 ? "positive" : "warning",
    },
    {
      label: "Cost / successful task",
      value: outcomes ? `$${deriveEconomics(state).costPerSuccessfulTask}` : "Not instrumented",
      target: "Target <= $0.40",
      tone: deriveEconomics(state).costPerSuccessfulTask <= 0.4 ? "positive" : "warning",
    },
    {
      label: "Human intervention",
      value: tools ? `${intervention}%` : "Not instrumented",
      target: "Target <= 20%",
      tone: intervention <= 20 ? "positive" : "warning",
    },
    {
      label: "Issue to merge",
      value: outcomes ? "5.8 hr" : "Not instrumented",
      target: "Target <= 8 hr",
      tone: "positive",
    },
  ];
};

export const deriveArchitecture = (
  state: AdvisorState,
): DerivedArchitecture => {
  let components: ArchitectureComponent[] = [...baseComponents];
  let edges: ArchitectureEdge[] = [...baseEdges];
  let services: ServiceCandidate[] = [...baseServices];

  for (const decision of decisions) {
    const selected = getSelectedOption(state, decision);
    if (!selected) continue;

    const removals = new Set(selected.removeComponents ?? []);
    components = components.filter((item) => !removals.has(item.id));
    edges = edges.filter(
      (edge) => !removals.has(edge.source) && !removals.has(edge.target),
    );
    components.push(...selected.components);
    edges.push(...selected.edges);
    services.push(...selected.services);
  }

  const activeIds = new Set(components.map((item) => item.id));
  edges = edges.filter(
    (edge) => activeIds.has(edge.source) && activeIds.has(edge.target),
  );

  return {
    components: uniqueById(components),
    edges: uniqueEdges(edges),
    services: uniqueServices(services),
    economics: deriveEconomics(state),
    outcomes: deriveOutcomes(state),
  };
};

export const applyDecision = (
  state: AdvisorState,
  decisionId: DecisionDefinition["id"],
  optionId: string,
): AdvisorState => {
  const decision = getDecision(decisionId);
  if (!decision?.options.some((option) => option.id === optionId)) {
    throw new Error(`Unknown option ${optionId} for decision ${decisionId}`);
  }

  return {
    answers: {
      ...state.answers,
      [decisionId]: optionId,
    },
    lastDecision: decisionId,
  };
};

export const getLatestComponentIds = (state: AdvisorState): Set<string> => {
  if (!state.lastDecision) return new Set();
  const decision = getDecision(state.lastDecision);
  const selected = decision ? getSelectedOption(state, decision) : undefined;
  return new Set(selected?.components.map((item) => item.id) ?? []);
};
