from __future__ import annotations

import json
from collections.abc import Callable
from html import escape
from typing import Any

from mwangaza.services.dashboard_shell import (
    DashboardShellData,
    fallback_dashboard_shell_data,
    load_dashboard_shell_data,
)
from mwangaza.maps import build_regional_risk_map_html

SAFE_ERROR_MESSAGE = "Dashboard data could not be loaded. Showing a safe fallback shell."


def build_dashboard_shell_html(data: DashboardShellData, *, safe_error: bool = False) -> str:
    shell_id = _shell_dom_id(data)
    nav = "\n".join(
        f'<button class="nav-item{" is-active" if item.active else ""}" '
        f'type="button" data-nav-target="{escape(item.key)}">'
        f"<span>{escape(item.label)}</span></button>"
        for item in data.navigation
    )
    metrics = "\n".join(
        '<section class="metric-card" data-severity="{severity}">'
        '<span class="metric-label">{label}</span>'
        '<strong>{value}<small>{unit}</small></strong>'
        '<p>{detail}</p>'
        "</section>".format(
            severity=escape(metric.severity),
            label=escape(metric.label),
            value=escape(metric.value),
            unit=escape(metric.unit),
            detail=escape(metric.detail),
        )
        for metric in data.metrics
    )
    trends = _render_trends(data.trends)
    alerts = _render_alerts(data)
    risk_map = build_regional_risk_map_html(data.risk_map)
    selected_region = _selected_map_region(data)
    region_options = _render_region_options(data)
    region_profiles_json = _region_profiles_json(data)
    temporal_periods_json = _temporal_periods_json(data)
    temporal_options = _render_temporal_options(data)
    selected_period = _selected_temporal_period(data)
    region_panel = _render_region_panel(data)
    recommendations = "\n".join(
        f"<li>{escape(recommendation)}</li>" for recommendation in data.recommendations
    )
    mode_chips = "\n".join(
        '<span class="mode-chip{active}" data-mode="{mode}">{label}</span>'.format(
            active=" is-active" if data.data_status.mode == mode else "",
            mode=mode,
            label=label,
        )
        for mode, label in (("live", "Live data"), ("cache", "Cache data"), ("demo", "Demo data"))
    )
    error_banner = (
        f'<div class="safe-error" role="alert">{escape(SAFE_ERROR_MESSAGE)}</div>'
        if safe_error
        else ""
    )

    return f"""
<style>
:root {{
  --mwa-bg: #f6f8fa;
  --mwa-panel: #ffffff;
  --mwa-border: #dfe4ea;
  --mwa-border-soft: #e8ecf1;
  --mwa-text: #0f1727;
  --mwa-muted: #667085;
  --mwa-green: #18853b;
  --mwa-green-soft: #e9f5eb;
  --mwa-yellow: #f7bb0c;
  --mwa-orange: #ff8513;
  --mwa-red: #e9322c;
  --mwa-blue: #1d5fbf;
  --mwa-shadow: 0 1px 4px rgba(24, 35, 52, .11);
}}
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--mwa-bg);
  color: var(--mwa-text);
  overflow-x: hidden;
}}
.mwa-shell, .mwa-shell * {{
  box-sizing: border-box;
  min-width: 0;
}}
.mwa-shell {{
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  grid-template-rows: 84px minmax(0, 1fr) 48px;
  width: 100%;
  max-width: 1366px;
  margin: 0 auto;
  min-height: 900px;
  font-family: Inter, Segoe UI, Arial, sans-serif;
  background: linear-gradient(#fbfcfd, #f7f9fb);
}}
.sidebar, .topbar, .panel, .metric-card {{
  background: var(--mwa-panel);
  border: 1px solid var(--mwa-border);
  border-radius: 8px;
  box-shadow: var(--mwa-shadow);
}}
.topbar {{
  grid-column: 1 / -1;
  grid-row: 1;
  min-height: 84px;
  padding: 0 24px;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) auto;
  gap: 18px;
  align-items: center;
  border-radius: 0;
  border-left: 0;
  border-right: 0;
  border-top: 0;
  box-shadow: none;
}}
.sidebar {{
  grid-column: 1;
  grid-row: 2;
  min-height: 0;
  padding: 20px 13px 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  border-left: 0;
  border-top: 0;
  border-bottom: 0;
  border-radius: 0;
  box-shadow: none;
}}
.brand-row {{
  display: flex;
  align-items: center;
  gap: 14px;
}}
.brand-mark {{
  width: 52px;
  height: 52px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--mwa-yellow) 0 45%, var(--mwa-green) 46% 100%);
}}
.brand-title {{
  margin: 0;
  font-size: 27px;
  line-height: 1.1;
  color: #17233b;
}}
.tagline {{
  margin: 6px 0 0;
  color: #4e5970;
  font-size: 13px;
}}
.nav-stack {{
  display: grid;
  gap: 3px;
}}
.nav-item {{
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  border: 0;
  color: var(--mwa-text);
  background: transparent;
  min-height: 56px;
  padding: 0 18px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: left;
  cursor: pointer;
}}
.nav-item.is-active {{
  background: linear-gradient(90deg, #f0f7f1, #f5f8f5);
  color: #08742b;
  font-weight: 700;
}}
.nav-item.is-active::before {{
  content: "";
  position: absolute;
  left: 0;
  top: 9px;
  bottom: 9px;
  width: 4px;
  border-radius: 4px;
  background: #0a8a33;
}}
.mode-stack {{
  margin-top: auto;
  display: grid;
  gap: 7px;
}}
.mode-chip {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--mwa-border);
  border-radius: 999px;
  padding: 6px 9px;
  color: var(--mwa-muted);
  font-size: 12px;
}}
.mode-chip[data-mode="live"] {{ border-color: #b8dbc8; }}
.mode-chip[data-mode="cache"] {{ border-color: #ead88e; }}
.mode-chip[data-mode="demo"] {{ border-color: #b8cce0; }}
.mode-chip.is-active {{
  background: var(--mwa-green-soft);
  color: var(--mwa-green);
  font-weight: 700;
}}
.status-band {{
  justify-self: center;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 12px;
  min-height: 44px;
  padding: 8px 18px;
  border-radius: 24px;
  background: #f3f5f8;
  color: #384259;
  font-size: 12px;
}}
.status-divider {{
  width: 1px;
  height: 18px;
  background: #d8dde5;
}}
.status-mode {{
  justify-self: end;
  display: grid;
  place-items: center;
  min-width: 56px;
  height: 34px;
  border-radius: 999px;
  background: var(--mwa-green-soft);
  color: var(--mwa-green);
  font-size: 12px;
  font-weight: 800;
}}
.period-control {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--mwa-muted);
  font-size: 11px;
  font-weight: 700;
}}
.period-control select {{
  border: 1px solid var(--mwa-border);
  border-radius: 7px;
  background: #fff;
  color: var(--mwa-text);
  padding: 6px 9px;
}}
.period-state {{
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 4px 8px;
  background: var(--mwa-green-soft);
  color: var(--mwa-green);
  font-size: 11px;
  font-weight: 800;
}}
.period-state[data-period-status="partial"] {{
  background: #fff7d8;
  color: #8a6500;
}}
.main {{
  grid-column: 2;
  grid-row: 2;
  display: grid;
  gap: 12px;
  padding: 13px 14px 8px 15px;
  overflow: hidden;
}}
.page-title {{
  margin: 0;
  font-size: 18px;
  line-height: 1.1;
}}
.status-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}}
.status-pill {{
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 6px 10px;
  background: var(--mwa-green-soft);
  color: var(--mwa-green);
  font-size: 12px;
  font-weight: 700;
}}
.status-pill[data-freshness="stale"] {{ background: #fff7d8; color: #8a6500; }}
.status-pill[data-freshness="error"] {{ background: #fdecec; color: var(--mwa-red); }}
.timestamp {{
  color: var(--mwa-muted);
  font-size: 12px;
}}
.safe-error {{
  border: 1px solid #f1b5b5;
  background: #fff3f3;
  color: #8b1e1e;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
}}
.workspace {{
  display: grid;
  grid-template-columns: minmax(660px, 1.28fr) minmax(360px, 0.72fr);
  gap: 14px;
  min-height: 0;
}}
.panel {{
  padding: 0;
  overflow: hidden;
}}
.panel h2 {{
  margin: 0;
  font-size: 16px;
}}
.panel-header {{
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 14px;
  border-bottom: 1px solid var(--mwa-border);
}}
.panel-body {{
  padding: 12px;
}}
.map-panel {{
  min-height: 416px;
}}
.regional-risk-map {{
  display: grid;
  gap: 10px;
}}
.regional-risk-svg {{
  width: 100%;
  height: 300px;
  border-radius: 8px;
  border: 1px solid #d7e0da;
  background: #eef4f0;
}}
.risk-region {{
  stroke: #ffffff;
  stroke-width: 2;
  cursor: pointer;
  transition: opacity 120ms ease, stroke-width 120ms ease;
}}
.risk-region:focus,
.risk-region:hover {{
  opacity: 0.78;
  stroke-width: 4;
  outline: none;
}}
.risk-region.is-selected {{
  stroke: #17231c;
  stroke-width: 4;
}}
.risk-region.is-active {{
  filter: drop-shadow(0 2px 3px rgba(23, 35, 28, 0.28));
}}
.risk-green {{ fill: var(--mwa-green); }}
.risk-yellow {{ fill: var(--mwa-yellow); }}
.risk-orange {{ fill: var(--mwa-orange); }}
.risk-red {{ fill: var(--mwa-red); }}
.risk-unknown {{ fill: #8c9690; }}
.risk-map-legend {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--mwa-muted);
  font-size: 12px;
}}
.risk-legend-item {{
  display: inline-flex;
  align-items: center;
  gap: 5px;
}}
.risk-legend-item i {{
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: currentColor;
}}
.risk-legend-item.risk-green {{ color: var(--mwa-green); }}
.risk-legend-item.risk-yellow {{ color: #9a7300; }}
.risk-legend-item.risk-orange {{ color: var(--mwa-orange); }}
.risk-legend-item.risk-red {{ color: var(--mwa-red); }}
.risk-legend-item.risk-unknown {{ color: #6f7973; }}
.region-readout {{
  border: 1px solid #d7e0da;
  border-radius: 8px;
  padding: 9px 10px;
  background: #fbfdfc;
}}
.region-readout strong {{
  display: block;
  font-size: 14px;
}}
.region-readout span {{
  display: block;
  margin-top: 3px;
  color: var(--mwa-muted);
  font-size: 12px;
}}
.region-toolbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}}
.region-toolbar select {{
  border: 1px solid var(--mwa-border);
  border-radius: 8px;
  background: #ffffff;
  color: var(--mwa-text);
  padding: 7px 9px;
  min-width: 150px;
}}
.region-detail {{
  min-height: 220px;
}}
.region-detail h3 {{
  margin: 10px 0 0;
  font-size: 16px;
}}
.region-detail p {{
  margin: 5px 0 0;
  color: var(--mwa-muted);
  font-size: 12px;
}}
.pilot-ranking {{
  display: grid;
  gap: 8px;
  margin-top: 10px;
}}
.pilot-unit {{
  border: 1px solid var(--mwa-border);
  border-left: 4px solid #8c9690;
  border-radius: 8px;
  padding: 9px;
}}
.pilot-unit[data-risk-level="watch"] {{ border-left-color: var(--mwa-yellow); }}
.pilot-unit[data-risk-level="warning"] {{ border-left-color: var(--mwa-orange); }}
.pilot-unit[data-risk-level="emergency"] {{ border-left-color: var(--mwa-red); }}
.pilot-unit strong {{
  display: block;
  font-size: 13px;
}}
.pilot-unit span {{
  display: block;
  margin-top: 3px;
  color: var(--mwa-muted);
  font-size: 12px;
}}
.legend {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
  color: var(--mwa-muted);
  font-size: 12px;
}}
.legend span::before {{
  content: "";
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-right: 5px;
  background: currentColor;
}}
.metrics-grid {{
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 7px;
}}
.metric-card {{
  padding: 10px 9px 8px;
  min-height: 106px;
  box-shadow: none;
  text-align: center;
}}
.metric-card strong {{
  display: block;
  margin-top: 7px;
  font-size: 21px;
  font-weight: 700;
}}
.metric-card small {{
  margin-left: 3px;
  color: var(--mwa-muted);
  font-size: 12px;
}}
.metric-label, .metric-card p {{
  color: var(--mwa-muted);
  font-size: 11px;
}}
.metric-card p {{
  margin: 8px 0 0;
}}
.metric-card[data-severity="critical"] {{ border-left: 4px solid var(--mwa-red); }}
.metric-card[data-severity="warning"] {{ border-left: 4px solid var(--mwa-orange); }}
.metric-card[data-severity="watch"] {{ border-left: 4px solid var(--mwa-yellow); }}
.metric-card[data-severity="normal"] {{ border-left: 4px solid var(--mwa-green); }}
.trends-panel .panel-body {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}}
.trend-card {{
  border: 1px solid var(--mwa-border);
  border-radius: 8px;
  padding: 10px;
  background: #fff;
}}
.trend-card h3 {{
  margin: 0;
  font-size: 13px;
}}
.trend-meta, .trend-detail {{
  margin: 5px 0 0;
  color: var(--mwa-muted);
  font-size: 10px;
}}
.trend-chart {{
  width: 100%;
  height: 112px;
  margin-top: 8px;
}}
.trend-observed {{
  fill: none;
  stroke: var(--mwa-green);
  stroke-width: 2.4;
}}
.trend-baseline {{
  fill: none;
  stroke: #586579;
  stroke-width: 1.8;
  stroke-dasharray: 6 4;
}}
.trend-point {{
  fill: #fff;
  stroke: var(--mwa-green);
  stroke-width: 2;
}}
.trend-gap {{
  fill: var(--mwa-red);
}}
.trend-axis {{
  stroke: #e4e8ee;
  stroke-width: 1;
}}
.trend-empty {{
  border: 1px dashed var(--mwa-border);
  border-radius: 8px;
  padding: 12px;
  color: var(--mwa-muted);
  font-size: 12px;
}}
.alert-list {{
  display: grid;
  gap: 8px;
}}
.alert-filters {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}}
.alert-filters label {{
  display: grid;
  gap: 4px;
  color: var(--mwa-muted);
  font-size: 11px;
  font-weight: 700;
}}
.alert-filters select {{
  width: 100%;
  border: 1px solid var(--mwa-border);
  border-radius: 8px;
  padding: 7px 8px;
  background: #fff;
  color: var(--mwa-text);
}}
.alert-item {{
  border: 1px solid var(--mwa-border);
  border-left: 4px solid var(--mwa-yellow);
  border-radius: 8px;
  padding: 10px;
}}
.alert-item[data-severity="critical"] {{ border-left-color: var(--mwa-red); }}
.alert-item[data-severity="warning"] {{ border-left-color: var(--mwa-orange); }}
.alert-item[data-severity="normal"] {{ border-left-color: var(--mwa-green); }}
.alert-item[data-severity="unknown"] {{ border-left-color: #98a2b3; }}
.alert-heading {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}}
.alert-rank {{
  flex: 0 0 auto;
  color: var(--mwa-muted);
  font-size: 11px;
  font-weight: 700;
}}
.alert-item h3 {{
  margin: 0;
  font-size: 14px;
}}
.alert-item p, .recommendations li {{
  color: var(--mwa-muted);
  font-size: 12px;
}}
.alert-evidence {{
  display: grid;
  gap: 2px;
  margin-top: 6px;
  padding: 0;
  list-style: none;
}}
.alert-evidence li {{
  color: var(--mwa-muted);
  font-size: 11px;
}}
.alert-action {{
  display: inline-block;
  margin-top: 6px;
  color: var(--mwa-green);
  font-weight: 700;
  font-size: 12px;
}}
.recommendations {{
  margin: 0;
  padding-left: 18px;
}}
.side-column {{
  display: grid;
  grid-template-rows: minmax(190px, auto) minmax(160px, auto) minmax(105px, auto);
  gap: 12px;
}}
.main-column {{
  display: grid;
  grid-template-rows: auto auto auto;
  gap: 12px;
  min-width: 0;
}}
.footer {{
  grid-column: 1 / -1;
  grid-row: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 24px 0 274px;
  background: #fff;
  border-top: 1px solid #e2e6eb;
  color: #4e5b70;
  font-size: 10px;
}}
.footer-note {{
  color: var(--mwa-muted);
  font-size: 11px;
}}
@media (max-width: 1120px) {{
  .mwa-shell {{
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto auto;
  }}
  .topbar, .sidebar, .main, .footer {{
    grid-column: 1;
  }}
  .topbar {{
    grid-template-columns: 1fr;
  }}
  .sidebar {{
    grid-row: 2;
    border-right: 0;
    border-bottom: 1px solid var(--mwa-border);
  }}
  .main {{
    grid-row: 3;
  }}
  .footer {{
    grid-row: 4;
    padding: 12px 16px;
    flex-wrap: wrap;
  }}
  .workspace {{
    grid-template-columns: 1fr;
  }}
  .metrics-grid {{
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }}
  .trends-panel .panel-body {{
    grid-template-columns: 1fr;
  }}
}}
@media (max-width: 560px) {{
  .metrics-grid {{
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }}
}}
</style>
<div class="mwa-shell" data-shell-id="{escape(shell_id)}">
  <header class="topbar">
    <div class="brand-row">
      <div class="brand-mark" aria-hidden="true"></div>
      <div>
        <h1 class="brand-title">{escape(data.project)}</h1>
        <p class="tagline">{escape(data.tagline)}</p>
      </div>
    </div>
    <div class="status-band" aria-label="Data status">
      <span><strong>Data source:</strong> {escape(data.data_status.source)}</span>
      <span class="status-divider"></span>
      <span><strong>Last update:</strong> {escape(data.data_status.last_updated)}</span>
      <span class="status-divider"></span>
      <span><strong>{escape(data.data_status.message)}</strong></span>
    </div>
    <div class="status-mode" data-mode="{escape(data.data_status.mode)}">{escape(data.data_status.mode.upper())}</div>
  </header>
  <aside class="sidebar" aria-label="Mwangaza navigation">
    <nav class="nav-stack">{nav}</nav>
    <div class="mode-stack" aria-label="Data origin modes">{mode_chips}</div>
  </aside>
  <main class="main">
    {error_banner}
    <section class="workspace">
      <div class="main-column">
        <section class="panel map-panel" id="overview">
          <div class="panel-header">
            <h2>Regional Risk Map - IGAD <span data-period-title>{escape(selected_period.label)}</span></h2>
            <label class="period-control">
              Period
              <select data-period-selector>{temporal_options}</select>
              <span class="period-state" data-period-status="{escape(selected_period.status)}">{escape(selected_period.status)}</span>
            </label>
          </div>
          <div class="panel-body">
            <div data-risk-map-slot>{risk_map}</div>
            <div class="region-readout" aria-live="polite">
              <strong data-region-readout-name>{escape(selected_region.name)}</strong>
              <span data-region-readout-detail>
                Score: {escape(selected_region.score_label)} | Level: {escape(selected_region.color_level)} |
                Period: {escape(selected_region.period)} | Quality: {escape(selected_region.quality_flag)}
              </span>
            </div>
            <p class="footer-note">Selected region: <span data-selected-region-label>{escape(data.selected_region)}</span></p>
          </div>
        </section>
        <section class="panel region-detail" id="region">
          <div class="panel-header region-toolbar">
            <div>
              <h2>Region</h2>
            </div>
            <label>
              <span class="footer-note">Country</span>
              <select data-region-selector>{region_options}</select>
            </label>
          </div>
          <div class="panel-body" data-region-detail>{region_panel}</div>
        </section>
        <section class="metrics-grid" data-region-metrics>{metrics}</section>
        <section class="panel trends-panel" id="trends">
          <div class="panel-header"><h2>Indicator Trends</h2></div>
          <div class="panel-body" data-region-trends>{trends}</div>
        </section>
      </div>
      <aside class="side-column">
        <section class="panel" id="alerts">
          <div class="panel-header"><h2>Active Alerts</h2></div>
          <div class="panel-body">
            {_render_alert_filters(data)}
            <div data-alert-panel>{alerts}</div>
          </div>
        </section>
        <section class="panel" id="reports">
          <div class="panel-header"><h2>Early Action Recommendations</h2></div>
          <div class="panel-body"><ul class="recommendations">{recommendations}</ul></div>
        </section>
        <section class="panel" id="about">
          <div class="panel-header"><h2>About</h2></div>
          <div class="panel-body">
            <p class="footer-note">
              Prototype dashboard shell. Observed, cached and demo data are labelled separately.
            </p>
          </div>
        </section>
      </aside>
    </section>
  </main>
  <footer class="footer">
    <div>Mwangaza is a decision-support prototype. Use satellite observations alongside local knowledge.</div>
    <div>IGAD regional drought operations</div>
  </footer>
</div>
<script type="application/json" data-region-profiles="{escape(shell_id)}">{region_profiles_json}</script>
<script type="application/json" data-temporal-periods="{escape(shell_id)}">{temporal_periods_json}</script>
<script>
(() => {{
  const currentScript = document.currentScript;
  const temporalScript = currentScript?.previousElementSibling;
  const dataScript = temporalScript?.previousElementSibling;
  const shellId = dataScript?.getAttribute("data-region-profiles") || "";
  const root = Array.from(document.querySelectorAll(".mwa-shell"))
    .find((candidate) => candidate.dataset.shellId === shellId);
  if (
    !root
    || dataScript?.getAttribute("data-region-profiles") !== shellId
    || temporalScript?.getAttribute("data-temporal-periods") !== shellId
  ) return;
  if (root.dataset.mwangazaInteractive === "1") return;
  root.dataset.mwangazaInteractive = "1";
  let profiles = dataScript?.textContent ? JSON.parse(dataScript.textContent) : {{}};
  const periods = temporalScript?.textContent ? JSON.parse(temporalScript.textContent) : [];
  let paths = [];
  const selectedLabel = root.querySelector("[data-selected-region-label]");
  const readoutName = root.querySelector("[data-region-readout-name]");
  const readoutDetail = root.querySelector("[data-region-readout-detail]");
  const selector = root.querySelector("[data-region-selector]");
  const periodSelector = root.querySelector("[data-period-selector]");
  const periodTitle = root.querySelector("[data-period-title]");
  const periodState = root.querySelector("[data-period-status]");
  const mapSlot = root.querySelector("[data-risk-map-slot]");
  const detail = root.querySelector("[data-region-detail]");
  const metricsGrid = root.querySelector("[data-region-metrics]");
  const trendsGrid = root.querySelector("[data-region-trends]");
  const navButtons = Array.from(root.querySelectorAll("[data-nav-target]"));
  const alertPanel = root.querySelector("[data-alert-panel]");
  const alertFilters = Array.from(root.querySelectorAll("[data-alert-filter]"));

  function escapeHtml(value) {{
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({{
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }}[char]));
  }}

  function metricHtml(metric) {{
    return `<section class="metric-card" data-severity="${{escapeHtml(metric.severity)}}">`
      + `<span class="metric-label">${{escapeHtml(metric.label)}}</span>`
      + `<strong>${{escapeHtml(metric.value)}}<small>${{escapeHtml(metric.unit)}}</small></strong>`
      + `<p>${{escapeHtml(metric.detail)}}</p></section>`;
  }}

  function alertsHtml(alerts) {{
    if (!alerts.length) return '<p class="footer-note" data-alert-empty>No active alerts available for this region.</p>';
    const items = alerts.map((alert) => `<article class="alert-item" data-severity="${{escapeHtml(alert.severity)}}" data-region-id="${{escapeHtml(alert.region_id)}}" data-region-type="${{escapeHtml(alert.region_type)}}">`
      + `<div class="alert-heading"><h3>${{escapeHtml(alert.title)}}</h3><span class="alert-rank">#${{escapeHtml(alert.priority_rank || "")}}</span></div>`
      + `<p>${{escapeHtml(alert.region)}} - ${{escapeHtml(alert.period)}} | Quality: ${{escapeHtml(alert.quality_flag)}}</p>`
      + evidenceHtml(alert.evidence)
      + `<span class="alert-action">${{escapeHtml(alert.action)}}</span></article>`).join("");
    return `<div class="alert-list">${{items}}</div><p class="footer-note" data-alert-filter-empty hidden>No alerts match the selected filters.</p>`;
  }}

  function evidenceHtml(items) {{
    if (!items || !items.length) return "";
    return `<ul class="alert-evidence">${{items.map((item) => `<li>${{escapeHtml(item[0])}}: ${{escapeHtml(item[1])}}</li>`).join("")}}</ul>`;
  }}

  function applyAlertFilters() {{
    const severity = root.querySelector('[data-alert-filter="severity"]')?.value || "all";
    const region = root.querySelector('[data-alert-filter="region"]')?.value || "all";
    const type = root.querySelector('[data-alert-filter="type"]')?.value || "all";
    const items = Array.from(alertPanel?.querySelectorAll(".alert-item") || []);
    let visible = 0;
    items.forEach((item) => {{
      const show = (severity === "all" || item.dataset.severity === severity)
        && (region === "all" || item.dataset.regionId === region)
        && (type === "all" || item.dataset.regionType === type);
      item.hidden = !show;
      if (show) visible += 1;
    }});
    const empty = alertPanel?.querySelector("[data-alert-filter-empty]");
    if (empty) empty.hidden = visible !== 0 || items.length === 0;
  }}

  function pilotHtml(units) {{
    if (!units.length) {{
      return '<p class="footer-note">Subnational pilot is not enabled for this country in 1.0; IGAD coverage remains national here.</p>';
    }}
    return '<div class="pilot-ranking">' + units.map((unit) => `<article class="pilot-unit" data-pilot-id="${{escapeHtml(unit.pilot_id)}}" data-risk-level="${{escapeHtml(unit.risk_level)}}">`
      + `<strong>#${{escapeHtml(unit.rank)}} ${{escapeHtml(unit.name)}}</strong>`
      + `<span>Parent: ${{escapeHtml(unit.parent_label)}} | Level: ${{escapeHtml(unit.level)}} | Geometry: ${{escapeHtml(unit.geometry_source)}}</span>`
      + `<span>Score: ${{escapeHtml(unit.score ?? "No data")}} | Risk: ${{escapeHtml(unit.risk_level)}} | Quality: ${{escapeHtml(unit.quality_flag)}}</span>`
      + `<span>${{escapeHtml(unit.coverage_note)}}</span></article>`).join("") + "</div>";
  }}

  function recommendationsHtml(items) {{
    if (!items.length) return "<li>No action recommendations are available yet.</li>";
    return items.map((item) => `<li>${{escapeHtml(item)}}</li>`).join("");
  }}

  function trendHtml(series) {{
    if (!series.length) return '<div class="trend-empty">No trend series available for this region.</div>';
    return series.map((item) => `<article class="trend-card">`
      + `<h3>${{escapeHtml(item.label)}}</h3>`
      + `<p class="trend-meta">${{escapeHtml(item.unit)}} | ${{escapeHtml(item.source)}}</p>`
      + `${{item.svg || ""}}`
      + `<p class="trend-detail">${{escapeHtml(item.baseline_label)}} | Latest quality: ${{escapeHtml(item.latest_quality)}} | Latest anomaly: ${{escapeHtml(item.latest_anomaly)}}</p>`
      + `</article>`).join("");
  }}

  function renderProfile(regionId) {{
    const profile = profiles[regionId];
    if (!profile) return;
    if (selector) selector.value = regionId;
    if (selectedLabel) selectedLabel.textContent = profile.label;
    if (detail) {{
      detail.innerHTML = `<h3>${{escapeHtml(profile.label)}}</h3>`
        + `<p>Status: ${{escapeHtml(profile.status)}} | Loaded payload drilldown</p>`
        + `<h3>Subnational pilot</h3>`
        + pilotHtml(profile.pilot_units)
        + alertsHtml(profile.alerts);
    }}
    if (metricsGrid) metricsGrid.innerHTML = profile.metrics.map(metricHtml).join("");
    if (trendsGrid) trendsGrid.innerHTML = trendHtml(profile.trends || []);
    if (alertPanel) {{
      alertPanel.innerHTML = alertsHtml(profile.alerts);
      applyAlertFilters();
    }}
    const recommendations = root.querySelector("#reports .recommendations");
    if (recommendations) recommendations.innerHTML = recommendationsHtml(profile.recommendations);
  }}

  function bindPaths() {{
    paths = Array.from(root.querySelectorAll(".risk-region"));
    paths.forEach((path) => {{
      path.setAttribute("role", "button");
      path.setAttribute("aria-pressed", path.classList.contains("is-selected") ? "true" : "false");
      path.addEventListener("click", () => selectRegion(path));
      path.addEventListener("keydown", (event) => {{
        if (event.key === "Enter" || event.key === " ") {{
          event.preventDefault();
          selectRegion(path);
        }}
      }});
    }});
  }}

  function selectRegion(path) {{
    paths.forEach((item) => {{
      item.classList.remove("is-selected", "is-active");
      item.setAttribute("aria-pressed", "false");
    }});
    path.classList.add("is-selected", "is-active");
    path.setAttribute("aria-pressed", "true");
    const name = path.dataset.regionName || path.dataset.regionId || "Unknown region";
    const score = path.dataset.score || "No data";
    const level = path.dataset.riskLevel || "unknown";
    const period = path.dataset.period || "No period";
    const quality = path.dataset.quality || "unknown";
    if (selectedLabel) selectedLabel.textContent = (path.dataset.regionId || name).toUpperCase();
    if (readoutName) readoutName.textContent = name;
    if (readoutDetail) {{
      readoutDetail.textContent = `Score: ${{score}} | Level: ${{level}} | Period: ${{period}} | Quality: ${{quality}}`;
    }}
    renderProfile(path.dataset.regionId || "");
    const url = new URL(window.location.href);
    url.searchParams.set("region", path.dataset.regionId || "");
    window.history.replaceState(null, "", url);
  }}

  function renderPeriod(periodKey) {{
    const period = periods.find((item) => item.period_key === periodKey);
    if (!period) return;
    profiles = period.profiles || {{}};
    if (mapSlot) {{
      mapSlot.innerHTML = period.risk_map_html || "";
      bindPaths();
    }}
    if (periodTitle) periodTitle.textContent = period.label;
    if (periodState) {{
      periodState.textContent = period.status;
      periodState.dataset.periodStatus = period.status;
    }}
    if (periodSelector) periodSelector.value = period.period_key;
    const preferredRegion = selector?.value && profiles[selector.value] ? selector.value : period.selected_region_id;
    const path = paths.find((item) => item.dataset.regionId === preferredRegion);
    if (path) selectRegion(path);
    else renderProfile(preferredRegion);
    const url = new URL(window.location.href);
    url.searchParams.set("period", period.period_key);
    window.history.replaceState(null, "", url);
  }}

  bindPaths();
  navButtons.forEach((button) => {{
    button.addEventListener("click", () => {{
      const target = root.querySelector(`#${{button.dataset.navTarget || ""}}`);
      if (!target) return;
      navButtons.forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      target.scrollIntoView({{ block: "start", behavior: "smooth" }});
    }});
  }});
  alertFilters.forEach((filter) => filter.addEventListener("change", applyAlertFilters));
  selector?.addEventListener("change", () => {{
    const path = paths.find((item) => item.dataset.regionId === selector.value);
    if (path) selectRegion(path);
    else renderProfile(selector.value);
  }});
  periodSelector?.addEventListener("change", () => renderPeriod(periodSelector.value));
  const requestedPeriod = new URLSearchParams(window.location.search).get("period");
  if (requestedPeriod && periods.some((item) => item.period_key === requestedPeriod)) {{
    renderPeriod(requestedPeriod);
  }}
  const requestedRegion = new URLSearchParams(window.location.search).get("region");
  if (requestedRegion && profiles[requestedRegion]) {{
    const path = paths.find((item) => item.dataset.regionId === requestedRegion);
    if (path) selectRegion(path);
  }}
}})();
</script>
"""


