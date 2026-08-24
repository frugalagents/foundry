'use client'

import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { useStore } from '@/store'
import type {
  ArchNode,
  ArchitectureArtifact,
  ArchitectureCustomization,
  ArchitectureFlowSegment,
  ArchitectureLayerSummary,
  ArchitectureOverlayGroup,
} from '@/lib/types'
import { normalizeWorkspace } from '@/lib/message-analysis'
import { normalizeAdvisoryStage } from '@/lib/workflow'
import IconGlyph from './IconGlyph'

const LAYER_META: Record<string, { label: string; color: string; purpose: string }> = {
  surface: {
    label: 'Developer Surface',
    color: '#5161ff',
    purpose: 'Where developers start and interact with the platform.',
  },
  harness: {
    label: 'Approved Harness',
    color: '#7c4dff',
    purpose: 'The approved working environments that the enterprise governs.',
  },
  execution: {
    label: 'Execution Boundary',
    color: '#a855f7',
    purpose: 'Where agent work runs and what trust boundary contains it.',
  },
  gateway: {
    label: 'Shared Control Path',
    color: '#0ea5e9',
    purpose: 'The enterprise routing layer for tools, context, and model access.',
  },
  model: {
    label: 'Model Route',
    color: '#10b981',
    purpose: 'How the platform selects and reaches model providers.',
  },
  ops: {
    label: 'Operations',
    color: '#f59e0b',
    purpose: 'How the platform is observed, governed, and cost controlled.',
  },
  access: {
    label: 'Identity and Policy',
    color: '#ef4444',
    purpose: 'How access, guardrails, and compliance are enforced.',
  },
}

type ResolvedPathRole = 'primary' | 'overlay' | 'supporting'
type ResolvedNode = ArchNode & { resolvedKind: string; resolvedPathRole: ResolvedPathRole }

type FlowStage = {
  id: string
  title: string
  subtitle: string
  accent: string
  nodes: ResolvedNode[]
}

type ControlGroup = {
  id: string
  title: string
  subtitle: string
  accent: string
  nodes: ResolvedNode[]
}

