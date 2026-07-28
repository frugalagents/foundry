'use client';
import { useMemo, useState } from 'react';
import type { IntakeFormData, IntakeAnswers } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

interface IntakeFormProps {
  data: IntakeFormData | null;
  onAnswer: (questionId: string, value: string | string[]) => void;
  onSubmit: () => void;
  streaming: boolean;
}

type Archetype = NonNullable<IntakeAnswers['archetype']>;

interface Option { value: string; label: string; hint?: string }
interface Question {
  id: keyof IntakeAnswers;
  label: string;
  why: string;
  kind?: 'hard' | 'soft';            // hard = disqualifier, soft = weight (default soft)
  multi?: boolean;                    // multi-select
  options: Option[];
  notSure?: boolean;                  // show a "Not sure" chip (zero-pressure)
  showFor?: Archetype[];              // Stage-3 branch gating
}

// ── Stage 1: archetype (question filter) ────────────────────────────────────
const ARCHETYPES: Option[] = [
  { value: 'coding',             label: 'Coding & dev-productivity agents', hint: 'Help engineers write, review, ship code (Claude Code / Copilot style)' },
  { value: 'internal_copilot',   label: 'Internal copilot / knowledge assistant', hint: 'Answer questions & do tasks for employees over our data' },
  { value: 'hosting_platform',   label: 'Platform for other teams to build & run agents', hint: 'We provide the infrastructure; other teams build on it' },
  { value: 'customer_facing',    label: 'Customer-facing agentic product', hint: 'Agents embedded in a product our customers use' },
  { value: 'process_automation', label: 'Process / workflow automation', hint: 'Back-office automation — ops, claims, incident response' },
  { value: 'marketplace',        label: 'Agent marketplace / economy', hint: 'Agents that discover, compose, and transact with each other' },
];

// ── Stages 2–4: spine + branch + tune ───────────────────────────────────────
const SPINE: Question[] = [
  {
    id: 'autonomy_model', label: 'How much should agents act on their own?',
    why: 'Sets your autonomy tier and how many guardrails you need.', notSure: true,
    options: [
      { value: 'full',       label: 'Act independently', hint: 'Take actions without a human checking first' },
      { value: 'hitl',       label: 'Act with approval gates', hint: 'Propose; a human approves before it executes' },
      { value: 'supervised', label: 'Suggest only', hint: 'The human always performs the action (copilot)' },
    ],
  },
  {
    id: 'lob_count', label: 'How many distinct teams will build agents within 12 months?',
    why: 'The single biggest driver of Centralized vs. Federated. Counts teams, not people.', notSure: true,
    options: [
      { value: '1-3',  label: 'One to a few (1–3)' },
      { value: '4-10', label: 'Many (4–10)' },
      { value: '10+',  label: 'Org-wide (10+)' },
    ],
  },
  {
    id: 'team_expertise', label: 'Who will build the agents?',
    why: 'Decides managed-vs-open-source and the component tier.', notSure: true,
    options: [
      { value: 'high',   label: 'AI/ML engineers' },
      { value: 'medium', label: 'General full-stack developers' },
      { value: 'low',    label: 'Business users / low-code' },
    ],
  },
  {
    id: 'cloud_posture', label: 'Cloud & portability stance?',
    why: 'Shapes topology and portability.', notSure: true,
    options: [
      { value: 'single_aws',  label: 'All-in on AWS' },
      { value: 'aws_primary', label: 'AWS-primary, some elsewhere' },
      { value: 'multi_cloud', label: 'Must run across 2+ clouds' },
    ],
  },
  {
    id: 'data_gravity', label: 'Where does the data the agents need actually live?',
    why: 'A hard constraint on topology and residency.', notSure: true,
    options: [
      { value: 'single_region', label: 'One cloud region' },
      { value: 'multi_region',  label: 'Multiple regions' },
      { value: 'on_prem_cloud', label: 'On-prem + cloud (hybrid)' },
      { value: 'edge',          label: 'Edge / distributed' },
    ],
  },
  {
    id: 'compliance_regime', label: 'Which regulations must this platform satisfy?',
    why: 'Some combinations rule out certain architectures entirely.', kind: 'hard', multi: true,
    options: [
      { value: 'sox',       label: 'SOX' },
      { value: 'pci_dss',   label: 'PCI-DSS' },
      { value: 'hipaa',     label: 'HIPAA' },
      { value: 'fedramp',   label: 'FedRAMP' },
      { value: 'gdpr',      label: 'GDPR' },
      { value: 'eu_ai_act', label: 'EU AI Act' },
      { value: 'none',      label: 'None / not yet' },
    ],
  },
];

