'use client'

import { useMemo, type CSSProperties } from 'react'
import { useStore } from '@/store'
import type { ArchNode, ArchitectureArtifact } from '@/lib/types'
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
    purpose: 'The operating environment and governance shell for the agent loop.',
  },
  execution: {
    label: 'Execution',
    color: '#a78bfa',
    purpose: 'Where the work actually runs and what trust boundary contains it.',
  },
  gateway: {
    label: 'Gateway',
    color: '#06b6d4',
    purpose: 'Where routing, policy enforcement, and enterprise integration happen.',
  },
  model: {
    label: 'Model',
    color: '#10b981',
    purpose: 'The capability tiers that power different classes of work.',
  },
  ops: {
    label: 'Ops',
    color: '#f59e0b',
    purpose: 'How the platform is observed, governed, and cost-controlled.',
  },
  access: {
    label: 'Access',
    color: '#ef4444',
    purpose: 'Identity, spend policy, and protection controls.',
  },
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
  const grouped = useMemo(() => groupByLayer(archNodes), [archNodes])
  const factHighlights = workspace.facts.slice(0, 4)
  const decisionHighlights = (architectureArtifact?.decisions ?? []).slice(0, 3)
  const sessionTitle = conversations.find((item) => item.session.session_id === activeSessionId)?.session.title
    ?? 'Current architecture'
  const updatedAt = workspace.updated_at ?? ''
  const hasArchitecture = archNodes.length > 0 || Boolean(architectureArtifact)
  const organizationAdditions = useMemo(
    () => archNodes.filter((node) => addedNodeIdSet.has(node.id)),
    [addedNodeIdSet, archNodes],
  )
  const baselineComponentCount = archNodes.length - organizationAdditions.length
  const accessNodes = grouped.access
  const opsNodes = grouped.ops
  const gatewayNodes = grouped.gateway
  const modelNodes = grouped.model
  const executionNode = grouped.execution[0]
  const baselineLayers = architectureArtifact?.baseline.layers ?? []
  const summary = architectureArtifact?.executive_summary || workspace.recommendation

  if (!hasArchitecture) {
    return (
      <div style={{
        flex: 1,
        minHeight: 0,
        overflow: 'auto',
        background: 'var(--bg-elevated-2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}>
        <div style={{
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
        }}>
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
    <div style={{
      flex: 1,
      minHeight: 0,
      overflow: 'auto',
      background: 'linear-gradient(180deg, #0f1116 0%, #17171b 100%)',
      color: '#1f1b16',
    }}>
      <div style={{
        maxWidth: 1560,
        margin: '0 auto',
        padding: '20px 18px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
      }}>
        <header style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.5fr) minmax(240px, 0.7fr)',
          gap: 14,
          alignItems: 'start',
        }}>
          <div style={{
            background: 'rgba(255,255,255,0.76)',
            border: '1px solid rgba(31,27,22,0.12)',
            borderRadius: 24,
            padding: 18,
            boxShadow: '0 18px 50px rgba(80, 60, 38, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}>
            <span style={eyebrow}>Architecture</span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <h1 style={{
                fontSize: 28,
                lineHeight: 1.04,
                fontWeight: 700,
                letterSpacing: '-0.04em',
              }}>
                Architecture Board
              </h1>
              <p style={{
                fontSize: 13.5,
                lineHeight: 1.6,
                color: 'rgba(31,27,22,0.82)',
                maxWidth: 860,
              }}>
                A leadership-readable view of the current session architecture. This tab is driven from the live
                architecture artifact, so it should change whenever new answers alter the baseline or add customer-specific controls.
              </p>
            </div>
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 10,
            }}>
              <span style={factPill}>Baseline components {baselineComponentCount}</span>
              <span style={addedPill(organizationAdditions.length > 0)}>Customer additions {organizationAdditions.length}</span>
              {factHighlights.map((fact) => (
                <span key={fact} style={factPill}>{fact}</span>
              ))}
            </div>
          </div>

          <div style={{
            background: '#1f1b16',
            color: '#f6f0e8',
            borderRadius: 24,
            padding: 18,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            boxShadow: '0 22px 60px rgba(31,27,22,0.18)',
          }}>
            <span style={{ ...eyebrow, color: 'rgba(246,240,232,0.66)' }}>Source</span>
            <div>
              <div style={{ fontSize: 14, color: 'rgba(246,240,232,0.72)' }}>Session</div>
              <div style={{ fontSize: 18, lineHeight: 1.4, fontWeight: 600 }}>{sessionTitle}</div>
            </div>
            <div>
              <div style={{ fontSize: 14, color: 'rgba(246,240,232,0.72)' }}>Snapshot</div>
              <div style={{ fontSize: 15, lineHeight: 1.4 }}>{formatTimestamp(updatedAt)}</div>
            </div>
            <div>
              <div style={{ fontSize: 14, color: 'rgba(246,240,232,0.72)' }}>Target Architecture</div>
              <div style={{ fontSize: 15, lineHeight: 1.45 }}>
                {architectureArtifact?.baseline.name || 'Working architecture'}
              </div>
            </div>
          </div>
        </header>

        {workspace.open_questions.length > 0 && (
          <section style={{
            background: 'rgba(245,158,11,0.12)',
            border: '1px solid rgba(245,158,11,0.28)',
            color: '#f7dd9c',
            borderRadius: 18,
            padding: '14px 16px',
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
          }}>
            <span style={{ ...eyebrow, color: 'rgba(247,221,156,0.74)' }}>Pending Inputs</span>
            <p style={{ fontSize: 13.5, lineHeight: 1.6 }}>
              {workspace.open_questions.length} open question{workspace.open_questions.length === 1 ? '' : 's'} still
              affect the architecture. Use the `Questions` tab to answer them; this board will refresh when the advisor revises the design.
            </p>
          </section>
        )}

        <section style={heroPanel}>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.7fr) minmax(300px, 0.8fr)', gap: 18 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <span style={eyebrow}>Recommended Direction</span>
              <p style={{
                fontSize: 15.5,
                lineHeight: 1.62,
                color: 'rgba(31,27,22,0.88)',
              }}>
                {summary || 'Architecture summary will appear here as the advisor converges on a recommendation.'}
              </p>
            </div>
            <div style={{
              borderLeft: '1px solid rgba(31,27,22,0.12)',
              paddingLeft: 18,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}>
              <span style={eyebrow}>Three Things To Remember</span>
              {decisionHighlights.length > 0 ? decisionHighlights.map((item) => (
                <div key={item.decision} style={{
                  padding: '12px 14px',
                  borderRadius: 16,
                  background: 'rgba(31,27,22,0.04)',
                  border: '1px solid rgba(31,27,22,0.08)',
                }}>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{item.decision}</div>
                  <div style={{ fontSize: 12.5, lineHeight: 1.55, color: 'rgba(31,27,22,0.72)' }}>{item.why}</div>
                </div>
              )) : (
                <div style={{
                  padding: '12px 14px',
                  borderRadius: 16,
                  background: 'rgba(31,27,22,0.04)',
                  border: '1px solid rgba(31,27,22,0.08)',
                  fontSize: 12.5,
                  lineHeight: 1.55,
                  color: 'rgba(31,27,22,0.72)',
                }}>
                  Decision rationale will populate here once the architecture artifact includes explicit decisions.
                </div>
              )}
            </div>
          </div>
        </section>

        <section style={boardPanel}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
              <div>
                <span style={eyebrow}>Target Platform Shape</span>
                <h2 style={{
                  marginTop: 8,
                  fontSize: 22,
                  lineHeight: 1.12,
                  letterSpacing: '-0.03em',
                }}>
                  Standard platform in the center, governance on the edges
                </h2>
              </div>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                flexWrap: 'wrap',
                justifyContent: 'flex-end',
              }}>
                <LegendBadge label="Baseline" />
                <LegendBadge label="Added for customer" accent />
                <LegendSwatch color="#8b5cf6" label="Primary platform" />
                <LegendSwatch color="#06b6d4" label="Control points" />
                <LegendSwatch color="#10b981" label="Model tiers" />
              </div>
            </div>

            <div style={{
              marginTop: 16,
              padding: 16,
              borderRadius: 24,
              background: 'linear-gradient(180deg, rgba(255,255,255,0.92) 0%, rgba(255,255,255,0.76) 100%)',
              border: '1px solid rgba(31,27,22,0.1)',
              display: 'flex',
              flexDirection: 'column',
              gap: 14,
            }}>
              <FlowCard
                title="Developer Surface"
                subtitle={findLayerPurpose(architectureArtifact, 'surface')}
                nodes={grouped.surface}
                accent="#6366f1"
                addedNodeIdSet={addedNodeIdSet}
              />

              <FlowArrow label="Developer invokes the agent from the IDE" />

              <FlowCard
                title="Enterprise Harness"
                subtitle={findLayerPurpose(architectureArtifact, 'harness')}
                nodes={grouped.harness}
                accent="#8b5cf6"
                addedNodeIdSet={addedNodeIdSet}
              />

              <FlowArrow label="Requests pass through centralized policy and routing gates" />

              <FlowCard
                title="Gateway & Policy"
                subtitle={findLayerPurpose(architectureArtifact, 'gateway')}
                nodes={gatewayNodes}
                accent="#06b6d4"
                addedNodeIdSet={addedNodeIdSet}
                emphasis="control"
              />

              <FlowArrow label="Gateway selects the right model tier and execution path" />

              <FlowCard
                title="Model Tiers"
                subtitle={findLayerPurpose(architectureArtifact, 'model')}
                nodes={modelNodes}
                accent="#10b981"
                addedNodeIdSet={addedNodeIdSet}
                emphasis="model"
              />

              {executionNode && (
                <>
                  <FlowArrow label="Execution remains vendor-managed rather than customer-operated" />
                  <div style={{
                    borderRadius: 22,
                    padding: '14px 16px',
                    background: 'linear-gradient(135deg, rgba(167,139,250,0.16), rgba(139,92,246,0.1))',
                    border: '1px solid rgba(139,92,246,0.2)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span style={{
                        width: 38,
                        height: 38,
                        borderRadius: 12,
                        background: 'rgba(139,92,246,0.12)',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}>
                        <IconGlyph icon={executionNode.icon} color={executionNode.color} size={18} />
                      </span>
                      <div>
                        <div style={{ fontSize: 15, fontWeight: 650 }}>
                          {executionNode.label}
                          {addedNodeIdSet.has(executionNode.id) && (
                            <span style={{
                              marginLeft: 8,
                              padding: '2px 6px',
                              borderRadius: 999,
                              background: `${executionNode.color}18`,
                              border: `1px solid ${executionNode.color}35`,
                              fontSize: 10,
                              fontWeight: 700,
                              letterSpacing: '0.05em',
                              textTransform: 'uppercase',
                            }}>
                              Added
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: 12.5, color: 'rgba(31,27,22,0.74)', marginTop: 4 }}>
                          {executionNode.sublabel}
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>

            <div style={controlSectionGridStyle}>
              <div style={subPanel}>
                <span style={eyebrow}>Access Controls</span>
                <div style={compactControlGridStyle}>
                  {accessNodes.map((node) => (
                    <ControlCard
                      key={node.id}
                      node={node}
                      isAdded={addedNodeIdSet.has(node.id)}
                    />
                  ))}
                </div>
                <LayerNote
                  label="Access Layer"
                  text={findLayerPurpose(architectureArtifact, 'access')}
                />
              </div>

              <div style={subPanel}>
                <span style={eyebrow}>Run Controls</span>
                <div style={compactControlGridStyle}>
                  {opsNodes.map((node) => (
                    <ControlCard
                      key={node.id}
                      node={node}
                      isAdded={addedNodeIdSet.has(node.id)}
                    />
                  ))}
                </div>
                <LayerNote
                  label="Operations Layer"
                  text={findLayerPurpose(architectureArtifact, 'ops')}
                />
              </div>
            </div>

            <details style={supportingDetailsStyle}>
              <summary style={supportingSummaryStyle}>Supporting detail</summary>
              <div style={supportingBodyStyle}>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1.1fr 0.9fr',
                  gap: 16,
                }}>
                  <div style={subPanel}>
                    <span style={eyebrow}>Standard Platform</span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 10 }}>
                      {baselineLayers.map((layer) => (
                        <div key={layer.id} style={{
                          display: 'grid',
                          gridTemplateColumns: '120px 1fr',
                          gap: 12,
                          alignItems: 'start',
                        }}>
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
                        <div style={{
                          padding: '16px 16px',
                          borderRadius: 16,
                          background: 'rgba(31,27,22,0.035)',
                          border: '1px dashed rgba(31,27,22,0.14)',
                          fontSize: 12.5,
                          lineHeight: 1.6,
                          color: 'rgba(31,27,22,0.68)',
                        }}>
                          No org-specific structural additions were identified in this session. This means the current
                          recommendation remains a governed baseline rather than a one-off platform build.
                        </div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                          {organizationAdditions.map((node) => {
                            const customization = findCustomizationForNode(architectureArtifact, node.id)
                            return (
                              <div key={node.id} style={{
                                padding: '14px 14px',
                                borderRadius: 16,
                                background: 'rgba(99,102,241,0.06)',
                                border: '1px solid rgba(99,102,241,0.15)',
                              }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                  <span style={{
                                    width: 28,
                                    height: 28,
                                    borderRadius: 10,
                                    background: `${node.color}18`,
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    flexShrink: 0,
                                  }}>
                                    <IconGlyph icon={node.icon} color={node.color} size={14} />
                                  </span>
                                  <div style={{ fontSize: 13, fontWeight: 650 }}>{node.label}</div>
                                </div>
                                <div style={{ fontSize: 12.5, lineHeight: 1.55, marginTop: 7 }}>
                                  {customization?.reason || node.sublabel || 'Added beyond the baseline architecture for this organization.'}
                                </div>
                                {customization?.tradeoff && (
                                  <div style={{
                                    marginTop: 6,
                                    fontSize: 12,
                                    color: 'rgba(31,27,22,0.66)',
                                  }}>
                                    Tradeoff: {customization.tradeoff}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1.1fr 0.9fr',
                  gap: 18,
                }}>
                  <div style={subPanel}>
                    <span style={eyebrow}>Primary Risks</span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 10 }}>
                      {(architectureArtifact?.risks ?? []).map((risk) => (
                        <div key={risk.risk} style={{
                          borderRadius: 18,
                          background: 'rgba(255,255,255,0.78)',
                          border: '1px solid rgba(31,27,22,0.08)',
                          padding: '14px 14px',
                        }}>
                          <div style={{ fontSize: 13.5, fontWeight: 650, marginBottom: 4 }}>{risk.risk}</div>
                          <div style={{ fontSize: 12.5, lineHeight: 1.6, color: 'rgba(31,27,22,0.72)' }}>{risk.mitigation}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div style={subPanel}>
                    <span style={eyebrow}>Rollout</span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 10 }}>
                      {(architectureArtifact?.rollout ?? []).map((phase, index) => (
                        <div key={phase.phase} style={{
                          display: 'grid',
                          gridTemplateColumns: '34px 1fr',
                          gap: 12,
                          alignItems: 'start',
                        }}>
                          <div style={{
                            width: 34,
                            height: 34,
                            borderRadius: 12,
                            background: '#1f1b16',
                            color: '#f6f0e8',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: 13,
                            fontWeight: 700,
                          }}>
                            {index + 1}
                          </div>
                          <div style={{
                            borderRadius: 18,
                            background: 'rgba(255,255,255,0.78)',
                            border: '1px solid rgba(31,27,22,0.08)',
                            padding: '12px 14px',
                          }}>
                            <div style={{ fontSize: 13.5, fontWeight: 650 }}>{phase.phase}</div>
                            <div style={{ fontSize: 12.5, lineHeight: 1.6, color: 'rgba(31,27,22,0.72)', marginTop: 4 }}>
                              {phase.outcome}
                            </div>
                          </div>
                        </div>
                      ))}
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

function groupByLayer(nodes: ArchNode[]) {
  return {
    surface: nodes.filter((node) => node.layer === 'surface'),
    harness: nodes.filter((node) => node.layer === 'harness'),
    execution: nodes.filter((node) => node.layer === 'execution'),
    gateway: nodes.filter((node) => node.layer === 'gateway'),
    model: nodes.filter((node) => node.layer === 'model'),
    ops: nodes.filter((node) => node.layer === 'ops'),
    access: nodes.filter((node) => node.layer === 'access'),
  }
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

function FlowCard({
  title,
  subtitle,
  nodes,
  accent,
  addedNodeIdSet,
  emphasis = 'primary',
}: {
  title: string
  subtitle: string
  nodes: ArchNode[]
  accent: string
  addedNodeIdSet?: Set<string>
  emphasis?: 'primary' | 'control' | 'model'
}) {
  return (
    <div style={{
      borderRadius: 22,
      border: `1px solid ${accent}22`,
      background: `${accent}0d`,
      padding: 18,
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
    }}>
      <div>
        <div style={{ fontSize: 17, fontWeight: 650 }}>{title}</div>
        <div style={{ fontSize: 12.5, lineHeight: 1.55, color: 'rgba(31,27,22,0.68)', marginTop: 5 }}>
          {subtitle}
        </div>
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: 12,
      }}>
        {nodes.map((node) => (
          <NodeCard key={node.id} node={node} emphasis={emphasis} isAdded={addedNodeIdSet ? addedNodeIdSet.has(node.id) : false} />
        ))}
      </div>
    </div>
  )
}

function FlowArrow({ label }: { label: string }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 10,
      color: 'rgba(31,27,22,0.48)',
      fontSize: 12,
      letterSpacing: '0.02em',
    }}>
      <span style={{ width: 1, height: 12, background: 'rgba(31,27,22,0.15)' }} />
      <span>{label}</span>
      <span style={{ fontSize: 18, lineHeight: 1 }}>↓</span>
      <span style={{ width: 1, height: 12, background: 'rgba(31,27,22,0.15)' }} />
    </div>
  )
}

function NodeCard({
  node,
  emphasis,
  isAdded = false,
}: {
  node?: ArchNode
  emphasis: 'primary' | 'control' | 'model'
  isAdded?: boolean
}) {
  if (!node) return null

  const background = emphasis === 'model'
    ? 'linear-gradient(180deg, rgba(16,185,129,0.16), rgba(16,185,129,0.08))'
    : emphasis === 'control'
      ? 'linear-gradient(180deg, rgba(6,182,212,0.15), rgba(8,145,178,0.08))'
      : 'rgba(255,255,255,0.82)'

  return (
    <div style={{
      borderRadius: 18,
      background,
      border: isAdded ? `1px solid ${node.color}66` : `1px solid ${node.color}26`,
      padding: '14px 14px',
      minHeight: 112,
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      boxShadow: '0 10px 24px rgba(31,27,22,0.05)',
      position: 'relative',
    }}>
      {isAdded && (
        <span style={{
          position: 'absolute',
          top: 10,
          right: 10,
          padding: '3px 7px',
          borderRadius: 999,
          background: `${node.color}18`,
          border: `1px solid ${node.color}35`,
          color: '#1f1b16',
          fontSize: 10,
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
        }}>
          Added
        </span>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{
          width: 34,
          height: 34,
          borderRadius: 12,
          background: `${node.color}20`,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          <IconGlyph icon={node.icon} color={node.color} size={16} />
        </span>
        <div style={{ fontSize: 15, fontWeight: 650, lineHeight: 1.25 }}>{node.label}</div>
      </div>
      <div style={{ fontSize: 12.5, lineHeight: 1.58, color: 'rgba(31,27,22,0.7)' }}>
        {node.sublabel}
      </div>
    </div>
  )
}

function ControlCard({ node, isAdded = false }: { node: ArchNode; isAdded?: boolean }) {
  return (
    <div style={{
      padding: '14px 14px',
      borderRadius: 18,
      background: 'rgba(255,255,255,0.82)',
      border: isAdded ? `1px solid ${node.color}55` : `1px solid ${node.color}1f`,
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      boxShadow: '0 10px 24px rgba(31,27,22,0.05)',
      position: 'relative',
    }}>
      {isAdded && (
        <span style={{
          position: 'absolute',
          top: 10,
          right: 10,
          padding: '3px 7px',
          borderRadius: 999,
          background: `${node.color}18`,
          border: `1px solid ${node.color}35`,
          color: '#1f1b16',
          fontSize: 10,
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
        }}>
          Added
        </span>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{
          width: 32,
          height: 32,
          borderRadius: 11,
          background: `${node.color}16`,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          <IconGlyph icon={node.icon} color={node.color} size={15} />
        </span>
        <div style={{ fontSize: 14, fontWeight: 650, lineHeight: 1.25 }}>{node.label}</div>
      </div>
      <div style={{ fontSize: 12.5, lineHeight: 1.58, color: 'rgba(31,27,22,0.68)' }}>
        {node.sublabel}
      </div>
    </div>
  )
}

function LayerNote({ label, text }: { label: string; text: string }) {
  return (
    <div style={{
      marginTop: 'auto',
      paddingTop: 12,
      borderTop: '1px solid rgba(31,27,22,0.1)',
      display: 'flex',
      flexDirection: 'column',
      gap: 5,
    }}>
      <div style={{ fontSize: 12.5, fontWeight: 650 }}>{label}</div>
      <div style={{ fontSize: 12, lineHeight: 1.55, color: 'rgba(31,27,22,0.64)' }}>{text}</div>
    </div>
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

const eyebrow: CSSProperties = {
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.12em',
  fontWeight: 700,
  color: 'rgba(31,27,22,0.52)',
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

const heroPanel: CSSProperties = {
  background: 'rgba(255,255,255,0.78)',
  border: '1px solid rgba(31,27,22,0.1)',
  borderRadius: 24,
  padding: 18,
  boxShadow: '0 18px 50px rgba(80, 60, 38, 0.08)',
}

const boardPanel: CSSProperties = {
  borderRadius: 28,
  background: 'rgba(248,243,234,0.88)',
  border: '1px solid rgba(31,27,22,0.1)',
  padding: 18,
  minWidth: 0,
  boxShadow: '0 22px 60px rgba(80, 60, 38, 0.08)',
}

const subPanel: CSSProperties = {
  borderRadius: 24,
  background: 'rgba(255,255,255,0.74)',
  border: '1px solid rgba(31,27,22,0.1)',
  padding: 18,
  boxShadow: '0 18px 50px rgba(80, 60, 38, 0.06)',
}

const controlSectionGridStyle: CSSProperties = {
  marginTop: 14,
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
  gap: 14,
}

const compactControlGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
  gap: 10,
  marginTop: 10,
}

const supportingDetailsStyle: CSSProperties = {
  marginTop: 14,
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
