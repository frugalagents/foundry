'use client'

import { hasAdvisoryCaseContent } from './advisory-case'
import { normalizeWorkspace } from './message-analysis'
import type {
  AdvisoryCase,
  AdvisoryDecision,
  AdvisoryOutputPack,
  ArchEdge,
  ArchNode,
  ArchitectureArtifact,
  ConsultingWorkspace,
  Message,
  WorkspaceAssumption,
} from './types'

type ExportFile = {
  name: string
  content: string
  mimeType: string
}

export type SessionExportContext = {
  activeSessionId: string | null
  sessionTitle?: string | null
  workspace: ConsultingWorkspace | null
  architectureArtifact: ArchitectureArtifact | null
  canvasNodes: ArchNode[]
  canvasEdges: ArchEdge[]
  baselineNodeIds: string[]
  messages: Message[]
}

export function hasOutputPackContent(pack: AdvisoryOutputPack) {
  return Boolean(
    pack.executive_summary ||
    pack.recommendation_memo ||
    pack.architecture_narrative ||
    pack.key_decisions.length > 0 ||
    pack.risks_and_mitigations.length > 0 ||
    pack.rollout_30_90_180.length > 0 ||
    pack.operating_principles.length > 0 ||
    pack.control_checklist.length > 0,
  )
}

export function buildExportMarkdown(outputPack: AdvisoryOutputPack | null, fallbackMarkdown: string) {
  if (!outputPack || !hasOutputPackContent(outputPack)) {
    return fallbackMarkdown
  }

  const lines: string[] = []

  if (outputPack.executive_summary) {
    lines.push('## Executive Summary', '', outputPack.executive_summary, '')
  }
  if (outputPack.recommendation_memo) {
    lines.push('## Recommendation Memo', '', outputPack.recommendation_memo, '')
  }
  if (outputPack.architecture_narrative) {
    lines.push('## Architecture Narrative', '', outputPack.architecture_narrative, '')
  }
  if (outputPack.key_decisions.length) {
    lines.push('## Key Decisions', '')
    outputPack.key_decisions.forEach((item, index) => lines.push(`${index + 1}. ${item}`))
    lines.push('')
  }
  if (outputPack.risks_and_mitigations.length) {
    lines.push('## Risks And Mitigations', '')
    outputPack.risks_and_mitigations.forEach((item) => {
      lines.push(`- **${item.risk}**${item.mitigation ? `: ${item.mitigation}` : ''}`)
    })
    lines.push('')
  }
  if (outputPack.open_questions.length) {
    lines.push('## Open Questions', '')
    outputPack.open_questions.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }
  if (outputPack.rollout_30_90_180.length) {
    lines.push('## 30 / 90 / 180 Day Rollout', '')
    outputPack.rollout_30_90_180.forEach((item) => lines.push(`- **${item.horizon}**: ${item.outcome}`))
    lines.push('')
  }
  if (outputPack.operating_principles.length) {
    lines.push('## Operating Principles', '')
    outputPack.operating_principles.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }
  if (outputPack.control_checklist.length) {
    lines.push('## Control Checklist', '')
    outputPack.control_checklist.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }

  if (hasTechnicalBlueprintTables(fallbackMarkdown)) {
    lines.push(fallbackMarkdown.trim(), '')
  }

  return lines.join('\n').trim()
}

