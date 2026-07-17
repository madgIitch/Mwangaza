import { useEffect, useMemo, useState } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { loadApiDashboardDetails, loadApiDashboardSnapshot } from "./api";
import { demoDashboard } from "./fixtures";
import { normalizeLanguage, t } from "./i18n";
import type { Alert, DashboardData, GeoJsonGeometry, Language, Metric, RegionProfile, RegionRisk, Severity, TrendSeries } from "./types";
import "./styles.css";

interface AppProps {
  initialData?: DashboardData;
  initialLanguage?: Language;
  initialLowBandwidth?: boolean;
  initialOffline?: boolean;
  skipApiLoad?: boolean;
}

const severityRank: Record<Severity, number> = {
  critical: 4,
  warning: 3,
  watch: 2,
  normal: 1,
  unknown: 0
};

export function App({
  initialData,
  initialLanguage,
  initialLowBandwidth,
  initialOffline,
  skipApiLoad = !shouldLoadApiByDefault()
}: AppProps): JSX.Element {
  const [data, setData] = useState(initialData ?? (skipApiLoad ? demoDashboard : loadingApiDashboard()));
  const [apiFallback, setApiFallback] = useState(false);
  const [language, setLanguage] = useState<Language>(
    initialLanguage ?? normalizeLanguage(new URLSearchParams(window.location.search).get("lang"))
  );
  const [lowBandwidth, setLowBandwidth] = useState(
    initialLowBandwidth ?? new URLSearchParams(window.location.search).get("lite") === "1"
  );
  const [offline, setOffline] = useState(initialOffline ?? navigator.onLine === false);
  const [selectedRegionId, setSelectedRegionId] = useState(data.selectedRegionId);

  useEffect(() => {
    if (skipApiLoad || initialData) {
      appLog("api load skipped", { skipApiLoad, hasInitialData: Boolean(initialData) });
      return;
    }
    let cancelled = false;
    appLog("api load effect start");
    loadApiDashboardSnapshot()
      .then((snapshotData) => {
        if (cancelled) {
          appLog("snapshot ignored after cancellation", {
            dataMode: snapshotData.dataMode,
            selectedRegionId: snapshotData.selectedRegionId
          });
          return null;
        }
        if (!cancelled) {
          appLog("snapshot applied", {
            dataMode: snapshotData.dataMode,
            source: snapshotData.source,
            selectedRegionId: snapshotData.selectedRegionId,
            metrics: snapshotData.metrics.length,
            regions: snapshotData.regions.length
          });
          setData(snapshotData);
          setSelectedRegionId(snapshotData.selectedRegionId);
        }
        return loadApiDashboardDetails(snapshotData);
      })
      .then((next) => {
        if (!cancelled && next) {
          appLog("details applied", {
            alerts: next.alerts.length,
            forecastAvailable: next.forecastDiagnostics.available,
            selectedRegionId: next.selectedRegionId
          });
          setData(next);
          setSelectedRegionId(next.selectedRegionId);
        }
      })
      .catch(() => {
        if (!cancelled) {
          appLog("api fallback applied");
          setApiFallback(true);
          setData(demoDashboard);
          setSelectedRegionId(demoDashboard.selectedRegionId);
        }
      });
    return () => {
      cancelled = true;
      appLog("api load effect cancelled");
    };
  }, [initialData, skipApiLoad]);

  useEffect(() => {
    const markOnline = (): void => setOffline(false);
    const markOffline = (): void => setOffline(true);
    window.addEventListener("online", markOnline);
    window.addEventListener("offline", markOffline);
    return () => {
      window.removeEventListener("online", markOnline);
      window.removeEventListener("offline", markOffline);
    };
  }, []);

  useEffect(() => {
    if (window.location.hash) {
      window.history.replaceState({}, "", `${window.location.pathname}${window.location.search}`);
    }
  }, []);

  const selectedRegion = data.regions.find((region) => region.id === selectedRegionId) ?? data.regions[0];
  const selectedProfile = data.profiles.find((profile) => profile.id === selectedRegion.id) ?? data.profiles[0];
  const activeAlerts = useMemo(
    () => data.alerts.filter((alert) => alert.status === "active").sort((a, b) => severityRank[b.severity] - severityRank[a.severity]),
    [data.alerts]
  );
  const route = window.location.pathname;
  const isOverviewRoute = route === "/" || route === "/overview";

  return (
    <div className="app-shell" data-low-bandwidth={lowBandwidth ? "true" : "false"}>
      <aside className="sidebar" aria-label="Mwangaza navigation">
        <div className="brand-block">
          <div className="brand-mark" aria-hidden="true" />
          <div>
            <h1>{data.project}</h1>
            <p>{data.tagline}</p>
          </div>
        </div>
        <nav>
          <a data-active={isOverviewRoute ? "true" : "false"} href="/overview">{t(language, "overview")}</a>
          <a data-active={route === "/region" ? "true" : "false"} href="/region">{t(language, "regions")}</a>
          <a data-active={route === "/alerts" ? "true" : "false"} href="/alerts">{t(language, "activeAlerts")}</a>
          <a data-active={route === "/reports" ? "true" : "false"} href="/reports">{t(language, "reports")}</a>
          <a data-active={route === "/about" ? "true" : "false"} href="/about">{t(language, "about")}</a>
        </nav>
        <label className="field">
          <span>Language</span>
          <select value={language} onChange={(event) => setLanguage(normalizeLanguage(event.target.value))}>
            <option value="en">English</option>
            <option value="es">Espanol</option>
            <option value="sw">Kiswahili</option>
          </select>
        </label>
        <label className="toggle">
          <input checked={lowBandwidth} onChange={(event) => setLowBandwidth(event.target.checked)} type="checkbox" />
          <span>{t(language, "lowBandwidth")}</span>
        </label>
      </aside>

      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">{t(language, "liveClaim")}</p>
            <h2>{data.source}</h2>
          </div>
          <div className="status-strip">
            <span data-mode={offline ? "offline" : data.dataMode}>{offline ? t(language, "offline") : data.dataMode.toUpperCase()}</span>
            <span>{data.lastUpdated}</span>
            <span>{data.message}</span>
          </div>
        </header>

        {(offline || apiFallback) && (
          <section className="notice" role="alert">
            {offline ? t(language, "offlineWarning") : t(language, "apiFallback")} Timestamp: {data.lastUpdated}.
          </section>
        )}

        {route === "/alerts" ? (
          <AlertsCenter data={data} activeAlerts={activeAlerts} />
        ) : route === "/reports" ? (
          <ReportsCenter data={data} />
        ) : route === "/about" ? (
          <StandalonePage title={t(language, "about")} detail="Dedicated about page pending. This route is separate from Overview." />
        ) : lowBandwidth ? (
          <LowBandwidthView data={data} language={language} activeAlerts={activeAlerts} />
        ) : route === "/region" ? (
          <RegionExplorer
            data={data}
            selectedRegion={selectedRegion}
            selectedProfile={selectedProfile}
            activeAlerts={activeAlerts}
            onSelectRegion={setSelectedRegionId}
          />
        ) : isOverviewRoute ? (
          <OverviewScreen
            data={data}
            language={language}
            selectedRegion={selectedRegion}
            selectedProfile={selectedProfile}
            activeAlerts={activeAlerts}
            onSelectRegion={setSelectedRegionId}
          />
        ) : (
          <StandalonePage title="Page not found" detail="This route does not have an approved screen yet." />
        )}
      </main>
    </div>
  );
}

