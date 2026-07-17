from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class SimulatedNotification:
    notification_id: str
    dedupe_key: str
    alert_id: str
    channel: str
    recipient_masked: str
    content: str
    status: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


class NotificationOutbox:
    def __init__(self) -> None:
        self._items: dict[str, SimulatedNotification] = {}

    def enqueue(
        self,
        *,
        alert_id: str,
        channel: str,
        recipient: str,
        content: str,
        template_id: str = "default",
        metadata: dict[str, Any] | None = None,
    ) -> SimulatedNotification:
        recipient_masked = mask_recipient(recipient)
        dedupe_key = _dedupe_key(alert_id, channel, recipient_masked, template_id)
        existing = self._items.get(dedupe_key)
        if existing is not None:
            return existing
        created_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        item = SimulatedNotification(
            notification_id=hashlib.sha1(dedupe_key.encode("utf-8")).hexdigest()[:12],
            dedupe_key=dedupe_key,
            alert_id=alert_id,
            channel=channel,
            recipient_masked=recipient_masked,
            content=content,
            status="simulated",
            created_at=created_at,
            metadata=metadata or {},
        )
        self._items[dedupe_key] = item
        return item

    def list_items(self) -> tuple[SimulatedNotification, ...]:
        return tuple(self._items.values())


def simulate_notifications_for_alert(
    alert: Any,
    *,
    outbox: NotificationOutbox | None = None,
    recipients: dict[str, tuple[str, ...]] | None = None,
    enabled_severities: tuple[str, ...] = ("warning", "emergency", "critical"),
) -> tuple[SimulatedNotification, ...]:
    severity = str(getattr(alert, "severity", "") or getattr(alert, "risk_level", ""))
    if severity not in enabled_severities:
        return ()
    box = outbox or NotificationOutbox()
    alert_id = str(getattr(alert, "alert_id", "") or f"{getattr(alert, 'region_id', 'unknown')}-{severity}")
    region = str(getattr(alert, "region", "") or getattr(alert, "region_id", "Unknown region"))
    title = str(getattr(alert, "title", "Drought alert"))
    action = str(getattr(alert, "recommended_action", "") or getattr(alert, "action", "Review early action plan."))
    configured = recipients or {
        "sms": ("+254700000000",),
        "email": ("operations@example.org",),
        "telegram": ("@mwangaza_ops",),
    }
    items: list[SimulatedNotification] = []
    for channel, channel_recipients in configured.items():
        for recipient in channel_recipients:
            content = f"[SIMULATED] {title} for {region}. Recommended action: {action}"
            items.append(
                box.enqueue(
                    alert_id=alert_id,
                    channel=channel,
                    recipient=recipient,
                    content=content,
                    template_id="alert-v1",
                    metadata={"severity": severity, "region": region},
                )
            )
    return tuple(items)


def send_with_real_adapter(*, real_adapters_enabled: bool = False, secrets: dict[str, str] | None = None) -> None:
    if not real_adapters_enabled or not secrets:
        raise RuntimeError("real notification adapters are disabled")


def mask_recipient(recipient: str) -> str:
    if "@" in recipient and not recipient.startswith("@"):
        name, domain = recipient.split("@", 1)
        return f"{name[:2]}***@{domain}"
    if recipient.startswith("@"):
        return recipient[:3] + "***"
    digits = "".join(char for char in recipient if char.isdigit())
    if len(digits) >= 4:
        return "***" + digits[-4:]
    return "***"


def _dedupe_key(alert_id: str, channel: str, recipient_masked: str, template_id: str) -> str:
    return "|".join((alert_id, channel, recipient_masked, template_id))


__all__ = [
    "NotificationOutbox",
    "SimulatedNotification",
    "mask_recipient",
    "send_with_real_adapter",
    "simulate_notifications_for_alert",
]
