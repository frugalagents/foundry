'use client'

import { useMemo, useState } from 'react'
import { useStore } from '@/store'
import { hasAdvisoryCaseContent } from '@/lib/advisory-case'
import { normalizeWorkspace } from '@/lib/message-analysis'
import { renderMarkdown } from '@/lib/render-markdown'
import {
  buildExportMarkdown,
  buildFallbackBlueprint,
  hasOutputPackContent,
} from '@/lib/session-export'
import { normalizeAdvisoryStage } from '@/lib/workflow'
import type { AdvisoryOutputPack } from '@/lib/types'

export default function BlueprintPanel() {
  const workspace = useStore((s) => s.workspace)
  const architectureArtifact = useStore((s) => s.architectureArtifact)
  const [copied, setCopied] = useState(false)
  const [activeTab, setActiveTab] = useState('brief')

  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])
  const advisoryCase = hasAdvisoryCaseContent(view.advisory_case) ? view.advisory_case : null
  const stage = normalizeAdvisoryStage(view.stage) ?? 'discovery'
  const outputPack = advisoryCase?.output_pack ?? null
  const fallbackMarkdown = useMemo(
    () => (view.blueprint_markdown?.trim() || buildFallbackBlueprint(view, architectureArtifact)).trim(),
    [view, architectureArtifact],
  )
  const technicalSections = useMemo(() => parseMarkdownSections(fallbackMarkdown), [fallbackMarkdown])
  const exportMarkdown = useMemo(
    () => buildExportMarkdown(outputPack, fallbackMarkdown),
    [outputPack, fallbackMarkdown],
  )
  const hasStructuredPack = Boolean(outputPack && hasOutputPackContent(outputPack))
  const markdownSections = useMemo(() => parseMarkdownSections(exportMarkdown), [exportMarkdown])
  const hasBlueprint =
    hasStructuredPack ||
    !!view.blueprint_markdown?.trim() ||
    (stage === 'blueprint' && exportMarkdown.length > 0)

  async function handleCopy() {
    if (!hasBlueprint) return
    try {
      await navigator.clipboard.writeText(exportMarkdown)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch (err) {
      console.error('Failed to copy blueprint', err)
    }
  }

  return (
    <div style={shellStyle}>
      <div style={headerStyle}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <span style={eyebrowStyle}>Output Pack</span>
          <p style={subtitleStyle}>
            This is the reusable advisory package for docs, reviews, and leadership conversations.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <ArtifactButton onClick={handleCopy} disabled={!hasBlueprint}>
            {copied ? 'Copied' : 'Copy'}
          </ArtifactButton>
        </div>
      </div>

      {!hasBlueprint ? (
        <div style={{ padding: '18px 16px' }}>
          <p style={{ fontSize: 12.5, color: 'var(--text-faint)', lineHeight: 1.65 }}>
            {stage === 'discovery'
              ? 'Questions and assumptions are being prioritized first. The blueprint will generate after the recommendation is coherent enough to defend.'
              : 'The engine will publish the reusable output pack here once the recommendation, decisions, risks, and rollout are coherent enough to defend.'}
          </p>
        </div>
      ) : hasStructuredPack && outputPack ? (
        <StructuredBlueprintView
          outputPack={outputPack}
          technicalSections={technicalSections}
          activeTab={activeTab}
          onChange={setActiveTab}
        />
      ) : (
        <MarkdownBlueprintView sections={markdownSections} activeTab={activeTab} onChange={setActiveTab} />
      )}
    </div>
  )
}

