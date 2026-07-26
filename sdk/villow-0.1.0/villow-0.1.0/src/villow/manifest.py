from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from villow.artifacts import ALLOWED_ARTIFACT_TYPES


@dataclass(frozen=True)
class ManifestValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
    manifest: dict[str, Any]


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("agent manifest must be a YAML object")
    return data


def validate_manifest(path: str | Path) -> ManifestValidationResult:
    errors: list[str] = []
    try:
        manifest = load_manifest(path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return ManifestValidationResult(valid=False, errors=[str(exc)], warnings=[], manifest={})

    warnings: list[str] = []
    for field in ["publisher_id", "agent_id", "name", "version", "task_templates"]:
        if not manifest.get(field):
            errors.append(f"{field} is required")

    templates = manifest.get("task_templates")
    if not isinstance(templates, list) or not templates:
        errors.append("task_templates must be a non-empty list")
    elif len(templates) > 5:
        errors.append("V1 launch agents should keep templates tightly scoped")
    else:
        for index, template in enumerate(templates):
            _validate_template(index, template, errors, warnings)

    _validate_tool_rate_limits(manifest.get("tool_rate_limits"), errors, warnings)
    return ManifestValidationResult(valid=not errors, errors=errors, warnings=warnings, manifest=manifest)


def _validate_template(index: int, template: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(template, dict):
        errors.append(f"task_templates[{index}] must be an object")
        return
    slug = template.get("slug")
    if not slug:
        errors.append(f"task_templates[{index}].slug is required")
    if template.get("artifact_type") not in ALLOWED_ARTIFACT_TYPES:
        errors.append(f"task_templates[{index}].artifact_type must be a V1 artifact type")
    if "preview_tier" in template:
        warnings.append(
            f"task_templates[{index}].preview_tier is forward-compatible only; V1 does not require or exercise /preview"
        )
    review_primitive = template.get("artifact_review_primitive")
    if review_primitive in {"gallery_review", "before_after_compare", "document_preview_with_fields"}:
        warnings.append(
            f"task_templates[{index}].artifact_review_primitive {review_primitive} is deferred from V1 launch "
            "and will render with the simple typed fallback"
        )
    _validate_price_bounds(index, template, errors)
    composition = template.get("input_composition") or []
    if len(composition) > 10:
        errors.append(f"task_templates[{index}].input_composition exceeds 10 primitives")
    for primitive_index, primitive in enumerate(composition):
        if not isinstance(primitive, dict):
            errors.append(f"task_templates[{index}].input_composition[{primitive_index}] must be an object")
            continue
        if not primitive.get("id"):
            errors.append(f"task_templates[{index}].input_composition[{primitive_index}].id is required")
        if "decide_for_me" not in primitive:
            errors.append(f"task_templates[{index}].input_composition[{primitive_index}].decide_for_me is required")


def _validate_price_bounds(index: int, template: dict[str, Any], errors: list[str]) -> None:
    """Validate the optional per-unit price ceiling fields (T·M; N1.5, formalizes F3).

    ``unit_ceiling`` is M (the publisher-committed worst case in credits); ``typical_charge`` is T
    (the typical charge). Both are **optional and additive** — a manifest without them stays valid
    (M becomes a hard requirement at vetting, N2.5, not here). Validate only when present: M a
    positive integer, T a non-negative integer, and T never above M (a typical charge above the
    ceiling is incoherent).
    """

    ceiling = template.get("unit_ceiling")
    typical = template.get("typical_charge")
    if ceiling is not None:
        if isinstance(ceiling, bool) or not isinstance(ceiling, int) or ceiling <= 0:
            errors.append(f"task_templates[{index}].unit_ceiling must be a positive integer (credits)")
            ceiling = None
    if typical is not None:
        if isinstance(typical, bool) or not isinstance(typical, int) or typical < 0:
            errors.append(f"task_templates[{index}].typical_charge must be a non-negative integer (credits)")
            typical = None
    if isinstance(ceiling, int) and isinstance(typical, int) and typical > ceiling:
        errors.append(f"task_templates[{index}].typical_charge must not exceed unit_ceiling")


def _validate_tool_rate_limits(value: Any, errors: list[str], warnings: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append("tool_rate_limits must be an object keyed by tool name")
        return
    for tool_name, config in value.items():
        if not isinstance(config, dict):
            errors.append(f"tool_rate_limits.{tool_name} must be an object")
            continue
        per_minute = config.get("per_minute")
        if isinstance(per_minute, bool) or not isinstance(per_minute, int) or per_minute <= 0:
            errors.append(f"tool_rate_limits.{tool_name}.per_minute must be a positive integer")
        if not config.get("justification"):
            warnings.append(f"tool_rate_limits.{tool_name}.justification is recommended for publisher vetting")
