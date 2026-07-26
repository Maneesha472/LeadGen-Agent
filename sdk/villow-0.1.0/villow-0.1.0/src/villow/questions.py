from __future__ import annotations

from typing import Any


class Question:
    @staticmethod
    def single_select(
        *,
        id: str,
        label: str,
        options: list[str],
        default: str | None = None,
        decide_for_me: dict[str, Any] | None,
        required: bool = True,
    ) -> dict[str, Any]:
        if not options:
            raise ValueError("single_select requires at least one option")
        if default is not None and default not in options:
            raise ValueError("default must be one of options")
        return _question(
            id=id,
            label=label,
            question_type="single_select",
            default=default,
            validation={"options": options},
            options=options,
            decide_for_me=decide_for_me,
            required=required,
        )

    @staticmethod
    def number(
        *,
        id: str,
        label: str,
        min: int | float | None = None,
        max: int | float | None = None,
        default: int | float | None = None,
        decide_for_me: dict[str, Any] | None,
        required: bool = True,
    ) -> dict[str, Any]:
        validation: dict[str, Any] = {}
        if min is not None:
            validation["min"] = min
        if max is not None:
            validation["max"] = max
        if min is not None and max is not None and min > max:
            raise ValueError("min cannot be greater than max")
        if default is not None:
            if min is not None and default < min:
                raise ValueError("default cannot be below min")
            if max is not None and default > max:
                raise ValueError("default cannot exceed max")
        return _question(
            id=id,
            label=label,
            question_type="number",
            default=default,
            validation=validation,
            decide_for_me=decide_for_me,
            required=required,
        )

    @staticmethod
    def boolean(
        *,
        id: str,
        label: str,
        default: bool | None = None,
        decide_for_me: dict[str, Any] | None,
        required: bool = True,
    ) -> dict[str, Any]:
        return _question(
            id=id,
            label=label,
            question_type="boolean",
            default=default,
            validation={},
            decide_for_me=decide_for_me,
            required=required,
        )

    @staticmethod
    def text(
        *,
        id: str,
        label: str,
        default: str | None = None,
        decide_for_me: dict[str, Any] | None,
        required: bool = True,
        max_length: int | None = None,
    ) -> dict[str, Any]:
        validation: dict[str, Any] = {}
        if max_length is not None:
            validation["max_length"] = max_length
        return _question(
            id=id,
            label=label,
            question_type="text",
            default=default,
            validation=validation,
            decide_for_me=decide_for_me,
            required=required,
        )


def _question(
    *,
    id: str,
    label: str,
    question_type: str,
    default: Any,
    validation: dict[str, Any],
    decide_for_me: dict[str, Any] | None,
    required: bool,
    options: list[str] | None = None,
) -> dict[str, Any]:
    if not id:
        raise ValueError("question id is required")
    if not label:
        raise ValueError("question label is required")
    if decide_for_me is None:
        raise ValueError("decide_for_me is required for every clarification question")
    question: dict[str, Any] = {
        "id": id,
        "type": question_type,
        "label": label,
        "required": required,
        "default_value": default,
        "validation": validation,
        "decide_for_me": decide_for_me,
    }
    if options is not None:
        question["options"] = options
    return question
