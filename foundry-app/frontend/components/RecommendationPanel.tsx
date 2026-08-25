'use client'

import { useMemo } from 'react'
import { useStore } from '@/store'
import { normalizeWorkspace } from '@/lib/message-analysis'
import type { AdvisoryAlternative, WorkspaceCandidateOption } from '@/lib/types'

export default function RecommendationPanel() {
  const workspace = useStore((s) => s.workspace)
  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])
  const recommendationState = view.recommendation_state
  const advisoryCase = view.advisory_case
  const architectureCase = view.architecture_case
  const primaryRecommendation = advisoryCase?.recommendation.summary
    || architectureCase?.current_recommendation
    || recommendationState?.primary_recommendation
    || view.recommendation
  const confidence = advisoryCase?.recommendation.confidence || recommendationState?.confidence || ''
  const confidenceReason = advisoryCase?.recommendation.confidence_reason || ''
  const whyThis = advisoryCase?.recommendation.why_this || architectureCase?.artifacts.recommendation_memo || ''
  const missingEvidence = recommendationState?.missing_evidence ?? architectureCase?.open_questions.map((item) => item.text) ?? []
  const factRows = view.facts.length > 0 ? view.facts : (architectureCase?.facts.map((item) => item.statement) ?? [])
  const hasWorkspace = Boolean(
    primaryRecommendation
    || factRows.length > 0
    || view.operating_model
    || missingEvidence.length > 0,
  )

  const alternatives = useMemo(() => {
    if (advisoryCase?.alternatives?.length) {
      return advisoryCase.alternatives
        .filter((item) => item.position !== 'recommended')
        .slice(0, 3)
        .map((item) => ({
          key: item.id,
          title: item.title,
          summary: item.summary,
          position: item.position,
        }))
    }

    const candidateOptions = recommendationState?.candidate_options ?? []
    return candidateOptions
      .filter((item) => item.position !== 'recommended')
      .slice(0, 3)
      .map((item) => ({
        key: item.path,
        title: item.title,
        summary: item.summary,
        position: item.position,
      }))
  }, [advisoryCase?.alternatives, recommendationState?.candidate_options])

  const confirmationItems = useMemo(() => {
    const fromQuestions = view.question_state
      ?.filter((item) => item.status === 'open')
      .map((item) => ({ text: item.text, why: item.why_it_matters }))
      ?? []
    if (fromQuestions.length > 0) return fromQuestions.slice(0, 3)
    return missingEvidence.slice(0, 3).map((text) => ({ text, why: '' }))
  }, [architectureCase?.open_questions, missingEvidence, view.question_state])

  const readinessCopy = describeRecommendationReadiness(view.artifact_status?.recommendation, view.artifact_status?.blocking_question_count ?? 0)
  const operatingModelLabel = formatOperatingModel(view.operating_model)

  return (
    <div style={{
      padding: '14px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span style={eyebrowStyle}>Recommendation</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {readinessCopy ? <span style={statusPillStyle(readinessCopy.tone)}>{readinessCopy.label}</span> : null}
          {view.stage ? <span style={stagePillStyle}>{view.stage}</span> : null}
        </div>
      </div>

      {!hasWorkspace ? (
        <p style={bodyStyle}>
          The advisor has not committed to a direction yet. Once the engine has enough signal, the recommendation and decision posture will appear here.
        </p>
      ) : (
        <>
          {primaryRecommendation ? (
            <section style={sectionStyle}>
              <div style={sectionHeaderStyle}>
                <div style={sectionLabelStyle}>Recommended Direction</div>
                {confidence ? <span style={confidencePillStyle(confidence)}>{formatConfidence(confidence)}</span> : null}
              </div>
              <p style={primaryBodyStyle}>{primaryRecommendation}</p>
              {confidenceReason ? <p style={supportingBodyStyle}>{confidenceReason}</p> : null}
            </section>
          ) : null}

          {whyThis ? (
            <section style={sectionStyle}>
              <div style={sectionLabelStyle}>Why This Fits</div>
              <p style={bodyStyle}>{whyThis}</p>
            </section>
          ) : null}

          {operatingModelLabel ? (
            <section style={sectionStyle}>
              <div style={sectionLabelStyle}>Target Rollout Pattern</div>
              <p style={bodyStyle}>{operatingModelLabel}</p>
            </section>
          ) : null}

          {alternatives.length > 0 ? (
            <section style={sectionStyle}>
              <div style={sectionLabelStyle}>Also Considered</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {alternatives.map((option) => (
                  <article key={option.key} style={alternativeCardStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                      <strong style={alternativeTitleStyle}>{option.title}</strong>
                      {option.position ? <span style={optionPillStyle}>{formatOptionPosition(option.position)}</span> : null}
                    </div>
                    {option.summary ? <p style={supportingBodyStyle}>{option.summary}</p> : null}
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {confirmationItems.length > 0 ? (
            <section style={sectionStyle}>
              <div style={sectionLabelStyle}>Still To Confirm</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {confirmationItems.map((item) => (
                  <article key={item.text} style={confirmationCardStyle}>
                    <p style={questionTextStyle}>{item.text}</p>
                    {item.why ? <p style={supportingBodyStyle}>{item.why}</p> : null}
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {factRows.length > 0 ? (
            <section style={sectionStyle}>
              <div style={sectionLabelStyle}>What The Advisor Is Using</div>
              <ul style={listStyle}>
                {factRows.slice(0, 4).map((fact) => <li key={fact}>{fact}</li>)}
              </ul>
            </section>
          ) : null}
        </>
      )}
    </div>
  )
}

const eyebrowStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
}

const sectionStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const sectionHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 10,
  flexWrap: 'wrap',
}

const sectionLabelStyle: React.CSSProperties = {
  fontSize: 10.5,
  fontWeight: 700,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
  color: 'var(--text-faint)',
}

const bodyStyle: React.CSSProperties = {
  fontSize: 12.5,
  color: 'var(--text)',
  lineHeight: 1.6,
}

const primaryBodyStyle: React.CSSProperties = {
  fontSize: 13,
  color: 'var(--text)',
  lineHeight: 1.65,
}

const supportingBodyStyle: React.CSSProperties = {
  fontSize: 12,
  color: 'var(--text-muted)',
  lineHeight: 1.55,
}

const listStyle: React.CSSProperties = {
  margin: 0,
  paddingLeft: 18,
  fontSize: 12.5,
  color: 'var(--text)',
  lineHeight: 1.55,
}

const stagePillStyle: React.CSSProperties = {
  padding: '3px 8px',
  borderRadius: 999,
  border: '1px solid var(--border)',
  background: 'var(--bg-elevated)',
  fontSize: 10.5,
  color: 'var(--text-faint)',
  textTransform: 'capitalize',
}

const alternativeCardStyle: React.CSSProperties = {
  borderRadius: 10,
  border: '1px solid var(--border)',
  background: 'var(--bg-elevated)',
  padding: '10px 12px',
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
}

const confirmationCardStyle: React.CSSProperties = {
  borderRadius: 10,
  border: '1px solid rgba(245,158,11,0.28)',
  background: 'rgba(245,158,11,0.06)',
  padding: '10px 12px',
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
}

const alternativeTitleStyle: React.CSSProperties = {
  fontSize: 12.5,
  color: 'var(--text)',
}

const optionPillStyle: React.CSSProperties = {
  padding: '3px 8px',
  borderRadius: 999,
  background: 'rgba(15,109,119,0.08)',
  border: '1px solid rgba(15,109,119,0.18)',
  color: 'var(--accent-strong)',
  fontSize: 10.5,
  textTransform: 'capitalize',
}

const questionTextStyle: React.CSSProperties = {
  fontSize: 12.5,
  color: 'var(--text)',
  lineHeight: 1.55,
}

function confidencePillStyle(confidence: string): React.CSSProperties {
  const tone = confidence === 'high'
    ? { bg: 'rgba(24,112,68,0.12)', border: 'rgba(24,112,68,0.2)', color: 'var(--success)' }
    : confidence === 'medium'
      ? { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.24)', color: 'var(--amber)' }
      : { bg: 'var(--bg-elevated)', border: 'var(--border)', color: 'var(--text-faint)' }

  return {
    padding: '3px 8px',
    borderRadius: 999,
    background: tone.bg,
    border: `1px solid ${tone.border}`,
    color: tone.color,
    fontSize: 10.5,
    textTransform: 'capitalize',
  }
}

function statusPillStyle(tone: 'neutral' | 'warning' | 'success'): React.CSSProperties {
  const palette = tone === 'success'
    ? { bg: 'rgba(24,112,68,0.12)', border: 'rgba(24,112,68,0.2)', color: 'var(--success)' }
    : tone === 'warning'
      ? { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.24)', color: 'var(--amber)' }
      : { bg: 'var(--bg-elevated)', border: 'var(--border)', color: 'var(--text-faint)' }

  return {
    padding: '3px 8px',
    borderRadius: 999,
    background: palette.bg,
    border: `1px solid ${palette.border}`,
    color: palette.color,
    fontSize: 10.5,
  }
}

function describeRecommendationReadiness(status: string | undefined, blockingQuestions: number) {
  switch (status) {
    case 'ready':
      return { label: 'Direction is ready to review', tone: 'success' as const }
    case 'stale':
      return { label: 'Direction is being refreshed', tone: 'warning' as const }
    case 'draft':
      return { label: blockingQuestions > 0 ? 'Direction is still being shaped' : 'Working direction available', tone: 'warning' as const }
    default:
      return blockingQuestions > 0 ? { label: 'Waiting on a few key answers', tone: 'neutral' as const } : null
  }
}

function formatOperatingModel(value?: string) {
  switch (value) {
    case 'single_standard':
      return 'One standard tool for most teams.'
    case 'multi_harness_governed':
      return 'Several approved tools under one shared governance model.'
    case 'default_plus_exceptions':
      return 'One default tool, with formal exception lanes for specific teams.'
    case 'undecided':
      return 'The rollout pattern is still being decided.'
    default:
      return ''
  }
}

function formatConfidence(value: string) {
  switch (value) {
    case 'high':
      return 'High confidence'
    case 'medium':
      return 'Medium confidence'
    case 'low':
      return 'Low confidence'
    default:
      return value
  }
}

function formatOptionPosition(value: AdvisoryAlternative['position'] | WorkspaceCandidateOption['position']) {
  switch (value) {
    case 'viable':
      return 'viable option'
    case 'deferred':
      return 'future option'
    case 'recommended':
      return 'recommended'
    default:
      return 'option'
  }
}
