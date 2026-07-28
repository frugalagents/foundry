'use client';
import { useEffect, useCallback, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAgentStream } from '@/hooks/useAgentStream';
import { getSession, exportBlueprint, updateIntakeAnswers } from '@/lib/api';
import { ChatPanel } from '@/components/session/ChatPanel';
import { StepIndicator } from '@/components/session/StepIndicator';
import { PanelRouter } from '@/components/panels/PanelRouter';
import { DrilldownDrawer } from '@/components/panels/DrilldownDrawer';
import type { IntakeAnswers } from '@/lib/types';

const STEP_LABELS: Record<number, string> = {
  1: 'Intake',
  2: 'Patterns',
  3: 'Components',
  4: 'Innovations',
  5: 'Compliance',
  6: 'Services',
  7: 'Risks',
  8: 'Roadmap',
  9: 'Costs',
  10: 'Blueprint',
};

// Scored spine + archetype filter (discovery-methodology §3). Must match the
// agent's _INTAKE_REQUIRED. Secondary/current-state fields are optional.
const REQUIRED_IDS: (keyof IntakeAnswers)[] = [
  'archetype', 'autonomy_model', 'lob_count', 'team_expertise',
  'cloud_posture', 'data_gravity', 'cost_sensitivity', 'compliance_regime',
];

// A required field counts as answered when present and (for multi-selects) non-empty.
const isAnswered = (answers: Partial<IntakeAnswers>, id: keyof IntakeAnswers): boolean => {
  const v = answers[id];
  if (v === undefined || v === null) return false;
  if (Array.isArray(v)) return v.length > 0;
  return true;
};
const missingRequired = (answers: Partial<IntakeAnswers>): string[] =>
  REQUIRED_IDS.filter((id) => !isAnswered(answers, id));

