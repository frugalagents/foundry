import { create } from 'zustand'
import type {
  Message,
  ConversationRow,
  ArchNode,
  ArchEdge,
  Module,
  ConsultingWorkspace,
} from '@/lib/types'

interface AppState {
  // ── Auth ────────────────────────────────────────────────────────────────────
  userId: string | null
  userName: string | null
  isAdmin: boolean
  setUser: (id: string, name: string, admin: boolean) => void

  // ── Active session ──────────────────────────────────────────────────────────
  activeCustomerId: string | null
  activeSessionId: string | null
  activeModule: string | null
  setActiveSession: (customerId: string, sessionId: string, module?: string) => void
  clearActiveSession: () => void

  // ── Messages ────────────────────────────────────────────────────────────────
  messages: Message[]
  appendMessage: (msg: Message) => void
  appendChunk: (id: string, chunk: string) => void
  finalizeMessage: (id: string) => void
  clearMessages: () => void

  // ── Consulting workspace ────────────────────────────────────────────────────
  workspace: ConsultingWorkspace | null
  setWorkspace: (workspace: ConsultingWorkspace | null) => void
  clearWorkspace: () => void

  // ── Architecture canvas ─────────────────────────────────────────────────────
  canvasVisible: boolean
  canvasNodes: ArchNode[]
  canvasEdges: ArchEdge[]
  baselineNodeIds: string[]   // IDs from the first canvas update — everything else is a customer addition
  setCanvas: (nodes: ArchNode[], edges: ArchEdge[]) => void
  showCanvas: () => void
  hideCanvas: () => void

  // ── Sidebar conversations ───────────────────────────────────────────────────
  conversations: ConversationRow[]
  setConversations: (rows: ConversationRow[]) => void
  prependConversation: (row: ConversationRow) => void
  updateConversation: (sessionId: string, patch: Partial<ConversationRow['session']>) => void

  // ── Modules ─────────────────────────────────────────────────────────────────
  modules: Module[]
  setModules: (modules: Module[]) => void

  // ── Streaming state ─────────────────────────────────────────────────────────
  streaming: boolean
  setStreaming: (v: boolean) => void

  // ── UI module override ───────────────────────────────────────────────────────
  setActiveModule: (module: string) => void

  // ── Admin ────────────────────────────────────────────────────────────────────
  showAdminView: boolean
  setShowAdminView: (v: boolean) => void
}

export const useStore = create<AppState>((set) => ({
  // ── Auth ────────────────────────────────────────────────────────────────────
  userId: null,
  userName: null,
  isAdmin: false,
  setUser: (id, name, admin) => set({ userId: id, userName: name, isAdmin: admin }),

  // ── Active session ──────────────────────────────────────────────────────────
  activeCustomerId: null,
  activeSessionId: null,
  activeModule: null,
  setActiveSession: (customerId, sessionId, module) =>
    set({ activeCustomerId: customerId, activeSessionId: sessionId, activeModule: module ?? null }),
  clearActiveSession: () =>
    set({ activeCustomerId: null, activeSessionId: null, activeModule: null }),

  // ── Messages ────────────────────────────────────────────────────────────────
  messages: [],
  appendMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  appendChunk: (id, chunk) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + chunk } : m,
      ),
    })),
  finalizeMessage: (id) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, streaming: false } : m,
      ),
    })),
  clearMessages: () => set({ messages: [], baselineNodeIds: [] }),

  // ── Consulting workspace ────────────────────────────────────────────────────
  workspace: null,
  setWorkspace: (workspace) => set({ workspace }),
  clearWorkspace: () => set({ workspace: null }),

  // ── Architecture canvas ─────────────────────────────────────────────────────
  canvasVisible: false,
  canvasNodes: [],
  canvasEdges: [],
  baselineNodeIds: [],
  setCanvas: (nodes, edges) => set((s) => {
    const isFirst = s.baselineNodeIds.length === 0
    return {
      canvasNodes: nodes,
      canvasEdges: edges,
      canvasVisible: true,
      baselineNodeIds: isFirst ? nodes.map((n) => n.id) : s.baselineNodeIds,
    }
  }),
  showCanvas: () => set({ canvasVisible: true }),
  hideCanvas: () => set({ canvasVisible: false, baselineNodeIds: [] }),

  // ── Sidebar conversations ───────────────────────────────────────────────────
  conversations: [],
  setConversations: (rows) => set({ conversations: rows }),
  prependConversation: (row) =>
    set((s) => ({ conversations: [row, ...s.conversations] })),
  updateConversation: (sessionId, patch) =>
    set((s) => ({
      conversations: s.conversations.map((c) =>
        c.session.session_id === sessionId
          ? { ...c, session: { ...c.session, ...patch } }
          : c,
      ),
    })),

  // ── Modules ─────────────────────────────────────────────────────────────────
  modules: [],
  setModules: (modules) => set({ modules }),

  // ── Streaming state ─────────────────────────────────────────────────────────
  streaming: false,
  setStreaming: (v) => set({ streaming: v }),

  // ── UI module override ───────────────────────────────────────────────────────
  setActiveModule: (module) => set({ activeModule: module }),

  // ── Admin ────────────────────────────────────────────────────────────────────
  showAdminView: false,
  setShowAdminView: (v) => set({ showAdminView: v }),
}))
