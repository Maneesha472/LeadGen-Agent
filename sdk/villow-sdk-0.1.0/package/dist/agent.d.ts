import type { FastifyInstance } from 'fastify';
declare const TASK_TEMPLATE: unique symbol;
declare const PREVIEW_TEMPLATE: unique symbol;
type Handler = (...args: unknown[]) => unknown;
type DecoratedHandler = Handler & {
    [TASK_TEMPLATE]?: string;
    [PREVIEW_TEMPLATE]?: string;
};
export interface PlatformRequestInput {
    url: string;
    method: 'POST';
    headers: Record<string, string>;
    body: Buffer;
}
export interface PlatformResponse {
    statusCode: number;
    body: unknown;
}
export type PlatformRequest = (input: PlatformRequestInput) => Promise<PlatformResponse>;
export interface AgentOptions {
    publisherId?: string;
    agentId?: string;
    keyId?: string;
    secret?: string;
    platformBaseUrl?: string;
    platformRequest?: PlatformRequest;
}
export declare class Agent {
    publisherId: string;
    agentId: string;
    keyId: string;
    secret: string;
    platformBaseUrl: string;
    platformRequest?: PlatformRequest;
    taskTemplates: Map<string, {
        slug: string;
    }>;
    prepareHandlers: Map<string, Handler>;
    runHandlers: Map<string, Handler>;
    previewHandlers: Map<string, Handler>;
    idempotencyStore: Map<string, {
        bodyHash: string;
        statusCode: number;
        payload: Record<string, unknown>;
    }>;
    answersByTask: Map<string, Record<string, unknown>>;
    delegatedByTask: Map<string, Record<string, boolean>>;
    taskEvents: Map<string, {
        kind: string;
        payload: Record<string, unknown>;
    }[]>;
    taskArtifacts: Map<string, Record<string, unknown>[]>;
    taskStates: Map<string, string>;
    taskAgentState: Map<string, Record<string, unknown>>;
    constructor(options?: AgentOptions);
    fastifyApp(): FastifyInstance;
    signedPlatformPost(pathOrUrl: string, payload: Record<string, unknown>, options: {
        idempotencyKey: string;
    }): Promise<Record<string, unknown>>;
    private absoluteUrl;
    private registerDecoratedHandlers;
}
export declare function taskTemplate(slug: string): (valueOrTarget: unknown, _propertyKeyOrContext?: string | symbol | ClassMethodDecoratorContext, descriptor?: PropertyDescriptor) => void | DecoratedHandler;
export declare function preview(slug: string): (valueOrTarget: unknown, _propertyKeyOrContext?: string | symbol | ClassMethodDecoratorContext, descriptor?: PropertyDescriptor) => void | DecoratedHandler;
export declare function stableJsonBuffer(payload: Record<string, unknown>): Buffer;
export {};
