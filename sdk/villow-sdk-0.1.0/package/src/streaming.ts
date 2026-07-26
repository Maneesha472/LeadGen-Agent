// AG-UI-aligned streaming emit API for publisher agents (D-104, plan 11 Phase 6).
// Node parity with sdk/python/src/villow/streaming.py: same event-type names and part schemas (wire
// fields stay snake_case), so the platform ingests both SDKs identically. Publishers supply DATA; the
// platform owns rendering (closed registry, D-106).

import { randomUUID } from 'node:crypto';

export type Part = { type: string; [key: string]: unknown };
export type StreamEvent = {
  type: string;
  seq: number;
  run_id: string;
  ts: number;
  nonce: string;
  part?: Part;
  data: Record<string, unknown>;
};

export const EVENT = {
  RUN_STARTED: 'RUN_STARTED',
  RUN_FINISHED: 'RUN_FINISHED',
  RUN_ERROR: 'RUN_ERROR',
  STEP_STARTED: 'STEP_STARTED',
  TEXT_MESSAGE_CHUNK: 'TEXT_MESSAGE_CHUNK',
  PART: 'PART',
  ARTIFACT_STAGED: 'ARTIFACT_STAGED',
  APPROVAL_REQUIRED: 'APPROVAL_REQUIRED',
  CLARIFICATION_REQUIRED: 'CLARIFICATION_REQUIRED',
  BUDGET_HOLD: 'BUDGET_HOLD',
  COST_UPDATE: 'COST_UPDATE',
  BUDGET_SETTLE: 'BUDGET_SETTLE',
} as const;

type Column = string | { key?: string; label?: string; type?: string };

export function tablePart(
  columns: Column[],
  rows: Array<unknown[] | Record<string, unknown>>,
  opts: { title?: string; reconciliation?: Record<string, unknown>; exceptions?: Array<Record<string, unknown>> } = {},
): Part {
  const cols: Array<{ key: string; label: string; type?: string }> = [];
  const keys: string[] = [];
  for (const col of columns) {
    if (typeof col === 'object') {
      const key = String(col.key ?? col.label);
      cols.push({ key, label: col.label ?? key, type: col.type ?? 'string' });
      keys.push(key);
    } else {
      cols.push({ key: String(col), label: String(col) });
      keys.push(String(col));
    }
  }
  const outRows = rows.map((row) => {
    if (Array.isArray(row)) {
      const obj: Record<string, unknown> = {};
      row.forEach((v, i) => {
        obj[keys[i] ?? `c${i}`] = v;
      });
      return obj;
    }
    return row;
  });
  const part: Part = { type: 'table_data', columns: cols, rows: outRows };
  if (opts.title) part.title = opts.title;
  if (opts.reconciliation) part.reconciliation = opts.reconciliation;
  if (opts.exceptions && opts.exceptions.length) part.exceptions = opts.exceptions;
  return part;
}

export function artifactToPart(artifact: Record<string, unknown>): Part {
  const atype = (artifact.artifact_type ?? artifact.type) as string | undefined;
  const payload = (artifact.type_payload ?? artifact.payload ?? {}) as Record<string, unknown>;
  const title = artifact.title as string | undefined;
  if (atype === 'table_data') {
    return tablePart((payload.columns as Column[]) ?? [], (payload.rows as unknown[][]) ?? [], {
      title,
      reconciliation: payload.reconciliation as Record<string, unknown> | undefined,
      exceptions: payload.exceptions as Array<Record<string, unknown>> | undefined,
    });
  }
  if (atype === 'structured_fields') {
    // The legacy artifact uses a dict of fields; the streaming part wants a list of {label, value}.
    let fields = payload.fields as unknown;
    if (fields && typeof fields === 'object' && !Array.isArray(fields)) {
      fields = Object.entries(fields as Record<string, unknown>).map(([k, v]) => ({ label: k, value: v }));
    }
    return { type: 'structured_fields', fields: (fields as unknown[]) ?? [] };
  }
  if (atype && ['file_set', 'message_draft', 'event_proposal'].includes(atype)) {
    const part: Part = { type: atype, ...payload };
    if (title && atype === 'file_set') part.title = title;
    return part;
  }
  return { type: 'generic', data: { artifact_type: atype, title, ...payload }, original_type: atype };
}

