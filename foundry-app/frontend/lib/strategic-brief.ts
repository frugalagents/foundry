export interface BriefOption {
  label: string
  value: string
}

export interface StrategicBrief {
  teamSize: string
  primaryDriver: string
  regulatoryContext: string
  hostingPreference: string
  timeline: string
  budgetPosture: string
  additionalContext: string
}

export interface BriefField {
  key: keyof Omit<StrategicBrief, 'additionalContext'>
  label: string
  options: BriefOption[]
}

export const STRATEGIC_BRIEF_FIELDS: BriefField[] = [
  {
    key: 'teamSize',
    label: 'Team size',
    options: [
      { label: '1-10', value: '1-10 developers' },
      { label: '10-50', value: '10-50 developers' },
      { label: '50-200', value: '50-200 developers' },
      { label: '200+', value: '200+ developers across multiple teams' },
    ],
  },
  {
    key: 'primaryDriver',
    label: 'Primary driver',
    options: [
      { label: 'Productivity', value: 'Developer productivity and faster delivery' },
      { label: 'Cost', value: 'Cost control and better utilization' },
      { label: 'Quality', value: 'Code quality, review, and SDLC automation' },
      { label: 'Strategy', value: 'Strategic platform positioning and long-term capability buildout' },
    ],
  },
  {
    key: 'regulatoryContext',
    label: 'Regulatory context',
    options: [
      { label: 'Standard', value: 'Standard commercial environment' },
      { label: 'Moderate', value: 'Moderately regulated environment' },
      { label: 'High', value: 'Highly regulated environment' },
      { label: 'Unknown', value: 'Need help deciding the right control posture' },
    ],
  },
  {
    key: 'hostingPreference',
    label: 'Hosting preference',
    options: [
      { label: 'AWS managed', value: 'Prefer AWS-managed services where possible' },
      { label: 'Hybrid', value: 'Need a hybrid design with some managed and some self-hosted components' },
      { label: 'Self-hosted', value: 'Prefer self-hosted or customer-controlled infrastructure' },
      { label: 'Recommend', value: 'Need a recommendation based on our security and scale constraints' },
    ],
  },
  {
    key: 'timeline',
    label: 'Timeline',
    options: [
      { label: 'This quarter', value: 'Need a decision or pilot this quarter' },
      { label: '6 months', value: 'Targeting rollout within 6 months' },
      { label: '12+ months', value: 'Longer-term strategic investment over 12+ months' },
      { label: 'Exploring', value: 'Still exploring and not committed to a date' },
    ],
  },
  {
    key: 'budgetPosture',
    label: 'Budget posture',
    options: [
      { label: 'Lean', value: 'Keep cost as lean as possible' },
      { label: 'Balanced', value: 'Balance cost with speed and governance' },
      { label: 'Invest', value: 'Willing to invest more for strategic advantage' },
      { label: 'Unknown', value: 'Need help understanding the likely cost tradeoffs' },
    ],
  },
]

export const EMPTY_STRATEGIC_BRIEF: StrategicBrief = {
  teamSize: '',
  primaryDriver: '',
  regulatoryContext: '',
  hostingPreference: '',
  timeline: '',
  budgetPosture: '',
  additionalContext: '',
}

export function buildStrategicBriefPrompt(
  brief: StrategicBrief,
  openQuestions: string[],
): string {
  const lines = ['Use this operating brief as the primary input:']

  for (const field of STRATEGIC_BRIEF_FIELDS) {
    const value = brief[field.key]
    if (value) lines.push(`- ${field.label}: ${value}`)
  }

  if (brief.additionalContext.trim()) {
    lines.push(`- Additional context: ${brief.additionalContext.trim()}`)
  }

  if (openQuestions.length > 0) {
    lines.push('')
    lines.push('Please use this brief to resolve these open questions where possible:')
    for (const question of openQuestions.slice(0, 4)) {
      lines.push(`- ${question.replace(/\s+/g, ' ').trim()}`)
    }
  }

  lines.push('')
  lines.push('Do not keep drilling into generic setup questions.')
  lines.push('If anything is still missing, ask only the minimum blocking questions.')
  lines.push('Otherwise give me:')
  lines.push('1. Your recommended target architecture')
  lines.push('2. The key tradeoffs and risks')
  lines.push('3. The next decisions I should make')

  return lines.join('\n')
}
