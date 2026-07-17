# Executive Report

Sprint 31 adds a deterministic executive report generated from the dashboard
snapshot already loaded in memory.

Contracts:

- `build_executive_report_context(data, region_id=None, dashboard_url=None, generated_at=None)`;
- `render_executive_report_html(context)`;
- `render_executive_report_pdf(context)`;
- `safe_report_filename(context)`.

The report includes region, period, score, level, quality, indicators,
recommendations, sources, versions and limitations. It does not query Earth
Engine, read remote data or recalculate indicators.

The QR section is included only when a safe `http://` or `https://` dashboard URL
is provided. Without a URL, the section is omitted.

The generated filename is deterministic and safe for local filesystems:
`mwangaza-executive-report-<region>-<period>.pdf`.
