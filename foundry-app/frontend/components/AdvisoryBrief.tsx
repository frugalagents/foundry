'use client'

import { useEffect, useMemo, useState } from 'react'
import { useStore } from '@/store'
import { hasAdvisoryCaseContent } from '@/lib/advisory-case'
import { normalizeWorkspace } from '@/lib/message-analysis'
import { normalizeAdvisoryStage } from '@/lib/workflow'

type MetricTone = 'neutral' | 'warning' | 'success'
type BriefTab = 'overview' | 'scenarios' | 'maturity'

export default function AdvisoryBrief() {
  const workspace = useStore((s) => s.workspace)
  const conversations = useStore((s) => s.conversations)
  const activeSessionId = useStore((s) => s.activeSessionId)
  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])
  const advisoryCase = hasAdvisoryCaseContent(view.advisory_case) ? view.advisory_case : null
  const stage = normalizeAdvisoryStage(view.stage) ?? 'discovery'
  const sessionTitle = conversations.find((row) => row.session.session_id === activeSessionId)?.session.title
    ?? 'Current engagement'
  const outputPack = advisoryCase?.output_pack
  const readout = advisoryCase?.readout
  const alternatives = advisoryCase?.alternatives ?? []
  const maturity = advisoryCase?.maturity ?? []
  const delta = advisoryCase?.delta
  const nextBestQuestion = advisoryCase?.next_best_question
  const recommendationSummary =
    advisoryCase?.recommendation.summary ||
    readout?.current_recommendation ||
    outputPack?.executive_summary ||
    view.recommendation
  const fallbackDecisions = view.decisions.slice(0, 5)
  const fallbackRisks = view.risks.slice(0, 5)
  const fallbackQuestions = view.open_questions.slice(0, 5)
  const outputPackDecisionFallback = outputPack?.key_decisions.slice(0, 5) ?? []
  const outputPackRiskFallback = outputPack?.risks_and_mitigations.slice(0, 5).map((item) => item.risk) ?? []
  const outputPackQuestionFallback = outputPack?.open_questions.slice(0, 5) ?? []
  const importantDecisions = readout?.important_decisions?.length
    ? readout.important_decisions
    : advisoryCase?.decisions.length
      ? advisoryCase.decisions.slice(0, 5).map((item) => item.statement || item.recommendation).filter(Boolean)
      : outputPackDecisionFallback.length
        ? outputPackDecisionFallback
        : fallbackDecisions
  const biggestRisks = readout?.biggest_risks?.length
    ? readout.biggest_risks
    : advisoryCase?.risks.length
      ? advisoryCase.risks.slice(0, 5).map((item) => item.risk)
      : outputPackRiskFallback.length
        ? outputPackRiskFallback
        : fallbackRisks
  const openQuestions = readout?.open_questions?.length
    ? readout.open_questions
    : outputPackQuestionFallback.length
      ? outputPackQuestionFallback
      : fallbackQuestions
  const keyFacts = view.facts.slice(0, 4)
  const keySignals: Array<{ label: string; value: string; tone: MetricTone }> = [
    {
      label: 'Confidence',
      value: advisoryCase?.recommendation.confidence ? `${advisoryCase.recommendation.confidence} confidence` : 'Awaiting engine signal',
      tone: advisoryCase?.recommendation.confidence === 'high'
        ? 'success'
        : advisoryCase?.recommendation.confidence === 'medium'
          ? 'warning'
          : 'neutral',
    },
    {
      label: 'Decisions',
      value: importantDecisions.length ? String(importantDecisions.length) : '0',
      tone: importantDecisions.length ? 'success' : 'neutral',
    },
    {
      label: 'Risks',
      value: biggestRisks.length ? String(biggestRisks.length) : '0',
      tone: biggestRisks.length ? 'warning' : 'neutral',
    },
    {
      label: 'Open Questions',
      value: openQuestions.length ? String(openQuestions.length) : '0',
      tone: openQuestions.length ? 'warning' : 'neutral',
    },
  ]

  const tabs = useMemo<Array<{ id: BriefTab; label: string; badge?: string }>>(() => {
    const nextTabs: Array<{ id: BriefTab; label: string; badge?: string }> = [
      { id: 'overview', label: 'Overview' },
    ]

    if (alternatives.length > 0 || delta) {
      nextTabs.push({
        id: 'scenarios',
        label: 'Scenarios',
        badge: alternatives.length > 0 ? String(alternatives.length) : 'delta',
      })
    }

    if (maturity.length > 0) {
      nextTabs.push({ id: 'maturity', label: 'Maturity', badge: String(maturity.length) })
    }

    return nextTabs
  }, [alternatives.length, delta, maturity.length])

  const [activeTab, setActiveTab] = useState<BriefTab>('overview')

  useEffect(() => {
    if (!tabs.some((tab) => tab.id === activeTab)) {
      setActiveTab('overview')
    }
  }, [activeTab, tabs])

  return (
    <section style={shellStyle}>
      <div style={briefScrollerStyle}>
        <div style={headerStyle}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0, flex: 1 }}>
            <span style={eyebrowStyle}>Advisory Brief</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <h1 style={titleStyle}>{sessionTitle}</h1>
              <span style={stagePill(stage)}>{stage}</span>
            </div>
            <p style={introStyle}>
              {recommendationSummary || 'The engine will publish a structured recommendation here as soon as it has enough context to commit to a direction.'}
            </p>
          </div>
          {keyFacts.length > 0 ? (
            <div style={factWrapStyle}>
              {keyFacts.map((fact) => (
                <span key={fact} style={factPillStyle}>{fact}</span>
              ))}
            </div>
          ) : null}
        </div>

        <div style={tabBarStyle}>
          {tabs.map((tab) => (
            <BriefTabButton
              key={tab.id}
              active={activeTab === tab.id}
              badge={tab.badge}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </BriefTabButton>
          ))}
        </div>

        {activeTab === 'overview' ? (
          <div style={contentStackStyle}>
            <div style={signalGridStyle}>
              {keySignals.map((signal) => (
                <SignalCard key={signal.label} label={signal.label} value={signal.value} tone={signal.tone} />
              ))}
            </div>

            <section style={featureCardStyle}>
              <div style={cardHeaderStyle}>
                <span style={cardLabelStyle}>Primary Recommendation</span>
                {advisoryCase?.recommendation.confidence ? (
                  <span style={confidencePill(advisoryCase.recommendation.confidence)}>
                    {advisoryCase.recommendation.confidence} confidence
                  </span>
                ) : null}
              </div>
              <p style={primaryBodyStyle}>
                {recommendationSummary || 'No recommendation published yet.'}
              </p>

              <div style={insightGridStyle}>
                {advisoryCase?.recommendation.why_this ? (
                  <InsightBlock label="Why This" body={advisoryCase.recommendation.why_this} />
                ) : outputPack?.recommendation_memo ? (
                  <InsightBlock label="Why This" body={outputPack.recommendation_memo} />
                ) : null}
                {advisoryCase?.recommendation.why_not ? (
                  <InsightBlock label="Why This, Not That" body={advisoryCase.recommendation.why_not} />
                ) : null}
                {nextBestQuestion?.question ? (
                  <InsightBlock
                    label="Next Best Question"
                    body={nextBestQuestion.question}
                    tone="warning"
                  />
                ) : null}
              </div>

              {advisoryCase?.recommendation.confidence_reason ? (
                <DetailBlock label="Confidence Rationale" body={advisoryCase.recommendation.confidence_reason} />
              ) : null}
              {advisoryCase?.recommendation.change_triggers?.length ? (
                <TokenList
                  label="What Would Change This"
                  items={advisoryCase.recommendation.change_triggers}
                  tone="warning"
                />
              ) : null}
              {nextBestQuestion?.why_it_matters ? (
                <DetailBlock label="Why This Question Matters" body={nextBestQuestion.why_it_matters} />
              ) : null}
            </section>

            {delta ? (
              <section style={cardStyle}>
                <div style={cardHeaderStyle}>
                  <span style={cardLabelStyle}>Recommendation Delta</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {delta.summary ? <p style={compactBodyStyle}>{delta.summary}</p> : null}
                  {delta.recommendation_change ? <DetailBlock label="Change" body={delta.recommendation_change} /> : null}
                  {delta.cost_or_complexity_impact ? <DetailBlock label="Cost / Complexity" body={delta.cost_or_complexity_impact} /> : null}
                  {delta.changed_assumptions?.length ? <TokenList label="Changed Assumptions" items={delta.changed_assumptions} tone="neutral" /> : null}
                  {delta.new_risks?.length ? <TokenList label="New Risks" items={delta.new_risks} tone="warning" /> : null}
                  {delta.added_controls?.length ? <TokenList label="Added Controls" items={delta.added_controls} tone="success" /> : null}
                  {delta.removed_controls?.length ? <TokenList label="Removed Controls" items={delta.removed_controls} tone="neutral" /> : null}
                </div>
              </section>
            ) : null}

            <section style={snapshotCardStyle}>
              <div style={cardHeaderStyle}>
                <span style={cardLabelStyle}>Decision Snapshot</span>
              </div>
              <div style={snapshotGridStyle}>
                <MiniListCard label="Decisions" items={importantDecisions} />
                <MiniListCard label="Risks" items={biggestRisks} tone="warning" />
                <MiniListCard label="Open Questions" items={openQuestions} tone="warning" />
              </div>
            </section>
          </div>
        ) : null}

        {activeTab === 'scenarios' ? (
          <div style={contentStackStyle}>
            {alternatives.length > 0 ? (
              <section style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                  <span style={sectionTitleStyle}>Scenario Comparison</span>
                  <span style={sectionMetaStyle}>{alternatives.length} options</span>
                </div>
                <div style={comparisonGridStyle}>
                  {alternatives.map((option) => (
                    <article key={option.id} style={optionCardStyle(option.position)}>
                      <div style={cardHeaderStyle}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          <span style={optionPillStyle(option.position)}>{option.position || 'option'}</span>
                          <h3 style={optionTitleStyle}>{option.title}</h3>
                        </div>
                      </div>
                      {option.summary ? <p style={compactBodyStyle}>{option.summary}</p> : null}
                      <MiniList label="Benefits" items={option.benefits} />
                      <MiniList label="Risks" items={option.risks} />
                      {option.operational_burden ? <DetailBlock label="Operational Burden" body={option.operational_burden} /> : null}
                      {option.governance_implications ? <DetailBlock label="Governance" body={option.governance_implications} /> : null}
                      {option.best_fit_conditions?.length ? <TokenList label="Best Fit" items={option.best_fit_conditions} tone="neutral" /> : null}
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            {delta ? (
              <section style={cardStyle}>
                <div style={cardHeaderStyle}>
                  <span style={cardLabelStyle}>Latest Recommendation Shift</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {delta.summary ? <p style={compactBodyStyle}>{delta.summary}</p> : null}
                  {delta.recommendation_change ? <DetailBlock label="Change" body={delta.recommendation_change} /> : null}
                  {delta.cost_or_complexity_impact ? <DetailBlock label="Cost / Complexity" body={delta.cost_or_complexity_impact} /> : null}
                </div>
              </section>
            ) : null}

            {alternatives.length === 0 && !delta ? (
              <EmptyTabState body="The engine has not published scenario comparisons yet." />
            ) : null}
          </div>
        ) : null}

        {activeTab === 'maturity' ? (
          maturity.length > 0 ? (
            <div style={contentStackStyle}>
              <section style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                  <span style={sectionTitleStyle}>Maturity View</span>
                  <span style={sectionMetaStyle}>{maturity.length} domains</span>
                </div>
                <div style={maturityGridStyle}>
                  {maturity.map((domain) => (
                    <article key={domain.domain} style={cardStyle}>
                      <div style={cardHeaderStyle}>
                        <span style={cardLabelStyle}>{domain.domain}</span>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {domain.current_state ? <DetailBlock label="Current" body={domain.current_state} /> : null}
                        {domain.target_state ? <DetailBlock label="Target" body={domain.target_state} /> : null}
                        {domain.gap ? <DetailBlock label="Gap" body={domain.gap} /> : null}
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            </div>
          ) : (
            <EmptyTabState body="The engine has not published a maturity assessment yet." />
          )
        ) : null}
      </div>
    </section>
  )
}

function DetailBlock({ label, body }: { label: string; body: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={detailLabelStyle}>{label}</span>
      <p style={compactBodyStyle}>{body}</p>
    </div>
  )
}

function InsightBlock({
  label,
  body,
  tone = 'neutral',
}: {
  label: string
  body: string
  tone?: MetricTone
}) {
  return (
    <div style={insightBlockStyle(tone)}>
      <span style={detailLabelStyle}>{label}</span>
      <p style={compactBodyStyle}>{body}</p>
    </div>
  )
}

function TokenList({
  label,
  items,
  tone,
}: {
  label: string
  items: string[]
  tone: MetricTone
}) {
  if (items.length === 0) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <span style={detailLabelStyle}>{label}</span>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {items.map((item) => (
          <span key={item} style={tokenStyle(tone)}>{item}</span>
        ))}
      </div>
    </div>
  )
}

function MiniList({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <span style={detailLabelStyle}>{label}</span>
      <ul style={miniListStyle}>
        {items.slice(0, 5).map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  )
}

function MiniListCard({
  label,
  items,
  tone = 'neutral',
}: {
  label: string
  items: string[]
  tone?: MetricTone
}) {
  return (
    <article style={miniListCardStyle(tone)}>
      <MiniList label={label} items={items} />
      {items.length === 0 ? <p style={emptyMiniListStyle}>No signal published yet.</p> : null}
    </article>
  )
}

function SignalCard({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone: MetricTone
}) {
  return (
    <article style={signalCardStyle(tone)}>
      <span style={detailLabelStyle}>{label}</span>
      <strong style={signalValueStyle}>{value}</strong>
    </article>
  )
}

function BriefTabButton({
  active,
  badge,
  children,
  onClick,
}: {
  active: boolean
  badge?: string
  children: React.ReactNode
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 12px',
        borderRadius: 10,
        border: active ? '1px solid rgba(15,109,119,0.18)' : '1px solid transparent',
        background: active ? 'var(--bg)' : 'transparent',
        color: active ? 'var(--text)' : 'var(--text-muted)',
        fontSize: 12.5,
        fontWeight: active ? 700 : 600,
        cursor: 'pointer',
      }}
    >
      <span>{children}</span>
      {badge ? <span style={tabBadgeStyle}>{badge}</span> : null}
    </button>
  )
}

function EmptyTabState({ body }: { body: string }) {
  return (
    <section style={emptyStateStyle}>
      <span style={cardLabelStyle}>Pending</span>
      <p style={compactBodyStyle}>{body}</p>
    </section>
  )
}

const shellStyle: React.CSSProperties = {
  height: '100%',
  minHeight: 0,
  borderRadius: 24,
  border: '1px solid var(--border)',
  background: 'linear-gradient(180deg, rgba(255,253,249,0.96) 0%, rgba(247,241,232,0.92) 100%)',
  boxShadow: 'var(--shadow-lg)',
  padding: 18,
  overflow: 'hidden',
}

const briefScrollerStyle: React.CSSProperties = {
  height: '100%',
  minHeight: 0,
  overflowY: 'auto',
  paddingRight: 4,
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
}

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 14,
  flexWrap: 'wrap',
}

const eyebrowStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
}

const titleStyle: React.CSSProperties = {
  fontSize: 24,
  lineHeight: 1.08,
  letterSpacing: '-0.03em',
  color: 'var(--text)',
}

const introStyle: React.CSSProperties = {
  maxWidth: 860,
  fontSize: 13.5,
  lineHeight: 1.65,
  color: 'var(--text-2)',
}

const factWrapStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 8,
  flexWrap: 'wrap',
  justifyContent: 'flex-end',
}

function stagePill(stage: string): React.CSSProperties {
  const palette = stage === 'blueprint'
    ? { background: 'rgba(15,109,119,0.12)', border: 'rgba(15,109,119,0.22)', color: 'var(--accent-strong)' }
    : stage === 'solutioning'
      ? { background: 'rgba(183,121,31,0.12)', border: 'rgba(183,121,31,0.22)', color: 'var(--amber)' }
      : { background: 'rgba(124,112,98,0.1)', border: 'var(--border)', color: 'var(--text-muted)' }

  return {
    padding: '4px 9px',
    borderRadius: 999,
    border: `1px solid ${palette.border}`,
    background: palette.background,
    color: palette.color,
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.05em',
    textTransform: 'capitalize',
  }
}

const factPillStyle: React.CSSProperties = {
  borderRadius: 999,
  padding: '6px 10px',
  border: '1px solid var(--border)',
  background: 'rgba(15,109,119,0.07)',
  color: 'var(--accent-strong)',
  fontSize: 11.5,
  lineHeight: 1.2,
}

const tabBarStyle: React.CSSProperties = {
  display: 'flex',
  gap: 4,
  padding: 4,
  borderRadius: 12,
  background: 'rgba(255,253,249,0.82)',
  border: '1px solid var(--border)',
  width: 'fit-content',
  maxWidth: '100%',
  flexWrap: 'wrap',
}

const tabBadgeStyle: React.CSSProperties = {
  minWidth: 18,
  height: 18,
  padding: '0 6px',
  borderRadius: 999,
  background: 'rgba(15,109,119,0.08)',
  border: '1px solid rgba(15,109,119,0.16)',
  color: 'var(--accent-strong)',
  fontSize: 10,
  fontWeight: 700,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  textTransform: 'uppercase',
}

const contentScrollerStyle: React.CSSProperties = {
  minHeight: 0,
}

const contentStackStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}

const signalGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
  gap: 10,
}

const featureCardStyle: React.CSSProperties = {
  borderRadius: 20,
  border: '1px solid rgba(15,109,119,0.14)',
  background: 'rgba(255,253,249,0.96)',
  padding: '16px 16px 14px',
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}

const insightGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 10,
}

const snapshotGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
  gap: 10,
}

const twoColumnGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
  gap: 12,
}

const comparisonGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
  gap: 12,
}

const maturityGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 12,
}

const cardStyle: React.CSSProperties = {
  borderRadius: 18,
  border: '1px solid var(--border)',
  background: 'var(--bg-elevated)',
  padding: '14px 14px 12px',
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}

const snapshotCardStyle: React.CSSProperties = {
  ...cardStyle,
  background: 'rgba(255,253,249,0.88)',
}

const cardHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 8,
}

const cardLabelStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
}

const sectionTitleStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 700,
  color: 'var(--text)',
}

const sectionMetaStyle: React.CSSProperties = {
  fontSize: 11,
  color: 'var(--text-faint)',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
}

const primaryBodyStyle: React.CSSProperties = {
  fontSize: 14,
  lineHeight: 1.65,
  color: 'var(--text)',
}

const compactBodyStyle: React.CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.6,
  color: 'var(--text)',
}

