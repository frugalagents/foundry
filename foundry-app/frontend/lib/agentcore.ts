'use client';

/**
 * Direct AgentCore Runtime invocation from the browser.
 *
 * Auth flow:
 *   Cognito id_token → Identity Pool → temporary AWS credentials → SigV4-signed POST
 *
 * API:
 *   POST https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encodedArn}/invocations
 *   Header: x-amzn-bedrock-agentcore-runtime-session-id  (≥ 33 chars)
 *   Response: text/event-stream (SSE, double-encoded)
 */

import { fromCognitoIdentityPool } from '@aws-sdk/credential-provider-cognito-identity';
import { SignatureV4 } from '@smithy/signature-v4';
import { Sha256 } from '@aws-crypto/sha256-browser';

const REGION           = process.env.NEXT_PUBLIC_AWS_REGION          ?? 'us-east-1';
const IDENTITY_POOL_ID = process.env.NEXT_PUBLIC_IDENTITY_POOL_ID    ?? '';
const USER_POOL_ID     = process.env.NEXT_PUBLIC_USER_POOL_ID        ?? '';
export const RUNTIME_ARN = process.env.NEXT_PUBLIC_AGENTCORE_RUNTIME_ARN ?? '';

const AGENTCORE_HOST = `bedrock-agentcore.${REGION}.amazonaws.com`;

export function isDirectModeEnabled(): boolean {
  return !!(RUNTIME_ARN && IDENTITY_POOL_ID && USER_POOL_ID);
}

/** Ensures runtimeSessionId meets the ≥ 33 character requirement. */
export function buildRuntimeSessionId(customerId: string, sessionId: string): string {
  const raw = `${customerId}-${sessionId}`;
  return raw.length >= 33 ? raw : raw.padEnd(33, '0');
}

async function getCredentials(idToken: string) {
  return fromCognitoIdentityPool({
    clientConfig: { region: REGION },
    identityPoolId: IDENTITY_POOL_ID,
    logins: {
      [`cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}`]: idToken,
    },
  })();
}

function tokenSubject(idToken: string): string {
  try {
    const encoded    = idToken.split('.')[1];
    const normalized = encoded.replace(/-/g, '+').replace(/_/g, '/');
    const padded     = normalized.padEnd(normalized.length + ((4 - normalized.length % 4) % 4), '=');
    const claims     = JSON.parse(atob(padded)) as { sub?: unknown };
    if (typeof claims.sub === 'string' && claims.sub.trim()) return claims.sub.trim();
  } catch { /* fall through */ }
  throw new Error('Cognito ID token is missing a valid subject');
}

export async function invokeAgentCore(
  payload: Record<string, unknown>,
  runtimeSessionId: string,
  idToken: string,
  signal?: AbortSignal,
): Promise<ReadableStream<Uint8Array>> {
  const runtimeUserId = tokenSubject(idToken);
  const credentials   = await getCredentials(idToken);
  const path          = `/runtimes/${encodeURIComponent(RUNTIME_ARN)}/invocations`;
  const body          = JSON.stringify(payload);

  const signer = new SignatureV4({
    service: 'bedrock-agentcore',
    region: REGION,
    credentials,
    sha256: Sha256,
  });

  const signed = await signer.sign({
    method: 'POST',
    protocol: 'https:',
    hostname: AGENTCORE_HOST,
    path,
    headers: {
      host: AGENTCORE_HOST,
      'content-type': 'application/json',
      accept: 'text/event-stream',
      'x-amzn-bedrock-agentcore-runtime-session-id': runtimeSessionId,
      'x-amzn-bedrock-agentcore-runtime-user-id': runtimeUserId,
      'x-amzn-bedrock-agentcore-runtime-custom-cognito-id-token': idToken,
    },
    body,
  });

  const response = await fetch(`https://${AGENTCORE_HOST}${path}`, {
    method: 'POST',
    headers: signed.headers as Record<string, string>,
    body,
    signal,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(`AgentCore ${response.status}: ${text}`);
  }

  return response.body!;
}

/**
 * Async-iterate a Server-Sent Events stream, yielding parsed event objects.
 * Handles AgentCore double-encoding: the outer SSE data field may be a
 * JSON-encoded string that is itself an SSE block.
 */
export async function* readSSEEvents(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<Record<string, unknown>> {
  const reader  = stream.getReader();
  const decoder = new TextDecoder();
  let buf = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      const lines = buf.split('\n');
      buf = lines.pop() ?? '';

      for (const rawLine of lines) {
        const line = rawLine.trimEnd();
        if (!line.startsWith('data: ')) continue;

        const raw = line.slice(6);
        if (raw === '[DONE]') continue;

        let parsed: unknown;
        try { parsed = JSON.parse(raw); } catch { continue; }

        // Double-encoding: outer data is a JSON string containing inner SSE
        if (typeof parsed === 'string') {
          for (const inner of parsed.split('\n')) {
            if (!inner.startsWith('data: ')) continue;
            const innerRaw = inner.slice(6);
            if (innerRaw === '[DONE]') continue;
            try { yield JSON.parse(innerRaw) as Record<string, unknown>; } catch { /* skip */ }
          }
        } else if (typeof parsed === 'object' && parsed !== null) {
          yield parsed as Record<string, unknown>;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
