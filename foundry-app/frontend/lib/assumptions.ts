import type {
  ArchNode,
  ArchitectureArtifact,
  ConsultingWorkspace,
  WorkspaceAssumption,
  WorkspaceAssumptionOption,
} from './types'

function normalizeAssumptionOption(value: unknown): WorkspaceAssumptionOption | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.id !== 'string' || typeof raw.label !== 'string' || typeof raw.prompt !== 'string') {
    return null
  }
  return {
    id: raw.id,
    label: raw.label,
    prompt: raw.prompt,
  }
}

function normalizeAssumption(value: unknown): WorkspaceAssumption | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  if (typeof raw.id !== 'string' || typeof raw.title !== 'string' || typeof raw.assumed !== 'string') {
    return null
  }
  const confidence = raw.confidence === 'inferred' || raw.confidence === 'confirmed'
    ? raw.confidence
    : 'default'
  return {
    id: raw.id,
    title: raw.title,
    assumed: raw.assumed,
    why: typeof raw.why === 'string' ? raw.why : '',
    impact: typeof raw.impact === 'string' ? raw.impact : '',
    confidence,
    options: Array.isArray(raw.options)
      ? raw.options.map(normalizeAssumptionOption).filter((item): item is WorkspaceAssumptionOption => Boolean(item))
      : [],
  }
}

export function normalizeWorkspaceAssumptions(value: unknown): WorkspaceAssumption[] {
  return Array.isArray(value)
    ? value.map(normalizeAssumption).filter((item): item is WorkspaceAssumption => Boolean(item))
    : []
}

function includesAny(haystack: string, terms: string[]): boolean {
  return terms.some((term) => haystack.includes(term))
}

function buildHaystack(
  workspace: ConsultingWorkspace | null,
  architectureArtifact: ArchitectureArtifact | null,
  canvasNodes: ArchNode[],
): string {
  return [
    workspace?.recommendation ?? '',
    workspace?.blueprint_markdown ?? '',
    ...(workspace?.facts ?? []),
    ...(workspace?.open_questions ?? []),
    ...(workspace?.decisions ?? []),
    ...(workspace?.risks ?? []),
    ...(workspace?.implementation_plan ?? []),
    architectureArtifact?.executive_summary ?? '',
    architectureArtifact?.baseline.name ?? '',
    ...((architectureArtifact?.baseline.layers ?? []).flatMap((layer) => [
      layer.label,
      layer.purpose,
      ...layer.component_labels,
    ])),
    ...((architectureArtifact?.customizations ?? []).flatMap((item) => [
      item.title,
      item.reason,
      item.tradeoff,
      ...item.triggered_by,
    ])),
    ...((architectureArtifact?.decisions ?? []).flatMap((item) => [
      item.decision,
      item.why,
      ...(item.alternatives_rejected ?? []),
    ])),
    ...((architectureArtifact?.risks ?? []).flatMap((item) => [item.risk, item.mitigation])),
    ...((architectureArtifact?.rollout ?? []).flatMap((item) => [item.phase, item.outcome])),
    ...canvasNodes.flatMap((node) => [node.label, node.sublabel ?? '', node.layer ?? '', ...(node.comments ?? []).map((comment) => comment.text)]),
  ]
    .join(' ')
    .toLowerCase()
}