export function buildFallbackBlueprint(
  workspace: ConsultingWorkspace,
  architectureArtifact: ArchitectureArtifact | null,
): string {
  const lines: string[] = []
  const baselineName = architectureArtifact?.baseline.name || 'Working baseline'

  if (
    !workspace.recommendation &&
    !workspace.blueprint_markdown &&
    !architectureArtifact?.executive_summary &&
    workspace.decisions.length === 0 &&
    workspace.implementation_plan.length === 0
  ) {
    return ''
  }

  lines.push('## Technical Blueprint')
  lines.push('')

  if (workspace.recommendation) {
    lines.push('### Current Direction')
    lines.push(workspace.recommendation)
    lines.push('')
  }

  if (architectureArtifact?.executive_summary) {
    lines.push('### Executive Summary')
    lines.push(architectureArtifact.executive_summary)
    lines.push('')
  }

  lines.push('### Baseline')
  lines.push(`**${baselineName}**`)
  lines.push('')

  if (architectureArtifact?.baseline.layers.length) {
    for (const layer of architectureArtifact.baseline.layers) {
      const components = layer.component_labels.join(', ')
      lines.push(`- **${layer.label}**: ${components || 'TBD'}`)
      if (layer.purpose) lines.push(`  ${layer.purpose}`)
    }
    lines.push('')
  }

  if ((architectureArtifact?.customizations.length ?? 0) > 0) {
    lines.push('### Added For This Organization')
    lines.push('')
    for (const item of architectureArtifact?.customizations ?? []) {
      lines.push(`- **${item.title}** (${item.layer})`)
      lines.push(`  Reason: ${item.reason}`)
      if (item.tradeoff) lines.push(`  Tradeoff: ${item.tradeoff}`)
    }
    lines.push('')
  }

  if (workspace.facts.length > 0) {
    lines.push('### Confirmed Facts')
    lines.push(...workspace.facts.map((fact) => `- ${fact}`))
    lines.push('')
  }

  if (workspace.decisions.length > 0 || (architectureArtifact?.decisions.length ?? 0) > 0) {
    lines.push('### Key Decisions')
    lines.push(
      ...(architectureArtifact?.decisions.length
        ? architectureArtifact.decisions.map((item) =>
            `- **${item.decision}**${item.why ? `: ${item.why}` : ''}`,
          )
        : workspace.decisions.map((decision) => `- ${decision}`)),
    )
    lines.push('')
  }

  if (workspace.risks.length > 0 || (architectureArtifact?.risks.length ?? 0) > 0) {
    lines.push('### Risks And Tradeoffs')
    lines.push(
      ...(architectureArtifact?.risks.length
        ? architectureArtifact.risks.map((item) =>
            `- **${item.risk}**${item.mitigation ? `: ${item.mitigation}` : ''}`,
          )
        : workspace.risks.map((risk) => `- ${risk}`)),
    )
    lines.push('')
  }

  if (workspace.implementation_plan.length > 0 || (architectureArtifact?.rollout.length ?? 0) > 0) {
    lines.push('### Rollout Plan')
    lines.push(
      ...(architectureArtifact?.rollout.length
        ? architectureArtifact.rollout.map((phase, index) => `${index + 1}. **${phase.phase}**: ${phase.outcome}`)
        : workspace.implementation_plan.map((step, index) => `${index + 1}. ${step}`)),
    )
    lines.push('')
  }

  if (workspace.open_questions.length > 0) {
    lines.push('### Open Questions')
    lines.push(...workspace.open_questions.map((question) => `- ${question}`))
    lines.push('')
  }

  return lines.join('\n').trim()
}

export function hasSessionExportContent(context: SessionExportContext) {
  const workspace = normalizeWorkspace(context.workspace)
  return Boolean(
    context.activeSessionId &&
    (
      workspace.recommendation ||
      workspace.blueprint_markdown ||
      workspace.facts.length > 0 ||
      workspace.open_questions.length > 0 ||
      workspace.decisions.length > 0 ||
      workspace.risks.length > 0 ||
      workspace.implementation_plan.length > 0 ||
      context.architectureArtifact ||
      context.canvasNodes.length > 0 ||
      context.messages.length > 0
    )
  )
}

export async function downloadSessionBrief(context: SessionExportContext) {
  const slug = slugify(context.sessionTitle || context.activeSessionId || 'foundry-session')
  const files = buildSessionExportFiles(context, slug)
  const blob = buildZipBlob(files)
  downloadBlob(`${slug}-brief.zip`, blob)
}

