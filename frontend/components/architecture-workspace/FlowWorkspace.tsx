'use client';

// Assembles the approved architecture into React Flow blocks/wires and pairs
// the canvas with the discovery-questions side panel. The block content,
// per-block questions, live-answer wiring, and evidence display are shared with
// the approved design; only the diagram engine is now React Flow.

import { useCallback, useMemo, useState } from 'react';
import type {
  ArchitectureWorkspaceProjection,
  EvidenceClaim,
  RequirementValue,
} from '@/lib/architecture-workspace';
import { FlowCanvas, type FlowBlock, type FlowWire } from './FlowCanvas';
import { BLOCKS, WIRES, PHASE, GROUP_COLOR, ACTIVE_MAP, LAYOUT, GROUP_LAYOUT, type BlockDef } from './architecture-model';
import { generateArchitecture, chatArchitecture, type GeneratedArchitecture } from '@/lib/architecture-api';

interface BlueprintContext { name: string; description: string; type: string }
const TYPE_LABEL: Record<string, string> = {
  coding: 'Agentic Coding Platform', internal: 'Internal-Facing Platform',
  'customer-facing': 'Customer-Facing Agentic Platform', saas: 'SaaS Decomposition', marketplace: 'Marketplace',
};

interface Props {
  projection: ArchitectureWorkspaceProjection;
  blueprint?: BlueprintContext | null;
  onAnswer?: (requirementId: string, value: RequirementValue) => Promise<void> | void;
  applying?: boolean;
}

