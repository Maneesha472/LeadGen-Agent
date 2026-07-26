export interface ProgressEventPayload {
    event_type: string;
    [key: string]: unknown;
}
export declare class ProgressEvent {
    static itemCompleted(input: {
        current: number;
        total: number;
        itemId: string;
        thumbnailUrl?: string;
        focusItemId?: string;
        displayName?: string;
        detail?: string;
    }): ProgressEventPayload;
    static milestone(input: {
        id: string;
        state: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
        label?: string;
        detail?: string;
    }): ProgressEventPayload;
    static unitCharge(input: {
        amount?: number;
        currency?: string;
        amountInrPaise?: number;
        unitCount?: number;
        unit?: string;
        metadata?: Record<string, unknown>;
    }): ProgressEventPayload;
    /** @deprecated Use unitCharge. The callback wire key remains stable for compatibility. */
    static costTelemetry(input: {
        amount: number;
        currency: string;
        unitCount?: number;
        unit?: string;
        metadata?: Record<string, unknown>;
    }): ProgressEventPayload;
}