type AudienceView = {
  id: string
  label: string
  description: string
  nodes: ResolvedNode[]
  customizations: ArchitectureCustomization[]
  triggers: string[]
  tradeoffs: string[]
  addedCount: number
  isBaseline?: boolean
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
  const sessionTitle = conversations.find((item) => item.session.session_id === activeSessionId)?.session.title
    ?? 'Current architecture'
  const updatedAt = workspace.updated_at ?? ''
  const hasArchitecture = resolvedNodes.length > 0 || Boolean(architectureArtifact)
  const openQuestionCount = workspace.open_questions.length
  const addedNodes = useMemo(
    () => resolvedNodes.filter((node) => addedNodeIdSet.has(node.id)),
    [addedNodeIdSet, resolvedNodes],
  )
  const primaryStages = useMemo(
    () => buildFlowStages(architectureArtifact, resolvedNodes, nodeById),
    [architectureArtifact, nodeById, resolvedNodes],
  )
  const controlGroups = useMemo(
    () => buildControlGroups(architectureArtifact, resolvedNodes, nodeById),
    [architectureArtifact, nodeById, resolvedNodes],
  )
  const supportingGroups = useMemo(
    () => buildSupportingGroups(architectureArtifact, resolvedNodes, nodeById),
    [architectureArtifact, nodeById, resolvedNodes],
  )
  const audienceViews = useMemo(
    () => buildAudienceViews({
      artifact: architectureArtifact,
      addedNodeIdSet,
      nodeById,
      resolvedNodes,
      supportingGroups,
    }),
    [addedNodeIdSet, architectureArtifact, nodeById, resolvedNodes, supportingGroups],
  )
  const [activeAudienceId, setActiveAudienceId] = useState(audienceViews[0]?.id ?? 'baseline')

  useEffect(() => {
    if (!audienceViews.some((view) => view.id === activeAudienceId)) {
      setActiveAudienceId(audienceViews[0]?.id ?? 'baseline')
    }
  }, [activeAudienceId, audienceViews])

  const activeAudience = audienceViews.find((view) => view.id === activeAudienceId) ?? audienceViews[0]
  const summary = architectureArtifact?.executive_summary || workspace.recommendation
  const baselineLayers = architectureArtifact?.baseline.layers ?? []
  const decisionHighlights = (architectureArtifact?.decisions ?? []).slice(0, 3)
  const riskHighlights = (architectureArtifact?.risks ?? []).slice(0, 3)
  const baselineCount = resolvedNodes.length - addedNodes.length

  if (!hasArchitecture) {
    return (
      <div style={emptyShellStyle}>
        <div style={emptyCardStyle}>
          <span style={eyebrow}>Architecture</span>
          <h2 style={{ fontSize: 20, lineHeight: 1.2 }}>No architecture snapshot yet</h2>
          <p style={{ fontSize: 13, lineHeight: 1.65, color: 'var(--text-2)' }}>
            {stage === 'discovery'
              ? 'The advisor is still collecting the first decision-driving answers. The architecture will appear here once there is enough evidence to show a stable baseline.'
              : 'The architecture board will appear here once the advisor publishes a baseline or revised design.'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div style={shellStyle}>
      <div style={innerStyle}>
        <header style={headerStyle}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span style={eyebrow}>Architecture</span>
              <h1 style={titleStyle}>Platform shape and control boundary</h1>
              <p style={introStyle}>
                This view shows the standard request path, the cross-cutting control plane, and the customer-specific lanes that change the baseline.
              </p>
            </div>
            <div style={pillWrapStyle}>
              <MetricPill label="Baseline" value={String(Math.max(baselineCount, 0))} />
              <MetricPill label="Customer additions" value={String(addedNodes.length)} accent />
              {openQuestionCount > 0 ? <MetricPill label="Open questions" value={String(openQuestionCount)} warning /> : null}
            </div>
          </div>

          <div style={sourceCardStyle}>
            <InfoPair label="Session" value={sessionTitle} />
            <InfoPair label="Snapshot" value={formatTimestamp(updatedAt)} />
            <InfoPair label="Architecture" value={architectureArtifact?.baseline.name || 'Working architecture'} />
          </div>
        </header>

        <section style={summaryPanelStyle}>
          <div style={summaryBodyPanelStyle}>
            <span style={eyebrow}>Recommended Direction</span>
            <p style={summaryBodyStyle}>
              {summary || 'Architecture summary will appear here as the recommendation converges.'}
            </p>
          </div>

          <div style={summarySidePanelStyle}>
            <span style={eyebrow}>Key Decisions</span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {decisionHighlights.length > 0 ? decisionHighlights.map((item) => (
                <div key={item.decision} style={microCardStyle}>
                  <div style={microCardTitleStyle}>{item.decision}</div>
                  <div style={microCardTextStyle}>{item.why}</div>
                </div>
              )) : (
                <div style={microCardStyle}>Decision rationale will populate here once the engine publishes it.</div>
              )}
            </div>
          </div>
        </section>

        <section style={diagramSectionStyle}>
          <div style={sectionHeadingRowStyle}>
            <div>
              <span style={eyebrow}>Platform Map</span>
              <h2 style={sectionTitleStyle}>End-to-end flow with a cross-cutting control plane</h2>
            </div>
            <div style={legendWrapStyle}>
              <LegendBadge label="Baseline" />
              <LegendBadge label="Added for customer" accent />
            </div>
          </div>

          <div style={diagramViewportStyle}>
            <div style={diagramSceneStyle}>
              <div style={flowAreaStyle}>
                <div style={laneHeadingStyle}>
                  <span style={laneHeadingEyebrowStyle}>Shared Baseline Flow</span>
                  <div style={laneHeadingTitleStyle}>How a request moves through the standard platform</div>
                </div>
                <div style={flowStripStyle}>
                  {primaryStages.map((stageItem, index) => (
                    <div key={stageItem.id} style={flowItemWrapStyle}>
                      <FlowStageCard
                        stage={stageItem}
                        addedNodeIdSet={addedNodeIdSet}
                      />
                      {index < primaryStages.length - 1 ? (
                        <FlowConnector label={transitionLabel(stageItem, primaryStages[index + 1])} />
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>

              <aside style={controlStripStyle}>
                <div style={controlStripHeaderStyle}>
                  <span style={laneHeadingEyebrowStyle}>Control Plane</span>
                  <div style={laneHeadingTitleStyle}>What governs every lane</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {controlGroups.map((group) => (
                    <ControlGroupCard
                      key={group.id}
                      group={group}
                      addedNodeIdSet={addedNodeIdSet}
                    />
                  ))}
                </div>
              </aside>
            </div>
          </div>

          {openQuestionCount > 0 ? (
            <div style={pendingBannerStyle}>
              {openQuestionCount} open question{openQuestionCount === 1 ? '' : 's'} can still change the architecture. Answer them in the `Questions` tab and this map will refresh.
            </div>
          ) : null}
        </section>

        <section style={audienceSectionStyle}>
          <div style={sectionHeadingRowStyle}>
            <div>
              <span style={eyebrow}>Audience Views</span>
              <h2 style={sectionTitleStyle}>Shared baseline first, then persona and exception deltas</h2>
            </div>
          </div>

          <div style={tabBarStyle}>
            {audienceViews.map((view) => (
              <button
                key={view.id}
                type="button"
                onClick={() => setActiveAudienceId(view.id)}
                style={tabButtonStyle(activeAudienceId === view.id)}
              >
                <span>{view.label}</span>
                {view.addedCount > 0 ? <span style={tabCountStyle(activeAudienceId === view.id)}>{view.addedCount}</span> : null}
              </button>
            ))}
          </div>

          {activeAudience ? (
            activeAudience.isBaseline ? (
              <div style={detailGridStyle}>
                <div style={detailCardStyle}>
                  <span style={eyebrow}>Standard Platform</span>
                  <p style={detailIntroStyle}>
                    {activeAudience.description}
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {(baselineLayers.length > 0 ? baselineLayers : inferLayerRowsFromStages(primaryStages)).map((layer) => (
                      <LayerRow key={layer.id} layer={layer} />
                    ))}
                  </div>
                </div>

                <div style={detailCardStyle}>
                  <span style={eyebrow}>Specialized Lanes</span>
                  <p style={detailIntroStyle}>
                    Populations or workflows that diverge from the standard platform show up here as explicit exception lanes.
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {audienceViews.filter((view) => !view.isBaseline).length > 0 ? audienceViews.filter((view) => !view.isBaseline).map((view) => (
                      <div key={view.id} style={exceptionRowStyle}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
                          <div style={exceptionTitleStyle}>{view.label}</div>
                          {view.addedCount > 0 ? <span style={exceptionCountStyle}>{view.addedCount} addition{view.addedCount === 1 ? '' : 's'}</span> : null}
                        </div>
                        <div style={exceptionTextStyle}>{view.description}</div>
                      </div>
                    )) : (
                      <div style={emptyNoteStyle}>No explicit persona or exception lane has been published yet. The recommendation is still operating as one governed baseline.</div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div style={detailGridStyle}>
                <div style={detailCardStyle}>
                  <span style={eyebrow}>{activeAudience.label}</span>
                  <p style={detailIntroStyle}>{activeAudience.description}</p>
                  <div style={nodeListStyle}>
                    {activeAudience.nodes.length > 0 ? activeAudience.nodes.map((node) => (
                      <AudienceNodeRow
                        key={node.id}
                        node={node}
                        isAdded={addedNodeIdSet.has(node.id)}
                      />
                    )) : (
                      <div style={emptyNoteStyle}>No specific components were tagged for this lane yet.</div>
                    )}
                  </div>
                </div>

                <div style={detailCardStyle}>
                  <span style={eyebrow}>Why This Lane Exists</span>
                  <p style={detailIntroStyle}>
                    The engine uses customer answers, constraints, and explicit tradeoffs to justify each deviation from the baseline.
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {activeAudience.customizations.map((item) => (
                      <div key={item.id} style={reasonCardStyle}>
                        <div style={reasonTitleStyle}>{item.title}</div>
                        <div style={reasonTextStyle}>{item.reason || 'Added beyond the standard baseline for this organization.'}</div>
                        {item.tradeoff ? <div style={tradeoffTextStyle}>Tradeoff: {item.tradeoff}</div> : null}
                      </div>
                    ))}
                    {activeAudience.triggers.length > 0 ? (
                      <div style={reasonCardStyle}>
                        <div style={reasonTitleStyle}>Decision triggers</div>
                        <div style={bulletListStyle}>
                          {activeAudience.triggers.map((trigger) => (
                            <div key={trigger} style={bulletRowStyle}>• {trigger}</div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                    {activeAudience.customizations.length === 0 && activeAudience.triggers.length === 0 ? (
                      <div style={emptyNoteStyle}>This lane is published as a distinct view, but the engine has not attached explicit rationale text yet.</div>
                    ) : null}
                  </div>
                </div>
              </div>
            )
          ) : null}
        </section>

        <section style={detailGridStyle}>
          <div style={detailCardStyle}>
            <span style={eyebrow}>Risk Watchlist</span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 10 }}>
              {riskHighlights.length > 0 ? riskHighlights.map((risk) => (
                <div key={risk.risk} style={reasonCardStyle}>
                  <div style={reasonTitleStyle}>{risk.risk}</div>
                  <div style={reasonTextStyle}>{risk.mitigation}</div>
                </div>
              )) : (
                <div style={emptyNoteStyle}>No architecture risks have been published yet.</div>
              )}
            </div>
          </div>

          <div style={detailCardStyle}>
            <span style={eyebrow}>Customer-specific additions</span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 10 }}>
              {addedNodes.length > 0 ? addedNodes.slice(0, 8).map((node) => {
                const customization = findCustomizationForNode(architectureArtifact, node.id)
                return (
                  <div key={node.id} style={additionRowStyle}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <span style={smallIconWrapStyle(node.color)}>
                        <IconGlyph icon={node.icon} color={node.color} size={14} />
                      </span>
                      <div>
                        <div style={reasonTitleStyle}>{node.label}</div>
                        <div style={reasonTextStyle}>{customization?.reason || node.sublabel || 'Added for this customer beyond the reference baseline.'}</div>
                      </div>
                    </div>
                  </div>
                )
              }) : (
                <div style={emptyNoteStyle}>This session is still aligned to the standard baseline and has not introduced customer-specific structural additions.</div>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

function buildFlowStages(
  artifact: ArchitectureArtifact | null,
  nodes: ResolvedNode[],
  nodeById: Map<string, ResolvedNode>,
): FlowStage[] {
  if (artifact?.primary_flow.length) {
    return artifact.primary_flow
      .map((segment) => sectionFromFlowSegment(segment, nodeById, nodes))
      .filter((item): item is FlowStage => Boolean(item))
  }

  const toolContextNodes = nodes.filter((node) => (
    node.layer === 'gateway'
    && node.resolvedPathRole === 'primary'
    && !isModelRouteNode(node)
    && !isControlPlaneGatewayNode(node)
  ))
  const modelRouteNodes = nodes.filter((node) => (
    node.layer === 'model'
    || (node.layer === 'gateway' && node.resolvedPathRole === 'primary' && isModelRouteNode(node))
  ))

  return [
    makeFlowStage(
      'surface',
      'Developer entry',
      artifact?.baseline.layers.find((layer) => layer.id === 'surface')?.purpose || LAYER_META.surface.purpose,
      '#5161ff',
      nodes.filter((node) => node.layer === 'surface'),
    ),
    makeFlowStage(
      'harness',
      'Approved harness',
      artifact?.baseline.layers.find((layer) => layer.id === 'harness')?.purpose || LAYER_META.harness.purpose,
      '#7c4dff',
      nodes.filter((node) => node.layer === 'harness' && node.resolvedPathRole === 'primary'),
    ),
    makeFlowStage(
      'execution',
      'Execution boundary',
      artifact?.baseline.layers.find((layer) => layer.id === 'execution')?.purpose || LAYER_META.execution.purpose,
      '#a855f7',
      nodes.filter((node) => node.layer === 'execution' && node.resolvedPathRole === 'primary'),
    ),
    makeFlowStage(
      'tool-path',
      'Tool and context path',
      'Where approved tools, repositories, and context sources are reached through the shared platform path.',
      '#0ea5e9',
      toolContextNodes,
    ),
    makeFlowStage(
      'model-route',
      'Model route',
      artifact?.baseline.layers.find((layer) => layer.id === 'model')?.purpose || LAYER_META.model.purpose,
      '#10b981',
      modelRouteNodes,
    ),
  ].filter((item): item is FlowStage => Boolean(item))
}

function buildControlGroups(
  artifact: ArchitectureArtifact | null,
  nodes: ResolvedNode[],
  nodeById: Map<string, ResolvedNode>,
): ControlGroup[] {
  if (artifact?.cross_cutting_controls.length) {
    return artifact.cross_cutting_controls
      .map((group) => sectionFromOverlay(group, nodeById))
      .filter((item): item is ControlGroup => Boolean(item))
  }

  const identityAndPolicy = nodes.filter((node) => (
    node.layer === 'access'
    || ['identity_control', 'policy_control'].includes(node.resolvedKind)
  ))
  const registryAndCatalog = nodes.filter((node) => (
    (node.layer === 'gateway' && isControlPlaneGatewayNode(node))
    || isRegistryNode(node)
  ))
  const auditAndOperations = nodes.filter((node) => (
    node.layer === 'ops'
    || ['observability_control', 'cost_control'].includes(node.resolvedKind)
    || isAuditNode(node)
  ))

  return [
    makeControlGroup(
      'identity-policy',
      'Identity and policy',
      'Access control, guardrails, compliance policy, and entitlement checks applied across the platform.',
      '#ef4444',
      identityAndPolicy,
    ),
    makeControlGroup(
      'registry-catalog',
      'Registry and catalog',
      'Approved tool registry, MCP catalog, and shared platform services that sit across multiple lanes.',
      '#0ea5e9',
      registryAndCatalog,
    ),
    makeControlGroup(
      'audit-operations',
      'Audit, observability, and cost',
      'Audit trail, usage visibility, quota enforcement, and operating controls.',
      '#f59e0b',
      auditAndOperations,
    ),
  ].filter((item): item is ControlGroup => Boolean(item))
}

function buildSupportingGroups(
  artifact: ArchitectureArtifact | null,
  nodes: ResolvedNode[],
  nodeById: Map<string, ResolvedNode>,
): ControlGroup[] {
  if (artifact?.supporting_lanes.length) {
    return artifact.supporting_lanes
      .map((group) => sectionFromOverlay(group, nodeById, 'supporting'))
      .filter((item): item is ControlGroup => Boolean(item))
  }

  const specializedLanes = nodes.filter((node) => (
    node.resolvedPathRole === 'supporting'
    && ['custom_harness', 'framework_sdk', 'agent_runtime'].includes(node.resolvedKind)
  ))
  const adjacentComponents = nodes.filter((node) => (
    node.resolvedPathRole === 'supporting'
    && !['custom_harness', 'framework_sdk', 'agent_runtime'].includes(node.resolvedKind)
  ))

  return [
    makeControlGroup(
      'specialized-lanes',
      'Specialized lanes',
      'Exception workflows, specialized harnesses, or background lanes that exist beside the main path.',
      '#7c4dff',
      specializedLanes,
    ),
    makeControlGroup(
      'adjacent-components',
      'Adjacent components',
      'Supporting platform components that matter to the design without being part of the main request path.',
      '#4f46e5',
      adjacentComponents,
    ),
  ].filter((item): item is ControlGroup => Boolean(item))
}

function buildAudienceViews({
  artifact,
  addedNodeIdSet,
  nodeById,
  resolvedNodes,
  supportingGroups,
}: {
  artifact: ArchitectureArtifact | null
  addedNodeIdSet: Set<string>
  nodeById: Map<string, ResolvedNode>
  resolvedNodes: ResolvedNode[]
  supportingGroups: ControlGroup[]
}): AudienceView[] {
  const baselineDescription = artifact?.baseline.name
    ? `${artifact.baseline.name}. This is the standard platform shape before persona-specific controls or exception lanes are applied.`
    : 'This is the standard platform shape before persona-specific controls or exception lanes are applied.'

  const views: AudienceView[] = [{
    id: 'baseline',
    label: 'Shared Baseline',
    description: baselineDescription,
    nodes: resolvedNodes.filter((node) => !addedNodeIdSet.has(node.id) && node.resolvedPathRole !== 'overlay'),
    customizations: [],
    triggers: [],
    tradeoffs: [],
    addedCount: 0,
    isBaseline: true,
  }]

  const assignedCustomizationIds = new Set<string>()

  supportingGroups.forEach((group) => {
    if (group.nodes.length === 0) return
    const groupNodeIds = new Set(group.nodes.map((node) => node.id))
    const customizations = (artifact?.customizations ?? []).filter((item) => {
      const matches = item.added_component_ids.some((id) => groupNodeIds.has(id))
      if (matches) assignedCustomizationIds.add(item.id)
      return matches
    })
    views.push({
      id: group.id,
      label: friendlyAudienceLabel(group.title),
      description: group.subtitle,
      nodes: group.nodes,
      customizations,
      triggers: dedupeText(customizations.flatMap((item) => item.triggered_by)),
      tradeoffs: dedupeText(customizations.map((item) => item.tradeoff).filter(Boolean)),
      addedCount: group.nodes.filter((node) => addedNodeIdSet.has(node.id)).length,
    })
  })

  const unmatchedCustomizations = (artifact?.customizations ?? []).filter((item) => !assignedCustomizationIds.has(item.id))
  const unmatchedNodes = uniqueNodes(
    unmatchedCustomizations.flatMap((item) => item.added_component_ids.map((id) => nodeById.get(id)).filter(Boolean) as ResolvedNode[]),
  )
  if (unmatchedCustomizations.length > 0 || unmatchedNodes.length > 0) {
    views.push({
      id: 'customer-additions',
      label: 'Customer additions',
      description: 'Customer-specific components that change the standard platform but were not grouped into a dedicated persona lane.',
      nodes: unmatchedNodes,
      customizations: unmatchedCustomizations,
      triggers: dedupeText(unmatchedCustomizations.flatMap((item) => item.triggered_by)),
      tradeoffs: dedupeText(unmatchedCustomizations.map((item) => item.tradeoff).filter(Boolean)),
      addedCount: unmatchedNodes.filter((node) => addedNodeIdSet.has(node.id)).length,
    })
  }

  return views
}

function sectionFromFlowSegment(
  segment: ArchitectureFlowSegment,
  nodeById: Map<string, ResolvedNode>,
  nodes: ResolvedNode[],
): FlowStage | null {
  const resolved = uniqueNodes(segment.component_ids.map((id) => nodeById.get(id)).filter(Boolean) as ResolvedNode[])
  const fallback = resolved.length > 0 ? resolved : inferFlowNodesFromSegment(segment, nodes)
  if (fallback.length === 0) return null
  return {
    id: segment.id,
    title: friendlyFlowTitle(segment.title, segment.id),
    subtitle: segment.narrative,
    accent: accentForSection(segment.id, fallback[0]?.layer),
    nodes: fallback,
  }
}

function sectionFromOverlay(
  group: ArchitectureOverlayGroup,
  nodeById: Map<string, ResolvedNode>,
  mode: 'control' | 'supporting' = 'control',
): ControlGroup | null {
  const resolved = uniqueNodes(group.component_ids.map((id) => nodeById.get(id)).filter(Boolean) as ResolvedNode[])
  if (resolved.length === 0) return null
  const accent = mode === 'supporting'
    ? accentForSupportingSection(group.id, resolved[0]?.layer)
    : accentForControlSection(group.id, resolved[0]?.layer)

  return {
    id: group.id,
    title: mode === 'supporting' ? friendlyAudienceLabel(group.title) : friendlyControlTitle(group.title, group.id),
    subtitle: group.narrative,
    accent,
    nodes: resolved,
  }
}

function makeFlowStage(
  id: string,
  title: string,
  subtitle: string,
  accent: string,
  nodes: ResolvedNode[],
): FlowStage | null {
  if (nodes.length === 0) return null
  return { id, title, subtitle, accent, nodes }
}

function makeControlGroup(
  id: string,
  title: string,
  subtitle: string,
  accent: string,
  nodes: ResolvedNode[],
): ControlGroup | null {
  if (nodes.length === 0) return null
  return { id, title, subtitle, accent, nodes }
}

function inferFlowNodesFromSegment(segment: ArchitectureFlowSegment, nodes: ResolvedNode[]) {
  const id = segment.id.toLowerCase()
  const title = segment.title.toLowerCase()

  if (id.includes('surface') || title.includes('surface') || title.includes('developer')) {
    return nodes.filter((node) => node.layer === 'surface')
  }
  if (id.includes('harness') || title.includes('harness')) {
    return nodes.filter((node) => node.layer === 'harness' && node.resolvedPathRole === 'primary')
  }
  if (id.includes('execution') || title.includes('execution')) {
    return nodes.filter((node) => node.layer === 'execution' && node.resolvedPathRole === 'primary')
  }
  if (id.includes('model') || title.includes('model')) {
    return nodes.filter((node) => node.layer === 'model' || isModelRouteNode(node))
  }
  if (id.includes('tool') || title.includes('tool') || id.includes('gateway') || title.includes('gateway') || title.includes('context')) {
    return nodes.filter((node) => node.layer === 'gateway' && node.resolvedPathRole === 'primary' && !isControlPlaneGatewayNode(node))
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
    return label.includes('cost') || label.includes('spend') || label.includes('quota')
      ? 'cost_control'
      : 'observability_control'
  }
  if (node.layer === 'execution') {
    return label.includes('runtime') ? 'agent_runtime' : 'execution_lane'
  }
  if (node.layer === 'gateway') {
    if (label.includes('model gateway') || label.includes('litellm') || label.includes('bedrock')) return 'model_gateway'
    if (label.includes('knowledge base') || label.includes(' kb') || label.endsWith('kb')) return 'knowledge_source'
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

function findCustomizationForNode(
  artifact: ArchitectureArtifact | null,
  nodeId: string,
) {
  if (!artifact) return null
  return artifact.customizations.find((item) => item.added_component_ids.includes(nodeId)) ?? null
}

function uniqueNodes(nodes: ResolvedNode[]) {
  const seen = new Set<string>()
  return nodes.filter((node) => {
    if (seen.has(node.id)) return false
    seen.add(node.id)
    return true
  })
}

function dedupeText(items: string[]) {
  return Array.from(new Set(items.filter(Boolean)))
}

function accentForSection(id: string, layer?: string) {
  const normalized = id.toLowerCase()
  if (normalized.includes('surface') || normalized.includes('developer')) return '#5161ff'
  if (normalized.includes('harness')) return '#7c4dff'
  if (normalized.includes('execution')) return '#a855f7'
  if (normalized.includes('model')) return '#10b981'
  if (normalized.includes('tool') || normalized.includes('gateway') || normalized.includes('context')) return '#0ea5e9'
  if (layer && LAYER_META[layer]) return LAYER_META[layer].color
  return '#7c4dff'
}

function accentForControlSection(id: string, layer?: string) {
  const normalized = id.toLowerCase()
  if (normalized.includes('identity') || normalized.includes('policy') || normalized.includes('access')) return '#ef4444'
  if (normalized.includes('registry') || normalized.includes('catalog') || normalized.includes('tool')) return '#0ea5e9'
  if (normalized.includes('audit') || normalized.includes('ops') || normalized.includes('cost') || normalized.includes('observe')) return '#f59e0b'
  if (layer === 'access') return '#ef4444'
  if (layer === 'ops') return '#f59e0b'
  if (layer === 'gateway') return '#0ea5e9'
  return '#ef4444'
}

function accentForSupportingSection(id: string, layer?: string) {
  const normalized = id.toLowerCase()
  if (normalized.includes('runtime')) return '#9333ea'
  if (normalized.includes('exception')) return '#7c3aed'
  if (layer === 'execution') return '#a855f7'
  if (layer === 'harness') return '#7c4dff'
  return '#7c3aed'
}

function friendlyFlowTitle(title: string, id: string) {
  const source = `${title} ${id}`.toLowerCase()
  if (source.includes('surface') || source.includes('developer')) return 'Developer entry'
  if (source.includes('harness')) return 'Approved harness'
  if (source.includes('execution')) return 'Execution boundary'
  if (source.includes('tool') || source.includes('context')) return 'Tool and context path'
  if (source.includes('gateway') && !source.includes('model')) return 'Shared platform path'
  if (source.includes('model')) return 'Model route'
  return title
}

function friendlyControlTitle(title: string, id: string) {
  const source = `${title} ${id}`.toLowerCase()
  if (source.includes('identity') || source.includes('access')) return 'Identity and access'
  if (source.includes('policy') || source.includes('guardrail')) return 'Policy and guardrails'
  if (source.includes('registry') || source.includes('catalog')) return 'Registry and catalog'
  if (source.includes('audit')) return 'Audit trail'
  if (source.includes('observe')) return 'Observability'
  if (source.includes('cost') || source.includes('quota') || source.includes('spend')) return 'Cost and quota'
  return title
}

function friendlyAudienceLabel(title: string) {
  const value = title.trim()
  if (!value) return 'Specialized lane'
  return value
}

function isModelRouteNode(node: ResolvedNode) {
  return node.resolvedKind === 'model_gateway' || node.layer === 'model'
}

function isRegistryNode(node: ResolvedNode) {
  const label = `${node.label} ${node.sublabel ?? ''}`.toLowerCase()
  return node.resolvedKind === 'registry_control'
    || label.includes('registry')
    || label.includes('catalog')
    || label.includes('mcp')
}

function isAuditNode(node: ResolvedNode) {
  const label = `${node.label} ${node.sublabel ?? ''}`.toLowerCase()
  return label.includes('audit') || label.includes('log') || label.includes('siem')
}

function isControlPlaneGatewayNode(node: ResolvedNode) {
  const label = `${node.label} ${node.sublabel ?? ''}`.toLowerCase()
  return node.resolvedPathRole === 'overlay'
    || node.resolvedKind === 'registry_control'
    || label.includes('registry')
    || label.includes('catalog')
    || label.includes('policy')
}

function transitionLabel(current: FlowStage, next: FlowStage) {
  const from = current.id.toLowerCase()
  const to = next.id.toLowerCase()
  if (from.includes('surface') && to.includes('harness')) return 'The developer enters an approved workspace'
  if (to.includes('execution')) return 'The platform selects the execution boundary'
  if (to.includes('tool') || to.includes('context')) return 'The request passes through the shared platform path'
  if (to.includes('model')) return 'The control plane routes to the right model path'
  return 'The request moves to the next platform step'
}

function inferLayerRowsFromStages(stages: FlowStage[]): ArchitectureLayerSummary[] {
  return stages.map((stage) => ({
    id: stage.id,
    label: stage.title,
    purpose: stage.subtitle,
    component_ids: stage.nodes.map((node) => node.id),
    component_labels: stage.nodes.map((node) => node.label),
  }))
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

function FlowStageCard({
  stage,
  addedNodeIdSet,
}: {
  stage: FlowStage
  addedNodeIdSet: Set<string>
}) {
  return (
    <div style={flowCardStyle(stage.accent)}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
          <div style={flowCardTitleStyle}>{stage.title}</div>
          <span style={flowBadgeStyle(stage.accent)}>{stage.nodes.length}</span>
        </div>
        <div style={flowCardTextStyle}>{stage.subtitle}</div>
      </div>
      <div style={chipWrapStyle}>
        {stage.nodes.map((node) => (
          <NodeChip key={node.id} node={node} isAdded={addedNodeIdSet.has(node.id)} />
        ))}
      </div>
    </div>
  )
}

function ControlGroupCard({
  group,
  addedNodeIdSet,
}: {
  group: ControlGroup
  addedNodeIdSet: Set<string>
}) {
  return (
    <div style={controlCardStyle(group.accent)}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={controlCardTitleStyle}>{group.title}</div>
        <div style={controlCardTextStyle}>{group.subtitle}</div>
      </div>
      <div style={controlNodeListStyle}>
        {group.nodes.map((node) => (
          <NodeRow key={node.id} node={node} isAdded={addedNodeIdSet.has(node.id)} />
        ))}
      </div>
    </div>
  )
}

function NodeChip({ node, isAdded }: { node: ResolvedNode; isAdded: boolean }) {
  return (
    <div style={nodeChipStyle(node.color, isAdded)}>
      <span style={tinyIconWrapStyle(node.color)}>
        <IconGlyph icon={node.icon} color={node.color} size={14} />
      </span>
      <span style={{ minWidth: 0 }}>{node.label}</span>
      {isAdded ? <span style={inlineAddedStyle}>Added</span> : null}
    </div>
  )
}

function NodeRow({ node, isAdded }: { node: ResolvedNode; isAdded: boolean }) {
  return (
    <div style={nodeRowStyle(node.color, isAdded)}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', minWidth: 0 }}>
        <span style={smallIconWrapStyle(node.color)}>
          <IconGlyph icon={node.icon} color={node.color} size={14} />
        </span>
        <div style={{ minWidth: 0 }}>
          <div style={nodeRowTitleStyle}>{node.label}</div>
          {node.sublabel ? <div style={nodeRowTextStyle}>{node.sublabel}</div> : null}
        </div>
      </div>
      {isAdded ? <span style={sideAddedStyle}>Added</span> : null}
    </div>
  )
}

function AudienceNodeRow({ node, isAdded }: { node: ResolvedNode; isAdded: boolean }) {
  return (
    <div style={audienceNodeRowStyle(node.color, isAdded)}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <span style={smallIconWrapStyle(node.color)}>
          <IconGlyph icon={node.icon} color={node.color} size={14} />
        </span>
        <div>
          <div style={reasonTitleStyle}>{node.label}</div>
          {node.sublabel ? <div style={reasonTextStyle}>{node.sublabel}</div> : null}
        </div>
      </div>
      {isAdded ? <span style={sideAddedStyle}>Added</span> : null}
    </div>
  )
}

function FlowConnector({ label }: { label: string }) {
  return (
    <div style={flowConnectorStyle}>
      <span style={connectorRuleStyle} />
      <span style={connectorTextStyle}>{label}</span>
      <span style={connectorArrowStyle}>→</span>
    </div>
  )
}

function LayerRow({ layer }: { layer: ArchitectureLayerSummary }) {
  return (
    <div style={layerRowStyle}>
      <div style={layerLabelStyle}>{layer.label}</div>
      <div style={layerComponentsStyle}>
        {layer.component_labels.join(' · ') || 'Components will appear here as the baseline forms.'}
      </div>
      {layer.purpose ? <div style={layerPurposeStyle}>{layer.purpose}</div> : null}
    </div>
  )
}

function MetricPill({
  label,
  value,
  accent = false,
  warning = false,
}: {
  label: string
  value: string
  accent?: boolean
  warning?: boolean
}) {
  return (
    <span style={metricPillStyle({ accent, warning })}>
      <span>{label}</span>
      <strong>{value}</strong>
    </span>
  )
}

function InfoPair({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={infoLabelStyle}>{label}</div>
      <div style={infoValueStyle}>{value}</div>
    </div>
  )
}

function LegendBadge({ label, accent = false }: { label: string; accent?: boolean }) {
  return (
    <span style={legendBadgeStyle(accent)}>
      {label}
    </span>
  )
}

const emptyShellStyle: CSSProperties = {
  minHeight: 0,
  height: '100%',
  overflowY: 'auto',
  padding: 18,
}

const emptyCardStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  borderRadius: 22,
  padding: 22,
  background: 'linear-gradient(180deg, rgba(255,255,255,0.95), rgba(247,241,231,0.92))',
  border: '1px solid rgba(31,27,22,0.08)',
}

const shellStyle: CSSProperties = {
  minHeight: 0,
  height: '100%',
  overflowY: 'auto',
  padding: 18,
  background: 'linear-gradient(180deg, #f6f0e8 0%, #efe5d7 100%)',
}

const innerStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 18,
  minWidth: 0,
}

const headerStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1.35fr) minmax(260px, 0.65fr)',
  gap: 16,
  alignItems: 'stretch',
}

const sourceCardStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'space-between',
  gap: 14,
  padding: 18,
  borderRadius: 20,
  color: '#f6f0e8',
  background: 'linear-gradient(180deg, #1f2332 0%, #10141f 100%)',
  boxShadow: '0 18px 36px rgba(16,20,31,0.18)',
}

const summaryPanelStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1.45fr) minmax(320px, 0.8fr)',
  gap: 16,
}

const summaryBodyPanelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  padding: 20,
  borderRadius: 22,
  background: 'rgba(255,255,255,0.84)',
  border: '1px solid rgba(31,27,22,0.08)',
  boxShadow: '0 12px 24px rgba(90,69,42,0.08)',
}

const summarySidePanelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  padding: 20,
  borderRadius: 22,
  background: 'rgba(255,255,255,0.84)',
  border: '1px solid rgba(31,27,22,0.08)',
  boxShadow: '0 12px 24px rgba(90,69,42,0.08)',
}

const diagramSectionStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
  padding: 20,
  borderRadius: 24,
  background: 'rgba(255,255,255,0.84)',
  border: '1px solid rgba(31,27,22,0.08)',
  boxShadow: '0 12px 24px rgba(90,69,42,0.08)',
}

const sectionHeadingRowStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
  flexWrap: 'wrap',
}

const diagramViewportStyle: CSSProperties = {
  overflowX: 'auto',
  paddingBottom: 2,
}

const diagramSceneStyle: CSSProperties = {
  minWidth: 1040,
  display: 'grid',
  gridTemplateColumns: 'minmax(720px, 1fr) 270px',
  gap: 16,
  alignItems: 'stretch',
}

const flowAreaStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}

const controlStripStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  padding: 16,
  borderRadius: 20,
  background: 'linear-gradient(180deg, rgba(27,31,45,0.96), rgba(18,22,32,0.96))',
  color: '#f6f0e8',
}

const laneHeadingStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
}

const controlStripHeaderStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  paddingBottom: 8,
  borderBottom: '1px solid rgba(246,240,232,0.12)',
}

const flowStripStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(5, minmax(150px, 1fr))',
  gap: 12,
  alignItems: 'start',
}

const flowItemWrapStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
}

const audienceSectionStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
  padding: 20,
  borderRadius: 24,
  background: 'rgba(255,255,255,0.84)',
  border: '1px solid rgba(31,27,22,0.08)',
  boxShadow: '0 12px 24px rgba(90,69,42,0.08)',
}

const detailGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: 16,
}

const detailCardStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  padding: 18,
  borderRadius: 20,
  background: 'rgba(255,255,255,0.84)',
  border: '1px solid rgba(31,27,22,0.08)',
  boxShadow: '0 10px 20px rgba(90,69,42,0.06)',
  minWidth: 0,
}

const tabBarStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
  flexWrap: 'wrap',
}

const nodeListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  marginTop: 4,
}

const reasonCardStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  padding: 14,
  borderRadius: 16,
  background: 'rgba(31,27,22,0.035)',
  border: '1px solid rgba(31,27,22,0.08)',
}

const pendingBannerStyle: CSSProperties = {
  marginTop: 4,
  padding: '12px 14px',
  borderRadius: 14,
  background: 'rgba(245, 158, 11, 0.10)',
  border: '1px solid rgba(245, 158, 11, 0.20)',
  fontSize: 12.5,
  lineHeight: 1.55,
  color: '#6b4e12',
}

const titleStyle: CSSProperties = {
  fontSize: 32,
  lineHeight: 1.05,
  margin: 0,
  color: '#1f1b16',
  letterSpacing: '-0.03em',
}