def render_dashboard(
    *,
    data_loader: Callable[[], DashboardShellData] = load_dashboard_shell_data,
    streamlit_module: Any | None = None,
) -> None:
    safe_error = False
    try:
        data = data_loader()
    except Exception:
        data = fallback_dashboard_shell_data()
        safe_error = True

    html = build_dashboard_shell_html(data, safe_error=safe_error)
    st = streamlit_module
    if st is None:
        try:
            import streamlit as imported_streamlit
        except ModuleNotFoundError:
            print(f"{data.project} - {data.tagline}")
            print(f"Last update: {data.data_status.last_updated}")
            print(f"Data status: {data.data_status.message}")
            if safe_error:
                print(SAFE_ERROR_MESSAGE)
            return
        st = imported_streamlit

    st.set_page_config(page_title=data.project, page_icon="M", layout="wide")
    _render_html(st, html)


def main() -> None:
    render_dashboard()


def _render_html(st: Any, html: str) -> None:
    components = getattr(st, "components", None)
    component_html = getattr(getattr(components, "v1", None), "html", None)
    if callable(component_html):
        component_html(html, height=900, scrolling=True)
        return

    if getattr(st, "__name__", "") == "streamlit":
        try:
            import streamlit.components.v1 as streamlit_components
        except ModuleNotFoundError:
            streamlit_components = None
        if streamlit_components is not None:
            streamlit_components.html(html, height=900, scrolling=True)
            return

    html_renderer = getattr(st, "html", None)
    if callable(html_renderer):
        html_renderer(html)
        return

    st.markdown(html, unsafe_allow_html=True)


