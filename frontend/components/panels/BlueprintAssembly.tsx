'use client';
import type { BlueprintData } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

interface BlueprintAssemblyProps {
  data: BlueprintData | null;
  streaming: boolean;
  onExport: (format: 'pdf' | 'pptx') => void;
  customerName?: string;
  sessionName?: string;
  exportError?: string | null;
  exporting?: 'pdf' | 'pptx' | null;
}

export function BlueprintAssembly({
  data, streaming, onExport, customerName, sessionName, exportError, exporting,
}: BlueprintAssemblyProps) {
  if (!data) {
    return (
      <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="skeleton" style={{ height: i === 1 ? 80 : i === 2 ? 300 : 60 }} />
        ))}
      </div>
    );
  }

  const confPct = Math.round((data.confidence ?? 0) * 100);
  const confColor = confPct > 60 ? 'green' : confPct > 30 ? 'orange' : 'red';

  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Document header — client-ready identity */}
      <Card glow style={{ padding: 20 }}>
        {(customerName || sessionName) && (
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {customerName && <span>{customerName}</span>}
            {sessionName && <span>· {sessionName}</span>}
            <span>· Generated {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
          </div>
        )}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
          <div>
            <div className="eyebrow" style={{ marginBottom: 4 }}>Recommended architecture</div>
            <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)' }}>
              {data.pattern_name ?? data.pattern_id}
            </div>
          </div>
          <Badge color={confColor} size="md">{confPct}% confidence</Badge>
        </div>

        {/* Stats row */}
        <div style={{ display: 'flex', gap: 16, marginTop: 12, flexWrap: 'wrap' }}>
          {[
            { label: 'Components', value: data.components_count },
            { label: 'Phases', value: data.phases_count },
            { label: 'Services', value: data.services_count },
            { label: 'Anti-patterns', value: data.antipatterns_count },
            { label: 'Innovations', value: data.innovations_count },
          ].map(({ label, value }) => value != null && (
            <div key={label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>{value}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Blueprint markdown */}
      {data.markdown && (
        <Card style={{ padding: 20, flex: 1 }}>
          <BlueprintMarkdown text={data.markdown} />
        </Card>
      )}

      {/* Export */}
      {data.export_ready && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 14, background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-default)' }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', flex: 1 }}>
              Share this blueprint with your client
            </span>
            <Button variant="primary" size="sm" onClick={() => onExport('pdf')} loading={exporting === 'pdf'}>Export PDF</Button>
            <Button variant="secondary" size="sm" onClick={() => onExport('pptx')} loading={exporting === 'pptx'}>Export PPTX</Button>
          </div>
          {exportError && (
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--danger)' }}>{exportError}</span>
          )}
        </div>
      )}
    </div>
  );
}

/** Renders markdown including H1-H3, tables, code blocks, HR, and bullet lists. */
function BlueprintMarkdown({ text }: { text: string }) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let key = 0;

  // Table accumulator
  let tableRows: string[][] = [];
  let inCode = false;
  let codeLines: string[] = [];

  function flushTable() {
    if (tableRows.length === 0) return;
    const [headerRow, ...bodyRows] = tableRows;
    elements.push(
      <div key={key++} style={{ overflowX: 'auto', margin: '8px 0' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              {headerRow.map((cell, ci) => (
                <th key={ci} style={{ padding: '5px 10px', textAlign: 'left', background: 'var(--bg-elevated)', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, borderBottom: '1px solid var(--border-default)', whiteSpace: 'nowrap' }}>
                  {cell}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {bodyRows.map((row, ri) => (
              <tr key={ri} style={{ borderBottom: '1px solid var(--border-default)', background: ri % 2 === 0 ? 'transparent' : 'var(--bg-sunken)' }}>
                {row.map((cell, ci) => (
                  <td key={ci} style={{ padding: '5px 10px', color: 'var(--text-secondary)', verticalAlign: 'top' }}>
                    <InlineBold text={cell} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
    tableRows = [];
  }

  function flushCode() {
    if (codeLines.length === 0) return;
    elements.push(
      <pre key={key++} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: 6, padding: '10px 12px', fontSize: 11, color: 'var(--text-secondary)', overflowX: 'auto', margin: '6px 0', lineHeight: 1.6, fontFamily: 'monospace', whiteSpace: 'pre' }}>
        {codeLines.join('\n')}
      </pre>
    );
    codeLines = [];
    inCode = false;
  }

  for (const line of lines) {
    // Code block toggle
    if (line.startsWith('```')) {
      if (inCode) {
        flushCode();
      } else {
        flushTable();
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      codeLines.push(line);
      continue;
    }

    // Table row
    if (line.startsWith('|')) {
      if (line.replace(/\|/g, '').replace(/-/g, '').trim() === '') continue; // separator
      const cells = line.split('|').slice(1, -1).map((c) => c.trim());
      tableRows.push(cells);
      continue;
    }

    // Non-table line — flush any accumulated table
    flushTable();

    // HR
    if (line.match(/^-{3,}$/) || line.match(/^\*{3,}$/)) {
      elements.push(<hr key={key++} style={{ border: 'none', borderTop: '1px solid var(--border-default)', margin: '10px 0' }} />);
      continue;
    }

    // H1
    if (line.startsWith('# ') && !line.startsWith('## ')) {
      elements.push(
        <div key={key++} style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-primary)', marginTop: 12, marginBottom: 6, borderBottom: '2px solid var(--border-default)', paddingBottom: 6 }}>
          <InlineBold text={line.slice(2)} />
        </div>
      );
      continue;
    }

    // H2
    if (line.startsWith('## ')) {
      elements.push(
        <div key={key++} style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginTop: 16, marginBottom: 4, borderBottom: '1px solid var(--border-default)', paddingBottom: 4 }}>
          <InlineBold text={line.slice(3)} />
        </div>
      );
      continue;
    }

    // H3
    if (line.startsWith('### ')) {
      elements.push(
        <div key={key++} style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginTop: 10, marginBottom: 2 }}>
          <InlineBold text={line.slice(4)} />
        </div>
      );
      continue;
    }

    // Bullet
    if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(
        <div key={key++} style={{ display: 'flex', gap: 8, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, paddingLeft: 8 }}>
          <span style={{ color: 'var(--accent-blue)', flexShrink: 0 }}>•</span>
          <span><InlineBold text={line.slice(2)} /></span>
        </div>
      );
      continue;
    }

    // Blank line
    if (line.trim() === '') {
      elements.push(<div key={key++} style={{ height: 4 }} />);
      continue;
    }

    // Plain text
    elements.push(
      <div key={key++} style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
        <InlineBold text={line} />
      </div>
    );
  }

  // Flush any remaining table/code
  flushTable();
  flushCode();

  return <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>{elements}</div>;
}

function InlineBold({ text }: { text: string }) {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return (
    <>
      {parts.map((p, i) =>
        p.startsWith('**') && p.endsWith('**')
          ? <strong key={i} style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{p.slice(2, -2)}</strong>
          : <span key={i}>{p}</span>
      )}
    </>
  );
}

export default BlueprintAssembly;
