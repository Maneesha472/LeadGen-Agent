"""Streaming publisher examples (plan 11 Phase 6 / P6.4).

Two things publishers need:
  1. ``books_ready_stream`` — a hand-written streaming agent using the fluent ``Stream`` API.
  2. ``adapt_framework_run`` — a **framework adapter**: map a framework's native step output
     (LangGraph/CrewAI/your-own-loop emit step dicts) onto AG-UI events, one branch per step kind.
     Unknown kinds are ignored, so the adapter is forward-compatible.

Both return a ``Stream``; the publisher does ``for chunk in stream.sse(): yield chunk`` to stream to
the platform, or ``stream.events()`` for the batch/non-streaming path.
"""

from __future__ import annotations

from typing import Any

from villow import Stream


def books_ready_stream(*, run_id: str | None = None) -> Stream:
    """A realistic books-ready monthly-package run, emitted as AG-UI events."""

    s = Stream(run_id)
    s.reasoning("I see 47 PDFs — 9 are scans (I'll OCR those) and 3 look like April duplicates.")
    s.step("Reconciling statement 3 of 7")
    s.text("Here's your **March books-ready package**. Totals tie out; 2 transactions need your eye.")
    s.money_hold(typical=120, ceiling=180)
    s.table(
        columns=["merchant", "category", "amount"],
        rows=[["Amazon Web Services", "Software", "4210.00"], ["Gusto", "Payroll", "1749.36"]],
        title="March ledger (QBO import format)",
        reconciliation={"label": "Totals reconcile to your statements", "expected": "14302.11", "actual": "14302.11", "ok": True},
        exceptions=[{"id": "e1", "message": "2 receipts have no matching statement line", "evidence": "receipt-041.pdf, receipt-042.pdf"}],
    )
    s.clarify(
        question="2 receipts have no matching statement line. Fold them in, or flag them?",
        options=[{"id": "fold", "label": "Fold them in"}, {"id": "flag", "label": "Flag for review"}],
    )
    s.require_approval(action="Write March-ledger.xlsx to your Google Drive", summary="Nothing is written until you approve.")
    s.money_settle(captured=118, hold=180, stats={"transactions categorized": 312, "statements reconciled": 2})
    return s.finish()


def adapt_framework_run(framework_steps: list[dict[str, Any]], *, run_id: str | None = None) -> Stream:
    """Adapt a framework's native step output into AG-UI events.

    ``framework_steps`` is whatever your framework emits, normalized to ``{"kind": ..., ...}``. The
    mapping below is the shape you'd write in a real LangGraph/CrewAI adapter — one branch per kind.
    """

    s = Stream(run_id)
    for step in framework_steps:
        kind = step.get("kind")
        if kind == "thought":
            s.reasoning(str(step.get("text", "")))
        elif kind == "message":
            s.text(str(step.get("text", "")))
        elif kind == "tool_start":
            s.step(f"Calling {step.get('name', 'tool')}")
        elif kind == "table":
            s.table(columns=step.get("columns", []), rows=step.get("rows", []),
                    title=step.get("title"), reconciliation=step.get("reconciliation"))
        elif kind == "ask":
            s.clarify(question=str(step.get("question", "")), options=step.get("options"))
        elif kind == "write":
            s.require_approval(action=str(step.get("action", "")))
        elif kind == "cost":
            s.money_settle(captured=int(step.get("captured_credits", 0)))
        # any other kind is ignored — forward-compatible with framework changes
    return s.finish()


if __name__ == "__main__":  # pragma: no cover - manual demo
    for chunk in books_ready_stream(run_id="demo").sse():
        print(chunk, end="")
