export interface ContractValidationError {
  field_path: string;
  message: string;
  expected?: string;
  received?: string;
}

export interface ContractValidationResult {
  valid: boolean;
  errors: ContractValidationError[];
}

type Schema = {
  type: 'object' | 'array' | 'string' | 'boolean';
  required?: string[];
  properties?: Record<string, Schema>;
  items?: Schema;
  maxItems?: number;
  additionalProperties?: boolean;
};

const object = (required: string[] = [], properties: Record<string, Schema> = {}): Schema => ({
  type: 'object',
  required,
  properties,
  additionalProperties: true,
});
const array = (items?: Schema, maxItems?: number): Schema => ({ type: 'array', items, maxItems });
const OBJECT = object();

export const CONTRACT_SCHEMAS: Record<string, Schema> = {
  'request.discover': object(),
  'response.discover': object(['publisher_id', 'agent_id'], { publisher_id: { type: 'string' }, agent_id: { type: 'string' } }),
  'request.prepare': object(['task_id', 'task_template'], { task_id: { type: 'string' }, task_template: { type: 'string' }, initial_inputs: OBJECT, session_context: OBJECT, agent_state: OBJECT }),
  'response.prepare': object(['task_id', 'state'], { task_id: { type: 'string' }, state: { type: 'string' }, composition_response: OBJECT }),
  'request.preview': object(['task_id', 'task_template'], { task_id: { type: 'string' }, task_template: { type: 'string' }, current_inputs: OBJECT }),
  'response.preview': object(['task_id', 'preview'], { task_id: { type: 'string' }, preview: OBJECT }),
  'request.execute': object(['task_id', 'task_template'], { task_id: { type: 'string' }, task_template: { type: 'string' }, inputs: OBJECT, callback_urls: OBJECT, session_context: OBJECT, agent_state: OBJECT }),
  'response.execute': object(['task_id'], { task_id: { type: 'string' }, accepted: { type: 'boolean' }, agent_state: OBJECT }),
  'request.clarification_response': object(['task_id', 'clarification_id', 'phase'], { task_id: { type: 'string' }, clarification_id: { type: 'string' }, phase: { type: 'string' }, answers: OBJECT }),
  'response.clarification_response': object(['task_id', 'accepted'], { task_id: { type: 'string' }, accepted: { type: 'boolean' } }),
  'request.status': object(['task_id'], { task_id: { type: 'string' } }),
  'response.status': object(['task_id', 'state'], { task_id: { type: 'string' }, state: { type: 'string' } }),
  'request.cancel': object(['task_id'], { task_id: { type: 'string' } }),
  'response.cancel': object(['task_id'], { task_id: { type: 'string' }, cancelling: { type: 'boolean' } }),
  'request.result': object(['task_id'], { task_id: { type: 'string' } }),
  'response.result': object(['task_id', 'state'], { task_id: { type: 'string' }, state: { type: 'string' }, artifacts: array(), agent_state: OBJECT }),
  'callback.status': object(['task_id'], { task_id: { type: 'string' }, state: { type: 'string' }, progress: OBJECT, messages: array() }),
  'callback.progress': object(['task_id'], { task_id: { type: 'string' }, progress: OBJECT, messages: array() }),
  'callback.progress_batch': object(['events'], { events: array(object(['task_id'], { task_id: { type: 'string' }, progress: OBJECT }), 100) }),
  'callback.clarification_required': object(['task_id'], { task_id: { type: 'string' }, phase: { type: 'string' }, questions: array() }),
  'callback.sample_complete': object(['task_id'], { task_id: { type: 'string' }, sample_artifact: OBJECT }),
  'callback.artifact_staged': object(['task_id'], { task_id: { type: 'string' }, artifact: OBJECT }),
  'callback.error': object(['task_id'], { task_id: { type: 'string' }, message: { type: 'string' } }),
};

export function validateContractMessage(kind: string, payload: unknown): ContractValidationResult {
  const schema = CONTRACT_SCHEMAS[kind];
  if (!schema) return { valid: false, errors: [{ field_path: '', message: 'unknown contract message kind', received: kind }] };
  const errors: ContractValidationError[] = [];
  validate(schema, payload, '', errors);
  return { valid: errors.length === 0, errors };
}

function validate(schema: Schema, value: unknown, path: string, errors: ContractValidationError[]): void {
  if (!matches(value, schema.type)) {
    errors.push({ field_path: path, message: `expected ${schema.type}`, expected: schema.type, received: received(value) });
    return;
  }
  if (schema.type === 'object') {
    const source = value as Record<string, unknown>;
    for (const field of schema.required ?? []) {
      if (!(field in source)) errors.push({ field_path: joinPath(path, field), message: 'required field missing', expected: schema.properties?.[field]?.type, received: 'missing' });
    }
    for (const [field, child] of Object.entries(schema.properties ?? {})) {
      if (field in source) validate(child, source[field], joinPath(path, field), errors);
    }
  }
  if (schema.type === 'array') {
    const source = value as unknown[];
    if (schema.maxItems !== undefined && source.length > schema.maxItems) {
      errors.push({ field_path: path, message: `must contain at most ${schema.maxItems} items`, expected: `maxItems:${schema.maxItems}`, received: String(source.length) });
    }
    if (schema.items) source.forEach((item, index) => validate(schema.items as Schema, item, joinPath(path, String(index)), errors));
  }
}

function matches(value: unknown, expected: Schema['type']): boolean {
  if (expected === 'object') return value !== null && typeof value === 'object' && !Array.isArray(value);
  if (expected === 'array') return Array.isArray(value);
  if (expected === 'string') return typeof value === 'string';
  if (expected === 'boolean') return typeof value === 'boolean';
  return true;
}

function received(value: unknown): string {
  if (Array.isArray(value)) return 'array';
  if (value === null) return 'null';
  return typeof value === 'object' ? 'object' : typeof value;
}

function joinPath(prefix: string, field: string): string {
  return prefix ? `${prefix}.${field}` : field;
}
