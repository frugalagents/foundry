import type { Message } from './types'

export type AdvisoryStage = 'discovery' | 'solutioning' | 'blueprint'
export type AdvisoryWorkspaceTab = 'questions' | 'assumptions' | 'blueprint' | 'architecture'

export function normalizeAdvisoryStage(value?: string | null): AdvisoryStage | undefined {
  switch ((value ?? '').trim().toLowerCase()) {
    case 'discovery':
      return 'discovery'
    case 'solutioning':
      return 'solutioning'
    case 'blueprint':
      return 'blueprint'
    default:
      return undefined
  }
}

export function resolveAdvisoryStage(
  value: string | null | undefined,
  _messages: Message[],
  _hasArchitecture: boolean,
): AdvisoryStage {
  const normalized = normalizeAdvisoryStage(value)
  if (normalized) return normalized
  return 'discovery'
}

export function preferredWorkspaceTab(
  stage: AdvisoryStage | undefined,
  {
    questionCount,
    blueprintReady,
    architectureReady,
  }: {
    questionCount: number
    blueprintReady: boolean
    architectureReady: boolean
  },
): AdvisoryWorkspaceTab {
  if (questionCount > 0) return 'questions'

  switch (stage) {
    case 'discovery':
      return 'assumptions'
    case 'solutioning':
      return architectureReady ? 'assumptions' : 'questions'
    case 'blueprint':
      return blueprintReady ? 'blueprint' : architectureReady ? 'architecture' : 'assumptions'
    default:
      return blueprintReady ? 'blueprint' : architectureReady ? 'architecture' : 'assumptions'
  }
}
