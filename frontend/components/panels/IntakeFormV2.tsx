'use client';

import { useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, ShieldAlert } from 'lucide-react';
import type { IntakeFormData } from '@/lib/types';
import {
  type AdvisorQuestion,
  type AssessmentDraft,
  isAnswered,
  questionsFor,
} from '@/lib/advisor-v2';
import { Button } from '@/components/ui/Button';

interface Props {
  data: IntakeFormData | null;
  onAnswer: (path: string, value: unknown) => void;
  onSubmit: () => void;
  streaming: boolean;
}

const SECTIONS = [
  { id: 'frame', label: 'Frame' },
  { id: 'ownership', label: 'Ownership' },
  { id: 'risk', label: 'Risk and boundaries' },
  { id: 'workload', label: 'Workload scale' },
  { id: 'readiness', label: 'Readiness' },
  { id: 'review', label: 'Review' },
] as const;

function inputStyle() {
  return {
    minHeight: 38,
    border: '1px solid var(--border-default)',
    borderRadius: 6,
    background: 'var(--bg-card)',
    color: 'var(--text-primary)',
    padding: '7px 10px',
    fontSize: 13,
    width: '100%',
  };
}

export function IntakeFormV2({ data, onAnswer, onSubmit, streaming }: Props) {
  const draft = (data?.answers ?? {}) as AssessmentDraft;
  const [sectionIndex, setSectionIndex] = useState(0);
  const questions = useMemo(() => questionsFor(draft), [draft]);
  const section = SECTIONS[sectionIndex].id;
  const visible = section === 'review' ? [] : questions.filter((q) => q.section === section);
  const sectionMissing = visible.filter((q) => q.required && !isProvided(draft[q.path], q.type));
  const allMissing = data?.missing ?? [];
  const canAdvance = sectionMissing.length === 0;
  const hasFrame = typeof draft.audience === 'string' && typeof draft.primary_workload === 'string';

  return (
    <div style={{ padding: 20, maxWidth: 860, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div>
        <h2 className="text-panel-title">Architecture Evidence</h2>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 3 }}>
          Questions adapt to the primary workload. Critical unknowns block the final blueprint.
        </div>
      </div>

      <div className="v2-section-tabs" style={{ display: 'grid', gridTemplateColumns: `repeat(${SECTIONS.length}, minmax(0, 1fr))`, gap: 4, overflowX: 'auto' }}>
        {SECTIONS.map((item, index) => {
          const active = index === sectionIndex;
          const done = index < sectionIndex;
          return (
            <button
              key={item.id}
              onClick={() => setSectionIndex(index)}
              style={{
                border: 0,
                borderBottom: `2px solid ${active ? 'var(--accent)' : done ? 'var(--success)' : 'var(--border-default)'}`,
                background: 'transparent',
                color: active ? 'var(--text-primary)' : 'var(--text-muted)',
                padding: '7px 4px',
                fontSize: 11,
                cursor: 'pointer',
                minWidth: 0,
              }}
            >
              {done && <Check size={11} style={{ marginRight: 3, verticalAlign: -2 }} />}
              {item.label}
            </button>
          );
        })}
      </div>

      {section !== 'review' ? (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {visible.map((question, index) => (
            <QuestionField
              key={question.path}
              question={question}
              value={draft[question.path]}
              onChange={(value) => onAnswer(question.path, value)}
              first={index === 0}
            />
          ))}
          {visible.length === 0 && section === 'workload' && (
            <div style={{ padding: 24, color: 'var(--text-muted)', textAlign: 'center' }}>
              Select a primary workload in Frame to load its sizing questions.
            </div>
          )}
        </div>
      ) : (
        <Review draft={draft} questions={questions} missing={allMissing} />
      )}

      <div style={{ display: 'flex', gap: 8, justifyContent: 'space-between' }}>
        <Button
          variant="secondary"
          disabled={sectionIndex === 0}
          onClick={() => setSectionIndex((value) => Math.max(0, value - 1))}
        >
          <ArrowLeft size={14} /> Back
        </Button>
        {sectionIndex < SECTIONS.length - 1 ? (
          <Button
            variant="primary"
            disabled={!canAdvance}
            onClick={() => setSectionIndex((value) => Math.min(SECTIONS.length - 1, value + 1))}
          >
            Next <ArrowRight size={14} />
          </Button>
        ) : (
          <Button variant="primary" disabled={!hasFrame} loading={streaming} onClick={onSubmit}>
            {data?.complete ? 'Evaluate architecture' : 'Evaluate provisional'}
          </Button>
        )}
      </div>
      <style jsx global>{`
        @media (max-width: 700px) {
          .v2-question-row,
          .v2-review-row {
            grid-template-columns: minmax(0, 1fr) !important;
            gap: 8px !important;
          }
          .v2-section-tabs {
            grid-template-columns: repeat(6, minmax(92px, 1fr)) !important;
          }
        }
      `}</style>
    </div>
  );
}

function QuestionField({
  question,
  value,
  onChange,
  first,
}: {
  question: AdvisorQuestion;
  value: unknown;
  onChange: (value: unknown) => void;
  first: boolean;
}) {
  return (
    <div className="v2-question-row" data-question={question.id} style={{
      padding: '17px 0',
      borderTop: first ? 'none' : '1px solid var(--border-default)',
      display: 'grid',
      gridTemplateColumns: 'minmax(220px, 0.8fr) minmax(280px, 1.2fr)',
      gap: 22,
      alignItems: 'start',
    }}>
      <div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{question.prompt}</span>
          {question.required && <span title="Required for a decision-grade result" style={{ color: 'var(--danger)', fontSize: 11 }}>*</span>}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.45, marginTop: 4 }}>{question.why}</div>
      </div>
      <QuestionControl question={question} value={value} onChange={onChange} />
    </div>
  );
}

