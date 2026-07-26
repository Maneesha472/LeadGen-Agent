from __future__ import annotations

from typing import Any

ALLOWED_ARTIFACT_TYPES = {
    "file_set",
    "structured_fields",
    "message_draft",
    "event_proposal",
    "table_data",
    "generic",
}


class Artifact:
    @staticmethod
    def file_set(
        *,
        files: list[dict[str, Any]],
        preview_urls: list[str] | None = None,
        destination_proposal: dict[str, Any] | None = None,
        title: str = "Files",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _artifact(
            "file_set",
            title=title,
            type_payload={"files": files},
            preview_data={"preview_urls": preview_urls or [], "file_count": len(files)},
            destination_proposal=destination_proposal,
            metadata=metadata,
        )

    @staticmethod
    def structured_fields(
        *,
        fields: dict[str, Any],
        title: str = "Structured fields",
        confidence: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        return _artifact(
            "structured_fields",
            title=title,
            type_payload={"fields": fields, "confidence": confidence or {}},
            preview_data={"field_count": len(fields)},
        )

    @staticmethod
    def message_draft(
        *,
        subject: str,
        body: str,
        to: list[str] | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        title: str = "Message draft",
    ) -> dict[str, Any]:
        return _artifact(
            "message_draft",
            title=title,
            type_payload={"to": to or [], "cc": cc or [], "bcc": bcc or [], "subject": subject, "body": body},
            preview_data={"subject": subject, "body_preview": body[:200]},
        )

    @staticmethod
    def event_proposal(
        *,
        title: str,
        start: str,
        end: str,
        attendees: list[str] | None = None,
        location: str | None = None,
    ) -> dict[str, Any]:
        return _artifact(
            "event_proposal",
            title=title,
            type_payload={"title": title, "start": start, "end": end, "attendees": attendees or [], "location": location},
            preview_data={"start": start, "end": end},
        )

    @staticmethod
    def table_data(
        *,
        columns: list[str],
        rows: list[list[Any]],
        title: str = "Table data",
    ) -> dict[str, Any]:
        return _artifact(
            "table_data",
            title=title,
            type_payload={"columns": columns, "rows": rows},
            preview_data={"column_count": len(columns), "row_count": len(rows), "sample_rows": rows[:5]},
        )

    @staticmethod
    def generic(
        *,
        payload: dict[str, Any],
        title: str = "Artifact",
        preview_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _artifact("generic", title=title, type_payload=payload, preview_data=preview_data or {})


def _artifact(
    artifact_type: str,
    *,
    title: str,
    type_payload: dict[str, Any],
    preview_data: dict[str, Any],
    destination_proposal: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if artifact_type not in ALLOWED_ARTIFACT_TYPES:
        raise ValueError(f"unsupported artifact type: {artifact_type}")
    payload: dict[str, Any] = {
        "artifact_type": artifact_type,
        "title": title,
        "type_payload": type_payload,
        "preview_data": preview_data,
    }
    if destination_proposal is not None:
        payload["destination_proposal"] = destination_proposal
    if metadata is not None:
        payload["metadata"] = metadata
    return payload
