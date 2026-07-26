from __future__ import annotations

from typing import Any


class ProgressEvent:
    @staticmethod
    def item_completed(
        *,
        current: int,
        total: int,
        item_id: str,
        thumbnail_url: str | None = None,
        focus_item_id: str | None = None,
        display_name: str | None = None,
        detail: str | None = None,
    ) -> dict[str, Any]:
        if current < 0 or total < 0 or current > total:
            raise ValueError("progress current/total values are invalid")
        item: dict[str, Any] = {"item_id": item_id, "state": "completed"}
        if thumbnail_url:
            item["thumbnail_url"] = thumbnail_url
        if display_name:
            item["display_name"] = display_name
        payload: dict[str, Any] = {
            "event_type": "item_completed",
            "progress": {"current": current, "total": total},
            "item": item,
        }
        if focus_item_id:
            payload["focus_item_id"] = focus_item_id
        if detail:
            payload["detail"] = detail
        return payload

    @staticmethod
    def milestone(
        *,
        id: str,
        state: str,
        label: str | None = None,
        detail: str | None = None,
    ) -> dict[str, Any]:
        if state not in {"pending", "running", "completed", "failed", "skipped"}:
            raise ValueError("unsupported milestone state")
        milestone: dict[str, Any] = {"id": id, "state": state}
        if label:
            milestone["label"] = label
        payload: dict[str, Any] = {"event_type": "milestone", "milestone": milestone}
        if detail:
            payload["detail"] = detail
        return payload

    @staticmethod
    def unit_charge(
        *,
        amount: int | float | None = None,
        currency: str = "INR",
        amount_inr_paise: int | None = None,
        unit_count: int | None = None,
        unit: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        telemetry: dict[str, Any] = {}
        if amount_inr_paise is not None:
            telemetry["reported_cost_inr_paise"] = amount_inr_paise
        elif currency.upper() == "INR" and amount is not None:
            telemetry["reported_cost_inr_paise"] = int(amount)
        else:
            telemetry["publisher_reported_amount"] = amount
            telemetry["currency"] = currency
        if unit_count is not None:
            telemetry["unit_count"] = unit_count
        if unit is not None:
            telemetry["unit"] = unit
        if metadata is not None:
            telemetry["metadata"] = metadata
        return {"event_type": "cost_telemetry", "cost_telemetry": telemetry}

    @staticmethod
    def cost_telemetry(
        *,
        amount: int | float,
        currency: str,
        unit_count: int | None = None,
        unit: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deprecated compatibility alias for unit_charge."""

        return ProgressEvent.unit_charge(
            amount=amount,
            currency=currency,
            unit_count=unit_count,
            unit=unit,
            metadata=metadata,
        )
