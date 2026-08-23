'use client'

import { useMemo, type CSSProperties } from 'react'
import { useStore } from '@/store'
import type {
  ArchNode,
  ArchitectureArtifact,
  ArchitectureFlowSegment,
  ArchitectureOverlayGroup,
} from '@/lib/types'
import { normalizeWorkspace } from '@/lib/message-analysis'
import { normalizeAdvisoryStage } from '@/lib/workflow'
import IconGlyph from './IconGlyph'

const LAYER_META: Record<string, { label: string; color: string; purpose: string }> = {
  surface: {
    label: 'Surface',
    color: '#6366f1',
    purpose: 'Where developers interact with the platform.',
  },
  harness: {
    label: 'Harness',
    color: '#8b5cf6',
    purpose: 'The approved interactive coding environments.',
  },
  execution: {
    label: 'Execution',
    color: '#a78bfa',
    purpose: 'Where interactive work runs and what trust boundary contains it.',
  },
  gateway: {
    label: 'Gateway',
    color: '#06b6d4',
    purpose: 'Where routing, policy enforcement, context, and enterprise integration happen.',
  },
  model: {
    label: 'Model',
    color: '#10b981',
    purpose: 'The model providers and tiers that power the platform.',
  },
  ops: {
    label: 'Ops',
    color: '#f59e0b',
    purpose: 'How the platform is observed, cost-controlled, and operated.',
  },
  access: {
    label: 'Access',
    color: '#ef4444',
    purpose: 'Identity, guardrails, compliance, and quota controls.',
  },
}

type SectionEmphasis = 'primary' | 'control' | 'model'
type ResolvedPathRole = 'primary' | 'overlay' | 'supporting'
type ResolvedNode = ArchNode & { resolvedKind: string; resolvedPathRole: ResolvedPathRole }
type ArchitectureSection = {
  id: string
  title: string
  subtitle: string
  nodes: ResolvedNode[]
  accent: string
  emphasis: SectionEmphasis
}

