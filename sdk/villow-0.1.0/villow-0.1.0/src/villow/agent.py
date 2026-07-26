from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin

import httpx

from villow.signing import sign_request


def task_template(slug: str):
    def decorator(func: Callable):
        setattr(func, "__villow_task_template__", slug)
        return func

    return decorator


def preview(slug: str):
    def decorator(func: Callable):
        setattr(func, "__villow_preview_template__", slug)
        return func

    return decorator


class Agent:
    def __init__(
        self,
        *,
        publisher_id: str = "publisher_local",
        agent_id: str = "agent_local",
        key_id: str = "key_local",
        secret: str = "local-secret",
        platform_base_url: str = "http://127.0.0.1:8000",
        transport: httpx.AsyncBaseTransport | httpx.BaseTransport | None = None,
    ) -> None:
        self.publisher_id = publisher_id
        self.agent_id = agent_id
        self.key_id = key_id
        self.secret = secret
        self.platform_base_url = platform_base_url.rstrip("/")
        self.transport = transport
        self.task_templates: dict[str, dict[str, str]] = {}
        self.prepare_handlers: dict[str, Callable[..., Any]] = {}
        self.run_handlers: dict[str, Callable[..., Any]] = {}
        self.preview_handlers: dict[str, Callable[..., Any]] = {}
        self._idempotency_store: dict[tuple[str, str], tuple[str, int, dict[str, Any]]] = {}
        self._answers_by_task: dict[str, dict[str, Any]] = {}
        self._delegated_by_task: dict[str, dict[str, bool]] = {}
        self._task_events: dict[str, list[dict[str, Any]]] = {}
        self._task_artifacts: dict[str, list[dict[str, Any]]] = {}
        self._task_states: dict[str, str] = {}
        # N1.5: last opaque continuation blob a handler returned, keyed by task (surfaced from /result).
        self._task_agent_state: dict[str, dict[str, Any]] = {}
        self._register_decorated_handlers()

    def context(self, **kwargs: Any):
        from villow.context import Context

        return Context(agent=self, **kwargs)

    def asgi_app(self):
        from villow.server import create_app

        return create_app(self)

    async def signed_platform_post(
        self,
        path_or_url: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        url = self._absolute_url(path_or_url)
        body = _json_body(payload)
        headers = sign_request(
            method="POST",
            path=httpx.URL(url).path,
            body=body,
            key_id=self.key_id,
            secret=self.secret,
            publisher_id=self.publisher_id,
            agent_id=self.agent_id,
            idempotency_key=idempotency_key,
        )
        headers["content-type"] = "application/json"
        async with httpx.AsyncClient(transport=self.transport, timeout=30) as client:
            response = await client.post(url, content=body, headers=headers)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()

    def _absolute_url(self, path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        return urljoin(f"{self.platform_base_url}/", path_or_url.lstrip("/"))

    def _register_decorated_handlers(self) -> None:
        for name in dir(self):
            member = getattr(self, name)
            if not callable(member):
                continue
            func = getattr(member, "__func__", member)
            slug = getattr(func, "__villow_task_template__", None)
            if slug:
                self.task_templates.setdefault(slug, {"slug": slug})
                if name == "prepare" or name.startswith("prepare_"):
                    self.prepare_handlers[slug] = member
                elif name in {"run", "execute"} or name.startswith("run_") or name.startswith("execute_"):
                    self.run_handlers[slug] = member
            preview_slug = getattr(func, "__villow_preview_template__", None)
            if preview_slug:
                self.task_templates.setdefault(preview_slug, {"slug": preview_slug})
                self.preview_handlers[preview_slug] = member


def _json_body(payload: dict[str, Any]) -> bytes:
    import json

    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
