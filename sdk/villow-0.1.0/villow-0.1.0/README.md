# Villow Python SDK

Local-first SDK for self-hosted publisher agents.

## Install Locally

```bash
python3 -m pip install -e sdk/python
villow validate sdk/python/examples/agent.yaml
python3 -m pytest tests/test_python_sdk_m32.py -v
```

## Minimal Agent

```python
from villow import Agent, Artifact, task_template


class HelloAgent(Agent):
    @task_template("hello_world")
    async def run(self, inputs, ctx):
        await ctx.stage_artifact(Artifact.generic(payload={"message": f"Hello {inputs['name']}"}))
```

Run a local task flow with the mock platform harness:

```python
from sdk.python.examples.hello_world_agent import HelloWorldAgent
from villow.testing import MockPlatformHarness

result = MockPlatformHarness(HelloWorldAgent(), render_mode="simple").run_task(
    "hello_world",
    {"name": "Villow"},
    answers={"tone": "friendly"},
)
```

## Unit Charges

Publishers set a per-unit charge that may include legitimate operating margin. Report the
running/final charge with `ProgressEvent.unit_charge(...)` and `ctx.report_unit_charge(...)`.
The listing's publisher-committed ceiling is the hard maximum; Villow's category markup
band is advisory for BYOK agents until consumption can be independently metered.

```python
event = ProgressEvent.unit_charge(amount=120, currency="INR")
await ctx.report_unit_charge(event["cost_telemetry"])
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

## Continuation State (`agent_state`)

For open-ended sessions, an agent may return an opaque `agent_state` blob to avoid recomputing
on the next unit. Read the replayed blob from `ctx.agent_state`; set the next one with
`ctx.set_agent_state({...})`. The platform stores it session-scoped, encrypted, and size-capped,
and replays it on the next unit — it never interprets the contents (JSON object only).

```python
prior = ctx.agent_state.get("cursor")
ctx.set_agent_state({"cursor": "page-3"})
```

## Local Boundaries

The SDK signs callbacks and tool calls with the M3.1 canonical HMAC contract. Tool calls use opaque `tool_access_grant` handles only; raw OAuth tokens are never passed to publishers.

The `@preview` decorator and manifest `preview_tier` field are forward-compatible only in the post-V1 scope-reduced launch contract. Agents may keep them for V1.5+ experiments, but V1 does not require or exercise `/preview`; deferred rich artifact review primitives such as `gallery_review`, `before_after_compare`, and `document_preview_with_fields` validate with warnings and render through simple typed fallbacks.

Publishing to PyPI, package signing, hosted docs, production publisher onboarding, callback-domain allowlisting, and production endpoint hosting are deferred operational setup. Local editable install, `villow validate`, `MockPlatformHarness`, and tests are the M3.2 build gate.
