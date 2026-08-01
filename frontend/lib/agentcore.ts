'use client';

/**
 * Direct AgentCore Runtime invocation from the browser.
 *
 * Auth flow:
 *   Cognito id_token → Identity Pool → temporary AWS credentials → SigV4-signed POST
 *
 * API reference:
 *   POST https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encodedArn}/invocations
 *   Header: X-Amzn-Bedrock-AgentCore-Runtime-Session-Id  (≥ 33 chars)
 *   Body:   JSON payload
 *   Response: text/event-stream (SSE)
 */

import { fromCognitoIdentityPool } from '@aws-sdk/credential-provider-cognito-identity';
import { SignatureV4 } from '@smithy/signature-v4';
import { Sha256 } from '@aws-crypto/sha256-browser';

const REGION = process.env.NEXT_PUBLIC_AWS_REGION ?? 'us-east-1';
const IDENTITY_POOL_ID = process.env.NEXT_PUBLIC_IDENTITY_POOL_ID ?? '';
const USER_POOL_ID = process.env.NEXT_PUBLIC_USER_POOL_ID ?? '';

export const AGENTCORE_RUNTIME_ARN = process.env.NEXT_PUBLIC_AGENTCORE_RUNTIME_ARN ?? '';

const AGENTCORE_HOST = `bedrock-agentcore.${REGION}.amazonaws.com`;
const COGNITO_TOKEN_HEADER =
  'x-amzn-bedrock-agentcore-runtime-custom-cognito-id-token';
const RUNTIME_USER_HEADER =
  'x-amzn-bedrock-agentcore-runtime-user-id';

/** Returns true when all env vars needed for direct AgentCore calls are present. */
export function isDirectModeEnabled(): boolean {
  return !!(AGENTCORE_RUNTIME_ARN && IDENTITY_POOL_ID && USER_POOL_ID);
}

/** Ensures runtimeSessionId meets the ≥ 33 character requirement. */
export function buildRuntimeSessionId(customerId: string, sessionId: string): string {
  const raw = `${customerId}-${sessionId}`;
  return raw.length >= 33 ? raw : raw.padEnd(33, '0');
}

/** Exchange a Cognito ID token for temporary AWS credentials via the Identity Pool. */
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
    const encoded = idToken.split('.')[1];
    const normalized = encoded.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(
      normalized.length + ((4 - normalized.length % 4) % 4),
      '=',
    );
    const claims = JSON.parse(atob(padded)) as { sub?: unknown };
    if (typeof claims.sub === 'string' && claims.sub.trim()) {
      return claims.sub.trim();
    }
  } catch {
    // The caller receives one fail-closed identity error below.
  }
  throw new Error('Cognito ID token is missing a valid subject');
}

/**
 * Invoke AgentCore Runtime and return the raw SSE ReadableStream.
 * The caller is responsible for parsing and consuming the stream.
 */
export async function invokeAgentCore(
  payload: Record<string, unknown>,
  runtimeSessionId: string,
  idToken: string,
  signal?: AbortSignal,
): Promise<ReadableStream<Uint8Array>> {
  const runtimeUserId = tokenSubject(idToken);
  const credentials = await getCredentials(idToken);
  const path = `/runtimes/${encodeURIComponent(AGENTCORE_RUNTIME_ARN)}/invocations`;
  const body = JSON.stringify(payload);

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
      [RUNTIME_USER_HEADER]: runtimeUserId,
      [COGNITO_TOKEN_HEADER]: idToken,
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
 * Async-iterate a Server-Sent Events stream, yielding { event?, data } pairs.
 * Handles the AgentCore double-encoding: the outer SSE data field contains a
 * JSON-encoded string that is itself an SSE block. Both formats are yielded.
 */
export async function* readSSE(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<{ event?: string; data: string }> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  let pendingEvent: string | undefined;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      const lines = buf.split('\n');
      buf = lines.pop() ?? '';

      for (const rawLine of lines) {
        const line = rawLine.trimEnd();
        if (line.startsWith('event: ')) {
          pendingEvent = line.slice(7);
        } else if (line.startsWith('data: ')) {
          yield { event: pendingEvent, data: line.slice(6) };
          pendingEvent = undefined;
        } else if (line === '') {
          pendingEvent = undefined;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
