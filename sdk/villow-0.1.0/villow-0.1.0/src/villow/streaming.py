"""AG-UI-aligned streaming emit API for publisher agents (D-104, plan 11 Phase 6).

A publisher builds one turn's event stream with a fluent ``Stream`` and either streams it (``sse()``)
or hands the platform the event list (``events()``). The emitted events match the platform's canonical
contract (``apps/api/worklane_api/streaming/{events,parts}.py``) — same event-type names and part
schemas — so the platform ingests them with no translation. Publishers supply DATA; the platform owns
rendering (closed registry, D-106).

    s = Stream()
    s.reasoning("I see 47 PDFs — 9 are scans, 3 look like April duplicates.")
    s.text("Here's your **March books-ready package**.")
    s.table(columns=["merchant", "amount"], rows=[["ACME", "14302.11"]],
            reconciliation={"label": "Totals", "expected": "14302.11", "actual": "14302.11", "ok": True})
    s.require_approval(action="Write March-ledger.xlsx to your Drive")
    for chunk in s.sse():
        yield chunk

Non-streaming publishers can use ``Stream.from_batch(result)`` to turn a single result into a stream.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Iterable

# Event-type constants (mirror worklane_api.streaming.events.EventType).
RUN_STARTED = "RUN_STARTED"
RUN_FINISHED = "RUN_FINISHED"
RUN_ERROR = "RUN_ERROR"
STEP_STARTED = "STEP_STARTED"
TEXT_MESSAGE_CHUNK = "TEXT_MESSAGE_CHUNK"
PART = "PART"
ARTIFACT_STAGED = "ARTIFACT_STAGED"
APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
BUDGET_HOLD = "BUDGET_HOLD"
COST_UPDATE = "COST_UPDATE"
BUDGET_SETTLE = "BUDGET_SETTLE"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _nonce() -> str:
    return uuid.uuid4().hex


def table_part(
    columns: list[Any],
    rows: list[Any],
    *,
    title: str | None = None,
    reconciliation: dict[str, Any] | None = None,
    exceptions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a ``table_data`` part from friendly inputs (columns as names or {key,label,type})."""

    cols: list[dict[str, Any]] = []
    keys: list[str] = []
    for col in columns:
        if isinstance(col, dict):
            key = str(col.get("key") or col.get("label"))
            cols.append({"key": key, "label": col.get("label") or key, "type": col.get("type", "string")})
        else:
            key = str(col)
            cols.append({"key": key, "label": key})
        keys.append(key)
    out_rows: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out_rows.append(row)
        elif isinstance(row, (list, tuple)):
            out_rows.append({(keys[i] if i < len(keys) else f"c{i}"): v for i, v in enumerate(row)})
        else:
            out_rows.append({"value": row})
    part: dict[str, Any] = {"type": "table_data", "columns": cols, "rows": out_rows}
    if title:
        part["title"] = title
    if reconciliation is not None:
        part["reconciliation"] = reconciliation
    if exceptions:
        part["exceptions"] = exceptions
    return part


def artifact_to_part(artifact: dict[str, Any]) -> dict[str, Any]:
    """Map a legacy typed-artifact dict ({artifact_type, title, type_payload}) onto a part."""

    atype = artifact.get("artifact_type") or artifact.get("type")
    payload = artifact.get("type_payload") or artifact.get("payload") or {}
    title = artifact.get("title")
    if atype == "table_data":
        return table_part(payload.get("columns") or [], payload.get("rows") or [], title=title,
                          reconciliation=payload.get("reconciliation"), exceptions=payload.get("exceptions"))
    if atype == "structured_fields":
        # The legacy artifact uses a dict of fields; the streaming part wants a list of {label, value}.
        fields = payload.get("fields")
        if isinstance(fields, dict):
            fields = [{"label": str(k), "value": v} for k, v in fields.items()]
        return {"type": "structured_fields", "fields": fields or []}
    if atype in {"file_set", "message_draft", "event_proposal"}:
        part = {"type": atype, **payload}
        if title and atype == "file_set":
            part["title"] = title
        return part
    return {"type": "generic", "data": {"artifact_type": atype, "title": title, **payload}, "original_type": atype}


