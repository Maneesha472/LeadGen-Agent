import { randomUUID } from 'node:crypto';
import { Tools } from './tools.js';
export class Context {
    agent;
    taskId;
    taskTemplate;
    inputs;
    answers;
    delegatedDecisions;
    toolAccessGrants;
    callbackUrls;
    sampleMode;
    budgetCap;
    // M6: platform-replayed session memory for follow-up units (empty for a fresh task).
    // The publisher stays stateless — read prior transcript/artifacts from here.
    sessionContext;
    // N1.5: the platform replays the opaque continuation blob this agent returned on a prior unit
    // (empty for a fresh session). The platform stores/replays it but never interprets it; call
    // setAgentState(...) to update it for the next unit.
    agentState;
    nextAgentState = null;
    emittedEvents = [];
    tools;
    constructor(options) {
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
    setAgentState(state) {
        if (!state || typeof state !== 'object' || Array.isArray(state)) {
            throw new Error('agentState must be a JSON object');
        }
        this.nextAgentState = state;
    }
    hasAnswer(questionId) {
        return Object.hasOwn(this.answers, questionId);
    }
    answer(questionId, defaultValue) {
        return this.answers[questionId] ?? defaultValue;
    }
    wasDelegated(questionId) {
        return Boolean(this.delegatedDecisions[questionId]);
    }
    readyToAuthorize(input) {
        const payload = {
            task_id: this.taskId,
            state: 'ready_to_authorize',
            normalized_inputs: input.normalizedInputs,
            price_units: input.priceUnits ?? {},
        };
        if (input.compositionResponse)
            payload.composition_response = input.compositionResponse;
        return payload;
    }
    requestClarification(questions, options = {}) {
        validateQuestions(questions);
        const payload = {
            task_id: this.taskId,
            state: 'clarification_required',
            phase: 'pre_execution',
            clarification_id: `clarification_${randomUUID().replace(/-/g, '')}`,
            questions,
        };
        if (options.compositionResponse)
            payload.composition_response = options.compositionResponse;
        return payload;
    }
    async requestMidExecutionClarification(questions) {
        validateQuestions(questions);
        return this.emitCallback('clarification_required', {
            task_id: this.taskId,
            state: 'clarification_required',
            phase: 'mid_execution',
            clarification_id: `clarification_${randomUUID().replace(/-/g, '')}`,
            questions,
        });
    }
    async reportProgress(event) {
        return this.emitCallback('status', { task_id: this.taskId, state: 'executing', progress: event });
    }
    async reportSampleComplete(sampleArtifacts) {
        return this.emitCallback('sample_complete', { task_id: this.taskId, state: 'sample_review', sample_artifacts: sampleArtifacts });
    }
    async stageArtifact(input) {
        const artifact = Object.hasOwn(input, 'artifact') ? input.artifact : input;
        return this.emitCallback('artifact_staged', { task_id: this.taskId, state: 'artifact_review', artifact });
    }
    async reportUnitCharge(unitCharge) {
        return this.emitCallback('status', { task_id: this.taskId, state: 'executing', cost_telemetry: unitCharge });
    }
    /** @deprecated Use reportUnitCharge. */
    async reportCostTelemetry(costTelemetry) {
        return this.reportUnitCharge(costTelemetry);
    }
    resolveToolAccessGrant(toolName) {
        if (!this.toolAccessGrants.length)
            return null;
        const prefix = toolName.includes('.') ? `${toolName.split('.', 1)[0]}.` : toolName;
        for (const grant of this.toolAccessGrants) {
            if (typeof grant === 'string')
                return grant;
            const grantTool = String(grant.tool_name ?? '');
            const grantId = grant.tool_access_grant_id ?? grant.grant_id ?? grant.id;
            if (grantTool === toolName && grantId)
                return String(grantId);
        }
        for (const grant of this.toolAccessGrants) {
            if (typeof grant !== 'object' || grant === null)
                continue;
            const grantTool = String(grant.tool_name ?? '');
            const grantId = grant.tool_access_grant_id ?? grant.grant_id ?? grant.id;
            if (grantTool.startsWith(prefix) && grantId)
                return String(grantId);
        }
        const legacyIds = [];
        for (const grant of this.toolAccessGrants) {
            if (typeof grant !== 'object' || grant === null)
                continue;
            const grantId = grant.tool_access_grant_id ?? grant.grant_id ?? grant.id;
            if (grantId && !grant.tool_name)
                legacyIds.push(String(grantId));
        }
        if (legacyIds.length === 1)
            return legacyIds[0];
        return null;
    }
    idempotencyKey(operation) {
        return `${this.taskId}:${operation}:${randomUUID().replace(/-/g, '')}`;
    }
    async emitCallback(kind, payload) {
        this.emittedEvents.push({ kind, payload });
        const url = this.callbackUrls[kind];
        if (!url)
            return { accepted: true, local: true };
        return this.agent.signedPlatformPost(url, payload, { idempotencyKey: this.idempotencyKey(kind) });
    }
}
function validateQuestions(questions) {
    for (const question of questions) {
        if (!Object.hasOwn(question, 'decide_for_me') || question.decide_for_me === undefined || question.decide_for_me === null) {
            throw new Error('every clarification question requires decideForMe');
        }
    }
}
