'use client';
import { useCallback, useRef } from 'react';
import { useAppStore } from '@/store';
import type { AgentEvent, ConfirmationRequestEvent, DrilldownData, WhatIfData } from '@/lib/types';
import { getToken } from '@/lib/auth';
import {
  isDirectModeEnabled,
  buildRuntimeSessionId,
  invokeAgentCore,
  readSSE,
} from '@/lib/agentcore';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080/api/v1';

/**
 * Single hook for all agent interactions.
 *
 * Every user action — submitting intake answers, confirming a pattern,
 * changing an answer mid-pipeline, or asking a free-text question — calls
 * sendMessage(). The Strands Agent on the other end decides which pipeline
 * tools to invoke based on the message content and its conversation history.
 *
 * extraPayload is forwarded alongside user_message so the backend can prime
 * PipelineContext with structured data (e.g. answers JSON on first submit).
 */
export function useAgentStream(customerId: string, sessionId: string) {
  const abortRef = useRef<AbortController | null>(null);
  const esRef    = useRef<EventSource | null>(null);
  const store    = useAppStore();

  const runtimeSessionId = buildRuntimeSessionId(customerId, sessionId);

  // ── Core send (AgentCore direct path) ────────────────────────────────────

  const _sendToAgentCore = useCallback(
    async (
      payload: Record<string, unknown>,
      signal: AbortSignal,
    ) => {
      const token = getToken() ?? '';
      const stream = await invokeAgentCore(payload, runtimeSessionId, token, signal);

      for await (const { data } of readSSE(stream)) {
        if (signal.aborted) break;

        let parsed: unknown;
        try { parsed = JSON.parse(data); } catch { continue; }

        // AgentCore double-encoding: outer data is a JSON string containing SSE
        if (typeof parsed === 'string') {
          for (const line of parsed.split('\n')) {
            if (line.startsWith('data: ')) {
              try { dispatchAgentEvent(JSON.parse(line.slice(6)), store); } catch { /* skip */ }
            }
          }
        } else if (typeof parsed === 'object' && parsed !== null) {
          dispatchAgentEvent(parsed as AgentEvent, store);
        }
      }
    },
    [runtimeSessionId, store],
  );

  // ── Core send (local dev EventSource fallback) ────────────────────────────

  const _sendToLocalDev = useCallback(
    (userMessage: string, extra: Record<string, unknown>) => {
      esRef.current?.close();

      const token = getToken() ?? '';
      const params = new URLSearchParams({ token, user_message: userMessage });
      // Flatten extra payload as JSON-encoded query params for local dev
      for (const [k, v] of Object.entries(extra)) {
        params.set(k, typeof v === 'string' ? v : JSON.stringify(v));
      }

      const es = new EventSource(
        `${API_BASE}/sessions/${customerId}/${sessionId}/run?${params}`,
      );
      esRef.current = es;

      const eventTypes = [
        'panel_update', 'panel_complete', 'card_add', 'card_update',
        'chat_message', 'chat_stream', 'step_transition',
        'confirmation_request', 'error', 'complete',
      ];
      eventTypes.forEach((t) =>
        es.addEventListener(t, (e: MessageEvent) => {
          try { dispatchAgentEvent(JSON.parse(e.data) as AgentEvent, store); }
          catch (err) { console.error('SSE parse error', err); }
        }),
      );
      es.addEventListener('complete', () => {
        es.close();
        esRef.current = null;
        store.setStreaming(false);
      });
      es.onerror = () => {
        es.close();
        esRef.current = null;
        store.setStreaming(false);
      };
    },
    [customerId, sessionId, store],
  );

  // ── Public API ────────────────────────────────────────────────────────────

  /**
   * Send any message to the agent.
   *
   * Works for all interaction types:
   *   - Intake submission:  sendMessage("Analyze my requirements", { answers, industry, pain_points })
   *   - Pattern confirm:    sendMessage("Yes, federated looks right, continue")
   *   - Pattern override:   sendMessage("Use centralized instead")
   *   - Mid-pipeline change: sendMessage("Actually we have 3 LOBs not 10+")
   *   - Free-text question: sendMessage("Why was Federated recommended?")
   */
  const sendMessage = useCallback(
    async (
      content: string,
      extraPayload: Record<string, unknown> = {},
    ) => {
      // Abort any in-flight stream
      abortRef.current?.abort();
      esRef.current?.close();
      esRef.current = null;

      // Add user message to chat immediately
      store.addChatMessage({
        id:        `user-${Date.now()}`,
        role:      'user',
        content,
        timestamp: new Date().toISOString(),
      });
      store.setStreaming(true);

      const payload: Record<string, unknown> = {
        user_message: content,
        session_id:   sessionId,
        customer_id:  customerId,
        ...extraPayload,
      };

      if (isDirectModeEnabled()) {
        const ctrl = new AbortController();
        abortRef.current = ctrl;

        _sendToAgentCore(payload, ctrl.signal)
          .catch((err) => {
            if ((err as Error).name === 'AbortError') return;
            console.error('AgentCore error', err);
            store.addChatMessage({
              id:        `err-${Date.now()}`,
              role:      'assistant',
              content:   `Error: ${(err as Error).message}`,
              timestamp: new Date().toISOString(),
            });
          })
          .finally(() => store.setStreaming(false));
      } else {
        _sendToLocalDev(content, extraPayload);
      }
    },
    [customerId, sessionId, store, _sendToAgentCore, _sendToLocalDev],
  );

  /**
   * Fetch a component drilldown — completely separate from the pipeline stream.
   * Does NOT set isStreaming or touch chatMessages.
   */
  const sendDrilldown = useCallback(
    async (componentId: string, componentName: string) => {
      store.setDrilldownLoading(true);
      store.setDrilldownComponentId(componentId);
      store.setDrilldownData(null);

      try {
        if (isDirectModeEnabled()) {
          const token = getToken() ?? '';
          const ctrl = new AbortController();
          const payload = {
            action:         'drilldown',
            component_id:   componentId,
            component_name: componentName,
            session_id:     sessionId,
            customer_id:    customerId,
          };
          const stream = await invokeAgentCore(payload, runtimeSessionId, token, ctrl.signal);

          for await (const { data } of readSSE(stream)) {
            let parsed: unknown;
            try { parsed = JSON.parse(data); } catch { continue; }

            // Unwrap double-encoding
            if (typeof parsed === 'string') {
              for (const line of parsed.split('\n')) {
                if (line.startsWith('data: ')) {
                  try {
                    const ev = JSON.parse(line.slice(6));
                    if (ev.type === 'drilldown_complete') {
                      store.setDrilldownData((ev.data ?? ev) as DrilldownData);
                    }
                  } catch { /* skip */ }
                }
              }
            } else if (typeof parsed === 'object' && parsed !== null) {
              const ev = parsed as { type?: string; data?: DrilldownData };
              if (ev.type === 'drilldown_complete') {
                store.setDrilldownData(ev.data ?? (ev as unknown as DrilldownData));
              }
            }
          }
        } else {
          // Local dev: plain REST endpoint
          const token = getToken() ?? '';
          const params = new URLSearchParams({
            token,
            component_id:   componentId,
            component_name: componentName,
          });
          const resp = await fetch(
            `${API_BASE}/sessions/${customerId}/${sessionId}/drilldown?${params}`,
          );
          if (resp.ok) {
            const data = (await resp.json()) as DrilldownData;
            store.setDrilldownData(data);
          }
        }
      } catch (err) {
        console.error('Drilldown error', err);
      } finally {
        store.setDrilldownLoading(false);
      }
    },
    [customerId, sessionId, runtimeSessionId, store],
  );

  /**
   * Re-score with hypothetical intake answer overrides (P4 What-If).
   * Returns immediately with the new radar data — does not stream.
   */
  const sendWhatIf = useCallback(
    async (overrides: Record<string, string>) => {
      store.setWhatIfLoading(true);
      store.setWhatIfData(null);

      try {
        if (isDirectModeEnabled()) {
          const token = getToken() ?? '';
          const ctrl = new AbortController();
          const payload = {
            action:      'whatif',
            overrides,
            session_id:  sessionId,
            customer_id: customerId,
          };
          const stream = await invokeAgentCore(payload, runtimeSessionId, token, ctrl.signal);

          for await (const { data } of readSSE(stream)) {
            let parsed: unknown;
            try { parsed = JSON.parse(data); } catch { continue; }

            if (typeof parsed === 'string') {
              for (const line of parsed.split('\n')) {
                if (line.startsWith('data: ')) {
                  try {
                    const ev = JSON.parse(line.slice(6));
                    if (ev.type === 'whatif_complete') {
                      store.setWhatIfData((ev.data ?? ev) as WhatIfData);
                    }
                  } catch { /* skip */ }
                }
              }
            } else if (typeof parsed === 'object' && parsed !== null) {
              const ev = parsed as { type?: string; data?: WhatIfData };
              if (ev.type === 'whatif_complete') {
                store.setWhatIfData(ev.data ?? (ev as unknown as WhatIfData));
              }
            }
          }
        } else {
          const token = getToken() ?? '';
          const params = new URLSearchParams({ token });
          const resp = await fetch(
            `${API_BASE}/sessions/${customerId}/${sessionId}/whatif?${params}`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ overrides }),
            },
          );
          if (resp.ok) {
            store.setWhatIfData((await resp.json()) as WhatIfData);
          }
        }
      } catch (err) {
        console.error('What-if error', err);
      } finally {
        store.setWhatIfLoading(false);
      }
    },
    [customerId, sessionId, runtimeSessionId, store],
  );

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    esRef.current?.close();
    esRef.current = null;
    store.setStreaming(false);
  }, [store]);

  return { sendMessage, sendDrilldown, sendWhatIf, stopStream };
}

