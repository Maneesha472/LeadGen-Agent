const MAX_PRIMITIVES = 10;
export class Composition {
    static input(primitives, options = {}) {
        if (primitives.length > MAX_PRIMITIVES) {
            throw new Error('V1 compositions must use no more than 10 primitives');
        }
        ensureUniqueIds(primitives);
        return {
            composition_id: options.compositionId,
            task_template: options.taskTemplate,
            mode: 'input_collection',
            primitives,
            fallback_slots: options.fallbackSlots ?? fallbackSlots(primitives),
        };
    }
    static visualPicker(id, options = {}) {
        return primitive('visual_picker', id, {
            label: options.label,
            defaultValue: options.default,
            options: options.options ?? [],
            preview: { tier: options.previewTier ?? 1 },
        });
    }
    static aspectRatioPicker(id, options = {}) {
        const values = options.options ?? ['original', 'square', '4:5', '16:9'];
        return primitive('aspect_ratio_picker', id, {
            label: options.label,
            defaultValue: options.default ?? 'original',
            validation: { options: values },
            options: values,
        });
    }
    static sliderWithLivePreview(id, options) {
        if (options.min > options.max)
            throw new Error('min cannot be greater than max');
        if (options.default < options.min || options.default > options.max)
            throw new Error('default must be within bounds');
        return primitive('slider_with_live_preview', id, {
            label: options.label,
            defaultValue: options.default,
            validation: { min: options.min, max: options.max },
            preview: { live: true },
        });
    }
    static drivePicker(id, options = {}) {
        const mode = options.mode ?? 'file';
        return primitive('drive_picker', id, {
            label: options.label,
            validation: { mode, provider: options.provider ?? 'google', allow_multiple: options.allowMultiple ?? false },
        });
    }
    static toggleWithExplanation(id, options = {}) {
        const payload = primitive('toggle_with_explanation', id, { label: options.label, defaultValue: options.default ?? false });
        if (options.explanation)
            payload.explanation = options.explanation;
        return payload;
    }
    static dropdownWithDescriptions(id, options) {
        return primitive('dropdown_with_descriptions', id, {
            label: options.label,
            defaultValue: options.default,
            options: options.options,
        });
    }
    static multiSelectChips(id, options) {
        return primitive('multi_select_chips', id, {
            label: options.label,
            defaultValue: options.default ?? [],
            validation: { options: options.options },
        });
    }
}
function primitive(primitiveType, id, options = {}) {
    if (!id)
        throw new Error('primitive id is required');
    const payload = {
        primitive: primitiveType,
        type: primitiveType,
        id,
        label: options.label ?? labelFromId(id),
        validation: options.validation ?? {},
    };
    if (options.defaultValue !== undefined)
        payload.default_value = options.defaultValue;
    if (options.options !== undefined)
        payload.options = options.options;
    if (options.preview !== undefined)
        payload.preview = options.preview;
    return payload;
}
function ensureUniqueIds(primitives) {
    const seen = new Set();
    for (const item of primitives) {
        if (seen.has(item.id))
            throw new Error(`duplicate primitive id: ${item.id}`);
        seen.add(item.id);
    }
}
function fallbackSlots(primitives) {
    return primitives.map((item) => ({
        id: item.id,
        label: item.label,
        type: fallbackType(item),
        default_value: item.default_value,
        validation: item.validation,
    }));
}
function fallbackType(item) {
    if (item.primitive === 'slider_with_live_preview')
        return 'number';
    if (item.primitive === 'drive_picker')
        return item.validation.mode === 'folder' ? 'drive_folder' : 'drive_file';
    if (item.primitive === 'toggle_with_explanation')
        return 'boolean';
    if (['visual_picker', 'aspect_ratio_picker', 'dropdown_with_descriptions'].includes(item.primitive))
        return 'single_select';
    if (item.primitive === 'multi_select_chips')
        return 'multi_select';
    return 'text';
}
function labelFromId(id) {
    return id.replace(/_/g, ' ').replace(/([a-z])([A-Z])/g, '$1 $2').replace(/\b\w/g, (char) => char.toUpperCase());
}
