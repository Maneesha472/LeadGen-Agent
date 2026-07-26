from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from villow.context import Context
from villow.signing import request_body_hash, verify_request_signature


def create_app(agent) -> FastAPI:
    app = FastAPI(title="Villow Publisher Agent", version="0.1.0")

    async def signed_endpoint(request: Request, handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]):
        body = await request.body()
        try:
            principal = verify_request_signature(
                method=request.method,
                path=request.url.path,
                body=body,
                headers=dict(request.headers),
                secret=agent.secret,
            )
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

        idem_key = (request.url.path, principal.idempotency_key)
        body_hash = request_body_hash(body)
        stored = agent._idempotency_store.get(idem_key)
        if stored:
            stored_hash, status_code, response_payload = stored
            if stored_hash != body_hash:
                raise HTTPException(status_code=409, detail="idempotency_key_conflict")
            return JSONResponse(
                status_code=status_code,
                content=response_payload,
                headers={"x-worklane-idempotent-replay": "true"},
            )

        payload = _parse_body(body)
        response_payload = await handler(payload)
        agent._idempotency_store[idem_key] = (body_hash, 200, response_payload)
        return JSONResponse(status_code=200, content=response_payload)

    @app.post("/discover")
    async def discover(request: Request):
        async def handle(_: dict[str, Any]) -> dict[str, Any]:
            templates = []
            for slug in sorted(agent.task_templates):
                templates.append(
                    {
                        "slug": slug,
                        "has_prepare": slug in agent.prepare_handlers,
                        "has_execute": slug in agent.run_handlers,
                        "has_preview": slug in agent.preview_handlers,
                    }
                )
            return {"publisher_id": agent.publisher_id, "agent_id": agent.agent_id, "task_templates": templates}

        return await signed_endpoint(request, handle)

    @app.post("/prepare")
    async def prepare(request: Request):
        async def handle(payload: dict[str, Any]) -> dict[str, Any]:
            task_template = _required(payload, "task_template")
            task_id = _required(payload, "task_id")
            handler = _handler(agent.prepare_handlers, task_template)
            ctx = _context(agent, payload, task_id=task_id, task_template=task_template, inputs=payload.get("initial_inputs") or {})
            result = await _maybe_await(handler(ctx.inputs, ctx))
            agent._task_states[task_id] = result.get("state", "preparing")
            return result

        return await signed_endpoint(request, handle)

    @app.post("/preview")
    async def preview(request: Request):
        async def handle(payload: dict[str, Any]) -> dict[str, Any]:
            task_template = _required(payload, "task_template")
            task_id = _required(payload, "task_id")
            ctx = _context(agent, payload, task_id=task_id, task_template=task_template, inputs=payload.get("current_inputs") or {})
            handler = agent.preview_handlers.get(task_template)
            if handler is None:
                preview_payload = {"type": "static", "value": "Preview unavailable in local SDK fallback"}
            else:
                preview_payload = await _maybe_await(handler(ctx.inputs, ctx))
            return {
                "task_id": task_id,
                "preview_session_id": payload.get("preview_session_id"),
                "primitive_id": payload.get("primitive_id"),
                "preview": preview_payload,
            }

        return await signed_endpoint(request, handle)

    @app.post("/execute")
    async def execute(request: Request):
        async def handle(payload: dict[str, Any]) -> dict[str, Any]:
            task_template = _required(payload, "task_template")
            task_id = _required(payload, "task_id")
            handler = _handler(agent.run_handlers, task_template)
            ctx = _context(agent, payload, task_id=task_id, task_template=task_template, inputs=payload.get("inputs") or {})
            result = await _maybe_await(handler(ctx.inputs, ctx))
            _record_context_events(agent, task_id, ctx)
            if not isinstance(result, dict):
                result = {"task_id": task_id, "accepted": True}
            result.setdefault("task_id", task_id)
            result.setdefault("accepted", True)
            # N1.5: round-trip the opaque continuation blob if the handler set one (the agent may
            # also place it on the result dict directly; an explicit set_agent_state wins).
            if ctx._next_agent_state is not None:
                result["agent_state"] = ctx._next_agent_state
            if isinstance(result.get("agent_state"), dict):
                agent._task_agent_state[task_id] = result["agent_state"]
            agent._task_states.setdefault(task_id, "executing")
            return result

        return await signed_endpoint(request, handle)

    @app.post("/clarification_response")
    async def clarification_response(request: Request):
        async def handle(payload: dict[str, Any]) -> dict[str, Any]:
            task_id = _required(payload, "task_id")
            answers = payload.get("answers") or {}
            delegated = payload.get("delegated_decisions") or {}
            agent._answers_by_task.setdefault(task_id, {}).update(answers)
            agent._delegated_by_task.setdefault(task_id, {}).update(delegated)
            agent._task_states[task_id] = "preparing" if payload.get("phase") == "pre_execution" else "executing"
            return {"task_id": task_id, "accepted": True, "next_state": agent._task_states[task_id]}

        return await signed_endpoint(request, handle)

    @app.post("/status")
    async def status(request: Request):
        async def handle(payload: dict[str, Any]) -> dict[str, Any]:
            task_id = _required(payload, "task_id")
            return {
                "task_id": task_id,
                "state": agent._task_states.get(task_id, "unknown"),
                "events": agent._task_events.get(task_id, []),
            }

        return await signed_endpoint(request, handle)

    @app.post("/cancel")
    async def cancel(request: Request):
        async def handle(payload: dict[str, Any]) -> dict[str, Any]:
            task_id = _required(payload, "task_id")
            agent._task_states[task_id] = "cancelled"
            return {"task_id": task_id, "cancelling": True}

        return await signed_endpoint(request, handle)

    @app.post("/result")
    async def result(request: Request):
        async def handle(payload: dict[str, Any]) -> dict[str, Any]:
            task_id = _required(payload, "task_id")
            response: dict[str, Any] = {
                "task_id": task_id,
                "state": agent._task_states.get(task_id, "unknown"),
                "artifacts": agent._task_artifacts.get(task_id, []),
            }
            # N1.5: surface the continuation blob from result too (see /execute).
            agent_state = agent._task_agent_state.get(task_id)
            if agent_state is not None:
                response["agent_state"] = agent_state
            return response

        return await signed_endpoint(request, handle)

    return app


