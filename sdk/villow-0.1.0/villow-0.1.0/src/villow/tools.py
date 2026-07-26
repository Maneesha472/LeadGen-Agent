from __future__ import annotations

from typing import Any


class Tools:
    def __init__(self, context) -> None:
        self.drive = DriveTools(context)
        self.fs = FilesystemTools(context)
        self.http = HttpTools(context)
        self.mail = MailTools(context)
        self.calendar = CalendarTools(context)


class BaseToolClient:
    def __init__(self, context) -> None:
        self.context = context

    async def _call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        idempotency_key = self.context._idempotency_key(f"tool:{tool_name}")
        payload: dict[str, Any] = {
            "task_id": self.context.task_id,
            "agent_id": self.context.agent.agent_id,
            "args": args,
            "idempotency_key": idempotency_key,
        }
        grant_id = self.context.resolve_tool_access_grant(tool_name)
        if grant_id:
            payload["tool_access_grant_id"] = grant_id
        response = await self.context.agent.signed_platform_post(
            f"/v1/tools/{tool_name}",
            payload,
            idempotency_key=idempotency_key,
        )
        return _unwrap_tool_response(response)


def _unwrap_tool_response(response: dict[str, Any]) -> dict[str, Any]:
    """Unwrap the tool proxy's ToolCallResponse envelope into the tool result itself.

    The proxy answers ``{"tool_name", "task_id", "status", "result": {...}, "artifact_id"}``,
    but the SDK dialect hands publishers the result payload directly (``entries``/``files``/
    ``content`` at the top level). Returning the raw envelope silently broke every agent that
    read ``listing["entries"]`` — the read found nothing and batches "succeeded" empty.
    Staged-write metadata (non-success ``status``, ``artifact_id``) is carried into the
    unwrapped payload so stage-and-approve flows keep working.
    """

    if not isinstance(response, dict) or "result" not in response:
        return response
    result = response.get("result")
    result = dict(result) if isinstance(result, dict) else {}
    status = response.get("status")
    if status and status != "success":
        result.setdefault("status", str(status))
    if response.get("artifact_id"):
        result.setdefault("artifact_id", str(response["artifact_id"]))
    return result


class DriveTools(BaseToolClient):
    async def list_files(self, *, folder_id: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._call("drive.list_files", {"folder_id": folder_id, "filters": filters or {}})

    async def read_file(self, *, file_id: str) -> dict[str, Any]:
        return await self._call("drive.read_file", {"file_id": file_id})

    async def create_file(
        self,
        *,
        folder_id: str,
        name: str,
        mime_type: str,
        content: str | None = None,
        content_ref: str | None = None,
    ) -> dict[str, Any]:
        return await self._call(
            "drive.create_file",
            {
                "folder_id": folder_id,
                "name": name,
                "content": content if content is not None else (content_ref or ""),
                "mime_type": mime_type,
            },
        )


class FilesystemTools(BaseToolClient):
    async def write(
        self,
        *,
        path: str,
        content: str | None = None,
        content_ref: str | None = None,
        content_b64: str | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"path": path}
        if content_b64 is not None:
            args["content_b64"] = content_b64
        elif content is not None:
            args["content"] = content
        elif content_ref is not None:
            args["content"] = content_ref
        else:
            args["content"] = ""
        return await self._call("fs.write", args)

    async def read(self, *, path: str, encoding: str | None = None) -> dict[str, Any]:
        args: dict[str, Any] = {"path": path}
        if encoding:
            args["encoding"] = encoding
        return await self._call("fs.read", args)

    async def list(self, *, path: str = ".") -> dict[str, Any]:
        """List workspace entries at ``path`` → ``{"path": ..., "entries": [name, ...]}``."""

        return await self._call("fs.list", {"path": path})


class HttpTools(BaseToolClient):
    async def get(self, *, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        return await self._call("http.get", {"url": url, "headers": headers or {}})

    async def post(self, *, url: str, json: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        return await self._call("http.post", {"url": url, "json": json, "headers": headers or {}})


class MailTools(BaseToolClient):
    async def read_thread(self, *, thread_id: str) -> dict[str, Any]:
        return await self._call("mail.read_thread", {"thread_id": thread_id})


class CalendarTools(BaseToolClient):
    async def list_events(self, *, calendar_id: str, time_min: str, time_max: str) -> dict[str, Any]:
        return await self._call(
            "calendar.list_events",
            {"calendar_id": calendar_id, "time_min": time_min, "time_max": time_max},
        )