const introStyle: CSSProperties = {
  margin: 0,
  fontSize: 14,
  lineHeight: 1.65,
  color: 'rgba(31,27,22,0.72)',
  maxWidth: 760,
}

const eyebrow: CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: 'rgba(31,27,22,0.5)',
}

const summaryBodyStyle: CSSProperties = {
  margin: 0,
  fontSize: 14,
  lineHeight: 1.72,
  color: '#1f1b16',
}

const microCardStyle: CSSProperties = {
  padding: 12,
  borderRadius: 14,
  background: 'rgba(31,27,22,0.035)',
  border: '1px solid rgba(31,27,22,0.08)',
  fontSize: 12.5,
  lineHeight: 1.55,
  color: 'rgba(31,27,22,0.78)',
}

const microCardTitleStyle: CSSProperties = {
  fontSize: 13.5,
  fontWeight: 650,
  marginBottom: 4,
  color: '#1f1b16',
}

const microCardTextStyle: CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.55,
  color: 'rgba(31,27,22,0.74)',
}

const sectionTitleStyle: CSSProperties = {
  fontSize: 22,
  lineHeight: 1.1,
  letterSpacing: '-0.02em',
  margin: '4px 0 0',
  color: '#1f1b16',
}

const legendWrapStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
  alignItems: 'center',
  flexWrap: 'wrap',
}

