from __future__ import annotations

from typing import Any

MAX_PRIMITIVES = 10


class Composition:
    @staticmethod
    def input(
        primitives: list[dict[str, Any]],
        *,
        fallback_slots: list[dict[str, Any]] | None = None,
        task_template: str | None = None,
        composition_id: str | None = None,
    ) -> dict[str, Any]:
        if len(primitives) > MAX_PRIMITIVES:
            raise ValueError("V1 compositions must use no more than 10 primitives")
        _ensure_unique_ids(primitives)
        return {
            "composition_id": composition_id,
            "task_template": task_template,
            "mode": "input_collection",
            "primitives": primitives,
            "fallback_slots": fallback_slots if fallback_slots is not None else _fallback_slots(primitives),
        }

    @staticmethod
    def visual_picker(
        id: str,
        *,
        label: str | None = None,
        options: list[dict[str, Any]] | None = None,
        default: str | None = None,
        preview_tier: int = 1,
    ) -> dict[str, Any]:
        payload = _primitive("visual_picker", id, label=label, default=default)
        payload["options"] = options or []
        payload["preview"] = {"tier": preview_tier}
        return payload

    @staticmethod
    def aspect_ratio_picker(
        id: str,
        *,
        label: str | None = None,
        default: str = "original",
        options: list[str] | None = None,
    ) -> dict[str, Any]:
        values = options or ["original", "square", "4:5", "16:9"]
        return _primitive("aspect_ratio_picker", id, label=label, default=default, validation={"options": values}, options=values)

    @staticmethod
    def slider_with_live_preview(
        id: str,
        *,
        label: str | None = None,
        min: int | float,
        max: int | float,
        default: int | float,
    ) -> dict[str, Any]:
        if min > max:
            raise ValueError("min cannot be greater than max")
        if default < min or default > max:
            raise ValueError("default must be within slider bounds")
        return _primitive(
            "slider_with_live_preview",
            id,
            label=label,
            default=default,
            validation={"min": min, "max": max},
            preview={"live": True},
        )

    @staticmethod
    def drive_picker(
        id: str,
        *,
        label: str | None = None,
        mode: str = "file",
        provider: str = "google",
        allow_multiple: bool = False,
    ) -> dict[str, Any]:
        if mode not in {"file", "folder"}:
            raise ValueError("drive_picker mode must be file or folder")
        return _primitive(
            "drive_picker",
            id,
            label=label,
            validation={"mode": mode, "provider": provider, "allow_multiple": allow_multiple},
        )

    @staticmethod
    def toggle_with_explanation(
        id: str,
        *,
        label: str | None = None,
        default: bool = False,
        explanation: str | None = None,
    ) -> dict[str, Any]:
        payload = _primitive("toggle_with_explanation", id, label=label, default=default)
        if explanation:
            payload["explanation"] = explanation
        return payload

    @staticmethod
    def dropdown_with_descriptions(
        id: str,
        *,
        label: str | None = None,
        options: list[dict[str, Any]],
        default: str | None = None,
    ) -> dict[str, Any]:
        return _primitive("dropdown_with_descriptions", id, label=label, default=default, options=options)

    @staticmethod
    def multi_select_chips(
        id: str,
        *,
        label: str | None = None,
        options: list[str],
        default: list[str] | None = None,
    ) -> dict[str, Any]:
        return _primitive("multi_select_chips", id, label=label, default=default or [], validation={"options": options})


def _primitive(
    primitive: str,
    id: str,
    *,
    label: str | None = None,
    default: Any = None,
    validation: dict[str, Any] | None = None,
    options: list[Any] | None = None,
    preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not id:
        raise ValueError("primitive id is required")
    payload: dict[str, Any] = {
        "primitive": primitive,
        "type": primitive,
        "id": id,
        "label": label or id.replace("_", " ").title(),
        "validation": validation or {},
    }
    if default is not None:
        payload["default_value"] = default
    if options is not None:
        payload["options"] = options
    if preview is not None:
        payload["preview"] = preview
    return payload


def _ensure_unique_ids(primitives: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for primitive in primitives:
        primitive_id = primitive.get("id")
        if not primitive_id:
            raise ValueError("every primitive requires an id")
        if primitive_id in seen:
            raise ValueError(f"duplicate primitive id: {primitive_id}")
        seen.add(primitive_id)


def _fallback_slots(primitives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for primitive in primitives:
        slots.append(
            {
                "id": primitive["id"],
                "label": primitive.get("label", primitive["id"]),
                "type": _fallback_type(primitive),
                "default_value": primitive.get("default_value"),
                "validation": primitive.get("validation", {}),
            }
        )
    return slots


def _fallback_type(primitive: dict[str, Any]) -> str:
    primitive_type = primitive.get("primitive") or primitive.get("type")
    if primitive_type == "slider_with_live_preview":
        return "number"
    if primitive_type == "drive_picker":
        mode = primitive.get("validation", {}).get("mode", "file")
        return "drive_folder" if mode == "folder" else "drive_file"
    if primitive_type == "toggle_with_explanation":
        return "boolean"
    if primitive_type in {"visual_picker", "aspect_ratio_picker", "dropdown_with_descriptions"}:
        return "single_select"
    if primitive_type == "multi_select_chips":
        return "multi_select"
    return "text"
