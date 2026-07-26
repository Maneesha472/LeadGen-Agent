import { randomUUID } from 'node:crypto';

import type { Agent } from './agent.js';
import { Tools } from './tools.js';

export interface ContextOptions {
  agent: Agent;
  taskId: string;
  taskTemplate: string;
  inputs: Record<string, unknown>;
  answers?: Record<string, unknown>;
  delegatedDecisions?: Record<string, boolean>;
  toolAccessGrants?: Array<Record<string, unknown> | string>;
  callbackUrls?: Record<string, string>;
  sampleMode?: boolean;
  budgetCap?: Record<string, unknown>;
  sessionContext?: Record<string, unknown>;
  agentState?: Record<string, unknown>;
}

export class Context {
  agent: Agent;
  taskId: string;
  taskTemplate: string;
  inputs: Record<string, unknown>;
  answers: Record<string, unknown>;
  delegatedDecisions: Record<string, boolean>;
  toolAccessGrants: Array<Record<string, unknown> | string>;
  callbackUrls: Record<string, string>;
  sampleMode: boolean;
  budgetCap: Record<string, unknown>;
  // M6: platform-replayed session memory for follow-up units (empty for a fresh task).
  // The publisher stays stateless — read prior transcript/artifacts from here.
  sessionContext: Record<string, unknown>;
  // N1.5: the platform replays the opaque continuation blob this agent returned on a prior unit
  // (empty for a fresh session). The platform stores/replays it but never interprets it; call
  // setAgentState(...) to update it for the next unit.
  agentState: Record<string, unknown>;
  nextAgentState: Record<string, unknown> | null = null;
  emittedEvents: Array<{ kind: string; payload: Record<string, unknown> }> = [];
  tools: Tools;

  constructor(options: ContextOptions) {
    this.agent = options.agent;
    this.taskId = options.taskId;
    this.taskTemplate = options.taskTemplate;
    this.inputs = options.inputs;
    this.answers = options.answers ?? {};
    this.delegatedDecisions = options.delegatedDecisions ?? {};
    this.toolAccessGrants = options.toolAccessGrants ?? [];
    this.callbackUrls = options.callbackUrls ?? {};
    this.sampleMode = options.sampleMode ?? false;
    this.budgetCap = options.budgetCap ?? {};
    this.sessionContext = options.sessionContext ?? {};
    this.agentState = options.agentState ?? {};
    this.tools = new Tools(this);
  }

  /**
   * Set the opaque continuation blob to return from this execute/result. The platform stores it
   * (session-scoped, encrypted, size-capped) and replays it as `ctx.agentState` on the next unit.
   * Must be a JSON object; keep it small.
   */
  setAgentState(state: Record<string, unknown>): void {
    if (!state || typeof state !== 'object' || Array.isArray(state)) {
      throw new Error('agentState must be a JSON object');
    }
    this.nextAgentState = state;
  }

  hasAnswer(questionId: string): boolean {
    return Object.hasOwn(this.answers, questionId);
  }

  answer(questionId: string, defaultValue?: unknown): unknown {
    return this.answers[questionId] ?? defaultValue;
  }

  wasDelegated(questionId: string): boolean {
    return Boolean(this.delegatedDecisions[questionId]);
  }

  readyToAuthorize(input: {
    normalizedInputs: Record<string, unknown>;
    compositionResponse?: Record<string, unknown>;
    priceUnits?: Record<string, unknown>;
  }): Record<string, unknown> {
    const payload: Record<string, unknown> = {
      task_id: this.taskId,
      state: 'ready_to_authorize',
      normalized_inputs: input.normalizedInputs,
      price_units: input.priceUnits ?? {},
    };
    if (input.compositionResponse) payload.composition_response = input.compositionResponse;
    return payload;
  }

