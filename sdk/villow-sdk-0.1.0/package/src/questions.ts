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

export class Question {
  static singleSelect(input: BaseQuestionInput & { options: string[]; default?: string }): BaseQuestion {
    if (input.options.length === 0) {
      throw new Error('singleSelect requires at least one option');
    }
    if (input.default !== undefined && !input.options.includes(input.default)) {
      throw new Error('default must be one of options');
    }
    return question({
      ...input,
      type: 'single_select',
      validation: { options: input.options },
      options: input.options,
    });
  }

  static number(input: BaseQuestionInput & { min?: number; max?: number; default?: number }): BaseQuestion {
    if (input.min !== undefined && input.max !== undefined && input.min > input.max) {
      throw new Error('min cannot be greater than max');
    }
    if (input.default !== undefined) {
      if (input.min !== undefined && input.default < input.min) {
        throw new Error('default cannot be below min');
      }
      if (input.max !== undefined && input.default > input.max) {
        throw new Error('default cannot exceed max');
      }
    }
    const validation: JsonObject = {};
    if (input.min !== undefined) validation.min = input.min;
    if (input.max !== undefined) validation.max = input.max;
    return question({ ...input, type: 'number', validation });
  }

  static boolean(input: BaseQuestionInput & { default?: boolean }): BaseQuestion {
    return question({ ...input, type: 'boolean', validation: {} });
  }

  static text(input: BaseQuestionInput & { default?: string; maxLength?: number }): BaseQuestion {
    const validation: JsonObject = {};
    if (input.maxLength !== undefined) validation.max_length = input.maxLength;
    return question({ ...input, type: 'text', validation });
  }
}

function question(
  input: BaseQuestionInput & { type: string; validation: JsonObject; options?: string[] },
): BaseQuestion {
  if (!input.id) throw new Error('question id is required');
  if (!input.label) throw new Error('question label is required');
  if (!input.decideForMe) throw new Error('decideForMe is required for every clarification question');
  const payload: BaseQuestion = {
    id: input.id,
    type: input.type,
    label: input.label,
    required: input.required ?? true,
    validation: input.validation,
    decide_for_me: input.decideForMe,
  };
  if (input.default !== undefined) payload.default_value = input.default;
  if (input.options) payload.options = input.options;
  return payload;
}
