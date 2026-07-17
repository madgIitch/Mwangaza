from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from typing import Any


@dataclass(frozen=True)
class ReportMetric:
    label: str
    value: str
    unit: str
    detail: str
    severity: str


@dataclass(frozen=True)
class ExecutiveReportContext:
    region_id: str
    region_label: str
    period_label: str
    generated_at: str
    score: str
    risk_level: str
    quality: str
    metrics: tuple[ReportMetric, ...]
    recommendations: tuple[str, ...]
    sources: tuple[str, ...]
    versions: tuple[str, ...]
    limitations: tuple[str, ...]
    dashboard_url: str = ""
    qr_matrix: tuple[str, ...] = ()


def build_executive_report_context(
    data: Any,
    *,
    region_id: str | None = None,
    dashboard_url: str | None = None,
    generated_at: datetime | None = None,
) -> ExecutiveReportContext:
    selected_region = (region_id or getattr(data, "selected_region_id", "")).lower()
    profile = _profile_for_region(data, selected_region)
    metrics = tuple(
        ReportMetric(
            label=str(metric.label),
            value=str(metric.value),
            unit=str(metric.unit),
            detail=str(metric.detail),
            severity=str(metric.severity),
        )
        for metric in (getattr(profile, "metrics", ()) or getattr(data, "metrics", ()))
    )
    map_region = _map_region_for(data, selected_region)
    period_label = _period_label_from_data(data, map_region)
    generated = (generated_at or datetime.now(UTC)).replace(microsecond=0).isoformat()
    source_values = _unique(
        (
            getattr(getattr(data, "data_status", None), "source", ""),
            *(metric.detail for metric in metrics if _looks_like_source(metric.detail)),
        )
    )
    version_values = _unique(_metric_versions(metrics))
    url = _safe_url(dashboard_url or "")
    return ExecutiveReportContext(
        region_id=selected_region,
        region_label=str(getattr(profile, "label", "") or getattr(data, "selected_region", "") or selected_region.upper()),
        period_label=period_label,
        generated_at=generated,
        score=_metric_value(metrics, "Composite score"),
        risk_level=str(getattr(map_region, "color_level", "") or _risk_from_metric(metrics)),
        quality=_metric_value(metrics, "Data quality"),
        metrics=metrics,
        recommendations=tuple(str(item) for item in getattr(profile, "recommendations", ()) or getattr(data, "recommendations", ())),
        sources=source_values or ("No source metadata available",),
        versions=version_values or ("No version metadata available",),
        limitations=(
            "This report is a decision-support prototype, not an official alert.",
            "`potentially_exposed` is potential exposure, not measured impact.",
            "Observed, cached and demo/synthetic data must be interpreted separately.",
        ),
        dashboard_url=url,
        qr_matrix=_qr_matrix(url) if url else (),
    )


