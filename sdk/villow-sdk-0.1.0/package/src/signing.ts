import { createHash, createHmac, timingSafeEqual } from 'node:crypto';

export const KEY_ID_HEADER = 'x-worklane-key-id';
export const SIGNATURE_HEADER = 'x-worklane-signature';
export const TIMESTAMP_HEADER = 'x-worklane-timestamp';
export const NONCE_HEADER = 'x-worklane-nonce';
export const PUBLISHER_ID_HEADER = 'x-worklane-publisher-id';
export const AGENT_ID_HEADER = 'x-worklane-agent-id';
export const IDEMPOTENCY_KEY_HEADER = 'x-worklane-idempotency-key';

export interface SigningPrincipal {
  publisherId: string;
  agentId: string;
  keyId: string;
  nonce: string;
  timestamp: number;
  idempotencyKey: string;
}

export interface SignRequestInput {
  method: string;
  path: string;
  body: Buffer | string | Uint8Array;
  keyId: string;
  secret: string;
  publisherId: string;
  agentId: string;
  idempotencyKey: string;
  timestamp?: number;
  nonce?: string;
}

export interface VerifyRequestInput {
  method: string;
  path: string;
  body: Buffer | string | Uint8Array;
  headers: Record<string, string | string[] | undefined>;
  secret: string;
  now?: number;
  maxSkewSeconds?: number;
}

export function requestBodyHash(body: Buffer | string | Uint8Array): string {
  return createHash('sha256').update(toBuffer(body)).digest('hex');
}

export function canonicalRequest(input: Omit<SignRequestInput, 'secret'> & { timestamp: number; nonce: string }): string {
  return [
    input.method.toUpperCase(),
    input.path,
    String(input.timestamp),
    input.nonce,
    input.keyId,
    input.publisherId,
    input.agentId,
    input.idempotencyKey,
    requestBodyHash(input.body),
  ].join('\n');
}

export function signRequest(input: SignRequestInput): Record<string, string> {
  const timestamp = input.timestamp ?? Math.floor(Date.now() / 1000);
  const nonce = input.nonce ?? createHash('sha256').update(`${timestamp}:${Math.random()}`).digest('hex').slice(0, 32);
  const canonical = canonicalRequest({ ...input, timestamp, nonce });
  const digest = createHmac('sha256', input.secret).update(canonical).digest('hex');
  return {
    [KEY_ID_HEADER]: input.keyId,
    [SIGNATURE_HEADER]: `v1:${digest}`,
    [TIMESTAMP_HEADER]: String(timestamp),
    [NONCE_HEADER]: nonce,
    [PUBLISHER_ID_HEADER]: input.publisherId,
    [AGENT_ID_HEADER]: input.agentId,
    [IDEMPOTENCY_KEY_HEADER]: input.idempotencyKey,
  };
}

export function verifyRequestSignature(input: VerifyRequestInput): SigningPrincipal {
  const headers = normalizeHeaders(input.headers);
  const keyId = requireHeader(headers, KEY_ID_HEADER);
  const signature = requireHeader(headers, SIGNATURE_HEADER);
  const timestamp = Number.parseInt(requireHeader(headers, TIMESTAMP_HEADER), 10);
  const nonce = requireHeader(headers, NONCE_HEADER);
  const publisherId = requireHeader(headers, PUBLISHER_ID_HEADER);
  const agentId = headers[AGENT_ID_HEADER] ?? '';
  const idempotencyKey = headers[IDEMPOTENCY_KEY_HEADER] ?? '';
  if (!Number.isInteger(timestamp)) {
    throw new Error('missing_or_invalid_signature_headers');
  }

  const now = input.now ?? Math.floor(Date.now() / 1000);
  const maxSkewSeconds = input.maxSkewSeconds ?? 300;
  if (Math.abs(now - timestamp) > maxSkewSeconds) {
    throw new Error('stale_signature');
  }

  const canonical = canonicalRequest({
    method: input.method,
    path: input.path,
    body: input.body,
    keyId,
    publisherId,
    agentId,
    idempotencyKey,
    timestamp,
    nonce,
  });
  const expected = `v1:${createHmac('sha256', input.secret).update(canonical).digest('hex')}`;
  if (!safeEqual(signature, expected)) {
    throw new Error('invalid_signature');
  }
  return { publisherId, agentId, keyId, nonce, timestamp, idempotencyKey };
}

function normalizeHeaders(headers: Record<string, string | string[] | undefined>): Record<string, string> {
  const normalized: Record<string, string> = {};
  for (const [key, value] of Object.entries(headers)) {
    if (typeof value === 'string') {
      normalized[key.toLowerCase()] = value;
    } else if (Array.isArray(value) && value.length > 0) {
      normalized[key.toLowerCase()] = value[0];
    }
  }
  return normalized;
}

function requireHeader(headers: Record<string, string>, name: string): string {
  const value = headers[name];
  if (!value) {
    throw new Error('missing_or_invalid_signature_headers');
  }
  return value;
}

function safeEqual(actual: string, expected: string): boolean {
  const actualBuffer = Buffer.from(actual);
  const expectedBuffer = Buffer.from(expected);
  return actualBuffer.length === expectedBuffer.length && timingSafeEqual(actualBuffer, expectedBuffer);
}

function toBuffer(body: Buffer | string | Uint8Array): Buffer {
  return Buffer.isBuffer(body) ? body : Buffer.from(body);
}