def _render_alerts(data: DashboardShellData) -> str:
    if not data.alerts:
        return '<p class="footer-note" data-alert-empty>No active alerts available in the current shell view.</p>'
    return '<div class="alert-list">{items}</div>'.format(
        items="\n".join(
            '<article class="alert-item" data-severity="{severity}" data-region-id="{region_id}" '
            'data-region-type="{region_type}">'
            '<div class="alert-heading"><h3>{title}</h3><span class="alert-rank">#{rank}</span></div>'
            "<p>{region} - {period} | Quality: {quality}</p>"
            "{evidence}"
            '<span class="alert-action">{action}</span>'
            "</article>".format(
                severity=escape(alert.severity),
                region_id=escape(alert.region_id),
                region_type=escape(alert.region_type),
                title=escape(alert.title),
                rank=alert.priority_rank or "",
                region=escape(alert.region),
                period=escape(alert.period),
                quality=escape(alert.quality_flag),
                evidence=_render_alert_evidence(alert.evidence),
                action=escape(alert.action),
            )
            for alert in data.alerts
        )
    ) + '<p class="footer-note" data-alert-filter-empty hidden>No alerts match the selected filters.</p>'


def _render_alert_filters(data: DashboardShellData) -> str:
    severity_options = _alert_filter_options(
        "severity",
        (("all", "All levels"),) + tuple((severity, severity.title()) for severity in _ordered_alert_values(data.alerts, "severity")),
    )
    region_options = _alert_filter_options(
        "region",
        (("all", "All countries"),)
        + tuple((alert.region_id, alert.region) for alert in data.alerts if alert.region_id),
    )
    type_options = _alert_filter_options(
        "type",
        (("all", "All region types"),)
        + tuple((kind, kind.title()) for kind in _ordered_alert_values(data.alerts, "region_type")),
    )
    return (
        '<div class="alert-filters" aria-label="Active alert filters">'
        f'<label>Level{severity_options}</label>'
        f'<label>Country{region_options}</label>'
        f'<label>Type{type_options}</label>'
        "</div>"
    )