export default function ArchitectureBoard() {
  const activeSessionId = useStore((s) => s.activeSessionId)
  const conversations = useStore((s) => s.conversations)
  const workspaceState = useStore((s) => s.workspace)
  const architectureArtifact = useStore((s) => s.architectureArtifact)
  const canvasNodes = useStore((s) => s.canvasNodes)
  const baselineNodeIds = useStore((s) => s.baselineNodeIds)

  const workspace = useMemo(() => normalizeWorkspace(workspaceState), [workspaceState])
  const stage = normalizeAdvisoryStage(workspace.stage) ?? 'discovery'
  const archNodes = useMemo(
    () => canvasNodes.filter((node) => node.type === 'arch'),
    [canvasNodes],
  )
  const baselineSet = useMemo(() => new Set(baselineNodeIds), [baselineNodeIds])
  const artifactAddedNodeIds = useMemo(
    () => new Set((architectureArtifact?.customizations ?? []).flatMap((item) => item.added_component_ids)),
    [architectureArtifact],
  )
  const addedNodeIdSet = useMemo(() => {
    const ids = new Set<string>(artifactAddedNodeIds)
    archNodes.forEach((node) => {
      if (baselineSet.size > 0 && !baselineSet.has(node.id)) ids.add(node.id)
    })
    return ids
  }, [archNodes, artifactAddedNodeIds, baselineSet])
  const sessionTitle = conversations.find((item) => item.session.session_id === activeSessionId)?.session.title
    ?? 'Current architecture'
  const updatedAt = workspace.updated_at ?? ''
  const hasArchitecture = archNodes.length > 0 || Boolean(architectureArtifact)
  const factHighlights = workspace.facts.slice(0, 4)
  const baselineLayers = architectureArtifact?.baseline.layers ?? []
  const summary = architectureArtifact?.executive_summary || workspace.recommendation
  const decisionHighlights = (architectureArtifact?.decisions ?? []).slice(0, 3)
  const changeDrivers = useMemo(
    () => (architectureArtifact?.customizations ?? []).filter((item) => item.triggered_by.length > 0).slice(0, 4),
    [architectureArtifact],
  )
  const resolvedNodes = useMemo(
    () => archNodes.map((node) => ({
      ...node,
      resolvedKind: resolveNodeKind(node),
      resolvedPathRole: resolvePathRole(node),
    })),
    [archNodes],
  )
  const nodeById = useMemo(
    () => new Map(resolvedNodes.map((node) => [node.id, node])),
    [resolvedNodes],
  )
  const organizationAdditions = useMemo(
    () => resolvedNodes.filter((node) => addedNodeIdSet.has(node.id)),
    [addedNodeIdSet, resolvedNodes],
  )
  const baselineComponentCount = resolvedNodes.length - organizationAdditions.length
  const primarySections = useMemo(
    () => buildPrimarySections(architectureArtifact, resolvedNodes, nodeById),
    [architectureArtifact, nodeById, resolvedNodes],
  )
  const overlaySections = useMemo(
    () => buildOverlaySections(architectureArtifact, resolvedNodes, nodeById),
    [architectureArtifact, nodeById, resolvedNodes],
  )
  const supportingSections = useMemo(
    () => buildSupportingSections(architectureArtifact, resolvedNodes, nodeById),
    [architectureArtifact, nodeById, resolvedNodes],
  )

  if (!hasArchitecture) {
    return (
      <div style={emptyShellStyle}>
        <div style={emptyCardStyle}>
          <span style={eyebrow}>Architecture</span>
          <h2 style={{ fontSize: 20, lineHeight: 1.2 }}>No architecture snapshot yet</h2>
          <p style={{ fontSize: 13, lineHeight: 1.65, color: 'var(--text-2)' }}>
            {stage === 'discovery'
              ? 'The advisor is still collecting the first questions and assumptions. A baseline architecture will appear here after the direction is stable enough to visualize.'
              : 'The architecture board will appear here once the advisor emits a baseline or revised design.'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div style={shellStyle}>
      <div style={innerStyle}>
        <header style={headerGridStyle}>
          <div style={heroHeaderStyle}>
            <span style={eyebrow}>Architecture</span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <h1 style={titleStyle}>Architecture Board</h1>
              <p style={introStyle}>
                A leadership-readable view of the current request path, supporting lanes, and cross-cutting controls.
                This tab updates when new answers change the platform shape, control boundaries, or customer-specific additions.
              </p>
            </div>
            <div style={pillWrapStyle}>
              <span style={factPill}>Baseline components {baselineComponentCount}</span>
              <span style={addedPill(organizationAdditions.length > 0)}>Customer additions {organizationAdditions.length}</span>
              {factHighlights.map((fact) => (
                <span key={fact} style={factPill}>{fact}</span>
              ))}
            </div>
          </div>

          <div style={sourceCardStyle}>
            <span style={{ ...eyebrow, color: 'rgba(246,240,232,0.66)' }}>Source</span>
            <div>
              <div style={sourceLabelStyle}>Session</div>
              <div style={sourceValueStyle}>{sessionTitle}</div>
            </div>
            <div>
              <div style={sourceLabelStyle}>Snapshot</div>
              <div style={{ fontSize: 15, lineHeight: 1.4 }}>{formatTimestamp(updatedAt)}</div>
            </div>
            <div>
              <div style={sourceLabelStyle}>Target Architecture</div>
              <div style={{ fontSize: 15, lineHeight: 1.45 }}>
                {architectureArtifact?.baseline.name || 'Working architecture'}
              </div>
            </div>
          </div>
        </header>

        {workspace.open_questions.length > 0 && (
          <section style={warningBannerStyle}>
            <span style={{ ...eyebrow, color: 'rgba(247,221,156,0.74)' }}>Pending Inputs</span>
            <p style={{ fontSize: 13.5, lineHeight: 1.6 }}>
              {workspace.open_questions.length} open question{workspace.open_questions.length === 1 ? '' : 's'} still affect the architecture.
              Use the `Questions` tab to answer them; this board will refresh when the advisor revises the design.
            </p>
          </section>
        )}

        <section style={heroPanel}>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.7fr) minmax(320px, 0.8fr)', gap: 18 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <span style={eyebrow}>Recommended Direction</span>
              <p style={summaryBodyStyle}>
                {summary || 'Architecture summary will appear here as the advisor converges on a recommendation.'}
              </p>
            </div>
            <div style={decisionColumnStyle}>
              <span style={eyebrow}>Three Things To Remember</span>
              {decisionHighlights.length > 0 ? decisionHighlights.map((item) => (
                <div key={item.decision} style={miniDecisionCardStyle}>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{item.decision}</div>
                  <div style={{ fontSize: 12.5, lineHeight: 1.55, color: 'rgba(31,27,22,0.72)' }}>{item.why}</div>
                </div>
              )) : (
                <div style={miniDecisionCardStyle}>
                  Decision rationale will populate here once the architecture artifact includes explicit decisions.
                </div>
              )}
            </div>
          </div>
        </section>

        <section style={boardPanel}>
          <div style={sectionHeaderRowStyle}>
            <div>
              <span style={eyebrow}>Target Platform Shape</span>
              <h2 style={sectionTitleStyle}>Primary request path, overlays, and supporting lanes</h2>
            </div>
            <div style={legendWrapStyle}>
              <LegendBadge label="Baseline" />
              <LegendBadge label="Added for customer" accent />
              <LegendSwatch color="#8b5cf6" label="Interactive stack" />
              <LegendSwatch color="#06b6d4" label="Control plane" />
              <LegendSwatch color="#10b981" label="Model path" />
            </div>
          </div>

          <div style={requestFlowPanelStyle}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {primarySections.map((section, index) => (
                <div key={section.id} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <FlowSectionCard section={section} addedNodeIdSet={addedNodeIdSet} />
                  {index < primarySections.length - 1 ? (
                    <FlowArrow label={buildTransitionLabel(section.title, primarySections[index + 1].title)} />
                  ) : null}
                </div>
              ))}
            </div>
          </div>

          {supportingSections.length > 0 ? (
            <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <span style={eyebrow}>Supporting Lanes</span>
                <h3 style={subsectionTitleStyle}>Components that exist beside the main interactive path</h3>
              </div>
              <div style={sectionGridStyle}>
                {supportingSections.map((section) => (
                  <SupportingLaneCard key={section.id} section={section} addedNodeIdSet={addedNodeIdSet} />
                ))}
              </div>
            </div>
          ) : null}

          {overlaySections.length > 0 ? (
            <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <span style={eyebrow}>Cross-Cutting Controls</span>
                <h3 style={subsectionTitleStyle}>Controls that apply across harnesses and execution lanes</h3>
              </div>
              <div style={sectionGridStyle}>
                {overlaySections.map((section) => (
                  <OverlayCard key={section.id} section={section} addedNodeIdSet={addedNodeIdSet} />
                ))}
              </div>
            </div>
          ) : null}

          <details style={supportingDetailsStyle}>
            <summary style={supportingSummaryStyle}>Supporting detail</summary>
            <div style={supportingBodyStyle}>
              <div style={detailsGridStyle}>
                <div style={subPanel}>
                  <span style={eyebrow}>Standard Platform</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 10 }}>
                    {baselineLayers.map((layer) => (
                      <div key={layer.id} style={layerRowStyle}>
                        <div style={{ fontSize: 13, fontWeight: 650 }}>{layer.label}</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          <div style={{ fontSize: 12.5, color: 'rgba(31,27,22,0.86)' }}>
                            {layer.component_labels.join(' · ')}
                          </div>
                          <div style={{ fontSize: 12, lineHeight: 1.55, color: 'rgba(31,27,22,0.64)' }}>
                            {layer.purpose}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={subPanel}>
                  <span style={eyebrow}>Organization-specific Additions</span>
                  <div style={{ marginTop: 10 }}>
                    {organizationAdditions.length === 0 ? (
                      <div style={emptySubpanelStyle}>
                        No org-specific structural additions were identified in this session. This means the current recommendation remains a governed baseline rather than a one-off platform build.
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {organizationAdditions.map((node) => {
                          const customization = findCustomizationForNode(architectureArtifact, node.id)
                          return (
                            <div key={node.id} style={additionCardStyle}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                <span style={smallIconWrapStyle(node.color)}>
                                  <IconGlyph icon={node.icon} color={node.color} size={14} />
                                </span>
                                <div style={{ fontSize: 13, fontWeight: 650 }}>{node.label}</div>
                              </div>
                              <div style={{ fontSize: 12.5, lineHeight: 1.55, marginTop: 7 }}>
                                {customization?.reason || node.sublabel || 'Added beyond the baseline architecture for this organization.'}
                              </div>
                              {customization?.tradeoff ? (
                                <div style={{ marginTop: 6, fontSize: 12, color: 'rgba(31,27,22,0.66)' }}>
                                  Tradeoff: {customization.tradeoff}
                                </div>
                              ) : null}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div style={detailsGridStyle}>
                <div style={subPanel}>
                  <span style={eyebrow}>Primary Risks</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 10 }}>
                    {(architectureArtifact?.risks ?? []).map((risk) => (
                      <div key={risk.risk} style={riskCardStyle}>
                        <div style={{ fontSize: 13.5, fontWeight: 650, marginBottom: 4 }}>{risk.risk}</div>
                        <div style={{ fontSize: 12.5, lineHeight: 1.6, color: 'rgba(31,27,22,0.72)' }}>{risk.mitigation}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={subPanel}>
                  <span style={eyebrow}>Change Drivers</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 10 }}>
                    {changeDrivers.length > 0 ? changeDrivers.map((item) => (
                      <div key={item.id} style={riskCardStyle}>
                        <div style={{ fontSize: 13.5, fontWeight: 650, marginBottom: 6 }}>{item.title}</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {item.triggered_by.map((trigger) => (
                            <div key={trigger} style={{ fontSize: 12.5, lineHeight: 1.6, color: 'rgba(31,27,22,0.72)' }}>
                              {trigger}
                            </div>
                          ))}
                        </div>
                      </div>
                    )) : (
                      <div style={emptySubpanelStyle}>
                        This design is still operating as a governed baseline. Customer-specific structural drivers will appear here as the architecture diverges.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </details>
        </section>
      </div>
    </div>
  )
}

function buildPrimarySections(
  artifact: ArchitectureArtifact | null,
  nodes: ResolvedNode[],
  nodeById: Map<string, ResolvedNode>,
): ArchitectureSection[] {
  if (artifact?.primary_flow.length) {
    return artifact.primary_flow
      .map((segment) => sectionFromFlowSegment(segment, nodeById, nodes))
      .filter((section): section is ArchitectureSection => Boolean(section))
  }

  const surfaces = nodes.filter((node) => node.layer === 'surface')
  const harnesses = nodes.filter((node) => node.layer === 'harness' && node.resolvedPathRole === 'primary')
  const executions = nodes.filter((node) => node.layer === 'execution' && node.resolvedPathRole === 'primary')
  const toolAndContext = nodes.filter((node) => node.layer === 'gateway' && node.resolvedPathRole === 'primary' && ['tool_gateway', 'tool_connector', 'knowledge_source'].includes(node.resolvedKind))
  const modelGateways = nodes.filter((node) => node.layer === 'gateway' && node.resolvedPathRole === 'primary' && node.resolvedKind === 'model_gateway')
  const models = nodes.filter((node) => node.layer === 'model')

  return [
    makeSection('surface', 'Developer Surface', findLayerPurpose(artifact, 'surface'), surfaces, '#6366f1', 'primary'),
    makeSection('harness', 'Approved Interactive Harnesses', findLayerPurpose(artifact, 'harness'), harnesses, '#8b5cf6', 'primary'),
    makeSection('execution', 'Interactive Execution Lanes', findLayerPurpose(artifact, 'execution'), executions, '#a78bfa', 'primary'),
    makeSection('tool-gateway', 'Tool and Context Gateway', 'Tool routing, MCP surfaces, repo systems, and context sources the interactive path depends on.', toolAndContext, '#06b6d4', 'control'),
    makeSection('model-gateway', 'Model Gateway', 'Central model routing and provider abstraction.', modelGateways, '#0ea5e9', 'control'),
    makeSection('model', 'Model Tiers', findLayerPurpose(artifact, 'model'), models, '#10b981', 'model'),
  ].filter((section): section is ArchitectureSection => Boolean(section))
}

function buildOverlaySections(
  artifact: ArchitectureArtifact | null,
  nodes: ResolvedNode[],
  nodeById: Map<string, ResolvedNode>,
): ArchitectureSection[] {
  if (artifact?.cross_cutting_controls.length) {
    return artifact.cross_cutting_controls
      .map((group) => sectionFromOverlay(group, nodeById, '#f59e0b'))
      .filter((section): section is ArchitectureSection => Boolean(section))
  }

  const accessNodes = nodes.filter((node) => node.layer === 'access' || node.resolvedPathRole === 'overlay' && ['identity_control', 'policy_control'].includes(node.resolvedKind))
  const opsNodes = nodes.filter((node) => node.layer === 'ops' || node.resolvedPathRole === 'overlay' && ['observability_control', 'cost_control'].includes(node.resolvedKind))

  return [
    makeSection('identity-policy', 'Identity and Policy Overlay', findLayerPurpose(artifact, 'access'), accessNodes, '#ef4444', 'control'),
    makeSection('ops-governance', 'Operations and Governance Overlay', findLayerPurpose(artifact, 'ops'), opsNodes, '#f59e0b', 'control'),
  ].filter((section): section is ArchitectureSection => Boolean(section))
}

function buildSupportingSections(
  artifact: ArchitectureArtifact | null,
  nodes: ResolvedNode[],
  nodeById: Map<string, ResolvedNode>,
): ArchitectureSection[] {
  if (artifact?.supporting_lanes.length) {
    return artifact.supporting_lanes
      .map((group) => sectionFromOverlay(group, nodeById, '#7c3aed', 'primary'))
      .filter((section): section is ArchitectureSection => Boolean(section))
  }

  const background = nodes.filter((node) => node.resolvedPathRole === 'supporting' && ['custom_harness', 'framework_sdk', 'agent_runtime'].includes(node.resolvedKind))
  const adjunct = nodes.filter((node) => node.resolvedPathRole === 'supporting' && !['custom_harness', 'framework_sdk', 'agent_runtime'].includes(node.resolvedKind))

  return [
    makeSection('supporting-lane', 'Background and Exception Lanes', 'Custom agents, framework-based lanes, and exception environments that sit beside the main interactive path.', background, '#7c3aed', 'primary'),
    makeSection('adjacent-components', 'Adjacent Platform Components', 'Supporting components that matter to the design but do not sit on the main interactive request path.', adjunct, '#4338ca', 'control'),
  ].filter((section): section is ArchitectureSection => Boolean(section))
}

function sectionFromFlowSegment(
  segment: ArchitectureFlowSegment,
  nodeById: Map<string, ResolvedNode>,
  nodes: ResolvedNode[],
): ArchitectureSection | null {
  const resolved = uniqueNodes(segment.component_ids.map((id) => nodeById.get(id)).filter(Boolean) as ResolvedNode[])
  const fallback = resolved.length > 0 ? resolved : inferFlowNodesFromSegment(segment, nodes)
  const accent = accentForSection(segment.id, fallback[0]?.layer)
  const emphasis = emphasisForSection(segment.id, fallback[0]?.layer)
  return makeSection(segment.id, segment.title, segment.narrative, fallback, accent, emphasis)
}

function sectionFromOverlay(
  group: ArchitectureOverlayGroup,
  nodeById: Map<string, ResolvedNode>,
  accent: string,
  emphasis: SectionEmphasis = 'control',
): ArchitectureSection | null {
  const resolved = uniqueNodes(group.component_ids.map((id) => nodeById.get(id)).filter(Boolean) as ResolvedNode[])
  return makeSection(group.id, group.title, group.narrative, resolved, accent, emphasis)
}

function makeSection(
  id: string,
  title: string,
  subtitle: string,
  nodes: ResolvedNode[],
  accent: string,
  emphasis: SectionEmphasis,
): ArchitectureSection | null {
  if (nodes.length === 0) return null
  return { id, title, subtitle, nodes, accent, emphasis }
}

function uniqueNodes(nodes: ResolvedNode[]) {
  const seen = new Set<string>()
  return nodes.filter((node) => {
    if (seen.has(node.id)) return false
    seen.add(node.id)
    return true
  })
}

function inferFlowNodesFromSegment(segment: ArchitectureFlowSegment, nodes: ResolvedNode[]) {
  const id = segment.id.toLowerCase()
  const title = segment.title.toLowerCase()

  if (id.includes('surface') || title.includes('surface')) {
    return nodes.filter((node) => node.layer === 'surface')
  }
  if (id.includes('harness') || title.includes('harness')) {
    return nodes.filter((node) => node.layer === 'harness' && node.resolvedPathRole === 'primary')
  }
  if (id.includes('execution') || title.includes('execution')) {
    return nodes.filter((node) => node.layer === 'execution' && node.resolvedPathRole === 'primary')
  }
  if (id.includes('model') && !id.includes('gateway')) {
    return nodes.filter((node) => node.layer === 'model')
  }
  if (id.includes('gateway') || title.includes('gateway')) {
    return nodes.filter((node) => node.layer === 'gateway' && node.resolvedPathRole === 'primary')
  }

  return []
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
    return label.includes('cost') || label.includes('spend') ? 'cost_control' : 'observability_control'
  }
  if (node.layer === 'execution') {
    return label.includes('runtime') ? 'agent_runtime' : 'execution_lane'
  }
  if (node.layer === 'gateway') {
    if (label.includes('model gateway') || label.includes('litellm') || label.includes('bedrock')) return 'model_gateway'
    if (label.includes('knowledge base') || label.includes(' kb') || label.endsWith('kb')) return 'knowledge_source'
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
  if (['identity_control', 'policy_control', 'observability_control', 'cost_control'].includes(kind)) return 'overlay'
  if (['custom_harness', 'framework_sdk', 'agent_runtime'].includes(kind)) return 'supporting'
  return 'primary'
}

function findCustomizationForNode(
  artifact: ArchitectureArtifact | null,
  nodeId: string,
) {
  if (!artifact) return null
  return artifact.customizations.find((item) => item.added_component_ids.includes(nodeId)) ?? null
}

function findLayerPurpose(artifact: ArchitectureArtifact | null, layerId: string) {
  return artifact?.baseline.layers.find((layer) => layer.id === layerId)?.purpose
    ?? LAYER_META[layerId]?.purpose
    ?? ''
}

function formatTimestamp(value: string) {
  if (!value) return 'Live session'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function accentForSection(id: string, layer?: string) {
  const normalized = id.toLowerCase()
  if (normalized.includes('model')) return '#10b981'
  if (normalized.includes('gateway') || normalized.includes('tool') || normalized.includes('context')) return '#06b6d4'
  if (normalized.includes('execution')) return '#a78bfa'
  if (normalized.includes('surface')) return '#6366f1'
  if (normalized.includes('support')) return '#7c3aed'
  if (layer && LAYER_META[layer]) return LAYER_META[layer].color
  return '#8b5cf6'
}

function emphasisForSection(id: string, layer?: string): SectionEmphasis {
  const normalized = id.toLowerCase()
  if (normalized.includes('model') || layer === 'model') return 'model'
  if (normalized.includes('gateway') || normalized.includes('tool') || normalized.includes('context') || layer === 'gateway') return 'control'
  return 'primary'
}

function buildTransitionLabel(fromTitle: string, toTitle: string) {
  if (fromTitle.toLowerCase().includes('surface') && toTitle.toLowerCase().includes('harness')) {
    return 'Developer invokes the approved agent environment'
  }
  if (toTitle.toLowerCase().includes('execution')) {
    return 'The harness selects the execution boundary'
  }
  if (toTitle.toLowerCase().includes('gateway')) {
    return 'Requests pass through shared routing, tool, and policy gates'
  }
  if (toTitle.toLowerCase().includes('model')) {
    return 'The control plane chooses the model tier and provider path'
  }
  return 'The request moves to the next control point'
}

function kindLabel(kind: string) {
  switch (kind) {
    case 'developer_surface':
      return 'Surface'
    case 'interactive_harness':
      return 'Interactive harness'
    case 'custom_harness':
      return 'Custom lane'
    case 'framework_sdk':
      return 'Framework SDK'
    case 'execution_lane':
      return 'Execution lane'
    case 'agent_runtime':
      return 'Runtime'
    case 'tool_gateway':
      return 'Tool gateway'
    case 'tool_connector':
      return 'Connector'
    case 'knowledge_source':
      return 'Knowledge source'
    case 'model_gateway':
      return 'Model gateway'
    case 'model_provider':
      return 'Model tier'
    case 'identity_control':
      return 'Identity'
    case 'policy_control':
      return 'Policy'
    case 'observability_control':
      return 'Observability'
    case 'cost_control':
      return 'Cost control'
    default:
      return ''
  }
}

function FlowSectionCard({
  section,
  addedNodeIdSet,
}: {
  section: ArchitectureSection
  addedNodeIdSet: Set<string>
}) {
  return (
    <div style={flowCardStyle(section.accent)}>
      <div>
        <div style={{ fontSize: 17, fontWeight: 650 }}>{section.title}</div>
        <div style={{ fontSize: 12.5, lineHeight: 1.55, color: 'rgba(31,27,22,0.68)', marginTop: 5 }}>
          {section.subtitle}
        </div>
      </div>
      <div style={nodeGridStyle}>
        {section.nodes.map((node) => (
          <NodeCard
            key={node.id}
            node={node}
            emphasis={section.emphasis}
            isAdded={addedNodeIdSet.has(node.id)}
          />
        ))}
      </div>
    </div>
  )
}

function SupportingLaneCard({
  section,
  addedNodeIdSet,
}: {
  section: ArchitectureSection
  addedNodeIdSet: Set<string>
}) {
  return (
    <div style={subPanel}>
      <span style={eyebrow}>{section.title}</span>
      <p style={{ fontSize: 12.5, lineHeight: 1.6, color: 'rgba(31,27,22,0.7)', marginTop: 8 }}>
        {section.subtitle}
      </p>
      <div style={{ ...nodeGridStyle, marginTop: 12 }}>
        {section.nodes.map((node) => (
          <NodeCard
            key={node.id}
            node={node}
            emphasis={section.emphasis}
            isAdded={addedNodeIdSet.has(node.id)}
          />
        ))}
      </div>
    </div>
  )
}

function OverlayCard({
  section,
  addedNodeIdSet,
}: {
  section: ArchitectureSection
  addedNodeIdSet: Set<string>
}) {
  return (
    <div style={subPanel}>
      <span style={eyebrow}>{section.title}</span>
      <p style={{ fontSize: 12.5, lineHeight: 1.6, color: 'rgba(31,27,22,0.7)', marginTop: 8 }}>
        {section.subtitle}
      </p>
      <div style={{ ...nodeGridStyle, marginTop: 12 }}>
        {section.nodes.map((node) => (
          <ControlCard key={node.id} node={node} isAdded={addedNodeIdSet.has(node.id)} />
        ))}
      </div>
    </div>
  )
}

function FlowArrow({ label }: { label: string }) {
  return (
    <div style={arrowStyle}>
      <span style={arrowRuleStyle} />
      <span>{label}</span>
      <span style={{ fontSize: 18, lineHeight: 1 }}>↓</span>
      <span style={arrowRuleStyle} />
    </div>
  )
}

function NodeCard({
  node,
  emphasis,
  isAdded = false,
}: {
  node: ResolvedNode
  emphasis: SectionEmphasis
  isAdded?: boolean
}) {
  const background = emphasis === 'model'
    ? 'linear-gradient(180deg, rgba(16,185,129,0.16), rgba(16,185,129,0.08))'
    : emphasis === 'control'
      ? 'linear-gradient(180deg, rgba(6,182,212,0.15), rgba(8,145,178,0.08))'
      : 'rgba(255,255,255,0.82)'
  const label = kindLabel(node.resolvedKind)

  return (
    <div style={nodeCardStyle(background, node.color, isAdded)}>
      {isAdded ? <AddedBadge color={node.color} /> : null}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={iconWrapStyle(node.color)}>
          <IconGlyph icon={node.icon} color={node.color} size={16} />
        </span>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 15, fontWeight: 650, lineHeight: 1.25 }}>{node.label}</div>
          {label ? <div style={chipStyle(node.color)}>{label}</div> : null}
        </div>
      </div>
      <div style={{ fontSize: 12.5, lineHeight: 1.58, color: 'rgba(31,27,22,0.7)' }}>
        {node.sublabel}
      </div>
    </div>
  )
}

function ControlCard({ node, isAdded = false }: { node: ResolvedNode; isAdded?: boolean }) {
  const label = kindLabel(node.resolvedKind)
  return (
    <div style={controlCardStyle(node.color, isAdded)}>
      {isAdded ? <AddedBadge color={node.color} /> : null}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={smallIconWrapStyle(node.color)}>
          <IconGlyph icon={node.icon} color={node.color} size={15} />
        </span>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 650, lineHeight: 1.25 }}>{node.label}</div>
          {label ? <div style={chipStyle(node.color)}>{label}</div> : null}
        </div>
      </div>
      <div style={{ fontSize: 12.5, lineHeight: 1.58, color: 'rgba(31,27,22,0.68)' }}>
        {node.sublabel}
      </div>
    </div>
  )
}

function AddedBadge({ color }: { color: string }) {
  return (
    <span style={{
      position: 'absolute',
      top: 10,
      right: 10,
      padding: '3px 7px',
      borderRadius: 999,
      background: `${color}18`,
      border: `1px solid ${color}35`,
      color: '#1f1b16',
      fontSize: 10,
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.06em',
    }}>
      Added
    </span>
  )
}

function LegendSwatch({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <span style={{
        width: 10,
        height: 10,
        borderRadius: '999px',
        background: color,
        boxShadow: `0 0 0 4px ${color}18`,
      }} />
      <span style={{ fontSize: 12, color: 'rgba(31,27,22,0.74)' }}>{label}</span>
    </div>
  )
}

function LegendBadge({ label, accent = false }: { label: string; accent?: boolean }) {
  return (
    <span style={{
      padding: '5px 8px',
      borderRadius: 999,
      border: accent ? '1px solid rgba(99,102,241,0.22)' : '1px solid rgba(31,27,22,0.12)',
      background: accent ? 'rgba(99,102,241,0.08)' : 'rgba(31,27,22,0.04)',
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: '0.04em',
      textTransform: 'uppercase',
      color: 'rgba(31,27,22,0.78)',
    }}>
      {label}
    </span>
  )
}

const emptyShellStyle: CSSProperties = {
  flex: 1,
  minHeight: 0,
  overflow: 'auto',
  background: 'var(--bg-elevated-2)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 24,
}

const emptyCardStyle: CSSProperties = {
  width: 360,
  maxWidth: '100%',
  borderRadius: 20,
  border: '1px solid var(--border)',
  background: 'var(--bg-elevated)',
  padding: 22,
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  textAlign: 'center',
}

const shellStyle: CSSProperties = {
  flex: 1,
  minHeight: 0,
  overflow: 'auto',
  background: 'linear-gradient(180deg, #0f1116 0%, #17171b 100%)',
  color: '#1f1b16',
}

const innerStyle: CSSProperties = {
  maxWidth: 1560,
  margin: '0 auto',
  padding: '20px 18px 24px',
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
}

const headerGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1.5fr) minmax(240px, 0.7fr)',
  gap: 14,
  alignItems: 'start',
}

const heroHeaderStyle: CSSProperties = {
  background: 'rgba(255,255,255,0.76)',
  border: '1px solid rgba(31,27,22,0.12)',
  borderRadius: 24,
  padding: 18,
  boxShadow: '0 18px 50px rgba(80, 60, 38, 0.08)',
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
}

const sourceCardStyle: CSSProperties = {
  background: '#1f1b16',
  color: '#f6f0e8',
  borderRadius: 24,
  padding: 18,
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  boxShadow: '0 22px 60px rgba(31,27,22,0.18)',
}

const sourceLabelStyle: CSSProperties = {
  fontSize: 14,
  color: 'rgba(246,240,232,0.72)',
}

const sourceValueStyle: CSSProperties = {
  fontSize: 18,
  lineHeight: 1.4,
  fontWeight: 600,
}

const warningBannerStyle: CSSProperties = {
  background: 'rgba(245,158,11,0.12)',
  border: '1px solid rgba(245,158,11,0.28)',
  color: '#f7dd9c',
  borderRadius: 18,
  padding: '14px 16px',
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
}

const heroPanel: CSSProperties = {
  background: 'rgba(255,255,255,0.78)',
  border: '1px solid rgba(31,27,22,0.1)',
  borderRadius: 24,
  padding: 18,
  boxShadow: '0 18px 50px rgba(80, 60, 38, 0.08)',
}

const decisionColumnStyle: CSSProperties = {
  borderLeft: '1px solid rgba(31,27,22,0.12)',
  paddingLeft: 18,
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}

const miniDecisionCardStyle: CSSProperties = {
  padding: '12px 14px',
  borderRadius: 16,
  background: 'rgba(31,27,22,0.04)',
  border: '1px solid rgba(31,27,22,0.08)',
  fontSize: 12.5,
  lineHeight: 1.55,
  color: 'rgba(31,27,22,0.72)',
}

const boardPanel: CSSProperties = {
  borderRadius: 28,
  background: 'rgba(248,243,234,0.88)',
  border: '1px solid rgba(31,27,22,0.1)',
  padding: 18,
  minWidth: 0,
  boxShadow: '0 22px 60px rgba(80, 60, 38, 0.08)',
}

const requestFlowPanelStyle: CSSProperties = {
  marginTop: 16,
  padding: 16,
  borderRadius: 24,
  background: 'linear-gradient(180deg, rgba(255,255,255,0.92) 0%, rgba(255,255,255,0.76) 100%)',
  border: '1px solid rgba(31,27,22,0.1)',
}

const subPanel: CSSProperties = {
  borderRadius: 24,
  background: 'rgba(255,255,255,0.74)',
  border: '1px solid rgba(31,27,22,0.1)',
  padding: 18,
  boxShadow: '0 18px 50px rgba(80, 60, 38, 0.06)',
}

const supportingDetailsStyle: CSSProperties = {
  marginTop: 16,
  borderRadius: 18,
  border: '1px solid rgba(31,27,22,0.1)',
  background: 'rgba(255,255,255,0.72)',
  overflow: 'hidden',
}

const supportingSummaryStyle: CSSProperties = {
  cursor: 'pointer',
  padding: '12px 14px',
  fontSize: 12.5,
  fontWeight: 700,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
  color: 'rgba(31,27,22,0.8)',
  background: 'rgba(31,27,22,0.04)',
}

const supportingBodyStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
  padding: 14,
}

const detailsGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1.1fr 0.9fr',
  gap: 16,
}

const layerRowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '120px 1fr',
  gap: 12,
  alignItems: 'start',
}

const additionCardStyle: CSSProperties = {
  padding: '14px 14px',
  borderRadius: 16,
  background: 'rgba(99,102,241,0.06)',
  border: '1px solid rgba(99,102,241,0.15)',
}

const riskCardStyle: CSSProperties = {
  borderRadius: 18,
  background: 'rgba(255,255,255,0.78)',
  border: '1px solid rgba(31,27,22,0.08)',
  padding: '14px 14px',
}

const emptySubpanelStyle: CSSProperties = {
  padding: '16px 16px',
  borderRadius: 16,
  background: 'rgba(31,27,22,0.035)',
  border: '1px dashed rgba(31,27,22,0.14)',
  fontSize: 12.5,
  lineHeight: 1.6,
  color: 'rgba(31,27,22,0.68)',
}

const eyebrow: CSSProperties = {
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.12em',
  fontWeight: 700,
  color: 'rgba(31,27,22,0.52)',
}

const titleStyle: CSSProperties = {
  fontSize: 28,
  lineHeight: 1.04,
  fontWeight: 700,
  letterSpacing: '-0.04em',
}

const introStyle: CSSProperties = {
  fontSize: 13.5,
  lineHeight: 1.6,
  color: 'rgba(31,27,22,0.82)',
  maxWidth: 860,
}

const summaryBodyStyle: CSSProperties = {
  fontSize: 15.5,
  lineHeight: 1.62,
  color: 'rgba(31,27,22,0.88)',
}

const pillWrapStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 10,
}