// ── Event dispatch ────────────────────────────────────────────────────────────

function dispatchAgentEvent(
  event: AgentEvent,
  store: ReturnType<typeof useAppStore.getState>,
) {
  const id      = `${Date.now()}-${Math.random()}`;
  const payload = (event as { data?: AgentEvent }).data ?? event;
  const type    = (payload as { type?: string }).type ?? (event as { type?: string }).type;

  switch (type) {
    case 'panel_update':
    case 'panel_complete': {
      const e = payload as Extract<AgentEvent, { type: 'panel_complete' }>;
      store.setPanelData(e.step, e.data ?? (e as unknown as Record<string, unknown>));
      store.setCurrentStep(e.step);
      break;
    }
    case 'card_add': {
      const e = payload as Extract<AgentEvent, { type: 'card_add' }>;
      store.appendCardData(e.step, e.panel_type, e.card_id, e.card_data);
      break;
    }
    case 'chat_message': {
      const e = payload as Extract<AgentEvent, { type: 'chat_message' }>;
      store.addChatMessage({
        id,
        role:      e.role ?? 'assistant',
        content:   e.content,
        timestamp: (e as { timestamp?: string }).timestamp ?? new Date().toISOString(),
        step:      (e as { step?: number }).step,
      });
      break;
    }
    case 'chat_stream': {
      const e = payload as Extract<AgentEvent, { type: 'chat_stream' }>;
      store.appendChatDelta(e.delta);
      break;
    }
    case 'step_transition': {
      const e = payload as Extract<AgentEvent, { type: 'step_transition' }>;
      store.setCurrentStep(e.to_step);
      break;
    }
    case 'confirmation_request': {
      store.setAwaitingConfirmation(true, payload as ConfirmationRequestEvent);
      break;
    }
    case 'error': {
      const e = payload as Extract<AgentEvent, { type: 'error' }>;
      store.addChatMessage({
        id,
        role:      'assistant',
        content:   `Error: ${e.message}`,
        timestamp: new Date().toISOString(),
      });
      store.setStreaming(false);
      break;
    }
    case 'complete': {
      store.setStreaming(false);
      break;
    }
  }
}
