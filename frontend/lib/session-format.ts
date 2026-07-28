import type { Session, SessionStatus, Customer } from './types';

// Human labels for each pipeline step (single source of truth, 1-indexed → 10 steps).
export const STEP_NAMES = [
  'Evidence', 'Decision', 'Architecture', 'Requirements', 'Controls',
  'AWS map', 'Risks', 'Roadmap', 'Cost', 'Blueprint',
] as const;

const STATUS_LABEL: Record<SessionStatus, string> = {
  active: 'Draft',
  intake: 'Intake', scoring: 'Pattern scoring', components: 'Components',
  innovation: 'Innovations', services: 'Service map', antipatterns: 'Risks',
  phasing: 'Roadmap', blueprint: 'Blueprint', complete: 'Complete',
};

export const statusLabel = (s?: SessionStatus): string =>
  s ? STATUS_LABEL[s] ?? s : 'Draft';

export const isComplete = (s: Session): boolean => s.status === 'complete';

/** Prettify a pattern id/name: "pattern:federated" → "Federated". */
export function prettyPattern(pattern?: string | null): string {
  if (!pattern) return '';
  const tail = pattern.includes(':') ? pattern.split(':').pop()! : pattern;
  return tail.charAt(0).toUpperCase() + tail.slice(1);
}

/**
 * A recognizable title for a session. Uses the user-set name when it is real
 * (not the old auto "Session <date>" placeholder); otherwise composes one from
 * the pattern + industry, degrading to a draft label.
 */
export function sessionTitle(s: Session): string {
  const name = s.title?.trim() || s.name?.trim();
  if (name && !/^session\s+\d/i.test(name)) return name;

  const pattern = prettyPattern(s.recommendation ?? s.pattern_selected);
  const industry = s.intake_answers?.industry as string | undefined;
  const workload = s.intake_answers?.primary_workload as string | undefined;
  if (pattern) {
    return industry ? `${pattern} · ${industry}` : `${pattern} platform`;
  }
  if (workload) return `${prettyPattern(workload.replaceAll('_', ' '))} assessment`;
  if (industry) return `${industry} draft`;
  return 'Untitled draft';
}

/** Compose the default title to send at creation time. */
export function suggestedTitle(customer: Pick<Customer, 'industry'>): string {
  const base = customer.industry ? `${customer.industry} platform` : 'New platform';
  return base;
}

/** Compact metadata line for a session card. */
export function sessionMeta(s: Session): string {
  const parts: string[] = [];
  const industry = s.intake_answers?.industry as string | undefined;
  if (industry) parts.push(industry);
  const workload = s.intake_answers?.primary_workload as string | undefined;
  if (workload) parts.push(workload.replaceAll('_', ' '));
  const compliance = (
    s.intake_answers?.['data.regulations'] ?? s.intake_answers?.compliance_regime
  ) as unknown;
  if (Array.isArray(compliance) && compliance.length && !compliance.includes('none')) {
    parts.push(compliance.map((c) => String(c).toUpperCase()).join(', '));
  }
  if (!isComplete(s)) parts.push(`Step ${s.current_step || 1} of 10`);
  return parts.join(' · ');
}

export function workloadLabel(workload?: string | null): string {
  if (!workload) return 'Not selected';
  return workload
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function evidenceLabel(state: Session['evidence_state']): string {
  return {
    not_started: 'Not evaluated',
    provisional: 'Provisional',
    decision_ready: 'Decision-ready',
    overridden: 'Overridden',
  }[state];
}

/** Relative time: "just now", "3h ago", "5d ago", or a date. */
export function relativeTime(iso?: string): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diff = Date.now() - then;
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  if (day < 30) return `${day}d ago`;
  return new Date(iso).toLocaleDateString();
}

/** A session is a stale draft if not complete and untouched > 14 days. */
export function isStaleDraft(s: Session): boolean {
  if (isComplete(s)) return false;
  const t = new Date(s.updated_at).getTime();
  if (Number.isNaN(t)) return false;
  return Date.now() - t > 14 * 24 * 60 * 60 * 1000;
}
