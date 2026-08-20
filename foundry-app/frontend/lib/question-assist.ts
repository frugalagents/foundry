export interface GuidedAnswerOption {
  label: string
  answer: string
}

export interface GuidedQuestionAssist {
  question: string
  fieldLabel: string
  options: GuidedAnswerOption[]
}

function cleanQuestionText(question: string): string {
  return question
    .replace(/\*\*/g, '')
    .replace(/`/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function makeAnswer(fieldLabel: string, answer: string): string {
  return `- ${fieldLabel}: ${answer}`
}

function fallbackLabel(question: string): string {
  const cleaned = cleanQuestionText(question).replace(/\?+$/, '')
  if (!cleaned) return 'Answer'
  return cleaned.length > 48 ? `${cleaned.slice(0, 45).trim()}...` : cleaned
}

export function buildQuestionAssist(question: string): GuidedQuestionAssist {
  const cleaned = cleanQuestionText(question)
  const lower = cleaned.toLowerCase()

  if (/\bteam size\b|\bhow many developers\b|\bhow many engineers\b|\bhow many people\b/.test(lower)) {
    const fieldLabel = 'Team size'
    return {
      question: cleaned,
      fieldLabel,
      options: [
        { label: '1-10', answer: makeAnswer(fieldLabel, '1-10 developers') },
        { label: '10-50', answer: makeAnswer(fieldLabel, '10-50 developers') },
        { label: '50-200', answer: makeAnswer(fieldLabel, '50-200 developers') },
        { label: '200+', answer: makeAnswer(fieldLabel, '200+ developers across multiple teams') },
      ],
    }
  }

  if (/\bdriving this\b|\bprimary driver\b|\bobjective\b|\bgoal\b|\bwhy now\b|\bwhat's driving\b/.test(lower)) {
    const fieldLabel = 'Primary driver'
    return {
      question: cleaned,
      fieldLabel,
      options: [
        { label: 'Productivity', answer: makeAnswer(fieldLabel, 'Developer productivity and faster delivery') },
        { label: 'Cost control', answer: makeAnswer(fieldLabel, 'Cost control and better utilization') },
        { label: 'Code review', answer: makeAnswer(fieldLabel, 'Code review and engineering workflow automation') },
        { label: 'Need rec', answer: makeAnswer(fieldLabel, 'I want your recommendation based on our context') },
      ],
    }
  }

  if (/\bindustry\b|\bregulated\b|\bcompliance\b|\bfinance\b|\bhealthcare\b|\bdefense\b/.test(lower)) {
    const fieldLabel = 'Regulatory context'
    return {
      question: cleaned,
      fieldLabel,
      options: [
        { label: 'High', answer: makeAnswer(fieldLabel, 'Highly regulated environment') },
        { label: 'Moderate', answer: makeAnswer(fieldLabel, 'Moderately regulated environment') },
        { label: 'Standard', answer: makeAnswer(fieldLabel, 'Standard commercial environment') },
        { label: 'Unsure', answer: makeAnswer(fieldLabel, 'I need help determining the right control posture') },
      ],
    }
  }

  if (/\btimeline\b|\burgency\b|\bwhen\b|\bdeadline\b|\bthis quarter\b|\bthis year\b/.test(lower)) {
    const fieldLabel = 'Timeline'
    return {
      question: cleaned,
      fieldLabel,
      options: [
        { label: 'This quarter', answer: makeAnswer(fieldLabel, 'We need a decision or pilot this quarter') },
        { label: '6 months', answer: makeAnswer(fieldLabel, 'We are targeting rollout within 6 months') },
        { label: '12+ months', answer: makeAnswer(fieldLabel, 'This is a longer-term strategic investment over 12+ months') },
        { label: 'Exploring', answer: makeAnswer(fieldLabel, 'We are still exploring and not committed to a date') },
      ],
    }
  }

  if (/\baws\b|\bcloud\b|\bhost(?:ing)?\b|\bdeploy\b|\bself-hosted\b|\bon-?prem\b/.test(lower)) {
    const fieldLabel = 'Hosting preference'
    return {
      question: cleaned,
      fieldLabel,
      options: [
        { label: 'AWS managed', answer: makeAnswer(fieldLabel, 'Prefer AWS-managed services where possible') },
        { label: 'Hybrid', answer: makeAnswer(fieldLabel, 'Need a hybrid design with some managed and some self-hosted components') },
        { label: 'Self-hosted', answer: makeAnswer(fieldLabel, 'Prefer self-hosted or customer-controlled infrastructure') },
        { label: 'Need rec', answer: makeAnswer(fieldLabel, 'I want your recommendation based on our security and scale needs') },
      ],
    }
  }

  if (/\bbudget\b|\bcost\b|\bspend\b/.test(lower)) {
    const fieldLabel = 'Budget posture'
    return {
      question: cleaned,
      fieldLabel,
      options: [
        { label: 'Lean', answer: makeAnswer(fieldLabel, 'Keep cost as lean as possible') },
        { label: 'Balanced', answer: makeAnswer(fieldLabel, 'Balance cost with speed and governance') },
        { label: 'Invest', answer: makeAnswer(fieldLabel, 'Willing to invest more for strategic advantage') },
        { label: 'Unsure', answer: makeAnswer(fieldLabel, 'I need help sizing the likely budget tradeoffs') },
      ],
    }
  }

  const fieldLabel = fallbackLabel(cleaned)
  return {
    question: cleaned,
    fieldLabel,
    options: [
      { label: 'Yes', answer: makeAnswer(fieldLabel, 'Yes') },
      { label: 'No', answer: makeAnswer(fieldLabel, 'No') },
      { label: 'Partially', answer: makeAnswer(fieldLabel, 'Partially') },
      { label: 'Need rec', answer: makeAnswer(fieldLabel, 'I want your recommendation here') },
    ],
  }
}

export function buildStructuredReplyTemplate(questions: string[]): string {
  const visible = questions.slice(0, 4).map(buildQuestionAssist)
  if (visible.length === 0) return ''

  return [
    'Here are my answers:',
    ...visible.map((assist) => `- ${assist.fieldLabel}: `),
  ].join('\n')
}