const factPill: CSSProperties = {
  borderRadius: 999,
  padding: '8px 12px',
  border: '1px solid rgba(31,27,22,0.09)',
  background: 'rgba(31,27,22,0.04)',
  fontSize: 12.5,
  color: 'rgba(31,27,22,0.84)',
}

function addedPill(active: boolean): CSSProperties {
  return {
    borderRadius: 999,
    padding: '8px 12px',
    border: `1px solid ${active ? 'rgba(99,102,241,0.18)' : 'rgba(31,27,22,0.09)'}`,
    background: active ? 'rgba(99,102,241,0.08)' : 'rgba(31,27,22,0.04)',
    fontSize: 12.5,
    color: 'rgba(31,27,22,0.84)',
  }
}

const sectionHeaderRowStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  gap: 12,
  flexWrap: 'wrap',
}

const sectionTitleStyle: CSSProperties = {
  marginTop: 8,
  fontSize: 22,
  lineHeight: 1.12,
  letterSpacing: '-0.03em',
}

const subsectionTitleStyle: CSSProperties = {
  marginTop: 6,
  fontSize: 18,
  lineHeight: 1.2,
  letterSpacing: '-0.02em',
}

const legendWrapStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  flexWrap: 'wrap',
  justifyContent: 'flex-end',
}

const sectionGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
  gap: 14,
}

function flowCardStyle(accent: string): CSSProperties {
  return {
    borderRadius: 22,
    border: `1px solid ${accent}22`,
    background: `${accent}0d`,
    padding: 18,
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  }
}

const nodeGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
  gap: 12,
}

const arrowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 10,
  color: 'rgba(31,27,22,0.48)',
  fontSize: 12,
  letterSpacing: '0.02em',
}

const arrowRuleStyle: CSSProperties = {
  width: 1,
  height: 12,
  background: 'rgba(31,27,22,0.15)',
}

function nodeCardStyle(background: string, color: string, isAdded: boolean): CSSProperties {
  return {
    borderRadius: 18,
    background,
    border: isAdded ? `1px solid ${color}66` : `1px solid ${color}26`,
    padding: '14px 14px',
    minHeight: 120,
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    boxShadow: '0 10px 24px rgba(31,27,22,0.05)',
    position: 'relative',
  }
}

function controlCardStyle(color: string, isAdded: boolean): CSSProperties {
  return {
    padding: '14px 14px',
    borderRadius: 18,
    background: 'rgba(255,255,255,0.82)',
    border: isAdded ? `1px solid ${color}55` : `1px solid ${color}1f`,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    boxShadow: '0 10px 24px rgba(31,27,22,0.05)',
    position: 'relative',
  }
}

function iconWrapStyle(color: string): CSSProperties {
  return {
    width: 34,
    height: 34,
    borderRadius: 12,
    background: `${color}20`,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  }
}

function smallIconWrapStyle(color: string): CSSProperties {
  return {
    width: 32,
    height: 32,
    borderRadius: 11,
    background: `${color}16`,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  }
}

function chipStyle(color: string): CSSProperties {
  return {
    marginTop: 6,
    display: 'inline-flex',
    alignItems: 'center',
    width: 'fit-content',
    borderRadius: 999,
    padding: '3px 7px',
    background: `${color}12`,
    border: `1px solid ${color}24`,
    color: 'rgba(31,27,22,0.76)',
    fontSize: 10.5,
    fontWeight: 700,
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
  }
}
