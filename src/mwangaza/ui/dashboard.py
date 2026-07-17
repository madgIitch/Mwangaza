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
    nav = "\n".join(
        f'<a class="nav-item{" is-active" if item.active else ""}" href="#{escape(item.key)}">'
        f"{escape(item.label)}</a>"
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
    alerts = _render_alerts(data)
    risk_map = build_regional_risk_map_html(data.risk_map)
    selected_region = _selected_map_region(data)
    region_options = _render_region_options(data)
    region_profiles_json = _region_profiles_json(data)
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
  color: var(--mwa-text);
  text-decoration: none;
  min-height: 56px;
  padding: 0 18px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
.alert-list {{
  display: grid;
  gap: 8px;
}}
.alert-item {{
  border: 1px solid var(--mwa-border);
  border-left: 4px solid var(--mwa-yellow);
  border-radius: 8px;
  padding: 10px;
}}
.alert-item[data-severity="critical"] {{ border-left-color: var(--mwa-red); }}
.alert-item[data-severity="warning"] {{ border-left-color: var(--mwa-orange); }}
.alert-item h3 {{
  margin: 0;
  font-size: 14px;
}}
.alert-item p, .recommendations li {{
  color: var(--mwa-muted);
  font-size: 12px;
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
}}
@media (max-width: 560px) {{
  .metrics-grid {{
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }}
}}
</style>
<div class="mwa-shell">
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
          <div class="panel-header"><h2>Regional Risk Map - IGAD</h2></div>
          <div class="panel-body">
            {risk_map}
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
      </div>
      <aside class="side-column">
        <section class="panel" id="alerts">
          <div class="panel-header"><h2>Active Alerts</h2></div>
          <div class="panel-body">{alerts}</div>
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
<script type="application/json" data-region-profiles>{region_profiles_json}</script>
<script>
(() => {{
  const dataScript = document.currentScript?.previousElementSibling;
  const root = dataScript?.previousElementSibling;
  if (!root || root.dataset.mwangazaInteractive === "1") return;
  root.dataset.mwangazaInteractive = "1";
  const profiles = dataScript?.textContent ? JSON.parse(dataScript.textContent) : {{}};
  const paths = Array.from(root.querySelectorAll(".risk-region"));
  const selectedLabel = root.querySelector("[data-selected-region-label]");
  const readoutName = root.querySelector("[data-region-readout-name]");
  const readoutDetail = root.querySelector("[data-region-readout-detail]");
  const selector = root.querySelector("[data-region-selector]");
  const detail = root.querySelector("[data-region-detail]");
  const metricsGrid = root.querySelector("[data-region-metrics]");

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
    if (!alerts.length) return '<p class="footer-note">No active alerts available for this region.</p>';
    return alerts.map((alert) => `<article class="alert-item" data-severity="${{escapeHtml(alert.severity)}}">`
      + `<h3>${{escapeHtml(alert.title)}}</h3><p>${{escapeHtml(alert.region)}} - ${{escapeHtml(alert.period)}}</p>`
      + `<span class="alert-action">${{escapeHtml(alert.action)}}</span></article>`).join("");
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
        + `<div class="alert-list">${{alertsHtml(profile.alerts)}}</div>`;
    }}
    if (metricsGrid) metricsGrid.innerHTML = profile.metrics.map(metricHtml).join("");
    const alertsPanel = root.querySelector("#alerts .alert-list, #alerts .footer-note");
    if (alertsPanel) alertsPanel.outerHTML = `<div class="alert-list">${{alertsHtml(profile.alerts)}}</div>`;
    const recommendations = root.querySelector("#reports .recommendations");
    if (recommendations) recommendations.innerHTML = recommendationsHtml(profile.recommendations);
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
  selector?.addEventListener("change", () => {{
    const path = paths.find((item) => item.dataset.regionId === selector.value);
    if (path) selectRegion(path);
    else renderProfile(selector.value);
  }});
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
        return '<p class="footer-note">No active alerts available in the current shell view.</p>'
    return '<div class="alert-list">{items}</div>'.format(
        items="\n".join(
            '<article class="alert-item" data-severity="{severity}">'
            "<h3>{title}</h3>"
            "<p>{region} - {period}</p>"
            '<span class="alert-action">{action}</span>'
            "</article>".format(
                severity=escape(alert.severity),
                title=escape(alert.title),
                region=escape(alert.region),
                period=escape(alert.period),
                action=escape(alert.action),
            )
            for alert in data.alerts
        )
    )


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
        return '<p class="footer-note">No active alerts available for this region.</p>'
    return "\n".join(
        '<article class="alert-item" data-severity="{severity}">'
        "<h3>{title}</h3>"
        "<p>{region} - {period}</p>"
        '<span class="alert-action">{action}</span>'
        "</article>".format(
            severity=escape(alert.severity),
            title=escape(alert.title),
            region=escape(alert.region),
            period=escape(alert.period),
            action=escape(alert.action),
        )
        for alert in alerts
    )


def _selected_region_profile(data: DashboardShellData) -> Any | None:
    for profile in data.region_profiles:
        if profile.region_id == data.selected_region_id:
            return profile
    return data.region_profiles[0] if data.region_profiles else None


def _region_profiles_json(data: DashboardShellData) -> str:
    profiles = {
        profile.region_id: {
            "region_id": profile.region_id,
            "label": profile.label,
            "status": profile.status,
            "metrics": [
                {
                    "label": metric.label,
                    "value": metric.value,
                    "unit": metric.unit,
                    "severity": metric.severity,
                    "detail": metric.detail,
                }
                for metric in profile.metrics
            ],
            "alerts": [
                {
                    "region": alert.region,
                    "severity": alert.severity,
                    "title": alert.title,
                    "period": alert.period,
                    "action": alert.action,
                }
                for alert in profile.alerts
            ],
            "recommendations": list(profile.recommendations),
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
        for profile in data.region_profiles
    }
    raw = json.dumps(profiles, ensure_ascii=True, separators=(",", ":"))
    return raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


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


def _period_label(period_start: str, period_end: str) -> str:
    if period_start and period_end:
        return f"{period_start[:10]} to {period_end[:10]}"
    if period_end:
        return period_end[:10]
    return "No period"


def _format_map_score(score: float) -> str:
    return f"{score:.2f}".rstrip("0").rstrip(".")
