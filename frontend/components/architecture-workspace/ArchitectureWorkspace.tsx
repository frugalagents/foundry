'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  ArrowRight,
  Blocks,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  Coins,
  Download,
  FileText,
  GitBranch,
  Layers3,
  ListChecks,
  Map,
  Plus,
  Scale,
  ShieldCheck,
  Sparkles,
  Target,
  XCircle,
} from 'lucide-react';
import type {
  AnswerImpact,
  ArchitectureComponent,
  ArchitectureWorkspaceProjection,
  DeployableCandidate,
  DeployableSelection,
  FeasibilityStatus,
  NumericRange,
  RequirementValue,
} from '@/lib/architecture-workspace';
import { PlatformCanvas } from './PlatformCanvas';
import { buildStrategyDocument } from '@/lib/strategy-document';

interface ArchitectureWorkspaceProps {
  projection: ArchitectureWorkspaceProjection;
  onApplyAnswer?: (requirementId: string, answer: RequirementValue) => Promise<void>;
  applying?: boolean;
  offline?: boolean;
}

type CanvasMode = 'logical' | 'deployable';
type InspectorTab =
  | 'fit'
  | 'requirements'
  | 'matrix'
  | 'security'
  | 'economics'
  | 'outcomes'
  | 'roadmap'
  | 'trace';


const feasibilityStyles: Record<FeasibilityStatus, {
  icon: typeof CheckCircle2;
  iconClass: string;
  label: string;
}> = {
  feasible: { icon: CheckCircle2, iconClass: 'text-[#277256]', label: 'Feasible' },
  rejected: { icon: XCircle, iconClass: 'text-[#a64539]', label: 'Rejected' },
  unknown: { icon: CircleHelp, iconClass: 'text-[#a06d16]', label: 'Needs input' },
};

const inspectorTabs: {
  id: InspectorTab;
  label: string;
  icon: typeof ListChecks;
}[] = [
  { id: 'fit', label: 'Fit', icon: ListChecks },
  { id: 'requirements', label: 'Requirements / Assumptions', icon: ClipboardList },
  { id: 'matrix', label: 'Decision Matrix', icon: Scale },
  { id: 'security', label: 'Security / Best Practices', icon: ShieldCheck },
  { id: 'economics', label: 'Economics / Tokenomics', icon: Coins },
  { id: 'outcomes', label: 'Outcomes', icon: Target },
  { id: 'roadmap', label: 'Roadmap', icon: Map },
  { id: 'trace', label: 'Revision Trace', icon: GitBranch },
];

