import { readFileSync } from 'node:fs';
import { parse } from 'yaml';
import { z } from 'zod';
const artifactTypes = z.enum(['file_set', 'structured_fields', 'message_draft', 'event_proposal', 'table_data', 'generic']);
const primitiveSchema = z.object({
    primitive: z.string(),
    id: z.string().min(1),
    label: z.string().optional(),
    default_value: z.unknown().optional(),
    decide_for_me: z.record(z.string(), z.unknown()),
});
const templateSchema = z
    .object({
    slug: z.string().min(1),
    category_slug: z.string().optional(),
    artifact_type: artifactTypes,
    preview_tier: z.number().int().min(1).max(3).optional(),
    artifact_review_primitive: z.string().optional(),
    // T·M per-unit price ceilings (N1.5, formalizes F3): optional + additive — a manifest without
    // them stays valid (M is enforced at vetting, not here). unit_ceiling = M (worst case),
    // typical_charge = T. Validate only when present; T must never exceed M.
    unit_ceiling: z.number().int().positive().optional(),
    typical_charge: z.number().int().nonnegative().optional(),
    input_composition: z.array(primitiveSchema).max(10).default([]),
})
    .refine((template) => template.unit_ceiling === undefined ||
    template.typical_charge === undefined ||
    template.typical_charge <= template.unit_ceiling, { message: 'typical_charge must not exceed unit_ceiling', path: ['typical_charge'] });
const toolRateLimitSchema = z.object({
    per_minute: z.number().int().positive(),
    justification: z.string().optional(),
});
const manifestSchema = z.object({
    publisher_id: z.string().min(1),
    agent_id: z.string().min(1),
    name: z.string().min(1),
    version: z.string().min(1),
    task_templates: z.array(templateSchema).min(1),
    tool_rate_limits: z.record(z.string(), toolRateLimitSchema).optional(),
});
export function loadManifest(path) {
    const parsed = parse(readFileSync(path, 'utf8'));
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('agent manifest must be a YAML object');
    }
    return parsed;
}
export function validateManifest(path) {
    try {
        const manifest = loadManifest(path);
        const result = manifestSchema.safeParse(manifest);
        return {
            valid: result.success,
            errors: result.success ? [] : result.error.issues.map((issue) => `${issue.path.join('.')}: ${issue.message}`),
            warnings: result.success ? manifestWarnings(result.data) : [],
            manifest,
        };
    }
    catch (error) {
        return {
            valid: false,
            errors: [error instanceof Error ? error.message : 'manifest validation failed'],
            warnings: [],
            manifest: {},
        };
    }
}
function manifestWarnings(manifest) {
    const warnings = [];
    const deferredReviewPrimitives = new Set(['gallery_review', 'before_after_compare', 'document_preview_with_fields']);
    manifest.task_templates.forEach((template, index) => {
        if (template.preview_tier !== undefined) {
            warnings.push(`task_templates[${index}].preview_tier is forward-compatible only; V1 does not require or exercise /preview`);
        }
        if (template.artifact_review_primitive && deferredReviewPrimitives.has(template.artifact_review_primitive)) {
            warnings.push(`task_templates[${index}].artifact_review_primitive ${template.artifact_review_primitive} is deferred from V1 launch and will render with the simple typed fallback`);
        }
    });
    for (const [toolName, config] of Object.entries(manifest.tool_rate_limits ?? {})) {
        if (!config.justification) {
            warnings.push(`tool_rate_limits.${toolName}.justification is recommended for publisher vetting`);
        }
    }
    return warnings;
}
