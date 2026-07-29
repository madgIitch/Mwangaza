from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from typing import Any

from mwangaza.services.drought_continuation import (
    DroughtContinuationServiceError,
    load_continuation_snapshot,
)


@dataclass(frozen=True)
class ReportMetric:
    label: str
    value: str
    unit: str
    detail: str
    severity: str


@dataclass(frozen=True)
class ReportContinuationEstimate:
    region_id: str
    as_of: str
    horizon_days: int
    phase: str
    kind: str
    status: str
    probability: float | None
    model: str
    validation_status: str
    quality_status: str
    artifact_version: str
    skill_score: float | None = None
    interval_95: tuple[float, float] | None = None
    target: str = "same_episode_continues"


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
    continuation: tuple[ReportContinuationEstimate, ...] = ()
    dashboard_url: str = ""
    qr_matrix: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReportRecord:
    id: str
    generated_at: str
    updated_at: str
    expires_at: str | None
    status: str
    region_id: str
    region: str
    period_start: str
    period_end: str
    template_id: str
    language: str
    author: str
    snapshot_id: str
    formats: tuple[str, ...]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "generated_at": self.generated_at, "updated_at": self.updated_at,
            "expires_at": self.expires_at, "status": self.status, "region_id": self.region_id,
            "region": self.region, "period_start": self.period_start, "period_end": self.period_end,
            "template_id": self.template_id, "language": self.language, "author": self.author,
            "snapshot_id": self.snapshot_id, "formats": list(self.formats), "error": self.error,
        }


