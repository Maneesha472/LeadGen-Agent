export declare const KEY_ID_HEADER = "x-worklane-key-id";
export declare const SIGNATURE_HEADER = "x-worklane-signature";
export declare const TIMESTAMP_HEADER = "x-worklane-timestamp";
export declare const NONCE_HEADER = "x-worklane-nonce";
export declare const PUBLISHER_ID_HEADER = "x-worklane-publisher-id";
export declare const AGENT_ID_HEADER = "x-worklane-agent-id";
export declare const IDEMPOTENCY_KEY_HEADER = "x-worklane-idempotency-key";
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
export declare function requestBodyHash(body: Buffer | string | Uint8Array): string;
export declare function canonicalRequest(input: Omit<SignRequestInput, 'secret'> & {
    timestamp: number;
    nonce: string;
}): string;
export declare function signRequest(input: SignRequestInput): Record<string, string>;
export declare function verifyRequestSignature(input: VerifyRequestInput): SigningPrincipal;
