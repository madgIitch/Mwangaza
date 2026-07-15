from __future__ import annotations

from collections.abc import Callable
from html import escape
from typing import Any

from mwangaza.services.dashboard_shell import (
    DashboardShellData,
    fallback_dashboard_shell_data,
    load_dashboard_shell_data,
)

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
  --mwa-bg: #f5f7f6;
  --mwa-panel: #ffffff;
  --mwa-border: #dfe7e1;
  --mwa-text: #17231c;
  --mwa-muted: #647067;
  --mwa-green: #1f7a4d;
  --mwa-green-soft: #e7f4ed;
  --mwa-yellow: #f4c542;
  --mwa-orange: #e68032;
  --mwa-red: #c93636;
  --mwa-blue: #3b6f9e;
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
  grid-template-columns: minmax(188px, 230px) minmax(0, 1fr);
  gap: 16px;
  width: 100%;
  max-width: 1366px;
  margin: 0 auto;
  padding: 8px;
  font-family: Inter, Segoe UI, Arial, sans-serif;
}}
.sidebar, .topbar, .panel, .metric-card {{
  background: var(--mwa-panel);
  border: 1px solid var(--mwa-border);
  border-radius: 8px;
  box-shadow: 0 8px 20px rgba(25, 42, 31, 0.06);
}}
.sidebar {{
  min-height: 720px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}}
.brand-row {{
  display: flex;
  align-items: center;
  gap: 10px;
}}
.brand-mark {{
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--mwa-yellow) 0 45%, var(--mwa-green) 46% 100%);
}}
.brand-title {{
  margin: 0;
  font-size: 20px;
  line-height: 1.1;
}}
.tagline {{
  margin: 4px 0 0;
  color: var(--mwa-muted);
  font-size: 12px;
}}
.nav-stack {{
  display: grid;
  gap: 6px;
}}
.nav-item {{
  color: var(--mwa-text);
  text-decoration: none;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.nav-item.is-active {{
  background: var(--mwa-green-soft);
  color: var(--mwa-green);
  font-weight: 700;
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
.main {{
  display: grid;
  gap: 14px;
}}
.topbar {{
  min-height: 74px;
  padding: 14px 16px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}}
.page-title {{
  margin: 0;
  font-size: 24px;
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
  grid-template-columns: minmax(0, 1.45fr) minmax(260px, 0.8fr);
  gap: 14px;
}}
.panel {{
  padding: 14px;
}}
.panel h2 {{
  margin: 0 0 12px;
  font-size: 16px;
}}
.map-panel {{
  min-height: 284px;
}}
.map-canvas {{
  height: 220px;
  border-radius: 8px;
  border: 1px solid #d7e0da;
  background:
    linear-gradient(140deg, rgba(31, 122, 77, 0.24), rgba(244, 197, 66, 0.18)),
    repeating-linear-gradient(45deg, #eef4f0 0 14px, #e3ebe6 14px 28px);
  display: grid;
  place-items: center;
  color: #2f5c45;
  font-weight: 700;
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}}
.metric-card {{
  padding: 12px;
  min-height: 116px;
  box-shadow: none;
}}
.metric-card strong {{
  display: block;
  margin-top: 8px;
  font-size: 22px;
}}
.metric-card small {{
  margin-left: 3px;
  color: var(--mwa-muted);
  font-size: 12px;
}}
.metric-label, .metric-card p {{
  color: var(--mwa-muted);
  font-size: 12px;
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
  gap: 10px;
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
.footer-note {{
  color: var(--mwa-muted);
  font-size: 11px;
}}
@media (max-width: 900px) {{
  .mwa-shell, .workspace {{
    grid-template-columns: 1fr;
  }}
  .sidebar {{
    min-height: auto;
  }}
  .metrics-grid {{
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }}
}}
@media (max-width: 560px) {{
  .metrics-grid, .topbar {{
    grid-template-columns: 1fr;
  }}
}}
</style>
<div class="mwa-shell">
  <aside class="sidebar" aria-label="Mwangaza navigation">
    <div class="brand-row">
      <div class="brand-mark" aria-hidden="true"></div>
      <div>
        <h1 class="brand-title">{escape(data.project)}</h1>
        <p class="tagline">{escape(data.tagline)}</p>
      </div>
    </div>
    <nav class="nav-stack">{nav}</nav>
    <div class="mode-stack" aria-label="Data origin modes">{mode_chips}</div>
  </aside>
  <main class="main">
    {error_banner}
    <header class="topbar">
      <div>
        <h2 class="page-title">Regional Drought Operations</h2>
        <div class="status-row">
          <span class="status-pill" data-freshness="{escape(data.data_status.freshness)}">
            {escape(data.data_status.message)}
          </span>
          <span class="status-pill">{escape(data.data_status.source)}</span>
          <span class="timestamp">Last update: {escape(data.data_status.last_updated)}</span>
        </div>
      </div>
      <div class="status-pill" data-mode="{escape(data.data_status.mode)}">
        {escape(data.data_status.mode.upper())}
      </div>
    </header>
    <section class="workspace">
      <div class="main-column">
        <section class="panel map-panel" id="overview">
          <h2>Regional Risk Map - IGAD</h2>
          <div class="map-canvas">Selected region: {escape(data.selected_region)}</div>
          <div class="legend">
            <span style="color: var(--mwa-green)">Low</span>
            <span style="color: var(--mwa-yellow)">Watch</span>
            <span style="color: var(--mwa-orange)">Warning</span>
            <span style="color: var(--mwa-red)">Critical</span>
            <span style="color: #8c9690">Unknown</span>
          </div>
        </section>
        <section class="metrics-grid" id="region">{metrics}</section>
      </div>
      <aside class="side-column">
        <section class="panel" id="alerts">
          <h2>Active Alerts</h2>
          {alerts}
        </section>
        <section class="panel" id="reports">
          <h2>Early Action Recommendations</h2>
          <ul class="recommendations">{recommendations}</ul>
        </section>
        <section class="panel" id="about">
          <h2>About</h2>
          <p class="footer-note">
            Prototype dashboard shell. Observed, cached and demo data are labelled separately.
          </p>
        </section>
      </aside>
    </section>
  </main>
</div>
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
    html_renderer = getattr(st, "html", None)
    if callable(html_renderer):
        html_renderer(html)
        return

    components = getattr(st, "components", None)
    component_html = getattr(getattr(components, "v1", None), "html", None)
    if callable(component_html):
        component_html(html, height=900, scrolling=True)
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