def _alert_filter_options(name: str, options: tuple[tuple[str, str], ...]) -> str:
    seen: set[str] = set()
    rendered: list[str] = []
    for value, label in options:
        if not value or value in seen:
            continue
        seen.add(value)
        rendered.append(f'<option value="{escape(value)}">{escape(label)}</option>')
    return f'<select data-alert-filter="{escape(name)}">{"".join(rendered)}</select>'


def _ordered_alert_values(alerts: tuple[Any, ...], field: str) -> tuple[str, ...]:
    priority = {
        "critical": 0,
        "warning": 1,
        "watch": 2,
        "normal": 3,
        "unknown": 4,
        "country": 0,
        "pilot": 1,
    }
    values = {str(getattr(alert, field, "")) for alert in alerts if getattr(alert, field, "")}
    return tuple(sorted(values, key=lambda item: (priority.get(item, 99), item)))


def _render_region_options(data: DashboardShellData) -> str:
    selected = data.selected_region_id
    return "\n".join(
        '<option value="{region_id}"{selected}>{label}</option>'.format(
            region_id=escape(profile.region_id),
            selected=" selected" if profile.region_id == selected else "",
            label=escape(profile.label),
        )
        for profile in data.region_profiles
    )


def _render_temporal_options(data: DashboardShellData) -> str:
    selected = _selected_temporal_period(data).period_key
    return "\n".join(
        '<option value="{period_key}"{selected}>{label}</option>'.format(
            period_key=escape(period.period_key),
            selected=" selected" if period.period_key == selected else "",
            label=escape(f"{period.label} ({period.status})"),
        )
        for period in _temporal_periods_for_view(data)
    )


