export class Question {
    static singleSelect(input) {
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
    static number(input) {
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
        const validation = {};
        if (input.min !== undefined)
            validation.min = input.min;
        if (input.max !== undefined)
            validation.max = input.max;
        return question({ ...input, type: 'number', validation });
    }
    static boolean(input) {
        return question({ ...input, type: 'boolean', validation: {} });
    }
    static text(input) {
        const validation = {};
        if (input.maxLength !== undefined)
            validation.max_length = input.maxLength;
        return question({ ...input, type: 'text', validation });
    }
}
function question(input) {
    if (!input.id)
        throw new Error('question id is required');
    if (!input.label)
        throw new Error('question label is required');
    if (!input.decideForMe)
        throw new Error('decideForMe is required for every clarification question');
    const payload = {
        id: input.id,
        type: input.type,
        label: input.label,
        required: input.required ?? true,
        validation: input.validation,
        decide_for_me: input.decideForMe,
    };
    if (input.default !== undefined)
        payload.default_value = input.default;
    if (input.options)
        payload.options = input.options;
    return payload;
}