function StandalonePage({ title, detail }: { title: string; detail: string }): JSX.Element {
  return (
    <section className="standalone-page" aria-label={title}>
      <p className="eyebrow">Section</p>
      <h2>{title}</h2>
      <Placeholder title="Page shell pending" detail={detail} />
    </section>
  );
}

function AlertsCenter({ data, activeAlerts }: { data: DashboardData; activeAlerts: Alert[] }): JSX.Element {
  const [query, setQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [regionFilter, setRegionFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [tab, setTab] = useState<"active" | "preventive" | "resolved" | "all">("active");
  const [selectedAlertKey, setSelectedAlertKey] = useState<string | null>(null);

  const alertRows = useMemo(() => data.alerts.map((alert, index) => ({
    alert,
    id: alertId(alert, index),
    region: data.regions.find((region) => region.id === alert.regionId),
    profile: data.profiles.find((profile) => profile.id === alert.regionId)
  })), [data.alerts, data.profiles, data.regions]);

  const filteredRows = alertRows.filter(({ alert }) => {
    const text = `${alert.region} ${alert.title} ${alert.action} ${alert.quality} ${alert.evidence.flat().join(" ")}`.toLowerCase();
    const matchesQuery = !query || text.includes(query.toLowerCase());
    const matchesSeverity = severityFilter === "all" || alert.severity === severityFilter;
    const matchesRegion = regionFilter === "all" || alert.regionId === regionFilter;
    const matchesStatus = statusFilter === "all" || alert.status === statusFilter;
    const matchesTab = tab === "all" || (tab === "active" && alert.status === "active") || (tab === "preventive" && alert.status === "preventive") || (tab === "resolved" && alert.status === "resolved");
    return matchesQuery && matchesSeverity && matchesRegion && matchesStatus && matchesTab;
  });
  const selectedRow = filteredRows.find((row) => row.id === selectedAlertKey) ?? filteredRows[0] ?? alertRows[0];
  const selectedAlert = selectedRow?.alert;
  const selectedProfile = selectedRow?.profile ?? data.profiles.find((profile) => profile.id === data.selectedRegionId) ?? data.profiles[0];
  const selectedRegion = selectedRow?.region ?? data.regions.find((region) => region.id === selectedAlert?.regionId) ?? data.regions[0];
  const selectedMetrics = selectedProfile?.metrics.length ? selectedProfile.metrics.slice(0, 4) : data.metrics.slice(0, 4);
  const severeCount = activeAlerts.filter((alert) => alert.severity === "critical").length;

  return (
    <section className="alerts-screen" aria-label="Alerts Center">
      <div className="alerts-header">
        <div>
          <h2>Alerts Center</h2>
          <p>Track active, preventive, and resolved drought alerts across IGAD</p>
        </div>
        <div className="alerts-header-actions">
          <button type="button" title="Filtered export endpoint pending">Export</button>
          <button type="button" title="Admin alert settings pending">Alert settings</button>
        </div>
      </div>

      <div className="alerts-filters" aria-label="Alert filters">
        <input aria-label="Search alerts" onChange={(event) => setQuery(event.target.value)} placeholder="Search alerts by region, country, or type..." value={query} />
        <select aria-label="Severity" onChange={(event) => setSeverityFilter(event.target.value)} value={severityFilter}>
          <option value="all">Severity: All</option>
          <option value="critical">Severe</option>
          <option value="warning">Alert</option>
          <option value="watch">Watch</option>
          <option value="normal">Green</option>
          <option value="unknown">Unknown</option>
        </select>
        <select aria-label="Country or region" onChange={(event) => setRegionFilter(event.target.value)} value={regionFilter}>
          <option value="all">Country / Region: All</option>
          {data.regions.map((region) => <option key={region.id} value={region.id}>{region.name}</option>)}
        </select>
        <select aria-label="Status" onChange={(event) => setStatusFilter(event.target.value)} value={statusFilter}>
          <option value="all">Status: All</option>
          <option value="active">Active</option>
          <option value="monitoring">Monitoring</option>
          <option value="preventive">Preventive</option>
          <option value="resolved">Resolved</option>
        </select>
        <select aria-label="Time period" disabled>
          <option>Last 30 days</option>
        </select>
      </div>

      <div className="alert-tabs" aria-label="Alert status tabs">
        {(["active", "preventive", "resolved", "all"] as const).map((item) => (
          <button data-active={tab === item ? "true" : "false"} key={item} onClick={() => setTab(item)} type="button">
            {item === "all" ? "All alerts" : item[0].toUpperCase() + item.slice(1)}
          </button>
        ))}
      </div>

      <section className="alert-summary-grid" aria-label="Alert summary">
        <SummaryTile label="Active alerts" value={activeAlerts.length} detail="Loaded active payload" severity="critical" />
        <SummaryTile label="Severe alerts" value={severeCount} detail="Critical severity rows" severity="critical" />
        <SummaryTile label="Preventive alerts" value="Pending" detail="Forecast alert contract pending" severity="watch" />
        <SummaryTile label="Resolved this month" value="Pending" detail="Resolved history pending" severity="normal" />
        <SummaryTile label="Notifications queued" value="Simulated" detail="No real messages are sent" severity="unknown" />
      </section>

      <div className="alerts-workspace">
        <section className="alerts-queue">
          <div className="section-heading">
            <h2>Active alerts queue</h2>
            <span className="muted">Showing {filteredRows.length ? `1 to ${filteredRows.length}` : "0"} of {alertRows.length} results</span>
          </div>
          {filteredRows.length ? (
            <table>
              <thead><tr><th></th><th>#</th><th>Severity</th><th>Region / Country</th><th>Alert type</th><th>Trigger / Evidence summary</th><th>Date issued</th><th>Status</th><th>Actions</th></tr></thead>
              <tbody>
                {filteredRows.map(({ alert, id }, index) => (
                  <tr data-selected={id === selectedRow?.id ? "true" : "false"} key={id}>
                    <td><input aria-label={`Select ${alert.region}`} checked={id === selectedRow?.id} onChange={() => setSelectedAlertKey(id)} type="radio" /></td>
                    <td>{index + 1}</td>
                    <td><span className="table-badge" data-severity={alert.severity}>{severityLabel(alert.severity)}</span></td>
                    <td>{alert.region}</td>
                    <td>Drought</td>
                    <td>{alert.title}</td>
                    <td>{alert.period}</td>
                    <td>{alert.status}</td>
                    <td><button onClick={() => setSelectedAlertKey(id)} type="button">View</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Placeholder title="No alerts match filters" detail="Adjust search, severity, country or status filters." />
          )}
        </section>

        <aside className="selected-alert-panel">
          {selectedAlert ? (
            <>
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Selected alert</p>
                  <h2>{selectedAlert.region} - {severityLabel(selectedAlert.severity)}</h2>
                  <p>{selectedAlert.title}</p>
                </div>
                <span className="severity-badge" data-severity={selectedAlert.severity}>{severityLabel(selectedAlert.severity)}</span>
              </div>
              <p className="muted">ID: {selectedRow.id}</p>
              <dl className="alert-meta">
                <div><dt>Quality</dt><dd>{qualityLabel(selectedAlert.quality)}</dd></div>
                <div><dt>Issued</dt><dd>{selectedAlert.period}</dd></div>
                <div><dt>Last updated</dt><dd>{selectedRegion.period}</dd></div>
              </dl>
              <div className="selected-alert-metrics">
                {selectedMetrics.map((metric) => (
                  <article key={metric.label}>
                    <span>{metric.label}</span>
                    <strong>{metric.value}<small>{metric.unit}</small></strong>
                    <p>No comparison yet</p>
                  </article>
                ))}
              </div>
              <p>{alertNarrative(selectedAlert, selectedRegion)}</p>
              <div className="alert-detail-actions">
                <a href="/region">View full region analysis</a>
                <a href="/reports">Generate PDF report</a>
              </div>
            </>
          ) : (
            <Placeholder title="No selected alert" detail="No alert is available in the current payload." />
          )}
        </aside>
      </div>

      <div className="alerts-lower-grid">
        <section>
          <h2>Recommended early actions</h2>
          <ul className="action-list">
            {(selectedProfile?.recommendations.length ? selectedProfile.recommendations : data.recommendations).map((item) => <li key={item}>{item}</li>)}
          </ul>
          <a className="text-link" href="/alerts">View all recommended actions</a>
        </section>
        <NotificationOutbox selectedAlert={selectedAlert} />
        <AlertLifecycle selectedAlert={selectedAlert} selectedRegion={selectedRegion} />
      </div>

      <section className="resolved-recent">
        <h2>Resolved & recent</h2>
        <Placeholder title="Resolved alert history pending" detail="The public API does not expose resolved, downgraded or superseded alert history yet." />
      </section>
    </section>
  );
}

function SummaryTile({ label, value, detail, severity }: { label: string; value: number | string; detail: string; severity: Severity }): JSX.Element {
  return (
    <article className="summary-tile" data-severity={severity}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

function NotificationOutbox({ selectedAlert }: { selectedAlert?: Alert }): JSX.Element {
  const rows = ["SMS", "Email", "Telegram", "Dashboard broadcast"];
  return (
    <section>
      <div className="section-heading">
        <h2>Notification outbox <span className="muted">(simulated)</span></h2>
        <span className="muted">No real messages are sent</span>
      </div>
      <table>
        <thead><tr><th>Channel</th><th>Message</th><th>Recipients</th><th>Status</th></tr></thead>
        <tbody>
          {rows.map((channel, index) => (
            <tr key={channel}>
              <td>{channel}</td>
              <td>{selectedAlert ? `${selectedAlert.region}: ${selectedAlert.title}` : "Alert message pending"}</td>
              <td>{index === 0 ? "+251 9** *** 123" : index === 1 ? "ops***@relief.org" : index === 2 ? "@relief_channel" : "All users"}</td>
              <td>{index === 3 ? "Delivered simulated" : "Queued"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function AlertLifecycle({ selectedAlert, selectedRegion }: { selectedAlert?: Alert; selectedRegion: RegionRisk }): JSX.Element {
  const label = selectedAlert?.period ?? selectedRegion.period;
  return (
    <section>
      <h2>Alert lifecycle</h2>
      <ol className="lifecycle-list">
        <li><strong>Triggered</strong><span>{label}</span></li>
        <li><strong>Escalated to {selectedAlert ? severityLabel(selectedAlert.severity) : "current level"}</strong><span>{selectedRegion.period}</span></li>
        <li><strong>Recommended actions generated</strong><span>Simulated from action catalog</span></li>
        <li><strong>Notifications simulated</strong><span>No external adapter enabled</span></li>
        <li><strong>Still active</strong><span>{selectedAlert?.status ?? "unknown"}</span></li>
      </ol>
    </section>
  );
}

interface ReportRow {
  id: string;
  regionId: string;
  region: string;
  type: string;
  period: string;
  generatedOn: string;
  status: "Ready" | "Review" | "Scheduled";
  filename: string;
  profile?: RegionProfile;
  risk?: RegionRisk;
}

function ReportsCenter({ data }: { data: DashboardData }): JSX.Element {
  const [query, setQuery] = useState("");
  const [regionFilter, setRegionFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [tab, setTab] = useState<"generated" | "scheduled" | "templates" | "all">("generated");
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

  const reports = useMemo(() => buildReportRows(data), [data]);
  const filteredReports = reports.filter((report) => {
    const text = `${report.id} ${report.region} ${report.type} ${report.period} ${report.status}`.toLowerCase();
    const matchesQuery = !query || text.includes(query.toLowerCase());
    const matchesRegion = regionFilter === "all" || report.regionId === regionFilter;
    const matchesType = typeFilter === "all" || report.type === typeFilter;
    const matchesStatus = statusFilter === "all" || report.status === statusFilter;
    const matchesTab = tab === "all" || (tab === "generated" && report.status !== "Scheduled") || (tab === "scheduled" && report.status === "Scheduled") || (tab === "templates" && false);
    return matchesQuery && matchesRegion && matchesType && matchesStatus && matchesTab;
  });
  const selectedReport = filteredReports.find((report) => report.id === selectedReportId) ?? filteredReports[0] ?? reports[0];
  const selectedProfile = selectedReport?.profile ?? data.profiles[0];
  const selectedRisk = selectedReport?.risk ?? data.regions[0];
  const selectedMetrics = selectedProfile?.metrics.length ? selectedProfile.metrics.slice(0, 4) : data.metrics.slice(0, 4);

  return (
    <section className="reports-screen" aria-label="Reports Center">
      <div className="reports-header">
        <div>
          <h2>Reports Center</h2>
          <p>Generate, review, and export executive drought reports across IGAD</p>
        </div>
        <div className="reports-header-actions">
          <button type="button" title="Template management pending">Report templates</button>
          <button type="button" title="Report generation endpoint pending">Generate new report</button>
        </div>
      </div>

      <div className="reports-filters" aria-label="Report filters">
        <input aria-label="Search reports" onChange={(event) => setQuery(event.target.value)} placeholder="Search reports by region, type, or ID..." value={query} />
        <select aria-label="Report region" onChange={(event) => setRegionFilter(event.target.value)} value={regionFilter}>
          <option value="all">Region / Country: All</option>
          {data.regions.map((region) => <option key={region.id} value={region.id}>{region.name}</option>)}
        </select>
        <select aria-label="Report type" onChange={(event) => setTypeFilter(event.target.value)} value={typeFilter}>
          <option value="all">Report type: All</option>
          <option value="Executive PDF">Executive PDF</option>
          <option value="Situation Brief">Situation Brief</option>
          <option value="Monthly Summary">Monthly Summary</option>
        </select>
        <select aria-label="Report time period" disabled>
          <option>Last 30 days</option>
        </select>
        <select aria-label="Report status" onChange={(event) => setStatusFilter(event.target.value)} value={statusFilter}>
          <option value="all">Status: All</option>
          <option value="Ready">Ready</option>
          <option value="Review">Review</option>
          <option value="Scheduled">Scheduled</option>
        </select>
      </div>

      <div className="report-tabs" aria-label="Report tabs">
        {(["generated", "scheduled", "templates", "all"] as const).map((item) => (
          <button data-active={tab === item ? "true" : "false"} key={item} onClick={() => setTab(item)} type="button">
            {item === "all" ? "All reports" : item[0].toUpperCase() + item.slice(1)}
          </button>
        ))}
      </div>

      <section className="report-summary-grid" aria-label="Report summary">
        <SummaryTile label="Generated this month" value={reports.filter((report) => report.status !== "Scheduled").length} detail="Derived from visible report rows" severity="normal" />
        <SummaryTile label="Scheduled reports" value={reports.filter((report) => report.status === "Scheduled").length} detail="Schedule contract pending" severity="watch" />
        <SummaryTile label="Pending review" value={reports.filter((report) => report.status === "Review").length} detail="Manual review placeholder" severity="warning" />
        <SummaryTile label="Downloaded" value="Pending" detail="Download audit pending" severity="normal" />
        <SummaryTile label="Shared with partners" value="Simulated" detail="Distribution contract pending" severity="unknown" />
      </section>

      <div className="reports-workspace">
        <section className="reports-queue">
          <div className="section-heading">
            <h2>Generated reports queue</h2>
            <span className="muted">Showing {filteredReports.length ? `1 to ${filteredReports.length}` : "0"} of {reports.length} reports</span>
          </div>
          {filteredReports.length ? (
            <table>
              <thead><tr><th>#</th><th>Report ID</th><th>Region / Country</th><th>Type</th><th>Period</th><th>Generated on</th><th>Status</th><th>Actions</th></tr></thead>
              <tbody>
                {filteredReports.map((report, index) => (
                  <tr data-selected={report.id === selectedReport?.id ? "true" : "false"} key={report.id}>
                    <td>{index + 1}</td>
                    <td>{report.id}</td>
                    <td>{report.region}</td>
                    <td>{report.type}</td>
                    <td>{report.period}</td>
                    <td>{report.generatedOn}</td>
                    <td><span className="report-status">{report.status}</span></td>
                    <td><button onClick={() => setSelectedReportId(report.id)} type="button">View</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Placeholder title="No reports match filters" detail="Adjust search, region, type or status filters." />
          )}
        </section>

        <SelectedReportPanel report={selectedReport} metrics={selectedMetrics} risk={selectedRisk} />
      </div>

      <div className="reports-lower-grid">
        <RecentExports report={selectedReport} data={data} />
        <ReportPreview report={selectedReport} metrics={selectedMetrics} recommendations={selectedProfile?.recommendations ?? data.recommendations} />
        <ReportSidePanels />
      </div>
    </section>
  );
}

function SelectedReportPanel({ report, metrics, risk }: { report?: ReportRow; metrics: Metric[]; risk: RegionRisk }): JSX.Element {
  if (!report) {
    return <section className="selected-report-panel"><Placeholder title="No selected report" detail="No report is available in the current payload." /></section>;
  }

  return (
    <section className="selected-report-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Selected report</p>
          <h2>{report.region} - {report.type} Report</h2>
          <p>Current drought conditions and early action summary</p>
        </div>
        <span className="severity-badge" data-severity={risk.level}>{severityLabel(risk.level)}</span>
      </div>
      <p className="muted">ID: {report.id}</p>
      <dl className="report-meta">
        <div><dt>Quality</dt><dd>{qualityLabel(risk.quality)}</dd></div>
        <div><dt>Generated</dt><dd>{report.generatedOn}</dd></div>
        <div><dt>Based on snapshot</dt><dd>{report.period}</dd></div>
        <div><dt>Language</dt><dd>EN</dd></div>
      </dl>
      <div className="selected-report-metrics">
        {metrics.map((metric) => (
          <article key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}<small>{metric.unit}</small></strong>
            <p>No comparison yet</p>
          </article>
        ))}
      </div>
      <p>{report.region} report is based on the published snapshot for {report.period}. Indicators and recommendations should be used alongside local knowledge.</p>
      <div className="report-actions">
        <a href="/reports">Open full preview</a>
        <a href="/reports">Download PDF</a>
        <a href="/reports">Share</a>
        <a href="/reports">Export data</a>
      </div>
    </section>
  );
}

function RecentExports({ report, data }: { report?: ReportRow; data: DashboardData }): JSX.Element {
  const rows = [
    ["PDF", report?.id ?? "RPT-PENDING", "Mwangaza Dashboard", "Local download", report?.filename ?? data.reportFilename],
    ["CSV", report?.id ?? "RPT-PENDING", "Dashboard export", "Local download", data.exportFilenames.csv],
    ["JSON", report?.id ?? "RPT-PENDING", "Partner API", "api.partner.org", data.exportFilenames.json]
  ];
  return (
    <section className="recent-exports">
      <h2>Recent exports</h2>
      <table>
        <thead><tr><th>Format</th><th>Report ID</th><th>User / Channel</th><th>Destination</th><th>Action</th></tr></thead>
        <tbody>
          {rows.map(([format, id, channel, destination, filename]) => (
            <tr key={`${format}-${id}`}>
              <td>{format}</td><td>{id}</td><td>{channel}</td><td>{destination}</td><td><button title={filename} type="button">Download</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <a className="text-link" href="/reports">View all exports</a>
    </section>
  );
}

function ReportPreview({ report, metrics, recommendations }: { report?: ReportRow; metrics: Metric[]; recommendations: string[] }): JSX.Element {
  return (
    <section className="report-preview-panel">
      <div className="section-heading">
        <h2>Report preview</h2>
        <span className="muted">1 / 8</span>
      </div>
      <article className="report-paper">
        <header>
          <strong>MWANGAZA EARLY WARNING REPORT</strong>
          <span>{report ? `${report.region} - ${report.period}` : "No report selected"}</span>
        </header>
        <div className="preview-map">Drought risk map preview pending real PDF render</div>
        <section>
          <h3>Key findings</h3>
          <ul>{metrics.slice(0, 3).map((metric) => <li key={metric.label}>{metric.label}: {metric.value}{metric.unit}</li>)}</ul>
        </section>
        <section>
          <h3>Recommended early actions</h3>
          <ul>{recommendations.slice(0, 3).map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      </article>
      <div className="viewer-controls" aria-label="PDF viewer controls pending">
        <button type="button">+</button>
        <button type="button">-</button>
        <button type="button">Full screen</button>
        <button type="button">Print</button>
      </div>
    </section>
  );
}

function ReportSidePanels(): JSX.Element {
  return (
    <aside className="report-side-panels">
      <section>
        <h2>Report contents</h2>
        <ul>
          <li>Overview</li>
          <li>Current indicators</li>
          <li>Historical comparison</li>
          <li>Early action recommendations</li>
          <li>Methodology</li>
        </ul>
        <a className="text-link" href="/reports">View full table of contents</a>
      </section>
      <section>
        <h2>Distribution</h2>
        <p>Dashboard: Available here</p>
        <p>Email summary: simulated</p>
        <p>Partner download: pending</p>
      </section>
      <section>
        <h2>Template used</h2>
        <p>Executive PDF</p>
        <p className="muted">Includes map, trends, recommendations and data provenance.</p>
      </section>
    </aside>
  );
}

function buildReportRows(data: DashboardData): ReportRow[] {
  return data.regions.map((region, index) => {
    const profile = data.profiles.find((item) => item.id === region.id);
    const type = index % 3 === 2 ? "Situation Brief" : index % 3 === 1 ? "Monthly Summary" : "Executive PDF";
    const status: ReportRow["status"] = index === 2 ? "Review" : index === 3 ? "Scheduled" : "Ready";
    return {
      id: `RPT-${region.id.toUpperCase()}-2026-${String(index + 1).padStart(3, "0")}`,
      regionId: region.id,
      region: region.name,
      type,
      period: region.period,
      generatedOn: "2026-07-17",
      status,
      filename: region.id === data.selectedRegionId ? data.reportFilename : `mwangaza-${region.id}-report-2026-07-17.pdf`,
      profile,
      risk: region
    };
  });
}

function RegionExplorer({
  data,
  selectedRegion,
  selectedProfile,
  activeAlerts,
  onSelectRegion
}: {
  data: DashboardData;
  selectedRegion: RegionRisk;
  selectedProfile: RegionProfile;
  activeAlerts: DashboardData["alerts"];
  onSelectRegion: (id: string) => void;
}): JSX.Element {
  const selectedAlerts = activeAlerts.filter((alert) => alert.regionId === selectedRegion.id);
  const primaryAlert = selectedAlerts[0] ?? activeAlerts[0];
  const displayMetrics = selectedProfile.metrics.length ? selectedProfile.metrics : data.metrics;
  const ndvi = metricByLabel(displayMetrics, "NDVI");
  const rainfall = metricByLabel(displayMetrics, "Rainfall");
  const lst = metricByLabel(displayMetrics, "LST");
  const composite = metricByLabel(displayMetrics, "Composite");
  const exposure = metricByLabel(displayMetrics, "potentially_exposed");
  const indicatorMetrics = [ndvi, rainfall, lst, composite, exposure].filter((metric): metric is Metric => Boolean(metric));

  return (
    <section className="region-screen" aria-label="Region Explorer">
      <div className="region-hero">
        <div>
          <p className="eyebrow">Region</p>
          <h2>Region Explorer</h2>
          <p>Country and subnational drought analysis</p>
        </div>
        <div className="region-controls">
          <label>
            <span>Country</span>
            <select value={selectedRegion.id} onChange={(event) => onSelectRegion(event.target.value)}>
              {data.regions.map((region) => (
                <option key={region.id} value={region.id}>{region.name}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Subregion / District</span>
            <select disabled>
              <option>{selectedProfile.pilotUnits.length ? "All pilot areas" : "Subnational unavailable"}</option>
            </select>
          </label>
          <label>
            <span>Time period</span>
            <select disabled>
              <option>{selectedRegion.period}</option>
            </select>
          </label>
          <div className="segmented" aria-label="View">
            <button type="button" data-active="true">National view</button>
            <button type="button" disabled>Pilot subnational view</button>
          </div>
        </div>
      </div>

      <div className="region-main-grid">
        <RegionRiskSurface data={data} selectedRegion={selectedRegion} onSelectRegion={onSelectRegion} />
        <section className="region-summary">
          <div className="section-heading">
            <h2>Region Summary</h2>
            <span className="info-dot" title="Operational summary for the selected region.">i</span>
          </div>
          <dl className="summary-list">
            <div><dt>Region</dt><dd>{selectedRegion.name}</dd></div>
            <div><dt>Level</dt><dd>{selectedProfile.pilotUnits.length ? "Country with pilot coverage" : "Country"}</dd></div>
            <div><dt>Potentially exposed population</dt><dd>{exposure?.value ?? "No data"} {exposure?.unit ?? ""}</dd></div>
            <div><dt>Last updated</dt><dd>{selectedRegion.period}</dd></div>
            <div><dt>Data quality</dt><dd>{qualityLabel(selectedRegion.quality)}</dd></div>
            <div><dt>Current alert level</dt><dd><span className="severity-badge" data-severity={selectedRegion.level}>{severityLabel(selectedRegion.level)}</span></dd></div>
          </dl>
          <div className="featured-alert" data-severity={primaryAlert?.severity ?? selectedRegion.level}>
            <strong>{primaryAlert?.title ?? `${severityLabel(selectedRegion.level)} drought status`}</strong>
            <p>{primaryAlert?.action ?? "No active regional alert is available for this period."}</p>
            <a href="/alerts">View all alerts</a>
          </div>
        </section>
      </div>

      <section className="region-indicators" aria-label="Selected indicators">
        {indicatorMetrics.map((metric) => (
          <article key={metric.label} className="indicator-tile" data-severity={metric.severity}>
            <span>{metric.label}</span>
            <strong>{metric.value}<small>{metric.unit}</small></strong>
            <p>{metric.detail}</p>
            <small>No comparison yet</small>
          </article>
        ))}
      </section>

      <div className="region-lower-grid">
        <section>
          <h2>Why this region is at risk <span className="info-dot" title="Estimated from visible indicators until contribution payloads are exposed.">i</span></h2>
          <ContributionRow label="NDVI anomaly" value={0.34} max={0.4} severity={ndvi?.severity ?? "unknown"} />
          <ContributionRow label="Rainfall anomaly" value={0.32} max={0.35} severity={rainfall?.severity ?? "unknown"} />
          <ContributionRow label="Temperature anomaly" value={0.2} max={0.25} severity={lst?.severity ?? "unknown"} />
          <p className="muted">Placeholder contribution weights; replace with backend contribution payload in a future sprint.</p>
        </section>

        <section>
          <div className="section-heading">
            <h2>Subnational ranking</h2>
            <span className="muted">Pilot districts</span>
          </div>
          {selectedProfile.pilotUnits.length ? (
            <table>
              <thead><tr><th>#</th><th>District / Area</th><th>Alert level</th><th>Composite score</th><th>Data quality</th></tr></thead>
              <tbody>
                {selectedProfile.pilotUnits.map((unit, index) => (
                  <tr key={unit}><td>{index + 1}</td><td>{unit}</td><td>{severityLabel(selectedRegion.level)}</td><td>{selectedRegion.score ?? "No data"}</td><td>{selectedRegion.quality}</td></tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Placeholder title="Subnational payload pending" detail="District ranking needs pilot-unit metric rows in the public API." />
          )}
        </section>

        <TrendPanel trends={selectedProfile.trends} />
      </div>

      <div className="region-lower-grid region-final-grid">
        <section>
          <h2>Historical comparison</h2>
          {selectedProfile.historicalRows.length ? (
            <table>
              <thead><tr><th>Period</th><th>Indicator</th><th>Current</th><th>Historical</th><th>Difference</th></tr></thead>
              <tbody>
                {selectedProfile.historicalRows.map((row) => (
                  <tr key={`${row.period}-${row.indicator}`}><td>{row.period}</td><td>{row.indicator}</td><td>{row.current}</td><td>{row.historical}</td><td>{row.difference}</td></tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Placeholder title="Historical comparison pending" detail="Comparable historical rows are not available for this live region payload yet." />
          )}
        </section>
        <section>
          <h2>Recommended early actions</h2>
          <ul className="action-list">
            {(selectedProfile.recommendations.length ? selectedProfile.recommendations : data.recommendations).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
        <section id="about" className="pilot-note">
          <h2>About the pilot analysis</h2>
          <p>Enhanced subnational analysis is limited to configured pilot areas. Other IGAD coverage remains national unless a validated pilot payload is available.</p>
          <span className="future-link">Methodology page pending</span>
        </section>
      </div>

      <footer className="region-footer">
        <p>Mwangaza is a decision-support prototype. Estimates should be used alongside local knowledge.</p>
        <p>Developed for the IGAD Hackathon 2026.</p>
      </footer>
    </section>
  );
}

function loadingApiDashboard(): DashboardData {
  return {
    ...demoDashboard,
    dataMode: "cache",
    source: "Loading public API",
    message: "Waiting for /api/v1/**",
    alerts: [],
    regions: demoDashboard.regions.map(stripUiGeometry),
    metrics: demoDashboard.metrics.map((metric) => ({ ...metric, detail: "Waiting for API response" }))
  };
}

function stripUiGeometry(region: RegionRisk): RegionRisk {
  return {
    id: region.id,
    name: region.name,
    score: region.score,
    level: region.level,
    quality: region.quality,
    period: region.period
  };
}

function shouldLoadApiByDefault(): boolean {
  const params = new URLSearchParams(window.location.search);
  return import.meta.env.MODE === "api" || params.get("api") === "1";
}

function appLog(message: string, fields: Record<string, unknown> = {}): void {
  const params = new URLSearchParams(window.location.search);
  if (import.meta.env.MODE !== "api" && params.get("debug") !== "1") {
    return;
  }
  console.info("[mwangaza.frontend.app]", message, fields);
}

function RegionRiskSurface({
  data,
  selectedRegion,
  onSelectRegion
}: {
  data: DashboardData;
  selectedRegion: RegionRisk;
  onSelectRegion: (id: string) => void;
}): JSX.Element {
  const geography = useMemo(() => buildRiskFeatureCollection(data.regions), [data.regions]);
  const hasGeometry = geography.features.length > 0;
  return (
    <section className="region-map-panel">
      <div className="section-heading">
        <h2>{selectedRegion.name} Risk Map</h2>
        <span className="info-dot" title="Country and pilot area risk from the current dashboard payload.">i</span>
      </div>
      <div className="region-map-stage" aria-label="Regions map">
        {hasGeometry ? (
          <ComposableMap
            projection="geoMercator"
            projectionConfig={{ center: [38, 8], scale: 760 }}
            width={760}
            height={360}
            className="region-svg-map"
          >
            <Geographies geography={geography}>
              {({ geographies }) => geographies.map((geo) => {
                const region = geo.properties.region as RegionRisk;
                return (
                  <Geography
                    aria-label={`${region.name}: ${region.score ?? "No data"} ${region.level}`}
                    geography={geo}
                    key={geo.rsmKey}
                    onClick={() => onSelectRegion(region.id)}
                    role="button"
                    style={{
                      default: {
                        fill: mapFill(region.level),
                        stroke: region.id === selectedRegion.id ? "#172033" : "#ffffff",
                        strokeWidth: region.id === selectedRegion.id ? 2.8 : 1.3,
                        outline: "none"
                      },
                      hover: { fill: mapHoverFill(region.level), outline: "none" },
                      pressed: { fill: mapHoverFill(region.level), outline: "none" }
                    }}
                    tabIndex={0}
                  />
                );
              })}
            </Geographies>
          </ComposableMap>
        ) : (
          <Placeholder title="Map geometry pending" detail="The public API has not provided GeoJSON UI geometry for this payload yet." />
        )}
        <div className="map-readout" role="list">
          {data.regions.map((region) => (
            <button
              data-selected={region.id === selectedRegion.id ? "true" : "false"}
              key={region.id}
              onClick={() => onSelectRegion(region.id)}
              type="button"
            >
              <span>{region.name}</span>
              <strong>{region.score ?? "No data"}</strong>
              <small>{region.level} | {region.quality}</small>
            </button>
          ))}
        </div>
      </div>
      <div className="map-legend" aria-label="Risk legend">
        <span data-severity="normal">Low</span>
        <span data-severity="watch">Watch</span>
        <span data-severity="warning">Alert</span>
        <span data-severity="critical">Severe</span>
        <span data-severity="unknown">Not assessed</span>
      </div>
      <p className="muted">Risk levels indicate current drought risk relative to the historical baseline.</p>
    </section>
  );
}

function ContributionRow({
  label,
  value,
  max,
  severity
}: {
  label: string;
  value: number;
  max: number;
  severity: Severity;
}): JSX.Element {
  return (
    <div className="contribution-row">
      <div>
        <span>{label}</span>
        <strong>{value.toFixed(2)} / {max.toFixed(2)}</strong>
      </div>
      <div className="contribution-track">
        <span data-severity={severity} style={{ width: `${Math.min(100, (value / max) * 100)}%` }} />
      </div>
    </div>
  );
}

function Placeholder({ title, detail }: { title: string; detail: string }): JSX.Element {
  return (
    <div className="placeholder-box">
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}

interface RiskFeature {
  type: "Feature";
  properties: { region: RegionRisk };
  geometry: GeoJsonGeometry;
}

interface RiskFeatureCollection {
  type: "FeatureCollection";
  features: RiskFeature[];
}

function buildRiskFeatureCollection(regions: RegionRisk[]): RiskFeatureCollection {
  return {
    type: "FeatureCollection",
    features: regions.filter((region) => region.uiGeometry).map((region) => ({
      type: "Feature",
      properties: { region },
      geometry: region.uiGeometry as GeoJsonGeometry
    }))
  };
}

function mapFill(severity: Severity): string {
  const fills: Record<Severity, string> = {
    normal: "#2f9e44",
    watch: "#f2c94c",
    warning: "#f08c2e",
    critical: "#d92d20",
    unknown: "#c4c9d1"
  };
  return fills[severity];
}

function mapHoverFill(severity: Severity): string {
  const fills: Record<Severity, string> = {
    normal: "#237a37",
    watch: "#d7a600",
    warning: "#d66b1f",
    critical: "#b42318",
    unknown: "#98a2b3"
  };
  return fills[severity];
}

function metricByLabel(metrics: Metric[], label: string): Metric | undefined {
  return metrics.find((metric) => metric.label.toLowerCase().includes(label.toLowerCase()));
}

function severityLabel(severity: Severity): string {
  const labels: Record<Severity, string> = {
    critical: "Severe",
    warning: "Alert",
    watch: "Watch",
    normal: "Low",
    unknown: "Unknown"
  };
  return labels[severity];
}

function qualityLabel(value: string): string {
  if (value === "ok" || value === "normal") {
    return "High";
  }
  if (value === "degraded" || value === "watch") {
    return "Medium";
  }
  if (value === "no_data" || value === "unknown") {
    return "Insufficient";
  }
  return value;
}

function alertId(alert: Alert, index: number): string {
  return `ALT-${alert.regionId.toUpperCase()}-${String(index + 1).padStart(3, "0")}`;
}

function alertNarrative(alert: Alert, region: RegionRisk): string {
  const score = region.score === null ? "no published composite score" : `a composite score of ${region.score}`;
  return `${alert.region} is classified as ${severityLabel(alert.severity).toLowerCase()} for ${alert.period}, with ${score}. ${alert.title}. Recommendations are decision support and should be validated with local knowledge.`;
}

function OverviewRiskMap({
  data,
  selectedRegion,
  onSelectRegion
}: {
  data: DashboardData;
  selectedRegion: RegionRisk;
  onSelectRegion: (id: string) => void;
}): JSX.Element {
  const geography = useMemo(() => buildRiskFeatureCollection(data.regions), [data.regions]);
  const hasGeometry = geography.features.length > 0;

  return (
    <section className="overview-map-panel">
      <div className="section-heading">
        <h2>Risk Map - IGAD</h2>
        <span className="info-dot" title="Current drought risk relative to the historical baseline.">i</span>
      </div>
      <div className="overview-map-stage" aria-label="Overview risk map">
        {hasGeometry ? (
          <ComposableMap
            projection="geoMercator"
            projectionConfig={{ center: [38, 8], scale: 760 }}
            width={760}
            height={360}
            className="region-svg-map"
          >
            <Geographies geography={geography}>
              {({ geographies }) => geographies.map((geo) => {
                const region = geo.properties.region as RegionRisk;
                return (
                  <Geography
                    aria-label={`${region.name}: ${region.score ?? "No data"} ${region.level}`}
                    geography={geo}
                    key={geo.rsmKey}
                    onClick={() => onSelectRegion(region.id)}
                    role="button"
                    style={{
                      default: {
                        fill: mapFill(region.level),
                        stroke: region.id === selectedRegion.id ? "#172033" : "#ffffff",
                        strokeWidth: region.id === selectedRegion.id ? 2.8 : 1.3,
                        outline: "none"
                      },
                      hover: { fill: mapHoverFill(region.level), outline: "none" },
                      pressed: { fill: mapHoverFill(region.level), outline: "none" }
                    }}
                    tabIndex={0}
                  />
                );
              })}
            </Geographies>
          </ComposableMap>
        ) : (
          <Placeholder title="Map geometry pending" detail="The public API has not provided GeoJSON UI geometry for this payload yet." />
        )}
        <div className="map-controls" aria-label="Map controls pending">
          <button type="button" title="Reset map view pending">Home</button>
          <button type="button" title="Zoom in pending">+</button>
          <button type="button" title="Zoom out pending">-</button>
          <button type="button" title="Layer selector pending">Layers</button>
        </div>
      </div>
      <div className="map-legend" aria-label="Risk legend">
        <span data-severity="normal">Green</span>
        <span data-severity="watch">Yellow</span>
        <span data-severity="warning">Orange</span>
        <span data-severity="critical">Red</span>
        <span data-severity="unknown">Unknown</span>
      </div>
      <p className="muted">Risk levels indicate current drought risk relative to the historical baseline.</p>
    </section>
  );
}

function OverviewScreen({
  data,
  language,
  selectedRegion,
  selectedProfile,
  activeAlerts,
  onSelectRegion
}: {
  data: DashboardData;
  language: Language;
  selectedRegion: RegionRisk;
  selectedProfile: RegionProfile;
  activeAlerts: DashboardData["alerts"];
  onSelectRegion: (id: string) => void;
}): JSX.Element {
  const displayMetrics = selectedProfile.metrics.length ? selectedProfile.metrics : data.metrics;
  const topAlerts = activeAlerts.slice(0, 4);

  return (
    <section className="overview-screen" aria-label={t(language, "overview")}>
      <div className="overview-top-grid">
        <OverviewRiskMap data={data} selectedRegion={selectedRegion} onSelectRegion={onSelectRegion} />
        <section className="overview-alerts">
          <div className="section-heading">
            <h2>{t(language, "activeAlerts")}</h2>
            <a className="text-link" href="/alerts">View all alerts</a>
          </div>
          <div className="overview-alert-list">
            {topAlerts.length ? topAlerts.map((alert, index) => (
              <article className="overview-alert-item" data-severity={alert.severity} key={`${alert.regionId}-${alert.title}`}>
                <span className="alert-rank">{index + 1}</span>
                <span className="alert-icon" aria-hidden="true">!</span>
                <div>
                  <h3>{alert.region} - {severityLabel(alert.severity)}</h3>
                  <p>{alert.title}</p>
                  <small>{alert.period} | quality {alert.quality}</small>
                </div>
                <a href="/alerts">View details</a>
              </article>
            )) : (
              <Placeholder title="No active alerts" detail="No active alert payload is available for this snapshot." />
            )}
          </div>
        </section>
      </div>

      <section className="selected-region-panel">
        <div className="section-heading selected-heading">
          <h2>Selected region: <strong>{selectedRegion.name}</strong></h2>
          <label>
            <span>Change region</span>
            <select value={selectedRegion.id} onChange={(event) => onSelectRegion(event.target.value)} aria-label={t(language, "selectedRegion")}>
              {data.regions.map((region) => (
                <option key={region.id} value={region.id}>{region.name}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="overview-metric-grid">
          {displayMetrics.map((metric) => (
            <article key={metric.label} className="overview-metric" data-severity={metric.severity}>
              <span>{metric.label}</span>
              <strong>{metric.value}<small>{metric.unit}</small></strong>
              <p>{metric.detail}</p>
              <small>No comparison yet</small>
            </article>
          ))}
        </div>
      </section>

      <div className="overview-bottom-grid">
        <TrendPanel title={`Trends (${selectedRegion.name})`} trends={selectedProfile.trends} />
        <section className="overview-actions">
          <h2>Early Action Recommendations</h2>
          <ul className="action-list">
            {(selectedProfile.recommendations.length ? selectedProfile.recommendations : data.recommendations).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <a className="text-link" href="/alerts">See guidance for severe drought</a>
        </section>
        <section className="overview-share">
          <a className="report-cta" href="/reports">
            <strong>Generate Executive PDF Report</strong>
            <span>{data.reportFilename}</span>
          </a>
          <div className="export-box">
            <h2>Export data</h2>
            <a href="/reports">CSV <span>{data.exportFilenames.csv}</span></a>
            <a href="/reports">JSON <span>{data.exportFilenames.json}</span></a>
          </div>
        </section>
      </div>

      <footer className="overview-footer">
        <p>Mwangaza is a decision-support prototype. Estimates are based on satellite observations and historical data and should be used alongside local knowledge.</p>
        <p>Built for the IGAD Hackathon 2026 using regional and open climate data.</p>
      </footer>
    </section>
  );
}

function TrendPanel({ trends, title = "Indicator Trends" }: { trends: TrendSeries[]; title?: string }): JSX.Element {
  return (
    <section>
      <h2>{title}</h2>
      <div className="trend-grid">
        {trends.length ? trends.map((trend) => (
          <article className="trend" key={trend.indicator}>
            <h3>{trend.label}</h3>
            <p>{trend.unit} | {trend.source}</p>
            <div className="sparkline" aria-label={`${trend.label} sparkline`}>
              {trend.points.map((point) => (
                <span
                  key={point.label}
                  style={{ height: `${Math.max(12, ((point.value ?? 0) / Math.max(...trend.points.map((p) => p.value ?? 1))) * 80)}px` }}
                  title={`${point.label}: ${point.value ?? "gap"} baseline ${point.baseline ?? "n/a"}`}
                />
              ))}
            </div>
          </article>
        )) : (
          <Placeholder title="Trend payload pending" detail="No trend series are available for the selected region yet." />
        )}
      </div>
    </section>
  );
}

function LowBandwidthView({
  data,
  language,
  activeAlerts
}: {
  data: DashboardData;
  language: Language;
  activeAlerts: DashboardData["alerts"];
}): JSX.Element {
  return (
    <section className="lite-view">
      <h2>{t(language, "lowBandwidth")}</h2>
      <table>
        <thead><tr><th>Indicator</th><th>Value</th><th>Detail</th></tr></thead>
        <tbody>
          {data.metrics.map((metric) => (
            <tr key={metric.label}><td>{metric.label}</td><td>{metric.value} {metric.unit}</td><td>{metric.detail}</td></tr>
          ))}
        </tbody>
      </table>
      <h2>{t(language, "activeAlerts")}</h2>
      <ul>
        {activeAlerts.map((alert) => (
          <li key={`${alert.regionId}-${alert.title}`}>{alert.region}: {alert.title} - {alert.action}</li>
        ))}
      </ul>
      <p>{data.reportFilename}</p>
      <p>/api/v1/snapshots/latest</p>
    </section>
  );
}
