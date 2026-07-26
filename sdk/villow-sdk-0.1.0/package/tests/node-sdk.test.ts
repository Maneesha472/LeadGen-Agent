import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import {
  Agent,
  Artifact,
  Composition,
  ProgressEvent,
  Question,
  Context,
  MockPlatformHarness,
  TIMESTAMP_HEADER,
  main as cliMain,
  preview,
  signRequest,
  taskTemplate,
  validateManifest,
  verifyRequestSignature,
} from '../src/index.ts';
import { HelloWorldAgent } from '../examples/hello-world-agent.ts';

const __dirname = dirname(fileURLToPath(import.meta.url));
const sdkRoot = resolve(__dirname, '..');

function stableJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.entries(value as Record<string, unknown>)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, item]) => `${JSON.stringify(key)}:${stableJson(item)}`)
      .join(',')}}`;
  }
  return JSON.stringify(value);
}

async function signedAgentInject(
  app: { inject: (input: { method: 'POST'; url: string; payload: Buffer; headers: Record<string, string> }) => Promise<{ statusCode: number; json: () => Record<string, unknown> }> },
  path: string,
  payload: Record<string, unknown>,
  options: { idempotencyKey: string; secret?: string },
) {
  const body = Buffer.from(stableJson(payload));
  const headers = signRequest({
    method: 'POST',
    path,
    body,
    keyId: 'key_1',
    secret: options.secret ?? 'local-secret',
    publisherId: 'publisher_1',
    agentId: 'agent_1',
    timestamp: Math.floor(Date.now() / 1000),
    nonce: `nonce_${options.idempotencyKey}`,
    idempotencyKey: options.idempotencyKey,
  });
  headers['content-type'] = 'application/json';
  return app.inject({ method: 'POST', url: path, payload: body, headers });
}

test('node sdk package metadata and public exports exist', () => {
  const pkg = JSON.parse(readFileSync(resolve(sdkRoot, 'package.json'), 'utf8'));
  const readme = readFileSync(resolve(sdkRoot, 'README.md'), 'utf8');
  const tsconfig = readFileSync(resolve(sdkRoot, 'tsconfig.json'), 'utf8');

  assert.equal(pkg.name, '@villow/sdk');
  assert.equal(pkg.scripts.test, 'tsx --test tests/*.test.ts');
  assert.equal(pkg.scripts.build, 'tsc -p tsconfig.json');
  assert.equal(pkg.bin['villow-node'], 'dist/cli.js');
  for (const dependency of ['fastify', 'undici', 'zod', 'yaml']) {
    assert.ok(pkg.dependencies[dependency], `${dependency} dependency missing`);
  }
  assert.match(readme, /Local-first SDK/);
  assert.match(tsconfig, /experimentalDecorators/);

  assert.equal(typeof Agent, 'function');
  assert.equal(typeof Artifact, 'function');
  assert.equal(typeof Composition, 'function');
  assert.equal(typeof ProgressEvent, 'function');
  assert.equal(typeof Question, 'function');
  assert.equal(typeof preview, 'function');
  assert.equal(typeof taskTemplate, 'function');
});

test('node sdk signing matches platform canonical contract', () => {
  const body = Buffer.from('{"task_id":"task_123","progress":{"current":1,"total":2}}');
  const headers = signRequest({
    method: 'POST',
    path: '/v1/callbacks/status',
    body,
    keyId: 'key_local_1',
    secret: 'local-secret',
    publisherId: 'publisher_1',
    agentId: 'agent_1',
    timestamp: 1_800_000_000,
    nonce: 'nonce_1',
    idempotencyKey: 'idem_1',
  });

  const principal = verifyRequestSignature({
    method: 'POST',
    path: '/v1/callbacks/status',
    body,
    headers,
    secret: 'local-secret',
    now: 1_800_000_010,
  });

  assert.equal(principal.publisherId, 'publisher_1');
  assert.equal(principal.agentId, 'agent_1');
  assert.equal(principal.idempotencyKey, 'idem_1');
  assert.throws(() =>
    verifyRequestSignature({
      method: 'POST',
      path: '/v1/callbacks/status',
      body: Buffer.from('{"task_id":"tampered"}'),
      headers,
      secret: 'local-secret',
      now: 1_800_000_010,
    }),
  );
});

test('question builders include decideForMe and validation', () => {
  const question = Question.singleSelect({
    id: 'aspectRatio',
    label: 'Aspect ratio',
    options: ['original', 'square', '16:9'],
    default: 'original',
    decideForMe: { strategy: 'preserveOriginal' },
  });
  assert.equal(question.id, 'aspectRatio');
  assert.equal(question.type, 'single_select');
  assert.equal(question.default_value, 'original');
  assert.deepEqual(question.validation.options, ['original', 'square', '16:9']);
  assert.deepEqual(question.decide_for_me, { strategy: 'preserveOriginal' });

  const number = Question.number({
    id: 'intensity',
    label: 'Style intensity',
    min: 0,
    max: 100,
    default: 70,
    decideForMe: { value: 70 },
  });
  assert.equal(number.type, 'number');
  assert.deepEqual(number.validation, { min: 0, max: 100 });

  assert.throws(() => Question.boolean({ id: 'facePreservation', label: 'Preserve faces' }));
});

test('composition builders create rich primitives and simple fallback payloads', () => {
  const composition = Composition.input(
    [
      Composition.visualPicker('style', { label: 'Style', options: [{ id: 'cinematic', label: 'Cinematic' }] }),
      Composition.sliderWithLivePreview('intensity', { label: 'Intensity', min: 0, max: 100, default: 70 }),
      Composition.drivePicker('source', { label: 'Source', mode: 'folder' }),
      Composition.toggleWithExplanation('facePreservation', { label: 'Preserve faces', default: true }),
    ],
    { taskTemplate: 'edit_photo_batch', compositionId: 'photo_batch_style_editing.v1' },
  );

  assert.equal(composition.mode, 'input_collection');
  assert.equal(composition.composition_id, 'photo_batch_style_editing.v1');
  assert.equal(composition.primitives[0].primitive, 'visual_picker');
  assert.deepEqual(composition.primitives[1].validation, { min: 0, max: 100 });
  assert.deepEqual(composition.fallback_slots.map((slot) => slot.id), ['style', 'intensity', 'source', 'facePreservation']);
  assert.equal(composition.fallback_slots[2].type, 'drive_folder');

  assert.throws(() => Composition.input(Array.from({ length: 11 }, (_, index) => Composition.visualPicker(`p${index}`))));
});

test('artifact builders emit allowed typed payloads', () => {
  const fileSet = Artifact.fileSet({
    files: [{ file_id: 'drive_file_1', name: 'edited.jpg' }],
    previewUrls: ['https://cdn.example/edited.jpg'],
    destinationProposal: { drive_folder_id: 'folder_1' },
  });
  assert.equal(fileSet.artifact_type, 'file_set');
  assert.equal(fileSet.type_payload.files[0].file_id, 'drive_file_1');
  assert.deepEqual(fileSet.destination_proposal, { drive_folder_id: 'folder_1' });

  const table = Artifact.tableData({
    columns: ['date', 'amount'],
    rows: [['2026-05-11', '99']],
    title: 'Expenses',
  });
  assert.equal(table.artifact_type, 'table_data');
  assert.deepEqual(table.type_payload.columns, ['date', 'amount']);
  assert.equal(table.preview_data.row_count, 1);

  const draft = Artifact.messageDraft({ subject: 'Hello', body: 'Body', to: ['user@example.com'] });
  assert.equal(draft.artifact_type, 'message_draft');
});

test('progress events have structured execution and unit-charge payloads', () => {
  const item = ProgressEvent.itemCompleted({
    current: 1,
    total: 3,
    itemId: 'photo_1',
    thumbnailUrl: 'https://cdn.example/photo_1.jpg',
    focusItemId: 'photo_2',
  });
  assert.equal(item.event_type, 'item_completed');
  assert.equal(item.progress.current, 1);
  assert.equal(item.item.state, 'completed');
  assert.equal(item.focus_item_id, 'photo_2');

  const milestone = ProgressEvent.milestone({ id: 'sample_ready', state: 'completed', label: 'Sample ready' });
  assert.equal(milestone.event_type, 'milestone');
  assert.equal(milestone.milestone.id, 'sample_ready');

  const charge = ProgressEvent.unitCharge({ amount: 42, currency: 'INR', unitCount: 7 });
  assert.equal(charge.event_type, 'cost_telemetry');
  assert.equal(charge.cost_telemetry.reported_cost_inr_paise, 42);
  assert.equal(charge.cost_telemetry.unit_count, 7);
});

test('agent registers decorated handlers and context response helpers', () => {
  class DemoAgent extends Agent {
    @taskTemplate('demo_task')
    prepare(inputs: Record<string, unknown>, ctx: Context) {
      return ctx.readyToAuthorize({ normalizedInputs: inputs, priceUnits: { unit: 'page', count: 2 } });
    }

    @preview('demo_task')
    previewDemo(inputs: Record<string, unknown>) {
      return { type: 'text', value: inputs.title };
    }

    @taskTemplate('demo_task')
    run() {
      return { accepted: true };
    }
  }

  const agent = new DemoAgent({ publisherId: 'publisher_1', agentId: 'agent_1', keyId: 'key_1', secret: 'local-secret' });
  assert.ok(agent.taskTemplates.has('demo_task'));
  assert.equal(agent.prepareHandlers.get('demo_task')?.name, 'bound prepare');
  assert.equal(agent.runHandlers.get('demo_task')?.name, 'bound run');
  assert.equal(agent.previewHandlers.get('demo_task')?.name, 'bound previewDemo');

  const ctx = new Context({
    agent,
    taskId: 'task_1',
    taskTemplate: 'demo_task',
    inputs: { title: 'Demo' },
    answers: { style: 'clean' },
    delegatedDecisions: { style: false, intensity: true },
  });
  assert.equal(ctx.hasAnswer('style'), true);
  assert.equal(ctx.answer('style'), 'clean');
  assert.equal(ctx.wasDelegated('intensity'), true);

  const ready = ctx.readyToAuthorize({ normalizedInputs: { title: 'Demo' }, priceUnits: { unit: 'page', count: 2 } });
  assert.equal(ready.state, 'ready_to_authorize');
  assert.deepEqual(ready.price_units, { unit: 'page', count: 2 });

  const clarification = ctx.requestClarification([
    Question.singleSelect({
      id: 'style',
      label: 'Style',
      options: ['clean', 'bold'],
      default: 'clean',
      decideForMe: { value: 'clean' },
    }),
  ]);
  assert.equal(clarification.state, 'clarification_required');
  assert.equal(clarification.phase, 'pre_execution');
  assert.deepEqual(clarification.questions[0].decide_for_me, { value: 'clean' });
});

test('context callbacks and tools are signed and use opaque grants', async () => {
  const captured: Array<{ path: string; principal: unknown; body: Record<string, unknown> }> = [];
  const agent = new Agent({
    publisherId: 'publisher_1',
    agentId: 'agent_1',
    keyId: 'key_1',
    secret: 'local-secret',
    platformBaseUrl: 'https://platform.local',
    platformRequest: async ({ url, method, headers, body }) => {
      const path = new URL(url).pathname;
      const principal = verifyRequestSignature({
        method,
        path,
        body,
        headers,
        secret: 'local-secret',
        now: Number(headers[TIMESTAMP_HEADER]) + 1,
      });
      const parsed = JSON.parse(body.toString('utf8')) as Record<string, unknown>;
      captured.push({ path, principal, body: parsed });
      if (path === '/v1/tools/drive.list_files') {
        return {
          statusCode: 200,
          body: {
            tool_name: 'drive.list_files',
            task_id: 'task_1',
            status: 'success',
            result: { files: [{ id: 'file_1', name: 'a.jpg' }] },
            artifact_id: null,
          },
        };
      }
      return { statusCode: 200, body: { accepted: true } };
    },
  });
  const ctx = new Context({
    agent,
    taskId: 'task_1',
    taskTemplate: 'demo_task',
    inputs: {},
    toolAccessGrants: [{ provider: 'google', scope: 'drive.read', grant_id: 'grant_1', access_token: 'raw-secret' }],
    callbackUrls: { status: 'https://platform.local/v1/callbacks/status' },
  });

  await ctx.reportProgress(ProgressEvent.itemCompleted({ current: 1, total: 2, itemId: 'file_1' }));
  const result = await ctx.tools.drive.listFiles({ folderId: 'folder_1', filters: { mimeType: 'image/*' } });

  assert.equal(result.files[0].id, 'file_1');
  assert.equal(captured[0].path, '/v1/callbacks/status');
  assert.equal(captured[1].path, '/v1/tools/drive.list_files');
  assert.equal(captured[1].body.task_id, 'task_1');
  assert.equal(captured[1].body.tool_access_grant_id, 'grant_1');
  assert.equal(JSON.stringify(captured[1].body).includes('raw-secret'), false);
});

test('fastify app exposes signed idempotent agent contract endpoints', async () => {
  class ServerAgent extends Agent {
    @taskTemplate('demo_task')
    prepare(inputs: Record<string, unknown>, ctx: Context) {
      const composition = Composition.input(
        [Composition.dropdownWithDescriptions('style', { options: [{ id: 'clean', label: 'Clean' }] })],
        { taskTemplate: 'demo_task', compositionId: 'demo_task.v1' },
      );
      if (!ctx.hasAnswer('style')) {
        return ctx.requestClarification(
          [
            Question.singleSelect({
              id: 'style',
              label: 'Style',
              options: ['clean', 'bold'],
              default: 'clean',
              decideForMe: { value: 'clean' },
            }),
          ],
          { compositionResponse: composition },
        );
      }
      return ctx.readyToAuthorize({
        normalizedInputs: { ...inputs, style: ctx.answer('style') },
        compositionResponse: composition,
      });
    }

    @preview('demo_task')
    previewDemo(inputs: Record<string, unknown>) {
      return { type: 'text', value: `Preview: ${inputs.title}` };
    }

    @taskTemplate('demo_task')
    async run(inputs: Record<string, unknown>, ctx: Context) {
      await ctx.reportProgress(ProgressEvent.itemCompleted({ current: 1, total: 1, itemId: 'row_1' }));
      await ctx.stageArtifact(Artifact.tableData({ columns: ['title'], rows: [[inputs.title]], title: 'Demo output' }));
      return { task_id: ctx.taskId, accepted: true, estimated_completion_seconds: 1 };
    }
  }

  const agent = new ServerAgent({ publisherId: 'publisher_1', agentId: 'agent_1', keyId: 'key_1', secret: 'local-secret' });
  const app = agent.fastifyApp();

  const unsigned = await app.inject({ method: 'POST', url: '/discover', payload: Buffer.from('{}'), headers: { 'content-type': 'application/json' } });
  assert.equal(unsigned.statusCode, 401);

  const discover = await signedAgentInject(app, '/discover', {}, { idempotencyKey: 'idem_discover' });
  assert.equal(discover.statusCode, 200);
  assert.equal((discover.json().task_templates as Array<Record<string, unknown>>)[0].slug, 'demo_task');

  const preparePayload = { task_id: 'task_1', task_template: 'demo_task', initial_inputs: { title: 'Demo' } };
  const prepare = await signedAgentInject(app, '/prepare', preparePayload, { idempotencyKey: 'idem_prepare' });
  assert.equal(prepare.statusCode, 200);
  const prepareBody = prepare.json();
  assert.equal(prepareBody.state, 'clarification_required');
  assert.equal(((prepareBody.composition_response as Record<string, unknown>).fallback_slots as Array<Record<string, unknown>>)[0].id, 'style');

  const replay = await signedAgentInject(app, '/prepare', preparePayload, { idempotencyKey: 'idem_prepare' });
  assert.deepEqual(replay.json(), prepareBody);
  const conflict = await signedAgentInject(
    app,
    '/prepare',
    { task_id: 'task_1', task_template: 'demo_task', initial_inputs: { title: 'Changed' } },
    { idempotencyKey: 'idem_prepare' },
  );
  assert.equal(conflict.statusCode, 409);

  const clarification = await signedAgentInject(
    app,
    '/clarification_response',
    {
      task_id: 'task_1',
      clarification_id: prepareBody.clarification_id,
      phase: 'pre_execution',
      answers: { style: 'clean' },
      delegated_decisions: { style: false },
    },
    { idempotencyKey: 'idem_clarification' },
  );
  assert.equal(clarification.statusCode, 200);
  assert.equal(clarification.json().accepted, true);

  const preparedAgain = await signedAgentInject(app, '/prepare', preparePayload, { idempotencyKey: 'idem_prepare_after_answer' });
  assert.equal(preparedAgain.json().state, 'ready_to_authorize');
  assert.equal((preparedAgain.json().normalized_inputs as Record<string, unknown>).style, 'clean');

  const previewResponse = await signedAgentInject(
    app,
    '/preview',
    { task_id: 'task_1', task_template: 'demo_task', current_inputs: { title: 'Demo' } },
    { idempotencyKey: 'idem_preview' },
  );
  assert.equal((previewResponse.json().preview as Record<string, unknown>).value, 'Preview: Demo');

  const execute = await signedAgentInject(
    app,
    '/execute',
    { task_id: 'task_1', task_template: 'demo_task', inputs: { title: 'Demo' }, tool_access_grants: [], callback_urls: {}, sample_mode: false },
    { idempotencyKey: 'idem_execute' },
  );
  assert.equal(execute.statusCode, 200);
  assert.equal(execute.json().accepted, true);

  const status = await signedAgentInject(app, '/status', { task_id: 'task_1' }, { idempotencyKey: 'idem_status' });
  assert.equal(status.json().state, 'artifact_review');

  const result = await signedAgentInject(app, '/result', { task_id: 'task_1' }, { idempotencyKey: 'idem_result' });
  assert.equal(((result.json().artifacts as Array<Record<string, unknown>>)[0]).artifact_type, 'table_data');

  const cancel = await signedAgentInject(app, '/cancel', { task_id: 'task_1' }, { idempotencyKey: 'idem_cancel' });
  assert.equal(cancel.json().cancelling, true);

  await app.close();
});

test('signed endpoint verifies Python-style float JSON without re-canonicalizing', async () => {
  const agent = new HelloWorldAgent();
  const app = agent.fastifyApp();
  await app.ready();
  // Python platform serializes whole floats as 40.0; must not 401 when bytes are preserved.
  const body = Buffer.from(
    '{"budget_cap":{"amount":40.0,"currency":"INR"},"inputs":{"title":"Demo"},"sample_mode":false,"task_id":"task_float","task_template":"demo_task","tool_access_grants":[],"callback_urls":{}}',
  );
  const headers = signRequest({
    method: 'POST',
    path: '/execute',
    body,
    keyId: 'key_1',
    secret: 'local-secret',
    publisherId: 'publisher_1',
    agentId: 'agent_1',
    idempotencyKey: 'float-body-test',
  });
  headers['content-type'] = 'application/json';
  const response = await app.inject({ method: 'POST', url: '/execute', payload: body, headers });
  assert.notEqual(response.statusCode, 401, 'float JSON must not break signature verification');
  await app.close();
});

test('manifest cli examples and mock platform harness run locally', async () => {
  const manifestPath = resolve(sdkRoot, 'examples/agent.yaml');
  const validation = validateManifest(manifestPath);
  assert.equal(validation.valid, true, validation.errors.join(', '));
  assert.equal(await cliMain(['validate', manifestPath]), 0);

  const examplePath = resolve(sdkRoot, 'examples/hello-world-agent.ts');
  const nonEmptyLines = readFileSync(examplePath, 'utf8')
    .split('\n')
    .filter((line) => line.trim() && !line.trim().startsWith('//'));
  assert.ok(nonEmptyLines.length <= 50, `hello-world example has ${nonEmptyLines.length} non-empty lines`);

  const harness = new MockPlatformHarness(new HelloWorldAgent(), { renderMode: 'simple' });
  const result = await harness.runTask('hello_world', { name: 'Worklane' }, { answers: { tone: 'friendly' } });
  assert.equal(result.state, 'completed');
  assert.equal((result.artifacts[0] as Record<string, unknown>).artifact_type, 'generic');
  assert.equal((result.composition_response as Record<string, unknown>).mode, 'input_collection');
  assert.equal((result.simple_fallback_slots as Array<Record<string, unknown>>)[0].id, 'tone');
  assert.ok(readFileSync(resolve(sdkRoot, 'examples/clarification-agent.ts'), 'utf8').includes('ClarificationAgent'));
  assert.ok(readFileSync(resolve(sdkRoot, 'examples/composition-preview-agent.ts'), 'utf8').includes('CompositionPreviewAgent'));
  await harness.close();
});

function tmpManifest(templateBody: string): string {
  const content = `publisher_id: pub_123