const BRANCH: Question[] = [
  {
    id: 'tenancy_model', label: 'How should teams be isolated from each other?',
    why: 'Drives multi-tenancy and topology isolation.', showFor: ['hosting_platform'],
    options: [
      { value: 'shared_rbac', label: 'Shared with role-based access' },
      { value: 'namespace',   label: 'Separate namespaces' },
      { value: 'account',     label: 'Separate accounts' },
      { value: 'tiered',      label: 'Tiered (mix)' },
    ],
  },
];

const TUNE: Question[] = [
  {
    id: 'cost_sensitivity', label: "What's your stance on cost?",
    why: 'Sets cost weights and model-routing strategy.', notSure: true,
    options: [
      { value: 'primary',        label: 'Cost is the #1 constraint' },
      { value: 'secondary',      label: 'Performance over cost' },
      { value: 'optimize_later', label: 'Predictable / flat spend' },
    ],
  },
];

const PAIN_POINT_OPTIONS = [
  'Too expensive', 'Can’t govern / control them', 'Teams build silos, no reuse',
  'Tool integration is slow', 'Auth / identity is a mess', 'Can’t trust the outputs',
  'No good data grounding',
];
const INDUSTRIES = ['Financial Services', 'Healthcare', 'Insurance', 'Retail', 'Manufacturing', 'Technology', 'Government', 'Other'];

const NOT_SURE = 'not_sure';

function chip(selected: boolean, color: string) {
  return {
    padding: '5px 12px', borderRadius: 20, fontSize: 12, cursor: 'pointer',
    transition: 'all 0.15s', textAlign: 'left' as const,
    border: `1px solid ${selected ? color : 'var(--border-default)'}`,
    background: selected ? `${color}22` : 'transparent',
    color: selected ? color : 'var(--text-secondary)',
    fontWeight: selected ? 600 : 400,
  };
}

