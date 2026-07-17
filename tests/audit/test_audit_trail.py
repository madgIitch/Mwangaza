from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mwangaza.audit import AuditRepository


class AuditTrailTests(unittest.TestCase):
    def test_event_includes_required_fields_and_snapshot_linkage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = AuditRepository(Path(tmp) / "audit.sqlite")
            try:
                event = repo.record_event(
                    actor="pipeline",
                    event_type="data_refreshed",
                    entity_type="snapshot",
                    entity_id="snapshot-1",
                    region_id="som",
                    run_id="run-1",
                    snapshot_id="snapshot-1",
                    model_version="risk-v1",
                    metadata={"rows": 5},
                )
            finally:
                repo.close()

        self.assertEqual(event.actor, "pipeline")
        self.assertEqual(event.event_type, "data_refreshed")
        self.assertEqual(event.entity_type, "snapshot")
        self.assertEqual(event.run_id, "run-1")
        self.assertEqual(event.snapshot_id, "snapshot-1")
        self.assertEqual(event.model_version, "risk-v1")
        self.assertIn("T", event.timestamp)

    def test_alert_lifecycle_events_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = AuditRepository(Path(tmp) / "audit.sqlite")
            try:
                for event_type in ("alert_created", "alert_escalated", "alert_deescalated", "alert_resolved"):
                    repo.record_alert_event(
                        actor="alerts",
                        event_type=event_type,
                        alert_id="alert-1",
                        region_id="som",
                        run_id="run-2",
                        snapshot_id="snapshot-2",
                        model_version="risk-v1",
                    )
                events = repo.list_events(run_id="run-2")
            finally:
                repo.close()

        self.assertEqual([event.event_type for event in events], [
            "alert_created",
            "alert_escalated",
            "alert_deescalated",
            "alert_resolved",
        ])

    def test_configuration_change_redacts_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = AuditRepository(Path(tmp) / "audit.sqlite")
            try:
                event = repo.record_config_change(
                    actor="operator",
                    entity_id="thresholds",
                    previous_version={"risk": 60, "private_key": "abc"},
                    new_version={"risk": 70, "token": "secret-token", "path": "C:\\Users\\secret.json"},
                    run_id="run-3",
                )
            finally:
                repo.close()

        self.assertEqual(event.metadata["previous_version"]["private_key"], "[redacted]")
        self.assertEqual(event.metadata["new_version"]["token"], "[redacted]")
        self.assertEqual(event.metadata["new_version"]["path"], "[redacted]")
        self.assertEqual(event.metadata["new_version"]["risk"], 70)

    def test_query_filters_by_region_run_and_type_with_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = AuditRepository(Path(tmp) / "audit.sqlite")
            try:
                repo.record_event(actor="a", event_type="data_refreshed", entity_type="snapshot", entity_id="1", region_id="som", run_id="run-a")
                repo.record_event(actor="a", event_type="data_refreshed", entity_type="snapshot", entity_id="2", region_id="ken", run_id="run-a")
                repo.record_event(actor="a", event_type="configuration_changed", entity_type="configuration", entity_id="3", region_id="som", run_id="run-b")
                events = repo.list_events(region_id="som", run_id="run-a", event_type="data_refreshed", limit=10)
            finally:
                repo.close()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].entity_id, "1")

    def test_repository_has_no_public_delete_method(self) -> None:
        public = {name for name in dir(AuditRepository) if not name.startswith("_")}

        self.assertNotIn("delete_event", public)
        self.assertNotIn("delete", public)
        self.assertNotIn("truncate", public)


if __name__ == "__main__":
    unittest.main()