function displayId(id: string) {
  const value = id.split(':').at(-1) ?? id;
  return value
    .split('-')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function answerLabel(answer: RequirementValue) {
  if (answer === true) return 'Yes';
  if (answer === false) return 'No';
  if (answer === null) return 'Not sure';
  return String(answer);
}

function formatRange(range: NumericRange, options?: Intl.NumberFormatOptions) {
  const formatter = new Intl.NumberFormat('en-US', options);
  return `${formatter.format(range.low)} - ${formatter.format(range.high)}`;
}

function EmptyArtifact({ message }: { message: string }) {
  return (
    <div className="px-5 py-8 text-center text-[11px] leading-5 text-[#78817f] sm:px-6">
      {message}
    </div>
  );
}

function ServiceTile({
  component,
  selection,
}: {
  component: ArchitectureComponent;
  selection?: DeployableSelection;
}) {
  return (
    <article className="min-h-[116px] rounded-[7px] border border-[#d9e1df] bg-white px-3.5 py-3">
      <div className="mb-2 flex min-h-5 items-start justify-between gap-2">
        <span className="text-[10px] font-semibold uppercase text-[#65706d]">
          {selection?.provider_class ?? 'unmapped'}
        </span>
        {selection && (
          <span className="max-w-[55%] truncate rounded-[5px] bg-[#edf3f1] px-1.5 py-0.5 text-[9px] font-medium text-[#4e5c58]">
            {selection.delivery_model}
          </span>
        )}
      </div>
      <h3 className="text-[13px] font-semibold leading-[1.35] text-[#182220]">
        {selection?.service_name ?? 'Service selection pending'}
      </h3>
      <p className="mt-1.5 text-[11px] leading-[1.45] text-[#68716f]">
        Implements {component.name}
      </p>
      {selection && (
        <p className="mt-2 truncate font-mono text-[9px] text-[#929a98]" title={selection.service_variant_id}>
          {selection.service_variant_id}
        </p>
      )}
    </article>
  );
}

function AnswerImpactSummary({ impact }: { impact: AnswerImpact }) {
  const changes = [
    { label: 'Components', value: impact.added_component_ids.length, icon: Plus },
    { label: 'Feasible', value: impact.feasible_pattern_ids.length, icon: CheckCircle2 },
    { label: 'Rejected', value: impact.rejected_pattern_ids.length, icon: XCircle },
    { label: 'Unknown', value: impact.unknown_pattern_ids.length, icon: CircleHelp },
  ];

  return (
    <div className="mt-4 border-t border-[#e2e7e5] pt-4">
      <div className="grid grid-cols-4 gap-2">
        {changes.map(({ label, value, icon: Icon }) => (
          <div key={label} className="min-w-0">
            <div className="flex items-center gap-1 text-[#6e7775]">
              <Icon size={12} />
              <span className="truncate text-[10px]">{label}</span>
            </div>
            <div className="mt-1 text-[17px] font-semibold tabular-nums text-[#1d2826]">
              {value}
            </div>
          </div>
        ))}
      </div>

      {impact.added_component_ids.length > 0 && (
        <div className="mt-3 rounded-[6px] border border-[#b7d8d2] bg-[#f4faf8] px-3 py-2.5">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[#276b61]">
            <Sparkles size={12} />
            Architecture change
          </div>
          <p className="mt-1 text-[11px] leading-5 text-[#53615e]">
            Add {impact.added_component_ids.map(displayId).join(', ')}.
          </p>
        </div>
      )}

      {impact.unknown_pattern_ids.length > 0 && (
        <p className="mt-3 flex items-start gap-2 text-[11px] leading-5 text-[#7b5b21]">
          <AlertCircle size={13} className="mt-0.5 shrink-0" />
          {impact.unknown_pattern_ids.map(displayId).join(', ')} remains unresolved.
        </p>
      )}
    </div>
  );
}

function CandidateStatus({ candidate }: { candidate: DeployableCandidate }) {
  const statusClass = candidate.compatibility_status === 'compatible'
    ? 'text-[#277256]'
    : candidate.compatibility_status === 'conditional'
      ? 'text-[#946519]'
      : 'text-[#a64539]';

  return (
    <span className={`text-[9px] font-semibold uppercase ${statusClass}`}>
      {candidate.compatibility_status}
    </span>
  );
}

export function ArchitectureWorkspace({
  projection,
  onApplyAnswer,
  applying = false,
  offline = false,
}: ArchitectureWorkspaceProps) {
  const [canvasMode, setCanvasMode] = useState<CanvasMode>('logical');
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('fit');
  const [selectedAnswerIndex, setSelectedAnswerIndex] = useState(0);

  const question = projection.next_question;
  const selectedImpact = question?.answer_impacts[selectedAnswerIndex] ?? null;
  const deployable = projection.deployable_solution;
  const assurance = projection.assurance;
  const recommendedCandidate = useMemo(
    () => deployable?.candidates.find(
      (candidate) => candidate.bundle_id === deployable.recommendation.candidate_id,
    ) ?? deployable?.candidates.find((candidate) => candidate.rank === 1),
    [deployable],
  );
  const selectionsByComponent = useMemo(
    () => Object.fromEntries(
      (recommendedCandidate?.selections ?? []).map((selection) => [
        selection.component_id,
        selection,
      ]),
    ) as Record<string, DeployableSelection>,
    [recommendedCandidate],
  );

  const answeredRequirements = projection.requirements.filter(
    (requirement) => requirement.status === 'answered',
  ).length;
  const assumedRequirements = projection.requirements.filter(
    (requirement) => requirement.status === 'assumed',
  ).length;
  const unresolvedRequirements = projection.requirements.filter(
    (requirement) => requirement.status === 'unknown' || requirement.status === 'unanswered',
  ).length;

  useEffect(() => {
    setSelectedAnswerIndex(0);
  }, [question?.requirement_id]);

  const slug = `platform-advisor-${projection.meta.workspace_id.replace(/[^a-zA-Z0-9_-]/g, '-')}-r${projection.meta.revision_number}`;

  const downloadBlob = (content: string, type: string, extension: string) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${slug}.${extension}`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  const downloadDecisionPackage = () =>
    downloadBlob(JSON.stringify(projection, null, 2), 'application/json', 'json');

  const downloadStrategyDocument = () =>
    downloadBlob(buildStrategyDocument(projection), 'text/markdown', 'md');

  return (
    <div className="min-h-full bg-[#f6f8f7] text-[#182220]" style={{ letterSpacing: 0 }}>
      <main className="grid min-h-full grid-cols-1 xl:grid-cols-[minmax(0,1fr)_420px]">
        <section className="min-w-0 px-4 py-5 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-[1500px]">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-x-5 gap-y-2 border-b border-[#dfe4e3] pb-3 text-[11px] text-[#68716f]">
              <div className="min-w-0">
                <span className="font-semibold text-[#26312f]">{projection.meta.workspace_name}</span>
                <span className="mx-2 text-[#aab1af]">/</span>
                <span className={offline ? 'text-[#946519]' : 'text-[#277256]'}>
                  {offline ? 'Snapshot mode' : 'Live engine'}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span>Revision {projection.meta.revision_number}</span>
                <span className="font-mono text-[10px]">Catalog {projection.meta.catalog_version}</span>
                <button
                  type="button"
                  onClick={downloadStrategyDocument}
                  title="Download tech-strategy document (Markdown)"
                  aria-label="Download tech-strategy document"
                  className="inline-flex size-8 items-center justify-center rounded-[6px] border border-[#d5ddda] bg-white text-[#53605d] hover:border-[#9db8b2] hover:text-[#225f57]"
                >
                  <FileText size={15} />
                </button>
                <button
                  type="button"
                  onClick={downloadDecisionPackage}
                  title="Download decision package JSON"
                  aria-label="Download decision package JSON"
                  className="inline-flex size-8 items-center justify-center rounded-[6px] border border-[#d5ddda] bg-white text-[#53605d] hover:border-[#9db8b2] hover:text-[#225f57]"
                >
                  <Download size={15} />
                </button>
              </div>
            </div>

            <div className="flex flex-wrap items-end justify-between gap-4 pb-5">
              <div>
                <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase text-[#64706d]">
                  <Layers3 size={14} />
                  Architecture
                </div>
                <h1 className="text-[24px] font-semibold leading-tight text-[#17201f]">
                  Coding agent platform
                </h1>
                <p className="mt-1.5 max-w-2xl text-[12px] leading-5 text-[#68716f]">
                  One logical baseline refined into a requirement-specific deployable solution.
                </p>
              </div>

              <div
                className="inline-flex rounded-[7px] border border-[#d4dcda] bg-white p-1"
                role="group"
                aria-label="Architecture canvas mode"
              >
                {(['logical', 'deployable'] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setCanvasMode(mode)}
                    disabled={mode === 'deployable' && !recommendedCandidate}
                    aria-pressed={canvasMode === mode}
                    className={`min-h-8 rounded-[5px] px-3 text-[11px] font-semibold capitalize ${
                      canvasMode === mode
                        ? 'bg-[#276b61] text-white'
                        : 'text-[#5f6b68] hover:bg-[#f2f5f4] disabled:cursor-not-allowed disabled:text-[#a9b0ae]'
                    }`}
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-[#68716f]">
              <span className="inline-flex items-center gap-1.5">
                <Blocks size={13} />
                <strong className="font-semibold text-[#26312f]">
                  {canvasMode === 'logical'
                    ? projection.architecture.component_count
                    : recommendedCandidate?.selections.length ?? 0}
                </strong>
                {canvasMode === 'logical' ? 'components' : 'service selections'}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <GitBranch size={13} />
                <strong className="font-semibold text-[#26312f]">{projection.architecture.edge_count}</strong>
                dependencies
              </span>
              <span className="inline-flex items-center gap-1.5">
                <ListChecks size={13} />
                <strong className="font-semibold text-[#26312f]">{answeredRequirements}</strong> answered
                <span className="text-[#946519]">/ {assumedRequirements} assumed</span>
                <span>/ {unresolvedRequirements} unresolved</span>
              </span>
            </div>

            {canvasMode === 'deployable' && (
            <div className="overflow-hidden border-y border-[#dce2e0]">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e2e7e5] bg-[#fafbfb] px-4 py-3">
                {recommendedCandidate ? (
                  <>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 size={15} className="shrink-0 text-[#277256]" />
                        <span className="truncate text-[11px] font-semibold text-[#33403d]">
                          {recommendedCandidate.name}
                        </span>
                      </div>
                      <p className="mt-1 max-w-3xl text-[10px] leading-4 text-[#737d7a]">
                        {deployable?.recommendation.rationale}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-3 text-[10px]">
                      <CandidateStatus candidate={recommendedCandidate} />
                      <span className="font-semibold tabular-nums text-[#33403d]">
                        {recommendedCandidate.weighted_score.toFixed(1)} / 100
                      </span>
                    </div>
                  </>
                ) : null}
              </div>

              {projection.architecture.planes.map((plane, index) => (
                  <section
                    key={plane.id}
                    className={`grid gap-3 px-3 py-3 sm:px-4 md:grid-cols-[112px_minmax(0,1fr)] md:gap-4 ${
                      index > 0 ? 'border-t border-[#e7ebe9]' : ''
                    }`}
                    aria-labelledby={`plane-${plane.id}`}
                  >
                    <div className="flex items-center justify-between md:block">
                      <h2 id={`plane-${plane.id}`} className="pt-1 text-[11px] font-semibold uppercase text-[#56615f]">
                        {plane.label}
                      </h2>
                      <span className="text-[10px] tabular-nums text-[#9aa19f] md:mt-1 md:block">
                        {plane.components.length} services
                      </span>
                    </div>
                    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,190px),1fr))] gap-2.5">
                      {plane.components.map((component) => (
                        <ServiceTile
                          key={component.id}
                          component={component}
                          selection={selectionsByComponent[component.id]}
                        />
                      ))}
                    </div>
                  </section>
                ))}
            </div>
            )}

            {canvasMode === 'logical' && <PlatformCanvas projection={projection} />}
          </div>
        </section>

        <aside className="border-t border-[#dce2e0] bg-white xl:border-l xl:border-t-0">
          <div className="xl:sticky xl:top-0 xl:max-h-screen xl:overflow-y-auto">
            <section className="px-5 py-5 sm:px-6">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <CircleHelp size={16} className="text-[#276b61]" />
                  <h2 className="text-[13px] font-semibold">Next decision</h2>
                </div>
                {question && (
                  <span className="max-w-[50%] truncate text-right font-mono text-[9px] text-[#919997]">
                    {displayId(question.requirement_id)}
                  </span>
                )}
              </div>

              {question ? (
                <>
                  <p className="mt-4 text-[17px] font-semibold leading-[1.4] text-[#1b2624]">
                    {question.prompt}
                  </p>
                  <p className="mt-2 text-[11px] leading-5 text-[#68716f]">{question.why_now}</p>

                  <div className="mt-4 grid grid-cols-3 gap-2" role="group" aria-label="Candidate answers">
                    {question.candidate_answers.map((answer, index) => {
                      const selected = selectedAnswerIndex === index;
                      return (
                        <button
                          key={`${String(answer)}-${index}`}
                          type="button"
                          onClick={() => setSelectedAnswerIndex(index)}
                          aria-pressed={selected}
                          className={`flex min-h-10 items-center justify-center gap-1.5 rounded-[6px] border px-2 text-[11px] font-semibold transition-colors ${
                            selected
                              ? 'border-[#276b61] bg-[#276b61] text-white'
                              : 'border-[#d9dfdd] bg-white text-[#4d5956] hover:border-[#9cb7b1] hover:bg-[#f5f8f7]'
                          }`}
                        >
                          {selected && <Check size={13} strokeWidth={2.5} />}
                          {answerLabel(answer)}
                        </button>
                      );
                    })}
                  </div>

                  {selectedImpact && <AnswerImpactSummary impact={selectedImpact} />}

                  <button
                    type="button"
                    disabled={!onApplyAnswer || applying || !selectedImpact}
                    onClick={() => selectedImpact && onApplyAnswer?.(question.requirement_id, selectedImpact.answer)}
                    className="mt-4 flex min-h-10 w-full items-center justify-center gap-2 rounded-[6px] bg-[#276b61] px-4 text-[11px] font-semibold text-white transition-colors hover:bg-[#1f5b53] disabled:cursor-not-allowed disabled:bg-[#dfe5e3] disabled:text-[#7d8784]"
                  >
                    {applying ? 'Recomputing architecture...' : 'Apply to architecture'}
                    <ArrowRight size={14} />
                  </button>
                </>
              ) : (
                <p className="mt-4 text-[12px] text-[#68716f]">No unresolved architecture decisions.</p>
              )}
            </section>

            <section className="border-t border-[#e2e7e5]">
              <div className="overflow-x-auto border-b border-[#e2e7e5]">
                <div className="flex min-w-max" role="tablist" aria-label="Decision package views">
                  {inspectorTabs.map(({ id, label, icon: Icon }) => (
                    <button
                      key={id}
                      type="button"
                      role="tab"
                      aria-selected={inspectorTab === id}
                      onClick={() => setInspectorTab(id)}
                      className={`flex min-h-11 items-center justify-center gap-1.5 whitespace-nowrap border-b-2 px-3 text-[10px] font-semibold ${
                        inspectorTab === id
                          ? 'border-[#276b61] text-[#225f57]'
                          : 'border-transparent text-[#77807e] hover:bg-[#f7f9f8]'
                      }`}
                    >
                      <Icon size={13} />
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {inspectorTab === 'fit' && (
                <div role="tabpanel">
                  {projection.feasibility.map((family) => {
                    const status = feasibilityStyles[family.status];
                    const StatusIcon = status.icon;
                    const reasonIds = family.status === 'rejected'
                      ? family.rejection_rule_ids
                      : family.blocking_requirement_ids;
                    return (
                      <div key={family.pattern_id} className="flex items-start gap-3 border-b border-[#edf0ef] px-5 py-3.5 last:border-b-0 sm:px-6">
                        <StatusIcon size={16} className={`mt-0.5 shrink-0 ${status.iconClass}`} />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-start justify-between gap-3">
                            <h3 className="text-[12px] font-semibold leading-[1.45] text-[#293330]">{family.name}</h3>
                            <span className={`shrink-0 text-[10px] font-semibold ${status.iconClass}`}>{status.label}</span>
                          </div>
                          {reasonIds.length > 0 && (
                            <p className="mt-1 text-[10px] leading-4 text-[#7d8684]">
                              {family.status === 'rejected' ? 'Excluded by ' : 'Waiting on '}
                              {reasonIds.map(displayId).join(', ')}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {inspectorTab === 'requirements' && (
                <div role="tabpanel">
                  {projection.requirements.map((requirement) => {
                    const statusLabel = requirement.status === 'answered'
                      ? 'Answered'
                      : requirement.status === 'assumed'
                        ? 'Assumption'
                        : requirement.status === 'unknown'
                          ? 'Not sure'
                          : 'Unanswered';
                    const statusClass = requirement.status === 'answered'
                      ? 'text-[#277256]'
                      : requirement.status === 'assumed'
                        ? 'text-[#8a641e]'
                        : requirement.status === 'unknown'
                          ? 'text-[#946519]'
                          : 'text-[#7b8381]';
                    return (
                      <div key={requirement.id} className="border-b border-[#edf0ef] px-5 py-3.5 last:border-b-0 sm:px-6">
                        <div className="flex items-start justify-between gap-3">
                          <h3 className="text-[11px] font-semibold leading-[1.45] text-[#293330]">{requirement.name}</h3>
                          <span className={`shrink-0 text-[9px] font-semibold uppercase ${statusClass}`}>{statusLabel}</span>
                        </div>
                        <p className="mt-1 break-words font-mono text-[10px] leading-4 text-[#687370]">
                          {requirement.status === 'unknown'
                            ? 'Not sure'
                            : requirement.status === 'unanswered'
                              ? 'Not provided'
                              : answerLabel(requirement.value)}
                        </p>
                        {requirement.assumption && (
                          <div className="mt-2 border-l-2 border-[#d4b36d] pl-2 text-[10px] leading-4 text-[#68716f]">
                            <p>{requirement.assumption.rationale}</p>
                            <p className="mt-1 text-[#8a9290]">
                              {Math.round(requirement.assumption.confidence * 100)}% confidence
                              {' / '}{requirement.assumption.owner}
                              {' / '}{requirement.assumption.source}
                            </p>
                          </div>
                        )}
                        {!requirement.assumption && requirement.source && (
                          <p className="mt-1 text-[9px] leading-4 text-[#919997]">Source: {requirement.source}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {inspectorTab === 'matrix' && (
                <div role="tabpanel">
                  {!deployable ? (
                    <EmptyArtifact message="Deployable decision matrix is not available for this revision." />
                  ) : (
                    <>
                      <div className="border-b border-[#e5eae8] bg-[#f8faf9] px-5 py-3 sm:px-6">
                        <p className="text-[10px] font-semibold uppercase text-[#65706d]">
                          {displayId(deployable.recommendation.state)}
                        </p>
                        <p className="mt-1 text-[11px] leading-5 text-[#4e5956]">{deployable.recommendation.rationale}</p>
                      </div>
                      {deployable.candidates
                        .slice()
                        .sort((left, right) => left.rank - right.rank)
                        .map((candidate) => (
                          <div key={candidate.bundle_id} className="border-b border-[#edf0ef] px-5 py-3.5 last:border-b-0 sm:px-6">
                            <div className="flex items-start gap-3">
                              <span className="flex size-6 shrink-0 items-center justify-center rounded-[6px] border border-[#d7dfdc] bg-[#f8faf9] text-[10px] font-semibold tabular-nums">
                                {candidate.rank}
                              </span>
                              <div className="min-w-0 flex-1">
                                <div className="flex items-start justify-between gap-2">
                                  <h3 className="text-[11px] font-semibold leading-4 text-[#293330]">{candidate.name}</h3>
                                  <CandidateStatus candidate={candidate} />
                                </div>
                                <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[9px] text-[#737d7a]">
                                  <span>{candidate.weighted_score.toFixed(1)} / 100</span>
                                  <span>{candidate.selections.length} services</span>
                                  {candidate.pareto_optimal && <span className="font-semibold text-[#276b61]">Pareto optimal</span>}
                                </div>
                                {candidate.tradeoffs.length > 0 && (
                                  <p className="mt-2 text-[10px] leading-4 text-[#68716f]">
                                    {candidate.tradeoffs.slice(0, 2).map((tradeoff) => tradeoff.statement).join(' ')}
                                  </p>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      {deployable.sensitivity.some((item) => item.winner_changes) && (
                        <div className="border-t border-[#e5eae8] bg-[#fffbf1] px-5 py-3 text-[10px] leading-4 text-[#745b28] sm:px-6">
                          Recommendation changes under sensitivity testing for{' '}
                          {deployable.sensitivity
                            .filter((item) => item.winner_changes)
                            .map((item) => displayId(item.dimension_id))
                            .join(', ')}.
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {inspectorTab === 'security' && (
                <div role="tabpanel">
                  {!assurance ? (
                    <EmptyArtifact message="Security and best-practice assurance is not available for this revision." />
                  ) : (
                    <>
                      <div className="grid grid-cols-3 border-b border-[#e5eae8] bg-[#f8faf9]">
                        {[
                          ['Residual risk', assurance.security.residual_risk_total],
                          ['High / critical', assurance.security.high_or_critical_residual_count],
                          ['Verified controls', assurance.security.verified_control_count],
                        ].map(([label, value]) => (
                          <div key={label} className="border-r border-[#e5eae8] px-2 py-3 text-center last:border-r-0">
                            <p className="text-[16px] font-semibold tabular-nums text-[#26312f]">{value}</p>
                            <p className="mt-1 text-[9px] text-[#727c79]">{label}</p>
                          </div>
                        ))}
                      </div>
                      <div className="px-5 pb-2 pt-4 text-[10px] font-semibold uppercase text-[#65706d] sm:px-6">Threats</div>
                      {assurance.security.threats.map((threat) => (
                        <div key={threat.threat_id} className="border-b border-[#edf0ef] px-5 py-3 sm:px-6">
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="text-[11px] font-semibold leading-4 text-[#293330]">{threat.title}</h3>
                            <span className={`text-[9px] font-semibold uppercase ${
                              threat.residual_rating === 'critical' || threat.residual_rating === 'high'
                                ? 'text-[#a64539]'
                                : threat.residual_rating === 'moderate'
                                  ? 'text-[#946519]'
                                  : 'text-[#277256]'
                            }`}>
                              {threat.residual_rating} {threat.residual_score}
                            </span>
                          </div>
                          <p className="mt-1 text-[9px] text-[#7b8582]">
                            Controls: {threat.required_control_ids.map(displayId).join(', ')}
                          </p>
                        </div>
                      ))}
                      <div className="px-5 pb-2 pt-4 text-[10px] font-semibold uppercase text-[#65706d] sm:px-6">Controls and verification</div>
                      {assurance.security.controls.map((control) => (
                        <div key={control.control_id} className="border-b border-[#edf0ef] px-5 py-3 sm:px-6">
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="text-[11px] font-semibold leading-4 text-[#293330]">{control.title}</h3>
                            <span className={`text-[9px] font-semibold uppercase ${
                              control.status === 'verified'
                                ? 'text-[#277256]'
                                : control.status === 'failed'
                                  ? 'text-[#a64539]'
                                  : 'text-[#946519]'
                            }`}>
                              {control.status}
                            </span>
                          </div>
                          <p className="mt-1 text-[10px] leading-4 text-[#68716f]">
                            {control.verification.method}
                          </p>
                          <p className="mt-1 text-[9px] leading-4 text-[#919997]">
                            Accept: {control.verification.acceptance_criteria}
                          </p>
                        </div>
                      ))}
                      <div className="px-5 pb-2 pt-4 text-[10px] font-semibold uppercase text-[#65706d] sm:px-6">Best practices</div>
                      {assurance.security.best_practices.map((practice) => (
                        <div key={practice.practice_id} className="border-b border-[#edf0ef] px-5 py-3 last:border-b-0 sm:px-6">
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="text-[11px] font-semibold leading-4 text-[#293330]">{practice.title}</h3>
                            <span className="text-[9px] font-semibold uppercase text-[#687370]">{practice.status}</span>
                          </div>
                          <p className="mt-1 text-[10px] leading-4 text-[#68716f]">{practice.implementation}</p>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              )}

              {inspectorTab === 'economics' && (
                <div role="tabpanel">
                  {!assurance ? (
                    <EmptyArtifact message="Economics and tokenomics are not available for this revision." />
                  ) : (
                    <>
                      {[
                        ['Cost / requested task', assurance.economics.totals.cost_per_requested_task],
                        ['Cost / successful task', assurance.economics.totals.cost_per_successful_task],
                        ['Cost / accepted PR', assurance.economics.totals.cost_per_accepted_pull_request],
                        ['Monthly platform cost', assurance.economics.totals.monthly_platform_cost],
                        ['Monthly cost / developer', assurance.economics.totals.monthly_cost_per_developer],
                      ].map(([label, range]) => (
                        <div key={label as string} className="flex items-center justify-between gap-4 border-b border-[#edf0ef] px-5 py-3.5 sm:px-6">
                          <span className="text-[11px] text-[#4f5a57]">{label as string}</span>
                          <strong className="text-right text-[11px] tabular-nums text-[#26312f]">
                            {formatRange(range as NumericRange, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 })}
                          </strong>
                        </div>
                      ))}
                      <div className="px-5 py-4 sm:px-6">
                        <h3 className="text-[10px] font-semibold uppercase text-[#65706d]">Sensitivity drivers</h3>
                        <ul className="mt-2 space-y-1.5">
                          {assurance.economics.sensitivity_drivers.map((driver) => (
                            <li key={driver} className="flex items-start gap-2 text-[10px] leading-4 text-[#68716f]">
                              <ChevronRight size={11} className="mt-0.5 shrink-0 text-[#8a9491]" />
                              {driver}
                            </li>
                          ))}
                        </ul>
                        <p className="mt-3 border-l-2 border-[#d4b36d] pl-2 text-[9px] leading-4 text-[#817047]">
                          {assurance.economics.pricing_warning}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              )}

              {inspectorTab === 'outcomes' && (
                <div role="tabpanel">
                  {!assurance ? (
                    <EmptyArtifact message="Outcome observability is not available for this revision." />
                  ) : (
                    <>
                      <div className="border-b border-[#e5eae8] bg-[#f8faf9] px-5 py-3 sm:px-6">
                        <p className="text-[9px] font-semibold uppercase text-[#65706d]">Correlation path</p>
                        <p className="mt-1 break-words font-mono text-[9px] leading-4 text-[#5b6764]">
                          {assurance.outcomes.join_path.join(' -> ')}
                        </p>
                      </div>
                      {assurance.outcomes.metrics.map((metric) => (
                        <div key={metric.metric_id} className="border-b border-[#edf0ef] px-5 py-3.5 sm:px-6">
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="text-[11px] font-semibold leading-4 text-[#293330]">{metric.name}</h3>
                            <span className="text-[9px] text-[#7b8582]">{metric.unit}</span>
                          </div>
                          <p className="mt-1 font-mono text-[9px] leading-4 text-[#68716f]">{metric.formula}</p>
                          <p className="mt-1 text-[9px] text-[#919997]">Denominator: {metric.denominator}</p>
                        </div>
                      ))}
                      <div className="grid grid-cols-2 gap-px bg-[#e5eae8]">
                        {assurance.outcomes.measurement_horizons.map((horizon) => (
                          <div key={horizon.horizon} className="bg-white px-4 py-3">
                            <h3 className="text-[10px] font-semibold uppercase text-[#276b61]">{displayId(horizon.horizon)}</h3>
                            <p className="mt-1 text-[10px] leading-4 text-[#68716f]">{horizon.objective}</p>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}

              {inspectorTab === 'roadmap' && (
                <div role="tabpanel">
                  {!assurance ? (
                    <EmptyArtifact message="Implementation roadmap is not available for this revision." />
                  ) : (
                    <>
                      <div className="flex items-center justify-between border-b border-[#e5eae8] bg-[#f8faf9] px-5 py-3 text-[10px] sm:px-6">
                        <span className="text-[#65706d]">Total effort</span>
                        <strong className="tabular-nums text-[#26312f]">
                          {formatRange(assurance.roadmap.total_effort_person_days)} person-days
                        </strong>
                      </div>
                      {assurance.roadmap.phases
                        .slice()
                        .sort((left, right) => left.sequence - right.sequence)
                        .map((phase) => (
                          <div key={phase.phase_id} className="border-b border-[#edf0ef] px-5 py-4 last:border-b-0 sm:px-6">
                            <div className="flex items-start gap-3">
                              <span className="flex size-6 shrink-0 items-center justify-center rounded-[6px] bg-[#276b61] text-[10px] font-semibold text-white">
                                {phase.sequence}
                              </span>
                              <div className="min-w-0 flex-1">
                                <h3 className="text-[11px] font-semibold text-[#293330]">{phase.name}</h3>
                                <div className="mt-2 space-y-2">
                                  {phase.work_packages.map((workPackage) => (
                                    <div key={workPackage.package_id} className="text-[10px] leading-4 text-[#68716f]">
                                      <div className="flex items-start justify-between gap-2">
                                        <span>{workPackage.title}</span>
                                        <span className="shrink-0 tabular-nums text-[#8a9290]">
                                          {formatRange(workPackage.effort_person_days)}d
                                        </span>
                                      </div>
                                      <span className="text-[9px] text-[#929a98]">{workPackage.owner}</span>
                                    </div>
                                  ))}
                                </div>
                                <p className="mt-2 text-[9px] leading-4 text-[#7b8582]">
                                  Exit: {phase.exit_criteria.join('; ')}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                    </>
                  )}
                </div>
              )}

              {inspectorTab === 'trace' && (
                <div role="tabpanel">
                  {projection.decision_history?.transitions.map((transition) => (
                    <div key={transition.transition_id} className="border-b border-[#dfe5e3] bg-[#f8faf9] px-5 py-3.5 sm:px-6">
                      <p className="font-mono text-[9px] text-[#687370]">{displayId(transition.transition_id)}</p>
                      <p className="mt-1 text-[10px] leading-4 text-[#4e5956]">
                        {transition.requirement_changes.length} requirement changes;{' '}
                        {transition.architecture_delta.components.added.length} components added;{' '}
                        {transition.architecture_delta.components.removed.length} removed.
                      </p>
                      {transition.requirement_changes.length > 0 && (
                        <p className="mt-1 text-[9px] leading-4 text-[#858e8b]">
                          {transition.requirement_changes
                            .map((change) => `${change.name} (${change.change_type})`)
                            .join(', ')}
                        </p>
                      )}
                    </div>
                  ))}
                  {projection.decision_trace.map((decision, index) => (
                    <div key={decision.evaluation_id} className="grid grid-cols-[24px_minmax(0,1fr)] gap-2.5 border-b border-[#edf0ef] px-5 py-3.5 last:border-b-0 sm:px-6">
                      <div className="flex size-6 items-center justify-center rounded-full border border-[#d7dfdc] bg-[#f8faf9] text-[9px] font-semibold tabular-nums text-[#687370]">
                        {index + 1}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`text-[9px] font-bold uppercase ${
                            decision.effect === 'exclude'
                              ? 'text-[#a64539]'
                              : decision.effect === 'recommend'
                                ? 'text-[#946519]'
                                : 'text-[#276b61]'
                          }`}>
                            {decision.effect}
                          </span>
                          <ChevronRight size={11} className="text-[#a7aeac]" />
                          <span className="truncate font-mono text-[9px] text-[#78817f]">{displayId(decision.rule_id)}</span>
                        </div>
                        <p className="mt-1.5 text-[11px] leading-[1.55] text-[#4e5956]">{decision.rationale}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </aside>
      </main>
    </div>
  );
}