function QuestionControl({
  question,
  value,
  onChange,
}: {
  question: AdvisorQuestion;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  if (question.type === 'number') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <input
          type="number"
          min={0}
          value={typeof value === 'number' ? value : ''}
          onChange={(event) => onChange(event.target.value === '' ? undefined : Number(event.target.value))}
          style={inputStyle()}
        />
        {question.unit && <span style={{ fontSize: 11, color: 'var(--text-muted)', minWidth: 54 }}>{question.unit}</span>}
      </div>
    );
  }

  if (question.type === 'range') {
    const rangeValue = (typeof value === 'object' && value !== null ? value : {}) as Record<string, unknown>;
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 6 }}>
        {(['low', 'expected', 'high'] as const).map((key) => (
          <label key={key} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'capitalize' }}>{key}</span>
            <input
              type="number"
              min={0}
              value={typeof rangeValue[key] === 'number' ? String(rangeValue[key]) : ''}
              onChange={(event) => {
                const next: Record<string, unknown> = {
                  ...rangeValue,
                  unit: question.unit ?? 'units',
                };
                if (event.target.value === '') delete next[key];
                else next[key] = Number(event.target.value);
                onChange(next);
              }}
              style={inputStyle()}
            />
          </label>
        ))}
      </div>
    );
  }

  if (question.type === 'boolean') {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
        {[{ value: true, label: 'Yes' }, { value: false, label: 'No' }].map((option) => (
          <button
            key={option.label}
            onClick={() => onChange(option.value)}
            style={{
              ...inputStyle(),
              cursor: 'pointer',
              borderColor: value === option.value ? 'var(--accent)' : 'var(--border-default)',
              background: value === option.value ? 'var(--accent-soft)' : 'var(--bg-card)',
            }}
          >
            {option.label}
          </button>
        ))}
      </div>
    );
  }

  if (question.type === 'multi') {
    const selected = Array.isArray(value) ? value as string[] : [];
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))', gap: 6 }}>
        {question.options?.map((option) => {
          const checked = selected.includes(option.value);
          return (
            <label key={option.value} style={{
              ...inputStyle(),
              display: 'flex',
              alignItems: 'center',
              gap: 7,
              cursor: 'pointer',
              borderColor: checked ? 'var(--accent)' : 'var(--border-default)',
            }}>
              <input
                type="checkbox"
                checked={checked}
                onChange={() => {
                  let next = checked ? selected.filter((item) => item !== option.value) : [...selected, option.value];
                  if (question.path === 'data.regulations') {
                    next = option.value === 'NONE' && !checked
                      ? ['NONE']
                      : next.filter((item) => item !== 'NONE');
                  }
                  onChange(next);
                }}
              />
              <span style={{ fontSize: 12 }}>{option.label}</span>
            </label>
          );
        })}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {question.options?.map((option) => {
        const selected = value === option.value;
        return (
          <button
            key={option.value}
            onClick={() => onChange(option.value)}
            style={{
              ...inputStyle(),
              cursor: 'pointer',
              textAlign: 'left',
              borderColor: selected ? 'var(--accent)' : 'var(--border-default)',
              background: selected ? 'var(--accent-soft)' : 'var(--bg-card)',
            }}
          >
            <div style={{ fontWeight: selected ? 600 : 400 }}>{option.label}</div>
            {option.hint && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{option.hint}</div>}
          </button>
        );
      })}
    </div>
  );
}

function Review({
  draft,
  questions,
  missing,
}: {
  draft: AssessmentDraft;
  questions: AdvisorQuestion[];
  missing: string[];
}) {
  const answered = questions.filter((q) => isAnswered(draft[q.path], q.type));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {missing.length > 0 && (
        <div style={{ display: 'flex', gap: 9, padding: 12, border: '1px solid var(--danger)', borderRadius: 6, background: 'var(--danger-subtle)' }}>
          <ShieldAlert size={17} color="var(--danger)" />
          <div style={{ fontSize: 12, color: 'var(--text-primary)' }}>
            {missing.length} critical evidence item{missing.length === 1 ? '' : 's'} remain. Return to the highlighted sections before evaluation.
          </div>
        </div>
      )}
      <div style={{ borderTop: '1px solid var(--border-default)' }}>
        {answered.map((question) => (
          <div key={question.path} className="v2-review-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, padding: '9px 0', borderBottom: '1px solid var(--border-default)', fontSize: 12 }}>
            <span style={{ color: 'var(--text-muted)' }}>{question.prompt}</span>
            <span style={{ color: 'var(--text-primary)', overflowWrap: 'anywhere' }}>{formatValue(draft[question.path])}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'object' && value !== null) {
    const range = value as Record<string, unknown>;
    return `${range.low ?? '?'} / ${range.expected ?? '?'} / ${range.high ?? '?'} ${range.unit ?? ''}`;
  }
  return String(value);
}

function isProvided(value: unknown, type: AdvisorQuestion['type']): boolean {
  if (value === undefined || value === null || value === '') return false;
  if (type === 'multi') return Array.isArray(value) && value.length > 0;
  if (type === 'range') {
    if (typeof value !== 'object' || value === null) return false;
    const range = value as Record<string, unknown>;
    return ['low', 'expected', 'high'].every((key) => typeof range[key] === 'number');
  }
  return true;
}

export default IntakeFormV2;
