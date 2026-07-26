from __future__ import annotations

import json
import time
from typing import Any

from fastapi.testclient import TestClient

from villow.signing import sign_request


class MockPlatformHarness:
    def __init__(
        self,
        agent,
        *,
        render_mode: str = "rich",
        key_id: str = "key_local",
        publisher_id: str = "publisher_local",
        agent_id: str = "agent_local",
        secret: str = "local-secret",
    ) -> None:
        self.agent = agent
        self.render_mode = render_mode
        self.key_id = key_id
        self.publisher_id = publisher_id
        self.agent_id = agent_id
        self.secret = secret
        self.client = TestClient(agent.asgi_app())
        self._counter = 0

    def run_task(
        self,
        task_template: str,
        inputs: dict[str, Any],
        *,
        answers: dict[str, Any] | None = None,
        delegated_decisions: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        task_id = f"task_{int(time.time() * 1000)}"
        self.post("/discover", {})
        prepare = self.post("/prepare", {"task_id": task_id, "task_template": task_template, "initial_inputs": inputs})
        composition_response = prepare.get("composition_response")

        if prepare.get("state") == "clarification_required":
            resolved_answers = answers or _answers_from_decide_for_me(prepare["questions"])
            self.post(
                "/clarification_response",
                {
                    "task_id": task_id,
                    "clarification_id": prepare["clarification_id"],
                    "phase": prepare["phase"],
                    "answers": resolved_answers,
                    "delegated_decisions": delegated_decisions or {},
                },
            )
            prepare = self.post("/prepare", {"task_id": task_id, "task_template": task_template, "initial_inputs": inputs})
            composition_response = prepare.get("composition_response") or composition_response

        self.post(
            "/execute",
            {
                "task_id": task_id,
                "task_template": task_template,
                "inputs": prepare.get("normalized_inputs", inputs),
                "tool_access_grants": [],
                "callback_urls": {},
                "sample_mode": False,
            },
        )
        result = self.post("/result", {"task_id": task_id})
        result["state"] = "completed" if result.get("artifacts") else result.get("state", "completed")
        if composition_response:
            result["composition_response"] = composition_response
            if self.render_mode == "simple":
                result["simple_fallback_slots"] = composition_response.get("fallback_slots", [])
        return result

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._counter += 1
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        headers = sign_request(
            method="POST",
            path=path,
            body=body,
            key_id=self.key_id,
            secret=self.secret,
            publisher_id=self.publisher_id,
            agent_id=self.agent_id,
            timestamp=int(time.time()),
            nonce=f"harness_{self._counter}",
            idempotency_key=f"harness_{self._counter}",
        )
        headers["content-type"] = "application/json"
        response = self.client.post(path, content=body, headers=headers)
        response.raise_for_status()
        return response.json()


def _answers_from_decide_for_me(questions: list[dict[str, Any]]) -> dict[str, Any]:
    answers: dict[str, Any] = {}
    for question in questions:
        decision = question.get("decide_for_me") or {}
        if "value" in decision:
            answers[question["id"]] = decision["value"]
        elif question.get("default_value") is not None:
            answers[question["id"]] = question["default_value"]
        else:
            answers[question["id"]] = None
    return answers
