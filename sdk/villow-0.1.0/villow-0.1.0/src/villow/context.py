from __future__ import annotations

from typing import Any
from uuid import uuid4

from villow.tools import Tools


class Context:
    def __init__(
        self,
        *,
        agent,
        task_id: str,
        task_template: str,
        inputs: dict[str, Any],
        answers: dict[str, Any] | None = None,
        delegated_decisions: dict[str, bool] | None = None,
        tool_access_grants: list[dict[str, Any] | str] | None = None,
        callback_urls: dict[str, str] | None = None,
        sample_mode: bool = False,
        budget_cap: dict[str, Any] | None = None,
        session_context: dict[str, Any] | None = None,
        agent_state: dict[str, Any] | None = None,
    ) -> None:
        self.agent = agent
        self.task_id = task_id
        self.task_template = task_template
        self.inputs = inputs
        self.answers = answers or {}
        self.delegated_decisions = delegated_decisions or {}
        self.tool_access_grants = tool_access_grants or []
        self.callback_urls = callback_urls or {}
        self.sample_mode = sample_mode
        self.budget_cap = budget_cap or {}
        # M6: platform-replayed session memory for follow-up units. Empty for a fresh task.
        # The publisher stays stateless — read prior transcript/artifacts from here.
        self.session_context = session_context or {}
        # N1.5: the platform replays the opaque continuation blob this agent returned on a prior
        # unit (empty for a fresh session). The platform stores/replays it but never interprets it;
        # call set_agent_state(...) to update it for the next unit.
        self.agent_state = agent_state or {}
        self._next_agent_state: dict[str, Any] | None = None
        self.emitted_events: list[dict[str, Any]] = []
        self.tools = Tools(self)

    def set_agent_state(self, state: dict[str, Any]) -> None:
        """Set the opaque continuation blob to return from this execute/result.

        The platform stores it (session-scoped, encrypted, size-capped) and replays it as
        ``ctx.agent_state`` on the next unit. Must be a JSON object; keep it small.
        """

        if not isinstance(state, dict):
            raise ValueError("agent_state must be a JSON object (dict)")
        self._next_agent_state = state

    def has_answer(self, question_id: str) -> bool:
        return question_id in self.answers

    def answer(self, question_id: str, default: Any = None) -> Any:
        return self.answers.get(question_id, default)

    def was_delegated(self, question_id: str) -> bool:
        return bool(self.delegated_decisions.get(question_id))

    def ready_to_authorize(
        self,
        *,
        normalized_inputs: dict[str, Any],
        composition_response: dict[str, Any] | None = None,
        price_units: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "task_id": self.task_id,
            "state": "ready_to_authorize",
            "normalized_inputs": normalized_inputs,
            "price_units": price_units or {},
        }
        if composition_response is not None:
            payload["composition_response"] = composition_response
        return payload

    def request_clarification(
        self,
        questions: list[dict[str, Any]],
        *,
        composition_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _validate_questions(questions)
        payload: dict[str, Any] = {
            "task_id": self.task_id,
            "state": "clarification_required",
            "phase": "pre_execution",
            "clarification_id": f"clarification_{uuid4().hex}",
            "questions": questions,
        }
        if composition_response is not None:
            payload["composition_response"] = composition_response
        return payload

    async def request_mid_execution_clarification(self, questions: list[dict[str, Any]]) -> dict[str, Any]:
        _validate_questions(questions)
        payload = {
            "task_id": self.task_id,
            "state": "clarification_required",
            "phase": "mid_execution",
            "clarification_id": f"clarification_{uuid4().hex}",
            "questions": questions,
        }
        return await self._emit_callback("clarification_required", payload)

    async def report_progress(self, event: dict[str, Any] | None = None, **progress: Any) -> dict[str, Any]:
        payload = {
            "task_id": self.task_id,
            "state": "executing",
            "progress": event or progress,
        }
        return await self._emit_callback("status", payload)

    async def report_sample_complete(self, sample_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {"task_id": self.task_id, "state": "sample_review", "sample_artifacts": sample_artifacts}
        return await self._emit_callback("sample_complete", payload)

    async def stage_artifact(self, artifact: dict[str, Any]) -> dict[str, Any]:
        payload = {"task_id": self.task_id, "state": "artifact_review", "artifact": artifact}
        return await self._emit_callback("artifact_staged", payload)

    async def report_unit_charge(self, unit_charge: dict[str, Any]) -> dict[str, Any]:
        payload = {"task_id": self.task_id, "state": "executing", "cost_telemetry": unit_charge}
        return await self._emit_callback("status", payload)

    async def report_cost_telemetry(self, cost_telemetry: dict[str, Any]) -> dict[str, Any]:
        """Deprecated compatibility alias for report_unit_charge."""

        return await self.report_unit_charge(cost_telemetry)

    def resolve_tool_access_grant(self, tool_name: str) -> str | None:
        if not self.tool_access_grants:
            return None
        prefix = f"{tool_name.split('.', 1)[0]}." if "." in tool_name else tool_name
        for grant in self.tool_access_grants:
            if isinstance(grant, str):
                return grant
            grant_tool = str(grant.get("tool_name") or "")
            grant_id = grant.get("tool_access_grant_id") or grant.get("grant_id") or grant.get("id")
            if grant_tool == tool_name and grant_id:
                return str(grant_id)
        for grant in self.tool_access_grants:
            if isinstance(grant, dict):
                grant_tool = str(grant.get("tool_name") or "")
                grant_id = grant.get("tool_access_grant_id") or grant.get("grant_id") or grant.get("id")
                if grant_tool.startswith(prefix) and grant_id:
                    return str(grant_id)
        legacy_ids: list[str] = []
        for grant in self.tool_access_grants:
            if isinstance(grant, dict):
                grant_id = grant.get("tool_access_grant_id") or grant.get("grant_id") or grant.get("id")
                if grant_id and not grant.get("tool_name"):
                    legacy_ids.append(str(grant_id))
        if len(legacy_ids) == 1:
            return legacy_ids[0]
        return None

    async def _emit_callback(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.emitted_events.append({"kind": kind, "payload": payload})
        url = self.callback_urls.get(kind)
        if not url:
            return {"accepted": True, "local": True}
        return await self.agent.signed_platform_post(url, payload, idempotency_key=self._idempotency_key(kind))

    def _idempotency_key(self, operation: str) -> str:
        return f"{self.task_id}:{operation}:{uuid4().hex}"


def _validate_questions(questions: list[dict[str, Any]]) -> None:
    for question in questions:
        if "decide_for_me" not in question or question["decide_for_me"] is None:
            raise ValueError("every clarification question requires decide_for_me")
