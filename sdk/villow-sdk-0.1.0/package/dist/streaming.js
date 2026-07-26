// AG-UI-aligned streaming emit API for publisher agents (D-104, plan 11 Phase 6).
// Node parity with sdk/python/src/villow/streaming.py: same event-type names and part schemas (wire
// fields stay snake_case), so the platform ingests both SDKs identically. Publishers supply DATA; the
// platform owns rendering (closed registry, D-106).
import { randomUUID } from 'node:crypto';
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
};
export function tablePart(columns, rows, opts = {}) {
    const cols = [];
    const keys = [];
    for (const col of columns) {
        if (typeof col === 'object') {
            const key = String(col.key ?? col.label);
            cols.push({ key, label: col.label ?? key, type: col.type ?? 'string' });
            keys.push(key);
        }
        else {
            cols.push({ key: String(col), label: String(col) });
            keys.push(String(col));
        }
    }
    const outRows = rows.map((row) => {
        if (Array.isArray(row)) {
            const obj = {};
            row.forEach((v, i) => {
                obj[keys[i] ?? `c${i}`] = v;
            });
            return obj;
        }
        return row;
    });
    const part = { type: 'table_data', columns: cols, rows: outRows };
    if (opts.title)
        part.title = opts.title;
    if (opts.reconciliation)
        part.reconciliation = opts.reconciliation;
    if (opts.exceptions && opts.exceptions.length)
        part.exceptions = opts.exceptions;
    return part;
}
export function artifactToPart(artifact) {
    const atype = (artifact.artifact_type ?? artifact.type);
    const payload = (artifact.type_payload ?? artifact.payload ?? {});
    const title = artifact.title;
    if (atype === 'table_data') {
        return tablePart(payload.columns ?? [], payload.rows ?? [], {
            title,
            reconciliation: payload.reconciliation,
            exceptions: payload.exceptions,
        });
    }
    if (atype === 'structured_fields') {
        // The legacy artifact uses a dict of fields; the streaming part wants a list of {label, value}.
        let fields = payload.fields;
        if (fields && typeof fields === 'object' && !Array.isArray(fields)) {
            fields = Object.entries(fields).map(([k, v]) => ({ label: k, value: v }));
        }
        return { type: 'structured_fields', fields: fields ?? [] };
    }
    if (atype && ['file_set', 'message_draft', 'event_proposal'].includes(atype)) {
        const part = { type: atype, ...payload };
        if (title && atype === 'file_set')
            part.title = title;
        return part;
    }
    return { type: 'generic', data: { artifact_type: atype, title, ...payload }, original_type: atype };
}
function progressLabel(progress) {
    const eventType = progress.event_type;
    if (eventType === 'milestone') {
        const m = (progress.milestone ?? {});
        return (m.label ?? m.id);
    }
    if (eventType === 'item_completed') {
        const item = (progress.item ?? {});
        const counts = (progress.progress ?? {});
        const name = (item.display_name ?? item.item_id ?? 'item');
        return counts.total ? `${name} (${counts.current}/${counts.total})` : name;
    }
    return progress.label;
}
function optionsToParts(options) {
    if (!Array.isArray(options))
        return [];
    return options.map((o) => (o && typeof o === 'object' ? o : { id: String(o), label: String(o) }));
}
/**
 * Adapt a publisher agent's SDK emissions ([{kind, payload}]) into a canonical AG-UI Stream
 * (plan 11 Phase 7) — the migration path for existing SDK agents. Parity with
 * villow.streaming.events_to_stream (Python).
 */
