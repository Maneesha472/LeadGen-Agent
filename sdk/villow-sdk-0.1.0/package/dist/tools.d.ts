import type { Context } from './context.js';
export declare class Tools {
    drive: DriveTools;
    fs: FilesystemTools;
    http: HttpTools;
    mail: MailTools;
    calendar: CalendarTools;
    constructor(context: Context);
}
declare class BaseToolClient {
    protected context: Context;
    constructor(context: Context);
    protected call(toolName: string, args: Record<string, unknown>): Promise<Record<string, unknown>>;
}
export declare class DriveTools extends BaseToolClient {
    listFiles(input: {
        folderId: string;
        filters?: Record<string, unknown>;
    }): Promise<Record<string, unknown>>;
    readFile(input: {
        fileId: string;
    }): Promise<Record<string, unknown>>;
    createFile(input: {
        folderId: string;
        name: string;
        mimeType: string;
        content?: string;
        contentRef?: string;
    }): Promise<Record<string, unknown>>;
}
export declare class FilesystemTools extends BaseToolClient {
    read(input: {
        path: string;
        encoding?: string;
    }): Promise<Record<string, unknown>>;
    write(input: {
        path: string;
        content?: string;
        contentRef?: string;
        contentB64?: string;
    }): Promise<Record<string, unknown>>;
    /** List workspace entries at `path` → `{ path, entries: [name, ...] }`. */
    list(input?: {
        path?: string;
    }): Promise<Record<string, unknown>>;
}
export declare class HttpTools extends BaseToolClient {
    get(input: {
        url: string;
        headers?: Record<string, string>;
    }): Promise<Record<string, unknown>>;
    post(input: {
        url: string;
        json: Record<string, unknown>;
        headers?: Record<string, string>;
    }): Promise<Record<string, unknown>>;
}
export declare class MailTools extends BaseToolClient {
    readThread(input: {
        threadId: string;
    }): Promise<Record<string, unknown>>;
}
export declare class CalendarTools extends BaseToolClient {
    listEvents(input: {
        calendarId: string;
        timeMin: string;
        timeMax: string;
    }): Promise<Record<string, unknown>>;
}
export {};