def _progress_label(progress: dict[str, Any]) -> str | None:
    event_type = progress.get("event_type")
    if event_type == "milestone":
        milestone = progress.get("milestone") or {}
        return milestone.get("label") or milestone.get("id")
    if event_type == "item_completed":
        item = progress.get("item") or {}
        counts = progress.get("progress") or {}
        name = item.get("display_name") or item.get("item_id") or "item"
        if counts.get("total"):
            return f"{name} ({counts.get('current')}/{counts.get('total')})"
        return name
    return progress.get("label")


def _options_to_parts(options: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for opt in options or []:
        out.append(opt if isinstance(opt, dict) else {"id": str(opt), "label": str(opt)})
    return out


def events_to_stream(emitted_events: list[dict[str, Any]], *, run_id: str | None = None) -> "Stream":
    """Adapt a publisher agent's SDK emissions into a canonical AG-UI Stream (plan 11 Phase 7).

    The migration path for existing SDK agents: they keep their rich ``ctx`` API (``report_progress`` /
    ``request_*_clarification`` / ``stage_artifact``) and this translates the recorded ``ctx.emitted_events``
    (``[{"kind", "payload"}]``) into the streaming contract — progress→step, clarification→clarify (with
    its decide_for_me preserved, rule #4), staged artifact→stage_artifact. Cost telemetry is billing
    input, not a renderable part, so it is intentionally not turned into a money part here.
    """

    stream = Stream(run_id)
    for event in emitted_events:
        kind = event.get("kind")
        payload = event.get("payload") or {}
        if kind == "status":
            progress = payload.get("progress")
            if isinstance(progress, dict):
                label = _progress_label(progress)
                if label:
                    stream.step(str(label))
        elif kind == "clarification_required":
            for question in payload.get("questions") or []:
                stream.clarify(
                    question=str(question.get("label") or question.get("question") or ""),
                    options=_options_to_parts(question.get("options")),
                    decide_for_me=question.get("decide_for_me"),
                    clarification_id=question.get("id"),
                )
        elif kind == "artifact_staged":
            artifact = payload.get("artifact")
            if artifact:
                stream.stage_artifact(artifact_to_part(artifact))
        elif kind == "sample_complete":
            for sample in payload.get("sample_artifacts") or []:
                stream.stage_artifact(artifact_to_part(sample))
    return stream.finish()


class Stream:
    """Builds one turn's canonical event stream. Auto-wraps RUN_STARTED/RUN_FINISHED."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = run_id or uuid.uuid4().hex
        self._events: list[dict[str, Any]] = []
        self._seq = 0
        self._started = False
        self._finished = False

    def _push(self, event_type: str, *, part: dict[str, Any] | None = None, data: dict[str, Any] | None = None) -> "Stream":
        event: dict[str, Any] = {"type": event_type, "seq": self._seq, "run_id": self.run_id, "ts": _now_ms(), "nonce": _nonce()}
        if part is not None:
            event["part"] = part
        event["data"] = data or {}
        self._events.append(event)
        self._seq += 1
        return self

    def _emit(self, event_type: str, *, part: dict[str, Any] | None = None, data: dict[str, Any] | None = None) -> "Stream":
        if not self._started:
            self._push(RUN_STARTED)
            self._started = True
        return self._push(event_type, part=part, data=data)

    # ----------------------------------------------------------------- content
    def reasoning(self, text: str) -> "Stream":
        return self._emit(PART, part={"type": "reasoning", "text": text})

    def text(self, text: str, *, role: str | None = None) -> "Stream":
        if role:
            return self._emit(TEXT_MESSAGE_CHUNK, data={"text": text, "role": role})
        return self._emit(PART, part={"type": "text", "text": text})

    def step(self, label: str) -> "Stream":
        return self._emit(STEP_STARTED, data={"name": label})

    def code(self, source: str, *, language: str | None = None, filename: str | None = None) -> "Stream":
        part: dict[str, Any] = {"type": "code", "source": source}
        if language:
            part["language"] = language
        if filename:
            part["filename"] = filename
        return self._emit(PART, part=part)

    def table(self, *, columns: list[Any], rows: list[Any], title: str | None = None,
              reconciliation: dict[str, Any] | None = None, exceptions: list[dict[str, Any]] | None = None) -> "Stream":
        return self._emit(ARTIFACT_STAGED, part=table_part(columns, rows, title=title, reconciliation=reconciliation, exceptions=exceptions))

    def file(self, *, id: str, name: str, mime: str, url: str, size_bytes: int | None = None) -> "Stream":
        ref: dict[str, Any] = {"id": id, "name": name, "mime": mime, "url": url}
        if size_bytes is not None:
            ref["size_bytes"] = size_bytes
        return self._emit(PART, part={"type": "file", "file": ref})

    def file_set(self, *, files: list[dict[str, Any]], title: str | None = None) -> "Stream":
        part: dict[str, Any] = {"type": "file_set", "files": files}
        if title:
            part["title"] = title
        return self._emit(ARTIFACT_STAGED, part=part)

    def stage_artifact(self, part: dict[str, Any]) -> "Stream":
        return self._emit(ARTIFACT_STAGED, part=part)

    # ----------------------------------------------------------------- trust
    def require_approval(self, *, action: str, summary: str | None = None, diff: dict[str, Any] | None = None,
                         target: dict[str, Any] | None = None, approval_id: str | None = None) -> "Stream":
        part: dict[str, Any] = {"type": "approval", "approval_id": approval_id or uuid.uuid4().hex, "action": action, "requires_approval": True}
        if summary:
            part["summary"] = summary
        if diff is not None:
            part["diff"] = diff
        if target is not None:
            part["target"] = target
        return self._emit(APPROVAL_REQUIRED, part=part)

    def clarify(self, *, question: str, options: list[dict[str, Any]] | None = None,
                decide_for_me: dict[str, Any] | None = None, allow_free_text: bool = False,
                clarification_id: str | None = None) -> "Stream":
        part: dict[str, Any] = {
            "type": "clarification",
            "clarification_id": clarification_id or uuid.uuid4().hex,
            "question": question,
            "options": options or [],
            "allow_free_text": allow_free_text,
            # rule #4: a clarification always carries a decide-for-me fallback.
            "decide_for_me": decide_for_me or {"label": "Decide for me"},
        }
        return self._emit(CLARIFICATION_REQUIRED, part=part)

    # ----------------------------------------------------------------- money
    def money_hold(self, *, typical: int | None = None, ceiling: int | None = None, hold: int | None = None) -> "Stream":
        part: dict[str, Any] = {"type": "money", "kind": "hold"}
        if typical is not None:
            part["typical_credits"] = typical
        if ceiling is not None:
            part["ceiling_credits"] = ceiling
        if hold is not None:
            part["hold_credits"] = hold
        return self._emit(BUDGET_HOLD, part=part)

    def money_settle(self, *, captured: int, hold: int | None = None, stats: dict[str, Any] | None = None) -> "Stream":
        part: dict[str, Any] = {"type": "money", "kind": "settle", "captured_credits": captured}
        if hold is not None:
            part["hold_credits"] = hold
        if stats is not None:
            part["stats"] = stats
        return self._emit(BUDGET_SETTLE, part=part)

    # ----------------------------------------------------------------- lifecycle
    def finish(self) -> "Stream":
        if not self._started:
            self._push(RUN_STARTED)
            self._started = True
        if not self._finished:
            self._push(RUN_FINISHED)
            self._finished = True
        return self

    def error(self, message: str) -> "Stream":
        if not self._started:
            self._push(RUN_STARTED)
            self._started = True
        if not self._finished:
            self._push(RUN_ERROR, data={"message": message})
            self._finished = True
        return self

    def events(self) -> list[dict[str, Any]]:
        if not self._finished:
            self.finish()
        return list(self._events)

    def sse(self) -> Iterable[str]:
        for event in self.events():
            yield f"id: {event['seq']}\nevent: {event['type']}\ndata: {json.dumps(event, separators=(',', ':'))}\n\n"

    @classmethod
    def from_batch(cls, result: Any, run_id: str | None = None) -> "Stream":
        """Batch→stream fallback (P6.3): a non-streaming publisher's single result → a part stream."""

        stream = cls(run_id)
        if isinstance(result, dict) and isinstance(result.get("parts"), list):
            parts = list(result["parts"])
        elif isinstance(result, dict) and result.get("artifact"):
            parts = [artifact_to_part(result["artifact"])]
        elif isinstance(result, dict) and isinstance(result.get("artifacts"), list):
            parts = [artifact_to_part(a) for a in result["artifacts"]]
        elif isinstance(result, dict):
            parts = [{"type": "generic", "data": dict(result)}]
        else:
            parts = [{"type": "generic", "data": {"value": result}}]
        for part in parts:
            stream.stage_artifact(part)
        return stream.finish()
