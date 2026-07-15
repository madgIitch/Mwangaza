from __future__ import annotations

import contextlib
import io
import json
import unittest

from mwangaza.cli import main
from mwangaza.pipeline import (
    PipelineConfig,
    PipelineError,
    PipelineTask,
    RegionRunResult,
    run_refresh_pipeline,
)


def _task(region_id: str, status: str) -> PipelineTask:
    return PipelineTask(region_id, lambda rid: RegionRunResult(rid, status, payload={"region": rid}))


class RefreshPipelineTests(unittest.TestCase):
    def test_run_has_id_times_config_and_stable_results(self) -> None:
        run = run_refresh_pipeline(
            [_task("som", "remote_query"), _task("ken", "cache_hit")],
            config=PipelineConfig(max_concurrency=2, max_failure_fraction=0.5),
            run_id="run-1",
        )

        self.assertEqual(run.run_id, "run-1")
        self.assertEqual([result.region_id for result in run.results], ["ken", "som"])
        self.assertEqual(run.summary["cache_hit"], 1)
        self.assertEqual(run.summary["remote_query"], 1)
        self.assertEqual(run.exit_code, 0)
        self.assertEqual(run.effective_config["max_concurrency"], 2)

    def test_regional_failure_is_isolated_and_threshold_sets_exit_code(self) -> None:
        def fail(_: str) -> RegionRunResult:
            raise RuntimeError("boom")

        run = run_refresh_pipeline(
            [PipelineTask("ken", fail), _task("som", "cache_hit")],
            config=PipelineConfig(max_failure_fraction=0.25),
        )

        self.assertEqual(run.summary["error"], 1)
        self.assertEqual(run.summary["cache_hit"], 1)
        self.assertEqual(run.exit_code, 1)

    def test_resume_skips_completed_and_processes_failed(self) -> None:
        calls: list[str] = []

        def processor(region_id: str) -> RegionRunResult:
            calls.append(region_id)
            return RegionRunResult(region_id, "remote_query")

        previous = [
            RegionRunResult("ken", "cache_hit", payload={"old": True}),
            RegionRunResult("som", "error"),
        ]
        run = run_refresh_pipeline(
            [PipelineTask("ken", processor), PipelineTask("som", processor)],
            resume=True,
            previous_results=previous,
        )

        self.assertEqual(calls, ["som"])
        self.assertEqual(run.results[0].status, "skipped")
        self.assertEqual(run.results[1].status, "remote_query")

    def test_validates_conservative_concurrency(self) -> None:
        with self.assertRaisesRegex(PipelineError, "max_concurrency"):
            run_refresh_pipeline([], config=PipelineConfig(max_concurrency=0))
        with self.assertRaisesRegex(PipelineError, "max_concurrency"):
            run_refresh_pipeline([], config=PipelineConfig(max_concurrency=9))

    def test_summary_distinguishes_all_statuses(self) -> None:
        run = run_refresh_pipeline(
            [
                _task("a", "cache_hit"),
                _task("b", "remote_query"),
                _task("c", "no_data"),
                _task("d", "skipped"),
            ],
            config=PipelineConfig(max_failure_fraction=1.0),
        )

        self.assertEqual(run.summary["cache_hit"], 1)
        self.assertEqual(run.summary["remote_query"], 1)
        self.assertEqual(run.summary["no_data"], 1)
        self.assertEqual(run.summary["skipped"], 1)
        self.assertEqual(run.summary["error"], 0)

    def test_cli_serializes_summary_and_returns_exit_code(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = main(["refresh-pipeline", "--region", "ken", "--dry-run"])

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["summary"]["cache_hit"], 1)
        self.assertTrue(payload["effective_config"]["dry_run"])


if __name__ == "__main__":
    unittest.main()