const laneHeadingEyebrowStyle: CSSProperties = {
  ...eyebrow,
  color: 'rgba(31,27,22,0.48)',
}

const laneHeadingTitleStyle: CSSProperties = {
  fontSize: 16,
  fontWeight: 650,
  lineHeight: 1.3,
  color: '#1f1b16',
}

const flowCardTitleStyle: CSSProperties = {
  fontSize: 15,
  fontWeight: 700,
  lineHeight: 1.2,
  color: '#1f1b16',
}

const flowCardTextStyle: CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.55,
  color: 'rgba(31,27,22,0.68)',
}

const controlCardTitleStyle: CSSProperties = {
  fontSize: 14.5,
  fontWeight: 700,
  lineHeight: 1.2,
  color: '#f6f0e8',
}

const controlCardTextStyle: CSSProperties = {
  fontSize: 12.25,
  lineHeight: 1.55,
  color: 'rgba(246,240,232,0.74)',
}

const chipWrapStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const controlNodeListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const flowConnectorStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  minHeight: 28,
}

const connectorRuleStyle: CSSProperties = {
  flex: 1,
  height: 1,
  background: 'rgba(31,27,22,0.12)',
}

const connectorTextStyle: CSSProperties = {
  fontSize: 11,
  lineHeight: 1.45,
  color: 'rgba(31,27,22,0.56)',
  textAlign: 'center',
}