function buildSessionExportFiles(context: SessionExportContext, slug: string): ExportFile[] {
  const workspace = normalizeWorkspace(context.workspace)
  const advisoryCase: AdvisoryCase | null = hasAdvisoryCaseContent(workspace.advisory_case)
    ? (workspace.advisory_case ?? null)
    : null
  const outputPack = advisoryCase?.output_pack ?? null
  const fallbackBlueprint = (workspace.blueprint_markdown?.trim() || buildFallbackBlueprint(workspace, context.architectureArtifact)).trim()
  const blueprintMarkdown = buildExportMarkdown(outputPack, fallbackBlueprint)
  const folder = `${slug}/`

  const files: ExportFile[] = []
  maybePush(files, folder, 'brief.md', blueprintMarkdown, 'text/markdown;charset=utf-8')
  maybePush(files, folder, 'recommendation.md', buildRecommendationMarkdown(advisoryCase, workspace), 'text/markdown;charset=utf-8')
  maybePush(files, folder, 'readout.md', buildReadoutMarkdown(advisoryCase), 'text/markdown;charset=utf-8')
  maybePush(files, folder, 'architecture.md', buildArchitectureMarkdown(context.architectureArtifact, context.canvasNodes, context.baselineNodeIds), 'text/markdown;charset=utf-8')
  maybePush(files, folder, 'decisions.md', buildDecisionsMarkdown(advisoryCase, context.architectureArtifact, workspace), 'text/markdown;charset=utf-8')
  maybePush(files, folder, 'risks.md', buildRisksMarkdown(advisoryCase, context.architectureArtifact, workspace), 'text/markdown;charset=utf-8')
  maybePush(files, folder, 'assumptions.md', buildAssumptionsMarkdown(workspace.assumptions ?? []), 'text/markdown;charset=utf-8')
  maybePush(files, folder, 'open-questions.md', buildOpenQuestionsMarkdown(advisoryCase, workspace), 'text/markdown;charset=utf-8')
  maybePush(files, folder, 'rollout.md', buildRolloutMarkdown(outputPack, context.architectureArtifact, workspace), 'text/markdown;charset=utf-8')
  maybePush(files, folder, 'maturity.md', buildMaturityMarkdown(advisoryCase), 'text/markdown;charset=utf-8')
  maybePush(files, folder, 'delta.md', buildDeltaMarkdown(advisoryCase), 'text/markdown;charset=utf-8')
  maybePush(files, folder, 'messages.md', buildMessagesMarkdown(context.messages), 'text/markdown;charset=utf-8')

  files.push({
    name: `${folder}architecture.json`,
    content: JSON.stringify({
      session_id: context.activeSessionId,
      baseline_node_ids: context.baselineNodeIds,
      architecture_artifact: context.architectureArtifact,
      nodes: context.canvasNodes,
      edges: context.canvasEdges,
    }, null, 2),
    mimeType: 'application/json;charset=utf-8',
  })

  files.push({
    name: `${folder}session.json`,
    content: JSON.stringify({
      session_id: context.activeSessionId,
      title: context.sessionTitle ?? context.activeSessionId,
      exported_at: new Date().toISOString(),
      workspace,
      architecture_artifact: context.architectureArtifact,
      canvas: {
        baseline_node_ids: context.baselineNodeIds,
        nodes: context.canvasNodes,
        edges: context.canvasEdges,
      },
      messages: context.messages,
    }, null, 2),
    mimeType: 'application/json;charset=utf-8',
  })

  return files
}

function maybePush(
  files: ExportFile[],
  folder: string,
  name: string,
  content: string,
  mimeType: string,
) {
  const trimmed = content.trim()
  if (!trimmed) return
  files.push({
    name: `${folder}${name}`,
    content: trimmed.endsWith('\n') ? trimmed : `${trimmed}\n`,
    mimeType,
  })
}

function buildRecommendationMarkdown(advisoryCase: AdvisoryCase | null, workspace: ConsultingWorkspace) {
  if (!advisoryCase && !workspace.recommendation) return ''

  const lines: string[] = ['# Recommendation', '']
  const recommendation = advisoryCase?.recommendation

  if (recommendation?.summary || workspace.recommendation) {
    lines.push('## Primary Recommendation', '', recommendation?.summary || workspace.recommendation, '')
  }
  if (recommendation?.why_this) {
    lines.push('## Why This', '', recommendation.why_this, '')
  }
  if (recommendation?.why_not) {
    lines.push('## Why Not The Alternatives', '', recommendation.why_not, '')
  }
  if (recommendation?.confidence) {
    lines.push('## Confidence', '', `**${capitalize(recommendation.confidence)}**${recommendation.confidence_reason ? `: ${recommendation.confidence_reason}` : ''}`, '')
  }
  if (recommendation?.change_triggers.length) {
    lines.push('## What Would Change This', '')
    recommendation.change_triggers.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }

  if (advisoryCase?.alternatives.length) {
    lines.push('## Alternatives', '')
    advisoryCase.alternatives.forEach((alternative) => {
      lines.push(`### ${alternative.title}`)
      if (alternative.position) lines.push(`Position: ${capitalize(alternative.position)}`)
      if (alternative.summary) lines.push('', alternative.summary)
      if (alternative.benefits.length) {
        lines.push('', 'Benefits')
        alternative.benefits.forEach((item) => lines.push(`- ${item}`))
      }
      if (alternative.risks.length) {
        lines.push('', 'Risks')
        alternative.risks.forEach((item) => lines.push(`- ${item}`))
      }
      if (alternative.operational_burden) {
        lines.push('', `Operational burden: ${alternative.operational_burden}`)
      }
      if (alternative.governance_implications) {
        lines.push(`Governance implications: ${alternative.governance_implications}`)
      }
      if (alternative.best_fit_conditions.length) {
        lines.push('Best fit conditions')
        alternative.best_fit_conditions.forEach((item) => lines.push(`- ${item}`))
      }
      lines.push('')
    })
  }

  return lines.join('\n').trim()
}

