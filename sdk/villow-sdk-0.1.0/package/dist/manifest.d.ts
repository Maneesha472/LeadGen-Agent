export interface ManifestValidationResult {
    valid: boolean;
    errors: string[];
    warnings: string[];
    manifest: Record<string, unknown>;
}
export declare function loadManifest(path: string): Record<string, unknown>;
export declare function validateManifest(path: string): ManifestValidationResult;