def _render_region_panel(data: DashboardShellData) -> str:
    profile = _selected_region_profile(data)
    if profile is None:
        return (
            "<h3>Unknown region</h3>"
            '<p class="footer-note">No region payloads are available in the current shell view.</p>'
        )
    return (
        f"<h3>{escape(profile.label)}</h3>"
        f"<p>Status: {escape(profile.status)} | Loaded payload drilldown</p>"
        "<h3>Subnational pilot</h3>"
        f"{_render_pilot_units(profile.pilot_units)}"
        f'<div class="alert-list">{_render_profile_alerts(profile.alerts)}</div>'
    )


def _render_pilot_units(units: tuple[Any, ...]) -> str:
    if not units:
        return (
            '<p class="footer-note">'
            "Subnational pilot is not enabled for this country in 1.0; IGAD coverage remains national here."
            "</p>"
        )
    return '<div class="pilot-ranking">{items}</div>'.format(
        items="\n".join(
            '<article class="pilot-unit" data-pilot-id="{pilot_id}" data-risk-level="{risk_level}">'
            "<strong>#{rank} {name}</strong>"
            "<span>Parent: {parent} | Level: {level} | Geometry: {geometry}</span>"
            "<span>Score: {score} | Risk: {risk_level} | Quality: {quality}</span>"
            "<span>{coverage_note}</span>"
            "</article>".format(
                pilot_id=escape(unit.pilot_id),
                rank=unit.rank,
                name=escape(unit.name),
                parent=escape(unit.parent_label),
                level=escape(unit.level),
                geometry=escape(unit.geometry_source),
                score=escape("No data" if unit.score is None else _format_map_score(unit.score)),
                risk_level=escape(unit.risk_level),
                quality=escape(unit.quality_flag),
                coverage_note=escape(unit.coverage_note),
            )
            for unit in units
        )
    )


