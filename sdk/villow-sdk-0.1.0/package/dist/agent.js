import { request } from 'undici';
import { createApp } from './server.js';
import { signRequest } from './signing.js';
const TASK_TEMPLATE = Symbol('villow.taskTemplate');
const PREVIEW_TEMPLATE = Symbol('villow.previewTemplate');
export class Agent {
    publisherId;
    agentId;
    keyId;
    secret;
    platformBaseUrl;
    platformRequest;
    taskTemplates = new Map();
    prepareHandlers = new Map();
    runHandlers = new Map();
    previewHandlers = new Map();
    idempotencyStore = new Map();
    answersByTask = new Map();
    delegatedByTask = new Map();
    taskEvents = new Map();
    taskArtifacts = new Map();
    taskStates = new Map();
    // N1.5: last opaque continuation blob a handler returned, keyed by task (surfaced from /result).
    taskAgentState = new Map();
    constructor(options = {}) {
        this.publisherId = options.publisherId ?? 'publisher_local';
        this.agentId = options.agentId ?? 'agent_local';
        this.keyId = options.keyId ?? 'key_local';
        this.secret = options.secret ?? 'local-secret';
        this.platformBaseUrl = (options.platformBaseUrl ?? 'http://127.0.0.1:8000').replace(/\/$/, '');
        this.platformRequest = options.platformRequest;
        this.registerDecoratedHandlers();
    }
    fastifyApp() {
        return createApp(this);
    }
    async signedPlatformPost(pathOrUrl, payload, options) {
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
        return (response.body ?? {});
    }
    absoluteUrl(pathOrUrl) {
        if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://'))
            return pathOrUrl;
        return `${this.platformBaseUrl}/${pathOrUrl.replace(/^\//, '')}`;
    }
    registerDecoratedHandlers() {
        const prototype = Object.getPrototypeOf(this);
        for (const name of Object.getOwnPropertyNames(prototype)) {
            if (name === 'constructor')
                continue;
            const original = prototype[name];
            if (typeof original !== 'function')
                continue;
            const taskSlug = original[TASK_TEMPLATE];
            if (taskSlug) {
                this.taskTemplates.set(taskSlug, { slug: taskSlug });
                const bound = original.bind(this);
                if (name === 'prepare' || name.startsWith('prepare')) {
                    this.prepareHandlers.set(taskSlug, bound);
                }
                else if (['run', 'execute'].includes(name) || name.startsWith('run') || name.startsWith('execute')) {
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
export function taskTemplate(slug) {
    return function taskTemplateDecorator(valueOrTarget, _propertyKeyOrContext, descriptor) {
        if (typeof valueOrTarget === 'function' && descriptor === undefined) {
            valueOrTarget[TASK_TEMPLATE] = slug;
            return valueOrTarget;
        }
        if (descriptor?.value) {
            descriptor.value[TASK_TEMPLATE] = slug;
        }
    };
}
export function preview(slug) {
    return function previewDecorator(valueOrTarget, _propertyKeyOrContext, descriptor) {
        if (typeof valueOrTarget === 'function' && descriptor === undefined) {
            valueOrTarget[PREVIEW_TEMPLATE] = slug;
            return valueOrTarget;
        }
        if (descriptor?.value) {
            descriptor.value[PREVIEW_TEMPLATE] = slug;
        }
    };
}
async function defaultPlatformRequest(input) {
    const response = await request(input.url, { method: input.method, headers: input.headers, body: input.body });
    const text = await response.body.text();
    return { statusCode: response.statusCode, body: text ? JSON.parse(text) : {} };
}
export function stableJsonBuffer(payload) {
    return Buffer.from(JSON.stringify(sortJson(payload)));
}
function sortJson(value) {
    if (Array.isArray(value))
        return value.map(sortJson);
    if (value && typeof value === 'object') {
        return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => [key, sortJson(item)]));
    }
    return value;
}
