import type { JsonObject } from './questions.js';
export interface PrimitivePayload {
    primitive: string;
    type: string;
    id: string;
    label: string;
    validation: JsonObject;
    default_value?: unknown;
    options?: unknown[];
    preview?: JsonObject;
    explanation?: string;
}
export interface CompositionPayload {
    composition_id?: string;
    task_template?: string;
    mode: 'input_collection';
    primitives: PrimitivePayload[];
    fallback_slots: Array<Record<string, unknown>>;
}
export declare class Composition {
    static input(primitives: PrimitivePayload[], options?: {
        fallbackSlots?: Array<Record<string, unknown>>;
        taskTemplate?: string;
        compositionId?: string;
    }): CompositionPayload;
    static visualPicker(id: string, options?: {
        label?: string;
        options?: Array<Record<string, unknown>>;
        default?: string;
        previewTier?: number;
    }): PrimitivePayload;
    static aspectRatioPicker(id: string, options?: {
        label?: string;
        default?: string;
        options?: string[];
    }): PrimitivePayload;
    static sliderWithLivePreview(id: string, options: {
        label?: string;
        min: number;
        max: number;
        default: number;
    }): PrimitivePayload;
    static drivePicker(id: string, options?: {
        label?: string;
        mode?: 'file' | 'folder';
        provider?: string;
        allowMultiple?: boolean;
    }): PrimitivePayload;
    static toggleWithExplanation(id: string, options?: {
        label?: string;
        default?: boolean;
        explanation?: string;
    }): PrimitivePayload;
    static dropdownWithDescriptions(id: string, options: {
        label?: string;
        options: Array<Record<string, unknown>>;
        default?: string;
    }): PrimitivePayload;
    static multiSelectChips(id: string, options: {
        label?: string;
        options: string[];
        default?: string[];
    }): PrimitivePayload;
}
