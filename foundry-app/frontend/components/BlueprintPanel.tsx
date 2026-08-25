'use client'

import { useMemo, useState } from 'react'
import { useStore } from '@/store'
import { normalizeWorkspace } from '@/lib/message-analysis'
import { renderMarkdown } from '@/lib/render-markdown'
import { buildFallbackBlueprint, buildStructuredBlueprintHtml, buildStructuredBlueprintSections } from '@/lib/session-export'
import { normalizeAdvisoryStage } from '@/lib/workflow'

export default function BlueprintPanel() {
  const workspace = useStore((s) => s.workspace)
  const architectureArtifact = useStore((s) => s.architectureArtifact)
  const [copied, setCopied] = useState(false)
  const [activeTab, setActiveTab] = useState('brief')

  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])
  const stage = normalizeAdvisoryStage(view.stage) ?? 'discovery'
  const rawBlueprint = useMemo(
    () => (view.architecture_case?.artifacts.blueprint_markdown?.trim() || view.blueprint_markdown?.trim() || '').trim(),
    [view.architecture_case?.artifacts.blueprint_markdown, view.blueprint_markdown],
  )
  const fallbackMarkdown = useMemo(
    () => (rawBlueprint || buildFallbackBlueprint(view, architectureArtifact)).trim(),
    [rawBlueprint, view, architectureArtifact],
  )
  const structuredBlueprintHtml = useMemo(
    () => buildStructuredBlueprintHtml(view, architectureArtifact).trim(),
    [view, architectureArtifact],
  )
  const structuredSections = useMemo(
    () => buildStructuredBlueprintSections(view, architectureArtifact),
    [view, architectureArtifact],
  )
  const useStructuredHtml = useMemo(
    () => shouldUseStructuredBlueprintHtml(rawBlueprint, fallbackMarkdown, structuredBlueprintHtml),
    [rawBlueprint, fallbackMarkdown, structuredBlueprintHtml],
  )
  const technicalSections = useMemo(
    () => (useStructuredHtml ? [] : parseMarkdownSections(fallbackMarkdown)),
    [fallbackMarkdown, useStructuredHtml],
  )
  const hasBlueprint =
    rawBlueprint.length > 0 ||
    structuredBlueprintHtml.length > 0 ||
    (stage === 'blueprint' && fallbackMarkdown.length > 0)
  const copySource = fallbackMarkdown || rawBlueprint

  async function handleCopy() {
    if (!hasBlueprint) return
    try {
      await navigator.clipboard.writeText(copySource)
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
          <span style={eyebrowStyle}>Blueprint</span>
          <p style={subtitleStyle}>
            This is the detailed technical blueprint for build teams, review threads, and architecture documentation.
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
              : 'The engine will publish the detailed technical blueprint here once the recommendation is coherent enough to implement.'}
          </p>
        </div>
      ) : useStructuredHtml ? (
        <StructuredBlueprintView
          html={structuredBlueprintHtml}
          sections={structuredSections}
          activeTab={activeTab}
          onChange={setActiveTab}
        />
      ) : (
        <MarkdownBlueprintView sections={technicalSections} activeTab={activeTab} onChange={setActiveTab} />
      )}
    </div>
  )
}

