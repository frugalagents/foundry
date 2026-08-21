'use client'

import { useMemo } from 'react'
import { useStore } from '@/store'
import { normalizeWorkspace } from '@/lib/message-analysis'
import OpenQuestionsPanel from './OpenQuestionsPanel'
import RecommendationPanel from './RecommendationPanel'
import DecisionLogPanel from './DecisionLogPanel'
import RiskRegisterPanel from './RiskRegisterPanel'
import ImplementationPlanPanel from './ImplementationPlanPanel'

export default function WorkspacePanelStack() {
  const workspace = useStore((s) => s.workspace)
  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])

  return (
    <div style={{
      background: 'var(--bg)',
      display: 'flex',
      flexDirection: 'column',
      overflowY: 'auto',
      flex: 1,
      minHeight: 0,
    }}>
      <OpenQuestionsPanel />
      <div style={{ height: 1, background: 'var(--border)' }} />
      <RecommendationPanel />
      {view.decisions.length > 0 && (
        <>
          <div style={{ height: 1, background: 'var(--border)' }} />
          <DecisionLogPanel />
        </>
      )}
      {view.risks.length > 0 && (
        <>
          <div style={{ height: 1, background: 'var(--border)' }} />
          <RiskRegisterPanel />
        </>
      )}
      {view.implementation_plan.length > 0 && (
        <>
          <div style={{ height: 1, background: 'var(--border)' }} />
          <ImplementationPlanPanel />
        </>
      )}
    </div>
  )
}
