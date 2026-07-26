import { type Agent } from './agent.js';
export interface HarnessOptions {
    renderMode?: 'rich' | 'simple';
    keyId?: string;
    publisherId?: string;
    agentId?: string;
    secret?: string;
}
export declare class MockPlatformHarness {
    private agent;
    private app;
    private counter;
    private renderMode;
    private keyId;
    private publisherId;
    private agentId;
    private secret;
    constructor(agent: Agent, options?: HarnessOptions);
    runTask(taskTemplate: string, inputs: Record<string, unknown>, options?: {
        answers?: Record<string, unknown>;
        delegatedDecisions?: Record<string, boolean>;
    }): Promise<Record<string, unknown>>;
    post(path: string, payload: Record<string, unknown>): Promise<Record<string, unknown>>;
    close(): Promise<void>;
}
