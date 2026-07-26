# Villow Node SDK

Local-first SDK for self-hosted publisher agents.

```bash
pnpm --dir sdk/node test
pnpm --dir sdk/node build
pnpm --dir sdk/node validate
```

## Unit Charges

Publishers set a per-unit charge that may include legitimate operating margin. Report the
running/final charge with `ProgressEvent.unitCharge(...)` and `ctx.reportUnitCharge(...)`.
The listing's publisher-committed ceiling is the hard maximum; Villow's category markup
band is advisory for BYOK agents until consumption can be independently metered.

```ts
const event = ProgressEvent.unitCharge({ amount: 120, currency: "INR" });
await ctx.reportUnitCharge(event.cost_telemetry as Record<string, unknown>);
```

## Price Ceilings (T·M)

Declare per-unit price ceilings on each task template: `typical_charge` (T) and `unit_ceiling`
(M, the publisher-committed worst case), both in credits. Both are optional and additive — a
manifest without them stays valid — and `typical_charge` must never exceed `unit_ceiling`. The
platform holds `min(M, platform cap, remaining envelope)` and captures `min(declared charge, hold)`.

```yaml
task_templates:
  - slug: my_template
    artifact_type: table_data
    typical_charge: 120   # T
    unit_ceiling: 240     # M
```

## Continuation State (`agentState`)

For open-ended sessions, an agent may return an opaque `agent_state` blob to avoid recomputing on
the next unit. Read the replayed blob from `ctx.agentState`; set the next one with
`ctx.setAgentState({...})`. The platform stores it session-scoped, encrypted, and size-capped, and
replays it on the next unit — it never interprets the contents (JSON object only).

```ts
const prior = ctx.agentState.cursor;
ctx.setAgentState({ cursor: 'page-3' });
```

The `preview` decorator and manifest `preview_tier` field are forward-compatible only in the post-V1 scope-reduced launch contract. Agents may keep them for V1.5+ experiments, but V1 does not require or exercise `/preview`; deferred rich artifact review primitives such as `gallery_review`, `before_after_compare`, and `document_preview_with_fields` validate with warnings and render through simple typed fallbacks.

npm publishing, package signing, hosted docs, and production publisher onboarding are deferred operational setup. Local package build, validation, examples, and tests are the M3.3 build gate.
