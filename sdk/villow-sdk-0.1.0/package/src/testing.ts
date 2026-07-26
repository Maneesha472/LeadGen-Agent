import type { FastifyInstance } from 'fastify';

import { stableJsonBuffer, type Agent } from './agent.js';
import { signRequest } from './signing.js';

export interface HarnessOptions {
  renderMode?: 'rich' | 'simple';
  keyId?: string;
  publisherId?: string;
  agentId?: string;
  secret?: string;
}

export class MockPlatformHarness {
  private app: FastifyInstance;
  private counter = 0;
  private renderMode: 'rich' | 'simple';
  private keyId: string;
  private publisherId: string;
  private agentId: string;
  private secret: string;

  constructor(private agent: Agent, options: HarnessOptions = {}) {
    this.app = agent.fastifyApp();
    this.renderMode = options.renderMode ?? 'rich';
    this.keyId = options.keyId ?? agent.keyId;
    this.publisherId = options.publisherId ?? agent.publisherId;
    this.agentId = options.agentId ?? agent.agentId;
    this.secret = options.secret ?? agent.secret;
  }

  async runTask(
    taskTemplate: string,
    inputs: Record<string, unknown>,
    options: { answers?: Record<string, unknown>; delegatedDecisions?: Record<string, boolean> } = {},
  ): Promise<Record<string, unknown>> {
    const taskId = `task_${Date.now()}_${++this.counter}`;
    await this.post('/discover', {});
    let prepare = await this.post('/prepare', { task_id: taskId, task_template: taskTemplate, initial_inputs: inputs });
    const compositionResponse = prepare.composition_response as Record<string, unknown> | undefined;

    if (prepare.state === 'clarification_required') {
      const answers = options.answers ?? answersFromDecideForMe(prepare.questions as Array<Record<string, unknown>>);
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
    if (Array.isArray(result.artifacts) && result.artifacts.length > 0) result.state = 'completed';
    if (compositionResponse) {
      result.composition_response = compositionResponse;
      if (this.renderMode === 'simple') result.simple_fallback_slots = compositionResponse.fallback_slots;
    }
    return result;
  }

  async post(path: string, payload: Record<string, unknown>): Promise<Record<string, unknown>> {
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
    return response.json() as Record<string, unknown>;
  }

  async close(): Promise<void> {
    await this.app.close();
  }
}

function answersFromDecideForMe(questions: Array<Record<string, unknown>>): Record<string, unknown> {
  return Object.fromEntries(questions.map((question) => {
    const decision = question.decide_for_me as Record<string, unknown> | undefined;
    return [String(question.id), decision && Object.hasOwn(decision, 'value') ? decision.value : question.default_value];
  }));
}
