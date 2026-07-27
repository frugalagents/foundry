'use client';
import type { IntakeFormData, IntakeAnswers } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

interface IntakeFormProps {
  data: IntakeFormData | null;
  onAnswer: (questionId: string, value: string | string[]) => void;
  onSubmit: () => void;
  streaming: boolean;
}

const QUESTIONS: {
  id: keyof IntakeAnswers;
  label: string;
  category: 'org' | 'tech' | 'gov' | 'ops';
  options: { value: string; label: string }[];
}[] = [
  {
    id: 'autonomy_model', label: 'Human oversight level', category: 'org',
    options: [{ value: 'full', label: 'Full autonomous' }, { value: 'hitl', label: 'Human-in-the-loop' }, { value: 'supervised', label: 'Supervised' }],
  },
  {
    id: 'lob_count', label: 'Lines of business', category: 'org',
    options: [{ value: '1-3', label: '1–3' }, { value: '4-10', label: '4–10' }, { value: '10+', label: '10+' }],
  },
  {
    id: 'governance_model', label: 'Governance model', category: 'org',
    options: [{ value: 'centralized', label: 'Centralized' }, { value: 'federated', label: 'Federated' }, { value: 'undecided', label: 'Undecided' }],
  },
  {
    id: 'cloud_posture', label: 'Cloud posture', category: 'tech',
    options: [{ value: 'single_aws', label: 'Single AWS' }, { value: 'aws_primary', label: 'AWS primary' }, { value: 'multi_cloud', label: 'Multi-cloud' }],
  },
  {
    id: 'stack_preference', label: 'Stack preference', category: 'tech',
    options: [{ value: 'open_source', label: 'Open source' }, { value: 'managed', label: 'Managed' }, { value: 'hybrid', label: 'Hybrid' }],
  },
  {
    id: 'auth_identity', label: 'Identity setup', category: 'tech',
    options: [{ value: 'oauth_oidc', label: 'OAuth/OIDC' }, { value: 'iam_heavy', label: 'IAM-heavy' }, { value: 'greenfield', label: 'Greenfield' }, { value: 'complex_multi', label: 'Complex multi-IdP' }],
  },
  {
    id: 'data_gravity', label: 'Data location', category: 'tech',
    options: [{ value: 'single_region', label: 'Single region' }, { value: 'multi_region', label: 'Multi-region' }, { value: 'on_prem_cloud', label: 'On-prem + cloud' }, { value: 'edge', label: 'Edge' }],
  },
  {
    id: 'observability', label: 'Observability', category: 'gov',
    options: [{ value: 'existing_stack', label: 'Existing stack' }, { value: 'greenfield', label: 'Greenfield' }],
  },
  {
    id: 'intake_maturity', label: 'AI maturity', category: 'gov',
    options: [{ value: 'mature', label: 'Mature (prod AI)' }, { value: 'emerging', label: 'Emerging' }, { value: 'greenfield', label: 'Greenfield' }],
  },
  {
    id: 'agent_purpose', label: 'Agent purpose', category: 'gov',
    options: [{ value: 'internal', label: 'Internal' }, { value: 'customer_facing', label: 'Customer-facing' }, { value: 'both', label: 'Both' }],
  },
  {
    id: 'compliance_regime', label: 'Compliance regime', category: 'gov',
    options: [
      { value: 'hipaa', label: 'HIPAA' },
      { value: 'soc2', label: 'SOC 2' },
      { value: 'gdpr', label: 'GDPR' },
      { value: 'pci_dss', label: 'PCI-DSS' },
      { value: 'fedramp', label: 'FedRAMP' },
      { value: 'none', label: 'None / TBD' },
    ],
  },
  {
    id: 'team_expertise', label: 'Team expertise', category: 'ops',
    options: [{ value: 'high', label: 'High' }, { value: 'medium', label: 'Medium' }, { value: 'low', label: 'Low' }],
  },
  {
    id: 'cost_sensitivity', label: 'Cost sensitivity', category: 'ops',
    options: [{ value: 'primary', label: '#1 constraint' }, { value: 'secondary', label: 'Secondary' }, { value: 'optimize_later', label: 'Optimize later' }],
  },
];

const CATEGORIES = {
  org: { label: 'Organization', color: 'var(--accent-blue)', emoji: '🔵' },
  tech: { label: 'Technical', color: 'var(--accent-green)', emoji: '🟢' },
  gov: { label: 'Governance', color: 'var(--accent-orange)', emoji: '🟠' },
  ops: { label: 'Operations', color: 'var(--accent-purple)', emoji: '🟣' },
};