const connectorArrowStyle: CSSProperties = {
  fontSize: 18,
  lineHeight: 1,
  color: 'rgba(31,27,22,0.36)',
}

const detailIntroStyle: CSSProperties = {
  margin: 0,
  fontSize: 13,
  lineHeight: 1.6,
  color: 'rgba(31,27,22,0.68)',
}

const exceptionRowStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  padding: 12,
  borderRadius: 16,
  background: 'rgba(31,27,22,0.035)',
  border: '1px solid rgba(31,27,22,0.08)',
}

const exceptionTitleStyle: CSSProperties = {
  fontSize: 13.5,
  fontWeight: 700,
  color: '#1f1b16',
}

const exceptionCountStyle: CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  color: 'rgba(31,27,22,0.52)',
}

const exceptionTextStyle: CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.55,
  color: 'rgba(31,27,22,0.72)',
}

const emptyNoteStyle: CSSProperties = {
  padding: 14,
  borderRadius: 16,
  background: 'rgba(31,27,22,0.03)',
  border: '1px dashed rgba(31,27,22,0.12)',
  fontSize: 12.5,
  lineHeight: 1.55,
  color: 'rgba(31,27,22,0.66)',
}

const reasonTitleStyle: CSSProperties = {
  fontSize: 13.5,
  fontWeight: 700,
  color: '#1f1b16',
}

