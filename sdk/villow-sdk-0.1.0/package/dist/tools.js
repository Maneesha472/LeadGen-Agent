export class Tools {
    drive;
    fs;
    http;
    mail;
    calendar;
    constructor(context) {
        this.drive = new DriveTools(context);
        this.fs = new FilesystemTools(context);
        this.http = new HttpTools(context);
        this.mail = new MailTools(context);
        this.calendar = new CalendarTools(context);
    }
}
class BaseToolClient {
    context;
    constructor(context) {
        this.context = context;
    }
    async call(toolName, args) {
        const idempotencyKey = this.context.idempotencyKey(`tool:${toolName}`);
        const payload = {
            task_id: this.context.taskId,
            agent_id: this.context.agent.agentId,
            args,
            idempotency_key: idempotencyKey,
        };
        const grantId = this.context.resolveToolAccessGrant(toolName);
        if (grantId)
            payload.tool_access_grant_id = grantId;
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
function unwrapToolResponse(response) {
    if (!response || typeof response !== 'object' || !('result' in response))
        return response;
    const raw = response.result;
    const result = raw && typeof raw === 'object' ? { ...raw } : {};
    const status = response.status;
    if (typeof status === 'string' && status !== 'success' && result.status === undefined) {
        result.status = status;
    }
    const artifactId = response.artifact_id;
    if (artifactId !== undefined && artifactId !== null && result.artifact_id === undefined) {
        result.artifact_id = String(artifactId);
    }
    return result;
}
export class DriveTools extends BaseToolClient {
    listFiles(input) {
        return this.call('drive.list_files', { folder_id: input.folderId, filters: input.filters ?? {} });
    }
    readFile(input) {
        return this.call('drive.read_file', { file_id: input.fileId });
    }
    createFile(input) {
        return this.call('drive.create_file', {
            folder_id: input.folderId,
            name: input.name,
            content: input.content ?? input.contentRef ?? '',
            mime_type: input.mimeType,
        });
    }
}
export class FilesystemTools extends BaseToolClient {
    read(input) {
        const args = { path: input.path };
        if (input.encoding)
            args.encoding = input.encoding;
        return this.call('fs.read', args);
    }
    write(input) {
        const args = { path: input.path };
        if (input.contentB64 !== undefined)
            args.content_b64 = input.contentB64;
        else if (input.content !== undefined)
            args.content = input.content;
        else
            args.content = input.contentRef ?? '';
        return this.call('fs.write', args);
    }
    /** List workspace entries at `path` → `{ path, entries: [name, ...] }`. */
    list(input = {}) {
        return this.call('fs.list', { path: input.path ?? '.' });
    }
}
export class HttpTools extends BaseToolClient {
    get(input) {
        return this.call('http.get', { url: input.url, headers: input.headers ?? {} });
    }
    post(input) {
        return this.call('http.post', { url: input.url, json: input.json, headers: input.headers ?? {} });
    }
}
export class MailTools extends BaseToolClient {
    readThread(input) {
        return this.call('mail.read_thread', { thread_id: input.threadId });
    }
}
export class CalendarTools extends BaseToolClient {
    listEvents(input) {
        return this.call('calendar.list_events', {
            calendar_id: input.calendarId,
            time_min: input.timeMin,
            time_max: input.timeMax,
        });
    }
}