const detailLabelStyle: React.CSSProperties = {
  fontSize: 10.5,
  fontWeight: 700,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
}

const miniListStyle: React.CSSProperties = {
  margin: 0,
  paddingLeft: 18,
  fontSize: 12.5,
  color: 'var(--text)',
  lineHeight: 1.55,
}

const miniListCardBaseStyle: React.CSSProperties = {
  borderRadius: 14,
  padding: '12px 12px 10px',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const emptyMiniListStyle: React.CSSProperties = {
  fontSize: 12,
  lineHeight: 1.5,
  color: 'var(--text-faint)',
}

const optionTitleStyle: React.CSSProperties = {
  fontSize: 15,
  fontWeight: 700,
  color: 'var(--text)',
}

const signalValueStyle: React.CSSProperties = {
  fontSize: 16,
  lineHeight: 1.25,
  color: 'var(--text)',
}

const emptyStateStyle: React.CSSProperties = {
  ...cardStyle,
  alignItems: 'flex-start',
  justifyContent: 'center',
  minHeight: 160,
}

function confidencePill(confidence: 'low' | 'medium' | 'high' | ''): React.CSSProperties {
  const palette = confidence === 'high'
    ? { background: 'rgba(15,159,110,0.12)', border: 'rgba(15,159,110,0.2)', color: 'var(--green)' }
    : confidence === 'medium'
      ? { background: 'rgba(183,121,31,0.12)', border: 'rgba(183,121,31,0.22)', color: 'var(--amber)' }
      : { background: 'rgba(185,28,28,0.08)', border: 'rgba(185,28,28,0.18)', color: 'var(--red)' }

  return {
    padding: '4px 9px',
    borderRadius: 999,
    border: `1px solid ${palette.border}`,
    background: palette.background,
    color: palette.color,
    fontSize: 11,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  }
}

function tokenStyle(tone: MetricTone): React.CSSProperties {
  const palette = tone === 'warning'
    ? { background: 'rgba(183,121,31,0.12)', border: 'rgba(183,121,31,0.22)', color: 'var(--amber)' }
    : tone === 'success'
      ? { background: 'rgba(15,159,110,0.12)', border: 'rgba(15,159,110,0.2)', color: 'var(--green)' }
      : { background: 'var(--bg)', border: 'var(--border)', color: 'var(--text-faint)' }

  return {
    borderRadius: 999,
    padding: '6px 10px',
    border: `1px solid ${palette.border}`,
    background: palette.background,
    color: palette.color,
    fontSize: 11.5,
    lineHeight: 1.3,
  }
}

function signalCardStyle(tone: MetricTone): React.CSSProperties {
  const palette = tone === 'warning'
    ? { background: 'rgba(255,250,239,0.96)', border: 'rgba(183,121,31,0.22)' }
    : tone === 'success'
      ? { background: 'rgba(244,250,249,0.96)', border: 'rgba(15,109,119,0.16)' }
      : { background: 'var(--bg-elevated)', border: 'var(--border)' }

  return {
    borderRadius: 16,
    border: `1px solid ${palette.border}`,
    background: palette.background,
    padding: '12px 13px',
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    justifyContent: 'space-between',
  }
}

function insightBlockStyle(tone: MetricTone): React.CSSProperties {
  const palette = tone === 'warning'
    ? { background: 'rgba(255,250,239,0.96)', border: 'rgba(183,121,31,0.24)' }
    : tone === 'success'
      ? { background: 'rgba(244,250,249,0.96)', border: 'rgba(15,109,119,0.18)' }
      : { background: 'rgba(244,239,232,0.52)', border: 'rgba(215,207,194,0.82)' }

  return {
    borderRadius: 14,
    border: `1px solid ${palette.border}`,
    background: palette.background,
    padding: '10px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  }
}

function miniListCardStyle(tone: MetricTone): React.CSSProperties {
  const palette = tone === 'warning'
    ? { background: 'rgba(255,250,239,0.96)', border: 'rgba(183,121,31,0.2)' }
    : tone === 'success'
      ? { background: 'rgba(244,250,249,0.96)', border: 'rgba(15,109,119,0.16)' }
      : { background: 'rgba(244,239,232,0.46)', border: 'rgba(215,207,194,0.82)' }

  return {
    ...miniListCardBaseStyle,
    background: palette.background,
    border: `1px solid ${palette.border}`,
  }
}

function optionCardStyle(position: 'recommended' | 'viable' | 'deferred' | ''): React.CSSProperties {
  return {
    ...cardStyle,
    border: position === 'recommended' ? '1px solid rgba(15,109,119,0.28)' : cardStyle.border,
    background: position === 'recommended' ? 'rgba(244,250,249,0.96)' : cardStyle.background,
  }
}

function optionPillStyle(position: 'recommended' | 'viable' | 'deferred' | ''): React.CSSProperties {
  const palette = position === 'recommended'
    ? { background: 'rgba(15,109,119,0.12)', border: 'rgba(15,109,119,0.22)', color: 'var(--accent-strong)' }
    : position === 'viable'
      ? { background: 'var(--bg)', border: 'var(--border)', color: 'var(--text-faint)' }
      : { background: 'rgba(183,121,31,0.12)', border: 'rgba(183,121,31,0.22)', color: 'var(--amber)' }

  return {
    width: 'fit-content',
    padding: '4px 8px',
    borderRadius: 999,
    border: `1px solid ${palette.border}`,
    background: palette.background,
    color: palette.color,
    fontSize: 10.5,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  }
}