const reasonTextStyle: CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.55,
  color: 'rgba(31,27,22,0.72)',
}

const tradeoffTextStyle: CSSProperties = {
  fontSize: 12.25,
  lineHeight: 1.5,
  color: 'rgba(31,27,22,0.6)',
}

const bulletListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
}

const bulletRowStyle: CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.55,
  color: 'rgba(31,27,22,0.72)',
}

const additionRowStyle: CSSProperties = {
  padding: 12,
  borderRadius: 16,
  background: 'rgba(31,27,22,0.035)',
  border: '1px solid rgba(31,27,22,0.08)',
}

const infoLabelStyle: CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'rgba(246,240,232,0.58)',
}

const infoValueStyle: CSSProperties = {
  fontSize: 14.5,
  lineHeight: 1.45,
  color: '#f6f0e8',
}

const layerRowStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  padding: '12px 14px',
  borderRadius: 14,
  background: 'rgba(31,27,22,0.035)',
  border: '1px solid rgba(31,27,22,0.08)',
}

const layerLabelStyle: CSSProperties = {
  fontSize: 13,
  fontWeight: 700,
  color: '#1f1b16',
}

const layerComponentsStyle: CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.55,
  color: 'rgba(31,27,22,0.78)',
}

const layerPurposeStyle: CSSProperties = {
  fontSize: 12.25,
  lineHeight: 1.5,
  color: 'rgba(31,27,22,0.6)',
}

const pillWrapStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
  flexWrap: 'wrap',
}

function metricPillStyle({
  accent,
  warning,
}: {
  accent?: boolean
  warning?: boolean
}): CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 12px',
    borderRadius: 999,
    border: warning
      ? '1px solid rgba(245, 158, 11, 0.25)'
      : accent
        ? '1px solid rgba(81,97,255,0.20)'
        : '1px solid rgba(31,27,22,0.10)',
    background: warning
      ? 'rgba(245, 158, 11, 0.10)'
      : accent
        ? 'rgba(81,97,255,0.08)'
        : 'rgba(255,255,255,0.75)',
    fontSize: 12,
    fontWeight: 600,
    color: '#1f1b16',
  }
}

function flowCardStyle(accent: string): CSSProperties {
  return {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    minHeight: 220,
    padding: 16,
    borderRadius: 20,
    background: 'linear-gradient(180deg, rgba(255,255,255,0.98), rgba(245,239,230,0.96))',
    border: `1px solid ${accent}20`,
    boxShadow: `0 12px 24px ${accent}10`,
  }
}

function flowBadgeStyle(accent: string): CSSProperties {
  return {
    minWidth: 24,
    height: 24,
    borderRadius: 999,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: `${accent}14`,
    border: `1px solid ${accent}25`,
    color: '#1f1b16',
    fontSize: 11,
    fontWeight: 700,
  }
}

function controlCardStyle(accent: string): CSSProperties {
  return {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    padding: 14,
    borderRadius: 16,
    background: 'rgba(246,240,232,0.05)',
    border: `1px solid ${accent}28`,
  }
}

function nodeChipStyle(color: string, isAdded: boolean): CSSProperties {
  return {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    minWidth: 0,
    padding: '8px 10px',
    borderRadius: 12,
    background: isAdded ? `${color}12` : 'rgba(31,27,22,0.04)',
    border: `1px solid ${isAdded ? `${color}28` : 'rgba(31,27,22,0.08)'}`,
    color: '#1f1b16',
    fontSize: 12.5,
    fontWeight: 600,
    lineHeight: 1.35,
  }
}

function nodeRowStyle(color: string, isAdded: boolean): CSSProperties {
  return {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 10,
    padding: '10px 10px',
    borderRadius: 12,
    background: isAdded ? `${color}10` : 'rgba(246,240,232,0.05)',
    border: `1px solid ${isAdded ? `${color}28` : 'rgba(246,240,232,0.10)'}`,
  }
}

function audienceNodeRowStyle(color: string, isAdded: boolean): CSSProperties {
  return {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 10,
    alignItems: 'flex-start',
    padding: 12,
    borderRadius: 14,
    background: isAdded ? `${color}10` : 'rgba(31,27,22,0.035)',
    border: `1px solid ${isAdded ? `${color}28` : 'rgba(31,27,22,0.08)'}`,
  }
}

function tinyIconWrapStyle(color: string): CSSProperties {
  return {
    width: 22,
    height: 22,
    borderRadius: 999,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: `${color}16`,
    border: `1px solid ${color}26`,
    flexShrink: 0,
  }
}

function smallIconWrapStyle(color: string): CSSProperties {
  return {
    width: 26,
    height: 26,
    borderRadius: 999,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: `${color}16`,
    border: `1px solid ${color}26`,
    flexShrink: 0,
  }
}

const inlineAddedStyle: CSSProperties = {
  marginLeft: 'auto',
  flexShrink: 0,
  padding: '2px 6px',
  borderRadius: 999,
  background: 'rgba(81,97,255,0.10)',
  border: '1px solid rgba(81,97,255,0.20)',
  fontSize: 10,
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  color: '#1f1b16',
}

const sideAddedStyle: CSSProperties = {
  flexShrink: 0,
  padding: '2px 6px',
  borderRadius: 999,
  background: 'rgba(81,97,255,0.10)',
  border: '1px solid rgba(81,97,255,0.20)',
  fontSize: 10,
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  color: '#1f1b16',
}

const nodeRowTitleStyle: CSSProperties = {
  fontSize: 12.75,
  fontWeight: 700,
  lineHeight: 1.35,
  color: '#f6f0e8',
}

const nodeRowTextStyle: CSSProperties = {
  fontSize: 11.75,
  lineHeight: 1.5,
  color: 'rgba(246,240,232,0.70)',
}

function legendBadgeStyle(accent: boolean): CSSProperties {
  return {
    padding: '5px 8px',
    borderRadius: 999,
    border: accent ? '1px solid rgba(81,97,255,0.22)' : '1px solid rgba(31,27,22,0.12)',
    background: accent ? 'rgba(81,97,255,0.08)' : 'rgba(31,27,22,0.04)',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    color: 'rgba(31,27,22,0.76)',
  }
}

function tabButtonStyle(active: boolean): CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '9px 12px',
    borderRadius: 12,
    border: active ? '1px solid rgba(81,97,255,0.26)' : '1px solid rgba(31,27,22,0.10)',
    background: active ? 'rgba(81,97,255,0.10)' : 'rgba(255,255,255,0.78)',
    color: '#1f1b16',
    fontSize: 12.5,
    fontWeight: 650,
    cursor: 'pointer',
  }
}

function tabCountStyle(active: boolean): CSSProperties {
  return {
    minWidth: 20,
    height: 20,
    borderRadius: 999,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: active ? 'rgba(81,97,255,0.18)' : 'rgba(31,27,22,0.07)',
    fontSize: 10.5,
    fontWeight: 700,
  }
}