def _render_profile_alerts(alerts: tuple[Any, ...]) -> str:
    if not alerts:
        return '<p class="footer-note" data-alert-empty>No active alerts available for this region.</p>'
    return "\n".join(
        '<article class="alert-item" data-severity="{severity}" data-region-id="{region_id}" '
        'data-region-type="{region_type}">'
        '<div class="alert-heading"><h3>{title}</h3><span class="alert-rank">#{rank}</span></div>'
        "<p>{region} - {period} | Quality: {quality}</p>"
        "{evidence}"
        '<span class="alert-action">{action}</span>'
        "</article>".format(
            severity=escape(alert.severity),
            region_id=escape(alert.region_id),
            region_type=escape(alert.region_type),
            title=escape(alert.title),
            rank=alert.priority_rank or "",
            region=escape(alert.region),
            period=escape(alert.period),
            quality=escape(alert.quality_flag),
            evidence=_render_alert_evidence(alert.evidence),
            action=escape(alert.action),
        )
        for alert in alerts
    )


def _render_alert_evidence(items: tuple[tuple[str, str], ...]) -> str:
    if not items:
        return ""
    return '<ul class="alert-evidence">{items}</ul>'.format(
        items="".join(f"<li>{escape(label)}: {escape(value)}</li>" for label, value in items)
    )