export function eventsToStream(emittedEvents, runId) {
    const s = new Stream(runId);
    for (const ev of emittedEvents) {
        const payload = ev.payload ?? {};
        if (ev.kind === 'status') {
            const progress = payload.progress;
            if (progress && typeof progress === 'object') {
                const label = progressLabel(progress);
                if (label)
                    s.step(label);
            }
        }
        else if (ev.kind === 'clarification_required') {
            for (const q of payload.questions ?? []) {
                s.clarify({
                    question: String(q.label ?? q.question ?? ''),
                    options: optionsToParts(q.options),
                    decideForMe: q.decide_for_me,
                    clarificationId: q.id,
                });
            }
        }
        else if (ev.kind === 'artifact_staged') {
            if (payload.artifact)
                s.stageArtifact(artifactToPart(payload.artifact));
        }
        else if (ev.kind === 'sample_complete') {
            for (const a of payload.sample_artifacts ?? [])
                s.stageArtifact(artifactToPart(a));
        }
    }
    return s.finish();
}
export class Stream {
    runId;
    events_ = [];
    seq = 0;
    started = false;
    finished = false;
    constructor(runId) {
        this.runId = runId ?? randomUUID().replace(/-/g, '');
    }
    push(type, part, data) {
        const event = { type, seq: this.seq, run_id: this.runId, ts: Date.now(), nonce: randomUUID().replace(/-/g, ''), data: data ?? {} };
        if (part !== undefined)
            event.part = part;
        this.events_.push(event);
        this.seq += 1;
        return this;
    }
    emit(type, part, data) {
        if (!this.started) {
            this.push(EVENT.RUN_STARTED);
            this.started = true;
        }
        return this.push(type, part, data);
    }
    // content
    reasoning(text) {
        return this.emit(EVENT.PART, { type: 'reasoning', text });
    }
    text(text, role) {
        if (role)
            return this.emit(EVENT.TEXT_MESSAGE_CHUNK, undefined, { text, role });
        return this.emit(EVENT.PART, { type: 'text', text });
    }
    step(label) {
        return this.emit(EVENT.STEP_STARTED, undefined, { name: label });
    }
    code(source, opts = {}) {
        const part = { type: 'code', source };
        if (opts.language)
            part.language = opts.language;
        if (opts.filename)
            part.filename = opts.filename;
        return this.emit(EVENT.PART, part);
    }
    table(opts) {
        return this.emit(EVENT.ARTIFACT_STAGED, tablePart(opts.columns, opts.rows, opts));
    }
    file(opts) {
        const ref = { id: opts.id, name: opts.name, mime: opts.mime, url: opts.url };
        if (opts.size_bytes !== undefined)
            ref.size_bytes = opts.size_bytes;
        return this.emit(EVENT.PART, { type: 'file', file: ref });
    }
    fileSet(opts) {
        const part = { type: 'file_set', files: opts.files };
        if (opts.title)
            part.title = opts.title;
        return this.emit(EVENT.ARTIFACT_STAGED, part);
    }
    stageArtifact(part) {
        return this.emit(EVENT.ARTIFACT_STAGED, part);
    }
    // trust
    requireApproval(opts) {
        const part = { type: 'approval', approval_id: opts.approvalId ?? randomUUID().replace(/-/g, ''), action: opts.action, requires_approval: true };
        if (opts.summary)
            part.summary = opts.summary;
        if (opts.diff !== undefined)
            part.diff = opts.diff;
        if (opts.target !== undefined)
            part.target = opts.target;
        return this.emit(EVENT.APPROVAL_REQUIRED, part);
    }
    clarify(opts) {
        const part = {
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
    moneyHold(opts = {}) {
        const part = { type: 'money', kind: 'hold' };
        if (opts.typical !== undefined)
            part.typical_credits = opts.typical;
        if (opts.ceiling !== undefined)
            part.ceiling_credits = opts.ceiling;
        if (opts.hold !== undefined)
            part.hold_credits = opts.hold;
        return this.emit(EVENT.BUDGET_HOLD, part);
    }
    moneySettle(opts) {
        const part = { type: 'money', kind: 'settle', captured_credits: opts.captured };
        if (opts.hold !== undefined)
            part.hold_credits = opts.hold;
        if (opts.stats !== undefined)
            part.stats = opts.stats;
        return this.emit(EVENT.BUDGET_SETTLE, part);
    }
    // lifecycle
    finish() {
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
    error(message) {
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
    events() {
        if (!this.finished)
            this.finish();
        return [...this.events_];
    }
    *sse() {
        for (const event of this.events()) {
            yield `id: ${event.seq}\nevent: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`;
        }
    }
    static fromBatch(result, runId) {
        const stream = new Stream(runId);
        let parts;
        const r = result;
        if (r && typeof r === 'object' && Array.isArray(r.parts))
            parts = r.parts;
        else if (r && typeof r === 'object' && r.artifact)
            parts = [artifactToPart(r.artifact)];
        else if (r && typeof r === 'object' && Array.isArray(r.artifacts))
            parts = r.artifacts.map(artifactToPart);
        else if (r && typeof r === 'object')
            parts = [{ type: 'generic', data: { ...r } }];
        else
            parts = [{ type: 'generic', data: { value: result } }];
        for (const part of parts)
            stream.stageArtifact(part);
        return stream.finish();
    }
}
