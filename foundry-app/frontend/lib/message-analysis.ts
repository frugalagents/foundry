import type { Message, ConsultingWorkspace } from './types'

export type AgentMsgType = 'question' | 'observation' | 'mixed'

export interface OpenQuestion {
  id: string
  text: string
}

export interface AgentMessageAnalysis {
  type: AgentMsgType
  questions: string[]
}

function normalizeLine(line: string): string {
  return line
    .trim()
    .replace(/^[-*]\s+/, '')
    .replace(/^\d+\.\s+/, '')
    .replace(/\s+/g, ' ')
}
function extractQuestions(content: string): string[] {
  const lines = content
    .trim()
    .split('\n')
    .map(normalizeLine)
    .filter(Boolean)

  return lines
    .filter((line) => line.includes('?'))
    .map((line) => {
      const withoutTrailingExplanation = line.replace(/\s*\([^)]*\)\s*$/, '').trim()
      return withoutTrailingExplanation
    })
    .map((line) => {
      const lastQuestionMark = line.lastIndexOf('?')
      return lastQuestionMark >= 0 ? line.slice(0, lastQuestionMark + 1).trim() : line
    })
    .filter(Boolean)
}

export function analyzeAgentMessage(content: string): AgentMessageAnalysis {
  if (!content.trim()) return { type: 'observation', questions: [] }

  const lines = content
    .trim()
    .split('\n')
    .map(normalizeLine)
    .filter(Boolean)
  const questions = extractQuestions(content)

  if (questions.length === 0) {
    return { type: 'observation', questions: [] }
  }

  const hasNarrative = lines.some((line) => !line.includes('?'))
  return {
    type: hasNarrative ? 'mixed' : 'question',
    questions,
  }
}

export function detectAgentMsgType(content: string): AgentMsgType {
  return analyzeAgentMessage(content).type
}

export function extractOpenQuestions(messages: Message[]): OpenQuestion[] {
  const openQuestions: OpenQuestion[] = []

  for (const message of messages) {
    if (message.role === 'agent') {
      const analysis = analyzeAgentMessage(message.content)
      if (analysis.questions.length > 0) {
        openQuestions.push(
          ...analysis.questions.map((question, index) => ({
            id: `${message.id}-${index}`,
            text: question,
          })),
        )
      }
      continue
    }

    if (message.role === 'user' && openQuestions.length > 0) {
      openQuestions.length = 0
    }
  }

  return openQuestions
}

export function normalizeWorkspace(workspace?: ConsultingWorkspace | null): ConsultingWorkspace {
  return {
    stage: workspace?.stage ?? '',
    recommendation: workspace?.recommendation ?? '',
    blueprint_markdown: workspace?.blueprint_markdown ?? '',
    assumptions: workspace?.assumptions ?? [],
    facts: workspace?.facts ?? [],
    operating_model: workspace?.operating_model ?? '',
    open_questions: workspace?.open_questions ?? [],
    decisions: workspace?.decisions ?? [],
    risks: workspace?.risks ?? [],
    implementation_plan: workspace?.implementation_plan ?? [],
    advisory_case: workspace?.advisory_case ?? null,
    updated_at: workspace?.updated_at,
  }
}
