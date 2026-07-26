import type { Context } from './context.js';

export class Tools {
  drive: DriveTools;
  fs: FilesystemTools;
  http: HttpTools;
  mail: MailTools;
  calendar: CalendarTools;

  constructor(context: Context) {
    this.drive = new DriveTools(context);
    this.fs = new FilesystemTools(context);
    this.http = new HttpTools(context);
    this.mail = new MailTools(context);
    this.calendar = new CalendarTools(context);
  }
}

class BaseToolClient {
  constructor(protected context: Context) {}

  protected async call(toolName: string, args: Record<string, unknown>): Promise<Record<string, unknown>> {
    const idempotencyKey = this.context.idempotencyKey(`tool:${toolName}`);
    const payload: Record<string, unknown> = {
      task_id: this.context.taskId,
      agent_id: this.context.agent.agentId,
      args,
      idempotency_key: idempotencyKey,
    };
    const grantId = this.context.resolveToolAccessGrant(toolName);
    if (grantId) payload.tool_access_grant_id = grantId;
    const response = await this.context.agent.signedPlatformPost(`/v1/tools/${toolName}`, payload, {
      idempotencyKey,
    });
    return unwrapToolResponse(response);
  }
}

/**
 * Unwrap the tool proxy's ToolCallResponse envelope into the tool result itself.
 * The proxy answers `{ tool_name, task_id, status, result, artifact_id }`, but the SDK
 * dialect hands publishers the result payload directly (`entries`/`files`/`content` at the
 * top level). Staged-write metadata (non-success `status`, `artifact_id`) is carried into
 * the unwrapped payload so stage-and-approve flows keep working. Mirrors the Python SDK.
 */
function unwrapToolResponse(response: Record<string, unknown>): Record<string, unknown> {
  if (!response || typeof response !== 'object' || !('result' in response)) return response;
  const raw = (response as { result?: unknown }).result;
  const result: Record<string, unknown> =
    raw && typeof raw === 'object' ? { ...(raw as Record<string, unknown>) } : {};
  const status = (response as { status?: unknown }).status;
  if (typeof status === 'string' && status !== 'success' && result.status === undefined) {
    result.status = status;
  }
  const artifactId = (response as { artifact_id?: unknown }).artifact_id;
  if (artifactId !== undefined && artifactId !== null && result.artifact_id === undefined) {
    result.artifact_id = String(artifactId);
  }
  return result;
}

export class DriveTools extends BaseToolClient {
  listFiles(input: { folderId: string; filters?: Record<string, unknown> }): Promise<Record<string, unknown>> {
    return this.call('drive.list_files', { folder_id: input.folderId, filters: input.filters ?? {} });
  }

  readFile(input: { fileId: string }): Promise<Record<string, unknown>> {
    return this.call('drive.read_file', { file_id: input.fileId });
  }

  createFile(input: { folderId: string; name: string; mimeType: string; content?: string; contentRef?: string }): Promise<Record<string, unknown>> {
    return this.call('drive.create_file', {
      folder_id: input.folderId,
      name: input.name,
      content: input.content ?? input.contentRef ?? '',
      mime_type: input.mimeType,
    });
  }
}

export class FilesystemTools extends BaseToolClient {
  read(input: { path: string; encoding?: string }): Promise<Record<string, unknown>> {
    const args: Record<string, unknown> = { path: input.path };
    if (input.encoding) args.encoding = input.encoding;
    return this.call('fs.read', args);
  }

  write(input: { path: string; content?: string; contentRef?: string; contentB64?: string }): Promise<Record<string, unknown>> {
    const args: Record<string, unknown> = { path: input.path };
    if (input.contentB64 !== undefined) args.content_b64 = input.contentB64;
    else if (input.content !== undefined) args.content = input.content;
    else args.content = input.contentRef ?? '';
    return this.call('fs.write', args);
  }

  /** List workspace entries at `path` → `{ path, entries: [name, ...] }`. */
  list(input: { path?: string } = {}): Promise<Record<string, unknown>> {
    return this.call('fs.list', { path: input.path ?? '.' });
  }
}

export class HttpTools extends BaseToolClient {
  get(input: { url: string; headers?: Record<string, string> }): Promise<Record<string, unknown>> {
    return this.call('http.get', { url: input.url, headers: input.headers ?? {} });
  }

  post(input: { url: string; json: Record<string, unknown>; headers?: Record<string, string> }): Promise<Record<string, unknown>> {
    return this.call('http.post', { url: input.url, json: input.json, headers: input.headers ?? {} });
  }
}

export class MailTools extends BaseToolClient {
  readThread(input: { threadId: string }): Promise<Record<string, unknown>> {
    return this.call('mail.read_thread', { thread_id: input.threadId });
  }
}

export class CalendarTools extends BaseToolClient {
  listEvents(input: { calendarId: string; timeMin: string; timeMax: string }): Promise<Record<string, unknown>> {
    return this.call('calendar.list_events', {
      calendar_id: input.calendarId,
      time_min: input.timeMin,
      time_max: input.timeMax,
    });
  }
}