  requestClarification(questions: Array<Record<string, unknown>>, options: { compositionResponse?: Record<string, unknown> } = {}): Record<string, unknown> {
    validateQuestions(questions);
    const payload: Record<string, unknown> = {
      task_id: this.taskId,
      state: 'clarification_required',
      phase: 'pre_execution',
      clarification_id: `clarification_${randomUUID().replace(/-/g, '')}`,
      questions,
    };
    if (options.compositionResponse) payload.composition_response = options.compositionResponse;
    return payload;
  }

  async requestMidExecutionClarification(questions: Array<Record<string, unknown>>): Promise<Record<string, unknown>> {
    validateQuestions(questions);
    return this.emitCallback('clarification_required', {
      task_id: this.taskId,
      state: 'clarification_required',
      phase: 'mid_execution',
      clarification_id: `clarification_${randomUUID().replace(/-/g, '')}`,
      questions,
    });
  }

  async reportProgress(event: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.emitCallback('status', { task_id: this.taskId, state: 'executing', progress: event });
  }

  async reportSampleComplete(sampleArtifacts: Array<Record<string, unknown>>): Promise<Record<string, unknown>> {
    return this.emitCallback('sample_complete', { task_id: this.taskId, state: 'sample_review', sample_artifacts: sampleArtifacts });
  }

  async stageArtifact(input: Record<string, unknown>): Promise<Record<string, unknown>> {
    const artifact = Object.hasOwn(input, 'artifact') ? input.artifact : input;
    return this.emitCallback('artifact_staged', { task_id: this.taskId, state: 'artifact_review', artifact });
  }

  async reportUnitCharge(unitCharge: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.emitCallback('status', { task_id: this.taskId, state: 'executing', cost_telemetry: unitCharge });
  }

  /** @deprecated Use reportUnitCharge. */
  async reportCostTelemetry(costTelemetry: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.reportUnitCharge(costTelemetry);
  }

  resolveToolAccessGrant(toolName: string): string | null {
    if (!this.toolAccessGrants.length) return null;
    const prefix = toolName.includes('.') ? `${toolName.split('.', 1)[0]}.` : toolName;
    for (const grant of this.toolAccessGrants) {
      if (typeof grant === 'string') return grant;
      const grantTool = String(grant.tool_name ?? '');
      const grantId = grant.tool_access_grant_id ?? grant.grant_id ?? grant.id;
      if (grantTool === toolName && grantId) return String(grantId);
    }
    for (const grant of this.toolAccessGrants) {
      if (typeof grant !== 'object' || grant === null) continue;
      const grantTool = String(grant.tool_name ?? '');
      const grantId = grant.tool_access_grant_id ?? grant.grant_id ?? grant.id;
      if (grantTool.startsWith(prefix) && grantId) return String(grantId);
    }
    const legacyIds: string[] = [];
    for (const grant of this.toolAccessGrants) {
      if (typeof grant !== 'object' || grant === null) continue;
      const grantId = grant.tool_access_grant_id ?? grant.grant_id ?? grant.id;
      if (grantId && !grant.tool_name) legacyIds.push(String(grantId));
    }
    if (legacyIds.length === 1) return legacyIds[0]!;
    return null;
  }

  idempotencyKey(operation: string): string {
    return `${this.taskId}:${operation}:${randomUUID().replace(/-/g, '')}`;
  }

  private async emitCallback(kind: string, payload: Record<string, unknown>): Promise<Record<string, unknown>> {
    this.emittedEvents.push({ kind, payload });
    const url = this.callbackUrls[kind];
    if (!url) return { accepted: true, local: true };
    return this.agent.signedPlatformPost(url, payload, { idempotencyKey: this.idempotencyKey(kind) });
  }
}

function validateQuestions(questions: Array<Record<string, unknown>>): void {
  for (const question of questions) {
    if (!Object.hasOwn(question, 'decide_for_me') || question.decide_for_me === undefined || question.decide_for_me === null) {
      throw new Error('every clarification question requires decideForMe');
    }
  }
}