function progressLabel(progress: Record<string, unknown>): string | undefined {
  const eventType = progress.event_type;
  if (eventType === 'milestone') {
    const m = (progress.milestone ?? {}) as Record<string, unknown>;
    return (m.label ?? m.id) as string | undefined;
  }
  if (eventType === 'item_completed') {
    const item = (progress.item ?? {}) as Record<string, unknown>;
    const counts = (progress.progress ?? {}) as Record<string, unknown>;
    const name = (item.display_name ?? item.item_id ?? 'item') as string;
    return counts.total ? `${name} (${counts.current}/${counts.total})` : name;
  }
  return progress.label as string | undefined;
}

function optionsToParts(options: unknown): Array<Record<string, unknown>> {
  if (!Array.isArray(options)) return [];
  return options.map((o) => (o && typeof o === 'object' ? (o as Record<string, unknown>) : { id: String(o), label: String(o) }));
}

/**
 * Adapt a publisher agent's SDK emissions ([{kind, payload}]) into a canonical AG-UI Stream
 * (plan 11 Phase 7) — the migration path for existing SDK agents. Parity with
 * villow.streaming.events_to_stream (Python).
 */
export function eventsToStream(emittedEvents: Array<{ kind?: string; payload?: Record<string, unknown> }>, runId?: string): Stream {
  const s = new Stream(runId);
  for (const ev of emittedEvents) {
    const payload = ev.payload ?? {};
    if (ev.kind === 'status') {
      const progress = payload.progress as Record<string, unknown> | undefined;
      if (progress && typeof progress === 'object') {
        const label = progressLabel(progress);
        if (label) s.step(label);
      }
    } else if (ev.kind === 'clarification_required') {
      for (const q of (payload.questions as Array<Record<string, unknown>>) ?? []) {
        s.clarify({
          question: String(q.label ?? q.question ?? ''),
          options: optionsToParts(q.options),
          decideForMe: q.decide_for_me as Record<string, unknown> | undefined,
          clarificationId: q.id as string | undefined,
        });
      }
    } else if (ev.kind === 'artifact_staged') {
      if (payload.artifact) s.stageArtifact(artifactToPart(payload.artifact as Record<string, unknown>));
    } else if (ev.kind === 'sample_complete') {
      for (const a of (payload.sample_artifacts as Array<Record<string, unknown>>) ?? []) s.stageArtifact(artifactToPart(a));
    }
  }
  return s.finish();
}

export class Stream {
  readonly runId: string;
  private events_: StreamEvent[] = [];
  private seq = 0;
  private started = false;
  private finished = false;

  constructor(runId?: string) {
    this.runId = runId ?? randomUUID().replace(/-/g, '');
  }

  private push(type: string, part?: Part, data?: Record<string, unknown>): this {
    const event: StreamEvent = { type, seq: this.seq, run_id: this.runId, ts: Date.now(), nonce: randomUUID().replace(/-/g, ''), data: data ?? {} };
    if (part !== undefined) event.part = part;
    this.events_.push(event);
    this.seq += 1;
    return this;
  }

  private emit(type: string, part?: Part, data?: Record<string, unknown>): this {
    if (!this.started) {
      this.push(EVENT.RUN_STARTED);
      this.started = true;
    }
    return this.push(type, part, data);
  }

  // content
  reasoning(text: string): this {
    return this.emit(EVENT.PART, { type: 'reasoning', text });
  }
  text(text: string, role?: string): this {
    if (role) return this.emit(EVENT.TEXT_MESSAGE_CHUNK, undefined, { text, role });
    return this.emit(EVENT.PART, { type: 'text', text });
  }
  step(label: string): this {
    return this.emit(EVENT.STEP_STARTED, undefined, { name: label });
  }
  code(source: string, opts: { language?: string; filename?: string } = {}): this {
    const part: Part = { type: 'code', source };
    if (opts.language) part.language = opts.language;
    if (opts.filename) part.filename = opts.filename;
    return this.emit(EVENT.PART, part);
  }
  table(opts: { columns: Column[]; rows: Array<unknown[] | Record<string, unknown>>; title?: string; reconciliation?: Record<string, unknown>; exceptions?: Array<Record<string, unknown>> }): this {
    return this.emit(EVENT.ARTIFACT_STAGED, tablePart(opts.columns, opts.rows, opts));
  }
  file(opts: { id: string; name: string; mime: string; url: string; size_bytes?: number }): this {
    const ref: Record<string, unknown> = { id: opts.id, name: opts.name, mime: opts.mime, url: opts.url };
    if (opts.size_bytes !== undefined) ref.size_bytes = opts.size_bytes;
    return this.emit(EVENT.PART, { type: 'file', file: ref });
  }
  fileSet(opts: { files: Array<Record<string, unknown>>; title?: string }): this {
    const part: Part = { type: 'file_set', files: opts.files };
    if (opts.title) part.title = opts.title;
    return this.emit(EVENT.ARTIFACT_STAGED, part);
  }
  stageArtifact(part: Part): this {
    return this.emit(EVENT.ARTIFACT_STAGED, part);
  }

