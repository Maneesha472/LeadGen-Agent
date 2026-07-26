# Villow Publisher SDK — Getting Started

**Version:** 0.1.0  
**Languages:** Python 3.13+ and Node.js 22+  
**Package contents in this folder:**

| File | Language | Install with |
|------|----------|--------------|
| `villow-0.1.0-py3-none-any.whl` | Python | `pip install` (preferred) |
| `villow-0.1.0.tar.gz` | Python | `pip install` (alternative) |
| `villow-sdk-0.1.0.tgz` | Node | `npm install` or `pnpm add` |

Both SDKs implement the same **publisher wire contract** (`/v1/` endpoints, HMAC signing, streaming event types). Choose the language your team uses — you do not need both.

---

## Table of contents

1. [What you are building](#1-what-you-are-building)
2. [How URLs work (read this first)](#2-how-urls-work-read-this-first)
3. [Prerequisites](#3-prerequisites)
4. [Install the SDK](#4-install-the-sdk)
5. [Verify the install](#5-verify-the-install)
6. [Your first agent (5 minutes)](#6-your-first-agent-5-minutes)
7. [Manifest (`agent.yaml`)](#7-manifest-agentyaml)
8. [Run locally](#8-run-locally)
9. [Self-check before onboarding](#9-self-check-before-onboarding)
10. [Open-ended sessions](#10-open-ended-sessions)
11. [Streaming agents (recommended)](#11-streaming-agents-recommended)
12. [Migrating existing callback-style agents](#12-migrating-existing-callback-style-agents)
13. [Pricing and unit charges](#13-pricing-and-unit-charges)
14. [Platform rules (non-negotiable)](#14-platform-rules-non-negotiable)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. What you are building

A **self-hosted HTTP agent** that Villow calls over signed `/v1/` requests:

| You implement | Purpose |
|---------------|---------|
| `POST /discover` | Advertise task templates |
| `POST /prepare` | Normalize inputs; return clarifications or `ready_to_authorize` |
| `POST /execute` | Run the task |
| `POST /clarification_response` | Resume after user answers |
| `POST /status`, `/cancel`, `/result` | Lifecycle |

You **call back** to Villow (also signed) for progress, clarifications, and staged artifacts — or emit an **AG-UI event stream** for the modern session UI.

The SDK gives you:

- HMAC request signing (matches the platform exactly)
- A local dev server (`create_app` / `createApp`)
- Helpers for artifacts, clarifications, composition, progress, and streaming
- A manifest validator and contract self-test CLI

---

## 2. How URLs work (read this first)

There are **three URLs** in the picture. Only **one** is yours to host.

```
  End user                Villow (we host)              You (publisher)
  ────────                ──────────────────              ───────────────

  Opens browser    →      Staging web app
                          worklane-staging.villow.ai
                               │
                               │  user starts a session
                               ▼
                          Villow platform calls  →     YOUR agent server
                          (orchestration)                  https://your-agent.com
                               ▲                               │
                               │                               │
                               └──── callbacks & tools ────────┘
                                    (URLs we send you in each request)
```

### Villow staging (we give you these — for testing)

| URL | Who uses it | What it is |
|-----|-------------|------------|
| **https://worklane-staging.villow.ai** | You + your test users | Staging **web app** — sign in here to run a real session against your agent |
| **https://worklane-staging-api-xpwnwabd4q-uc.a.run.app** | Villow (automatic) | Staging **platform API** — you do **not** configure your agent to call this for the main contract |

**You do not paste the platform API URL into your agent code.** When Villow runs your agent, each `/execute` request includes ready-made `callback_urls` and `tool_access_grant` handles. The SDK uses those automatically when you call `ctx.report_progress()`, `ctx.stage_artifact()`, or `ctx.tools.*`.

### Your agent URL (you give us this — required)

This is the **HTTPS base URL** where your agent server is reachable, for example:

```
https://agent.yourcompany.com
```

Villow sends signed `POST` requests to paths on **your** server:

- `/discover`, `/prepare`, `/execute`, `/status`, `/cancel`, `/result`, `/clarification_response`

**Before onboarding, send Villow:**

1. Your agent base URL (must be **HTTPS**, publicly reachable from the internet)
2. Your `agent.yaml` manifest
3. Confirmation that `villow contract-test <your-url>` passes (see [§9](#9-self-check-before-onboarding))

Villow registers that URL in staging. After that, when a user picks your agent on **worklane-staging.villow.ai**, calls flow **Villow → your URL**.

### Local development (your laptop)

While building, your agent runs on `http://localhost:8080`. Villow staging cannot reach localhost directly. Use a tunnel:

```bash
# Example with ngrok (any similar tunnel works)
ngrok http 8080
# → gives you https://abc123.ngrok-free.app  ← send this temporary URL for testing
```

Run the contract test against the **tunnel URL**, not the Villow staging URL:

```bash
villow contract-test https://abc123.ngrok-free.app \
  --publisher-id YOUR_PUBLISHER_ID \
  --agent-id YOUR_AGENT_ID \
  --signing-key-id YOUR_KEY_ID \
  --secret YOUR_SECRET
```

### Quick checklist

| Item | Owner | Example |
|------|-------|---------|
| Staging web app (where users test) | Villow | `https://worklane-staging.villow.ai` |
| Agent server URL (where Villow calls you) | **You** | `https://agent.yourcompany.com` |
| Callback / tool URLs during a run | Villow (in each request) | Auto — use SDK `ctx.*` helpers |
| Signing credentials | Villow (via onboarding) | `publisher_id`, `agent_id`, `key_id`, `secret` |

---

## 3. Prerequisites

### Python

- Python **3.13+**
- `pip`

### Node

- Node **22+**
- `npm`, `pnpm`, or `yarn`

### For both

- A reachable HTTPS endpoint for your agent (staging/production)
- Signing credentials from Villow onboarding: `publisher_id`, `agent_id`, `signing_key_id`, `secret`

---

## 4. Install the SDK

### Python

From the directory containing the wheel:

```bash
pip install villow-0.1.0-py3-none-any.whl
```

Alternative (source tarball):

```bash
pip install villow-0.1.0.tar.gz
```

This installs the `villow` package and two CLI entry points:

- `villow` — manifest validation, contract test
- `villow-contract-test` — alias for contract test

### Node

```bash
npm install ./villow-sdk-0.1.0.tgz
```

Or with pnpm:

```bash
pnpm add ./villow-sdk-0.1.0.tgz
```

This installs `@villow/sdk` and two CLI entry points:

- `villow-node` — manifest validation, contract test
- `villow-contract-test` — alias for contract test

> **Tip:** Use an absolute or relative path to the `.tgz` file as shown above.

---

## 5. Verify the install

### Python

```bash
python3 -c "from villow import Agent, Stream; print('villow OK')"
worklane --help
```

### Node

```bash
node -e "import('@villow/sdk').then(m => console.log('villow OK', Object.keys(m).slice(0,5)))"
npx villow-node --help
```

---

## 6. Your first agent (5 minutes)

### Python

Create `hello_agent.py`:

```python
from villow import Agent, Artifact, task_template


class HelloAgent(Agent):
    @task_template("hello_world")
    async def run(self, inputs, ctx):
        name = inputs.get("name", "there")
        await ctx.stage_artifact(
            Artifact.generic(payload={"message": f"Hello {name}"})
        )
```

Create `agent.yaml`:

```yaml
publisher_id: YOUR_PUBLISHER_ID
agent_id: YOUR_AGENT_ID
name: Hello World Agent
version: 0.1.0
task_templates:
  - slug: hello_world
    category_slug: documents_forms_data_extraction
    artifact_type: generic
    typical_charge: 20
    unit_ceiling: 40
```

Validate the manifest:

```bash
villow validate agent.yaml
```

Run a local server:

```python
# run_server.py
import uvicorn
from villow.server import create_app
from hello_agent import HelloAgent

agent = HelloAgent(
    publisher_id="YOUR_PUBLISHER_ID",
    agent_id="YOUR_AGENT_ID",
    signing_key_id="YOUR_KEY_ID",
    secret="YOUR_SECRET",
)
uvicorn.run(create_app(agent), host="0.0.0.0", port=8080)
```

```bash
pip install uvicorn   # if not already installed via worklane deps
python run_server.py
```

### Node

Create `hello-agent.ts`:

```typescript
import { Agent, Artifact, createApp, taskTemplate } from '@villow/sdk';

class HelloAgent extends Agent {
  @taskTemplate('hello_world')
  async run(inputs: Record<string, unknown>, ctx: { stageArtifact: (a: unknown) => Promise<unknown> }) {
    const name = (inputs.name as string) ?? 'there';
    await ctx.stageArtifact(Artifact.generic({ payload: { message: `Hello ${name}` } }));
  }
}

const agent = new HelloAgent({
  publisherId: 'YOUR_PUBLISHER_ID',
  agentId: 'YOUR_AGENT_ID',
  signingKeyId: 'YOUR_KEY_ID',
  secret: 'YOUR_SECRET',
});

createApp(agent).listen({ port: 8080, host: '0.0.0.0' });
```

Use the same `agent.yaml` as above, then:

```bash
villow-node validate agent.yaml
npx tsx hello-agent.ts
```

---

## 7. Manifest (`agent.yaml`)

Every agent ships a manifest Villow uses for marketplace listing and holds.

**Required top-level fields:** `publisher_id`, `agent_id`, `name`, `version`, `task_templates`.

**Per template:**

| Field | Required | Notes |
|-------|----------|-------|
| `slug` | Yes | Matches `@task_template` / `@taskTemplate` decorator |
| `category_slug` | Yes | Registered Villow category |
| `artifact_type` | Yes | One of: `file_set`, `structured_fields`, `message_draft`, `event_proposal`, `table_data`, `generic` |
| `typical_charge` | No | Typical credits per unit (T) |
| `unit_ceiling` | No | Worst-case credits per unit (M); platform hold cap |
| `input_composition` | No | Rich form definition for `/prepare` |

**Streaming agents** — add under the manifest root:

```yaml
capabilities:
  streaming: true
```

Validate before every deploy:

```bash
villow validate agent.yaml          # Python
villow-node validate agent.yaml     # Node
```

---

## 8. Run locally

Both SDKs include a **mock platform harness** for end-to-end local runs without Villow staging:

### Python

```python
from villow.testing import MockPlatformHarness
from hello_agent import HelloAgent

result = MockPlatformHarness(HelloAgent()).run_task(
    "hello_world",
    {"name": "Villow"},
)
print(result)
```

### Node

```typescript
import { MockPlatformHarness } from '@villow/sdk';
import { HelloAgent } from './hello-agent.js';

const result = await new MockPlatformHarness(new HelloAgent()).runTask('hello_world', { name: Villow });
console.log(result);
```

The SDK local server (`create_app` / `createApp`) implements the full `/v1/` surface with idempotent replay — use it behind ngrok or similar when running contract tests against your laptop.

---

## 9. Self-check before onboarding

Run the **contract test** against **your agent URL** (or ngrok tunnel) — **not** the Villow staging URL. This proves your server accepts signed Villow requests before we register you.

### Python

```bash
villow contract-test https://your-agent.example.com \
  --publisher-id YOUR_PUBLISHER_ID \
  --agent-id YOUR_AGENT_ID \
  --signing-key-id YOUR_KEY_ID \
  --secret YOUR_SECRET
```

Offline mode (signing + schemas only, no network):

```bash
villow contract-test https://localhost:8080 \
  --publisher-id YOUR_PUBLISHER_ID \
  --agent-id YOUR_AGENT_ID \
  --signing-key-id YOUR_KEY_ID \
  --secret YOUR_SECRET \
  --offline
```

### Node

```bash
villow-contract-test contract-test https://your-agent.example.com \
  --publisher-id YOUR_PUBLISHER_ID \
  --agent-id YOUR_AGENT_ID \
  --signing-key-id YOUR_KEY_ID \
  --secret YOUR_SECRET
```

**Pass criteria:** JSON report with `"passed": true` and green checks for:

- Signature verification
- Schema package available
- Signed `/discover` (when online)
- Idempotent replay
- Stale signature rejected
- Malformed `/prepare` rejected

Fix any `"passed": false` item using the `remediation` hint in the report before go-live.

---

## 10. Open-ended sessions

Villow sessions support **follow-up turns** in the same conversation. Your agent stays stateless; the platform replays context.

### Read on each unit

| Field | Python | Node | Purpose |
|-------|--------|------|---------|
| Session memory | `ctx.session_context` | `ctx.sessionContext` | Prior transcript, artifacts, refs |
| Continuation blob | `ctx.agent_state` | `ctx.agentState` | Your opaque state from the last unit |

### Write for the next unit

```python
# Python
ctx.set_agent_state({"cursor": "page-3", "processed_ids": ["a", "b"]})
```

```typescript
// Node
ctx.setAgentState({ cursor: 'page-3', processedIds: ['a', 'b'] });
```

Rules:

- Must be a **JSON object** (dict / plain object)
- Keep it **small** — platform enforces a size cap
- Platform stores it encrypted and replays it; it never interprets the contents

---

## 11. Streaming agents (recommended)

New agents should emit **AG-UI-aligned events** via the `Stream` API. The platform renders them in the live session UI.

### Python

```python
from villow import Stream

def run_turn(*, run_id: str | None = None) -> Stream:
    s = Stream(run_id)
    s.reasoning("Scanning 47 PDFs — 9 need OCR.")
    s.step("Reconciling statement 3 of 7")
    s.text("Here's your **March books-ready package**.")
    s.money_hold(typical=120, ceiling=180)
    s.table(
        columns=["merchant", "amount"],
        rows=[["ACME", "14302.11"]],
        title="March ledger",
    )
    s.require_approval(action="Write ledger.xlsx to Drive")
    s.money_settle(captured=118, hold=180, stats={"rows": 312})
    return s.finish()

# Stream to platform (SSE chunks):
# for chunk in run_turn().sse():
#     yield chunk

# Or return the full event list:
# events = run_turn().events()
```

### Node

```typescript
import { Stream } from '@villow/sdk';

function runTurn(runId?: string): Stream {
  const s = new Stream(runId);
  s.reasoning('Scanning 47 PDFs — 9 need OCR.');
  s.step('Reconciling statement 3 of 7');
  s.text("Here's your **March books-ready package**.");
  s.moneyHold({ typical: 120, ceiling: 180 });
  s.table({
    columns: ['merchant', 'amount'],
    rows: [['ACME', '14302.11']],
    title: 'March ledger',
  });
  s.requireApproval({ action: 'Write ledger.xlsx to Drive' });
  s.moneySettle({ captured: 118, hold: 180, stats: { rows: 312 } });
  return s.finish();
}

// SSE: for (const chunk of runTurn().sse()) { yield chunk; }
// Batch: const events = runTurn().events();
```

**Wire-format note:** SDK method names differ by language (snake_case vs camelCase), but **JSON field names on the wire are always snake_case** (`run_id`, `decide_for_me`, `typical_credits`, etc.). Python and Node produce identical wire output.

Set `capabilities.streaming: true` in your manifest.

---

## 12. Migrating existing callback-style agents

If you already use the rich `Context` API (`report_progress`, `stage_artifact`, `request_*_clarification`), you do **not** need to rewrite everything. Translate recorded emissions into a stream:

### Python

```python
from villow import events_to_stream

async def run(self, inputs, ctx):
    await ctx.report_progress({"event_type": "milestone", "milestone": {"label": "Parsing"}})
    await ctx.stage_artifact(Artifact.generic(payload={"done": True}))
    return events_to_stream(ctx.emitted_events)
```

### Node

```typescript
import { eventsToStream } from '@villow/sdk';

async run(inputs, ctx) {
  await ctx.reportProgress({ event_type: 'milestone', milestone: { label: 'Parsing' } });
  await ctx.stageArtifact(Artifact.generic({ payload: { done: true } }));
  return eventsToStream(ctx.emittedEvents);
}
```

**Non-streaming fallback:** wrap a single result:

```python
Stream.from_batch({"artifact": {...}})
```

```typescript
Stream.fromBatch({ artifact: { ... } })
```

---

## 13. Pricing and unit charges

Publishers declare per-unit pricing in the manifest:

```yaml
typical_charge: 120   # T — typical credits
unit_ceiling: 240     # M — worst-case hold (publisher-committed cap)
```

During execution, report running/final cost:

```python
from villow import ProgressEvent
await ctx.report_unit_charge(ProgressEvent.unit_charge(amount=120, currency="INR")["cost_telemetry"])
```

```typescript
import { ProgressEvent } from '@villow/sdk';
await ctx.reportUnitCharge(ProgressEvent.unitCharge({ amount: 120, currency: 'INR' }).cost_telemetry as Record<string, unknown>);
```

Platform capture never exceeds the user-authorized hold.

---

## 14. Platform rules (non-negotiable)

1. **Every clarification question must include `decide_for_me`** — the SDK enforces this when you use `Question` builders; streaming `clarify()` synthesizes a default if omitted.
2. **You never receive raw OAuth tokens** — only opaque `tool_access_grant` handles. Use `ctx.tools.*` helpers; they sign requests correctly.
3. **Writes require user approval** — stage artifacts with `stage_artifact` / `stageArtifact` or stream `require_approval` / `requireApproval`. Nothing writes to user accounts without explicit approval.
4. **Unknown wire fields are ignored** — the contract evolves additively within `/v1/`. Do not depend on undocumented platform behavior.

---

## 15. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `401` on all requests | Wrong secret or clock skew | Verify credentials; ensure server time is synced (NTP) |
| `409 idempotency_key_conflict` | Same idempotency key, different body | Use a fresh key per distinct operation |
| Signature fails cross-language | JSON re-serialization changed numbers | SDK signs exact bytes — do not round-trip JSON before signing |
| `every clarification question requires decide_for_me` | Missing fallback on a question | Add `decide_for_me` / `decideForMe` to every question |
| Streaming parts render as generic | Part schema mismatch | Use `Stream` helpers; run contract test; compare with golden events |
| Node `villow-node` not found | CLI not on PATH | Use `npx villow-node` or add `node_modules/.bin` to PATH |
| Python import error | Wrong Python version | Requires Python 3.13+ |

---

## Quick reference — CLI commands

| Task | Python | Node |
|------|--------|------|
| Validate manifest | `villow validate agent.yaml` | `villow-node validate agent.yaml` |
| Contract self-test | `villow contract-test <url> --publisher-id … --agent-id … --signing-key-id … --secret …` | `villow-contract-test contract-test <url> --publisher-id … --agent-id … --signing-key-id … --secret …` |

---

## Support

For onboarding credentials, category registration, and registering your agent URL on staging, contact **[support@villow.ai](mailto:support@villow.ai)** or your Villow partner channel.

**Staging web app for end-to-end testing:** https://worklane-staging.villow.ai

When reporting issues, include:

- SDK language and version (`0.1.0`)
- Output of the contract test JSON report
- Your `agent.yaml` (redact secrets)
- One failing request/response pair (redact secrets)