export function IntakeForm({ data, onAnswer, onSubmit, streaming }: IntakeFormProps) {
  const answers = (data?.answers ?? {}) as Partial<IntakeAnswers>;
  const complete = data?.complete ?? false;
  const [confirming, setConfirming] = useState(false);

  const archetype = answers.archetype as Archetype | undefined;

  // Questions visible given the chosen archetype (Stage-3 branch filter).
  const branchQuestions = useMemo(
    () => BRANCH.filter((q) => !q.showFor || (archetype && q.showFor.includes(archetype))),
    [archetype],
  );

  const isSel = (q: Question, val: string): boolean => {
    const a = answers[q.id];
    if (q.multi) return Array.isArray(a) && a.includes(val);
    return a === val;
  };

  const handlePick = (q: Question, val: string) => {
    if (q.multi) {
      const cur = (answers[q.id] as string[]) ?? [];
      const next = cur.includes(val) ? cur.filter((x) => x !== val) : [...cur, val];
      onAnswer(q.id, next);
    } else {
      onAnswer(q.id, val);
    }
  };

  // Answers marked "Not sure" — surfaced as assumptions in the confirmation step.
  const notSureFields = useMemo(
    () => [...SPINE, ...TUNE].filter((q) => answers[q.id] === NOT_SURE).map((q) => q.label),
    [answers],
  );

  const renderQuestion = (q: Question, accent: string) => (
    <div key={q.id} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{q.label}</span>
        {q.kind === 'hard' && (
          <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: 'rgba(239,68,68,0.15)', color: '#ef4444', fontWeight: 600 }}>
            HARD CONSTRAINT
          </span>
        )}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>{q.why}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        {q.options.map((opt) => (
          <button key={opt.value} onClick={() => handlePick(q, opt.value)} style={chip(isSel(q, opt.value), accent)}>
            <div>{isSel(q, opt.value) && q.multi ? '✓ ' : ''}{opt.label}</div>
            {opt.hint && <div style={{ fontSize: 10, opacity: 0.7, marginTop: 1 }}>{opt.hint}</div>}
          </button>
        ))}
        {q.notSure && (
          <button onClick={() => handlePick(q, NOT_SURE)} style={{ ...chip(isSel(q, NOT_SURE), 'var(--text-muted)'), fontStyle: 'italic' }}>
            Not sure — estimate for me
          </button>
        )}
      </div>
    </div>
  );

  // ── Stage 5: confirmation ──
  if (confirming) {
    return (
      <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>Confirm before scoring</h2>
        <Card style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Here’s what we heard. Correct anything before we score it.
          </div>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: 4 }}>
            {ARCHETYPES.find((a) => a.value === archetype) && (
              <li><b>Building:</b> {ARCHETYPES.find((a) => a.value === archetype)!.label}</li>
            )}
            {answers.lob_count && answers.lob_count !== NOT_SURE && <li><b>Teams:</b> {answers.lob_count}</li>}
            {answers.autonomy_model && answers.autonomy_model !== NOT_SURE && <li><b>Autonomy:</b> {answers.autonomy_model}</li>}
            {answers.cloud_posture && answers.cloud_posture !== NOT_SURE && <li><b>Cloud:</b> {answers.cloud_posture}</li>}
            {Array.isArray(answers.compliance_regime) && answers.compliance_regime.length > 0 && (
              <li><b>Compliance:</b> {answers.compliance_regime.join(', ')}</li>
            )}
            {answers.cost_sensitivity && answers.cost_sensitivity !== NOT_SURE && <li><b>Cost:</b> {answers.cost_sensitivity}</li>}
          </ul>
          {notSureFields.length > 0 && (
            <div style={{ fontSize: 11, color: 'var(--accent-orange)', marginTop: 6 }}>
              Assumptions (answered “Not sure”, no scoring pressure applied):
              <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>
                {notSureFields.map((f) => <li key={f}>{f}</li>)}
              </ul>
            </div>
          )}
        </Card>
        <div style={{ display: 'flex', gap: 10 }}>
          <Button variant="secondary" onClick={() => setConfirming(false)} style={{ flex: 1 }}>Let me fix something</Button>
          <Button variant="primary" onClick={onSubmit} loading={streaming} style={{ flex: 2 }}>Yes, score it →</Button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>Platform Intake</h2>
        <span style={{ fontSize: 12, color: complete ? 'var(--accent-green)' : 'var(--text-muted)' }}>
          {complete ? 'Ready' : `${(data?.missing ?? []).length} left`}
        </span>
      </div>

      {/* Stage 1 — Frame (archetype filter) */}
      <Card style={{ padding: 14 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          1 · Frame
        </div>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
          What is the primary job of this platform over the next 12 months?
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 10 }}>
          Decides which questions you’ll see next.
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          {ARCHETYPES.map((opt) => (
            <button key={opt.value} onClick={() => onAnswer('archetype', opt.value)} style={chip(archetype === opt.value, 'var(--accent-cyan)')}>
              <div>{opt.label}</div>
              {opt.hint && <div style={{ fontSize: 10, opacity: 0.7, marginTop: 1 }}>{opt.hint}</div>}
            </button>
          ))}
        </div>
      </Card>

      {/* Remaining stages appear once an archetype is chosen */}
      {archetype && (
        <>
          <Card style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-blue)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              2 · Your situation
            </div>
            {SPINE.map((q) => renderQuestion(q, 'var(--accent-blue)'))}
          </Card>

          {branchQuestions.length > 0 && (
            <Card style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-purple)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                3 · Specifics
              </div>
              {branchQuestions.map((q) => renderQuestion(q, 'var(--accent-purple)'))}
            </Card>
          )}

          <Card style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-green)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              4 · Priorities
            </div>
            {TUNE.map((q) => renderQuestion(q, 'var(--accent-green)'))}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                Biggest frustration with agents today? <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(up to 3)</span>
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {PAIN_POINT_OPTIONS.map((pp) => {
                  const sel = (answers.pain_points ?? []).includes(pp);
                  return (
                    <button key={pp} onClick={() => {
                      const cur = answers.pain_points ?? [];
                      const next = cur.includes(pp) ? cur.filter((x) => x !== pp) : (cur.length < 3 ? [...cur, pp] : cur);
                      onAnswer('pain_points', next);
                    }} style={chip(sel, 'var(--accent-orange)')}>
                      {sel ? '✓ ' : ''}{pp}
                    </button>
                  );
                })}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>Industry</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {INDUSTRIES.map((ind) => (
                  <button key={ind} onClick={() => onAnswer('industry', ind)} style={chip(answers.industry === ind, 'var(--accent-cyan)')}>
                    {ind}
                  </button>
                ))}
              </div>
            </div>
          </Card>

          <Button
            variant="primary" size="lg"
            onClick={() => setConfirming(true)}
            disabled={!complete}
            style={{ width: '100%' }}
          >
            {complete ? 'Review & score →' : `Answer ${(data?.missing ?? []).length} more`}
          </Button>
        </>
      )}
    </div>
  );
}

export default IntakeForm;
