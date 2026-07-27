'use client';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  ChatMessage,
  UserTokenPayload,
  ConfirmationRequestEvent,
  PanelType,
  DrilldownData,
  WhatIfData,
} from '@/lib/types';

interface AppState {
  // ── Auth ────────────────────────────────────────────────
  user: UserTokenPayload | null;
  setUser: (user: UserTokenPayload | null) => void;
  /** Admin-only: when true, admin sees the app as a regular user would */
  viewingAsUser: boolean;
  setViewingAsUser: (v: boolean) => void;

  // ── Session streaming state ──────────────────────────────
  currentStep: number;
  panelData: Record<number, unknown>;
  chatMessages: ChatMessage[];
  isStreaming: boolean;
  awaitingConfirmation: boolean;
  confirmationRequest: ConfirmationRequestEvent | null;

  // ── Drilldown ────────────────────────────────────────────
  drilldownData: DrilldownData | null;
  drilldownLoading: boolean;
  drilldownComponentId: string | null;
  setDrilldownData: (data: DrilldownData | null) => void;
  setDrilldownLoading: (v: boolean) => void;
  setDrilldownComponentId: (id: string | null) => void;

  // ── What-If ──────────────────────────────────────────────
  whatIfData: WhatIfData | null;
  whatIfLoading: boolean;
  setWhatIfData: (data: WhatIfData | null) => void;
  setWhatIfLoading: (v: boolean) => void;

  // ── Actions ──────────────────────────────────────────────
  setCurrentStep: (step: number) => void;
  setPanelData: (step: number, data: unknown) => void;
  appendCardData: (
    step: number,
    panelType: PanelType,
    cardId: string,
    cardData: unknown
  ) => void;
  addChatMessage: (msg: ChatMessage) => void;
  appendChatDelta: (delta: string) => void;
  setStreaming: (v: boolean) => void;
  setAwaitingConfirmation: (
    v: boolean,
    req?: ConfirmationRequestEvent
  ) => void;
  resetSession: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
      viewingAsUser: false,
      setViewingAsUser: (v) => set({ viewingAsUser: v }),

      currentStep: 1,
      panelData: {},
      chatMessages: [],
      isStreaming: false,
      awaitingConfirmation: false,
      confirmationRequest: null,
      drilldownData: null,
      drilldownLoading: false,
      drilldownComponentId: null,
      whatIfData: null,
      whatIfLoading: false,

      setDrilldownData: (data) => set({ drilldownData: data }),
      setDrilldownLoading: (v) => set({ drilldownLoading: v }),
      setDrilldownComponentId: (id) => set({ drilldownComponentId: id }),
      setWhatIfData: (data) => set({ whatIfData: data }),
      setWhatIfLoading: (v) => set({ whatIfLoading: v }),

      setCurrentStep: (step) => set({ currentStep: step }),

      setPanelData: (step, data) =>
        set((s) => ({ panelData: { ...s.panelData, [step]: data } })),

      appendCardData: (step, _panelType, cardId, cardData) =>
        set((s) => {
          const existing =
            (s.panelData[step] as Record<string, unknown>) ?? {};
          const cards = (existing.cards as unknown[]) ?? [];
          return {
            panelData: {
              ...s.panelData,
              [step]: {
                ...existing,
                cards: [
                  ...cards,
                  { id: cardId, ...(cardData as object) },
                ],
              },
            },
          };
        }),

      addChatMessage: (msg) =>
        set((s) => ({ chatMessages: [...s.chatMessages, msg] })),

      appendChatDelta: (delta) =>
        set((s) => {
          const msgs = [...s.chatMessages];
          const last = msgs[msgs.length - 1];
          if (last?.role === 'assistant' && last.streaming) {
            msgs[msgs.length - 1] = {
              ...last,
              content: last.content + delta,
            };
          } else {
            msgs.push({
              id: Date.now().toString(),
              role: 'assistant',
              content: delta,
              timestamp: new Date().toISOString(),
              streaming: true,
            });
          }
          return { chatMessages: msgs };
        }),

      setStreaming: (v) => set({ isStreaming: v }),

      setAwaitingConfirmation: (v, req) =>
        set({ awaitingConfirmation: v, confirmationRequest: req ?? null }),

      resetSession: () =>
        set({
          currentStep: 1,
          panelData: {},
          chatMessages: [],
          isStreaming: false,
          awaitingConfirmation: false,
          confirmationRequest: null,
        }),
    }),
    {
      name: 'platform-advisor-store',
      partialize: (state) => ({ user: state.user }),
    }
  )
);
