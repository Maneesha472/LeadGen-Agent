from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ContractValidationError:
    field_path: str
    message: str
    expected: str | None = None
    received: str | None = None


@dataclass(frozen=True)
class ContractValidationResult:
    valid: bool
    errors: list[ContractValidationError]


def _object(required: list[str] | None = None, properties: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"type": "object", "required": required or [], "properties": properties or {}, "additionalProperties": True}


def _array(items: dict[str, Any] | None = None, max_items: int | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "array"}
    if items is not None:
        schema["items"] = items
    if max_items is not None:
        schema["maxItems"] = max_items
    return schema


OBJECT = _object()

CONTRACT_SCHEMAS: dict[str, dict[str, Any]] = {
    "request.discover": _object(),
    "response.discover": _object(["publisher_id", "agent_id"], {"publisher_id": {"type": "string"}, "agent_id": {"type": "string"}}),
    "request.prepare": _object(["task_id", "task_template"], {"task_id": {"type": "string"}, "task_template": {"type": "string"}, "initial_inputs": OBJECT, "session_context": OBJECT, "agent_state": OBJECT}),
    "response.prepare": _object(["task_id", "state"], {"task_id": {"type": "string"}, "state": {"type": "string"}, "composition_response": OBJECT}),
    "request.preview": _object(["task_id", "task_template"], {"task_id": {"type": "string"}, "task_template": {"type": "string"}, "current_inputs": OBJECT}),
    "response.preview": _object(["task_id", "preview"], {"task_id": {"type": "string"}, "preview": OBJECT}),
    "request.execute": _object(["task_id", "task_template"], {"task_id": {"type": "string"}, "task_template": {"type": "string"}, "inputs": OBJECT, "callback_urls": OBJECT, "session_context": OBJECT, "agent_state": OBJECT}),
    "response.execute": _object(["task_id"], {"task_id": {"type": "string"}, "accepted": {"type": "boolean"}, "agent_state": OBJECT}),
    "request.clarification_response": _object(["task_id", "clarification_id", "phase"], {"task_id": {"type": "string"}, "clarification_id": {"type": "string"}, "phase": {"type": "string"}, "answers": OBJECT}),
    "response.clarification_response": _object(["task_id", "accepted"], {"task_id": {"type": "string"}, "accepted": {"type": "boolean"}}),
    "request.status": _object(["task_id"], {"task_id": {"type": "string"}}),
    "response.status": _object(["task_id", "state"], {"task_id": {"type": "string"}, "state": {"type": "string"}}),
    "request.cancel": _object(["task_id"], {"task_id": {"type": "string"}}),
    "response.cancel": _object(["task_id"], {"task_id": {"type": "string"}, "cancelling": {"type": "boolean"}}),
    "request.result": _object(["task_id"], {"task_id": {"type": "string"}}),
    "response.result": _object(["task_id", "state"], {"task_id": {"type": "string"}, "state": {"type": "string"}, "artifacts": _array(), "agent_state": OBJECT}),
    "callback.status": _object(["task_id"], {"task_id": {"type": "string"}, "state": {"type": "string"}, "progress": OBJECT, "messages": _array()}),
    "callback.progress": _object(["task_id"], {"task_id": {"type": "string"}, "progress": OBJECT, "messages": _array()}),
    "callback.progress_batch": _object(["events"], {"events": _array(_object(["task_id"], {"task_id": {"type": "string"}, "progress": OBJECT}), 100)}),
    "callback.clarification_required": _object(["task_id"], {"task_id": {"type": "string"}, "phase": {"type": "string"}, "questions": _array()}),
    "callback.sample_complete": _object(["task_id"], {"task_id": {"type": "string"}, "sample_artifact": OBJECT}),
    "callback.artifact_staged": _object(["task_id"], {"task_id": {"type": "string"}, "artifact": OBJECT}),
    "callback.error": _object(["task_id"], {"task_id": {"type": "string"}, "message": {"type": "string"}}),
}


def validate_contract_message(kind: str, payload: Any) -> ContractValidationResult:
    schema = CONTRACT_SCHEMAS.get(kind)
    if schema is None:
        return ContractValidationResult(False, [ContractValidationError("", "unknown contract message kind", received=kind)])
    errors: list[ContractValidationError] = []
    _validate(schema, payload, "", errors)
    return ContractValidationResult(not errors, errors)


def _validate(schema: dict[str, Any], value: Any, path: str, errors: list[ContractValidationError]) -> None:
    expected = schema.get("type")
    if expected and not _matches(value, str(expected)):
        errors.append(ContractValidationError(path, f"expected {expected}", str(expected), _received(value)))
        return
    if expected == "object":
        properties = schema.get("properties", {})
        for field in schema.get("required", []):
            if field not in value:
                errors.append(ContractValidationError(_path(path, field), "required field missing", _expected(properties.get(field, {})), "missing"))
        for field, field_schema in properties.items():
            if field in value:
                _validate(field_schema, value[field], _path(path, field), errors)
    if expected == "array":
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(value) > max_items:
            errors.append(ContractValidationError(path, f"must contain at most {max_items} items", f"maxItems:{max_items}", str(len(value))))
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                _validate(schema["items"], item, _path(path, str(index)), errors)


def _matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    return True


def _expected(schema: dict[str, Any]) -> str | None:
    return str(schema["type"]) if schema.get("type") else None


def _received(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return type(value).__name__


def _path(prefix: str, field: str) -> str:
    return field if not prefix else f"{prefix}.{field}"
