'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertCircle,
  Check,
  CheckCircle2,
  ChevronDown,
  Download,
  FileCheck2,
  ListChecks,
  MessageSquare,
  Pencil,
  RefreshCw,
  Send,
  Sparkles,
  X,
} from 'lucide-react';
import type {
  ArchitectureRequirement,
  ArchitectureWorkspaceProjection,
  EvidenceClaim,
  NextArchitectureQuestion,
  RequirementValue,
} from '@/lib/architecture-workspace';
import { deriveWorkspaceGuidance } from '@/lib/architecture-workspace';
import {
  chatArchitecture,
  downloadArchitecturePackage,
  type ArchitectureWorkspaceScope,
} from '@/lib/architecture-api';
import { FlowCanvas } from './FlowCanvas';
import {
  buildProjectionCanvas,
  componentPresentation,
  GROUP_COLOR,
  PHASE,
  type ArchitectureViewMode,
} from './architecture-model';

interface BlueprintContext {
  name: string;
  description: string;
  type: string;
}

interface Props {
  projection: ArchitectureWorkspaceProjection;
  blueprint?: BlueprintContext | null;
  onApplyPatch?: (answers: Record<string, RequirementValue>) => Promise<boolean> | boolean;
  scope?: ArchitectureWorkspaceScope;
  applying?: boolean;
  connectionState: 'live' | 'snapshot' | 'stale';
  onReload?: () => Promise<void> | void;
}

const TYPE_LABEL: Record<string, string> = {
  coding: 'Agentic Coding Platform',
  'agentic-coding': 'Agentic Coding Platform',
  internal: 'Internal-Facing Platform',
  'internal-facing': 'Internal-Facing Platform',
  'customer-facing': 'Customer-Facing Agentic Platform',
  saas: 'SaaS Decomposition',
  'saas-decomposition': 'SaaS Decomposition',
  marketplace: 'Marketplace',
};

const answerLabel = (answer: RequirementValue): string => {
  if (answer === true) return 'Yes';
  if (answer === false) return 'No';
  if (answer == null) return 'Not sure yet';
  const labels: Record<string, string> = {
    'developer-endpoint': 'Developer device',
    container: 'Isolated container',
    microvm: 'MicroVM',
    'dedicated-tenant': 'Dedicated environment',
  };
  if (labels[String(answer)]) return labels[String(answer)];
  return String(answer).replace(/[-_]/g, ' ').replace(/\b\w/g, (value) => value.toUpperCase());
};

function answerDescription(requirementId: string, answer: RequirementValue) {
  if (requirementId !== 'requirement:runtime-isolation') return '';
  const descriptions: Record<string, string> = {
    'developer-endpoint': 'Runs on the developer workstation with endpoint controls.',
    container: 'Separates tasks with an isolated process and filesystem.',
    microvm: 'Uses a lightweight virtual machine for stronger workload isolation.',
    'dedicated-tenant': 'Uses dedicated customer capacity for the strongest boundary.',
    null: 'Keep the alternatives open and confirm this later.',
  };
  return descriptions[String(answer)] ?? '';
}


const shortId = (value: string) => value.replace(/^[^:]+:/, '').replace(/-/g, ' ');

