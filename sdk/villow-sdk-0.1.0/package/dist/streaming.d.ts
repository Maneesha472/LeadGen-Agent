export type Part = {
    type: string;
    [key: string]: unknown;
};
export type StreamEvent = {
    type: string;
    seq: number;
    run_id: string;
    ts: number;
    nonce: string;
    part?: Part;
    data: Record<string, unknown>;
};
export declare const EVENT: {
    readonly RUN_STARTED: "RUN_STARTED";
    readonly RUN_FINISHED: "RUN_FINISHED";
    readonly RUN_ERROR: "RUN_ERROR";
    readonly STEP_STARTED: "STEP_STARTED";
    readonly TEXT_MESSAGE_CHUNK: "TEXT_MESSAGE_CHUNK";
    readonly PART: "PART";
    readonly ARTIFACT_STAGED: "ARTIFACT_STAGED";
    readonly APPROVAL_REQUIRED: "APPROVAL_REQUIRED";
    readonly CLARIFICATION_REQUIRED: "CLARIFICATION_REQUIRED";
    readonly BUDGET_HOLD: "BUDGET_HOLD";
    readonly COST_UPDATE: "COST_UPDATE";
    readonly BUDGET_SETTLE: "BUDGET_SETTLE";
};
type Column = string | {
    key?: string;
    label?: string;
    type?: string;
};
export declare function tablePart(columns: Column[], rows: Array<unknown[] | Record<string, unknown>>, opts?: {
    title?: string;
    reconciliation?: Record<string, unknown>;
    exceptions?: Array<Record<string, unknown>>;
}): Part;
export declare function artifactToPart(artifact: Record<string, unknown>): Part;
/**
 * Adapt a publisher agent's SDK emissions ([{kind, payload}]) into a canonical AG-UI Stream
 * (plan 11 Phase 7) — the migration path for existing SDK agents. Parity with
 * villow.streaming.events_to_stream (Python).
 */
export declare function eventsToStream(emittedEvents: Array<{
    kind?: string;
    payload?: Record<string, unknown>;
}>, runId?: string): Stream;
export declare class Stream {
    readonly runId: string;
    private events_;
    private seq;
    private started;
    private finished;
    constructor(runId?: string);
    private push;
    private emit;
    reasoning(text: string): this;
    text(text: string, role?: string): this;
    step(label: string): this;
    code(source: string, opts?: {
        language?: string;
        filename?: string;
    }): this;
    table(opts: {
        columns: Column[];
        rows: Array<unknown[] | Record<string, unknown>>;
        title?: string;
        reconciliation?: Record<string, unknown>;
        exceptions?: Array<Record<string, unknown>>;
    }): this;
    file(opts: {
        id: string;
        name: string;
        mime: string;
        url: string;
        size_bytes?: number;
    }): this;
    fileSet(opts: {
        files: Array<Record<string, unknown>>;
        title?: string;
    }): this;
    stageArtifact(part: Part): this;
    requireApproval(opts: {
        action: string;
        summary?: string;
        diff?: Record<string, unknown>;
        target?: Record<string, unknown>;
        approvalId?: string;
    }): this;
    clarify(opts: {
        question: string;
        options?: Array<Record<string, unknown>>;
        decideForMe?: Record<string, unknown>;
        allowFreeText?: boolean;
        clarificationId?: string;
    }): this;
    moneyHold(opts?: {
        typical?: number;
        ceiling?: number;
        hold?: number;
    }): this;
    moneySettle(opts: {
        captured: number;
        hold?: number;
        stats?: Record<string, unknown>;
    }): this;
    finish(): this;
    error(message: string): this;
    events(): StreamEvent[];
    sse(): IterableIterator<string>;
    static fromBatch(result: unknown, runId?: string): Stream;
}
export {};
