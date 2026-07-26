import Fastify from 'fastify';
import { stableJsonBuffer } from './agent.js';
import { Context } from './context.js';
import { requestBodyHash, verifyRequestSignature } from './signing.js';
export function createApp(agent) {
    const app = Fastify({ logger: false });
    // Verify HMAC against the exact bytes the caller signed — never re-canonicalize JSON
    // (e.g. Python's 40.0 must not become 40 or signatures fail cross-SDK).
    app.addContentTypeParser('application/json', { parseAs: 'buffer' }, (_request, body, done) => {
        done(null, body);
    });
    app.post('/discover', (request, reply) => signedEndpoint(agent, request, reply, async () => ({
        publisher_id: agent.publisherId,
        agent_id: agent.agentId,
        task_templates: [...agent.taskTemplates.keys()].sort().map((slug) => ({
            slug,
            has_prepare: agent.prepareHandlers.has(slug),
            has_execute: agent.runHandlers.has(slug),
            has_preview: agent.previewHandlers.has(slug),
        })),
    })));
    app.post('/prepare', (request, reply) => signedEndpoint(agent, request, reply, async (payload) => {
        const taskTemplate = requiredString(payload, 'task_template');
        const taskId = requiredString(payload, 'task_id');
        const handler = requiredHandler(agent.prepareHandlers, taskTemplate);
        const inputs = objectPayload(payload.initial_inputs);
        const ctx = contextFor(agent, payload, taskId, taskTemplate, inputs);
        const result = await handler(ctx.inputs, ctx);
        const response = objectPayload(result);
        agent.taskStates.set(taskId, stringValue(response.state) ?? 'preparing');
        return response;
    }));
    app.post('/preview', (request, reply) => signedEndpoint(agent, request, reply, async (payload) => {
        const taskTemplate = requiredString(payload, 'task_template');
        const taskId = requiredString(payload, 'task_id');
        const inputs = objectPayload(payload.current_inputs);
        const ctx = contextFor(agent, payload, taskId, taskTemplate, inputs);
        const handler = agent.previewHandlers.get(taskTemplate);
        const preview = handler ? await handler(ctx.inputs, ctx) : { type: 'static', value: 'Preview unavailable in local SDK fallback' };
        return {
            task_id: taskId,
            preview_session_id: payload.preview_session_id,
            primitive_id: payload.primitive_id,
            preview,
        };
    }));
    app.post('/execute', (request, reply) => signedEndpoint(agent, request, reply, async (payload) => {
        const taskTemplate = requiredString(payload, 'task_template');
        const taskId = requiredString(payload, 'task_id');
        const handler = requiredHandler(agent.runHandlers, taskTemplate);
        const inputs = objectPayload(payload.inputs);
        const ctx = contextFor(agent, payload, taskId, taskTemplate, inputs);
        const result = await handler(ctx.inputs, ctx);
        recordContextEvents(agent, taskId, ctx);
        const response = objectPayload(result);
        response.task_id ??= taskId;
        response.accepted ??= true;
        // N1.5: round-trip the opaque continuation blob if the handler set one (an explicit
        // setAgentState wins over a blob placed on the result dict directly).
        if (ctx.nextAgentState !== null)
            response.agent_state = ctx.nextAgentState;
        if (response.agent_state && typeof response.agent_state === 'object' && !Array.isArray(response.agent_state)) {
            agent.taskAgentState.set(taskId, response.agent_state);
        }
        if (!agent.taskStates.has(taskId))
            agent.taskStates.set(taskId, 'executing');
        return response;
    }));
    app.post('/clarification_response', (request, reply) => signedEndpoint(agent, request, reply, async (payload) => {
        const taskId = requiredString(payload, 'task_id');
        const answers = objectPayload(payload.answers);
        const delegated = booleanRecord(payload.delegated_decisions);
        agent.answersByTask.set(taskId, { ...(agent.answersByTask.get(taskId) ?? {}), ...answers });
        agent.delegatedByTask.set(taskId, { ...(agent.delegatedByTask.get(taskId) ?? {}), ...delegated });
        const nextState = payload.phase === 'pre_execution' ? 'preparing' : 'executing';
        agent.taskStates.set(taskId, nextState);
        return { task_id: taskId, accepted: true, next_state: nextState };
    }));
    app.post('/status', (request, reply) => signedEndpoint(agent, request, reply, async (payload) => {
        const taskId = requiredString(payload, 'task_id');
        return {
            task_id: taskId,
            state: agent.taskStates.get(taskId) ?? 'unknown',
            events: agent.taskEvents.get(taskId) ?? [],
        };
    }));
    app.post('/cancel', (request, reply) => signedEndpoint(agent, request, reply, async (payload) => {
        const taskId = requiredString(payload, 'task_id');
        agent.taskStates.set(taskId, 'cancelled');
        return { task_id: taskId, cancelling: true };
    }));
    app.post('/result', (request, reply) => signedEndpoint(agent, request, reply, async (payload) => {
        const taskId = requiredString(payload, 'task_id');
        const response = {
            task_id: taskId,
            state: agent.taskStates.get(taskId) ?? 'unknown',
            artifacts: agent.taskArtifacts.get(taskId) ?? [],
        };
        // N1.5: surface the continuation blob from result too (see /execute).
        const agentState = agent.taskAgentState.get(taskId);
        if (agentState !== undefined)
            response.agent_state = agentState;
        return response;
    }));
    return app;
}
async function signedEndpoint(agent, request, reply, handler) {
    const body = rawRequestBody(request.body);
    const payload = parseBody(body);
    let principal;
    try {
        principal = verifyRequestSignature({
            method: request.method,
            path: requestPath(request),
            body,
            headers: request.headers,
            secret: agent.secret,
        });
    }
    catch (error) {
        reply.code(401).send({ error: error instanceof Error ? error.message : 'invalid_signature' });
        return;
    }
    const storeKey = `${request.url}:${principal.idempotencyKey}`;
    const bodyHash = requestBodyHash(body);
    const stored = agent.idempotencyStore.get(storeKey);
    if (stored) {
        if (stored.bodyHash !== bodyHash) {
            reply.code(409).send({ error: 'idempotency_key_conflict' });
            return;
        }
        reply.header('x-worklane-idempotent-replay', 'true').code(stored.statusCode).send(stored.payload);
        return;
    }
    const response = await handler(payload);
    agent.idempotencyStore.set(storeKey, { bodyHash, statusCode: 200, payload: response });
    reply.code(200).send(response);
}
function contextFor(agent, payload, taskId, taskTemplate, inputs) {
    return new Context({
        agent,
        taskId,
        taskTemplate,
        inputs,
        answers: agent.answersByTask.get(taskId) ?? {},
        delegatedDecisions: agent.delegatedByTask.get(taskId) ?? {},
        toolAccessGrants: Array.isArray(payload.tool_access_grants) ? payload.tool_access_grants : [],
        callbackUrls: stringRecord(payload.callback_urls),
        sampleMode: payload.sample_mode === true,
        budgetCap: objectPayload(payload.budget_cap),
        sessionContext: objectPayload(payload.session_context),
        agentState: objectPayload(payload.agent_state),
    });
}
function recordContextEvents(agent, taskId, ctx) {
    const events = agent.taskEvents.get(taskId) ?? [];
    events.push(...ctx.emittedEvents);
    agent.taskEvents.set(taskId, events);
    for (const event of ctx.emittedEvents) {
        if (event.kind === 'artifact_staged') {
            const artifact = event.payload.artifact;
            if (artifact && typeof artifact === 'object') {
                const artifacts = agent.taskArtifacts.get(taskId) ?? [];
                artifacts.push(artifact);
                agent.taskArtifacts.set(taskId, artifacts);
            }
            agent.taskStates.set(taskId, 'artifact_review');
        }
        else if (event.kind === 'sample_complete') {
            agent.taskStates.set(taskId, 'sample_review');
        }
        else if (event.kind === 'clarification_required') {
            agent.taskStates.set(taskId, 'clarification_required');
        }
        else if (event.kind === 'status' && !agent.taskStates.has(taskId)) {
            agent.taskStates.set(taskId, 'executing');
        }
    }
}
function requiredHandler(handlers, taskTemplate) {
    const handler = handlers.get(taskTemplate);
    if (!handler)
        throw new Error(`unknown_task_template:${taskTemplate}`);
    return handler;
}
function requiredString(payload, key) {
    const value = payload[key];
    if (typeof value !== 'string' || value.length === 0)
        throw new Error(`${key}_required`);
    return value;
}
function rawRequestBody(body) {
    if (Buffer.isBuffer(body))
        return body;
    if (typeof body === 'string')
        return Buffer.from(body, 'utf8');
    return stableJsonBuffer(objectPayload(body));
}
function requestPath(request) {
    const url = request.url ?? '/';
    const queryIndex = url.indexOf('?');
    return queryIndex === -1 ? url : url.slice(0, queryIndex);
}
function parseBody(body) {
    if (Buffer.isBuffer(body))
        return JSON.parse(body.toString('utf8'));
    return objectPayload(body);
}
function objectPayload(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}
function booleanRecord(value) {
    const source = objectPayload(value);
    return Object.fromEntries(Object.entries(source).map(([key, item]) => [key, Boolean(item)]));
}
function stringRecord(value) {
    const source = objectPayload(value);
    return Object.fromEntries(Object.entries(source).filter((entry) => typeof entry[1] === 'string'));
}
function stringValue(value) {
    return typeof value === 'string' ? value : undefined;
}
