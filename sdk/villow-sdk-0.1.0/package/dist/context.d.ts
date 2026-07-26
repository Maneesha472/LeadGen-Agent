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
export declare class Context {
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
    sessionContext: Record<string, unknown>;
    agentState: Record<string, unknown>;
    nextAgentState: Record<string, unknown> | null;
    emittedEvents: Array<{
        kind: string;
        payload: Record<string, unknown>;
    }>;
    tools: Tools;
    constructor(options: ContextOptions);
    /**
     * Set the opaque continuation blob to return from this execute/result. The platform stores it
     * (session-scoped, encrypted, size-capped) and replays it as `ctx.agentState` on the next unit.
     * Must be a JSON object; keep it small.
     */
    setAgentState(state: Record<string, unknown>): void;
    hasAnswer(questionId: string): boolean;
    answer(questionId: string, defaultValue?: unknown): unknown;
    wasDelegated(questionId: string): boolean;
    readyToAuthorize(input: {
        normalizedInputs: Record<string, unknown>;
        compositionResponse?: Record<string, unknown>;
        priceUnits?: Record<string, unknown>;
    }): Record<string, unknown>;
    requestClarification(questions: Array<Record<string, unknown>>, options?: {
        compositionResponse?: Record<string, unknown>;
    }): Record<string, unknown>;
    requestMidExecutionClarification(questions: Array<Record<string, unknown>>): Promise<Record<string, unknown>>;
    reportProgress(event: Record<string, unknown>): Promise<Record<string, unknown>>;
    reportSampleComplete(sampleArtifacts: Array<Record<string, unknown>>): Promise<Record<string, unknown>>;
    stageArtifact(input: Record<string, unknown>): Promise<Record<string, unknown>>;
    reportUnitCharge(unitCharge: Record<string, unknown>): Promise<Record<string, unknown>>;
    /** @deprecated Use reportUnitCharge. */
    reportCostTelemetry(costTelemetry: Record<string, unknown>): Promise<Record<string, unknown>>;
    resolveToolAccessGrant(toolName: string): string | null;
    idempotencyKey(operation: string): string;
    private emitCallback;
}