function StructuredBlueprintView({
  html,
  sections,
  activeTab,
  onChange,
}: {
  html: string
  sections: Array<{ id: string; title: string; html: string }>
  activeTab: string
  onChange: (tab: string) => void
}) {
  const tabs = sections.map((section) => ({ id: section.id, label: section.title }))
  const selectedTab = tabs.find((tab) => tab.id === activeTab)?.id ?? tabs[0]?.id ?? 'overview'
  const activeSection = sections.find((section) => section.id === selectedTab) ?? sections[0] ?? null

  if (!activeSection) {
    return (
      <div style={contentShellStyle}>
        <section style={sectionStyle}>
          <span style={sectionTitleStyle}>Structured Blueprint</span>
          <div
            className="prose"
            style={proseStyle}
            dangerouslySetInnerHTML={{ __html: html }}
          />
        </section>
      </div>
    )
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
            dangerouslySetInnerHTML={{ __html: htmlForStructuredSection(activeSection.id, html, activeSection.html) }}
          />
        </section>
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
            dangerouslySetInnerHTML={{ __html: renderArtifactBody(activeSection.body) }}
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
        dangerouslySetInnerHTML={{ __html: renderArtifactBody(body) }}
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

  const h2Matches = Array.from(normalized.matchAll(/^##\s+(.+)$/gm))
  if (h2Matches.length > 1) {
    const sections: MarkdownSection[] = []
    const firstMatch = h2Matches[0]
    if ((firstMatch.index ?? 0) > 0) {
      const intro = normalized.slice(0, firstMatch.index).trim()
      if (intro) {
        sections.push({ id: 'overview', title: 'Overview', body: intro })
      }
    }

    h2Matches.forEach((match, index) => {
      const title = match[1].trim()
      const start = (match.index ?? 0) + match[0].length
      const end = h2Matches[index + 1]?.index ?? normalized.length
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

  const h3Matches = Array.from(normalized.matchAll(/^###\s+(.+)$/gm))
  if (h3Matches.length > 0) {
    const sections: MarkdownSection[] = []
    const leadingBoundary = h2Matches[0]?.index ?? 0
    const firstH3 = h3Matches[0]
    const introStart = h2Matches.length === 1
      ? (h2Matches[0].index ?? 0) + h2Matches[0][0].length
      : 0
    const introTitle = h2Matches.length === 1 ? h2Matches[0][1].trim() : 'Overview'
    const introEnd = firstH3.index ?? normalized.length
    const intro = normalized.slice(introStart, introEnd).trim()
    if (intro && introEnd >= leadingBoundary) {
      sections.push({ id: 'overview', title: introTitle, body: intro })
    }

    h3Matches.forEach((match, index) => {
      const title = match[1].trim()
      const start = (match.index ?? 0) + match[0].length
      const end = h3Matches[index + 1]?.index ?? normalized.length
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

  if (h2Matches.length === 0) {
    return [{ id: 'blueprint', title: 'Blueprint', body: normalized }]
  }

  const outerTitle = h2Matches[0][1].trim() || 'Blueprint'
  const outerBody = normalized.slice(((h2Matches[0].index ?? 0) + h2Matches[0][0].length)).trim()
  return [{ id: createSectionId(outerTitle, 0), title: outerTitle, body: outerBody || normalized }]
}

function createSectionId(title: string, index: number) {
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return slug || `section-${index + 1}`
}

function renderArtifactBody(body: string) {
  return looksLikeHtml(body) ? body : renderMarkdown(body)
}

function looksLikeHtml(body: string) {
  return /^\s*<(article|aside|div|dl|footer|h1|h2|h3|header|li|main|nav|ol|p|section|table|tbody|td|th|thead|tr|ul)\b/i.test(body)
}

function shouldUseStructuredBlueprintHtml(rawBlueprint: string, fallbackMarkdown: string, html: string) {
  if (!html) return false
  if (!rawBlueprint) return true
  if (looksLikeHtml(rawBlueprint)) return false
  const hasStructuredHeadings = /^##\s+.+$/m.test(fallbackMarkdown) || /^###\s+.+$/m.test(fallbackMarkdown)
  if (!hasStructuredHeadings) return true
  const paragraphCount = fallbackMarkdown.split(/\n\s*\n/).filter((item) => item.trim()).length
  return paragraphCount <= 2 && fallbackMarkdown.length > 240
}

function htmlForStructuredSection(sectionId: string, html: string, sectionHtml: string) {
  const marker = `data-blueprint-section="${sectionId}"`
  return html.includes(marker) ? sectionHtml : html
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