function buildReadoutMarkdown(advisoryCase: AdvisoryCase | null) {
  const readout = advisoryCase?.readout
  if (!readout) return ''
  if (
    !readout.current_recommendation &&
    readout.important_decisions.length === 0 &&
    readout.biggest_risks.length === 0 &&
    readout.open_questions.length === 0 &&
    !readout.rollout_summary &&
    !readout.architecture_snapshot
  ) {
    return ''
  }

  const lines: string[] = ['# Readout', '']
  if (readout.current_recommendation) {
    lines.push('## Current Recommendation', '', readout.current_recommendation, '')
  }
  if (readout.architecture_snapshot) {
    lines.push('## Architecture Snapshot', '', readout.architecture_snapshot, '')
  }
  if (readout.important_decisions.length) {
    lines.push('## Important Decisions', '')
    readout.important_decisions.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }
  if (readout.biggest_risks.length) {
    lines.push('## Biggest Risks', '')
    readout.biggest_risks.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }
  if (readout.open_questions.length) {
    lines.push('## Open Questions', '')
    readout.open_questions.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }
  if (readout.rollout_summary) {
    lines.push('## Rollout Summary', '', readout.rollout_summary, '')
  }
  return lines.join('\n').trim()
}

function buildArchitectureMarkdown(
  architectureArtifact: ArchitectureArtifact | null,
  canvasNodes: ArchNode[],
  baselineNodeIds: string[],
) {
  if (!architectureArtifact && canvasNodes.length === 0) return ''

  const baselineSet = new Set(baselineNodeIds)
  const customerAdditions = canvasNodes.filter((node) => node.type === 'arch' && baselineSet.size > 0 && !baselineSet.has(node.id))
  const lines: string[] = ['# Architecture', '']

  if (architectureArtifact?.executive_summary) {
    lines.push('## Executive Summary', '', architectureArtifact.executive_summary, '')
  }

  if (architectureArtifact?.baseline.name || architectureArtifact?.baseline.layers.length) {
    lines.push('## Baseline')
    if (architectureArtifact?.baseline.name) {
      lines.push('', `**${architectureArtifact.baseline.name}**`, '')
    } else {
      lines.push('')
    }
    architectureArtifact?.baseline.layers.forEach((layer) => {
      lines.push(`### ${layer.label}`)
      if (layer.purpose) lines.push(layer.purpose)
      if (layer.component_labels.length) {
        layer.component_labels.forEach((item) => lines.push(`- ${item}`))
      }
      lines.push('')
    })
  }

  if (architectureArtifact?.customizations.length || customerAdditions.length) {
    lines.push('## Customer Additions', '')
    architectureArtifact?.customizations.forEach((item) => {
      lines.push(`### ${item.title}`)
      if (item.layer) lines.push(`Layer: ${item.layer}`)
      if (item.reason) lines.push(`Reason: ${item.reason}`)
      if (item.tradeoff) lines.push(`Tradeoff: ${item.tradeoff}`)
      if (item.triggered_by.length) {
        lines.push('Triggered by')
        item.triggered_by.forEach((trigger) => lines.push(`- ${trigger}`))
      }
      lines.push('')
    })

    if (customerAdditions.length) {
      lines.push('### Added Components')
      customerAdditions.forEach((node) => {
        lines.push(`- ${node.label}${node.layer ? ` (${node.layer})` : ''}`)
      })
      lines.push('')
    }
  }

  if (architectureArtifact?.decisions.length) {
    lines.push('## Architecture Decisions', '')
    architectureArtifact.decisions.forEach((item) => {
      lines.push(`- **${item.decision}**${item.why ? `: ${item.why}` : ''}`)
    })
    lines.push('')
  }

  if (architectureArtifact?.risks.length) {
    lines.push('## Architecture Risks', '')
    architectureArtifact.risks.forEach((item) => {
      lines.push(`- **${item.risk}**${item.mitigation ? `: ${item.mitigation}` : ''}`)
    })
    lines.push('')
  }

  if (architectureArtifact?.rollout.length) {
    lines.push('## Architecture Rollout', '')
    architectureArtifact.rollout.forEach((phase, index) => {
      lines.push(`${index + 1}. **${phase.phase}**: ${phase.outcome}`)
    })
    lines.push('')
  }

  return lines.join('\n').trim()
}