def _parse_body(body: bytes) -> dict[str, Any]:
    if not body:
        return {}
    try:
        parsed = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="json_object_required")
    return parsed


def _context(agent, payload: dict[str, Any], *, task_id: str, task_template: str, inputs: dict[str, Any]) -> Context:
    return Context(
        agent=agent,
        task_id=task_id,
        task_template=task_template,
        inputs=inputs,
        answers=agent._answers_by_task.get(task_id, {}),
        delegated_decisions=agent._delegated_by_task.get(task_id, {}),
        tool_access_grants=payload.get("tool_access_grants") or [],
        callback_urls=payload.get("callback_urls") or {},
        sample_mode=bool(payload.get("sample_mode", False)),
        budget_cap=payload.get("budget_cap") or {},
        session_context=payload.get("session_context") or {},
        agent_state=payload.get("agent_state") or {},
    )


def _handler(handlers: dict[str, Callable[..., Any]], task_template: str) -> Callable[..., Any]:
    handler = handlers.get(task_template)
    if handler is None:
        raise HTTPException(status_code=404, detail=f"unknown_task_template:{task_template}")
    return handler


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _record_context_events(agent, task_id: str, ctx: Context) -> None:
    events = agent._task_events.setdefault(task_id, [])
    events.extend(ctx.emitted_events)
    for event in ctx.emitted_events:
        kind = event.get("kind")
        payload = event.get("payload", {})
        if kind == "artifact_staged":
            artifact = payload.get("artifact")
            if artifact:
                agent._task_artifacts.setdefault(task_id, []).append(artifact)
            agent._task_states[task_id] = "artifact_review"
        elif kind == "sample_complete":
            agent._task_states[task_id] = "sample_review"
        elif kind == "clarification_required":
            agent._task_states[task_id] = "clarification_required"
        elif kind == "status":
            agent._task_states.setdefault(task_id, payload.get("state", "executing"))


def _required(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not value:
        raise HTTPException(status_code=400, detail=f"{key}_required")
    return str(value)