function moneyRange(range?: { low: number; high: number }) {
  if (!range) return 'Not available';
  return `$${range.low.toLocaleString(undefined, { maximumFractionDigits: 2 })} - $${range.high.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function FlowWorkspace({
  projection,
  blueprint,
  onApplyPatch,
  scope,
  applying = false,
  connectionState,
  onReload,
}: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ArchitectureViewMode>('logical');
  const [asideView, setAsideView] = useState<'questions' | 'chat' | 'trace'>('questions');
  const [reviewOpen, setReviewOpen] = useState(false);
  const [chatLog, setChatLog] = useState<{ role: 'user' | 'agent'; text: string }[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatBusy, setChatBusy] = useState(false);
  const [pendingPatch, setPendingPatch] = useState<Record<string, RequirementValue> | null>(null);
  const [proposalEditing, setProposalEditing] = useState(false);
  const [downloadBusy, setDownloadBusy] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadedHash, setDownloadedHash] = useState<string | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const canMutate = connectionState === 'live' && !applying;

  const guidance = useMemo(() => deriveWorkspaceGuidance(projection), [projection]);
  const recommendation = projection.deployable_solution?.recommendation;
  const isAdvisoryComparison = recommendation?.state === 'advisory';
  const selectedCandidate = projection.deployable_solution?.candidates.find(
    (candidate) => candidate.bundle_id === recommendation?.candidate_id,
  ) ?? projection.deployable_solution?.candidates[0];
  const canvas = useMemo(
    () => buildProjectionCanvas(projection, viewMode, selectedCandidate),
    [projection, selectedCandidate, viewMode],
  );
  const requirementsById = useMemo(
    () => new Map(projection.requirements.map((requirement) => [requirement.id, requirement])),
    [projection.requirements],
  );
  const claimsById = useMemo(
    () => new Map((projection.evidence ?? []).map((claim) => [claim.claim_id, claim])),
    [projection.evidence],
  );
  const selectedCanvasBlock = canvas.blocks.find((block) => block.id === selected);
  const selectedComponentIds = new Set(
    selectedCanvasBlock?.componentIds ?? (selected ? [selected] : []),
  );
  const selectedPlane = projection.architecture.planes.find(
    (plane) => plane.id === selectedCanvasBlock?.group
      || plane.components.some((component) => selectedComponentIds.has(component.id)),
  );
  const selectedComponent = selectedPlane?.components.find(
    (component) => selectedComponentIds.has(component.id),
  );
  const selectedPresentation = selectedCanvasBlock
    ? {
      ...(selectedComponent
        ? componentPresentation(
          selectedComponent.id,
          selectedComponent.name,
          selectedComponent.description,
        )
        : { bestPractices: [] }),
      label: selectedCanvasBlock.label,
      detail: selectedCanvasBlock.detail,
    }
    : null;
  const selectedService = selectedCandidate?.selections.find(
    (selection) => selectedComponentIds.has(selection.component_id),
  );
  const selectedTrace = projection.decision_trace.filter(
    (entry) => entry.target_component_ids.some((componentId) =>
      selectedComponentIds.has(componentId)),
  );
  const selectedRequirementIds = new Set(selectedTrace.flatMap((entry) => entry.requirement_ids));
  const selectedRequirements = projection.requirements.filter(
    (requirement) => selectedRequirementIds.has(requirement.id),
  );
  const selectedClaims = selectedTrace.flatMap((entry) =>
    (entry.evidence_claim_ids ?? [])
      .map((claimId) => claimsById.get(claimId))
      .filter((claim): claim is EvidenceClaim => Boolean(claim)),
  ).filter((claim, index, claims) =>
    claims.findIndex((candidate) => candidate.claim_id === claim.claim_id) === index,
  );
  const assurance = projection.assurance;
  const selectedPractices = (assurance?.security.best_practices ?? []).filter(
    (practice) => practice.applicable_component_ids?.some((componentId) =>
      selectedComponentIds.has(componentId)),
  );
  const selectedControls = (assurance?.security.controls ?? []).filter(
    (control) => control.applicable_component_ids?.some((componentId) =>
      selectedComponentIds.has(componentId)),
  );
  const canDownload = canMutate && guidance.readiness === 'publishable';

  useEffect(() => {
    if (!reviewOpen) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButtonRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setReviewOpen(false);
      if (event.key === 'Tab') {
        const dialog = closeButtonRef.current?.closest('[role="dialog"]');
        const focusable = dialog
          ? Array.from(dialog.querySelectorAll<HTMLElement>(
            'button:not([disabled]), details > summary, a[href], input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
          ))
          : [];
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      previous?.focus();
    };
  }, [reviewOpen]);

  function proposePatch(
    answers: Record<string, RequirementValue>,
    message = 'Review the proposed requirement change before applying it.',
  ) {
    if (!canMutate) return;
    setPendingPatch(answers);
    setProposalEditing(false);
    setChatLog((log) => [...log, { role: 'agent', text: message }]);
  }

  async function sendChat() {
    const message = chatInput.trim();
    if (!message || chatBusy || !canMutate) return;
    setChatInput('');
    setChatLog((log) => [...log, { role: 'user', text: message }]);
    setChatBusy(true);
    try {
      const result = await chatArchitecture(message, scope);
      if (Object.keys(result.proposed_answers).length) {
        proposePatch(result.proposed_answers, result.reply || 'Review the extracted customer requirements.');
      } else {
        setChatLog((log) => [...log, {
          role: 'agent',
          text: result.reply || 'I could not map that to a decision. Name a concrete customer constraint.',
        }]);
      }
    } catch {
      setChatLog((log) => [...log, {
        role: 'agent',
        text: 'The proposal service is unavailable. No architecture changes were made.',
      }]);
    } finally {
      setChatBusy(false);
    }
  }

  async function acceptPatch(explicitPatch?: Record<string, RequirementValue>) {
    const thePatch = explicitPatch ?? pendingPatch;
    if (!thePatch || !canMutate) return;
    const committed = await onApplyPatch?.(thePatch);
    if (committed === true) {
      const count = Object.keys(thePatch).length;
      setPendingPatch(null);
      setProposalEditing(false);
      setChatLog((log) => [...log, {
        role: 'agent',
        text: `Accepted ${count} change${count === 1 ? '' : 's'} and committed a new architecture revision.`,
      }]);
    } else {
      setChatLog((log) => [...log, {
        role: 'agent',
        text: 'The proposal was not committed. Reload the workspace before retrying.',
      }]);
    }
  }

  function rejectPatch() {
    setPendingPatch(null);
    setProposalEditing(false);
    setChatLog((log) => [...log, {
      role: 'agent',
      text: 'Proposal rejected. The architecture was not changed.',
    }]);
  }

  function clearGuidedAnswer() {
    setPendingPatch(null);
    setProposalEditing(false);
  }

  function updateProposal(requirement: ArchitectureRequirement, rawValue: string) {
    if (!pendingPatch) return;
    let value: RequirementValue = rawValue;
    if (typeof requirement.value === 'number') value = Number(rawValue);
    if (rawValue === 'true') value = true;
    if (rawValue === 'false') value = false;
    if (rawValue === 'null') value = null;
    setPendingPatch({ ...pendingPatch, [requirement.id]: value });
  }

  async function downloadPackage() {
    if (!canDownload) return;
    setDownloadBusy(true);
    setDownloadError(null);
    try {
      const result = await downloadArchitecturePackage(
        projection.meta.persistence_revision ?? projection.meta.revision_number,
        scope,
      );
      const url = URL.createObjectURL(result.blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = result.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setDownloadedHash(result.packageHash);
    } catch {
      setDownloadError('The immutable package could not be exported. Reload and try again.');
    } finally {
      setDownloadBusy(false);
    }
  }

  const nextQuestion = projection.next_question;
  const activeJourneyStep = guidance.readiness === 'publishable'
    ? 4
    : guidance.openRequirements.length || guidance.assumedRequirements
      ? 2
      : projection.deployable_solution ? 3 : 2;

  return (
    <div className="fw-root">
      <WorkspaceStyles />
      <header className="fw-head">
        <div className="fw-brand">
          <div className="fw-mark" aria-hidden="true" />
          <div>
            <h1>{blueprint?.name ?? 'Coding Agent Platform'}</h1>
            <p>{blueprint
              ? `${TYPE_LABEL[blueprint.type] ?? blueprint.type}${blueprint.description ? ` | ${blueprint.description}` : ''}`
              : 'Customer-specific architecture workspace'}</p>
          </div>
        </div>
        <div className="fw-segment" aria-label="Architecture view">
          {(['logical', 'deployable'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              aria-pressed={viewMode === mode}
              className={viewMode === mode ? 'active' : ''}
              onClick={() => setViewMode(mode)}
              disabled={mode === 'deployable' && !selectedCandidate}
            >
              {mode === 'logical' ? 'Logical' : 'Deployable'}
            </button>
          ))}
        </div>
        <span className={`fw-connection ${connectionState}`}>
          {connectionState === 'live' ? 'Live revision' : connectionState === 'stale' ? 'Stale revision' : 'Read-only snapshot'}
        </span>
        <button
          className="fw-package-button"
          type="button"
          onClick={() => setReviewOpen(true)}
          title={nextQuestion ? 'Complete guided discovery before reviewing the package' : undefined}
        >
          <Sparkles size={14} />
          {nextQuestion ? `Review package (${guidance.openRequirements.length} left)` : 'Review package'}
        </button>
      </header>

      <div className="fw-journey" aria-label="Architecture workflow">
        {[
          ['Baseline', 'Engine loaded'],
          ['Discovery', nextQuestion ? `${guidance.openRequirements.length} decisions left` : 'Complete'],
          ['Feasibility', guidance.feasibleAlternatives > 0 ? `${guidance.feasibleAlternatives} families confirmed` : 'Pending answers'],
          ['Package', guidance.readiness === 'publishable' ? 'Ready to export' : guidance.feasibleAlternatives > 0 ? 'Reviewable' : 'Awaiting feasibility'],
        ].map(([label, detail], index) => {
          const step = index + 1;
          return (
            <div key={label} className={`fw-step${step < activeJourneyStep ? ' done' : ''}${step === activeJourneyStep ? ' current' : ''}`}>
              <span className="fw-step-icon">{step < activeJourneyStep ? <Check size={12} /> : step}</span>
              <span><b>{label}</b><small>{detail}</small></span>
            </div>
          );
        })}
      </div>

      <main className="fw-main">
        <section className="fw-canvas-wrap" aria-label={`${viewMode} architecture diagram`}>
          <div className="fw-view-caption">
            <b>{viewMode === 'logical' ? 'Provider-neutral logical architecture' : selectedCandidate?.name}</b>
            <span>{canvas.blocks.length} {viewMode === 'logical' ? 'capabilities' : 'services'} | {canvas.wires.length} relationships</span>
          </div>
          <FlowCanvas
            key={`${viewMode}-${projection.meta.revision_number}`}
            blocks={canvas.blocks}
            wires={canvas.wires}
            groups={canvas.groups}
            selected={selected}
            onSelect={(componentId) => {
              setSelected(componentId);
              setAsideView('questions');
            }}
          />
        </section>

        <aside className="fw-aside" aria-label="Architecture inspector and discovery">
          <div className="fw-aside-tabs fw-aside-tabs-3" role="tablist" aria-label="Advisor panel">
            <button
              type="button"
              role="tab"
              aria-selected={asideView === 'questions'}
              className={asideView === 'questions' ? 'active' : ''}
              onClick={() => {
                setAsideView('questions');
                setSelected(null);
              }}
            >
              <ListChecks size={14} /> Questions
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={asideView === 'chat'}
              className={asideView === 'chat' ? 'active' : ''}
              onClick={() => setAsideView('chat')}
            >
              <MessageSquare size={14} /> Ask advisor
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={asideView === 'trace'}
              className={asideView === 'trace' ? 'active' : ''}
              onClick={() => setAsideView('trace')}
            >
              <Activity size={14} /> Trace
            </button>
          </div>
          <div className="fw-aside-scroll">
            {asideView === 'trace' ? (
              <DecisionTracePanel
                projection={projection}
              />
            ) : asideView === 'chat' ? (
              <div className="fw-chat">
                <div className="fw-chat-intro">
                  <b>Ask about an exception</b>
                  <span>Use free-form input when the guided choices do not describe the customer.</span>
                </div>
                <div className="fw-chat-log" aria-live="polite">
                  {chatLog.map((message, index) => (
                    <div key={`${message.role}-${index}`} className={`fw-message ${message.role}`}>{message.text}</div>
                  ))}
                  {chatBusy && <div className="fw-message agent">Interpreting requirements...</div>}
                </div>
                {pendingPatch && (
                  <ProposalPreview
                    patch={pendingPatch}
                    requirementsById={requirementsById}
                    editing={proposalEditing}
                    disabled={!canMutate}
                    applying={applying}
                    onEdit={() => setProposalEditing((value) => !value)}
                    onChange={updateProposal}
                    onReject={rejectPatch}
                    onAccept={acceptPatch}
                  />
                )}
                <div className="fw-chat-input">
                  <input
                    aria-label="Customer discovery message"
                    value={chatInput}
                    onChange={(event) => setChatInput(event.target.value)}
                    onKeyDown={(event) => { if (event.key === 'Enter') void sendChat(); }}
                    placeholder={canMutate ? 'Describe the exception or constraint...' : 'Workspace is read-only'}
                    disabled={!canMutate || chatBusy}
                  />
                  <button
                    type="button"
                    onClick={() => void sendChat()}
                    disabled={!canMutate || chatBusy || !chatInput.trim()}
                    aria-label="Send discovery message"
                  >
                    <Send size={14} />
                  </button>
                </div>
              </div>
            ) : !selectedCanvasBlock || !selectedPlane || !selectedPresentation ? (
              <WorkspaceSummary
                projection={projection}
                guidance={guidance}
                nextQuestion={nextQuestion}
                applying={!canMutate}
                pendingPatch={pendingPatch}
                onPropose={(requirementId, answer) => {
                  setPendingPatch({ [requirementId]: answer });
                  setProposalEditing(false);
                }}
                onChangeAnswer={clearGuidedAnswer}
                onApplyAnswer={acceptPatch}
                onOpenReview={() => setReviewOpen(true)}
              />
            ) : (
              <div>
                <div className="fw-inspector-head" style={colorVars(GROUP_COLOR[selectedCanvasBlock.group] ?? '#8b98ab')}>
                  <span>{PHASE[selectedCanvasBlock.group] ?? selectedPlane.label}</span>
                  <h2>{selectedPresentation.label}</h2>
                  <p>{selectedPresentation.detail}</p>
                  {viewMode === 'deployable' && (
                    <div className="fw-service">
                      <b>{selectedService?.service_name ?? 'No service selected'}</b>
                      <small>{selectedService
                        ? `${selectedService.provider_class} | ${selectedService.delivery_model.replace(/_/g, ' ')}`
                        : 'The selected candidate does not bind this component.'}</small>
                    </div>
                  )}
                </div>
                <InspectorSection title="Decision rationale">
                  {selectedTrace.length ? selectedTrace.map((entry) => (
                    <div className="fw-rationale-item" key={entry.evaluation_id}>
                      <span>{entry.effect}</span>
                      <p>{entry.rationale}</p>
                    </div>
                  )) : <p className="fw-muted">This is a baseline component of the selected logical pattern.</p>}
                </InspectorSection>
                {selectedRequirements.length > 0 && (
                  <InspectorSection title="Customer requirements">
                    {selectedRequirements.map((requirement) => (
                      <div className="fw-requirement" key={requirement.id}>
                        <span>{requirement.name}</span>
                        <b>{answerLabel(requirement.value)}</b>
                        <small>{requirement.status}</small>
                      </div>
                    ))}
                  </InspectorSection>
                )}
                {(selectedPractices.length > 0 || selectedPresentation.bestPractices.length > 0) && (
                  <InspectorSection title="Best practices">
                    <ul className="fw-practices">
                      {selectedPractices.map((practice) => (
                        <li key={practice.practice_id}>
                          <b>{practice.title}</b><span>{practice.implementation}</span>
                        </li>
                      ))}
                      {selectedPractices.length === 0 && selectedPresentation.bestPractices.map((practice) => (
                        <li key={practice}><span>{practice}</span></li>
                      ))}
                    </ul>
                  </InspectorSection>
                )}
                {selectedControls.length > 0 && (
                  <InspectorSection title="Required controls">
                    {selectedControls.map((control) => (
                      <div className="fw-control" key={control.control_id}>
                        <span className={control.status}>{control.status}</span>
                        <p><b>{control.title}</b><small>{control.verification.acceptance_criteria}</small></p>
                      </div>
                    ))}
                  </InspectorSection>
                )}
                {selectedClaims.length > 0 && (
                  <InspectorSection title="Approved evidence">
                    {selectedClaims.map((claim) => (
                      <div className="fw-claim" key={claim.claim_id}>
                        <p>{claim.statement}</p>
                        <small>{claim.source_title ?? claim.source_id} | {claim.source_locator}</small>
                      </div>
                    ))}
                  </InspectorSection>
                )}
              </div>
            )}
          </div>
        </aside>
      </main>

      {reviewOpen && (
        <div
          className="fw-dialog-scrim"
          onMouseDown={(event) => { if (event.target === event.currentTarget) setReviewOpen(false); }}
        >
          <div className="fw-dialog" role="dialog" aria-modal="true" aria-labelledby="architecture-package-title">
            <header>
              <div>
                <span>Customer architecture package</span>
                <h2 id="architecture-package-title">{blueprint?.name ?? 'Coding Agent Platform'}</h2>
                <small>Revision {projection.meta.revision_number} | catalog {projection.meta.catalog_version}</small>
              </div>
              <button ref={closeButtonRef} type="button" aria-label="Close package review" onClick={() => setReviewOpen(false)}>
                <X size={16} />
              </button>
            </header>
            <div className="fw-dialog-body">
              {nextQuestion ? (
                <div className="fw-verdict needs-information">
                  <AlertCircle size={18} />
                  <p>
                    <b>Guided discovery in progress</b>
                    <span>
                      {guidance.openRequirements.length} decision{guidance.openRequirements.length === 1 ? '' : 's'} remaining.
                      Complete guided discovery to confirm deployment families before reviewing the publication gate.
                    </span>
                  </p>
                </div>
              ) : (
                <div className={`fw-verdict ${guidance.readiness}`}>
                  {guidance.readiness === 'publishable' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
                  <p><b>{guidance.readinessLabel}</b><span>{guidance.readinessDetail}</span></p>
                </div>
              )}
              {!nextQuestion && guidance.publicationBlockers.length > 0 && (() => {
                const archGates = guidance.publicationBlockers.filter((b) =>
                  b.includes('open requirement') || b.includes('deployment family') || b.includes('deployable solution'),
                );
                const assumptionGates = guidance.publicationBlockers.filter((b) => b.includes('unconfirmed assumption'));
                const contentGates = guidance.publicationBlockers.filter((b) =>
                  !archGates.includes(b) && !assumptionGates.includes(b),
                );
                return (
                  <>
                    {archGates.length > 0 && (
                      <section>
                        <h3>Architecture gates — resolve first</h3>
                        <p className="fw-dialog-copy" style={{ fontSize: 10, marginBottom: 6 }}>
                          These block everything else. Answer the open requirements via <b>Ask advisor</b> to unlock feasibility.
                        </p>
                        <ul className="fw-gates">{archGates.map((b) => <li key={b}>{b}</li>)}</ul>
                      </section>
                    )}
                    {assumptionGates.length > 0 && (
                      <section>
                        <h3>Assumptions to confirm</h3>
                        <p className="fw-dialog-copy" style={{ fontSize: 10, marginBottom: 6 }}>
                          The engine made {guidance.assumedRequirements} baseline assumptions on your behalf. These must be explicitly confirmed or overridden by the customer before publishing.
                        </p>
                        <ul className="fw-gates">{assumptionGates.map((b) => <li key={b}>{b}</li>)}</ul>
                      </section>
                    )}
                    {contentGates.length > 0 && (
                      <section>
                        <h3>Publication gates — engagement work required</h3>
                        <p className="fw-dialog-copy" style={{ fontSize: 10, marginBottom: 6 }}>
                          These require evidence from the real customer engagement: control verification, risk sign-off, economics evidence, and decision evidence approval.
                        </p>
                        <ul className="fw-gates">{contentGates.map((b) => <li key={b}>{b}</li>)}</ul>
                      </section>
                    )}
                  </>
                );
              })()}

              <section>
                <h3>
                  {isAdvisoryComparison
                    ? 'Advisory comparison leader'
                    : 'Recommended deployable solution'}
                </h3>
                {selectedCandidate ? (
                  <>
                    <p className="fw-dialog-copy"><b>{selectedCandidate.name}</b> | {recommendation?.rationale}</p>
                    <div className="fw-stack">
                      {selectedCandidate.selections.map((selection) => (
                        <div key={selection.component_id}>
                          <span>{shortId(selection.component_id)}</span>
                          <b>{selection.service_name}</b>
                          <small>{selection.provider_class} | {selection.delivery_model.replace(/_/g, ' ')}</small>
                        </div>
                      ))}
                    </div>
                  </>
                ) : <p className="fw-muted">No viable deployable candidate is available.</p>}
              </section>

              <section>
                <h3>Alternatives and decision matrix</h3>
                <div className="fw-alternatives">
                  {(projection.deployable_solution?.candidates ?? []).map((candidate) => (
                    <details key={candidate.bundle_id} open={candidate.bundle_id === selectedCandidate?.bundle_id}>
                      <summary>
                        <span><b>#{candidate.rank} {candidate.name}</b><small>{candidate.compatibility_status}</small></span>
                        <span className="fw-score">{candidate.weighted_score.toFixed(1)}</span>
                        {candidate.pareto_optimal && <i>Pareto</i>}
                      </summary>
                      <div>
                        {candidate.tradeoffs.map((tradeoff) => (
                          <p key={tradeoff.tradeoff_id}><b>{tradeoff.kind}</b>{tradeoff.statement}</p>
                        ))}
                        {(candidate.findings ?? []).map((finding) => (
                          <p key={finding.finding_id} className="finding"><b>{finding.severity}</b>{finding.message}</p>
                        ))}
                      </div>
                    </details>
                  ))}
                </div>
                <div className="fw-feasibility">
                  {projection.feasibility.map((family) => (
                    <div key={family.pattern_id} className={family.status}>
                      <span>{family.status}</span>
                      <p><b>{family.name}</b><small>{family.reason ?? family.description}</small></p>
                    </div>
                  ))}
                </div>
              </section>

              {(projection.deployable_solution?.sensitivity.length ?? 0) > 0 && (
                <section>
                  <h3>Sensitivity</h3>
                  <div className="fw-sensitivity">
                    {projection.deployable_solution?.sensitivity.map((indicator) => (
                      <div key={indicator.dimension_id}>
                        <b>{shortId(indicator.dimension_id)}</b>
                        <span>{indicator.winner_changes
                          ? `Comparison leader changes to ${shortId(indicator.challenger_candidate_id ?? 'challenger')} at weight ${indicator.switch_weight?.toFixed(2)}`
                          : 'Comparison leader remains stable across tested weights'}</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {assurance && (
                <>
                  <section>
                    <h3>Assurance, economics, and outcomes</h3>
                    <div className="fw-metrics">
                      <div><span>Verified controls</span><b>{assurance.security.verified_control_count}/{assurance.security.controls.length}</b></div>
                      <div><span>High / critical risks</span><b>{assurance.security.high_or_critical_residual_count}</b></div>
                      <div><span>Monthly platform cost</span><b>{moneyRange(assurance.economics.totals.monthly_platform_cost)}</b></div>
                      <div><span>Cost / accepted PR</span><b>{moneyRange(assurance.economics.totals.cost_per_accepted_pull_request)}</b></div>
                    </div>
                    <p className="fw-warning">{assurance.economics.pricing_warning}</p>
                    <div className="fw-outcomes">
                      {assurance.outcomes.metrics.map((metric) => (
                        <div key={metric.metric_id}><b>{metric.name}</b><span>{metric.formula}</span></div>
                      ))}
                    </div>
                  </section>
                  <section>
                    <h3>Implementation roadmap</h3>
                    <div className="fw-roadmap">
                      {assurance.roadmap.phases.map((phase) => (
                        <div key={phase.phase_id}>
                          <span>{phase.sequence}</span>
                          <p><b>{phase.name}</b><small>{phase.work_packages.length} work packages | {phase.exit_criteria.join('; ')}</small></p>
                        </div>
                      ))}
                    </div>
                  </section>
                </>
              )}

              <section>
                <h3>Decision and evidence trace</h3>
                <div className="fw-trace">
                  {projection.decision_trace.map((entry) => (
                    <div key={entry.evaluation_id}>
                      <span>{entry.effect}</span>
                      <p><b>{shortId(entry.rule_id)}</b>{entry.rationale}</p>
                      <small>{entry.evidence_claim_ids?.length ?? 0} claims</small>
                    </div>
                  ))}
                </div>
              </section>
            </div>
            <footer>
              <p><FileCheck2 size={15} /> Export pins the workspace revision, catalog, decision matrix, assurance packet, roadmap, and evidence trace.</p>
              {connectionState !== 'live' && (
                <button type="button" className="secondary" onClick={() => void onReload?.()}>
                  <RefreshCw size={14} /> Reload live revision
                </button>
              )}
              <button type="button" onClick={() => void downloadPackage()} disabled={!canDownload || downloadBusy}>
                <Download size={14} /> {downloadBusy ? 'Exporting...' : 'Download immutable package'}
              </button>
              {downloadError && <span role="alert">{downloadError}</span>}
              {downloadedHash && <span className="success">Package hash: {downloadedHash}</span>}
            </footer>
          </div>
        </div>
      )}
    </div>
  );
}

function DecisionTracePanel({
  projection,
}: {
  projection: ArchitectureWorkspaceProjection;
}) {
  const history = projection.decision_history;
  return (
    <div className="fw-trace-panel">
      <div className="fw-trace-panel-header">
        <b>Engine decision trace</b>
        <span>Revision {projection.meta.revision_number} · {projection.decision_trace.length} rules evaluated</span>
      </div>
      {history && history.transitions.length > 0 && (
        <div className="fw-trace-history">
          <div className="fw-trace-history-label">Answer history</div>
          {[...history.transitions].reverse().map((t) => (
            <div key={t.transition_id} className="fw-trace-history-item">
              <div className="fw-trace-history-changes">
                {t.requirement_changes.map((rc) => (
                  <span key={rc.requirement_id} className={`fw-trace-change ${rc.change_type}`}>{rc.name}</span>
                ))}
              </div>
              <div className="fw-trace-history-delta">
                {t.architecture_delta.components.added.length > 0 && (
                  <span className="added">+{t.architecture_delta.components.added.length} added</span>
                )}
                {t.architecture_delta.components.removed.length > 0 && (
                  <span className="removed">−{t.architecture_delta.components.removed.length} removed</span>
                )}
                {t.architecture_delta.components.added.length === 0
                  && t.architecture_delta.components.removed.length === 0 && (
                  <span className="unchanged">no change</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="fw-trace-rules">
        <div className="fw-trace-history-label">Active rules</div>
        <div className="fw-trace">
          {projection.decision_trace.map((entry) => (
            <div key={entry.evaluation_id}>
              <span>{entry.effect}</span>
              <p>
                <b>{entry.rule_id.replace(/^[^:]+:/, '').replace(/-/g, ' ')}</b>
                {entry.rationale}
              </p>
              <small>{entry.target_component_ids.length} components</small>
            </div>
          ))}
          {projection.decision_trace.length === 0 && (
            <p className="fw-muted fw-trace-empty">No rules have fired yet. Answer the guided questions to see engine decisions here.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function WorkspaceSummary({
  projection,
  guidance,
  nextQuestion,
  applying,
  pendingPatch,
  onPropose,
  onChangeAnswer,
  onApplyAnswer,
  onOpenReview,
}: {
  projection: ArchitectureWorkspaceProjection;
  guidance: ReturnType<typeof deriveWorkspaceGuidance>;
  nextQuestion: NextArchitectureQuestion | null;
  applying: boolean;
  pendingPatch: Record<string, RequirementValue> | null;
  onPropose: (requirementId: string, answer: RequirementValue) => void;
  onChangeAnswer: () => void;
  onApplyAnswer: (patch?: Record<string, RequirementValue>) => void;
  onOpenReview: () => void;
}) {
  const [conflictPatch, setConflictPatch] = useState<Record<string, RequirementValue>>({});
  const [openReqPatch, setOpenReqPatch] = useState<Record<string, RequirementValue>>({});
  const [assumptionPatch, setAssumptionPatch] = useState<Record<string, RequirementValue>>({});
  const [assumptionsOpen, setAssumptionsOpen] = useState(false);
  const questionNumber = guidance.confirmedRequirements + guidance.assumedRequirements + 1;
  const questionCount = projection.requirements.length;
  const pendingAnswer = nextQuestion && pendingPatch
    && Object.prototype.hasOwnProperty.call(pendingPatch, nextQuestion.requirement_id)
    ? pendingPatch[nextQuestion.requirement_id]
    : undefined;
  const engineDone = !nextQuestion && guidance.requiredOpenRequirements.length === 0;
  const allAnswered = guidance.openRequirements.length === 0;
  const feasibleCount = guidance.feasibleAlternatives;
  const conflict = engineDone && feasibleCount === 0 && guidance.allFamiliesRejected;

  const assumedReqs = useMemo(
    () => projection.requirements.filter((r) => r.status === 'assumed'),
    [projection.requirements],
  );
  useEffect(() => {
    if (engineDone && assumedReqs.length > 0) setAssumptionsOpen(true);
  }, [engineDone, assumedReqs.length]);

  // Derive which requirements are causing family rejections
  const conflictItems = useMemo(() => {
    if (!conflict) return [];
    const rejectionRuleIds = new Set(
      projection.feasibility
        .filter((f) => f.status === 'rejected')
        .flatMap((f) => f.rejection_rule_ids ?? []),
    );
    const conflictTraces = projection.decision_trace.filter((e) => rejectionRuleIds.has(e.rule_id));
    const seen = new Set<string>();
    const items: Array<{
      req: ArchitectureRequirement;
      rationale: string;
      options: RequirementValue[];
      isAssumption: boolean;
    }> = [];
    for (const trace of conflictTraces) {
      for (const reqId of trace.requirement_ids) {
        if (seen.has(reqId)) continue;
        seen.add(reqId);
        const req = projection.requirements.find((r) => r.id === reqId);
        if (!req) continue;
        items.push({
          req,
          rationale: trace.rationale,
          options: req.candidate_answers ?? [],
          isAssumption: req.source === 'assumption',
        });
      }
    }
    return items;
  }, [conflict, projection.feasibility, projection.decision_trace, projection.requirements]);
  return (
    <div className="fw-discovery">
      <header>
        <div>
          <b>Guided discovery</b>
          <span>
            {engineDone
              ? allAnswered ? 'All decisions confirmed' : 'Architecture specified'
              : `${guidance.openRequirements.length} decisions remaining`}
          </span>
        </div>
        <span className={feasibleCount > 0 ? 'fw-feasibility-badge confirmed' : conflict ? 'fw-feasibility-badge conflict' : 'fw-feasibility-badge'}>
          {feasibleCount > 0 ? `${feasibleCount} famil${feasibleCount === 1 ? 'y' : 'ies'} confirmed` : conflict ? 'All families rejected' : 'Feasibility pending'}
        </span>
      </header>
      <div className="fw-discovery-progress" aria-label={`${guidance.coveredPercent}% complete`}>
        <i style={{ width: `${guidance.coveredPercent}%` }} />
      </div>
      {nextQuestion ? (
        <div className="fw-next">
          <span>Question {Math.min(questionNumber, questionCount)} of {questionCount}</span>
          <h2>{nextQuestion.customer_question}</h2>
          {nextQuestion.why_it_matters && (
            <p className="fw-why-it-matters">{nextQuestion.why_it_matters}</p>
          )}
          <div className="fw-answer-list" role="radiogroup" aria-label={nextQuestion.customer_question}>
            {nextQuestion.candidate_answers.map((answer, idx) => {
              const selectedAnswer = pendingAnswer === answer;
              const enrichment = nextQuestion.answer_enrichments?.[idx];
              const label = enrichment?.label ?? answerLabel(answer);
              const description = enrichment?.description ?? answerDescription(nextQuestion.requirement_id, answer);
              const watchOut = enrichment?.watch_out;
              return (
                <button
                  type="button"
                  role="radio"
                  aria-checked={selectedAnswer}
                  className={selectedAnswer ? 'selected' : ''}
                  key={String(answer)}
                  disabled={applying}
                  onClick={() => onPropose(nextQuestion.requirement_id, answer)}
                >
                  <i>{selectedAnswer && <Check size={12} />}</i>
                  <span>
                    <b>{label}</b>
                    {description && <small>{description}</small>}
                    {selectedAnswer && watchOut && <small className="fw-watch-out">Watch out: {watchOut}</small>}
                  </span>
                </button>
              );
            })}
          </div>
          {pendingAnswer !== undefined && (
            <div className="fw-answer-actions">
              <button type="button" onClick={onChangeAnswer} disabled={applying}>Change</button>
              <button type="button" className="primary" onClick={() => onApplyAnswer()} disabled={applying}>
                {applying ? 'Applying...' : 'Apply answer'}
              </button>
            </div>
          )}
        </div>
      ) : engineDone ? (
        conflict ? (
          <div className="fw-engine-done fw-engine-conflict">
            <div className="fw-engine-done-icon"><AlertCircle size={22} /></div>
            <b>Requirements conflict — no deployment family confirmed</b>
            <p>Your current choices collectively reject every deployment family. Review what&apos;s causing the conflict below and select alternative values to resolve it.</p>
            {conflictItems.length > 0 && (
              <div className="fw-conflict-list">
                {conflictItems.map(({ req, rationale, options, isAssumption }) => {
                  const alternatives = options.filter((opt) => opt !== req.value);
                  return (
                    <div key={req.id} className="fw-conflict-item">
                      <div className="fw-conflict-item-header">
                        <span className="fw-conflict-req-name">{req.customer_question ?? req.name}</span>
                        <span className="fw-conflict-current">{answerLabel(req.value)}{isAssumption && <i> (assumed)</i>}</span>
                      </div>
                      <p className="fw-conflict-rationale">{rationale}</p>
                      {alternatives.length > 0 && (
                        <div className="fw-conflict-options">
                          <small>Try instead:</small>
                          <div className="fw-conflict-choices">
                            {alternatives.map((opt) => {
                              const selected = conflictPatch[req.id] === opt;
                              return (
                                <button
                                  key={String(opt)}
                                  type="button"
                                  className={selected ? 'selected' : ''}
                                  disabled={applying || isAssumption}
                                  onClick={() => {
                                    if (selected) {
                                      const next = { ...conflictPatch };
                                      delete next[req.id];
                                      setConflictPatch(next);
                                    } else {
                                      setConflictPatch({ ...conflictPatch, [req.id]: opt });
                                    }
                                  }}
                                >
                                  {selected && <Check size={10} />}
                                  {answerLabel(opt)}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
                      {isAssumption && (
                        <small className="fw-conflict-assumption-note">Set by assumption — use Ask advisor to override.</small>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
            {conflictItems.length === 0 && (
              <p className="fw-engine-done-next">Open the <b>Trace tab</b> to inspect which rules are firing, then use Ask advisor to change the conflicting answers.</p>
            )}
            {Object.keys(conflictPatch).length > 0 ? (
              <div className="fw-answer-actions">
                <button type="button" onClick={() => setConflictPatch({})} disabled={applying}>Reset</button>
                <button type="button" className="primary" onClick={() => onApplyAnswer(conflictPatch)} disabled={applying}>
                  {applying ? 'Applying…' : `Apply ${Object.keys(conflictPatch).length} fix${Object.keys(conflictPatch).length === 1 ? '' : 'es'}`}
                </button>
              </div>
            ) : (
              <button type="button" className="fw-review-cta" onClick={onOpenReview}>
                <AlertCircle size={14} /> View full trace
              </button>
            )}
          </div>
        ) : (
          <div className={`fw-engine-done${feasibleCount === 0 ? ' fw-engine-unresolved' : ''}`}>
            <div className="fw-engine-done-icon">
              {feasibleCount > 0 ? <CheckCircle2 size={22} /> : <AlertCircle size={22} />}
            </div>
            <b>{feasibleCount > 0 ? 'Architecture is fully specified' : 'Deployment families unresolved'}</b>
            {feasibleCount > 0 ? (
              <>
                <p className="fw-engine-done-next">
                  <b>{feasibleCount} deployment famil{feasibleCount === 1 ? 'y' : 'ies'} confirmed.</b>
                </p>
                {guidance.openRequirements.length > 0 ? (
                  <>
                    <p>{guidance.openRequirements.length} additional answer{guidance.openRequirements.length === 1 ? '' : 's'} will complete the bundle comparison for review.</p>
                    {guidance.openRequirements.map((req) => {
                      const chosen = openReqPatch[req.id];
                      if ((req.candidate_answers?.length ?? 0) > 0) {
                        return (
                          <div key={req.id} className="fw-open-req-item">
                            <span className="fw-open-req-label">{req.customer_question ?? req.name}</span>
                            <div className="fw-conflict-choices">
                              {(req.candidate_answers ?? []).map((opt) => {
                                const sel = chosen === opt;
                                return (
                                  <button
                                    key={String(opt)}
                                    type="button"
                                    className={sel ? 'selected' : ''}
                                    disabled={applying}
                                    onClick={() => {
                                      if (sel) {
                                        const next = { ...openReqPatch };
                                        delete next[req.id];
                                        setOpenReqPatch(next);
                                      } else {
                                        setOpenReqPatch({ ...openReqPatch, [req.id]: opt });
                                      }
                                    }}
                                  >
                                    {sel && <Check size={10} />}{answerLabel(opt)}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        );
                      }
                      return (
                        <div key={req.id} className="fw-open-req-item">
                          <span className="fw-open-req-label">{req.customer_question ?? req.description ?? req.name}</span>
                          <input
                            type="number"
                            className="fw-open-req-number"
                            min={1}
                            placeholder="Enter a number…"
                            value={chosen !== undefined ? String(chosen) : ''}
                            disabled={applying}
                            onChange={(e) => {
                              const val = e.target.value === '' ? undefined : Number(e.target.value);
                              if (val === undefined) {
                                const next = { ...openReqPatch };
                                delete next[req.id];
                                setOpenReqPatch(next);
                              } else {
                                setOpenReqPatch({ ...openReqPatch, [req.id]: val });
                              }
                            }}
                          />
                        </div>
                      );
                    })}
                    {Object.keys(openReqPatch).length > 0 && (
                      <div className="fw-answer-actions">
                        <button type="button" onClick={() => setOpenReqPatch({})} disabled={applying}>Reset</button>
                        <button type="button" className="primary" onClick={() => onApplyAnswer(openReqPatch)} disabled={applying}>
                          {applying ? 'Applying…' : `Apply ${Object.keys(openReqPatch).length} answer${Object.keys(openReqPatch).length === 1 ? '' : 's'}`}
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <p>All requirements are confirmed. The engine has all the information it needs.</p>
                )}
                <button type="button" className="fw-review-cta" onClick={onOpenReview}>
                  <Sparkles size={14} /> Review package
                </button>
              </>
            ) : (
              <>
                <p>{guidance.openRequirements.length} more answer{guidance.openRequirements.length === 1 ? '' : 's'} needed before the engine can confirm which deployment families are available to you.</p>
                {guidance.openRequirements.map((req) => {
                  const chosen = openReqPatch[req.id];
                  if ((req.candidate_answers?.length ?? 0) > 0) {
                    return (
                      <div key={req.id} className="fw-open-req-item">
                        <span className="fw-open-req-label">{req.customer_question ?? req.name}</span>
                        <div className="fw-conflict-choices">
                          {(req.candidate_answers ?? []).map((opt) => {
                            const sel = chosen === opt;
                            return (
                              <button
                                key={String(opt)}
                                type="button"
                                className={sel ? 'selected' : ''}
                                disabled={applying}
                                onClick={() => {
                                  if (sel) {
                                    const next = { ...openReqPatch };
                                    delete next[req.id];
                                    setOpenReqPatch(next);
                                  } else {
                                    setOpenReqPatch({ ...openReqPatch, [req.id]: opt });
                                  }
                                }}
                              >
                                {sel && <Check size={10} />}
                                {answerLabel(opt)}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  }
                  return (
                    <div key={req.id} className="fw-open-req-item">
                      <span className="fw-open-req-label">{req.customer_question ?? req.description ?? req.name}</span>
                      <input
                        type="number"
                        className="fw-open-req-number"
                        min={1}
                        placeholder="Enter a number…"
                        value={chosen !== undefined ? String(chosen) : ''}
                        disabled={applying}
                        onChange={(e) => {
                          const val = e.target.value === '' ? undefined : Number(e.target.value);
                          if (val === undefined) {
                            const next = { ...openReqPatch };
                            delete next[req.id];
                            setOpenReqPatch(next);
                          } else {
                            setOpenReqPatch({ ...openReqPatch, [req.id]: val });
                          }
                        }}
                      />
                    </div>
                  );
                })}
                {Object.keys(openReqPatch).length > 0 && (
                  <div className="fw-answer-actions">
                    <button type="button" onClick={() => setOpenReqPatch({})} disabled={applying}>Reset</button>
                    <button type="button" className="primary" onClick={() => onApplyAnswer(openReqPatch)} disabled={applying}>
                      {applying ? 'Applying…' : `Apply ${Object.keys(openReqPatch).length} answer${Object.keys(openReqPatch).length === 1 ? '' : 's'}`}
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )
      ) : (
        <div className="fw-engine-done fw-engine-blocked">
          <div className="fw-engine-done-icon">
            <AlertCircle size={22} />
          </div>
          <b>{guidance.requiredOpenRequirements.length} required decision{guidance.requiredOpenRequirements.length === 1 ? '' : 's'} still open</b>
          <p>The engine is waiting for a required answer before it can surface the next question.</p>
          <ul>
            {guidance.requiredOpenRequirements.map((req) => (
              <li key={req.id}><b>{req.name}</b></li>
            ))}
          </ul>
          <p className="fw-engine-blocked-hint">Use the <b>Ask advisor</b> tab to answer the requirement above, then reload.</p>
        </div>
      )}
      {assumedReqs.length > 0 && (
        <div className="fw-assumptions">
          <button
            type="button"
            className="fw-assumptions-header"
            onClick={() => setAssumptionsOpen((o) => !o)}
          >
            <span>
              <b>{assumedReqs.length} working assumption{assumedReqs.length === 1 ? '' : 's'}</b>
              <small>Engine-set defaults — confirm or change before publishing</small>
            </span>
            <ChevronDown size={12} className={assumptionsOpen ? 'fw-chevron-open' : undefined} />
          </button>
          {assumptionsOpen && (
            <>
              <div className="fw-assumptions-list">
                {assumedReqs.map((req) => {
                  const override = assumptionPatch[req.id];
                  const effectiveVal = override !== undefined ? override : req.value;
                  if ((req.candidate_answers?.length ?? 0) > 0) {
                    return (
                      <div key={req.id} className="fw-assumption-item">
                        <span className="fw-open-req-label">{req.customer_question ?? req.name}</span>
                        <div className="fw-conflict-choices">
                          {(req.candidate_answers ?? []).map((opt) => {
                            const sel = effectiveVal === opt;
                            const isOriginal = override === undefined && req.value === opt;
                            return (
                              <button
                                key={String(opt)}
                                type="button"
                                className={sel ? (isOriginal ? 'assumed' : 'selected') : ''}
                                disabled={applying}
                                onClick={() => {
                                  if (opt === req.value) {
                                    const next = { ...assumptionPatch };
                                    delete next[req.id];
                                    setAssumptionPatch(next);
                                  } else {
                                    setAssumptionPatch({ ...assumptionPatch, [req.id]: opt });
                                  }
                                }}
                              >
                                {sel && <Check size={10} />}
                                {answerLabel(opt)}
                                {isOriginal && <em>assumed</em>}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  }
                  return (
                    <div key={req.id} className="fw-assumption-item">
                      <span className="fw-open-req-label">{req.customer_question ?? req.description ?? req.name}</span>
                      <div className="fw-assumption-numeric">
                        <input
                          type="number"
                          className="fw-open-req-number"
                          min={1}
                          value={effectiveVal !== undefined && effectiveVal !== null ? String(effectiveVal) : ''}
                          disabled={applying}
                          onChange={(e) => {
                            const val = e.target.value === '' ? undefined : Number(e.target.value);
                            if (val === undefined || val === req.value) {
                              const next = { ...assumptionPatch };
                              delete next[req.id];
                              setAssumptionPatch(next);
                            } else {
                              setAssumptionPatch({ ...assumptionPatch, [req.id]: val });
                            }
                          }}
                        />
                        {override === undefined && <span className="fw-assumption-tag">assumed</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="fw-answer-actions">
                {Object.keys(assumptionPatch).length > 0 && (
                  <button type="button" onClick={() => setAssumptionPatch({})} disabled={applying}>Reset</button>
                )}
                <button
                  type="button"
                  className="primary"
                  disabled={applying}
                  onClick={() => {
                    const confirmPatch = {
                      ...Object.fromEntries(assumedReqs.map((r) => [r.id, r.value])),
                      ...assumptionPatch,
                    };
                    onApplyAnswer(confirmPatch);
                  }}
                >
                  {applying
                    ? 'Applying…'
                    : Object.keys(assumptionPatch).length > 0
                      ? `Apply ${Object.keys(assumptionPatch).length} change${Object.keys(assumptionPatch).length === 1 ? '' : 's'}`
                      : `Confirm all ${assumedReqs.length} as-is`}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function InspectorSection({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="fw-inspector-section"><h3>{title}</h3>{children}</section>;
}

function ProposalPreview({
  patch,
  requirementsById,
  editing,
  disabled,
  applying,
  onEdit,
  onChange,
  onReject,
  onAccept,
}: {
  patch: Record<string, RequirementValue>;
  requirementsById: Map<string, ArchitectureRequirement>;
  editing: boolean;
  disabled: boolean;
  applying: boolean;
  onEdit: () => void;
  onChange: (requirement: ArchitectureRequirement, value: string) => void;
  onReject: () => void;
  onAccept: () => void;
}) {
  return (
    <div className="fw-proposal">
      <span>Review proposed answers</span>
      {Object.entries(patch).map(([requirementId, value]) => {
        const requirement = requirementsById.get(requirementId) ?? {
          id: requirementId,
          name: shortId(requirementId),
          value,
          status: 'unanswered' as const,
        };
        return (
          <label key={requirementId}>
            <span>{requirement.name}</span>
            {editing ? (
              typeof value === 'boolean' ? (
                <select value={String(value)} onChange={(event) => onChange(requirement, event.target.value)}>
                  <option value="true">Yes</option><option value="false">No</option>
                </select>
              ) : (
                <input
                  type={typeof value === 'number' ? 'number' : 'text'}
                  value={value == null ? '' : String(value)}
                  onChange={(event) => onChange(requirement, event.target.value)}
                />
              )
            ) : <b>{answerLabel(value)}</b>}
          </label>
        );
      })}
      <div>
        <button type="button" onClick={onEdit} disabled={disabled}><Pencil size={13} />{editing ? 'Done' : 'Edit'}</button>
        <button type="button" onClick={onReject} disabled={disabled}><X size={13} />Reject</button>
        <button type="button" className="accept" onClick={onAccept} disabled={disabled}>
          <Check size={13} />{applying ? 'Applying...' : 'Accept'}
        </button>
      </div>
    </div>
  );
}

function colorVars(color: string): React.CSSProperties {
  return {
    ['--section-color' as string]: color,
    ['--section-tint' as string]: `${color}18`,
  };
}

function WorkspaceStyles() {
  return (
    <style>{`
.fw-root{--bg:#0e1116;--panel:#12161d;--line:#242e3b;--soft:#1c2531;--ink:#e6e9ef;--dim:#a7b2c2;--muted:#7c8899;--green:#37dd7d;--amber:#f0a850;--red:#fb7185;color:var(--ink);background:var(--bg);font:14px/1.5 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden}
.fw-root *{box-sizing:border-box;letter-spacing:0}
.fw-head{display:flex;align-items:center;gap:14px;padding:12px 20px;border-bottom:1px solid var(--soft);flex:none;background:#0f131a}
.fw-brand{display:flex;align-items:center;gap:11px;min-width:0}.fw-mark{width:30px;height:30px;border-radius:8px;background:conic-gradient(from 210deg,#37dd7d,#4cc4f5,#7d9bff,#b98cf0,#37dd7d);flex:none}.fw-brand h1{font-size:15px;margin:0}.fw-brand p{font-size:10.5px;color:var(--muted);margin:1px 0 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:390px}
.fw-segment{margin-left:auto;display:flex;padding:2px;border:1px solid var(--line);border-radius:7px;background:#090c11}.fw-segment button{border:0;background:transparent;color:var(--muted);padding:5px 10px;border-radius:5px;font:600 10px inherit;cursor:pointer}.fw-segment button.active{background:#26303e;color:var(--ink)}.fw-segment button:disabled{opacity:.4}
.fw-connection{font-size:9px;text-transform:uppercase;color:var(--green)}.fw-connection.snapshot,.fw-connection.stale{color:var(--amber)}
.fw-package-button{display:flex;align-items:center;gap:6px;border:0;border-radius:7px;background:var(--green);color:#07130c;padding:7px 11px;font:700 11px inherit;cursor:pointer}
.fw-journey{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));padding:0 20px;border-bottom:1px solid var(--soft);background:#0c1016;flex:none}.fw-step{display:flex;align-items:center;gap:8px;padding:7px 10px;color:#556072;min-width:0;border-right:1px solid var(--soft)}.fw-step:last-child{border:0}.fw-step-icon{width:20px;height:20px;display:grid;place-items:center;border:1px solid var(--line);border-radius:50%;font-size:9px;flex:none}.fw-step>span:last-child{display:flex;flex-direction:column;min-width:0}.fw-step b{font-size:10px}.fw-step small{font-size:8.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.fw-step.done{color:#64d998}.fw-step.current{color:var(--ink)}
.fw-main{display:flex;flex:1;min-height:0}.fw-canvas-wrap{position:relative;flex:1;min-width:0}.fw-view-caption{position:absolute;z-index:4;left:14px;top:12px;display:flex;flex-direction:column;padding:7px 9px;border:1px solid var(--line);border-radius:7px;background:#0e1116dd;pointer-events:none}.fw-view-caption b{font-size:10px}.fw-view-caption span{font-size:8.5px;color:var(--muted)}
.fw-aside{width:410px;flex:none;min-height:0;display:flex;flex-direction:column;background:var(--panel);border-left:1px solid var(--soft)}.fw-aside-scroll{flex:1;min-height:0;overflow:auto}
.fw-aside-tabs{display:grid;grid-template-columns:1fr 1fr;gap:4px;padding:8px;border-bottom:1px solid var(--soft);background:#0d1118}.fw-aside-tabs-3{grid-template-columns:1fr 1fr 1fr}.fw-aside-tabs button{display:flex;align-items:center;justify-content:center;gap:6px;border:0;border-radius:6px;background:transparent;color:var(--muted);padding:8px;font:650 10.5px inherit;cursor:pointer}.fw-aside-tabs button.active{background:#202936;color:var(--ink)}.fw-aside-tabs button:focus-visible{outline:2px solid var(--green);outline-offset:1px}
.fw-discovery{padding:22px 22px 28px}.fw-discovery>header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.fw-discovery>header div{display:flex;flex-direction:column}.fw-discovery>header b{font-size:13px}.fw-discovery>header>div>span{font-size:9.5px;color:var(--muted)}.fw-feasibility-badge{font-size:8.5px;color:var(--muted);padding:2px 7px;border-radius:10px;border:1px solid var(--line);white-space:nowrap;margin-top:2px}.fw-feasibility-badge.confirmed{color:#5eead4;border-color:#2dd4bf44;background:#2dd4bf12}.fw-feasibility-badge.conflict{color:#f87171;border-color:#f8717144;background:#f8717112}
.fw-engine-done{margin-top:20px;padding:16px;border:1px solid var(--line);border-radius:10px;background:#ffffff04;display:flex;flex-direction:column;gap:8px}.fw-engine-done-icon{color:var(--green)}.fw-engine-blocked .fw-engine-done-icon,.fw-engine-unresolved .fw-engine-done-icon{color:var(--amber)}.fw-engine-unresolved{border-color:#f0a85033 !important;background:#1a150904 !important}.fw-engine-conflict .fw-engine-done-icon{color:var(--red)}.fw-engine-conflict{border-color:#f8717133 !important;background:#1f0f1012 !important}.fw-engine-conflict .fw-review-cta{border-color:var(--red);background:#fb718512;color:var(--red)}.fw-engine-conflict .fw-review-cta:hover{background:#fb718522}.fw-engine-done b{font-size:12px}.fw-engine-done p{font-size:10.5px;color:var(--dim);margin:0;line-height:1.5}.fw-engine-done-next{color:var(--muted) !important;font-size:10px !important}.fw-engine-blocked-hint{color:var(--muted) !important;font-size:9.5px !important;font-style:italic}.fw-engine-done ul{margin:4px 0 0;padding-left:16px;display:flex;flex-direction:column;gap:5px}.fw-engine-done li{font-size:10px;color:var(--muted);line-height:1.5}.fw-engine-done li b{color:var(--ink)}.fw-open-req-item{display:flex;flex-direction:column;gap:6px;padding:9px 10px;border:1px solid #f0a85033;border-radius:7px;background:#1a150a}.fw-open-req-label{font-size:10px;font-weight:600;color:var(--ink);line-height:1.4}.fw-review-cta{display:flex;align-items:center;justify-content:center;gap:7px;margin-top:4px;padding:10px;border:1px solid var(--green);border-radius:7px;background:#37dd7d18;color:var(--green);font:650 11px inherit;cursor:pointer}.fw-review-cta:hover{background:#37dd7d28}
.fw-conflict-list{display:flex;flex-direction:column;gap:8px;margin-top:4px}.fw-conflict-item{display:flex;flex-direction:column;gap:6px;padding:10px;border:1px solid #f8717122;border-radius:7px;background:#1a0d0f}.fw-conflict-item-header{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}.fw-conflict-req-name{font-size:10.5px;font-weight:600;line-height:1.4;color:var(--ink)}.fw-conflict-current{font-size:9px;color:var(--red);white-space:nowrap;flex-shrink:0;margin-top:2px}.fw-conflict-current i{font-style:normal;color:var(--amber)}.fw-conflict-rationale{font-size:9px;color:var(--muted);margin:0;font-style:italic;border-left:2px solid #f8717144;padding-left:6px;line-height:1.45}.fw-conflict-options{display:flex;flex-direction:column;gap:5px}.fw-conflict-options>small{font-size:8.5px;text-transform:uppercase;font-weight:700;color:var(--muted)}.fw-conflict-choices{display:flex;flex-wrap:wrap;gap:5px}.fw-conflict-choices>button{display:flex;align-items:center;gap:4px;border:1px solid var(--line);border-radius:5px;background:transparent;color:var(--dim);padding:4px 8px;font:600 9.5px inherit;cursor:pointer}.fw-conflict-choices>button:hover:not(:disabled){border-color:#47576c;background:#151c26}.fw-conflict-choices>button.selected{border-color:var(--green);background:#102019;color:var(--green)}.fw-conflict-choices>button:disabled{opacity:.4;cursor:default}.fw-conflict-assumption-note{font-size:8.5px;color:var(--amber);font-style:italic}
.fw-discovery-progress{height:4px;margin:12px 0 27px;border-radius:2px;overflow:hidden;background:var(--line)}.fw-discovery-progress i{display:block;height:100%;background:var(--green)}
.fw-next>span,.fw-proposal>span{font-size:8.5px;text-transform:uppercase;color:var(--muted);font-weight:750}.fw-next h2{font-size:18px;line-height:1.35;margin:8px 0}.fw-next>p{font-size:10.5px;color:var(--muted);margin:0 0 17px}.fw-why-it-matters{font-size:10.5px;color:var(--dim);margin:0 0 17px;padding:9px 10px;border-left:2px solid var(--green);background:#37dd7d0a}.fw-answer-list small+small.fw-watch-out{color:var(--amber);margin-top:4px;font-style:italic}.fw-answer-list{display:flex;flex-direction:column;gap:7px}.fw-answer-list>button{width:100%;display:flex;align-items:flex-start;gap:10px;text-align:left;border:1px solid var(--line);border-radius:7px;background:#11161e;color:var(--ink);padding:10px 11px;cursor:pointer}.fw-answer-list>button:hover{border-color:#47576c;background:#151c26}.fw-answer-list>button.selected{border-color:var(--green);background:#102019}.fw-answer-list>button:disabled{opacity:.45}.fw-answer-list>button>i{width:17px;height:17px;display:grid;place-items:center;flex:none;margin-top:1px;border:1px solid #4b596d;border-radius:50%;color:#07130c;font-style:normal}.fw-answer-list>button.selected>i{border-color:var(--green);background:var(--green)}.fw-answer-list>button>span{display:flex;flex-direction:column}.fw-answer-list b{font-size:11.5px}.fw-answer-list small{font-size:9.5px;line-height:1.4;color:var(--muted);margin-top:2px}
.fw-answer-actions{display:flex;justify-content:flex-end;gap:7px;margin-top:16px;padding-top:13px;border-top:1px solid var(--soft)}.fw-answer-actions button{border:1px solid var(--line);border-radius:6px;background:transparent;color:var(--dim);padding:7px 10px;font:650 10px inherit}.fw-answer-actions button.primary{border-color:var(--green);background:var(--green);color:#07130c}.fw-answer-actions button:disabled{opacity:.45}
.fw-open-req-number{width:100%;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);padding:6px 8px;font:11px inherit}
.fw-assumptions{margin-top:18px;border:1px solid #7d9bff33;border-radius:9px;overflow:hidden;background:#111827}.fw-assumptions-header{width:100%;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 14px;background:transparent;border:0;color:var(--ink);cursor:pointer;text-align:left}.fw-assumptions-header:hover{background:#ffffff06}.fw-assumptions-header>span{display:flex;flex-direction:column;gap:2px}.fw-assumptions-header b{font-size:11px}.fw-assumptions-header small{font-size:9px;color:var(--muted)}.fw-chevron-open{transform:rotate(180deg)}.fw-assumptions-list{display:flex;flex-direction:column;gap:6px;padding:0 12px 4px}.fw-assumption-item{display:flex;flex-direction:column;gap:6px;padding:9px 10px;border:1px solid #7d9bff22;border-radius:7px;background:#0f1520}.fw-assumption-numeric{display:flex;align-items:center;gap:8px}.fw-assumption-tag{font-size:8px;text-transform:uppercase;color:#aebeff;padding:2px 5px;border-radius:4px;background:#7d9bff18;white-space:nowrap}.fw-conflict-choices>button.assumed{border-color:#7d9bff66;background:#101a2e;color:#aebeff}.fw-assumptions .fw-answer-actions{margin:8px 12px 12px;padding-top:10px}
.fw-inspector-head{padding:20px;border-bottom:1px solid var(--soft);border-left:3px solid var(--section-color);background:linear-gradient(110deg,var(--section-tint),transparent)}.fw-inspector-head>span{font-size:8.5px;text-transform:uppercase;color:var(--section-color);font-weight:750}.fw-inspector-head h2{font-size:18px;margin:6px 0}.fw-inspector-head>p{font-size:11.5px;color:var(--dim);margin:0}.fw-service{display:flex;flex-direction:column;margin-top:12px;padding:9px;border:1px solid var(--line);border-radius:7px;background:#0e1116}.fw-service b{font-size:11.5px}.fw-service small{font-size:9px;color:var(--muted)}
.fw-inspector-section{padding:17px 20px;border-bottom:1px solid var(--soft)}.fw-inspector-section h3,.fw-dialog-body section>h3{font-size:9px;text-transform:uppercase;color:var(--muted);margin:0 0 10px}.fw-muted{font-size:10.5px;color:var(--muted);margin:0}
.fw-rationale-item{display:flex;gap:9px;margin-top:8px}.fw-rationale-item>span{font-size:8px;text-transform:uppercase;color:#aebeff;width:50px;flex:none}.fw-rationale-item p{font-size:10.5px;color:var(--dim);margin:0}.fw-requirement{display:grid;grid-template-columns:1fr auto;gap:2px 8px;padding:7px 0;border-top:1px solid var(--soft)}.fw-requirement:first-of-type{border:0}.fw-requirement span{font-size:10.5px}.fw-requirement b{font-size:10px;color:#aebeff}.fw-requirement small{grid-column:1/-1;color:var(--muted);font-size:8px;text-transform:uppercase}
.fw-practices{list-style:none;margin:0;padding:0}.fw-practices li{display:flex;flex-direction:column;padding:7px 0;border-top:1px solid var(--soft)}.fw-practices li:first-child{border:0}.fw-practices b{font-size:10.5px}.fw-practices span{font-size:10px;color:var(--dim)}.fw-control{display:flex;gap:8px;margin-top:8px}.fw-control>span{font-size:8px;text-transform:uppercase;color:var(--amber);width:45px}.fw-control>span.verified{color:var(--green)}.fw-control p{display:flex;flex-direction:column;margin:0}.fw-control b{font-size:10.5px}.fw-control small{font-size:9px;color:var(--muted)}.fw-claim{padding:8px;border-left:2px solid #2dd4bf;background:#0f201d;margin-top:7px}.fw-claim p{font-size:10px;margin:0;color:var(--dim)}.fw-claim small{font-size:8px;color:var(--muted)}
.fw-chat{min-height:100%;display:flex;flex-direction:column;background:#0d1119}.fw-chat-intro{display:flex;flex-direction:column;padding:22px 20px 15px}.fw-chat-intro b{font-size:14px}.fw-chat-intro span{max-width:300px;margin-top:3px;color:var(--muted);font-size:10.5px}.fw-chat-log{flex:1;min-height:110px;overflow:auto;display:flex;flex-direction:column;gap:7px;padding:8px 14px}.fw-message{max-width:92%;padding:8px 10px;border:1px solid var(--line);border-radius:7px;background:#161d27;color:var(--dim);font-size:10.5px}.fw-message.user{align-self:flex-end;background:#173022;border-color:#37dd7d44}
.fw-chat-input{display:flex;gap:6px;padding:10px 12px 12px;border-top:1px solid var(--soft)}.fw-chat-input input{flex:1;min-width:0;border:1px solid var(--line);border-radius:7px;background:var(--bg);color:var(--ink);padding:9px;font:11px inherit}.fw-chat-input button{width:36px;border:0;border-radius:7px;background:var(--green);color:#07130c;display:grid;place-items:center}.fw-chat-input button:disabled,.fw-proposal button:disabled{opacity:.4}
.fw-proposal{margin:5px 12px 8px;padding:10px;border:1px solid #7d9bff55;border-radius:7px;background:#111a29}.fw-proposal label{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:6px;font-size:10px}.fw-proposal label>b{color:#aebeff}.fw-proposal input,.fw-proposal select{width:130px;border:1px solid var(--line);border-radius:5px;background:var(--bg);color:var(--ink);padding:4px;font-size:10px}.fw-proposal>div{display:flex;justify-content:flex-end;gap:5px;margin-top:9px}.fw-proposal button{display:flex;align-items:center;gap:4px;border:1px solid var(--line);border-radius:5px;background:transparent;color:var(--dim);padding:5px 7px;font:600 9px inherit}.fw-proposal button.accept{color:#77e5a5;border-color:#37dd7d66;background:#37dd7d12}
.fw-dialog-scrim{position:fixed;z-index:60;inset:0;display:grid;place-items:center;padding:24px;background:#060a0fdd;backdrop-filter:blur(3px)}.fw-dialog{display:flex;flex-direction:column;width:min(940px,100%);max-height:calc(100vh - 48px);border:1px solid #2a3446;border-radius:8px;background:#10151d;box-shadow:0 30px 80px #000;overflow:hidden}.fw-dialog>header{display:flex;justify-content:space-between;align-items:flex-start;padding:18px 22px;border-bottom:1px solid var(--soft)}.fw-dialog>header span{font-size:9px;text-transform:uppercase;color:var(--green)}.fw-dialog>header h2{font-size:19px;margin:4px 0}.fw-dialog>header small{font-size:9px;color:var(--muted)}.fw-dialog>header button{width:30px;height:30px;border:1px solid var(--line);border-radius:6px;background:#ffffff08;color:var(--dim)}.fw-dialog-body{padding:18px 22px;overflow:auto}.fw-dialog-body section{margin-top:21px}.fw-dialog-copy{font-size:11.5px;color:var(--dim)}
.fw-verdict{display:flex;gap:10px;padding:12px;border:1px solid var(--amber);border-radius:7px;background:#19170f}.fw-verdict.publishable{border-color:var(--green);background:#102018}.fw-verdict p{display:flex;flex-direction:column;margin:0}.fw-verdict b{font-size:12px}.fw-verdict span{font-size:10px;color:var(--dim)}.fw-gates{padding-left:18px;color:#f6c9d1;font-size:10.5px}
.fw-stack{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.fw-stack>div{display:grid;grid-template-columns:110px 1fr;gap:2px 8px;padding:8px;border:1px solid var(--soft);border-radius:6px;background:#ffffff04}.fw-stack span{font-size:8px;text-transform:uppercase;color:var(--muted)}.fw-stack b{font-size:10px}.fw-stack small{grid-column:2;font-size:8px;color:var(--muted)}
.fw-alternatives{border:1px solid var(--soft);border-radius:7px;overflow:hidden}.fw-alternatives details{border-top:1px solid var(--soft)}.fw-alternatives details:first-child{border:0}.fw-alternatives summary{display:grid;grid-template-columns:1fr 50px auto;gap:9px;align-items:center;padding:9px 11px;cursor:pointer}.fw-alternatives summary>span:first-child{display:flex;flex-direction:column}.fw-alternatives summary b{font-size:10.5px}.fw-alternatives summary small{font-size:8px;text-transform:uppercase;color:var(--muted)}.fw-alternatives summary i{font-size:8px;font-style:normal;color:#5eead4;background:#2dd4bf18;padding:2px 5px;border-radius:4px}.fw-score{font:700 10px monospace;color:var(--green)}.fw-alternatives details>div{padding:0 11px 8px}.fw-alternatives details p{display:flex;gap:8px;margin:5px 0;font-size:9.5px;color:var(--dim)}.fw-alternatives details p b{width:65px;text-transform:uppercase;font-size:8px;color:#aebeff}.fw-alternatives details p.finding b{color:var(--red)}
.fw-feasibility{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin-top:10px}.fw-feasibility>div{display:flex;gap:8px;padding:8px;border-left:2px solid var(--muted);background:#ffffff04}.fw-feasibility>div.feasible{border-color:var(--green)}.fw-feasibility>div.rejected{border-color:var(--red)}.fw-feasibility>div>span{width:45px;font-size:7.5px;text-transform:uppercase;color:var(--muted)}.fw-feasibility p{display:flex;flex-direction:column;margin:0}.fw-feasibility b{font-size:9.5px}.fw-feasibility small{font-size:8px;color:var(--muted)}
.fw-sensitivity{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.fw-sensitivity>div{display:flex;flex-direction:column;padding:8px;border:1px solid var(--soft);border-radius:6px}.fw-sensitivity b{font-size:9.5px;text-transform:capitalize}.fw-sensitivity span{font-size:8.5px;color:var(--muted)}
.fw-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}.fw-metrics>div{display:flex;flex-direction:column;padding:9px;border:1px solid var(--soft);border-radius:6px}.fw-metrics span{font-size:8px;text-transform:uppercase;color:var(--muted)}.fw-metrics b{font-size:11px}.fw-warning{padding:7px 9px;border-left:2px solid var(--amber);font-size:9px;color:var(--dim)}.fw-outcomes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px}.fw-outcomes>div{display:flex;flex-direction:column}.fw-outcomes b{font-size:9.5px}.fw-outcomes span{font-size:8.5px;color:var(--muted)}
.fw-roadmap{display:flex;flex-direction:column;gap:5px}.fw-roadmap>div{display:flex;gap:9px;padding:8px;border:1px solid var(--soft);border-radius:6px}.fw-roadmap>div>span{width:22px;height:22px;display:grid;place-items:center;border-radius:50%;background:#37dd7d18;color:var(--green);font-size:9px}.fw-roadmap p{display:flex;flex-direction:column;margin:0}.fw-roadmap b{font-size:10px}.fw-roadmap small{font-size:8.5px;color:var(--muted)}
.fw-trace-panel{display:flex;flex-direction:column;gap:0}.fw-trace-panel-header{padding:16px 18px 10px;border-bottom:1px solid var(--soft)}.fw-trace-panel-header b{display:block;font-size:12px;margin-bottom:2px}.fw-trace-panel-header span{font-size:9px;color:var(--muted)}
.fw-trace-history-label{padding:10px 18px 6px;font-size:8.5px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.fw-trace-history{border-bottom:1px solid var(--soft)}.fw-trace-history-item{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:6px 18px;border-bottom:1px solid #ffffff08}.fw-trace-history-changes{display:flex;flex-wrap:wrap;gap:4px;flex:1;min-width:0}.fw-trace-change{font-size:9px;padding:2px 6px;border-radius:4px;background:#ffffff0a;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:180px}.fw-trace-history-delta{display:flex;gap:4px;flex-shrink:0}.fw-trace-history-delta .added{font-size:9px;color:var(--green)}.fw-trace-history-delta .removed{font-size:9px;color:var(--red)}.fw-trace-history-delta .unchanged{font-size:9px;color:var(--muted)}
.fw-trace-rules{padding:0 0 18px}.fw-trace-rules .fw-trace{padding:0 18px;gap:5px}.fw-trace-empty{padding:4px 0}
.fw-trace{display:flex;flex-direction:column;gap:5px}.fw-trace>div{display:grid;grid-template-columns:55px 1fr 55px;gap:8px;padding:7px 8px;border-left:2px solid #7d9bff;background:#ffffff04}.fw-trace>div>span{font-size:7.5px;text-transform:uppercase;color:#aebeff}.fw-trace p{display:flex;flex-direction:column;margin:0;font-size:9px;color:var(--dim)}.fw-trace p b{font-size:8.5px;text-transform:capitalize;color:var(--ink)}.fw-trace small{font-size:8px;color:var(--muted);text-align:right}
.fw-dialog>footer{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:12px 18px;border-top:1px solid var(--soft);background:#0c1016}.fw-dialog>footer p{display:flex;align-items:center;gap:7px;flex:1;min-width:240px;margin:0;font-size:8.5px;color:var(--muted)}.fw-dialog>footer button{display:flex;align-items:center;gap:6px;border:0;border-radius:6px;background:var(--green);color:#07130c;padding:7px 10px;font:700 9.5px inherit}.fw-dialog>footer button.secondary{border:1px solid var(--line);background:transparent;color:var(--dim)}.fw-dialog>footer button:disabled{opacity:.4}.fw-dialog>footer>span{width:100%;font-size:9px;color:var(--red);text-align:right}.fw-dialog>footer>span.success{color:var(--green);font-family:monospace;overflow-wrap:anywhere}
@media(max-width:980px){.fw-brand p{max-width:230px}.fw-aside{width:360px}.fw-connection{display:none}.fw-stack{grid-template-columns:1fr}.fw-metrics{grid-template-columns:repeat(2,1fr)}}
@media(max-width:760px){.fw-head{padding:9px 10px;flex-wrap:wrap}.fw-brand{width:calc(100% - 120px)}.fw-brand p{max-width:220px}.fw-segment{order:3;margin-left:0}.fw-package-button{margin-left:auto}.fw-journey{padding:0 5px}.fw-step{padding:6px 4px}.fw-step small{display:none}.fw-main{flex-direction:column}.fw-canvas-wrap{height:43%;flex:none}.fw-aside{width:100%;flex:1;border-left:0;border-top:1px solid var(--soft)}.fw-dialog-scrim{padding:8px}.fw-dialog{max-height:calc(100vh - 16px)}.fw-dialog-body{padding:14px}.fw-feasibility,.fw-sensitivity,.fw-outcomes{grid-template-columns:1fr}}
    `}</style>
  );
}