function buildDecisionsMarkdown(
  advisoryCase: AdvisoryCase | null,
  architectureArtifact: ArchitectureArtifact | null,
  workspace: ConsultingWorkspace,
) {
  if (
    !advisoryCase?.decisions.length &&
    !(architectureArtifact?.decisions.length) &&
    workspace.decisions.length === 0
  ) {
    return ''
  }

  const lines: string[] = ['# Decisions', '']

  if (advisoryCase?.decisions.length) {
    lines.push('## Decision Log', '')
    advisoryCase.decisions.forEach((decision, index) => {
      appendAdvisoryDecision(lines, decision, index + 1)
    })
  }

  if (architectureArtifact?.decisions.length) {
    lines.push('## Architecture Decisions', '')
    architectureArtifact.decisions.forEach((item) => {
      lines.push(`- **${item.decision}**${item.why ? `: ${item.why}` : ''}`)
      if (item.alternatives_rejected?.length) {
        item.alternatives_rejected.forEach((alternative) => lines.push(`  - Rejected: ${alternative}`))
      }
    })
    lines.push('')
  }

  if (workspace.decisions.length) {
    lines.push('## Workspace Decisions', '')
    workspace.decisions.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }

  return lines.join('\n').trim()
}

function appendAdvisoryDecision(lines: string[], decision: AdvisoryDecision, index: number) {
  lines.push(`### Decision ${index}`)
  lines.push(`Statement: ${decision.statement}`)
  if (decision.recommendation) lines.push(`Recommendation: ${decision.recommendation}`)
  if (decision.why) lines.push(`Why: ${decision.why}`)
  if (decision.options_considered.length) {
    lines.push('Options considered')
    decision.options_considered.forEach((item) => lines.push(`- ${item}`))
  }
  if (decision.tradeoffs_accepted.length) {
    lines.push('Tradeoffs accepted')
    decision.tradeoffs_accepted.forEach((item) => lines.push(`- ${item}`))
  }
  if (decision.owner) lines.push(`Owner: ${decision.owner}`)
  if (decision.open_dependency) lines.push(`Open dependency: ${decision.open_dependency}`)
  lines.push('')
}

function buildRisksMarkdown(
  advisoryCase: AdvisoryCase | null,
  architectureArtifact: ArchitectureArtifact | null,
  workspace: ConsultingWorkspace,
) {
  if (!advisoryCase?.risks.length && !(architectureArtifact?.risks.length) && workspace.risks.length === 0) {
    return ''
  }

  const lines: string[] = ['# Risks', '']
  if (advisoryCase?.risks.length) {
    lines.push('## Advisory Risks', '')
    advisoryCase.risks.forEach((item) => {
      lines.push(`- **${item.risk}**`)
      if (item.category || item.severity) {
        lines.push(`  Category: ${item.category || 'Unspecified'}${item.severity ? ` | Severity: ${capitalize(item.severity)}` : ''}`)
      }
      if (item.mitigation) lines.push(`  Mitigation: ${item.mitigation}`)
    })
    lines.push('')
  }
  if (architectureArtifact?.risks.length) {
    lines.push('## Architecture Risks', '')
    architectureArtifact.risks.forEach((item) => {
      lines.push(`- **${item.risk}**${item.mitigation ? `: ${item.mitigation}` : ''}`)
    })
    lines.push('')
  }
  if (workspace.risks.length) {
    lines.push('## Workspace Risks', '')
    workspace.risks.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }
  return lines.join('\n').trim()
}

