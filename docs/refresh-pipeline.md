# Refresh Pipeline

Sprint 16 adds a small refresh pipeline contract for orchestrating per-region
work.

`run_refresh_pipeline(...)` accepts fakeable `PipelineTask` processors and returns
a `PipelineRun` with:

- `run_id`, `started_at`, `finished_at`
- sanitized effective configuration
- stable per-region results
- summary counts for `cache_hit`, `remote_query`, `no_data`, `error` and `skipped`
- `exit_code` derived from the configured failure threshold

Regional failures are isolated. Resume mode skips previously completed regions
and only processes pending or failed work. The CLI entrypoint
`mwangaza.cli refresh-pipeline` is additive and does not replace the existing
`python -m mwangaza.data.refresh --dry-run` command.
