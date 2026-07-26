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
export declare const CONTRACT_SCHEMAS: Record<string, Schema>;
export declare function validateContractMessage(kind: string, payload: unknown): ContractValidationResult;
export {};
