'use client'

import OpenQuestionsPanel from './OpenQuestionsPanel'
import RecommendationPanel from './RecommendationPanel'
import DecisionLogPanel from './DecisionLogPanel'
import RiskRegisterPanel from './RiskRegisterPanel'
import ImplementationPlanPanel from './ImplementationPlanPanel'

export default function WorkspacePanelStack() {
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
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
        borderTop: '1px solid var(--border)',
      }}>
        <div style={{ borderRight: '1px solid var(--border)' }}>
          <DecisionLogPanel />
        </div>
        <RiskRegisterPanel />
      </div>
      <div style={{ borderTop: '1px solid var(--border)' }}>
        <ImplementationPlanPanel />
      </div>
    </div>
  )
}
