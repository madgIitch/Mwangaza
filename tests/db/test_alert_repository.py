from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mwangaza.actions import recommend_actions
from mwangaza.alerts.repository import AlertRepository
from mwangaza.contracts import RiskSnapshot


def _risk(level: str = "watch", score: float = 40.0) -> RiskSnapshot:
    return RiskSnapshot(
        region_id="ken",
        period_start="2026-07-01T00:00:00Z",
        period_end="2026-07-08T00:00:00Z",
        composite_score=score,
        risk_level=level,
        contributing_indicators=("ndvi", "rainfall_mm"),
        source="TEST/RISK",
        quality_flag="ok",
        is_simulated=True,
        metadata={"model_version": "model-v1", "evidence": {"ndvi": 0.3}},
    )


class AlertRepositoryTests(unittest.TestCase):
    def test_migrations_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = AlertRepository(Path(tmp) / "alerts.sqlite")
            try:
                repo.migrate()
                repo.migrate()
            finally:
                repo.close()

    def test_reprocessing_same_snapshot_does_not_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = AlertRepository(Path(tmp) / "alerts.sqlite")
            try:
                risk = _risk()
                first = repo.upsert_alert(risk, recommend_actions(risk))
                second = repo.upsert_alert(risk, recommend_actions(risk))

                self.assertEqual(first.alert_id, second.alert_id)
                self.assertEqual(len(repo.list_events(first.alert_id)), 1)
            finally:
                repo.close()

    def test_severity_change_generates_transition_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = AlertRepository(Path(tmp) / "alerts.sqlite")
            try:
                first = repo.upsert_alert(_risk("watch", 40), recommend_actions(_risk("watch", 40)))
                changed = _risk("warning", 70)
                second = repo.upsert_alert(changed, recommend_actions(changed))
                events = repo.list_events(first.alert_id)

                self.assertEqual(first.alert_id, second.alert_id)
                self.assertEqual(events[-1]["event_type"], "severity_changed")
                self.assertEqual(events[-1]["from_severity"], "watch")
                self.assertEqual(events[-1]["to_severity"], "warning")
            finally:
                repo.close()

    def test_resolved_alert_keeps_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = AlertRepository(Path(tmp) / "alerts.sqlite")
            try:
                alert = repo.upsert_alert(_risk(), recommend_actions(_risk()))
                resolved = repo.resolve_alert(alert.alert_id, reason="rain recovered")
                events = repo.list_events(alert.alert_id)

                self.assertEqual(resolved.status, "resolved")
                self.assertEqual(events[0]["event_type"], "created")
                self.assertEqual(events[-1]["event_type"], "resolved")
                self.assertEqual(events[-1]["metadata"]["reason"], "rain recovered")
            finally:
                repo.close()

    def test_record_stores_score_quality_evidence_and_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = AlertRepository(Path(tmp) / "alerts.sqlite")
            try:
                risk = _risk("warning", 70)
                alert = repo.upsert_alert(risk, recommend_actions(risk))

                self.assertEqual(alert.score, 70)
                self.assertEqual(alert.quality_flag, "ok")
                self.assertEqual(alert.evidence["model_version"], "model-v1")
                self.assertEqual(alert.recommendations[0]["urgency"], "prepositioning")
            finally:
                repo.close()


if __name__ == "__main__":
    unittest.main()
