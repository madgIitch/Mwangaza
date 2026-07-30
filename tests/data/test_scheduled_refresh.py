from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from mwangaza.data.scheduled_refresh import (
    FileRefreshStore,
    GcsRefreshStore,
    load_refresh_status,
    run_scheduled_refresh,
)


def _payload(period_end: str = "2026-07-20") -> dict[str, object]:
    return {
        "payload_type": "risk_snapshot",
        "region_id": "som",
        "period_end": period_end,
        "status": "ok",
        "metadata": {"smoke_source": "real_gee"},
    }


class ScheduledRefreshTests(unittest.TestCase):
    def test_publishes_immutable_and_latest_snapshot_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_scheduled_refresh(
                lambda: (_payload(),),
                FileRefreshStore(root),
                period="2026-07-30",
                run_id="run-publish",
                now=_clock(datetime(2026, 7, 30, 10, tzinfo=UTC)),
            )

            self.assertEqual(result.status, "published")
            immutable = Path(result.snapshot_path or "")
            self.assertTrue(immutable.is_file())
            latest = json.loads((root / "live-dashboard-last-good.json").read_text())
            self.assertEqual(latest["refresh"]["run_id"], "run-publish")
            self.assertEqual(latest["refresh"]["effective_observation_at"], "2026-07-20")
            self.assertEqual(latest["refresh"]["age_days"], 10)
            self.assertEqual(latest["refresh"]["freshness"], "current")

    def test_same_period_is_idempotent_without_querying_again(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = FileRefreshStore(Path(directory))
            run_scheduled_refresh(
                lambda: (_payload(),),
                store,
                period="2026-07-30",
                run_id="first",
                now=_clock(datetime(2026, 7, 30, 10, tzinfo=UTC)),
            )

            def should_not_run() -> tuple[dict[str, object], ...]:
                raise AssertionError("provider must not run twice for the same period")

            second = run_scheduled_refresh(
                should_not_run,
                store,
                period="2026-07-30",
                run_id="second",
                now=_clock(datetime(2026, 7, 30, 11, tzinfo=UTC)),
            )
            self.assertEqual(second.status, "skipped")
            self.assertEqual(second.message, "period already published")

    def test_dashboard_reads_only_the_stable_snapshot_not_immutable_copies(self) -> None:
        from mwangaza.services.dashboard_shell import _read_cached_payloads

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_scheduled_refresh(
                lambda: (_payload(),),
                FileRefreshStore(root),
                period="2026-07-30",
                run_id="single-visible-copy",
                now=_clock(datetime(2026, 7, 30, 10, tzinfo=UTC)),
            )
            self.assertEqual(len(_read_cached_payloads(root)), 1)

    def test_live_lock_prevents_concurrent_processing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = FileRefreshStore(Path(directory))
            now = datetime(2026, 7, 30, 10, tzinfo=UTC)
            lock = store.acquire_lock("2026-07-30", "owner", now=now)
            try:
                result = run_scheduled_refresh(
                    lambda: (_payload(),),
                    store,
                    period="2026-07-30",
                    run_id="contender",
                    now=_clock(now),
                )
            finally:
                store.release_lock(lock, "owner")
            self.assertEqual(result.status, "skipped")
            self.assertIn("locked by run owner", result.message)

    def test_expired_lock_is_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = FileRefreshStore(Path(directory))
            old = datetime(2026, 7, 29, 1, tzinfo=UTC)
            store.acquire_lock("2026-07-30", "abandoned", now=old, ttl_minutes=5)
            result = run_scheduled_refresh(
                lambda: (_payload(),),
                store,
                period="2026-07-30",
                run_id="recovery",
                now=_clock(old + timedelta(days=1)),
            )
            self.assertEqual(result.status, "published")

    def test_failure_preserves_last_known_good_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = FileRefreshStore(root)
            run_scheduled_refresh(
                lambda: (_payload(),),
                store,
                period="2026-07-30",
                run_id="good",
                now=_clock(datetime(2026, 7, 30, 10, tzinfo=UTC)),
            )
            before = store.latest_path.read_bytes()

            def broken() -> tuple[dict[str, object], ...]:
                raise RuntimeError("upstream token=do-not-log")

            failed = run_scheduled_refresh(
                broken,
                store,
                period="2026-07-31",
                run_id="bad",
                now=_clock(datetime(2026, 7, 31, 10, tzinfo=UTC)),
            )
            self.assertEqual(failed.status, "failed")
            self.assertEqual(store.latest_path.read_bytes(), before)
            status = store.read_status()
            self.assertEqual(status["state"], "failed")
            self.assertEqual(status["last_success"]["run_id"], "good")
            self.assertNotIn("do-not-log", json.dumps(status))

    def test_old_observation_is_explicitly_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = FileRefreshStore(Path(directory))
            run_scheduled_refresh(
                lambda: (_payload("2026-06-01"),),
                store,
                period="2026-07-30",
                run_id="stale",
                now=_clock(datetime(2026, 7, 30, 10, tzinfo=UTC)),
                stale_after_days=21,
            )
            self.assertEqual(store.read_status()["state"], "stale")

    def test_freshness_becomes_stale_even_when_no_later_job_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = FileRefreshStore(root)
            run_scheduled_refresh(
                lambda: (_payload(),),
                store,
                period="2026-07-21",
                run_id="fresh-then-stale",
                now=_clock(datetime(2026, 7, 21, 10, tzinfo=UTC)),
                stale_after_days=21,
            )
            later = load_refresh_status(root, now=datetime(2026, 8, 20, 10, tzinfo=UTC))
            self.assertEqual(later["state"], "stale")
            self.assertEqual(later["last_success"]["age_days"], 31)

    def test_gcs_store_uses_generation_guarded_lock_and_atomic_objects(self) -> None:
        client = _FakeStorageClient()
        store = GcsRefreshStore("bucket", client=client)
        first = run_scheduled_refresh(
            lambda: (_payload(),),
            store,
            period="2026-07-30",
            run_id="gcs-first",
            now=_clock(datetime(2026, 7, 30, 10, tzinfo=UTC)),
        )
        second = run_scheduled_refresh(
            lambda: (_payload(),),
            store,
            period="2026-07-30",
            run_id="gcs-second",
            now=_clock(datetime(2026, 7, 30, 11, tzinfo=UTC)),
        )

        self.assertEqual(first.status, "published")
        self.assertEqual(second.status, "skipped")
        names = set(client.bucket("bucket").objects)
        self.assertIn("mwangaza-refresh/live-dashboard-last-good.json", names)
        self.assertIn("mwangaza-refresh/refresh-status.json", names)
        self.assertIn("mwangaza-refresh/snapshots/2026-07-30/gcs-first.json", names)
        self.assertNotIn("mwangaza-refresh/locks/active.json", names)


def _clock(start: datetime):
    values = iter((start, start + timedelta(seconds=2), start + timedelta(seconds=3)))
    return lambda: next(values)


class _FakeStorageClient:
    def __init__(self) -> None:
        self.buckets: dict[str, _FakeBucket] = {}

    def bucket(self, name: str):
        self.buckets.setdefault(name, _FakeBucket(name))
        return self.buckets[name]


class _FakeBucket:
    def __init__(self, name: str) -> None:
        self.name = name
        self.objects: dict[str, tuple[int, str]] = {}
        self.next_generation = 1

    def blob(self, name: str):
        return _FakeBlob(self, name)

    def get_blob(self, name: str):
        return _FakeBlob(self, name) if name in self.objects else None


class _FakeBlob:
    def __init__(self, bucket: _FakeBucket, name: str) -> None:
        self.bucket = bucket
        self.name = name

    @property
    def generation(self):
        value = self.bucket.objects.get(self.name)
        return value[0] if value else None

    def upload_from_string(self, value: str, **kwargs) -> None:
        from google.api_core.exceptions import PreconditionFailed

        expected = kwargs.get("if_generation_match")
        current = self.bucket.objects.get(self.name)
        if expected == 0 and current is not None:
            raise PreconditionFailed("object exists")
        generation = self.bucket.next_generation
        self.bucket.next_generation += 1
        self.bucket.objects[self.name] = (generation, value)

    def download_as_text(self) -> str:
        from google.api_core.exceptions import NotFound

        if self.name not in self.bucket.objects:
            raise NotFound("missing object")
        return self.bucket.objects[self.name][1]

    def delete(self, **kwargs) -> None:
        from google.api_core.exceptions import NotFound, PreconditionFailed

        current = self.bucket.objects.get(self.name)
        if current is None:
            raise NotFound("missing object")
        expected = kwargs.get("if_generation_match")
        if expected is not None and expected != current[0]:
            raise PreconditionFailed("generation changed")
        del self.bucket.objects[self.name]


if __name__ == "__main__":
    unittest.main()
