'use client';
import { useEffect, useCallback, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAgentStream } from '@/hooks/useAgentStream';
import {
  getSession,
  getCustomer,
  getPanelStates,
  exportBlueprint,
  updateIntakeAnswers,
} from '@/lib/api';
import { ChatPanel } from '@/components/session/ChatPanel';
import { StepIndicator } from '@/components/session/StepIndicator';
import { PanelRouter } from '@/components/panels/PanelRouter';
import { DrilldownDrawer } from '@/components/panels/DrilldownDrawer';
import { Badge } from '@/components/ui/Badge';
import type { AssessmentDraft } from '@/lib/advisor-v2';
import { buildAssessmentInput, missingRequired } from '@/lib/advisor-v2';
import { STEP_NAMES, prettyPattern, sessionTitle } from '@/lib/session-format';

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
  const [customerName, setCustomerName] = useState('');
  const [sessionName, setSessionName] = useState('');

  // Auto-advance to the newest panel ONLY while the user is following the pipeline.
  // Once they manually pick a step, never yank them away — surface a "new" hint instead.
  useEffect(() => {
    if (!userSelectedRef.current) setSelectedStep(store.currentStep);
  }, [store.currentStep]);

  useEffect(() => {
    if (!userSelectedRef.current && store.panelData[store.currentStep]) {
      setSelectedStep(store.currentStep);
    }
  }, [store.panelData, store.currentStep]);

  // Intake answers collected locally before first submit
  const [pendingAnswers, setPendingAnswers] = useState<AssessmentDraft>({});

  const { sendMessage, sendDrilldown, stopStream } = useAgentStream(customerId, sessionId);

  // Restore session state on mount
  useEffect(() => {
    if (!customerId || customerId === '_' || !sessionId || sessionId === '_') return;
    store.resetSession();
    userSelectedRef.current = false;
    setSelectedStep(1);
    Promise.all([
      getCustomer(customerId),
      getSession(customerId, sessionId),
      getPanelStates(customerId, sessionId),
    ])
      .then(([customer, session, panelResponse]) => {
        setCustomerName(customer.name);
        setSessionName(sessionTitle(session));
        for (const item of panelResponse.panels) {
          const panel = item as { step?: number; data?: unknown };
          if (typeof panel.step === 'number') {
            store.setPanelData(panel.step, panel.data);
          }
        }
        store.setCurrentStep(
          session.current_step && session.current_step > 0 ? session.current_step : 1,
        );
        const saved = session.intake_answers;
        if (saved && Object.keys(saved).length > 0 && saved.primary_workload) {
          setPendingAnswers(saved as AssessmentDraft);
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
    (questionId: string, value: unknown) => {
      setPendingAnswers((prev) => {
        let next: AssessmentDraft = { ...prev, [questionId]: value };
        if (questionId === 'primary_workload' && prev.primary_workload !== value) {
          next = Object.fromEntries(
            Object.entries(next).filter(([key]) => !key.startsWith('workload_profile.')),
          );
          const secondary = Array.isArray(next.secondary_workloads)
            ? next.secondary_workloads.filter((item) => item !== value)
            : [];
          next.secondary_workloads = secondary;
        }
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
    const assessmentInput = buildAssessmentInput(pendingAnswers);
    sendMessage(
      'Evaluate this evidence and generate the architecture blueprint.',
      { assessment_input: assessmentInput },
    );
  }, [sendMessage, pendingAnswers]);

  const handleOverride = useCallback(
    (path: string, value: string, rationale: string, engineValue: string) => {
      const assessmentInput = buildAssessmentInput(pendingAnswers);
      sendMessage('Apply the recorded architecture override and recompute all downstream decisions.', {
        assessment_input: assessmentInput,
        overrides: [{
          decision_path: path,
          engine_value: engineValue,
          override_value: value,
          rationale,
          author: 'session-user',
          timestamp: new Date().toISOString(),
        }],
      });
    },
    [sendMessage, pendingAnswers],
  );

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

  const [exporting, setExporting] = useState<'pdf' | 'pptx' | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const handleExport = useCallback(
    async (format: 'pdf' | 'pptx') => {
      setExporting(format);
      setExportError(null);
      try {
        const { url } = await exportBlueprint(customerId, sessionId, format);
        window.open(url, '_blank');
      } catch (err) {
        setExportError(`Export failed: ${(err as Error).message}. Try again.`);
      } finally {
        setExporting(null);
      }
    },
    [customerId, sessionId],
  );

  // ── Derived view state ───────────────────────────────────────────────────
  const availableSteps = new Set(
    Object.keys(store.panelData).map(Number).filter((n) => !!store.panelData[n]),
  );
  const decision = store.panelData[2] as { operating_model?: string; evidence_coverage?: number } | undefined;
  const recommendedPattern = prettyPattern(decision?.operating_model);
  const confidencePct = typeof decision?.evidence_coverage === 'number' ? Math.round(decision.evidence_coverage * 100) : null;

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: 'calc(100vh - 56px)', overflow: 'hidden',
    }}>
      {/* Session header: breadcrumb + recommended pattern */}
      <div style={{
        padding: '10px 20px',
        borderBottom: '1px solid var(--border-default)',
        background: 'var(--bg-card)',
        display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0,
      }}>
        <Link
          href={`/customers/${customerId}`}
          style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--text-sm)', flexShrink: 0 }}
        >
          <ArrowLeft size={14} />
        </Link>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, minWidth: 0, flexShrink: 1 }}>
          <span className="eyebrow" style={{ whiteSpace: 'nowrap' }}>
            {customerName || 'Customer'}
          </span>
          <span className="text-display" style={{ fontSize: 'var(--text-lg)', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {sessionName || 'Advisory session'}
          </span>
        </div>
        <div style={{ flex: 1 }} />
        {recommendedPattern && (
          <Badge color="blue" size="md">
            {recommendedPattern}{confidencePct != null ? ` · ${confidencePct}%` : ''}
          </Badge>
        )}
      </div>

      {/* Step navigator (single, clickable, all 10 states) */}
      <div style={{
        padding: '6px 16px',
        borderBottom: '1px solid var(--border-default)',
        background: 'var(--bg-card)',
        flexShrink: 0,
      }}>
        <StepIndicator
          currentStep={store.currentStep}
          selectedStep={selectedStep}
          availableSteps={availableSteps}
          streaming={store.isStreaming}
          onSelect={(step) => { userSelectedRef.current = true; setSelectedStep(step); }}
        />
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
            onStop={stopStream}
          />
        </div>

        {/* Visual panel — 65% */}
        <div style={{
          flex: 1, overflow: 'hidden',
          borderLeft: '1px solid var(--border-default)',
          position: 'relative',
          display: 'flex', flexDirection: 'column',
        }}>
          {/* Panel content */}
          <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
            <PanelRouter
              step={selectedStep}
              panelData={store.panelData}
              streaming={store.isStreaming}
              onAnswer={handleAnswer}
              onSubmit={handleSubmit}
              onExport={handleExport}
              onComponentClick={handleComponentClick}
              onOverride={handleOverride}
              customerName={customerName}
              sessionName={sessionName}
              exportError={exportError}
              exporting={exporting}
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
              background: 'rgba(251,250,247,0.7)',
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
                <p style={{ fontSize: 'var(--text-sm)' }}>
                  {STEP_NAMES[store.currentStep - 1] ? `${STEP_NAMES[store.currentStep - 1]}…` : 'Analyzing…'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