def _render_trends(series: tuple[Any, ...]) -> str:
    if not series:
        return '<div class="trend-empty">No trend series available for this region.</div>'
    return "\n".join(
        '<article class="trend-card">'
        "<h3>{label}</h3>"
        '<p class="trend-meta">{unit} | {source}</p>'
        "{svg}"
        '<p class="trend-detail">{baseline} | Latest quality: {quality} | Latest anomaly: {anomaly}</p>'
        "</article>".format(
            label=escape(item.label),
            unit=escape(item.unit),
            source=escape(item.source),
            svg=_trend_svg(item),
            baseline=escape(item.baseline_label),
            quality=escape(_latest_trend_quality(item)),
            anomaly=escape(_latest_trend_anomaly(item)),
        )
        for item in series
    )


def _selected_region_profile(data: DashboardShellData) -> Any | None:
    for profile in data.region_profiles:
        if profile.region_id == data.selected_region_id:
            return profile
    return data.region_profiles[0] if data.region_profiles else None


def _region_profiles_json(data: DashboardShellData) -> str:
    profiles = _profiles_dict(data.region_profiles)
    raw = json.dumps(profiles, ensure_ascii=True, separators=(",", ":"))
    return raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _temporal_periods_json(data: DashboardShellData) -> str:
    periods = [
        {
            "period_key": period.period_key,
            "label": period.label,
            "status": period.status,
            "is_partial": period.is_partial,
            "last_updated": period.last_updated,
            "selected_region_id": period.selected_region_id,
            "selected_region": period.selected_region,
            "risk_map_html": build_regional_risk_map_html(period.risk_map),
            "metrics": [_metric_dict(metric) for metric in period.metrics],
            "alerts": [_alert_dict(alert) for alert in period.alerts],
            "recommendations": list(period.recommendations),
            "profiles": _profiles_dict(period.region_profiles),
        }
        for period in _temporal_periods_for_view(data)
    ]
    raw = json.dumps(periods, ensure_ascii=True, separators=(",", ":"))
    return raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _profiles_dict(region_profiles: tuple[Any, ...]) -> dict[str, Any]:
    return {
        profile.region_id: {
            "region_id": profile.region_id,
            "label": profile.label,
            "status": profile.status,
            "metrics": [_metric_dict(metric) for metric in profile.metrics],
            "alerts": [_alert_dict(alert) for alert in profile.alerts],
            "recommendations": list(profile.recommendations),
            "trends": [_trend_dict(series) for series in profile.trends],
            "pilot_units": [
                {
                    "pilot_id": unit.pilot_id,
                    "name": unit.name,
                    "parent_id": unit.parent_id,
                    "parent_label": unit.parent_label,
                    "level": unit.level,
                    "coverage_type": unit.coverage_type,
                    "geometry_source": unit.geometry_source,
                    "score": unit.score,
                    "risk_level": unit.risk_level,
                    "quality_flag": unit.quality_flag,
                    "coverage_note": unit.coverage_note,
                    "rank": unit.rank,
                }
                for unit in profile.pilot_units
            ],
        }
        for profile in region_profiles
    }


def _metric_dict(metric: Any) -> dict[str, str]:
    return {
        "label": metric.label,
        "value": metric.value,
        "unit": metric.unit,
        "severity": metric.severity,
        "detail": metric.detail,
    }


def _alert_dict(alert: Any) -> dict[str, Any]:
    return {
        "region": alert.region,
        "region_id": alert.region_id,
        "region_type": alert.region_type,
        "severity": alert.severity,
        "title": alert.title,
        "period": alert.period,
        "action": alert.action,
        "quality_flag": alert.quality_flag,
        "evidence": list(alert.evidence),
        "priority_rank": str(alert.priority_rank or ""),
        "alert_type": alert.alert_type,
        "status": alert.status,
    }


