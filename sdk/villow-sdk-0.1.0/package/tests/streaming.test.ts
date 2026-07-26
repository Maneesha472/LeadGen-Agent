import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { Stream, eventsToStream, type StreamEvent } from '../src/streaming.js';

const here = dirname(fileURLToPath(import.meta.url));
// Cross-language parity: the Python SDK generates sdk/streaming-golden.json; this builds the same
// logical stream in Node and asserts the normalized output is identical (proves wire-format parity).
const fixture = JSON.parse(readFileSync(resolve(here, '../../streaming-golden.json'), 'utf8'));

function golden(): Stream {
  const s = new Stream('golden');
  s.reasoning('I see 47 PDFs.');
  s.text('Reconcile these two sheets', 'user');
  s.text("Here's your **March books-ready package**.");
  s.step('Reconciling statement 3 of 7');
  s.moneyHold({ typical: 120, ceiling: 180 });
  s.table({
    columns: ['merchant', 'amount'],
    rows: [['ACME', '14302.11']],
    title: 'March ledger',
    reconciliation: { label: 'Totals', expected: '14302.11', actual: '14302.11', ok: true },
    exceptions: [{ id: 'e1', message: '2 receipts unmatched' }],
  });
  s.fileSet({ files: [{ id: 'f1', name: 'ledger.xlsx', mime: 'application/vnd.ms-excel', url: '/m/f1' }] });
  s.requireApproval({ action: 'Write March-ledger.xlsx to your Drive', summary: 'Nothing writes until you approve.', approvalId: 'ap-1' });
  s.clarify({ question: 'Fold duplicates in?', options: [{ id: 'fold', label: 'Fold in' }], clarificationId: 'cl-1' });
  s.moneySettle({ captured: 118, hold: 180, stats: { 'transactions categorized': 312 } });
  return s;
}

function normalize(events: StreamEvent[]): Record<string, unknown>[] {
  return events.map((e) => {
    const clone: Record<string, unknown> = { ...e };
    delete clone.ts;
    delete clone.nonce;
    return clone;
  });
}

test('node SDK streaming emits the shared golden parity fixture', () => {
  assert.deepEqual(normalize(golden().events()), fixture);
});

test('clarify always carries a decide_for_me (rule #4)', () => {
  const events = new Stream().clarify({ question: 'Which format?' }).events();
  const clar = events.find((e) => e.type === 'CLARIFICATION_REQUIRED');
  assert.ok(clar?.part);
  assert.equal((clar.part as { decide_for_me: { label: string } }).decide_for_me.label, 'Decide for me');
});

test('fromBatch turns a single artifact into a stream', () => {
  const events = Stream.fromBatch({ artifact: { artifact_type: 'table_data', type_payload: { columns: ['a'], rows: [[1]] } } }).events();
  assert.equal(events[0].type, 'RUN_STARTED');
  assert.equal(events[events.length - 1].type, 'RUN_FINISHED');
  const staged = events.find((e) => e.type === 'ARTIFACT_STAGED');
  assert.equal((staged?.part as { type: string }).type, 'table_data');
});

test('sse framing carries id + event + data lines', () => {
  const chunks = [...new Stream('t').text('hi').sse()];
  assert.ok(chunks[0].startsWith('id: 0\nevent: RUN_STARTED\n'));
  assert.ok(chunks.every((c) => c.endsWith('\n\n')));
});

test('eventsToStream migrates a Node agent (text-writer) emission to the streaming contract', () => {
  // mirrors the text-writer agent: a message_draft staged artifact
  const emissions = [
    { kind: 'status', payload: { progress: { event_type: 'milestone', milestone: { id: 'm1', state: 'completed', label: 'drafting' } } } },
    { kind: 'artifact_staged', payload: { artifact: { artifact_type: 'message_draft', title: 'Draft', type_payload: { subject: 'Draft', body: 'Hello there.' } } } },
  ];
  const events = eventsToStream(emissions).events();
  assert.equal(events[0].type, 'RUN_STARTED');
  assert.equal(events[events.length - 1].type, 'RUN_FINISHED');
  assert.ok(events.some((e) => e.type === 'STEP_STARTED'));
  const staged = events.find((e) => e.type === 'ARTIFACT_STAGED');
  assert.equal((staged?.part as { type: string }).type, 'message_draft');
});

test('eventsToStream converts a structured_fields dict into a list', () => {
  const events = eventsToStream([
    { kind: 'artifact_staged', payload: { artifact: { artifact_type: 'structured_fields', type_payload: { fields: { issuer: 'Metro', row_count: 1 } } } } },
  ]).events();
  const staged = events.find((e) => e.type === 'ARTIFACT_STAGED');
  const fields = (staged?.part as { type: string; fields: unknown[] });
  assert.equal(fields.type, 'structured_fields');
  assert.ok(Array.isArray(fields.fields));
  assert.deepEqual(fields.fields[0], { label: 'issuer', value: 'Metro' });
});
