export interface ProgressEventPayload {
  event_type: string;
  [key: string]: unknown;
}

export class ProgressEvent {
  static itemCompleted(input: {
    current: number;
    total: number;
    itemId: string;
    thumbnailUrl?: string;
    focusItemId?: string;
    displayName?: string;
    detail?: string;
  }): ProgressEventPayload {
    if (input.current < 0 || input.total < 0 || input.current > input.total) {
      throw new Error('progress current/total values are invalid');
    }
    const item: Record<string, unknown> = { item_id: input.itemId, state: 'completed' };
    if (input.thumbnailUrl) item.thumbnail_url = input.thumbnailUrl;
    if (input.displayName) item.display_name = input.displayName;
    const payload: ProgressEventPayload = {
      event_type: 'item_completed',
      progress: { current: input.current, total: input.total },
      item,
    };
    if (input.focusItemId) payload.focus_item_id = input.focusItemId;
    if (input.detail) payload.detail = input.detail;
    return payload;
  }

  static milestone(input: { id: string; state: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'; label?: string; detail?: string }): ProgressEventPayload {
    const milestone: Record<string, unknown> = { id: input.id, state: input.state };
    if (input.label) milestone.label = input.label;
    const payload: ProgressEventPayload = { event_type: 'milestone', milestone };
    if (input.detail) payload.detail = input.detail;
    return payload;
  }

  static unitCharge(input: {
    amount?: number;
    currency?: string;
    amountInrPaise?: number;
    unitCount?: number;
    unit?: string;
    metadata?: Record<string, unknown>;
  }): ProgressEventPayload {
    const currency = input.currency ?? 'INR';
    const unitChargeTelemetry: Record<string, unknown> = {};
    if (input.amountInrPaise !== undefined) unitChargeTelemetry.reported_cost_inr_paise = input.amountInrPaise;
    else if (currency.toUpperCase() === 'INR' && input.amount !== undefined) unitChargeTelemetry.reported_cost_inr_paise = Math.trunc(input.amount);
    else {
      unitChargeTelemetry.publisher_reported_amount = input.amount;
      unitChargeTelemetry.currency = currency;
    }
    if (input.unitCount !== undefined) unitChargeTelemetry.unit_count = input.unitCount;
    if (input.unit !== undefined) unitChargeTelemetry.unit = input.unit;
    if (input.metadata !== undefined) unitChargeTelemetry.metadata = input.metadata;
    return { event_type: 'cost_telemetry', cost_telemetry: unitChargeTelemetry };
  }

  /** @deprecated Use unitCharge. The callback wire key remains stable for compatibility. */
  static costTelemetry(input: {
    amount: number;
    currency: string;
    unitCount?: number;
    unit?: string;
    metadata?: Record<string, unknown>;
  }): ProgressEventPayload {
    return ProgressEvent.unitCharge(input);
  }
}
