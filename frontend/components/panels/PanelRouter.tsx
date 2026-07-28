'use client';
import type {
  IntakeFormData,
  DecisionSummaryData,
  ArchitectureDiagramData,
  RequirementsData,
  ServiceMapData,
  RiskCardsData,
  PhaseTimelineData,
  CostEstimateV2,
  BlueprintData,
} from '@/lib/types';
import { IntakeFormV2 } from './IntakeFormV2';
import { DecisionSummary } from './DecisionSummary';
import { ArchitectureDiagram } from './ArchitectureDiagram';
import { RequirementsPanel } from './RequirementsPanel';
import { ServiceMap } from './ServiceMap';
import { RiskCards } from './RiskCards';
import { PhaseTimeline } from './PhaseTimeline';
import { CostRangePanel } from './CostRangePanel';
import { BlueprintAssembly } from './BlueprintAssembly';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

interface PanelRouterProps {
  step: number;
  panelData: Record<number, unknown>;
  streaming: boolean;
  onAnswer: (q: string, v: unknown) => void;
  onSubmit: () => void;
  onExport: (fmt: 'pdf' | 'pptx') => void;
  onComponentClick?: (id: string, name: string) => void;
  customerName?: string;
  sessionName?: string;
  exportError?: string | null;
  exporting?: 'pdf' | 'pptx' | null;
  onOverride?: (path: string, value: string, rationale: string, engineValue: string) => void;
}

// Backend step → panel mapping
// 1: evidence, 2: decision, 3: architecture, 4: requirements,
// 5: controls, 6: AWS mapping, 7: risks, 8: roadmap,
// 9: cost_estimate, 10: blueprint

export function PanelRouter({
  step,
  panelData,
  streaming,
  onAnswer,
  onSubmit,
  onExport,
  onComponentClick,
  customerName,
  sessionName,
  exportError,
  exporting,
  onOverride,
}: PanelRouterProps) {
  switch (step) {
    case 1:
      return (
        <IntakeFormV2
          data={(panelData[1] as IntakeFormData) ?? null}
          onAnswer={onAnswer}
          onSubmit={onSubmit}
          streaming={streaming}
        />
      );
    case 2:
      return (
        <DecisionSummary
          data={(panelData[2] as DecisionSummaryData) ?? null}
          onOverride={onOverride}
        />
      );
    case 3:
      return (
        <ArchitectureDiagram
          data={(panelData[3] as ArchitectureDiagramData) ?? null}
          streaming={streaming}
          onComponentClick={onComponentClick}
        />
      );
    case 4:
      return (
        <RequirementsPanel data={(panelData[4] as RequirementsData) ?? null} />
      );
    case 5:
      return <CompliancePanel data={panelData[5] as ComplianceData | null} streaming={streaming} />;
    case 6:
      return (
        <ServiceMap
          data={(panelData[6] as ServiceMapData) ?? null}
          streaming={streaming}
        />
      );
    case 7:
      return (
        <RiskCards
          data={(panelData[7] as RiskCardsData) ?? null}
          streaming={streaming}
        />
      );
    case 8:
      return (
        <PhaseTimeline
          data={(panelData[8] as PhaseTimelineData) ?? null}
          streaming={streaming}
        />
      );
    case 9:
      return (
        <CostRangePanel data={(panelData[9] as CostEstimateV2) ?? null} />
      );
    case 10:
      return (
        <BlueprintAssembly
          data={(panelData[10] as BlueprintData) ?? null}
          streaming={streaming}
          onExport={onExport}
          customerName={customerName}
          sessionName={sessionName}
          exportError={exportError}
          exporting={exporting}
        />
      );
    default:
      return (
        <div style={{ padding: 24, color: 'var(--text-muted)', textAlign: 'center' }}>
          Step {step} output will appear here.
        </div>
      );
  }
}

// ── Inline Compliance Panel (step 5) ─────────────────────────────────────────

interface ComplianceData {
  regime: string;
  controls: { name: string; status: string; description?: string }[];
  counts: { required: number; advisory: number; best_practice: number };
  law_notes: string[];
}

const STATUS_COLOR: Record<string, 'red' | 'orange' | 'blue'> = {
  required: 'red',
  advisory: 'orange',
  best_practice: 'blue',
};

function CompliancePanel({ data, streaming }: { data: ComplianceData | null; streaming: boolean }) {
  if (!data || !data.counts || !data.controls || !data.law_notes) {
    return (
      <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="skeleton" style={{ height: 60 }} />
        <div className="skeleton" style={{ height: 200 }} />
      </div>
    );
  }

  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card glow style={{ padding: 16 }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Compliance Regime</div>
        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 12 }}>{data.regime}</div>
        <div style={{ display: 'flex', gap: 12 }}>
          <span style={{ fontSize: 13, color: 'var(--accent-red)' }}><strong>{data.counts.required}</strong> Required</span>
          <span style={{ fontSize: 13, color: 'var(--accent-orange)' }}><strong>{data.counts.advisory}</strong> Advisory</span>
          <span style={{ fontSize: 13, color: 'var(--accent-blue)' }}><strong>{data.counts.best_practice}</strong> Best Practice</span>
        </div>
      </Card>

      {data.law_notes.length > 0 && (
        <Card style={{ padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>Regulatory Notes</div>
          {data.law_notes.map((note, i) => (
            <div key={i} style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 4 }}>• {note}</div>
          ))}
        </Card>
      )}

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '8px 14px', borderBottom: '1px solid var(--border-default)', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
          Controls ({data.controls.length})
        </div>
        <div style={{ maxHeight: 360, overflowY: 'auto' }}>
          {data.controls.map((c, i) => (
            <div key={i} style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-default)', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <Badge color={STATUS_COLOR[c.status] ?? 'blue'} size="sm">{c.status}</Badge>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{c.name}</div>
                {c.description && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{c.description}</div>}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

export default PanelRouter;