export function FlowWorkspace({ projection, blueprint, onAnswer, applying }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState<GeneratedArchitecture | null>(null);
  const [genError, setGenError] = useState<string | null>(null);
  const [chatLog, setChatLog] = useState<{ role: 'user' | 'agent'; text: string }[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatBusy, setChatBusy] = useState(false);

  async function sendChat() {
    const msg = chatInput.trim();
    if (!msg || chatBusy) return;
    setChatInput('');
    setChatLog((l) => [...l, { role: 'user', text: msg }]);
    setChatBusy(true);
    try {
      const res = await chatArchitecture(msg);
      const applied = Object.keys(res.applied_answers).length;
      setChatLog((l) => [...l, {
        role: 'agent',
        text: applied ? res.reply : (res.reply || 'I couldn’t map that to a decision — try naming a specific choice.'),
      }]);
    } catch {
      setChatLog((l) => [...l, { role: 'agent', text: 'Something went wrong — try again.' }]);
    } finally {
      setChatBusy(false);
    }
  }

  async function runGenerate() {
    setGenerating(true);
    setGenError(null);
    try {
      setGenerated(await generateArchitecture());
    } catch {
      setGenError('Could not generate the architecture. Try again.');
    } finally {
      setGenerating(false);
    }
  }

  const activeComponentIds = useMemo(() => {
    const set = new Set<string>();
    for (const plane of projection.architecture.planes)
      for (const c of plane.components) if (c.status === 'added') set.add(c.id);
    return set;
  }, [projection]);

  const isActive = useCallback((id: string) =>
    (ACTIVE_MAP[id] ?? []).some((cid) => activeComponentIds.has(cid)), [activeComponentIds]);

  // components changed by the most recent revision → animate their wires
  const recentlyChanged = useMemo(() => {
    const set = new Set<string>();
    const transitions = projection.decision_history?.transitions ?? [];
    const last = transitions[transitions.length - 1];
    for (const c of last?.architecture_delta.components.added ?? []) set.add(c.component_id);
    for (const c of last?.architecture_delta.components.removed ?? []) set.add(c.component_id);
    return set;
  }, [projection]);

  const byClaimId = useMemo(() => {
    const m = new Map<string, EvidenceClaim>();
    for (const e of projection.evidence ?? []) m.set(e.claim_id, e);
    return m;
  }, [projection]);

  const evidenceForRequirement = useCallback((requirementId?: string): EvidenceClaim[] => {
    if (!requirementId) return [];
    const claims: EvidenceClaim[] = [];
    for (const t of projection.decision_trace) {
      if (t.requirement_ids.includes(requirementId)) {
        for (const cid of t.evidence_claim_ids ?? []) {
          const c = byClaimId.get(cid);
          if (c && !claims.includes(c)) claims.push(c);
        }
      }
    }
    return claims;
  }, [projection, byClaimId]);

  const blocks = useMemo<FlowBlock[]>(() =>
    Object.values(BLOCKS).map((b: BlockDef) => {
      const pos = LAYOUT[b.id];
      return {
        id: b.id, label: b.t, detail: b.d, group: b.group,
        x: pos?.x ?? 0, y: pos?.y ?? 0, w: pos?.w, h: pos?.h,
        active: isActive(b.id),
        answerable: Boolean(b.requirement),
        heart: b.id === 'harness',
      };
    }), [isActive]);

  const wires = useMemo<FlowWire[]>(() =>
    WIRES.map((w) => {
      // animate a wire if either endpoint block maps to a recently-changed component
      const touches = (blockId: string) =>
        (ACTIVE_MAP[blockId] ?? []).some((cid) => recentlyChanged.has(cid));
      return { ...w, animated: touches(w.source) || touches(w.target) };
    }), [recentlyChanged]);

  const sel = selected ? BLOCKS[selected] : null;
  const selValue = sel?.requirement
    ? projection.requirements.find((r) => r.id === sel.requirement)?.value
    : undefined;
  const coerce = (v: string): RequirementValue => (v === 'true' ? true : v === 'false' ? false : v);
  const selClaims = evidenceForRequirement(sel?.requirement);

  return (
    <div className="fw-root">
      <FwStyles />
      <div className="fw-head">
        <div className="fw-brand">
          <div className="fw-mark" />
          <div>
            <h1>{blueprint?.name ?? 'Coding Agent Platform'}</h1>
            <p>{blueprint
              ? <>{TYPE_LABEL[blueprint.type] ?? blueprint.type}{blueprint.description ? ` · ${blueprint.description}` : ''}</>
              : 'Logical reference architecture · click any block for its design decisions'}</p>
          </div>
        </div>
        <div className="fw-legend">
          <span><i className="ln req" />runtime call</span>
          <span><i className="ln sup" />loads / composes</span>
          <span><i className="ln gov" />access &amp; policy</span>
        </div>
        <button className="fw-generate" onClick={runGenerate} disabled={generating}>
          {generating ? 'Generating…' : '✦ Generate my architecture'}
        </button>
      </div>

      <div className="fw-main">
        <div className="fw-canvas-wrap">
          <FlowCanvas blocks={blocks} wires={wires} groups={GROUP_LAYOUT} selected={selected} onSelect={setSelected} />
        </div>

        <aside className="fw-aside">
          <div className="fw-aside-scroll">
          {!sel ? (
            <div>
              {blueprint && (
                <div className="fw-bp">
                  <span className="fw-bp-kicker">Blueprint</span>
                  <h2>{blueprint.name}</h2>
                  <span className="fw-bp-type">{TYPE_LABEL[blueprint.type] ?? blueprint.type}</span>
                  {blueprint.description && <p className="fw-bp-desc">{blueprint.description}</p>}
                </div>
              )}
              <div className="fw-empty">
                <div className="ic">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#7d9bff" strokeWidth="1.6"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" opacity=".6" /></svg>
                </div>
                <h4>Answer the discovery questions</h4>
                <p>Click any block on the canvas to see the <b>questions for this blueprint</b> — as you answer, the architecture changes to fit.</p>
              </div>
            </div>
          ) : (
            <div>
              <div className="fw-hd" style={kVars(GROUP_COLOR[sel.group])}>
                <span className="fw-kicker"><i style={{ width: 7, height: 7, borderRadius: 2, background: GROUP_COLOR[sel.group], display: 'inline-block' }} />{PHASE[sel.group]}</span>
                <h2>{sel.t}</h2>
                <p>{sel.what}</p>
              </div>

              {sel.requirement && sel.answers && (
                <div className="fw-sec" style={kVars(GROUP_COLOR[sel.group])}>
                  <h3><span className="bar" />Answer this decision <span className="fw-live">live</span></h3>
                  <div className="fw-answers">
                    {sel.answers.map((a) => (
                      <button key={a.value} type="button" disabled={applying}
                        className={`fw-answer${selValue === coerce(a.value) ? ' on' : ''}`}
                        onClick={() => onAnswer?.(sel.requirement!, coerce(a.value))}>
                        <span className="dot" />{a.label}
                      </button>
                    ))}
                  </div>
                  {applying && <p className="fw-current">Updating architecture…</p>}
                  {!applying && selValue != null && <p className="fw-current">Current: <b>{String(selValue)}</b> — the diagram reflects this.</p>}
                  {selClaims.length > 0 && (
                    <div className="fw-evidence">
                      {selClaims.map((c) => (
                        <div className="fw-claim" key={c.claim_id}>
                          <p>{c.statement}</p>
                          <div className="src">
                            {c.source_title ?? c.source_id} · {c.source_locator}
                            {c.source_uri && <a href={c.source_uri} target="_blank" rel="noreferrer">source ↗</a>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="fw-sec" style={kVars(GROUP_COLOR[sel.group])}>
                <h3><span className="bar" />Architecture decisions</h3>
                {sel.dec.map((d, i) => (
                  <div className="fw-dec" key={i}>
                    <div className="q">{d.q}</div>
                    {d.opts.map((o, j) => (
                      <div className="opt" key={j}><span className="k">▸</span><span dangerouslySetInnerHTML={{ __html: o }} /></div>
                    ))}
                  </div>
                ))}
              </div>

              <div className="fw-sec" style={kVars(GROUP_COLOR[sel.group])}>
                <h3><span className="bar" />Best practices</h3>
                <ul className="fw-plist">{sel.p.map((x, i) => <li key={i}>{x}</li>)}</ul>
              </div>
            </div>
          )}
          </div>

          <div className="fw-chat">
            <div className="fw-chat-hd">◇ Discovery chat<span>describe the customer — it fills the blueprint</span></div>
            <div className="fw-chat-log">
              {chatLog.length === 0 && (
                <p className="fw-chat-hint">e.g. “Regulated bank, ~3-person platform team, no self-hosting, standardise on Bedrock.”</p>
              )}
              {chatLog.map((m, i) => (
                <div key={i} className={`fw-msg ${m.role}`}>{m.text}</div>
              ))}
              {chatBusy && <div className="fw-msg agent">…</div>}
            </div>
            <div className="fw-chat-input">
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') sendChat(); }}
                placeholder="Describe the customer or a decision…"
                disabled={chatBusy}
              />
              <button onClick={sendChat} disabled={chatBusy || !chatInput.trim()}>Send</button>
            </div>
          </div>
        </aside>
      </div>

      {(generated || genError) && (
        <div className="fw-modal-scrim" onClick={() => { setGenerated(null); setGenError(null); }}>
          <div className="fw-modal" onClick={(e) => e.stopPropagation()}>
            <div className="fw-modal-hd">
              <div>
                <span className="fw-modal-kicker">Purpose-built architecture</span>
                <h2>{blueprint?.name ?? 'Coding Agent Platform'}</h2>
              </div>
              <button className="fw-modal-x" onClick={() => { setGenerated(null); setGenError(null); }}>✕</button>
            </div>
            {genError && <div className="fw-modal-body"><p className="fw-err">{genError}</p></div>}
            {generated && (
              <div className="fw-modal-body">
                <div className={`fw-verdict ${generated.guard.passed ? 'ok' : 'veto'}`}>
                  {generated.guard.passed
                    ? '✓ Passed the deterministic guard — no violated constraints or invented integrations.'
                    : `✕ Guard vetoed ${generated.guard.violations.length} item(s).`}
                  <span className="fw-verdict-meta">guard {generated.guard.guard_version} · {generated.source}</span>
                </div>
                {!generated.guard.passed && (
                  <ul className="fw-viol">{generated.guard.violations.map((v, i) => <li key={i}><b>{v.check}</b> — {v.detail}</li>)}</ul>
                )}

                <h3 className="fw-modal-h3">Solution stack</h3>
                <div className="fw-stack">
                  {generated.stack.map((s) => (
                    <div className="fw-stack-row" key={s.box_id}>
                      <span className="fw-stack-box">{s.box_id}</span>
                      <span className="fw-stack-chosen">{s.chosen}</span>
                      {s.alternatives.length > 0 && (
                        <span className="fw-stack-alts">over {s.alternatives.join(', ')}</span>
                      )}
                    </div>
                  ))}
                </div>

                {generated.cascades.length > 0 && (
                  <>
                    <h3 className="fw-modal-h3">Downstream decisions this opens</h3>
                    <ul className="fw-casc">{generated.cascades.map((c, i) => <li key={i}>{c.note}</li>)}</ul>
                  </>
                )}

                <h3 className="fw-modal-h3">
                  Rationale
                  <span className={`fw-ground ${generated.grounded ? 'on' : 'off'}`}>
                    {generated.grounded ? 'grounded in knowledge base' : 'ungrounded (KB unavailable)'}
                  </span>
                </h3>
                <div className="fw-rationale">{generated.rationale}</div>

                {generated.critic_concerns.length > 0 && (
                  <>
                    <h3 className="fw-modal-h3">Critic flags</h3>
                    <ul className="fw-casc">{generated.critic_concerns.map((c, i) => <li key={i}>{c}</li>)}</ul>
                  </>
                )}

                <p className="fw-record-note">
                  A Decision Record was {generated.persisted ? 'saved' : 'generated'} — answers, proposal,
                  guard verdict, citations, and version stamps. Reproducible-with-trace, not bit-identical.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function kVars(col: string): React.CSSProperties {
  return { ['--k-fg' as string]: col, ['--k-bg' as string]: `${col}18`, ['--k-bd' as string]: `${col}44` };
}

function FwStyles() {
  return (
    <style>{`
.fw-root{--bg:#0e1116;--bg-soft:#12161d;--line:#242e3b;--line-soft:#1c2531;--ink:#e6e9ef;--ink-dim:#a7b2c2;--muted:#7c8899;--muted2:#556072;
  --font:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;--font-mono:"JetBrains Mono",ui-monospace,Menlo,monospace;
  background:radial-gradient(1000px 560px at 62% -10%,#1a35601c,transparent),var(--bg);color:var(--ink);font:14px/1.55 var(--font);display:flex;flex-direction:column;height:100vh;overflow:hidden}
.fw-root *{box-sizing:border-box}
.fw-head{padding:14px 24px;border-bottom:1px solid var(--line-soft);display:flex;align-items:center;gap:16px;background:linear-gradient(180deg,#0f131a,#0e1116);flex-shrink:0}
.fw-brand{display:flex;align-items:center;gap:12px}
.fw-mark{width:32px;height:32px;border-radius:9px;background:conic-gradient(from 210deg,#37dd7d,#4cc4f5,#7d9bff,#b98cf0,#37dd7d);box-shadow:0 0 0 1px #ffffff12;position:relative}
.fw-mark::after{content:"";position:absolute;inset:11px;border-radius:4px;background:var(--bg)}
.fw-brand h1{font-size:15.5px;margin:0;font-weight:650;letter-spacing:-.15px}
.fw-brand p{margin:1px 0 0;font-size:11px;color:var(--muted)}
.fw-legend{margin-left:auto;display:flex;gap:13px;font-size:10.5px;color:var(--muted);align-items:center}
.fw-legend span{display:flex;align-items:center;gap:6px}
.fw-legend .ln{width:20px;height:0;border-top:2px solid #4cc4f5}
.fw-legend .ln.sup{border-top:2px dashed #2dd4bf}
.fw-legend .ln.gov{border-top:2px dashed #7d9bff}
.fw-main{flex:1;display:flex;min-height:0}
.fw-canvas-wrap{flex:1;position:relative;min-width:0}
.fw-aside{width:412px;border-left:1px solid var(--line-soft);background:var(--bg-soft);flex-shrink:0;display:flex;flex-direction:column;min-height:0}
.fw-aside-scroll{flex:1;overflow:auto;min-height:0}
.fw-chat{border-top:1px solid var(--line-soft);background:#0d1119;display:flex;flex-direction:column;max-height:44%}
.fw-chat-hd{padding:10px 16px 8px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#37dd7d;display:flex;flex-direction:column;gap:2px}
.fw-chat-hd span{font-size:9.5px;font-weight:500;text-transform:none;letter-spacing:0;color:var(--muted)}
.fw-chat-log{flex:1;overflow:auto;padding:6px 16px;display:flex;flex-direction:column;gap:7px;min-height:70px}
.fw-chat-hint{margin:0;font-size:11px;color:var(--muted2);font-style:italic;line-height:1.5}
.fw-msg{font-size:12px;line-height:1.45;padding:7px 10px;border-radius:9px;max-width:90%}
.fw-msg.user{align-self:flex-end;background:#1d3a2b;color:#d6f0e2;border:1px solid #37dd7d44}
.fw-msg.agent{align-self:flex-start;background:#161d27;color:var(--ink-dim);border:1px solid var(--line)}
.fw-chat-input{display:flex;gap:8px;padding:10px 14px 12px;border-top:1px solid var(--line-soft)}
.fw-chat-input input{flex:1;background:#0e1116;border:1px solid var(--line);border-radius:8px;padding:9px 11px;color:var(--ink);font-size:12.5px;font-family:inherit}
.fw-chat-input input:focus{outline:none;border-color:#37dd7d}
.fw-chat-input button{background:#37dd7d;color:#08131a;border:none;border-radius:8px;padding:0 15px;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit}
.fw-chat-input button:disabled{opacity:.5;cursor:default}
.fw-bp{padding:22px 26px 4px;border-bottom:1px solid var(--line-soft)}
.fw-bp-kicker{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.11em;color:#37dd7d}
.fw-bp h2{margin:8px 0 0;font-size:19px;font-weight:680;letter-spacing:-.3px}
.fw-bp-type{display:inline-block;margin-top:8px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#0e1a13;background:#37dd7d;padding:3px 9px;border-radius:6px}
.fw-bp-desc{margin:12px 0 0;font-size:12.5px;line-height:1.6;color:var(--ink-dim)}
.fw-empty{padding:60px 34px;color:var(--muted2);text-align:center}
.fw-empty .ic{width:58px;height:58px;border-radius:15px;margin:0 auto 20px;background:#ffffff06;border:1px solid var(--line);display:grid;place-items:center}
.fw-empty h4{color:var(--ink-dim);font-size:14px;margin:0 0 8px;font-weight:600}
.fw-empty p{margin:0;font-size:12.5px;line-height:1.65}
.fw-hd{padding:24px 26px 20px;border-bottom:1px solid var(--line-soft);position:sticky;top:0;background:linear-gradient(180deg,var(--bg-soft),#0f141b);z-index:3}
.fw-kicker{display:inline-flex;align-items:center;gap:7px;font-size:10px;text-transform:uppercase;letter-spacing:.11em;margin-bottom:12px;font-weight:700;padding:4px 10px;border-radius:20px;background:var(--k-bg);color:var(--k-fg);border:1px solid var(--k-bd)}
.fw-hd h2{margin:0;font-size:20px;font-weight:680;letter-spacing:-.3px}
.fw-hd p{margin:11px 0 0;color:var(--ink-dim);font-size:13px;line-height:1.65}
.fw-sec{padding:20px 26px;border-bottom:1px solid var(--line-soft)}
.fw-sec h3{margin:0 0 14px;font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);font-weight:700;display:flex;align-items:center;gap:8px}
.fw-sec h3 .bar{width:16px;height:2px;border-radius:2px;background:var(--k-fg)}
.fw-live{margin-left:auto;font-size:8px;color:#0e1a13;background:#37dd7d;padding:2px 6px;border-radius:5px;letter-spacing:.06em}
.fw-answers{display:flex;flex-direction:column;gap:7px}
.fw-answer{display:flex;align-items:center;gap:9px;text-align:left;background:#ffffff05;border:1px solid var(--line);border-radius:9px;padding:10px 12px;color:var(--ink-dim);font-size:12px;cursor:pointer;font-family:inherit;transition:.14s}
.fw-answer:hover{border-color:#37dd7d;color:var(--ink)}
.fw-answer.on{border-color:#37dd7d;background:#14271b;color:var(--ink)}
.fw-answer .dot{width:8px;height:8px;border-radius:50%;border:1px solid var(--muted)}
.fw-answer.on .dot{background:#37dd7d;border-color:#37dd7d}
.fw-answer:disabled{opacity:.5;cursor:default}
.fw-current{margin:10px 0 0;font-size:11px;color:var(--muted)}
.fw-evidence{margin-top:12px;display:flex;flex-direction:column;gap:8px}
.fw-claim{border:1px solid #2dd4bf3a;background:#0f201d;border-radius:9px;padding:10px 11px}
.fw-claim p{margin:0;font-size:11.5px;line-height:1.45;color:var(--ink-dim)}
.fw-claim .src{margin-top:6px;font-size:9.5px;color:var(--muted);display:flex;gap:6px;align-items:center}
.fw-claim .src a{margin-left:auto;color:#2dd4bf;text-decoration:none}
.fw-dec{border:1px solid var(--line);background:#ffffff05;border-radius:12px;padding:14px 15px;margin-bottom:11px}
.fw-dec .q{font-weight:600;font-size:13px;margin-bottom:10px;color:var(--ink);line-height:1.4}
.fw-dec .opt{display:flex;gap:9px;font-size:12px;color:var(--ink-dim);padding:6px 0;border-top:1px solid var(--line-soft);line-height:1.45}
.fw-dec .opt:first-of-type{border-top:none}
.fw-dec .opt .k{color:var(--muted2);flex-shrink:0;margin-top:1px}
.fw-dec .opt b{color:var(--ink);font-weight:600}
.fw-plist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:9px}
.fw-plist li{padding-left:26px;position:relative;color:var(--ink-dim);font-size:12.5px;line-height:1.5}
.fw-plist li::before{content:"✓";position:absolute;left:0;top:0;color:#37dd7d;font-weight:800;background:#37dd7d18;width:18px;height:18px;border-radius:6px;display:grid;place-items:center;font-size:10px}
.fw-generate{margin-left:14px;background:linear-gradient(180deg,#37dd7d,#22c55e);color:#08131a;border:none;border-radius:9px;padding:8px 16px;font-size:12.5px;font-weight:700;cursor:pointer;font-family:inherit;transition:.15s;white-space:nowrap}
.fw-generate:hover{filter:brightness(1.08);box-shadow:0 0 22px -6px #37dd7d}
.fw-generate:disabled{opacity:.6;cursor:default}
.fw-modal-scrim{position:fixed;inset:0;background:#060a0fcc;backdrop-filter:blur(3px);z-index:50;display:flex;align-items:flex-start;justify-content:center;padding:48px 20px;overflow:auto}
.fw-modal{width:100%;max-width:760px;background:linear-gradient(180deg,#141a24,#0f141c);border:1px solid #2a3446;border-radius:16px;box-shadow:0 40px 90px -30px #000;overflow:hidden}
.fw-modal-hd{display:flex;align-items:flex-start;justify-content:space-between;padding:22px 26px 18px;border-bottom:1px solid #1c2531}
.fw-modal-kicker{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.11em;color:#37dd7d}
.fw-modal-hd h2{margin:8px 0 0;font-size:20px;font-weight:680;letter-spacing:-.3px}
.fw-modal-x{background:#ffffff08;border:1px solid #2a3446;color:#a7b2c2;width:30px;height:30px;border-radius:8px;cursor:pointer;font-size:13px}
.fw-modal-body{padding:22px 26px 28px}
.fw-err{color:#fb7185;font-size:13px}
.fw-verdict{border-radius:10px;padding:12px 14px;font-size:12.5px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.fw-verdict.ok{background:#12251c;border:1px solid #37dd7d55;color:#c7f0da}
.fw-verdict.veto{background:#241318;border:1px solid #fb718555;color:#f6c9d1}
.fw-verdict-meta{margin-left:auto;font-size:10px;font-family:var(--font-mono);color:#7c8899}
.fw-viol{margin:10px 0 0;padding-left:18px;font-size:12px;color:#f6c9d1}
.fw-modal-h3{margin:24px 0 10px;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#8b98ab;font-weight:700;display:flex;align-items:center;gap:10px}
.fw-ground{font-size:9px;font-weight:700;text-transform:none;letter-spacing:0;padding:2px 7px;border-radius:5px}
.fw-ground.on{background:#2dd4bf22;color:#5eead4}
.fw-ground.off{background:#f0a85022;color:#f0c088}
.fw-stack{display:flex;flex-direction:column;gap:8px}
.fw-stack-row{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;background:#ffffff05;border:1px solid #1c2531;border-radius:9px;padding:10px 13px}
.fw-stack-box{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#7c8899;min-width:100px}
.fw-stack-chosen{font-size:13.5px;font-weight:650;color:#e6e9ef}
.fw-stack-alts{font-size:11px;color:#6a7789;font-style:italic}
.fw-casc{margin:0;padding-left:18px;font-size:12.5px;color:#a7b2c2;line-height:1.6}
.fw-rationale{font-size:13px;line-height:1.7;color:#c3ccd8;white-space:pre-wrap}
.fw-record-note{margin-top:22px;padding-top:16px;border-top:1px solid #1c2531;font-size:11px;color:#6a7789;line-height:1.6}
    `}</style>
  );
}