def _trend_dict(series: Any) -> dict[str, Any]:
    return {
        "indicator": series.indicator,
        "label": series.label,
        "unit": series.unit,
        "source": series.source,
        "baseline_label": series.baseline_label,
        "latest_quality": _latest_trend_quality(series),
        "latest_anomaly": _latest_trend_anomaly(series),
        "svg": _trend_svg(series),
        "points": [
            {
                "period_start": point.period_start,
                "period_end": point.period_end,
                "value": point.value,
                "baseline_value": point.baseline_value,
                "anomaly_value": point.anomaly_value,
                "quality_flag": point.quality_flag,
                "is_gap": point.is_gap,
            }
            for point in series.points
        ],
    }


def _trend_svg(series: Any) -> str:
    points = list(series.points)
    if not points:
        return '<svg class="trend-chart" viewBox="0 0 320 112" role="img" aria-label="No trend data"></svg>'
    values = [
        value
        for point in points
        for value in (point.value, point.baseline_value)
        if isinstance(value, int | float)
    ]
    if not values:
        values = [0.0, 1.0]
    low, high = min(values), max(values)
    if low == high:
        low -= 1.0
        high += 1.0
    width, height = 320.0, 112.0
    left, right, top, bottom = 28.0, 10.0, 8.0, 24.0
    x_step = (width - left - right) / max(1, len(points) - 1)

    def x(index: int) -> float:
        return left + index * x_step

    def y(value: float) -> float:
        return top + (high - value) / (high - low) * (height - top - bottom)

    observed = " ".join(
        f"{x(index):.1f},{y(float(point.value)):.1f}"
        for index, point in enumerate(points)
        if isinstance(point.value, int | float) and not point.is_gap
    )
    baseline = " ".join(
        f"{x(index):.1f},{y(float(point.baseline_value)):.1f}"
        for index, point in enumerate(points)
        if isinstance(point.baseline_value, int | float)
    )
    circles = "".join(
        '<circle class="{klass}" cx="{cx:.1f}" cy="{cy:.1f}" r="3">'
        "<title>{title}</title></circle>".format(
            klass="trend-gap" if point.is_gap else "trend-point",
            cx=x(index),
            cy=y(float(point.value)) if isinstance(point.value, int | float) else height - bottom,
            title=escape(
                f"{point.period_end[:10]} value={point.value if point.value is not None else 'gap'} "
                f"anomaly={point.anomaly_value if point.anomaly_value is not None else 'n/a'} "
                f"quality={point.quality_flag}"
            ),
        )
        for index, point in enumerate(points)
    )
    labels = "".join(
        '<text x="{cx:.1f}" y="106" text-anchor="middle" fill="#667085" font-size="9">{label}</text>'.format(
            cx=x(index),
            label=escape(point.period_end[:10][5:]),
        )
        for index, point in enumerate(points)
    )
    return (
        f'<svg class="trend-chart" viewBox="0 0 320 112" role="img" '
        f'aria-label="{escape(series.label)} {escape(series.unit)} trend">'
        f'<line class="trend-axis" x1="{left}" x2="{width - right}" y1="{height - bottom}" y2="{height - bottom}" />'
        f'<polyline class="trend-baseline" points="{baseline}" />'
        f'<polyline class="trend-observed" points="{observed}" />'
        f"{circles}{labels}</svg>"
    )


def _latest_trend_quality(series: Any) -> str:
    return series.points[-1].quality_flag if series.points else "unknown"


def _latest_trend_anomaly(series: Any) -> str:
    if not series.points or series.points[-1].anomaly_value is None:
        return "n/a"
    return _format_map_score(float(series.points[-1].anomaly_value))


def _temporal_periods_for_view(data: DashboardShellData) -> tuple[Any, ...]:
    if data.temporal_periods:
        return data.temporal_periods
    return (
        _SinglePeriodView(
            period_key=data.data_status.last_updated,
            label=data.data_status.last_updated[:10] or "Current",
            status="complete",
            is_partial=False,
            last_updated=data.data_status.last_updated,
            selected_region_id=data.selected_region_id,
            selected_region=data.selected_region,
            risk_map=data.risk_map,
            metrics=data.metrics,
            alerts=data.alerts,
            recommendations=data.recommendations,
            region_profiles=data.region_profiles,
        ),
    )


def _selected_temporal_period(data: DashboardShellData) -> Any:
    return _temporal_periods_for_view(data)[0]


def _selected_map_region(data: DashboardShellData) -> Any:
    selected = data.risk_map.selected_region_id
    for region in data.risk_map.regions:
        if region.region_id == selected:
            return _MapRegionReadout(
                name=region.name,
                score_label="No data" if region.score is None else _format_map_score(region.score),
                color_level=region.color_level,
                period=_period_label(region.period_start, region.period_end),
                quality_flag=region.quality_flag or "unknown",
            )
    return _MapRegionReadout(data.selected_region, "No data", "unknown", "No period", "unknown")


class _MapRegionReadout:
    def __init__(
        self,
        name: str,
        score_label: str,
        color_level: str,
        period: str,
        quality_flag: str,
    ) -> None:
        self.name = name
        self.score_label = score_label
        self.color_level = color_level
        self.period = period
        self.quality_flag = quality_flag


class _SinglePeriodView:
    def __init__(
        self,
        *,
        period_key: str,
        label: str,
        status: str,
        is_partial: bool,
        last_updated: str,
        selected_region_id: str,
        selected_region: str,
        risk_map: Any,
        metrics: tuple[Any, ...],
        alerts: tuple[Any, ...],
        recommendations: tuple[str, ...],
        region_profiles: tuple[Any, ...],
    ) -> None:
        self.period_key = period_key
        self.label = label
        self.status = status
        self.is_partial = is_partial
        self.last_updated = last_updated
        self.selected_region_id = selected_region_id
        self.selected_region = selected_region
        self.risk_map = risk_map
        self.metrics = metrics
        self.alerts = alerts
        self.recommendations = recommendations
        self.region_profiles = region_profiles


def _period_label(period_start: str, period_end: str) -> str:
    if period_start and period_end:
        return f"{period_start[:10]} to {period_end[:10]}"
    if period_end:
        return period_end[:10]
    return "No period"


def _format_map_score(score: float) -> str:
    return f"{score:.2f}".rstrip("0").rstrip(".")


def _shell_dom_id(data: DashboardShellData) -> str:
    raw = f"{data.data_status.mode}-{data.selected_region_id}-{data.data_status.last_updated}"
    return "mwa-" + "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")
