from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from mwangaza.cache import AnalyticalCache, CacheConfig, CacheError, build_cache_key


def _key(**overrides: str):
    payload = {
        "region_id": "ken",
        "indicator": "ndvi",
        "period_start": "2026-07-01T00:00:00Z",
        "period_end": "2026-07-08T00:00:00Z",
        "source": "TEST/NDVI",
        "algorithm_version": "algo-v1",
        "data_type": "indicator",
    }
    payload.update(overrides)
    return build_cache_key(**payload)


class ParquetCacheTests(unittest.TestCase):
    def test_cache_key_includes_contract_fields(self) -> None:
        key = _key()
        changed = _key(algorithm_version="algo-v2")

        self.assertNotEqual(key.digest, changed.digest)
        self.assertTrue(key.filename.endswith(".json"))
        self.assertEqual(key.region_id, "ken")

    def test_hit_avoids_recomputing_producer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = AnalyticalCache(CacheConfig(Path(tmp), {"indicator": 60}))
            calls = 0

            def producer() -> dict[str, object]:
                nonlocal calls
                calls += 1
                return {"value": 0.42}

            first = cache.get_or_compute(_key(), producer)
            second = cache.get_or_compute(_key(), producer)

            self.assertEqual(calls, 1)
            self.assertEqual(first.payload, second.payload)
            self.assertEqual(cache.last_status, "hit")

    def test_write_uses_final_file_and_no_temp_file_remains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = AnalyticalCache(CacheConfig(Path(tmp), {"indicator": 60}))
            key = _key()
            entry = cache.write(key, {"value": 0.42})

            self.assertTrue((Path(tmp) / key.filename).exists())
            self.assertFalse(list(Path(tmp).glob("*.tmp")))
            self.assertEqual(entry.cache_key, key.digest)
            self.assertEqual(entry.algorithm_version, "algo-v1")

    def test_corrupt_entry_is_miss_and_can_regenerate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = AnalyticalCache(CacheConfig(Path(tmp), {"indicator": 60}))
            key = _key()
            (Path(tmp) / key.filename).write_text("{not json", encoding="utf-8")
            calls = 0

            def producer() -> dict[str, object]:
                nonlocal calls
                calls += 1
                return {"value": 0.5}

            entry = cache.get_or_compute(key, producer)

            self.assertEqual(calls, 1)
            self.assertEqual(entry.payload["value"], 0.5)
            self.assertEqual(cache.last_status, "miss")

    def test_ttl_by_data_type_expires_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = AnalyticalCache(CacheConfig(Path(tmp), {"indicator": 10, "default": 100}))
            now = datetime(2026, 7, 1, tzinfo=UTC)
            key = _key()
            cache.write(key, {"value": 0.42}, now=now)

            self.assertIsNotNone(cache.read(key, now=now + timedelta(seconds=9)))
            self.assertIsNone(cache.read(key, now=now + timedelta(seconds=10)))
            self.assertEqual(cache.last_status, "expired")

    def test_rejects_sensitive_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = AnalyticalCache(CacheConfig(Path(tmp), {"indicator": 60}))
            with self.assertRaisesRegex(CacheError, "sensitive"):
                cache.write(_key(), {"value": 1, "private_key": "do-not-store"})
            with self.assertRaisesRegex(CacheError, "sensitive"):
                cache.write(_key(), {"value": 1}, metadata={"service_account": "x"})


if __name__ == "__main__":
    unittest.main()
