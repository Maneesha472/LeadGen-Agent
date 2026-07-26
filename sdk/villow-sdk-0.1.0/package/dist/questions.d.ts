export type JsonObject = Record<string, unknown>;
export interface BaseQuestion {
    id: string;
    type: string;
    label: string;
    required: boolean;
    default_value?: unknown;
    validation: JsonObject;
    decide_for_me: JsonObject;
    options?: string[];
}
interface BaseQuestionInput {
    id: string;
    label: string;
    default?: unknown;
    decideForMe?: JsonObject;
    required?: boolean;
}
export declare class Question {
    static singleSelect(input: BaseQuestionInput & {
        options: string[];
        default?: string;
    }): BaseQuestion;
    static number(input: BaseQuestionInput & {
        min?: number;
        max?: number;
        default?: number;
    }): BaseQuestion;
    static boolean(input: BaseQuestionInput & {
        default?: boolean;
    }): BaseQuestion;
    static text(input: BaseQuestionInput & {
        default?: string;
        maxLength?: number;
    }): BaseQuestion;
}
export {};