const PAIN_POINT_OPTIONS = [
  'High latency', 'Security gaps', 'High cost', 'Lack of observability',
  'Vendor lock-in', 'Scaling issues', 'Poor governance', 'Tool fragmentation',
  'No RAG / grounding', 'Multi-cloud complexity',
];

const INDUSTRIES = ['Financial Services', 'Healthcare', 'Insurance', 'Retail', 'Manufacturing', 'Technology', 'Government', 'Other'];

export function IntakeForm({ data, onAnswer, onSubmit, streaming }: IntakeFormProps) {
  const answers = data?.answers ?? {};
  const missing = data?.missing ?? QUESTIONS.map((q) => q.id);
  const complete = data?.complete ?? false;
  const answeredCount = QUESTIONS.filter((q) => q.id in answers).length;

  const togglePainPoint = (pp: string) => {
    const current = (answers.pain_points as string[]) ?? [];
    const updated = current.includes(pp)
      ? current.filter((x) => x !== pp)
      : [...current, pp];
    onAnswer('pain_points', updated);
  };

  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>Platform Intake</h2>
        <span style={{ fontSize: 12, color: answeredCount === 13 ? 'var(--accent-green)' : 'var(--text-muted)' }}>
          {answeredCount}/13 answered
        </span>
      </div>

      {(['org', 'tech', 'gov', 'ops'] as const).map((cat) => {
        const catInfo = CATEGORIES[cat];
        const catQuestions = QUESTIONS.filter((q) => q.category === cat);
        return (
          <Card key={cat} style={{ padding: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: catInfo.color, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              {catInfo.emoji} {catInfo.label}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {catQuestions.map((q) => (
                <div key={q.id}>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>{q.label}</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {q.options.map((opt) => {
                      const selected = (answers[q.id] as string) === opt.value;
                      return (
                        <button
                          key={opt.value}
                          onClick={() => onAnswer(q.id, opt.value)}
                          style={{
                            padding: '4px 12px',
                            borderRadius: 20,
                            fontSize: 12,
                            border: `1px solid ${selected ? catInfo.color : 'var(--border-default)'}`,
                            background: selected ? `${catInfo.color}22` : 'transparent',
                            color: selected ? catInfo.color : 'var(--text-secondary)',
                            cursor: 'pointer',
                            transition: 'all 0.15s',
                            fontWeight: selected ? 600 : 400,
                          }}
                        >
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        );
      })}

      {/* Industry */}
      <Card style={{ padding: 14 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          🏢 Industry
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {INDUSTRIES.map((ind) => {
            const selected = answers.industry === ind;
            return (
              <button
                key={ind}
                onClick={() => onAnswer('industry', ind)}
                style={{
                  padding: '4px 12px',
                  borderRadius: 20,
                  fontSize: 12,
                  border: `1px solid ${selected ? 'var(--accent-cyan)' : 'var(--border-default)'}`,
                  background: selected ? 'rgba(86,212,221,0.15)' : 'transparent',
                  color: selected ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {ind}
              </button>
            );
          })}
        </div>
      </Card>

      {/* Pain Points */}
      <Card style={{ padding: 14 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-orange)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          ⚡ Pain Points
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {PAIN_POINT_OPTIONS.map((pp) => {
            const selected = ((answers.pain_points as string[]) ?? []).includes(pp);
            return (
              <button
                key={pp}
                onClick={() => togglePainPoint(pp)}
                style={{
                  padding: '4px 12px',
                  borderRadius: 20,
                  fontSize: 12,
                  border: `1px solid ${selected ? 'var(--accent-orange)' : 'var(--border-default)'}`,
                  background: selected ? 'rgba(210,153,34,0.15)' : 'transparent',
                  color: selected ? 'var(--accent-orange)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {selected ? '✓ ' : ''}{pp}
              </button>
            );
          })}
        </div>
      </Card>

      {/* CTA */}
      <Button
        variant="primary"
        size="lg"
        onClick={onSubmit}
        disabled={!complete}
        loading={streaming}
        style={{ width: '100%', marginTop: 4 }}
      >
        {complete ? 'Generate Blueprint →' : `Answer ${13 - answeredCount} more question${13 - answeredCount !== 1 ? 's' : ''}`}
      </Button>
    </div>
  );
}

export default IntakeForm;
