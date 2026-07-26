import { stableJsonBuffer } from './agent.js';
import { signRequest } from './signing.js';
export class MockPlatformHarness {
    agent;
    app;
    counter = 0;
    renderMode;
    keyId;
    publisherId;
    agentId;
    secret;
    constructor(agent, options = {}) {
        this.agent = agent;
        this.app = agent.fastifyApp();
        this.renderMode = options.renderMode ?? 'rich';
        this.keyId = options.keyId ?? agent.keyId;
        this.publisherId = options.publisherId ?? agent.publisherId;
        this.agentId = options.agentId ?? agent.agentId;
        this.secret = options.secret ?? agent.secret;
    }
    async runTask(taskTemplate, inputs, options = {}) {
        const taskId = `task_${Date.now()}_${++this.counter}`;
        await this.post('/discover', {});
        let prepare = await this.post('/prepare', { task_id: taskId, task_template: taskTemplate, initial_inputs: inputs });
        const compositionResponse = prepare.composition_response;
        if (prepare.state === 'clarification_required') {
            const answers = options.answers ?? answersFromDecideForMe(prepare.questions);
            await this.post('/clarification_response', {
                task_id: taskId,
                clarification_id: prepare.clarification_id,
                phase: prepare.phase,
                answers,
                delegated_decisions: options.delegatedDecisions ?? {},
            });
            prepare = await this.post('/prepare', { task_id: taskId, task_template: taskTemplate, initial_inputs: inputs });
        }
        await this.post('/execute', {
            task_id: taskId,
            task_template: taskTemplate,
            inputs: prepare.normalized_inputs ?? inputs,
            tool_access_grants: [],
            callback_urls: {},
            sample_mode: false,
        });
        const result = await this.post('/result', { task_id: taskId });
        if (Array.isArray(result.artifacts) && result.artifacts.length > 0)
            result.state = 'completed';
        if (compositionResponse) {
            result.composition_response = compositionResponse;
            if (this.renderMode === 'simple')
                result.simple_fallback_slots = compositionResponse.fallback_slots;
        }
        return result;
    }
    async post(path, payload) {
        const body = stableJsonBuffer(payload);
        const idempotencyKey = `harness_${++this.counter}`;
        const headers = signRequest({
            method: 'POST',
            path,
            body,
            keyId: this.keyId,
            secret: this.secret,
            publisherId: this.publisherId,
            agentId: this.agentId,
            idempotencyKey,
        });
        headers['content-type'] = 'application/json';
        const response = await this.app.inject({ method: 'POST', url: path, payload: body, headers });
        if (response.statusCode < 200 || response.statusCode >= 300) {
            throw new Error(`harness_request_failed:${path}:${response.statusCode}:${response.body}`);
        }
        return response.json();
    }
    async close() {
        await this.app.close();
    }
}
function answersFromDecideForMe(questions) {
    return Object.fromEntries(questions.map((question) => {
        const decision = question.decide_for_me;
        return [String(question.id), decision && Object.hasOwn(decision, 'value') ? decision.value : question.default_value];
    }));
}
