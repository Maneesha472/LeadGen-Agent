#!/usr/bin/env node
import { validateContractMessage } from './contractSchemas.js';
import { validateManifest } from './manifest.js';
import { signRequest, verifyRequestSignature } from './signing.js';

export async function main(argv = process.argv.slice(2)): Promise<number> {
  if ((process.argv[1] ?? '').endsWith('villow-contract-test') && argv[0] !== 'contract-test') {
    argv = ['contract-test', ...argv];
  }
  const [command, firstArg, ...rest] = argv;
  if (command === 'contract-test' && firstArg) {
    return await runContractTest(firstArg, rest);
  }
  const manifestPath = firstArg;
  if (command !== 'validate' || !manifestPath) {
    console.error('usage: villow-node validate <agent.yaml> | contract-test <endpoint> --publisher-id <id> --agent-id <id> --signing-key-id <id> --secret <secret> [--offline]');
    return 1;
  }
  const result = validateManifest(manifestPath);
  for (const warning of result.warnings) console.log(`warning: ${warning}`);
  if (result.valid) {
    console.log(`valid: ${manifestPath}`);
    return 0;
  }
  for (const error of result.errors) console.error(`error: ${error}`);
  return 1;
}

async function runContractTest(endpoint: string, args: string[]): Promise<number> {
  const options = parseOptions(args);
  const required = ['publisher-id', 'agent-id', 'signing-key-id', 'secret'];
  const missing = required.filter((key) => !options[key]);
  if (missing.length > 0) {
    console.error(`missing required options: ${missing.join(', ')}`);
    return 1;
  }
  const body = Buffer.from(JSON.stringify({ task_id: 'contract_test' }));
  const headers = signRequest({
    method: 'POST',
    path: '/discover',
    body,
    keyId: options['signing-key-id'],
    secret: options.secret,
    publisherId: options['publisher-id'],
    agentId: options['agent-id'],
    idempotencyKey: 'contract-test-signature',
  });
  const checks = [];
  try {
    verifyRequestSignature({ method: 'POST', path: '/discover', body, headers, secret: options.secret });
    checks.push({ name: 'signature_verification', passed: true, detail: 'signed request verifies locally' });
  } catch (error) {
    checks.push({ name: 'signature_verification', passed: false, detail: error instanceof Error ? error.message : 'signature failed' });
  }
  const schema = validateContractMessage('response.discover', { publisher_id: 'publisher', agent_id: 'agent' });
  checks.push({ name: 'schema_package', passed: schema.valid, detail: schema.valid ? 'schemas are available' : JSON.stringify(schema.errors) });
  if (options.offline !== 'true') {
    checks.push(await signedDiscoverCheck(endpoint, options));
    checks.push(await idempotencyCheck(endpoint, options));
    checks.push(await staleSignatureCheck(endpoint, options));
    checks.push(await malformedPrepareCheck(endpoint, options));
  }
  const report = {
    contract_test: 'villow.publisher.v1',
    endpoint,
    offline: options.offline === 'true',
    passed: checks.every((check) => check.passed),
    checks,
  };
  console.log(JSON.stringify(report, null, 2));
  return report.passed ? 0 : 1;
}

async function signedDiscoverCheck(endpoint: string, options: Record<string, string>): Promise<{ name: string; passed: boolean; detail: string; remediation?: string }> {
  const response = await postContract(endpoint, '/discover', {}, options, 'contract-test-discover');
  if (response.status >= 500) return { name: 'signed_discover', passed: false, detail: `HTTP ${response.status}`, remediation: 'Keep /discover lightweight and non-blocking.' };
  if (response.status >= 400) return { name: 'signed_discover', passed: false, detail: `HTTP ${response.status}`, remediation: 'Verify signing credentials and endpoint URL.' };
  const payload = await jsonObject(response);
  const validation = validateContractMessage('response.discover', payload);
  return validation.valid
    ? { name: 'signed_discover', passed: true, detail: 'signed /discover returned a schema-valid response' }
    : { name: 'signed_discover', passed: false, detail: JSON.stringify(validation.errors), remediation: 'Return the documented discover response shape.' };
}

async function idempotencyCheck(endpoint: string, options: Record<string, string>): Promise<{ name: string; passed: boolean; detail: string; remediation?: string }> {
  const first = await postContract(endpoint, '/discover', {}, options, 'contract-test-idempotency');
  const second = await postContract(endpoint, '/discover', {}, options, 'contract-test-idempotency');
  return first.status === second.status
    ? { name: 'idempotency', passed: true, detail: 'duplicate signed request returned a stable status' }
    : { name: 'idempotency', passed: false, detail: 'duplicate request returned a different status', remediation: 'Cache by idempotency key and request hash.' };
}

async function staleSignatureCheck(endpoint: string, options: Record<string, string>): Promise<{ name: string; passed: boolean; detail: string; remediation?: string }> {
  const response = await postContract(endpoint, '/discover', {}, options, 'contract-test-stale', 1);
  return [400, 401, 403].includes(response.status)
    ? { name: 'timestamp_tolerance', passed: true, detail: 'stale signature was rejected' }
    : { name: 'timestamp_tolerance', passed: false, detail: `HTTP ${response.status}`, remediation: 'Reject stale Villow signatures.' };
}

async function malformedPrepareCheck(endpoint: string, options: Record<string, string>): Promise<{ name: string; passed: boolean; detail: string; remediation?: string }> {
  const response = await postContract(endpoint, '/prepare', { task_template: 'missing_task_id' }, options, 'contract-test-malformed');
  return response.status >= 400
    ? { name: 'malformed_request_handling', passed: true, detail: `malformed prepare rejected with HTTP ${response.status}` }
    : { name: 'malformed_request_handling', passed: false, detail: 'malformed prepare was accepted', remediation: 'Reject missing required fields.' };
}

async function postContract(
  endpoint: string,
  path: string,
  payload: Record<string, unknown>,
  options: Record<string, string>,
  idempotencyKey: string,
  timestamp?: number,
): Promise<Response> {
  const url = contractUrl(endpoint, path);
  const body = Buffer.from(JSON.stringify(payload));
  const headers = signRequest({
    method: 'POST',
    path: new URL(url).pathname,
    body,
    keyId: options['signing-key-id'],
    secret: options.secret,
    publisherId: options['publisher-id'],
    agentId: options['agent-id'],
    idempotencyKey,
    timestamp,
  });
  return fetch(url, { method: 'POST', body, headers: { ...headers, 'content-type': 'application/json' } });
}

function contractUrl(endpoint: string, path: string): string {
  const base = endpoint.endsWith('/') ? endpoint : `${endpoint}/`;
  return new URL(path.replace(/^\//, ''), base).toString();
}

async function jsonObject(response: Response): Promise<Record<string, unknown>> {
  try {
    const payload = await response.json();
    return payload && typeof payload === 'object' && !Array.isArray(payload) ? payload as Record<string, unknown> : {};
  } catch {
    return {};
  }
}

function parseOptions(args: string[]): Record<string, string> {
  const options: Record<string, string> = {};
  for (let index = 0; index < args.length; index += 1) {
    const item = args[index];
    if (!item.startsWith('--')) continue;
    const key = item.slice(2);
    if (key === 'offline') {
      options.offline = 'true';
    } else {
      options[key] = args[index + 1] ?? '';
      index += 1;
    }
  }
  return options;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  process.exitCode = await main();
}
