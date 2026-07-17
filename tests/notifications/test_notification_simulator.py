from __future__ import annotations

import unittest

from mwangaza.notifications import (
    NotificationOutbox,
    mask_recipient,
    send_with_real_adapter,
    simulate_notifications_for_alert,
)
from mwangaza.services.dashboard_shell import load_dashboard_shell_data
from mwangaza.ui.dashboard import build_dashboard_shell_html


class NotificationSimulatorTests(unittest.TestCase):
    def test_simulated_notifications_store_channel_masked_recipient_content_alert_and_status(self) -> None:
        alert = load_dashboard_shell_data("demo").alerts[0]
        outbox = NotificationOutbox()

        items = simulate_notifications_for_alert(alert, outbox=outbox)

        self.assertEqual(len(items), 3)
        first = items[0]
        self.assertEqual(first.status, "simulated")
        self.assertEqual(first.alert_id, "som-critical")
        self.assertEqual(first.channel, "sms")
        self.assertEqual(first.recipient_masked, "***0000")
        self.assertIn("[SIMULATED]", first.content)
        self.assertIn("Drought risk escalation", first.content)
        self.assertEqual(len(outbox.list_items()), 3)

    def test_only_configured_severities_create_notifications(self) -> None:
        alert = load_dashboard_shell_data("demo").alerts[2]

        self.assertEqual(simulate_notifications_for_alert(alert, enabled_severities=("critical",)), ())

    def test_reprocessing_does_not_duplicate_same_dedupe_key(self) -> None:
        alert = load_dashboard_shell_data("demo").alerts[0]
        outbox = NotificationOutbox()

        simulate_notifications_for_alert(alert, outbox=outbox)
        simulate_notifications_for_alert(alert, outbox=outbox)

        self.assertEqual(len(outbox.list_items()), 3)

    def test_real_adapter_fails_closed_without_feature_flag_and_secrets(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "disabled"):
            send_with_real_adapter()

    def test_masking_and_dashboard_preview(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertEqual(mask_recipient("ops@example.org"), "op***@example.org")
        self.assertIn("Simulated notification preview", html)
        self.assertIn("real adapters disabled by default", html)
        self.assertNotIn("+254700000000", html)


if __name__ == "__main__":
    unittest.main()