export default function SessionPage() {
  const { id: paramCustomerId, sid: paramSessionId } =
    useParams<{ id: string; sid: string }>();
  const store = useAppStore();

  // Static export bakes in placeholder '_' — read real IDs from URL on mount
  const [customerId, setCustomerId] = useState(paramCustomerId ?? '');
  const [sessionId,  setSessionId]  = useState(paramSessionId  ?? '');

  useEffect(() => {
    const parts  = window.location.pathname.split('/').filter(Boolean);
    const custIdx = parts.indexOf('customers');
    const sessIdx = parts.indexOf('sessions');
    const realCid = custIdx >= 0 ? parts[custIdx + 1] : '';
    const realSid = sessIdx >= 0 ? parts[sessIdx + 1] : '';
    setCustomerId(realCid && realCid !== '_' ? realCid : paramCustomerId ?? '');
    setSessionId (realSid && realSid !== '_' ? realSid : paramSessionId  ?? '');
  }, [paramCustomerId, paramSessionId]);

  // Which panel is visible in the right pane (user can navigate independently of current step)
  const [selectedStep, setSelectedStep] = useState(1);
  const userSelectedRef = useRef(false);

  // Auto-advance to new panel when pipeline progresses, unless user manually picked a tab
  useEffect(() => {
    if (!userSelectedRef.current) {
      setSelectedStep(store.currentStep);
    }
  }, [store.currentStep]);

  // When new panel data lands for the current step, snap back to following the pipeline
  useEffect(() => {
    if (store.panelData[store.currentStep]) {
      userSelectedRef.current = false;
      setSelectedStep(store.currentStep);
    }
  }, [store.panelData, store.currentStep]);

  // Intake answers collected locally before first submit
  const [pendingAnswers, setPendingAnswers] = useState<Partial<IntakeAnswers>>({});
  const [industry,       setIndustry]       = useState('');
  const [painPoints,     setPainPoints]     = useState<string[]>([]);

  const { sendMessage, sendDrilldown, sendWhatIf, stopStream } = useAgentStream(customerId, sessionId);

  // Restore session state on mount
  useEffect(() => {
    if (!customerId || customerId === '_' || !sessionId || sessionId === '_') return;
    getSession(customerId, sessionId)
      .then((session) => {
        store.setCurrentStep(
          session.current_step && session.current_step > 0 ? session.current_step : 1,
        );
        const saved = session.intake_answers;
        if (saved && Object.keys(saved).length > 0) {
          setPendingAnswers(saved);
          if (saved.industry)    setIndustry(saved.industry as string);
          if (saved.pain_points) setPainPoints(saved.pain_points as string[]);
          const missing = missingRequired(saved);
          store.setPanelData(1, {
            answers: saved, missing, complete: missing.length === 0, streaming: false,
          });
        }
      })
      .catch(console.error);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId, sessionId]);

  // ── Intake form handlers ────────────────────────────────────────────────

  const handleAnswer = useCallback(
    (questionId: string, value: string | string[]) => {
      if (questionId === 'industry') {
        setIndustry(value as string);
      } else if (questionId === 'pain_points') {
        setPainPoints(Array.isArray(value) ? value : [value]);
      }
      setPendingAnswers((prev) => {
        const next    = { ...prev, [questionId]: value };
        const missing = missingRequired(next);
        store.setPanelData(1, {
          answers: next, missing, complete: missing.length === 0, streaming: false,
        });
        if (customerId && customerId !== '_' && sessionId && sessionId !== '_') {
          updateIntakeAnswers(customerId, sessionId, next).catch(() => {});
        }
        return next;
      });
    },
    [customerId, sessionId, store],
  );

  /**
   * Submit intake answers to the agent.
   * The structured answers are sent as extraPayload so the backend can prime
   * PipelineContext directly, while the user_message text gives the agent
   * natural-language context to start the pipeline conversation.
   */
  const handleSubmit = useCallback(() => {
    sendMessage(
      'I have provided my organizational constraints. Please analyze them and recommend an architecture pattern.',
      {
        answers:     pendingAnswers,
        industry,
        pain_points: painPoints,
      },
    );
  }, [sendMessage, pendingAnswers, industry, painPoints]);

  /**
   * Confirmation / pattern override — sent as a plain user message.
   * Examples: "Yes, continue with Federated"  |  "Use Centralized instead"
   */
  const handleConfirm = useCallback(
    (choice: string) => {
      store.setAwaitingConfirmation(false);
      sendMessage(choice);
    },
    [store, sendMessage],
  );

  const handleComponentClick = useCallback(
    (componentId: string, componentName: string) => {
      sendDrilldown(componentId, componentName);
    },
    [sendDrilldown],
  );

  const handleCloseDrilldown = useCallback(() => {
    store.setDrilldownData(null);
    store.setDrilldownComponentId(null);
  }, [store]);

  const handleExport = useCallback(
    async (format: 'pdf' | 'pptx') => {
      try {
        const { url } = await exportBlueprint(customerId, sessionId, format);
        window.open(url, '_blank');
      } catch (err) {
        console.error('Export failed', err);
      }
    },
    [customerId, sessionId],
  );

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: 'calc(100vh - 56px)', overflow: 'hidden',
    }}>
      {/* Session header */}
      <div style={{
        padding: '10px 20px',
        borderBottom: '1px solid var(--border-default)',
        background: 'var(--bg-card)',
        display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0,
      }}>
        <Link
          href={`/customers/${customerId}`}
          style={{
            color: 'var(--text-muted)', display: 'flex',
            alignItems: 'center', gap: 4, fontSize: 13,
          }}
        >
          <ArrowLeft size={13} /> Back
        </Link>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <StepIndicator currentStep={store.currentStep} />
        </div>
        <span style={{
          fontSize: 12, color: 'var(--text-muted)',
          minWidth: 60, textAlign: 'right',
        }}>
          Step {store.currentStep}/9
        </span>
      </div>

      {/* Split panel */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Chat — 35% */}
        <div style={{ width: '35%', minWidth: 280, flexShrink: 0, overflow: 'hidden' }}>
          <ChatPanel
            messages={store.chatMessages}
            isStreaming={store.isStreaming}
            awaitingConfirmation={store.awaitingConfirmation}
            confirmationRequest={store.confirmationRequest}
            onSendMessage={sendMessage}
            onConfirm={handleConfirm}
          />
        </div>

        {/* Visual panel — 65% */}
        <div style={{
          flex: 1, overflow: 'hidden',
          borderLeft: '1px solid var(--border-default)',
          position: 'relative',
          display: 'flex', flexDirection: 'column',
        }}>
          {/* Panel tab bar — shows all steps that have data */}
          {Object.keys(store.panelData).length > 0 && (
            <div style={{
              display: 'flex', flexShrink: 0, overflowX: 'auto',
              borderBottom: '1px solid var(--border-default)',
              background: 'var(--bg-card)',
              scrollbarWidth: 'none',
            }}>
              {Array.from({ length: 10 }, (_, i) => i + 1).map((step) => {
                const hasData = !!store.panelData[step];
                const isActive = selectedStep === step;
                const isCurrent = store.currentStep === step && store.isStreaming && !hasData;
                if (!hasData && !isCurrent) return null;
                return (
                  <button
                    key={step}
                    onClick={() => {
                      if (hasData) {
                        userSelectedRef.current = true;
                        setSelectedStep(step);
                      }
                    }}
                    style={{
                      padding: '8px 14px',
                      fontSize: 12,
                      fontWeight: isActive ? 600 : 400,
                      color: isActive ? 'var(--accent-blue)' : isCurrent ? 'var(--text-secondary)' : 'var(--text-muted)',
                      background: 'none',
                      border: 'none',
                      borderBottom: isActive ? '2px solid var(--accent-blue)' : '2px solid transparent',
                      cursor: hasData ? 'pointer' : 'default',
                      whiteSpace: 'nowrap',
                      flexShrink: 0,
                      transition: 'color 0.15s',
                      display: 'flex', alignItems: 'center', gap: 5,
                    }}
                  >
                    {isCurrent && (
                      <span style={{
                        width: 6, height: 6, borderRadius: '50%',
                        background: 'var(--accent-blue)',
                        animation: 'pulse-dot 1s ease-in-out infinite',
                        flexShrink: 0,
                      }} />
                    )}
                    {STEP_LABELS[step] ?? `Step ${step}`}
                  </button>
                );
              })}
              <style>{`
                @keyframes pulse-dot{0%,100%{opacity:0.4}50%{opacity:1}}
                div::-webkit-scrollbar{display:none}
              `}</style>
            </div>
          )}

          {/* Panel content */}
          <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
            <PanelRouter
              step={selectedStep}
              panelData={store.panelData}
              streaming={store.isStreaming}
              onAnswer={handleAnswer}
              onSubmit={handleSubmit}
              onConfirm={handleConfirm}
              onExport={handleExport}
              onComponentClick={handleComponentClick}
              onWhatIf={sendWhatIf}
              whatIfData={store.whatIfData}
              whatIfLoading={store.whatIfLoading}
            />
          </div>

          {/* Drilldown drawer */}
          {(store.drilldownLoading || store.drilldownData) && (
            <DrilldownDrawer
              data={store.drilldownData}
              loading={store.drilldownLoading}
              onClose={handleCloseDrilldown}
            />
          )}

          {/* Streaming overlay — only when active step has no data yet AND user is watching it */}
          {store.isStreaming && !store.panelData[store.currentStep] && selectedStep === store.currentStep && (
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'rgba(15,17,23,0.6)',
            }}>
              <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                <div style={{
                  width: 32, height: 32, borderRadius: '50%',
                  border: '3px solid var(--border-default)',
                  borderTopColor: 'var(--accent-blue)',
                  animation: 'spin 0.8s linear infinite',
                  margin: '0 auto 10px',
                }} />
                <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
                <p style={{ fontSize: 12 }}>Analyzing…</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