function buildAssumptionsMarkdown(assumptions: WorkspaceAssumption[]) {
  if (assumptions.length === 0) return ''

  const lines: string[] = ['# Assumptions', '']
  assumptions.forEach((assumption) => {
    lines.push(`## ${assumption.title}`)
    lines.push(`Assumed: ${assumption.assumed}`)
    if (assumption.confidence) lines.push(`Confidence: ${capitalize(assumption.confidence)}`)
    if (assumption.impact_level) lines.push(`Impact level: ${capitalize(assumption.impact_level)}`)
    if (assumption.drives_architecture) lines.push('Drives architecture: Yes')
    if (assumption.validation_priority) lines.push(`Validate: ${capitalize(assumption.validation_priority)}`)
    if (assumption.why) lines.push('', `Why: ${assumption.why}`)
    if (assumption.impact) lines.push(`Impact if wrong: ${assumption.impact}`)
    if (assumption.options.length) {
      lines.push('', 'Validation prompts')
      assumption.options.forEach((option) => lines.push(`- ${option.label}: ${option.prompt}`))
    }
    lines.push('')
  })
  return lines.join('\n').trim()
}

function buildOpenQuestionsMarkdown(advisoryCase: AdvisoryCase | null, workspace: ConsultingWorkspace) {
  const questions = dedupe([
    ...workspace.open_questions,
    ...(advisoryCase?.output_pack.open_questions ?? []),
    ...(advisoryCase?.readout.open_questions ?? []),
  ])

  if (questions.length === 0 && !advisoryCase?.next_best_question?.question) return ''

  const lines: string[] = ['# Open Questions', '']
  if (questions.length) {
    questions.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }
  if (advisoryCase?.next_best_question?.question) {
    lines.push('## Next Best Question', '', advisoryCase.next_best_question.question)
    if (advisoryCase.next_best_question.why_it_matters) {
      lines.push('', `Why it matters: ${advisoryCase.next_best_question.why_it_matters}`)
    }
    lines.push('')
  }
  return lines.join('\n').trim()
}

function buildRolloutMarkdown(
  outputPack: AdvisoryOutputPack | null,
  architectureArtifact: ArchitectureArtifact | null,
  workspace: ConsultingWorkspace,
) {
  const lines: string[] = ['# Rollout', '']
  let hasContent = false

  if (outputPack?.rollout_30_90_180.length) {
    hasContent = true
    lines.push('## 30 / 90 / 180 Day Rollout', '')
    outputPack.rollout_30_90_180.forEach((item) => lines.push(`- **${item.horizon}**: ${item.outcome}`))
    lines.push('')
  }

  if (architectureArtifact?.rollout.length) {
    hasContent = true
    lines.push('## Architecture Rollout', '')
    architectureArtifact.rollout.forEach((phase, index) => lines.push(`${index + 1}. **${phase.phase}**: ${phase.outcome}`))
    lines.push('')
  }

  if (workspace.implementation_plan.length) {
    hasContent = true
    lines.push('## Implementation Plan', '')
    workspace.implementation_plan.forEach((item, index) => lines.push(`${index + 1}. ${item}`))
    lines.push('')
  }

  return hasContent ? lines.join('\n').trim() : ''
}

function buildMaturityMarkdown(advisoryCase: AdvisoryCase | null) {
  if (!advisoryCase?.maturity.length) return ''
  const lines: string[] = ['# Maturity', '']
  advisoryCase.maturity.forEach((item) => {
    lines.push(`## ${item.domain}`)
    if (item.current_state) lines.push(`Current state: ${item.current_state}`)
    if (item.target_state) lines.push(`Target state: ${item.target_state}`)
    if (item.gap) lines.push(`Gap to close: ${item.gap}`)
    lines.push('')
  })
  return lines.join('\n').trim()
}

function buildDeltaMarkdown(advisoryCase: AdvisoryCase | null) {
  const delta = advisoryCase?.delta
  if (!delta) return ''
  if (
    !delta.summary &&
    !delta.recommendation_change &&
    delta.new_risks.length === 0 &&
    delta.added_controls.length === 0 &&
    delta.removed_controls.length === 0 &&
    !delta.cost_or_complexity_impact &&
    delta.changed_assumptions.length === 0
  ) {
    return ''
  }

  const lines: string[] = ['# Recommendation Delta', '']
  if (delta.summary) lines.push('## Summary', '', delta.summary, '')
  if (delta.recommendation_change) lines.push('## Recommendation Change', '', delta.recommendation_change, '')
  if (delta.new_risks.length) {
    lines.push('## New Risks', '')
    delta.new_risks.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }
  if (delta.added_controls.length) {
    lines.push('## Added Controls', '')
    delta.added_controls.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }
  if (delta.removed_controls.length) {
    lines.push('## Removed Controls', '')
    delta.removed_controls.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }
  if (delta.cost_or_complexity_impact) {
    lines.push('## Cost Or Complexity Impact', '', delta.cost_or_complexity_impact, '')
  }
  if (delta.changed_assumptions.length) {
    lines.push('## Changed Assumptions', '')
    delta.changed_assumptions.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }
  return lines.join('\n').trim()
}

