'use client';

// Blueprint entry gate: choose the platform type before the logical
// architecture is shown. Only the agentic coding platform is supported today;
// the others are presented as upcoming so the direction is visible.

interface PlatformType {
  id: string;
  name: string;
  blurb: string;
  available: boolean;
}

const TYPES: PlatformType[] = [
  { id: 'agentic-coding', name: 'Agentic Coding Platform', blurb: 'Enterprise platform for coding agents — Claude Code / Codex style, org-wide.', available: true },
  { id: 'internal-facing', name: 'Internal-Facing Platform', blurb: 'Internal agentic tools and workflows for employees.', available: false },
  { id: 'saas-decomposition', name: 'SaaS Decomposition', blurb: 'Decompose a SaaS product into agent-driven services.', available: false },
  { id: 'customer-facing', name: 'Customer-Facing Agentic Platform', blurb: 'External, customer-facing agent experiences.', available: false },
  { id: 'marketplace', name: 'Marketplace', blurb: 'Multi-tenant agent / tool marketplace.', available: false },
];

export function PlatformTypeGate({ onSelect }: { onSelect: (id: string) => void }) {
  return (
    <div className="pgate">
      <PgateStyles />
      <div className="pgate-inner">
        <div className="pgate-mark" />
        <h1>Start a blueprint</h1>
        <p className="pgate-sub">What kind of platform are you designing? We&apos;ll derive a purpose-built architecture from the baseline for that platform type.</p>

        <label className="pgate-label">Platform type</label>
        <div className="pgate-cards">
          {TYPES.map((t) => (
            <button
              key={t.id}
              type="button"
              disabled={!t.available}
              onClick={() => t.available && onSelect(t.id)}
              className={`pgate-card${t.available ? '' : ' soon'}`}
            >
              <div className="pgate-card-hd">
                <span className="pgate-card-name">{t.name}</span>
                {t.available
                  ? <span className="pgate-badge ready">available</span>
                  : <span className="pgate-badge soon">coming soon</span>}
              </div>
              <p className="pgate-card-blurb">{t.blurb}</p>
              {t.available && <span className="pgate-go">Start →</span>}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function PgateStyles() {
  return (
    <style>{`
.pgate{height:100%;min-height:0;background:radial-gradient(1000px 560px at 62% -10%,#1a35601c,transparent),radial-gradient(760px 520px at 100% 110%,#f0a8500a,transparent),#0e1116;color:#e6e9ef;font:14px/1.55 "Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;display:flex;align-items:center;justify-content:center;padding:40px 24px;overflow:auto}
.pgate *{box-sizing:border-box}
.pgate-inner{width:100%;max-width:720px}
.pgate-mark{width:40px;height:40px;border-radius:11px;background:conic-gradient(from 210deg,#37dd7d,#4cc4f5,#7d9bff,#b98cf0,#37dd7d);box-shadow:0 0 0 1px #ffffff12;margin-bottom:22px;position:relative}
.pgate-mark::after{content:"";position:absolute;inset:14px;border-radius:5px;background:#0e1116}
.pgate-inner h1{font-size:26px;font-weight:680;letter-spacing:-.4px;margin:0}
.pgate-sub{color:#a7b2c2;font-size:13.5px;line-height:1.6;margin:10px 0 28px;max-width:560px}
.pgate-label{display:block;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.11em;color:#7c8899;margin-bottom:12px}
.pgate-cards{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.pgate-card{position:relative;text-align:left;background:linear-gradient(180deg,#171d27,#131922);border:1px solid #242e3b;border-radius:13px;padding:16px 16px 15px;cursor:pointer;transition:transform .15s,border-color .15s,box-shadow .15s;color:#e6e9ef;font-family:inherit}
.pgate-card:not(.soon):hover{transform:translateY(-2px);border-color:#37dd7d;box-shadow:0 14px 30px -16px #000,0 0 60px -34px #37dd7d}
.pgate-card.soon{opacity:.5;cursor:not-allowed}
.pgate-card-hd{display:flex;align-items:center;gap:8px;margin-bottom:7px}
.pgate-card-name{font-size:14px;font-weight:650;letter-spacing:-.1px}
.pgate-badge{margin-left:auto;font-size:8px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;padding:3px 7px;border-radius:6px}
.pgate-badge.ready{background:#37dd7d;color:#0e1a13}
.pgate-badge.soon{background:#242e3b;color:#7c8899}
.pgate-card-blurb{margin:0;font-size:11.5px;line-height:1.5;color:#7c8899}
.pgate-go{display:inline-block;margin-top:11px;font-size:11.5px;font-weight:600;color:#37dd7d}
@media (max-width:640px){.pgate-cards{grid-template-columns:1fr}}
    `}</style>
  );
}