function StructuredBlueprintView({
  outputPack,
  technicalSections,
  activeTab,
  onChange,
}: {
  outputPack: AdvisoryOutputPack
  technicalSections: MarkdownSection[]
  activeTab: string
  onChange: (tab: string) => void
}) {
  const tabs = [
    outputPack.executive_summary || outputPack.recommendation_memo || outputPack.architecture_narrative
      ? { id: 'brief', label: 'Brief' }
      : null,
    outputPack.key_decisions.length || outputPack.open_questions.length
      ? { id: 'decisions', label: 'Decisions' }
      : null,
    outputPack.risks_and_mitigations.length
      ? { id: 'risks', label: 'Risks' }
      : null,
    outputPack.rollout_30_90_180.length
      ? { id: 'rollout', label: 'Rollout' }
      : null,
    outputPack.operating_principles.length || outputPack.control_checklist.length
      ? { id: 'controls', label: 'Controls' }
      : null,
    technicalSections.length
      ? { id: 'technical', label: 'Technical' }
      : null,
  ].filter((tab): tab is { id: string; label: string } => Boolean(tab))
  const selectedTab = tabs.find((tab) => tab.id === activeTab)?.id ?? tabs[0]?.id ?? 'brief'

  return (
    <>
      <TabBar tabs={tabs} activeTab={selectedTab} onChange={onChange} />
      <div style={contentShellStyle}>
        {selectedTab === 'brief' ? (
          <div style={contentStackStyle}>
            {outputPack.executive_summary ? <PackSection title="Executive Summary" body={outputPack.executive_summary} /> : null}
            {outputPack.recommendation_memo ? <PackSection title="Recommendation Memo" body={outputPack.recommendation_memo} /> : null}
            {outputPack.architecture_narrative ? <PackSection title="Architecture Narrative" body={outputPack.architecture_narrative} /> : null}
          </div>
        ) : null}

        {selectedTab === 'decisions' ? (
          <div style={twoColumnGridStyle}>
            {outputPack.key_decisions.length ? (
              <section style={sectionStyle}>
                <span style={sectionTitleStyle}>Key Decisions</span>
                <div style={numberedCardListStyle}>
                  {outputPack.key_decisions.map((item, index) => (
                    <div key={item} style={numberedCardStyle}>
                      <span style={numberBadgeStyle}>{index + 1}</span>
                      <p style={itemBodyStyle}>{item}</p>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {outputPack.open_questions.length ? (
              <section style={sectionStyle}>
                <span style={sectionTitleStyle}>Open Questions</span>
                <div style={contentStackStyle}>
                  {outputPack.open_questions.map((item) => (
                    <div key={item} style={questionCardStyle}>
                      <p style={itemBodyStyle}>{item}</p>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}
          </div>
        ) : null}

        {selectedTab === 'risks' ? (
          <section style={sectionStyle}>
            <span style={sectionTitleStyle}>Risks And Mitigations</span>
            <div style={riskGridStyle}>
              {outputPack.risks_and_mitigations.map((item) => (
                <div key={`${item.risk}-${item.mitigation}`} style={riskItemStyle}>
                  <span style={riskBadgeStyle}>!</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <p style={itemTitleStyle}>{item.risk}</p>
                    {item.mitigation ? <p style={itemBodyStyle}>{item.mitigation}</p> : null}
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {selectedTab === 'rollout' ? (
          <section style={sectionStyle}>
            <span style={sectionTitleStyle}>30 / 90 / 180 Day Rollout</span>
            <div style={rolloutGridStyle}>
              {outputPack.rollout_30_90_180.map((phase) => (
                <div key={`${phase.horizon}-${phase.outcome}`} style={phaseCardStyle}>
                  <span style={phaseLabelStyle}>{phase.horizon}</span>
                  <p style={itemBodyStyle}>{phase.outcome}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {selectedTab === 'controls' ? (
          <div style={twoColumnGridStyle}>
            {outputPack.operating_principles.length ? (
              <PackListSection title="Operating Principles" items={outputPack.operating_principles} />
            ) : null}
            {outputPack.control_checklist.length ? (
              <PackListSection title="Control Checklist" items={outputPack.control_checklist} />
            ) : null}
          </div>
        ) : null}

        {selectedTab === 'technical' ? (
          <div style={contentStackStyle}>
            {technicalSections.map((section) => (
              <section key={section.id} style={sectionStyle}>
                <span style={sectionTitleStyle}>{section.title}</span>
                <div
                  className="prose"
                  style={proseStyle}
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(section.body) }}
                />
              </section>
            ))}
          </div>
        ) : null}
      </div>
    </>
  )
}

function MarkdownBlueprintView({
  sections,
  activeTab,
  onChange,
}: {
  sections: MarkdownSection[]
  activeTab: string
  onChange: (tab: string) => void
}) {
  const tabs = sections.map((section) => ({ id: section.id, label: section.title }))
  const selectedTab = tabs.find((tab) => tab.id === activeTab)?.id ?? tabs[0]?.id ?? 'blueprint'
  const activeSection = sections.find((section) => section.id === selectedTab) ?? sections[0] ?? null

  if (!activeSection) {
    return null
  }

  return (
    <>
      {tabs.length > 1 ? <TabBar tabs={tabs} activeTab={selectedTab} onChange={onChange} /> : null}
      <div style={contentShellStyle}>
        <section style={sectionStyle}>
          <span style={sectionTitleStyle}>{activeSection.title}</span>
          <div
            className="prose"
            style={proseStyle}
            dangerouslySetInnerHTML={{ __html: renderMarkdown(activeSection.body) }}
          />
        </section>
      </div>
    </>
  )
}

function TabBar({
  tabs,
  activeTab,
  onChange,
}: {
  tabs: { id: string; label: string }[]
  activeTab: string
  onChange: (tab: string) => void
}) {
  return (
    <div style={tabBarShellStyle}>
      <div style={tabBarStyle}>
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              style={{
                ...tabStyle,
                ...(isActive ? activeTabStyle : null),
              }}
            >
              {tab.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function PackSection({ title, body }: { title: string; body: string }) {
  return (
    <section style={sectionStyle}>
      <span style={sectionTitleStyle}>{title}</span>
      <div
        className="prose"
        style={proseStyle}
        dangerouslySetInnerHTML={{ __html: renderMarkdown(body) }}
      />
    </section>
  )
}

function PackListSection({
  title,
  items,
  ordered = false,
}: {
  title: string
  items: string[]
  ordered?: boolean
}) {
  const ListTag = ordered ? 'ol' : 'ul'
  return (
    <section style={sectionStyle}>
      <span style={sectionTitleStyle}>{title}</span>
      <ListTag style={listStyle}>
        {items.map((item) => <li key={item}>{item}</li>)}
      </ListTag>
    </section>
  )
}

type MarkdownSection = {
  id: string
  title: string
  body: string
}

function parseMarkdownSections(markdown: string): MarkdownSection[] {
  const normalized = markdown.trim()
  if (!normalized) return []

  const matches = Array.from(normalized.matchAll(/^##\s+(.+)$/gm))
  if (matches.length === 0) {
    return [{ id: 'blueprint', title: 'Blueprint', body: normalized }]
  }

  const sections: MarkdownSection[] = []
  const firstMatch = matches[0]
  if ((firstMatch.index ?? 0) > 0) {
    const intro = normalized.slice(0, firstMatch.index).trim()
    if (intro) {
      sections.push({ id: 'overview', title: 'Overview', body: intro })
    }
  }

  matches.forEach((match, index) => {
    const title = match[1].trim()
    const start = (match.index ?? 0) + match[0].length
    const end = matches[index + 1]?.index ?? normalized.length
    const body = normalized.slice(start, end).trim()
    if (!body) return
    sections.push({
      id: createSectionId(title, index),
      title,
      body,
    })
  })

  return sections
}

function createSectionId(title: string, index: number) {
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return slug || `section-${index + 1}`
}

function ArtifactButton({
  children,
  disabled,
  onClick,
}: {
  children: React.ReactNode
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: '7px 10px',
        borderRadius: 8,
        border: '1px solid var(--border)',
        background: disabled ? 'var(--bg-hover)' : 'var(--bg-elevated)',
        color: disabled ? 'var(--text-faint)' : 'var(--text)',
        fontSize: 12,
        fontWeight: 500,
        cursor: disabled ? 'default' : 'pointer',
      }}
    >
      {children}
    </button>
  )
}

const shellStyle: React.CSSProperties = {
  flex: 1,
  height: '100%',
  minHeight: 0,
  overflowY: 'auto',
  background: 'var(--bg)',
  display: 'flex',
  flexDirection: 'column',
}

const headerStyle: React.CSSProperties = {
  padding: '14px 16px 12px',
  borderBottom: '1px solid var(--border)',
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: 12,
  position: 'sticky',
  top: 0,
  background: 'var(--bg)',
  zIndex: 2,
}

const eyebrowStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
}

const subtitleStyle: React.CSSProperties = {
  fontSize: 12,
  color: 'var(--text-faint)',
  lineHeight: 1.55,
}

const tabBarShellStyle: React.CSSProperties = {
  position: 'sticky',
  top: 66,
  zIndex: 1,
  padding: '10px 16px 0',
  background: 'linear-gradient(to bottom, var(--bg) 80%, rgba(244,239,232,0))',
}

const tabBarStyle: React.CSSProperties = {
  display: 'flex',
  gap: 8,
  overflowX: 'auto',
  paddingBottom: 10,
}

const tabStyle: React.CSSProperties = {
  borderRadius: 999,
  border: '1px solid var(--border)',
  background: 'var(--bg-elevated)',
  color: 'var(--text-muted)',
  fontSize: 12,
  fontWeight: 600,
  padding: '8px 12px',
  whiteSpace: 'nowrap',
  cursor: 'pointer',
  transition: 'background var(--transition), border-color var(--transition), color var(--transition)',
}

const activeTabStyle: React.CSSProperties = {
  background: 'var(--accent-dim)',
  borderColor: 'var(--accent-glow)',
  color: 'var(--accent-strong)',
}

const contentShellStyle: React.CSSProperties = {
  padding: '8px 18px 24px',
}

const contentStackStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
}

const twoColumnGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
  gap: 16,
  alignItems: 'start',
}

const sectionStyle: React.CSSProperties = {
  borderRadius: 14,
  border: '1px solid var(--border)',
  background: 'var(--bg-elevated)',
  padding: '14px 14px 12px',
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}

const sectionTitleStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
}

const proseStyle: React.CSSProperties = {
  fontSize: 13,
  color: 'var(--text)',
  lineHeight: 1.75,
  maxWidth: '78ch',
}

const listStyle: React.CSSProperties = {
  margin: 0,
  paddingLeft: 18,
  fontSize: 12.5,
  color: 'var(--text)',
  lineHeight: 1.65,
}

const numberedCardListStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
}

const numberedCardStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 10,
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid var(--border)',
  background: 'var(--bg)',
}

const numberBadgeStyle: React.CSSProperties = {
  minWidth: 22,
  height: 22,
  borderRadius: 999,
  background: 'var(--accent-dim)',
  color: 'var(--accent-strong)',
  fontSize: 11,
  fontWeight: 700,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
}

const riskGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
  gap: 10,
}

const riskItemStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 10,
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid rgba(245,158,11,0.22)',
  background: 'rgba(245,158,11,0.05)',
}

const questionCardStyle: React.CSSProperties = {
  borderRadius: 10,
  border: '1px solid rgba(15,109,119,0.18)',
  background: 'rgba(15,109,119,0.05)',
  padding: '10px 12px',
}

const riskBadgeStyle: React.CSSProperties = {
  width: 18,
  height: 18,
  borderRadius: 6,
  background: 'rgba(245,158,11,0.14)',
  color: 'var(--amber)',
  fontSize: 11,
  fontWeight: 700,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
}

const rolloutGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
  gap: 10,
}

const phaseCardStyle: React.CSSProperties = {
  borderRadius: 10,
  border: '1px solid var(--border)',
  background: 'var(--bg)',
  padding: '10px 12px',
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
}

const phaseLabelStyle: React.CSSProperties = {
  fontSize: 10.5,
  fontWeight: 700,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
}

const itemTitleStyle: React.CSSProperties = {
  fontSize: 12.5,
  fontWeight: 600,
  color: 'var(--text)',
}

const itemBodyStyle: React.CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.6,
  color: 'var(--text)',
}