def build_report_records(data: Any) -> tuple[ReportRecord, ...]:
    """Create stable backend-owned records from the materialized regional snapshot."""
    snapshot_id = str(getattr(data, "snapshot_id", "") or _snapshot_id(data))
    records: list[ReportRecord] = []
    for region in getattr(getattr(data, "risk_map", None), "regions", ()):
        region_id = str(getattr(region, "region_id", "")).lower()
        if not region_id or "-" in region_id:
            continue
        period_start = str(getattr(region, "period_start", "") or "")
        period_end = str(getattr(region, "period_end", "") or "")
        generated_at = _iso_timestamp(period_end)
        identity = hashlib.sha256(f"{region_id}|{period_start}|{period_end}|executive-v1|en".encode()).hexdigest()[:10].upper()
        records.append(ReportRecord(
            id=f"RPT-{region_id.upper()}-{identity}", generated_at=generated_at,
            updated_at=generated_at, expires_at=None, status="ready", region_id=region_id,
            region=str(getattr(region, "name", "") or region_id.upper()), period_start=period_start,
            period_end=period_end, template_id="executive-v1", language="en",
            author="Mwangaza automated report", snapshot_id=snapshot_id,
            formats=("pdf", "csv", "json"),
        ))
    return tuple(sorted(records, key=lambda item: (item.generated_at, item.id), reverse=True))


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
    continuation = _continuation_for_region(selected_region)
    return ExecutiveReportContext(
        region_id=selected_region,
        region_label=str(getattr(profile, "label", "") or getattr(data, "selected_region", "") or selected_region.upper()),
        period_label=period_label,
        generated_at=generated,
        score=_metric_value(metrics, "Composite score"),
        risk_level=_risk_from_metric(metrics),
        quality=_metric_value(metrics, "Data quality"),
        metrics=metrics,
        recommendations=tuple(str(item) for item in getattr(profile, "recommendations", ()) or getattr(data, "recommendations", ())),
        sources=source_values or ("No source metadata available",),
        versions=version_values or ("No version metadata available",),
        limitations=(
            "This report is a decision-support prototype, not an official alert.",
            "`potentially_exposed` is potential exposure, not measured impact.",
            "Observed, cached and demo/synthetic data must be interpreted separately.",
            "Drought continuation estimates describe persistence of the active observed condition; they do not predict onset, exact duration or human impact.",
        ),
        continuation=continuation,
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
    continuation = _render_continuation_html(context.continuation)
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
  {continuation}
  <h2>Sources and Versions</h2>
  <ul>{sources}{versions}</ul>
  <h2>Limitations</h2>
  <ul>{limitations}</ul>
  {qr}
</body>
</html>"""


def render_executive_report_pdf(context: ExecutiveReportContext) -> bytes:
    lines = [
        "Mwangaza Executive Report", f"Region: {context.region_label}",
        f"Period: {context.period_label}", f"Generated: {context.generated_at}",
        f"Composite score: {context.score}", f"Risk level: {context.risk_level}",
        f"Quality: {context.quality}", "", "Snapshot indicators",
        *(f"{metric.label}: {metric.value} {metric.unit} - {metric.severity}" for metric in context.metrics),
        "", "Recommended actions", *(f"- {item}" for item in context.recommendations),
        "", "Drought continuation", *_continuation_pdf_lines(context.continuation),
        "", "Sources and versions", *(f"- {item}" for item in (*context.sources, *context.versions)),
        "", "Limitations", *(f"- {item}" for item in context.limitations),
    ]
    return _simple_pdf(lines)


def safe_report_filename(context: ExecutiveReportContext) -> str:
    region = _slug(context.region_label or context.region_id)
    period = _slug(context.period_label)
    return f"mwangaza-executive-report-{region}-{period}.pdf"


def _profile_for_region(data: Any, region_id: str) -> Any:
    for profile in getattr(data, "region_profiles", ()):
        if getattr(profile, "region_id", "") == region_id:
            return profile
    return getattr(data, "region_profiles", (None,))[0] if getattr(data, "region_profiles", ()) else data


def _continuation_for_region(region_id: str) -> tuple[ReportContinuationEstimate, ...]:
    try:
        snapshot = load_continuation_snapshot()
    except (DroughtContinuationServiceError, OSError, ValueError):
        return ()
    prefix = _continuation_region_prefix(region_id)
    rows: list[ReportContinuationEstimate] = []
    for item in snapshot.items:
        if item.status == "not_applicable" or not (
            item.region_id == region_id or (prefix and item.region_id.startswith(prefix))
        ):
            continue
        for estimate in item.estimates:
            interval = estimate.validation.get("bootstrap_delta_brier_ci95")
            interval_95 = (
                (float(interval[0]), float(interval[1]))
                if isinstance(interval, list) and len(interval) == 2
                else None
            )
            rows.append(
                ReportContinuationEstimate(
                    region_id=item.region_id,
                    as_of=item.as_of,
                    horizon_days=item.horizon_days,
                    phase=item.current_phase,
                    kind=estimate.kind,
                    status=estimate.status,
                    probability=estimate.probability,
                    model=estimate.model,
                    validation_status=str(estimate.validation.get("status") or "unknown"),
                    quality_status=str(estimate.quality.get("status") or "unknown"),
                    artifact_version=str(
                        estimate.artifact.get("schema_version") or "historical-reference"
                    ),
                    skill_score=(
                        float(estimate.validation["episode_weighted_brier_skill_score"])
                        if isinstance(
                            estimate.validation.get("episode_weighted_brier_skill_score"),
                            (int, float),
                        )
                        else None
                    ),
                    interval_95=interval_95,
                    target=item.target,
                )
            )
    return tuple(sorted(rows, key=lambda row: (row.region_id, row.horizon_days, row.kind)))


def _continuation_region_prefix(region_id: str) -> str:
    iso2 = {
        "dji": "dj", "eri": "er", "eth": "et", "ken": "ke",
        "sdn": "sd", "som": "so", "ssd": "ss", "uga": "ug",
    }.get(region_id)
    return f"adm1-{iso2}-" if iso2 else ""


def _render_continuation_html(rows: tuple[ReportContinuationEstimate, ...]) -> str:
    if not rows:
        return "<h2>Drought Continuation</h2><p class=\"note\">No applicable materialized continuation estimate is available.</p>"
    body = "".join(
        "<tr><td>{region}</td><td>{as_of}</td><td>{phase}</td><td>{horizon} days</td><td>{kind}</td><td>{probability}</td><td>{method}</td><td>{evidence}</td></tr>".format(
            region=escape(row.region_id),
            as_of=escape(row.as_of[:10]),
            phase=escape(row.phase),
            horizon=row.horizon_days,
            kind=escape(_continuation_kind_label(row.kind)),
            probability=escape(_report_probability(row)),
            method=escape(row.model),
            evidence=escape(_continuation_evidence(row)),
        )
        for row in rows
    )
    satellite = any(row.target == "observed_drought_condition_continues" for row in rows)
    scope = (
        "Probability that the same observed multisignal drought condition continues."
        if satellite else "Probability that the same officially active episode continues."
    )
    return (
        "<h2>Drought Continuation</h2>"
        f"<p class=\"note\">{escape(scope)} Experimental ML: Not for operational use.</p>"
        "<table><thead><tr><th>Region</th><th>As of</th><th>Phase</th><th>Horizon</th><th>Estimate</th><th>Probability</th><th>Method</th><th>Evidence</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _continuation_pdf_lines(rows: tuple[ReportContinuationEstimate, ...]) -> tuple[str, ...]:
    if not rows:
        return ("No applicable materialized continuation estimate is available.",)
    satellite = any(row.target == "observed_drought_condition_continues" for row in rows)
    return (
        (
            "Same observed multisignal drought condition only; experimental ML is inconclusive and not for operational use."
            if satellite else
            "Same officially active episode only; experimental ML is inconclusive and not for operational use."
        ),
        *(
            f"{row.region_id} | {row.as_of[:10]} | {row.phase} | {row.horizon_days} days | {_continuation_kind_label(row.kind)} | {_report_probability(row)} | {row.model} | {_continuation_evidence(row)}"
            for row in rows
        ),
    )


def _continuation_kind_label(kind: str) -> str:
    return "Experimental ML prediction" if kind == "experimental_ml_prediction" else "Historical reference"


def _report_probability(row: ReportContinuationEstimate) -> str:
    return f"{row.probability * 100:.1f}%" if row.status == "available" and row.probability is not None else "Unavailable"


def _continuation_evidence(row: ReportContinuationEstimate) -> str:
    parts = [row.validation_status, row.quality_status, row.artifact_version]
    if row.skill_score is not None:
        parts.append(f"BSS {row.skill_score * 100:+.1f}%")
    if row.interval_95 is not None:
        parts.append(f"IC95 [{row.interval_95[0]:.4f}, {row.interval_95[1]:.4f}]")
    return " / ".join(parts)


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


def _snapshot_id(data: Any) -> str:
    raw = "|".join(
        f"{getattr(region, 'region_id', '')}:{getattr(region, 'period_end', '')}:{getattr(region, 'score', '')}"
        for region in getattr(getattr(data, "risk_map", None), "regions", ())
    )
    return f"snapshot-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def _iso_timestamp(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        return "1970-01-01T00:00:00+00:00"
    if len(candidate) == 10:
        return f"{candidate}T00:00:00+00:00"
    return candidate.replace("Z", "+00:00")


def _simple_pdf(lines: list[str]) -> bytes:
    """Render a dependency-free, standards-compliant single-page PDF."""
    wrapped: list[str] = []
    for line in lines:
        clean = line.encode("ascii", errors="replace").decode("ascii")
        if not clean:
            wrapped.append("")
            continue
        while len(clean) > 88:
            split_at = clean.rfind(" ", 0, 88)
            split_at = split_at if split_at > 30 else 88
            wrapped.append(clean[:split_at])
            clean = clean[split_at:].lstrip()
        wrapped.append(clean)
    wrapped = wrapped[:47]
    commands = ["BT", "/F1 16 Tf", "54 790 Td"]
    for index, line in enumerate(wrapped):
        if index == 1:
            commands.extend(["/F1 10 Tf"])
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.extend([f"({escaped}) Tj", "0 -15 Td"])
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(output.tell())
        output.write(f"{number} 0 obj\n".encode())
        output.write(obj)
        output.write(b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode())
    output.write(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return output.getvalue()


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
    "ReportContinuationEstimate",
    "ReportMetric",
    "build_executive_report_context",
    "build_report_records",
    "ReportRecord",
    "render_executive_report_html",
    "render_executive_report_pdf",
    "safe_report_filename",
]
