import { request } from 'undici';
import type { FastifyInstance } from 'fastify';

import { createApp } from './server.js';
import { signRequest } from './signing.js';

const TASK_TEMPLATE = Symbol('villow.taskTemplate');
const PREVIEW_TEMPLATE = Symbol('villow.previewTemplate');

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

export class Agent {
  publisherId: string;
  agentId: string;
  keyId: string;
  secret: string;
  platformBaseUrl: string;
  platformRequest?: PlatformRequest;
  taskTemplates = new Map<string, { slug: string }>();
  prepareHandlers = new Map<string, Handler>();
  runHandlers = new Map<string, Handler>();
  previewHandlers = new Map<string, Handler>();
  idempotencyStore = new Map<string, { bodyHash: string; statusCode: number; payload: Record<string, unknown> }>();
  answersByTask = new Map<string, Record<string, unknown>>();
  delegatedByTask = new Map<string, Record<string, boolean>>();
  taskEvents = new Map<string, Array<{ kind: string; payload: Record<string, unknown> }>>();
  taskArtifacts = new Map<string, Array<Record<string, unknown>>>();
  taskStates = new Map<string, string>();
  // N1.5: last opaque continuation blob a handler returned, keyed by task (surfaced from /result).
  taskAgentState = new Map<string, Record<string, unknown>>();

  constructor(options: AgentOptions = {}) {
    this.publisherId = options.publisherId ?? 'publisher_local';
    this.agentId = options.agentId ?? 'agent_local';
    this.keyId = options.keyId ?? 'key_local';
    this.secret = options.secret ?? 'local-secret';
    this.platformBaseUrl = (options.platformBaseUrl ?? 'http://127.0.0.1:8000').replace(/\/$/, '');
    this.platformRequest = options.platformRequest;
    this.registerDecoratedHandlers();
  }

  fastifyApp(): FastifyInstance {
    return createApp(this);
  }

  async signedPlatformPost(pathOrUrl: string, payload: Record<string, unknown>, options: { idempotencyKey: string }): Promise<Record<string, unknown>> {
    const url = this.absoluteUrl(pathOrUrl);
    const body = stableJsonBuffer(payload);
    const headers = signRequest({
      method: 'POST',
      path: new URL(url).pathname,
      body,
      keyId: this.keyId,
      secret: this.secret,
      publisherId: this.publisherId,
      agentId: this.agentId,
      idempotencyKey: options.idempotencyKey,
    });
    headers['content-type'] = 'application/json';

    const response = this.platformRequest
      ? await this.platformRequest({ url, method: 'POST', headers, body })
      : await defaultPlatformRequest({ url, method: 'POST', headers, body });

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw new Error(`platform_request_failed:${response.statusCode}`);
    }
    return (response.body ?? {}) as Record<string, unknown>;
  }

  private absoluteUrl(pathOrUrl: string): string {
    if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) return pathOrUrl;
    return `${this.platformBaseUrl}/${pathOrUrl.replace(/^\//, '')}`;
  }

  private registerDecoratedHandlers(): void {
    const prototype = Object.getPrototypeOf(this) as Record<string, DecoratedHandler>;
    for (const name of Object.getOwnPropertyNames(prototype)) {
      if (name === 'constructor') continue;
      const original = prototype[name];
      if (typeof original !== 'function') continue;
      const taskSlug = original[TASK_TEMPLATE];
      if (taskSlug) {
        this.taskTemplates.set(taskSlug, { slug: taskSlug });
        const bound = original.bind(this);
        if (name === 'prepare' || name.startsWith('prepare')) {
          this.prepareHandlers.set(taskSlug, bound);
        } else if (['run', 'execute'].includes(name) || name.startsWith('run') || name.startsWith('execute')) {
          this.runHandlers.set(taskSlug, bound);
        }
      }
      const previewSlug = original[PREVIEW_TEMPLATE];
      if (previewSlug) {
        this.taskTemplates.set(previewSlug, { slug: previewSlug });
        this.previewHandlers.set(previewSlug, original.bind(this));
      }
    }
  }
}

export function taskTemplate(slug: string) {
  return function taskTemplateDecorator(
    valueOrTarget: unknown,
    _propertyKeyOrContext?: string | symbol | ClassMethodDecoratorContext,
    descriptor?: PropertyDescriptor,
  ): void | DecoratedHandler {
    if (typeof valueOrTarget === 'function' && descriptor === undefined) {
      (valueOrTarget as DecoratedHandler)[TASK_TEMPLATE] = slug;
      return valueOrTarget as DecoratedHandler;
    }
    if (descriptor?.value) {
      (descriptor.value as DecoratedHandler)[TASK_TEMPLATE] = slug;
    }
  };
}

export function preview(slug: string) {
  return function previewDecorator(
    valueOrTarget: unknown,
    _propertyKeyOrContext?: string | symbol | ClassMethodDecoratorContext,
    descriptor?: PropertyDescriptor,
  ): void | DecoratedHandler {
    if (typeof valueOrTarget === 'function' && descriptor === undefined) {
      (valueOrTarget as DecoratedHandler)[PREVIEW_TEMPLATE] = slug;
      return valueOrTarget as DecoratedHandler;
    }
    if (descriptor?.value) {
      (descriptor.value as DecoratedHandler)[PREVIEW_TEMPLATE] = slug;
    }
  };
}

async function defaultPlatformRequest(input: PlatformRequestInput): Promise<PlatformResponse> {
  const response = await request(input.url, { method: input.method, headers: input.headers, body: input.body });
  const text = await response.body.text();
  return { statusCode: response.statusCode, body: text ? (JSON.parse(text) as unknown) : {} };
}

export function stableJsonBuffer(payload: Record<string, unknown>): Buffer {
  return Buffer.from(JSON.stringify(sortJson(payload)));
}

function sortJson(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortJson);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => [key, sortJson(item)]));
  }
  return value;
}