agent_id: agent_123
name: Ceiling Agent
version: v1
task_templates:
  - slug: extract_statements
    artifact_type: table_data
${templateBody}`;
  const path = join(tmpdir(), `villow-manifest-${randomUUID()}.yaml`);
  writeFileSync(path, content, 'utf8');
  return path;
}

test('manifest validates optional T·M price ceilings (N1.5, parity with python)', () => {
  // Valid T·M passes with no warnings.
  const ok = validateManifest(tmpManifest('    typical_charge: 120\n    unit_ceiling: 240\n'));
  assert.equal(ok.valid, true, ok.errors.join(', '));
  assert.deepEqual(ok.warnings, []);

  // Missing T·M stays valid (additive / back-compatible).
  const legacy = validateManifest(tmpManifest('    input_composition: []\n'));
  assert.equal(legacy.valid, true, legacy.errors.join(', '));
  assert.deepEqual(legacy.warnings, []);

  // T above M is rejected.
  const tAboveM = validateManifest(tmpManifest('    typical_charge: 300\n    unit_ceiling: 240\n'));
  assert.equal(tAboveM.valid, false);
  assert.ok(tAboveM.errors.some((e) => e.includes('typical_charge')), tAboveM.errors.join(', '));

  // Non-positive ceiling is rejected.
  const zeroM = validateManifest(tmpManifest('    unit_ceiling: 0\n'));
  assert.equal(zeroM.valid, false);
});

test('agent_state round-trips through a signed /execute (N1.5, parity with python)', async () => {
  class StateAgent extends Agent {
    @taskTemplate('state_demo')
    async run(_inputs: Record<string, unknown>, ctx: Context): Promise<Record<string, unknown>> {
      const prior = { ...ctx.agentState };
      ctx.setAgentState({ count: Number((prior.count as number) ?? 0) + 1 });
      await ctx.stageArtifact(Artifact.generic({ prior_count: (prior.count as number) ?? 0 }));
      return { echo_prior: prior };
    }
  }

  const agent = new StateAgent({ publisherId: 'publisher_1', agentId: 'agent_1', keyId: 'key_1', secret: 'local-secret' });
  const app = agent.fastifyApp();

  const execute = await signedAgentInject(
    app,
    '/execute',
    { task_id: 'task_state', task_template: 'state_demo', inputs: {}, agent_state: { count: 5 } },
    { idempotencyKey: 'idem_execute_state' },
  );
  assert.equal(execute.statusCode, 200);
  const executeBody = execute.json();
  assert.deepEqual(executeBody.echo_prior, { count: 5 });
  assert.deepEqual(executeBody.agent_state, { count: 6 });

  // /result surfaces the same continuation blob.
  const result = await signedAgentInject(app, '/result', { task_id: 'task_state' }, { idempotencyKey: 'idem_result_state' });
  assert.deepEqual(result.json().agent_state, { count: 6 });

  // Back-compat: an execute with no replayed blob still works.
  const fresh = await signedAgentInject(
    app,
    '/execute',
    { task_id: 'task_state_2', task_template: 'state_demo', inputs: {} },
    { idempotencyKey: 'idem_execute_fresh' },
  );
  assert.deepEqual(fresh.json().echo_prior, {});
  assert.deepEqual(fresh.json().agent_state, { count: 1 });

  await app.close();
});