  // trust
  requireApproval(opts: { action: string; summary?: string; diff?: Record<string, unknown>; target?: Record<string, unknown>; approvalId?: string }): this {
    const part: Part = { type: 'approval', approval_id: opts.approvalId ?? randomUUID().replace(/-/g, ''), action: opts.action, requires_approval: true };
    if (opts.summary) part.summary = opts.summary;
    if (opts.diff !== undefined) part.diff = opts.diff;
    if (opts.target !== undefined) part.target = opts.target;
    return this.emit(EVENT.APPROVAL_REQUIRED, part);
  }
  clarify(opts: { question: string; options?: Array<Record<string, unknown>>; decideForMe?: Record<string, unknown>; allowFreeText?: boolean; clarificationId?: string }): this {
    const part: Part = {
      type: 'clarification',
      clarification_id: opts.clarificationId ?? randomUUID().replace(/-/g, ''),
      question: opts.question,
      options: opts.options ?? [],
      allow_free_text: opts.allowFreeText ?? false,
      // rule #4: a clarification always carries a decide-for-me fallback.
      decide_for_me: opts.decideForMe ?? { label: 'Decide for me' },
    };
    return this.emit(EVENT.CLARIFICATION_REQUIRED, part);
  }

  // money
  moneyHold(opts: { typical?: number; ceiling?: number; hold?: number } = {}): this {
    const part: Part = { type: 'money', kind: 'hold' };
    if (opts.typical !== undefined) part.typical_credits = opts.typical;
    if (opts.ceiling !== undefined) part.ceiling_credits = opts.ceiling;
    if (opts.hold !== undefined) part.hold_credits = opts.hold;
    return this.emit(EVENT.BUDGET_HOLD, part);
  }
  moneySettle(opts: { captured: number; hold?: number; stats?: Record<string, unknown> }): this {
    const part: Part = { type: 'money', kind: 'settle', captured_credits: opts.captured };
    if (opts.hold !== undefined) part.hold_credits = opts.hold;
    if (opts.stats !== undefined) part.stats = opts.stats;
    return this.emit(EVENT.BUDGET_SETTLE, part);
  }

  // lifecycle
  finish(): this {
    if (!this.started) {
      this.push(EVENT.RUN_STARTED);
      this.started = true;
    }
    if (!this.finished) {
      this.push(EVENT.RUN_FINISHED);
      this.finished = true;
    }
    return this;
  }
  error(message: string): this {
    if (!this.started) {
      this.push(EVENT.RUN_STARTED);
      this.started = true;
    }
    if (!this.finished) {
      this.push(EVENT.RUN_ERROR, undefined, { message });
      this.finished = true;
    }
    return this;
  }

  events(): StreamEvent[] {
    if (!this.finished) this.finish();
    return [...this.events_];
  }

  *sse(): IterableIterator<string> {
    for (const event of this.events()) {
      yield `id: ${event.seq}\nevent: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`;
    }
  }

  static fromBatch(result: unknown, runId?: string): Stream {
    const stream = new Stream(runId);
    let parts: Part[];
    const r = result as Record<string, unknown>;
    if (r && typeof r === 'object' && Array.isArray(r.parts)) parts = r.parts as Part[];
    else if (r && typeof r === 'object' && r.artifact) parts = [artifactToPart(r.artifact as Record<string, unknown>)];
    else if (r && typeof r === 'object' && Array.isArray(r.artifacts)) parts = (r.artifacts as Array<Record<string, unknown>>).map(artifactToPart);
    else if (r && typeof r === 'object') parts = [{ type: 'generic', data: { ...r } }];
    else parts = [{ type: 'generic', data: { value: result } }];
    for (const part of parts) stream.stageArtifact(part);
    return stream.finish();
  }
}