def render_executive_report_html(context: ExecutiveReportContext) -> str:
    metrics = "\n".join(
        "<tr><td>{label}</td><td>{value} {unit}</td><td>{severity}</td><td>{detail}</td></tr>".format(
            label=escape(metric.label),
            value=escape(metric.value),
            unit=escape(metric.unit),
            severity=escape(metric.severity),
            detail=escape(metric.detail),
        )
        for metric in context.metrics
    )
    bars = "\n".join(
        '<div class="bar" data-metric="{label}"><span style="width:{width}%"></span><b>{label}: {value}</b></div>'.format(
            label=escape(metric.label),
            width=_bar_width(metric),
            value=escape(metric.value),
        )
        for metric in context.metrics
    )
    recommendations = "".join(f"<li>{escape(item)}</li>" for item in context.recommendations)
    sources = "".join(f"<li>{escape(item)}</li>" for item in context.sources)
    versions = "".join(f"<li>{escape(item)}</li>" for item in context.versions)
    limitations = "".join(f"<li>{escape(item)}</li>" for item in context.limitations)
    qr = _render_qr(context)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Mwangaza Executive Report - {escape(context.region_label)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #17233b; margin: 28px; }}
    h1 {{ margin: 0 0 6px; font-size: 24px; }}
    .meta, .note {{ color: #5c667a; font-size: 12px; }}
    .summary {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 18px 0; }}
    .tile {{ border: 1px solid #dfe4ea; border-radius: 8px; padding: 10px; }}
    .tile strong {{ display: block; font-size: 18px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }}
    th, td {{ border-bottom: 1px solid #e8ecf1; padding: 7px; text-align: left; vertical-align: top; }}
    .bar {{ position: relative; height: 24px; border: 1px solid #dfe4ea; margin: 7px 0; }}
    .bar span {{ display: block; height: 100%; background: #e9f5eb; }}
    .bar b {{ position: absolute; left: 8px; top: 5px; font-size: 11px; }}
    .qr {{ display: grid; grid-template-columns: repeat(9, 8px); gap: 1px; margin-top: 8px; }}
    .qr i {{ width: 8px; height: 8px; background: #fff; border: 1px solid #dfe4ea; }}
    .qr i.on {{ background: #17233b; border-color: #17233b; }}
  </style>
</head>
<body>
  <h1>Mwangaza Executive Report</h1>
  <p class="meta">Region: {escape(context.region_label)} | Period: {escape(context.period_label)} | Generated: {escape(context.generated_at)}</p>
  <section class="summary">
    <div class="tile"><span>Composite score</span><strong>{escape(context.score)}</strong></div>
    <div class="tile"><span>Risk level</span><strong>{escape(context.risk_level)}</strong></div>
    <div class="tile"><span>Quality</span><strong>{escape(context.quality)}</strong></div>
  </section>
  <h2>Snapshot Indicators</h2>
  <div>{bars}</div>
  <table>
    <thead><tr><th>Indicator</th><th>Value</th><th>Quality</th><th>Source and method</th></tr></thead>
    <tbody>{metrics}</tbody>
  </table>
  <h2>Recommended Actions</h2>
  <ul>{recommendations}</ul>
  <h2>Sources and Versions</h2>
  <ul>{sources}{versions}</ul>
  <h2>Limitations</h2>
  <ul>{limitations}</ul>
  {qr}
</body>
</html>"""


def render_executive_report_pdf(context: ExecutiveReportContext) -> bytes:
    html = render_executive_report_html(context)
    return b"%PDF-HTML\n" + html.encode("utf-8")


def safe_report_filename(context: ExecutiveReportContext) -> str:
    region = _slug(context.region_label or context.region_id)
    period = _slug(context.period_label)
    return f"mwangaza-executive-report-{region}-{period}.pdf"


def _profile_for_region(data: Any, region_id: str) -> Any:
    for profile in getattr(data, "region_profiles", ()):
        if getattr(profile, "region_id", "") == region_id:
            return profile
    return getattr(data, "region_profiles", (None,))[0] if getattr(data, "region_profiles", ()) else data


def _map_region_for(data: Any, region_id: str) -> Any:
    for region in getattr(getattr(data, "risk_map", None), "regions", ()):
        if getattr(region, "region_id", "") == region_id:
            return region
    return None


def _period_label_from_data(data: Any, map_region: Any) -> str:
    start = str(getattr(map_region, "period_start", "") or "")
    end = str(getattr(map_region, "period_end", "") or "")
    if start and end:
        return f"{start[:10]} to {end[:10]}"
    if getattr(data, "temporal_periods", ()):
        return str(data.temporal_periods[0].label)
    return str(getattr(getattr(data, "data_status", None), "last_updated", "") or "unknown-period")


def _metric_value(metrics: tuple[ReportMetric, ...], label: str) -> str:
    for metric in metrics:
        if metric.label == label:
            return f"{metric.value}{metric.unit}" if metric.unit else metric.value
    return "No data"


def _risk_from_metric(metrics: tuple[ReportMetric, ...]) -> str:
    for metric in metrics:
        if metric.label == "Composite score":
            return metric.severity
    return "unknown"


def _looks_like_source(value: str) -> bool:
    return any(marker in value for marker in ("MODIS", "CHIRPS", "source ", "demo-", "mwangaza."))


def _metric_versions(metrics: tuple[ReportMetric, ...]) -> tuple[str, ...]:
    values: list[str] = []
    for metric in metrics:
        if "version" in metric.detail.lower() or "demo" in metric.detail.lower():
            values.append(metric.detail)
    return tuple(values)


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _safe_url(value: str) -> str:
    value = value.strip()
    if value.startswith(("https://", "http://")) and not any(char in value for char in "<>\"'"):
        return value
    return ""


def _qr_matrix(value: str) -> tuple[str, ...]:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    bits = bin(int(digest[:21], 16))[2:].zfill(84)
    rows = []
    for index in range(9):
        row = bits[index * 9 : index * 9 + 9]
        rows.append(row.ljust(9, "0"))
    return tuple(rows)


def _render_qr(context: ExecutiveReportContext) -> str:
    if not context.dashboard_url or not context.qr_matrix:
        return ""
    cells = "".join(
        f'<i class="{"on" if value == "1" else "off"}"></i>'
        for row in context.qr_matrix
        for value in row
    )
    return (
        "<h2>Dashboard Link</h2>"
        f'<p class="meta">{escape(context.dashboard_url)}</p>'
        f'<div class="qr" aria-label="Deterministic QR placeholder">{cells}</div>'
    )


def _bar_width(metric: ReportMetric) -> int:
    match = re.search(r"-?\d+(?:\.\d+)?", metric.value)
    if not match:
        return 12
    value = abs(float(match.group(0)))
    if metric.label == "Composite score":
        return max(3, min(100, round(value)))
    return max(3, min(100, round(value * 3 if value < 10 else value)))


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "report"


__all__ = [
    "ExecutiveReportContext",
    "ReportMetric",
    "build_executive_report_context",
    "render_executive_report_html",
    "render_executive_report_pdf",
    "safe_report_filename",
]