function buildInferredAssumptionCards(
  workspace: ConsultingWorkspace | null,
  architectureArtifact: ArchitectureArtifact | null,
  canvasNodes: ArchNode[],
): WorkspaceAssumption[] {
  const haystack = buildHaystack(workspace, architectureArtifact, canvasNodes)

  const hasDurableSignal = includesAny(haystack, ['durable', 'background', 'workflow', 'queue', 'orchestr'])
  const hasMicroVMSignal = includesAny(haystack, ['microvm', 'micro-vm', 'firecracker'])
  const hasLocalSignal = includesAny(haystack, ['local execution', 'local runner', 'developer machine'])
  const hasStrictApprovalSignal = includesAny(haystack, [
    'approval',
    'gated',
    'human review',
    'progressive trust',
    'hard quota',
    'regulated',
  ])
  const hasKnowledgeSignal = includesAny(haystack, [
    'knowledge layer',
    'org knowledge',
    'standards',
    'retrieval',
    'code intelligence',
  ])
  const hasCISignal = includesAny(haystack, ['ci/cd', 'pr bot', 'phase two', 'pull request', 'ci gate'])

  const taskModel = hasDurableSignal
    ? {
        assumed: 'Durable background agents are part of the target model.',
        why: 'The current architecture already signals workflow-style or long-running execution beyond a single interactive session.',
        confidence: 'inferred' as const,
      }
    : {
        assumed: 'Agents are primarily interactive and session-based.',
        why: 'Nothing in the current conversation requires long-running autonomous work yet, so the simpler default is short-lived interactive execution.',
        confidence: 'default' as const,
      }

  const executionBoundary = hasMicroVMSignal
    ? {
        assumed: 'Execution should run in centrally managed microVM isolation.',
        why: 'The architecture already points toward stronger isolation, usually because of enterprise scale, compliance, or tighter trust boundaries.',
        confidence: 'inferred' as const,
      }
    : hasLocalSignal
      ? {
          assumed: 'Execution stays close to the developer, likely on local or lightly managed runners.',
          why: 'The current direction appears to optimize for speed and developer convenience over centralized isolation.',
          confidence: 'inferred' as const,
        }
      : {
          assumed: 'Execution runs in ephemeral managed containers.',
          why: 'This is the default middle ground when you need central control without the full cost and complexity of microVM isolation.',
          confidence: 'default' as const,
        }

  const approvalModel = hasStrictApprovalSignal
    ? {
        assumed: 'Material changes should hit explicit approval or gated review boundaries.',
        why: 'The conversation already signals tighter governance, approval, or risk controls around what agents are allowed to do autonomously.',
        confidence: 'inferred' as const,
      }
    : {
        assumed: 'Developers can use balanced autonomy with guardrails.',
        why: 'No hard signal yet says every action must be manually approved, so the working assumption is human review on meaningful changes rather than every step.',
        confidence: 'default' as const,
      }

  const knowledgeModel = hasKnowledgeSignal
    ? {
        assumed: 'The platform should inject organization knowledge and standards into the agent loop.',
        why: 'The current direction already suggests knowledge-layer behavior rather than relying only on repo context and tools.',
        confidence: 'inferred' as const,
      }
    : {
        assumed: 'Start repo-first and tool-first, then layer in org knowledge where it materially improves outcomes.',
        why: 'This keeps the first architecture simpler and avoids inventing retrieval or standards systems before there is evidence they are required.',
        confidence: 'default' as const,
      }

  const rolloutModel = hasCISignal
    ? {
        assumed: 'Rollout starts with developer surfaces and expands to PR or CI automation later.',
        why: 'The architecture already hints at an IDE/chat-first motion, which is usually the right order before broader autonomous CI behaviors.',
        confidence: 'inferred' as const,
      }
    : {
        assumed: 'Begin with direct developer workflows before pushing agents deeper into CI/CD.',
        why: 'That is the safer default because it proves value and governance before widening the blast radius.',
        confidence: 'default' as const,
      }

  return [
    {
      id: 'task-model',
      title: 'Task Model',
      assumed: taskModel.assumed,
      why: taskModel.why,
      impact: 'Changing this affects whether the architecture needs durable state, orchestration, retry/recovery, replay, and stronger audit semantics.',
      confidence: taskModel.confidence,
      options: [
        {
          id: 'session-based',
          label: 'Keep Session-Based',
          prompt: 'Change the architecture assumption to interactive session-based agents rather than durable background workflows. Refresh the architecture and blueprint and explain the main tradeoff briefly.',
        },
        {
          id: 'durable',
          label: 'Add Durable Agents',
          prompt: 'Change the architecture assumption to durable background agents that can survive beyond a single chat session. Refresh the architecture and blueprint and explain what components this adds.',
        },
      ],
    },
    {
      id: 'execution-boundary',
      title: 'Execution Boundary',
      assumed: executionBoundary.assumed,
      why: executionBoundary.why,
      impact: 'Changing this shifts the trust boundary, cost profile, isolation strength, and operational complexity of the platform.',
      confidence: executionBoundary.confidence,
      options: [
        {
          id: 'containers',
          label: 'Use Containers',
          prompt: 'Change the execution assumption to ephemeral centrally managed containers. Refresh the architecture and explain what becomes simpler or weaker versus the current design.',
        },
        {
          id: 'microvms',
          label: 'Use MicroVMs',
          prompt: 'Change the execution assumption to centrally managed microVM isolation. Refresh the architecture and explain why this stronger boundary is worth the extra complexity.',
        },
      ],
    },
    {
      id: 'approval-model',
      title: 'Approval Model',
      assumed: approvalModel.assumed,
      why: approvalModel.why,
      impact: 'Changing this affects developer friction, autonomy, audit posture, and how aggressive the agent can be in code, PR, or CI workflows.',
      confidence: approvalModel.confidence,
      options: [
        {
          id: 'balanced-autonomy',
          label: 'More Autonomy',
          prompt: 'Adjust the architecture assumption toward balanced developer autonomy with guardrails instead of tighter manual approvals. Refresh the architecture and call out the governance implications.',
        },
        {
          id: 'tighter-approvals',
          label: 'Tighter Approvals',
          prompt: 'Adjust the architecture assumption toward explicit approval or gated review for material agent actions. Refresh the architecture and explain what controls this adds.',
        },
      ],
    },
    {
      id: 'knowledge-model',
      title: 'Knowledge Model',
      assumed: knowledgeModel.assumed,
      why: knowledgeModel.why,
      impact: 'Changing this determines whether the platform stays repo-centric or adds standards injection, org knowledge retrieval, and more opinionated context management.',
      confidence: knowledgeModel.confidence,
      options: [
        {
          id: 'repo-first',
          label: 'Stay Repo-First',
          prompt: 'Keep the architecture repo-first and tool-first rather than adding an organization knowledge layer now. Refresh the architecture and explain what capability is deferred.',
        },
        {
          id: 'org-knowledge',
          label: 'Add Org Knowledge',
          prompt: 'Add an organization knowledge and standards layer to the architecture. Refresh the architecture and explain what new controls or dependencies this introduces.',
        },
      ],
    },
    {
      id: 'rollout-model',
      title: 'Rollout Path',
      assumed: rolloutModel.assumed,
      why: rolloutModel.why,
      impact: 'Changing this alters adoption risk, blast radius, and how quickly the platform moves from advisory help into broader automation.',
      confidence: rolloutModel.confidence,
      options: [
        {
          id: 'ide-first',
          label: 'IDE First',
          prompt: 'Keep the rollout assumption focused on IDE and direct developer workflows before deeper PR or CI automation. Refresh the architecture and rollout plan accordingly.',
        },
        {
          id: 'include-ci',
          label: 'Push Into CI',
          prompt: 'Change the rollout assumption to include PR or CI automation earlier in the platform rollout. Refresh the architecture and rollout plan and explain the added risk.',
        },
      ],
    },
  ]
}

export function buildAssumptionCards(
  workspace: ConsultingWorkspace | null,
  architectureArtifact: ArchitectureArtifact | null,
  canvasNodes: ArchNode[],
): WorkspaceAssumption[] {
  const inferred = buildInferredAssumptionCards(workspace, architectureArtifact, canvasNodes)
  const authored = normalizeWorkspaceAssumptions(workspace?.assumptions)

  if (authored.length === 0) {
    return inferred
  }

  const inferredById = new Map(inferred.map((item) => [item.id, item]))
  return authored.map((item) => {
    const fallback = inferredById.get(item.id)
    if (!fallback) return item
    return {
      ...fallback,
      ...item,
      why: item.why || fallback.why,
      impact: item.impact || fallback.impact,
      options: item.options.length > 0 ? item.options : fallback.options,
    }
  })
}