function buildMessagesMarkdown(messages: Message[]) {
  if (messages.length === 0) return ''
  const lines: string[] = ['# Session Transcript', '']
  messages.forEach((message, index) => {
    lines.push(`## ${index + 1}. ${capitalize(message.role)}`, '', message.content.trim() || '(empty)', '')
  })
  return lines.join('\n').trim()
}

function dedupe(values: string[]) {
  return [...new Set(values.filter(Boolean))]
}

function hasTechnicalBlueprintTables(markdown: string) {
  return (
    markdown.includes('| Layer | Decision | Alternatives Considered | Reasoning |') ||
    markdown.includes("| Dimension | What's needed | Owner | When |")
  )
}

function capitalize(value: string) {
  if (!value) return ''
  return value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, ' ')
}

function slugify(value: string) {
  const normalized = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return normalized || 'foundry-session'
}

function downloadBlob(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function buildZipBlob(files: ExportFile[]) {
  const encoder = new TextEncoder()
  const localParts: Uint8Array[] = []
  const centralParts: Uint8Array[] = []
  let offset = 0

  for (const file of files) {
    const nameBytes = encoder.encode(file.name)
    const dataBytes = encoder.encode(file.content)
    const crc = crc32(dataBytes)
    const localHeader = concatBytes(
      u32(0x04034b50),
      u16(20),
      u16(0),
      u16(0),
      u16(0),
      u16(0),
      u32(crc),
      u32(dataBytes.length),
      u32(dataBytes.length),
      u16(nameBytes.length),
      u16(0),
      nameBytes,
      dataBytes,
    )
    localParts.push(localHeader)

    const centralHeader = concatBytes(
      u32(0x02014b50),
      u16(20),
      u16(20),
      u16(0),
      u16(0),
      u16(0),
      u16(0),
      u32(crc),
      u32(dataBytes.length),
      u32(dataBytes.length),
      u16(nameBytes.length),
      u16(0),
      u16(0),
      u16(0),
      u16(0),
      u32(0),
      u32(offset),
      nameBytes,
    )
    centralParts.push(centralHeader)
    offset += localHeader.length
  }

  const centralDirectory = concatBytes(...centralParts)
  const localDirectory = concatBytes(...localParts)
  const endRecord = concatBytes(
    u32(0x06054b50),
    u16(0),
    u16(0),
    u16(files.length),
    u16(files.length),
    u32(centralDirectory.length),
    u32(localDirectory.length),
    u16(0),
  )

  return new Blob([localDirectory, centralDirectory, endRecord], { type: 'application/zip' })
}

function concatBytes(...arrays: Uint8Array[]) {
  const totalLength = arrays.reduce((sum, array) => sum + array.length, 0)
  const output = new Uint8Array(totalLength)
  let offset = 0
  arrays.forEach((array) => {
    output.set(array, offset)
    offset += array.length
  })
  return output
}

function u16(value: number) {
  const bytes = new Uint8Array(2)
  const view = new DataView(bytes.buffer)
  view.setUint16(0, value, true)
  return bytes
}

function u32(value: number) {
  const bytes = new Uint8Array(4)
  const view = new DataView(bytes.buffer)
  view.setUint32(0, value >>> 0, true)
  return bytes
}

const CRC_TABLE = createCrcTable()

function createCrcTable() {
  const table = new Uint32Array(256)
  for (let i = 0; i < 256; i += 1) {
    let c = i
    for (let bit = 0; bit < 8; bit += 1) {
      c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1)
    }
    table[i] = c >>> 0
  }
  return table
}

function crc32(bytes: Uint8Array) {
  let crc = 0xffffffff
  for (let index = 0; index < bytes.length; index += 1) {
    crc = CRC_TABLE[(crc ^ bytes[index]) & 0xff] ^ (crc >>> 8)
  }
  return (crc ^ 0xffffffff) >>> 0
}
