import { useEffect, useMemo, useState } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { activateAdminConfig, loadAdminConfig, loadApiDashboardDetails, loadApiDashboardSnapshot, loadTechnicalStatus, saveAdminConfig } from "./api";
import { demoDashboard } from "./fixtures";
import { normalizeLanguage, t } from "./i18n";
import { NorthernKenyaScenario } from "./components/NorthernKenyaScenario";
import { LandingPage } from "./pages/LandingPage";
import type { AdminConfigResponse, AdminConfiguration, AdministrativeUnit, Alert, DashboardData, GeoJsonGeometry, HistoricalRow, Language, Metric, RegionProfile, RegionRisk, Severity, TechnicalStatusResponse, TrendSeries } from "./types";
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
const IGAD_COUNTRIES: Array<{ id: string; name: string }> = [
  { id: "dji", name: "Djibouti" },
  { id: "eri", name: "Eritrea" },
  { id: "eth", name: "Ethiopia" },
  { id: "ken", name: "Kenya" },
  { id: "sdn", name: "Sudan" },
  { id: "som", name: "Somalia" },
  { id: "ssd", name: "South Sudan" },
  { id: "uga", name: "Uganda" }
];
const LIVE_REFRESH_POLL_MS = 3000;
const LIVE_REFRESH_MAX_ATTEMPTS = 30;

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
    let refreshTimer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;
    appLog("api load effect start");
    const loadSnapshot = async (): Promise<void> => {
      try {
        const snapshotData = await loadApiDashboardSnapshot();
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
          const next = await loadApiDashboardDetails(snapshotData);
          if (!cancelled) {
            appLog("details applied", {
              alerts: next.alerts.length,
              forecastAvailable: next.forecastDiagnostics.available,
              selectedRegionId: next.selectedRegionId
            });
            setData(next);
            setSelectedRegionId(next.selectedRegionId);
          }
          if (!cancelled && snapshotData.dataMode === "cache" && attempt < LIVE_REFRESH_MAX_ATTEMPTS) {
            attempt += 1;
            appLog("live snapshot retry scheduled", { attempt, delayMs: LIVE_REFRESH_POLL_MS });
            refreshTimer = setTimeout(() => { void loadSnapshot(); }, LIVE_REFRESH_POLL_MS);
          }
        } else {
          appLog("snapshot ignored after cancellation", {
            dataMode: snapshotData.dataMode,
            selectedRegionId: snapshotData.selectedRegionId
          });
        }
      } catch {
        if (!cancelled) {
          appLog("api fallback applied");
          setApiFallback(true);
          setData(demoDashboard);
          setSelectedRegionId(demoDashboard.selectedRegionId);
        }
      }
    };
    void loadSnapshot();
    return () => {
      cancelled = true;
      if (refreshTimer !== undefined) clearTimeout(refreshTimer);
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
  const isAlertsRoute = route === "/alerts" || route.startsWith("/alerts/");
  const requestedAlertId = route.startsWith("/alerts/") ? decodeURIComponent(route.slice("/alerts/".length)) : undefined;

  if (route === "/landing") return <LandingPage />;

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
          <a data-active={isAlertsRoute ? "true" : "false"} href="/alerts">{t(language, "activeAlerts")}</a>
          <a data-active={route === "/reports" ? "true" : "false"} href="/reports">{t(language, "reports")}</a>
          <a data-active={route === "/about" ? "true" : "false"} href="/about">{t(language, "about")}</a>
          <a data-active={route === "/admin" ? "true" : "false"} href="/admin">Admin</a>
          <a className="technical-link" data-active={route === "/technical" ? "true" : "false"} href="/technical">Technical status</a>
        </nav>
        <div className="language-control">
          <span>{t(language, "language")}</span>
          <div className="language-segments" aria-label={t(language, "language")}>
            {(["en", "sw", "so"] as const).map((item) => <button data-active={language === item ? "true" : "false"} key={item} onClick={() => setLanguage(item)} type="button">{item.toUpperCase()}</button>)}
          </div>
          <button className="legacy-language" data-active={language === "es" ? "true" : "false"} onClick={() => setLanguage("es")} type="button">ES</button>
        </div>
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
          <div className="topbar-placeholders" aria-label="Unavailable account controls">
            <span title={t(language, "notificationsUnavailable")}>{t(language, "notificationsUnavailable")}</span>
            <span title={t(language, "accountUnavailable")}>{t(language, "accountUnavailable")}</span>
          </div>
        </header>

        {(offline || apiFallback) && (
          <section className="notice" role="alert">
            {offline ? t(language, "offlineWarning") : t(language, "apiFallback")} Timestamp: {data.lastUpdated}.
          </section>
        )}

        {data.dataMode === "demo" && (
          <section className="demo-banner" role="status">
            <strong>Demo data</strong>
            <span>Offline fixture · reference_date: {data.referenceDate ?? data.lastUpdated} · snapshot_id: {data.snapshotId ?? "mwangaza-offline-demo-v1"}</span>
            <code>python scripts/reset_demo.py</code>
          </section>
        )}

        {isAlertsRoute && lowBandwidth ? (
          <LowBandwidthView
            activeAlerts={activeAlerts}
            data={data}
            language={language}
            onSelectRegion={setSelectedRegionId}
            route={route}
            selectedProfile={selectedProfile}
            selectedRegion={selectedRegion}
          />
        ) : isAlertsRoute ? (
          <AlertsCenter data={data} activeAlerts={activeAlerts} requestedAlertId={requestedAlertId} />
        ) : route === "/reports" ? (
          <ReportsCenter data={data} />
        ) : route === "/about/provenance" ? (
          <ProvenanceScreen />
        ) : route === "/about" ? (
          <AboutScreen data={data} />
        ) : route === "/admin" ? (
          <AdminPanel lowBandwidth={lowBandwidth} />
        ) : route === "/technical" ? (
          <TechnicalPanel lowBandwidth={lowBandwidth} />
        ) : lowBandwidth ? (
          <LowBandwidthView
            activeAlerts={activeAlerts}
            data={data}
            language={language}
            onSelectRegion={setSelectedRegionId}
            route={route}
            selectedProfile={selectedProfile}
            selectedRegion={selectedRegion}
          />
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

function TechnicalPanel({ lowBandwidth }: { lowBandwidth: boolean }): JSX.Element {
  const [status, setStatus] = useState<TechnicalStatusResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = (): void => {
    setLoading(true);
    setError("");
    loadTechnicalStatus()
      .then(setStatus)
      .catch(() => setError("Operational status is unavailable."))
      .finally(() => setLoading(false));
  };

  useEffect(refresh, []);
  const metrics = status?.metrics;

  return (
    <section className={lowBandwidth ? "technical-screen technical-lite" : "technical-screen"} aria-label="Technical status">
      <header className="technical-header">
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Technical status</h2>
          <p>API readiness, request health and processing counters.</p>
        </div>
        <div className="technical-header-actions">
          <span data-state={status?.status ?? "loading"}>{loading ? "Checking" : status?.status ?? "Unavailable"}</span>
          <button onClick={refresh} type="button">Refresh</button>
        </div>
      </header>

      {error ? <div className="notice" role="alert">{error}</div> : null}

      <section className="technical-summary" aria-label="Operational summary">
        <div><span>Readiness</span><strong>{status?.readiness.status ?? "checking"}</strong></div>
        <div><span>Average duration</span><strong>{metrics ? `${metrics.duration_ms_average} ms` : "-"}</strong></div>
        <div><span>Errors</span><strong>{metrics?.errors_total ?? "-"}</strong></div>
        <div><span>Active alerts</span><strong>{metrics?.active_alerts ?? "-"}</strong></div>
      </section>

      <div className="technical-grid">
        <section>
          <h3>Dependency checks</h3>
          <table>
            <thead><tr><th>Dependency</th><th>Status</th></tr></thead>
            <tbody>
              {Object.entries(status?.readiness.checks ?? {}).map(([name, value]) => (
                <tr key={name}><td>{name}</td><td data-check={value}>{value}</td></tr>
              ))}
              {!status ? <tr><td colSpan={2}>Waiting for readiness data.</td></tr> : null}
            </tbody>
          </table>
        </section>
        <section>
          <h3>Runtime metrics</h3>
          <dl>
            <div><dt>Requests</dt><dd>{metrics?.requests_total ?? "-"}</dd></div>
            <div><dt>Cache hit ratio</dt><dd>{metrics ? `${Math.round(metrics.cache_hit_ratio * 100)}%` : "-"}</dd></div>
            <div><dt>Regions processed</dt><dd>{metrics?.regions_processed ?? "-"}</dd></div>
            <div><dt>Run ID</dt><dd>{status?.run_id ?? "-"}</dd></div>
          </dl>
        </section>
      </div>
    </section>
  );
}

function AdminPanel({ lowBandwidth }: { lowBandwidth: boolean }): JSX.Element {
  const [response, setResponse] = useState<AdminConfigResponse | null>(null);
  const [draft, setDraft] = useState<AdminConfiguration>(defaultAdminDraft());
  const [message, setMessage] = useState("Loading admin configuration.");
  const [error, setError] = useState("");

  useEffect(() => {
    loadAdminConfig()
      .then((next) => {
        setResponse(next);
        setDraft(next.active_version?.configuration ?? defaultAdminDraft());
        setMessage("Public demo mode. Changes are available without credentials.");
      })
      .catch(() => {
        setMessage("Admin configuration endpoint is unavailable.");
      });
  }, []);

  const active = response?.active_version ?? null;
  const versions = response?.versions ?? [];

  const save = async (): Promise<void> => {
    setError("");
    try {
      const next = await saveAdminConfig(draft);
      setResponse(next);
      setMessage(`Saved append-only version ${next.saved_version?.version_id ?? ""}. No recalculation was triggered.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Configuration validation failed.");
    }
  };

  const activate = async (versionId: string): Promise<void> => {
    setError("");
    try {
      const next = await activateAdminConfig(versionId);
      setResponse(next);
      setDraft(next.active_version?.configuration ?? draft);
      setMessage(`Activated ${versionId}. Refresh jobs remain manual.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Activation failed.");
    }
  };

  const updateThresholdLabel = (label: string): void => {
    setDraft({ ...draft, thresholds: { ...draft.thresholds, label } });
  };
  const updateWarningAction = (action: string): void => {
    setDraft({
      ...draft,
      actions: {
        ...draft.actions,
        templates: {
          ...draft.actions.templates,
          warning: { ...draft.actions.templates.warning, action }
        }
      }
    });
  };

  return (
    <section className="admin-screen" aria-label="Admin Configuration">
      <div className="admin-header">
        <div>
          <p className="eyebrow">Demo admin</p>
          <h2>Admin Configuration</h2>
          <p>Version thresholds and early-action guidance without recalculating operational data.</p>
        </div>
        <span data-state="configured">Public access</span>
      </div>

      <section className="admin-login" aria-label="Admin access status">
        <p>{message}</p>
        {error ? <div className="notice" role="alert">{error}</div> : null}
      </section>

      <div className="admin-grid">
        <section className="admin-editor">
          <h2>Configuration editor</h2>
          <label className="field">
            <span>Threshold label</span>
            <input
              aria-label="Threshold label"
              disabled={!response}
              onChange={(event) => updateThresholdLabel(event.target.value)}
              value={draft.thresholds.label}
            />
          </label>
          <label className="field">
            <span>Warning action</span>
            <textarea
              aria-label="Warning action"
              disabled={!response}
              onChange={(event) => updateWarningAction(event.target.value)}
              value={draft.actions.templates.warning.action}
            />
          </label>
          <div className="admin-actions">
            <button disabled={!response} onClick={save} type="button">Save new version</button>
            <span>No refresh, forecast or Earth Engine call is triggered.</span>
          </div>
        </section>

        <section className="admin-active">
          <h2>Active version</h2>
          {active ? (
            <dl>
              <div><dt>Version</dt><dd>{active.version_id}</dd></div>
              <div><dt>Status</dt><dd>{active.status}</dd></div>
              <div><dt>Created</dt><dd>{active.created_at}</dd></div>
              <div><dt>Hash prefix</dt><dd>{active.content_hash.slice(0, 12)}</dd></div>
            </dl>
          ) : (
            <Placeholder title="No active version" detail="Save and activate a valid configuration to make it current." />
          )}
          <Placeholder title="Demo scope" detail="This hackathon panel is intentionally public. Add institutional identity and authorization before production use." />
        </section>
      </div>

      <section className={lowBandwidth ? "admin-history admin-history-lite" : "admin-history"}>
        <h2>Version history</h2>
        <table>
          <thead><tr><th>Version</th><th>Status</th><th>Created by</th><th>Validation</th><th>Action</th></tr></thead>
          <tbody>
            {versions.map((version) => (
              <tr key={version.version_id}>
                <td>{version.version_id}</td>
                <td>{version.status}</td>
                <td>{version.created_by}</td>
                <td>{version.validation_errors.length ? version.validation_errors.join("; ") : "valid"}</td>
                <td>
                  <button
                    disabled={version.status === "active" || version.validation_errors.length > 0}
                    onClick={() => void activate(version.version_id)}
                    type="button"
                  >
                    Activate
                  </button>
                </td>
              </tr>
            ))}
            {!versions.length ? <tr><td colSpan={5}>No configuration versions yet.</td></tr> : null}
          </tbody>
        </table>
      </section>
    </section>
  );
}

function defaultAdminDraft(): AdminConfiguration {
  return {
    schema_version: "mwangaza.admin.v1",
    thresholds: {
      threshold_version: "prototype-thresholds-v1",
      domain_min: 0,
      domain_max: 100,
      bands: [
        { level: "green", minimum: 0, maximum: 25 },
        { level: "yellow", minimum: 25, maximum: 50 },
        { level: "orange", minimum: 50, maximum: 75 },
        { level: "red", minimum: 75, maximum: 100 }
      ],
      is_official: false,
      label: "prototype-not-igad-official"
    },
    actions: {
      recommendation_version: "actions-v1",
      templates: {
        green: { level: "green", action: "Continue routine monitoring", suggested_actor: "Analyst", urgency: "monitoring" },
        watch: { level: "watch", action: "Prepare early action checklist", suggested_actor: "Program lead", urgency: "preparation" },
        warning: { level: "warning", action: "Preposition supplies and brief partners", suggested_actor: "Operations lead", urgency: "prepositioning" },
        emergency: { level: "emergency", action: "Activate urgent coordination review", suggested_actor: "Incident lead", urgency: "urgent_activation" },
        unknown: { level: "unknown", action: "Review data quality before intervention", suggested_actor: "Data lead", urgency: "data_review" }
      }
    }
  };
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

function AboutScreen({ data }: { data: DashboardData }): JSX.Element {
  const ndvi = metricByLabel(data.metrics, "NDVI");
  const rainfall = metricByLabel(data.metrics, "Rainfall");
  const lst = metricByLabel(data.metrics, "LST");
  const composite = metricByLabel(data.metrics, "Composite");
  const exposure = metricByLabel(data.metrics, "potentially_exposed");
  const pilotRegions = data.profiles.filter((profile) => profile.pilotUnits.length > 0);

  const capabilities = [
    {
      title: "Vegetation Monitoring",
      icon: "NDVI",
      detail: "Compares recent vegetation conditions with the historical seasonal baseline.",
      metric: ndvi
    },
    {
      title: "Rainfall Monitoring",
      icon: "RAIN",
      detail: "Tracks recent rainfall totals and deficit signals against expected seasonal conditions.",
      metric: rainfall
    },
    {
      title: "Surface Temperature",
      icon: "LST",
      detail: "Uses satellite-derived land surface temperature as complementary heat-stress evidence.",
      metric: lst
    },
    {
      title: "Early Action",
      icon: "ACT",
      detail: "Turns configured risk signals into alerts, recommendations and report-ready summaries.",
      metric: composite
    }
  ];

  const sources = [
    ["Google Earth Engine", "Cloud geospatial processing platform used to access and aggregate satellite and climate datasets."],
    ["MODIS vegetation / NDVI", "Satellite imagery used to derive recent vegetation conditions and NDVI signals."],
    ["CHIRPS rainfall", "Satellite and station-based rainfall estimates used to calculate recent totals and anomalies."],
    ["MODIS Land Surface Temperature", "Satellite-derived land surface temperature used as a complementary drought stress indicator."],
    ["Administrative boundaries", "National and pilot subnational geography used for aggregation and map display."],
    ["Population / exposure", exposure ? `${exposure.value}${exposure.unit} estimate. ${exposure.detail}` : "No valid exposure dataset is available in this snapshot."]
  ];

  return (
    <section className="about-screen" aria-label="About Mwangaza">
      <div className="about-header">
        <div>
          <p className="eyebrow">About</p>
          <h2>About</h2>
          <p>Methodology, data sources and project information</p>
        </div>
        <div className="about-header-actions">
          <span>Version 1.0.0 prototype</span>
          <span>{data.dataMode.toUpperCase()}</span>
          <span>{data.lastUpdated}</span>
          <button type="button" title="Documentation/status refresh endpoint pending">Refresh status</button>
        </div>
      </div>

      <section className="about-hero">
        <div className="about-hero-copy">
          <h2>About Mwangaza</h2>
          <p>Mwangaza is a satellite-powered drought early warning and early action platform designed for the IGAD region.</p>
          <p>It combines vegetation, rainfall and land-surface-temperature indicators with historical baselines to help identify deteriorating conditions and translate them into actionable early-warning information.</p>
          <div className="about-capabilities" aria-label="Mwangaza capabilities">
            {capabilities.map((capability) => (
              <article key={capability.title} title={capability.detail}>
                <span>{capability.icon}</span>
                <strong>{capability.title}</strong>
                <small>{capability.metric ? `${capability.metric.value}${capability.metric.unit}` : "No data"}</small>
              </article>
            ))}
          </div>
        </div>
        <div className="about-illustration" aria-label="Satellite drought monitoring concept">
          <div className="sun" />
          <div className="satellite">SAT</div>
          <div className="horn-map">
            <span data-severity="normal" />
            <span data-severity="watch" />
            <span data-severity="warning" />
            <span data-severity="critical" />
          </div>
          <div className="field-lines" />
        </div>
      </section>

      <div className="about-main-grid">
        <section className="about-panel">
          <h2>Data Sources</h2>
          <p>Mwangaza uses open satellite, climate and administrative datasets. Every indicator keeps its source, period, unit and processing context visible where the API provides it.</p>
          <div className="source-list">
            {sources.map(([name, detail]) => (
              <article key={name}>
                <span>{name.slice(0, 2).toUpperCase()}</span>
                <div>
                  <strong>{name}</strong>
                  <p>{detail}</p>
                </div>
              </article>
            ))}
          </div>
          <Placeholder title="Source detail drawers pending" detail="Dataset resolution, frequency, transformations and limitations need a dedicated metadata contract." />
        </section>

        <section className="about-panel">
          <h2>About This Project</h2>
          <p>Mwangaza was developed as an individual project for the IGAD Hackathon 2026 to explore how satellite observations can support drought early warning and anticipatory action.</p>
          <dl className="project-facts">
            <div><dt>Project</dt><dd>IGAD Hackathon 2026</dd></div>
            <div><dt>Team</dt><dd>Independent developer</dd></div>
            <div><dt>Development Period</dt><dd>29-day hackathon development cycle</dd></div>
            <div><dt>Purpose</dt><dd>Transform satellite observations into understandable drought-risk signals and actionable early-action recommendations.</dd></div>
          </dl>
        </section>
      </div>

      <div className="about-method-grid">
        <section className="about-panel">
          <h2>How Mwangaza Works</h2>
          <ol className="method-steps">
            <li><strong>Observe</strong><span>Retrieve NDVI, rainfall and land-surface temperature.</span></li>
            <li><strong>Compare</strong><span>Compare recent values with seasonal historical baselines.</span></li>
            <li><strong>Assess</strong><span>Generate anomalies, composite score, quality flags and drought level.</span></li>
            <li><strong>Act</strong><span>Surface alerts, recommendations and exportable reports.</span></li>
          </ol>
          <a className="text-link" href="/about/provenance">Data provenance and methodology</a>
        </section>

        <section className="about-panel">
          <h2>Pilot Coverage</h2>
          <ul className="action-list">
            <li>National view for configured IGAD countries.</li>
            <li>{pilotRegions.length ? `${pilotRegions.map((profile) => profile.name).join(", ")} include pilot-unit metadata.` : "Pilot subnational payloads are not available in this snapshot."}</li>
            <li>Additional subregions require approved geometry and aggregation contracts.</li>
          </ul>
        </section>

        <section className="about-panel">
          <h2>Version and System Status</h2>
          <dl className="system-status-list">
            <div><dt>App version</dt><dd>1.0.0 prototype</dd></div>
            <div><dt>Source mode</dt><dd>{data.dataMode}</dd></div>
            <div><dt>Current snapshot</dt><dd>{data.lastUpdated}</dd></div>
            <div><dt>Methodology version</dt><dd>dashboard-v1</dd></div>
            <div><dt>Forecast status</dt><dd>{data.forecastDiagnostics.available ? "Available" : data.forecastDiagnostics.message}</dd></div>
          </dl>
        </section>
      </div>

      <section className="about-limitations">
        <div>
          <h2>Limitations</h2>
          <p>Mwangaza is a decision-support prototype. Alerts are not official public warnings, satellite datasets can have delays or quality gaps, and estimates must be validated with local knowledge.</p>
        </div>
        <ul>
          <li>Composite scores depend on configurable thresholds.</li>
          <li>Land surface temperature is not air temperature.</li>
          <li>Exposure means potentially exposed, not confirmed affected population.</li>
          <li>Operational privacy, terms and contact pages are still pending.</li>
        </ul>
      </section>

      <footer className="about-footer">
        <p>(c) 2026 Mwangaza Project. Open-source license display pending.</p>
        <nav aria-label="About footer links">
          <a href="/about">Privacy Policy pending</a>
          <a href="/about">Terms of Use pending</a>
          <a href="/about">Contact pending</a>
        </nav>
      </footer>
    </section>
  );
}

function ProvenanceScreen(): JSX.Element {
  const sources = [
    ["MODIS/061/MOD13Q1", "NDVI", "index", "250 m / 16 days", "NASA Earthdata open data terms"],
    ["UCSB-CHG/CHIRPS/DAILY", "Rainfall", "mm", "0.05 degree / daily", "CHIRPS data terms"],
    ["MODIS/061/MOD11A2", "Land Surface Temperature", "deg C", "1 km / 8 days", "NASA Earthdata open data terms"],
    ["IGAD administrative catalog", "Administrative boundaries", "geometry", "versioned", "Pending verification"],
    ["Demo population grid", "Potential exposure", "people estimate", "1 km / 2024", "Synthetic demo"]
  ];
  return <section className="provenance-screen" aria-label="Data provenance and methodology">
    <p className="eyebrow">Responsible use</p><h2>Data provenance and methodology</h2>
    <p>Every source retains its variable, unit, resolution, frequency, terms, latency and limitations. Pending terms are not operational approval.</p>
    <table><thead><tr><th>Source</th><th>Indicator</th><th>Unit</th><th>Resolution / frequency</th><th>License or terms</th></tr></thead><tbody>{sources.map(row => <tr key={row[0]}>{row.map(value => <td key={value}>{value}</td>)}</tr>)}</tbody></table>
    <h2>Observation, anomaly, score, forecast and exposure</h2>
    <p>An observation describes a measured period. An anomaly compares it with a seasonal baseline. A score combines normalized anomalies using configurable, non-official prototype thresholds. A forecast estimates a future period. Exposure means potentially exposed population, not confirmed affected people.</p>
    <h2>Coverage and interpretation</h2><p>Clouds and QA masking reduce coverage; publication schedules create latency; aggregation can hide local variation. Live, cache and demo provenance remain explicit.</p>
    <h2>Data lineage</h2><div className="lineage-flow" aria-label="Data lineage">Source → Transformation and QA → Cache → API → UI → Report</div>
    <a className="text-link" href="/about">Back to About</a>
  </section>;
}

function AlertsCenter({ data, activeAlerts, requestedAlertId }: { data: DashboardData; activeAlerts: Alert[]; requestedAlertId?: string }): JSX.Element {
  const initialAlertParams = useMemo(() => new URLSearchParams(window.location.search), []);
  const [query, setQuery] = useState(initialAlertParams.get("q") ?? "");
  const [severityFilter, setSeverityFilter] = useState(initialAlertParams.get("severity") ?? "all");
  const [regionFilter, setRegionFilter] = useState(initialAlertParams.get("region") ?? "all");
  const [statusFilter, setStatusFilter] = useState(initialAlertParams.get("status") ?? "all");
  const [periodFilter, setPeriodFilter] = useState(initialAlertParams.get("period") ?? "all");
  const initialStatusTab = initialAlertParams.get("status");
  const [tab, setTab] = useState<"active" | "preventive" | "resolved" | "all">(initialStatusTab === "active" || initialStatusTab === "preventive" || initialStatusTab === "resolved" ? initialStatusTab : "active");
  const [selectedAlertKey, setSelectedAlertKey] = useState<string | null>(null);

  const alertRows = useMemo(() => data.alerts.map((alert) => ({
    alert,
    id: alertId(alert),
    region: data.regions.find((region) => region.id === alert.regionId),
    profile: data.profiles.find((profile) => profile.id === alert.regionId)
  })), [data.alerts, data.profiles, data.regions]);

  const filteredRows = alertRows.filter(({ alert }) => {
    const text = `${alert.region} ${alert.title} ${alert.action} ${alert.quality} ${alert.evidence.flat().join(" ")}`.toLowerCase();
    const matchesQuery = !query || text.includes(query.toLowerCase());
    const matchesSeverity = severityFilter === "all" || alert.severity === severityFilter;
    const matchesRegion = regionFilter === "all" || alert.regionId === regionFilter;
    const matchesStatus = statusFilter === "all" || alert.status === statusFilter;
    const matchesPeriod = periodFilter === "all" || alert.period === periodFilter;
    const matchesTab = tab === "all" || (tab === "active" && alert.status === "active") || (tab === "preventive" && alert.status === "preventive") || (tab === "resolved" && alert.status === "resolved");
    return matchesQuery && matchesSeverity && matchesRegion && matchesStatus && matchesPeriod && matchesTab;
  });
  const periods = Array.from(new Set(alertRows.map(({ alert }) => alert.period))).sort().reverse();
  const resolvedRows = alertRows.filter(({ alert }) => alert.status === "resolved" || alert.status === "superseded");
  const requestedRow = requestedAlertId ? alertRows.find((row) => row.id === requestedAlertId) : undefined;
  const selectedRow = requestedRow ?? filteredRows.find((row) => row.id === selectedAlertKey) ?? filteredRows[0] ?? alertRows[0];
  const selectedAlert = selectedRow?.alert;
  const selectedProfile = selectedRow?.profile ?? data.profiles.find((profile) => profile.id === data.selectedRegionId) ?? data.profiles[0];
  const selectedRegion = selectedRow?.region ?? data.regions.find((region) => region.id === selectedAlert?.regionId) ?? data.regions[0];
  const selectedMetrics = selectedProfile?.metrics.length ? selectedProfile.metrics.slice(0, 4) : data.metrics.slice(0, 4);
  const severeCount = activeAlerts.filter((alert) => alert.severity === "critical").length;
  const preventiveCount = data.alerts.filter((alert) => alert.status === "preventive").length;
  const resolvedCount = data.alerts.filter((alert) => alert.status === "resolved").length;
  const simulatedNotificationCount = data.alerts.reduce((total, alert) => total + (alert.notifications?.length ?? 0), 0);
  const filterParams = new URLSearchParams();
  if (query) filterParams.set("q", query);
  if (severityFilter !== "all") filterParams.set("severity", severityFilter);
  if (regionFilter !== "all") filterParams.set("region", regionFilter);
  if (statusFilter !== "all") filterParams.set("status", statusFilter);
  if (periodFilter !== "all") filterParams.set("period", periodFilter);
  const filterQuery = filterParams.toString();

  useEffect(() => {
    if (requestedAlertId) return;
    window.history.replaceState({}, "", `/alerts${filterQuery ? `?${filterQuery}` : ""}`);
  }, [filterQuery, requestedAlertId]);

  if (requestedAlertId && !requestedRow) {
    return <section className="alert-detail-page" aria-label="Alert not found"><p className="eyebrow">404</p><h2>Alert not found</h2><p>The requested alert is not present in the loaded snapshot.</p><a className="text-link" href="/alerts">Back to Alerts Center</a></section>;
  }

  if (requestedAlertId && selectedAlert && selectedProfile && selectedRegion) {
    return <AlertDetailPage alert={selectedAlert} alertIdValue={requestedAlertId} data={data} profile={selectedProfile} region={selectedRegion} />;
  }

  return (
    <section className="alerts-screen" aria-label="Alerts Center">
      <div className="alerts-header">
        <div>
          <h2>Alerts Center</h2>
          <p>Track active, preventive, and resolved drought alerts across IGAD</p>
        </div>
        <div className="alerts-header-actions">
          <a download href={`/api/v1/exports/alerts?${filterQuery ? `${filterQuery}&` : ""}format=csv`}>Export CSV</a>
          <a download href={`/api/v1/exports/alerts?${filterQuery ? `${filterQuery}&` : ""}format=json`}>Export JSON</a>
          <a download href={`/api/v1/reports/alerts${filterQuery ? `?${filterQuery}` : ""}`}>Export PDF</a>
          <button disabled type="button" title="Authentication and alert-setting permissions are not available">Alert settings unavailable</button>
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
          <option value="superseded">Superseded</option>
        </select>
        <select aria-label="Time period" onChange={(event) => setPeriodFilter(event.target.value)} value={periodFilter}>
          <option value="all">Period: All</option>
          {periods.map((period) => <option key={period} value={period}>{period}</option>)}
        </select>
      </div>

      <div className="alert-tabs" aria-label="Alert status tabs">
        {(["active", "preventive", "resolved", "all"] as const).map((item) => (
          <button data-active={tab === item ? "true" : "false"} key={item} onClick={() => { setTab(item); setStatusFilter(item); }} type="button">
            {item === "all" ? "All alerts" : item[0].toUpperCase() + item.slice(1)}
          </button>
        ))}
      </div>

      <dl className="alert-status-band" aria-label="Alert summary">
        <div><dt>Active</dt><dd>{activeAlerts.length}</dd></div>
        <div><dt>Severe</dt><dd>{severeCount}</dd></div>
        <div><dt>Preventive</dt><dd>{preventiveCount}</dd></div>
        <div><dt>Resolved</dt><dd>{resolvedCount}</dd></div>
        <div><dt>Simulated notifications</dt><dd>{simulatedNotificationCount}</dd></div>
      </dl>

      <div className="alerts-workspace">
        <section className="alerts-queue">
          <div className="section-heading">
            <h2>Alerts queue</h2>
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
                    <td>{alert.alertType ?? "Drought"}</td>
                    <td>{alert.title}</td>
                    <td>{alert.issuedAt ?? alert.period}</td>
                    <td>{alert.status}</td>
                    <td><button onClick={() => setSelectedAlertKey(id)} type="button">View</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-alert-filter"><Placeholder title="No alerts match filters" detail="Adjust search, severity, country, status or period." /><button onClick={() => { setQuery(""); setSeverityFilter("all"); setRegionFilter("all"); setStatusFilter("all"); setPeriodFilter("all"); setTab("all"); }} type="button">Clear filters</button></div>
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
                <div><dt>Issued</dt><dd>{selectedAlert.issuedAt ?? selectedAlert.period}</dd></div>
                <div><dt>Last updated</dt><dd>{selectedAlert.updatedAt ?? selectedRegion.period}</dd></div>
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
                <a href={`/region?country=${encodeURIComponent(selectedAlert.regionId)}`}>View full region analysis</a>
                <a href={`/api/v1/reports/alerts?q=${encodeURIComponent(selectedRow?.id ?? selectedAlert.id)}`}>Generate PDF report</a>
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
          {selectedAlert?.recommendations?.length ? <ol className="alert-recommendation-list">{selectedAlert.recommendations.map((item) => <li key={item.action}><strong>{item.action}</strong><span>{item.suggestedActor ?? "Actor pending"} · {item.urgency ?? "Priority pending"}{item.horizon ? ` · ${item.horizon}` : ""}</span><small>{item.recommendationVersion ?? "Catalog version pending"}</small></li>)}</ol> : <ul className="action-list">{(selectedProfile?.recommendations.length ? selectedProfile.recommendations : data.recommendations).map((item) => <li key={item}>{item}</li>)}</ul>}
        </section>
        <NotificationOutbox selectedAlert={selectedAlert} />
        <AlertLifecycle selectedAlert={selectedAlert} selectedRegion={selectedRegion} />
      </div>

      <section className="resolved-recent">
        <h2>Resolved & recent</h2>
        {resolvedRows.length ? <table><thead><tr><th>ID</th><th>Region</th><th>Status</th><th>Updated</th><th>Severity</th></tr></thead><tbody>{resolvedRows.map(({ alert, id }) => <tr key={id}><td><a href={`/alerts/${encodeURIComponent(id)}`}>{id}</a></td><td>{alert.region}</td><td>{alert.status}</td><td>{alert.resolvedAt ?? alert.updatedAt ?? alert.period}</td><td><span className="table-badge" data-severity={alert.severity}>{severityLabel(alert.severity)}</span></td></tr>)}</tbody></table> : <p className="muted">No resolved or superseded alerts are available in this repository.</p>}
      </section>
    </section>
  );
}

function AlertDetailPage({ alert, alertIdValue, data, profile, region }: { alert: Alert; alertIdValue: string; data: DashboardData; profile: RegionProfile; region: RegionRisk }): JSX.Element {
  const reportUrl = `/api/v1/reports/alerts?q=${encodeURIComponent(alertIdValue)}`;
  return (
    <section className="alert-detail-page" aria-label={`Alert ${alertIdValue}`}>
      <header>
        <div><p className="eyebrow">Active alert · {alertIdValue}</p><h2>{alert.region}</h2><p>{alert.title}</p></div>
        <span className="severity-badge" data-severity={alert.severity}>{severityLabel(alert.severity)}</span>
      </header>
      <div className="alert-detail-layout">
        <section>
          <h3>Decision context</h3>
          <p>{alertNarrative(alert, region)}</p>
          <dl className="alert-meta">
            <div><dt>Period</dt><dd>{alert.period}</dd></div>
            <div><dt>Data quality</dt><dd>{qualityLabel(alert.quality)}</dd></div>
            <div><dt>Source</dt><dd>{data.source}</dd></div>
          </dl>
          <h3>Evidence</h3>
          <table><thead><tr><th>Signal</th><th>Value</th></tr></thead><tbody>{alert.evidence.map(([label, value]) => <tr key={`${label}-${value}`}><td>{label}</td><td>{value}</td></tr>)}</tbody></table>
        </section>
        <aside>
          <h3>Current indicators</h3>
          <dl className="alert-indicator-list">{profile.metrics.slice(0, 6).map((metric) => <div key={metric.label}><dt>{metric.label}</dt><dd>{metric.value}{metric.unit}</dd></div>)}</dl>
          <div className="alert-primary-action"><span>Recommended next step</span><strong>{alert.action}</strong></div>
        </aside>
      </div>
      <div className="alerts-lower-grid alert-detail-support">
        <AlertLifecycle selectedAlert={alert} selectedRegion={region} />
        <NotificationOutbox selectedAlert={alert} />
      </div>
      <nav className="alert-detail-actions" aria-label="Alert actions">
        <a href={`/region?country=${encodeURIComponent(region.id)}`}>Open region analysis</a>
        <a href={reportUrl}>Download alert PDF</a>
        <a href={`/alerts?region=${encodeURIComponent(region.id)}&period=${encodeURIComponent(alert.period)}&status=${encodeURIComponent(alert.status)}`}>Back to filtered alerts</a>
      </nav>
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
  const rows = selectedAlert?.notifications ?? [];
  return (
    <section>
      <div className="section-heading">
        <h2>Notification outbox <span className="muted">(simulated)</span></h2>
        <span className="muted">No real messages are sent</span>
      </div>
      <table>
        <thead><tr><th>Channel</th><th>Message</th><th>Recipients</th><th>Status</th></tr></thead>
        <tbody>
          {rows.map((item) => (
            <tr key={item.id}>
              <td>{item.channel}</td>
              <td>{item.content}</td>
              <td>{item.recipientMasked}</td>
              <td><span className="simulation-badge">{item.isSimulated ? "Simulated" : "Blocked"}</span> {item.status}</td>
            </tr>
          ))}
          {!rows.length ? <tr><td colSpan={4}>No simulated notification payload is available for this alert.</td></tr> : null}
        </tbody>
      </table>
    </section>
  );
}

function AlertLifecycle({ selectedAlert, selectedRegion }: { selectedAlert?: Alert; selectedRegion: RegionRisk }): JSX.Element {
  const events = selectedAlert?.events ?? [];
  return (
    <section>
      <h2>Alert lifecycle</h2>
      <ol className="lifecycle-list">
        {events.length ? events.map((event, index) => <li key={`${event.eventType}-${event.createdAt}-${index}`}><strong>{event.eventType.replaceAll("_", " ")}</strong><span>{event.createdAt} · {event.status}{event.toSeverity ? ` · ${event.toSeverity}` : ""}</span></li>) : <li><strong>Lifecycle unavailable</strong><span>{selectedRegion.period}</span></li>}
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
  const [selectedPilotId, setSelectedPilotId] = useState("");
  const [selectedPeriod, setSelectedPeriod] = useState("");
  const [regionView, setRegionView] = useState<"national" | "pilot">("national");
  const [rankingOpen, setRankingOpen] = useState(false);
  const periodPayload = data.periods?.find((period) => period.key === selectedPeriod);
  const periodProfile = periodPayload?.profiles.find((profile) => profile.id === selectedRegion.id);
  const effectiveProfile = periodProfile ?? selectedProfile;
  const selectedAlerts = activeAlerts.filter((alert) => alert.regionId === selectedRegion.id);
  const primaryAlert = [...selectedAlerts].sort((left, right) => severityPriority(right.severity) - severityPriority(left.severity))[0];
  const displayMetrics = effectiveProfile.metrics.length ? effectiveProfile.metrics : data.metrics;
  const ndvi = metricByLabel(displayMetrics, "NDVI");
  const rainfall = metricByLabel(displayMetrics, "Rainfall");
  const lst = metricByLabel(displayMetrics, "LST");
  const composite = metricByLabel(displayMetrics, "Composite");
  const exposure = metricByLabel(displayMetrics, "potentially_exposed");
  const indicatorMetrics = [ndvi, rainfall, lst, composite, exposure].filter((metric): metric is Metric => Boolean(metric));
  const administrativeRows = (effectiveProfile.administrativeUnits ?? []).map((unit) => ({
    id: unit.regionId,
    name: unit.name,
    adminLevel: unit.adminLevel,
    score: unit.score,
    level: unit.level,
    quality: unit.quality,
    rank: unit.rank
  }));
  const rankedPilotRows = [...(administrativeRows.length ? administrativeRows : (effectiveProfile.pilotRows ?? []))].sort((left, right) =>
    left.score === null ? 1 : right.score === null ? -1 : right.score - left.score || left.name.localeCompare(right.name)
  );
  const availablePeriods = data.periods ?? [];
  const selectedPilot = rankedPilotRows.find((unit) => unit.id === selectedPilotId);
  const selectedAdministrativeUnit = effectiveProfile.administrativeUnits?.find(
    (unit) => unit.regionId === selectedPilotId
  );
  const activeContributions = selectedPilotId
    ? (selectedAdministrativeUnit?.contributions ?? [])
    : (effectiveProfile.contributions ?? []);
  const contributionScope = selectedAdministrativeUnit?.name ?? selectedPilot?.name ?? countryDisplayName(selectedRegion);
  const contributionCompositeScore = selectedAdministrativeUnit?.score ?? selectedPilot?.score ?? selectedRegion.score;
  const rankingUnitLabel = administrativeRows.length ? "ADM1 areas" : "subnational areas";
  const selectSubregion = (unitId: string): void => {
    setSelectedPilotId(unitId);
    setRegionView(unitId ? "pilot" : "national");
  };
  useEffect(() => {
    setSelectedPilotId("");
    setSelectedPeriod("");
    setRegionView("national");
    setRankingOpen(false);
  }, [selectedRegion.id]);
  const alertsHref = `/alerts?${new URLSearchParams({ region: selectedRegion.id, period: selectedRegion.period, status: "active" })}`;

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
                <option key={region.id} value={region.id}>{countryDisplayName(region)}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Subregion / District</span>
            <select disabled={!rankedPilotRows.length} value={selectedPilotId} onChange={(event) => selectSubregion(event.target.value)}>
              <option value="">{rankedPilotRows.length ? "All administrative areas" : "Subnational unavailable"}</option>
              {rankedPilotRows.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
            </select>
          </label>
          <label>
            <span>Time period</span>
            <select disabled={!availablePeriods.length} value={selectedPeriod} onChange={(event) => setSelectedPeriod(event.target.value)}>
              <option value="">{selectedRegion.period}</option>
              {availablePeriods.map((period) => <option key={period.key} value={period.key}>{period.label}</option>)}
            </select>
          </label>
          <div className="segmented" aria-label="View">
            <button type="button" data-active={regionView === "national"} onClick={() => selectSubregion("")}>National view</button>
            <button type="button" data-active={regionView === "pilot"} disabled={!rankedPilotRows.length} onClick={() => selectSubregion(selectedPilotId || rankedPilotRows[0]?.id || "")}>Subnational view</button>
          </div>
        </div>
      </div>

      {selectedRegion.id === "ken" && data.dataMode === "demo" ? <NorthernKenyaScenario /> : null}

      <div className="region-main-grid region-atlas-workspace">
        <RegionRiskSurface
          onSelectUnit={selectSubregion}
          profile={effectiveProfile}
          selectedRegion={selectedRegion}
          selectedUnitId={selectedPilotId}
        />
        <aside className="territory-inspector" key={selectedPilotId || selectedRegion.id} aria-live="polite">
          <header>
            <div>
              <p className="eyebrow">{selectedAdministrativeUnit ? "Selected ADM1" : selectedPilot ? "Selected pilot area" : "Country overview"}</p>
              <h2>{selectedAdministrativeUnit?.name ?? selectedPilot?.name ?? countryDisplayName(selectedRegion)}</h2>
              <p>{selectedAdministrativeUnit?.boundaryIso ?? (selectedPilot ? selectedPilot.adminLevel : "National observation")}</p>
            </div>
            <span className="severity-badge" data-severity={selectedAdministrativeUnit?.level ?? selectedPilot?.level ?? selectedRegion.level}>
              {severityLabel(selectedAdministrativeUnit?.level ?? selectedPilot?.level ?? selectedRegion.level)}
            </span>
          </header>
          <div className="inspector-score">
            <span>Composite score</span>
            <strong>{formatScoreValue(selectedAdministrativeUnit?.score ?? selectedPilot?.score ?? selectedRegion.score)}</strong>
            <small>/100</small>
          </div>
          {selectedAdministrativeUnit ? (
            <>
              <dl className="inspector-metrics">
                <div><dt>NDVI</dt><dd>{formatMapMetric(selectedAdministrativeUnit.ndvi)}</dd></div>
                <div><dt>Rainfall</dt><dd>{formatMapMetric(selectedAdministrativeUnit.rainfallMm, " mm")}</dd></div>
                <div><dt>LST</dt><dd>{formatMapMetric(selectedAdministrativeUnit.lstC, " °C")}</dd></div>
              </dl>
              <dl className="inspector-provenance">
                <div><dt>Data quality</dt><dd><span className="signal-badge" data-quality={selectedAdministrativeUnit.quality}>{qualityLabel(selectedAdministrativeUnit.quality)}</span></dd></div>
                <div><dt>Period</dt><dd>{formatPeriodLabel(selectedAdministrativeUnit.periodEnd)}</dd></div>
                <div><dt>Source</dt><dd>{selectedAdministrativeUnit.sourceMode.toUpperCase()}</dd></div>
              </dl>
            </>
          ) : (
            <dl className="inspector-provenance">
              <div><dt>Coverage</dt><dd>{effectiveProfile.administrativeUnits?.length ? `${effectiveProfile.administrativeUnits.length} ADM1 areas` : "National only"}</dd></div>
              <div><dt>Potentially exposed population</dt><dd>{exposure?.value ?? "No data"} {exposure?.unit ?? ""}</dd></div>
              <div><dt>Data quality</dt><dd><span className="signal-badge" data-quality={selectedRegion.quality}>{qualityLabel(selectedRegion.quality)}</span></dd></div>
              <div><dt>Period</dt><dd>{selectedRegion.period}</dd></div>
            </dl>
          )}
          <section className="inspector-action">
            <span>{primaryAlert ? "Highest-priority active alert" : selectedAdministrativeUnit ? "Country guidance for this area" : "Recommended next step"}</span>
            <strong>{primaryAlert?.action ?? effectiveProfile.recommendations[0] ?? "Review the current evidence before operational action."}</strong>
            <a href={alertsHref}>View all alerts</a>
          </section>
          {selectedPilotId ? <button className="inspector-clear" type="button" onClick={() => selectSubregion("")}>Return to national view</button> : null}
        </aside>
      </div>

      <section className="ranking-drawer" data-open={rankingOpen ? "true" : "false"}>
        <button className="ranking-toggle" type="button" aria-controls="subnational-ranking-table" aria-expanded={rankingOpen} onClick={() => setRankingOpen((open) => !open)}>
          <span><strong>Subnational ranking</strong><small>{rankedPilotRows.length} {rankingUnitLabel} · select a row to inspect it on the map</small></span>
          <span aria-hidden="true">{rankingOpen ? "−" : "+"}</span>
        </button>
        {rankingOpen ? (
          <div className="ranking-scroll" id="subnational-ranking-table">
            <table>
              <thead><tr><th>#</th><th>District / Area</th><th>Alert level</th><th>Composite score</th><th>Data quality</th></tr></thead>
              <tbody>
                {rankedPilotRows.map((unit, index) => (
                  <tr key={unit.id} data-selected={unit.id === selectedPilotId ? "true" : "false"} data-top-rank={index < 3 ? "true" : "false"}>
                    <td><span className="rank-marker" data-top={index < 3 ? "true" : "false"}>{index + 1}</span></td>
                    <td><button className="ranking-select" type="button" onClick={() => selectSubregion(unit.id)}>{unit.name}</button></td>
                    <td><span className="signal-badge" data-severity={unit.level}>{severityLabel(unit.level)}</span></td>
                    <td>{unit.score === null ? "No data" : formatScoreValue(unit.score)}</td>
                    <td><span className="signal-badge" data-quality={unit.quality}>{qualityLabel(unit.quality)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

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
          <h2>Why this region is at risk <span className="info-dot" title="Contributions reported by the composite-risk payload.">i</span></h2>
          {activeContributions.length
            ? <ContributionStack compositeScore={contributionCompositeScore} contributions={activeContributions} scope={contributionScope} />
            : <Placeholder title="Contribution payload pending" detail={`The API has not provided an attributable composite-score breakdown for ${contributionScope}.`} />}
        </section>

        <TrendPanel title={selectedAdministrativeUnit ? `Country trends · ${countryDisplayName(selectedRegion)}` : "Indicator Trends"} trends={effectiveProfile.trends} />
      </div>

      <div className="region-lower-grid region-final-grid">
        <section>
          <h2>Historical comparison</h2>
          {effectiveProfile.historicalRows.length ? (
            <HistoricalComparison rows={effectiveProfile.historicalRows} />
          ) : (
            <Placeholder title="Historical comparison pending" detail="Comparable historical rows are not available for this live region payload yet." />
          )}
        </section>
        <section id="about" className="pilot-note">
          <h2>About administrative coverage</h2>
          <p>Live analysis covers every first-level administrative area in the enabled IGAD countries. Units without conclusive source data remain explicitly unassessed.</p>
          <small className="coverage-note">Methodology documentation will be linked when published.</small>
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
  if (params.get("demo") === "1") {
    return false;
  }
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
  onSelectUnit,
  profile,
  selectedRegion,
  selectedUnitId
}: {
  onSelectUnit: (unitId: string) => void;
  profile: RegionProfile;
  selectedRegion: RegionRisk;
  selectedUnitId: string;
}): JSX.Element {
  const [administrativeMap, setAdministrativeMap] = useState<AdministrativeFeatureCollection | null>(null);
  const [mapState, setMapState] = useState<"loading" | "ready" | "unavailable">("loading");
  const [activeUnit, setActiveUnit] = useState<AdministrativeFeature | null>(null);
  const boundaryAsset = ADMIN_BOUNDARY_ASSETS[selectedRegion.id];
  const measuredUnits = useMemo(() => new Map<string, AdministrativeUnit>(
    (profile.administrativeUnits ?? []).map((unit) => [unit.boundaryIso, unit])
  ), [profile.administrativeUnits]);

  useEffect(() => {
    const controller = new AbortController();
    setAdministrativeMap(null);
    setActiveUnit(null);
    if (!boundaryAsset) {
      setMapState("unavailable");
      return () => controller.abort();
    }
    setMapState("loading");
    void fetch(boundaryAsset, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`Boundary asset returned ${response.status}`);
        return response.json() as Promise<AdministrativeFeatureCollection>;
      })
      .then((collection) => {
        setAdministrativeMap(normalizeAdministrativeRings(collection));
        setMapState("ready");
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) setMapState("unavailable");
      });
    return () => controller.abort();
  }, [boundaryAsset]);

  const mapView = ADMIN_MAP_VIEWS[selectedRegion.id] ?? ADMIN_MAP_VIEWS.som;
  const activeMeasurement = activeUnit ? measuredUnits.get(activeUnit.properties.shapeISO) : undefined;
  return (
    <section className="region-map-panel">
      <div className="region-map-heading">
        <div>
          <p className="eyebrow">Administrative atlas</p>
          <h2>{countryDisplayName(selectedRegion)}</h2>
          <p>First-level boundaries · national drought observation</p>
        </div>
        <div className="region-map-score" data-severity={selectedRegion.level}>
          <span>National score</span>
          <strong>{formatScoreValue(selectedRegion.score)}</strong>
          <small>{severityLabel(selectedRegion.level)}</small>
        </div>
      </div>
      <div className="region-map-stage" aria-label="Regions map">
        {mapState === "ready" && administrativeMap ? (
          <ComposableMap
            projection="geoMercator"
            projectionConfig={{ center: mapView.center, scale: mapView.scale }}
            width={820}
            height={500}
            className="region-svg-map"
          >
            <Geographies geography={administrativeMap}>
              {({ geographies }) => geographies.map((geo) => {
                const feature = geo as unknown as AdministrativeFeature & { rsmKey: string };
                const unit = measuredUnits.get(feature.properties.shapeISO);
                const selected = unit?.regionId === selectedUnitId;
                return (
                  <Geography
                    aria-label={`${feature.properties.shapeName}: ${unit ? `${unit.score ?? "No data"} ${unit.level}` : "not individually assessed"}`}
                    aria-current={selected ? "true" : undefined}
                    geography={geo}
                    key={geo.rsmKey}
                    onBlur={() => setActiveUnit(null)}
                    onClick={() => { if (unit) onSelectUnit(unit.regionId); }}
                    onFocus={() => setActiveUnit(feature)}
                    onKeyDown={(event) => {
                      if (unit && (event.key === "Enter" || event.key === " ")) {
                        event.preventDefault();
                        onSelectUnit(unit.regionId);
                      }
                    }}
                    onMouseEnter={() => setActiveUnit(feature)}
                    onMouseLeave={() => setActiveUnit(null)}
                    style={{
                      default: {
                        fill: unit ? mapFill(unit.level) : "#dce5dc",
                        stroke: selected ? "#173f31" : "#ffffff",
                        strokeWidth: selected ? 3 : 1.15,
                        outline: "none"
                      },
                      hover: { fill: unit ? mapHoverFill(unit.level) : "#bdcdbf", stroke: "#173f31", strokeWidth: 2.2, outline: "none" },
                      pressed: { fill: unit ? mapHoverFill(unit.level) : "#afc2b2", outline: "none" }
                    }}
                    role={unit ? "button" : undefined}
                    tabIndex={unit ? 0 : -1}
                  />
                );
              })}
            </Geographies>
          </ComposableMap>
        ) : mapState === "loading" ? (
          <div aria-live="polite" className="map-loading"><span />Loading administrative boundaries…</div>
        ) : (
          <Placeholder title="Administrative boundaries unavailable" detail="A validated local boundary asset is not available for this country yet. No synthetic geometry is shown." />
        )}
        {activeUnit ? (
          <div className="map-tooltip" role="status">
            <span>{activeUnit.properties.shapeISO}</span>
            <strong>{activeUnit.properties.shapeName}</strong>
            {activeMeasurement ? <div className="map-tooltip-badges"><span className="signal-badge" data-severity={activeMeasurement.level}>{severityLabel(activeMeasurement.level)}</span><span className="signal-badge" data-quality={activeMeasurement.quality}>{qualityLabel(activeMeasurement.quality)}</span><b>{formatScoreValue(activeMeasurement.score)}</b></div> : <small>Not individually assessed</small>}
            {activeMeasurement ? <em>NDVI {formatMapMetric(activeMeasurement.ndvi)} · Rain {formatMapMetric(activeMeasurement.rainfallMm, " mm")}</em> : null}
          </div>
        ) : null}
        <div className="map-scale-note">ADM1 · locally cached</div>
      </div>
      <div className="region-map-footer">
        <div className="map-legend" aria-label="Risk legend">
          <span data-severity="normal">Low</span>
          <span data-severity="watch">Watch</span>
          <span data-severity="warning">Alert</span>
          <span data-severity="critical">Severe</span>
          <span data-severity="unknown">Not assessed</span>
        </div>
        <p>Boundaries: geoBoundaries gbOpen · ADM1 · pinned source revision</p>
      </div>
      <p className="map-integrity-note"><strong>Coverage note.</strong> The score shown above is national. Administrative units stay neutral unless the API supplies a unit-specific observation.</p>
    </section>
  );
}

function ContributionStack({
  compositeScore,
  contributions,
  scope
}: {
  compositeScore: number | null;
  contributions: NonNullable<RegionProfile["contributions"]>;
  scope: string;
}): JSX.Element {
  const explained = contributions.map((item) => ({
    ...item,
    points: Math.max(0, item.weightedContribution ?? ((item.weight ?? 0) * (item.score ?? 0)))
  }));
  const total = explained.reduce((sum, item) => sum + item.points, 0);
  return (
    <div className="contribution-stack" aria-label={`Composite score contributions for ${scope}`}>
      <div className="contribution-summary">
        <span>{scope}</span>
        <strong>{formatScoreValue(total)} <small>of {formatScoreValue(compositeScore)} points explained</small></strong>
      </div>
      <div className="contribution-stack-bar" role="img" aria-label={explained.map((item) => `${indicatorLabel(item.indicator)} ${formatScoreValue(item.points)} points`).join(", ")}>
        {explained.map((item, index) => (
          <span
            data-contribution={index + 1}
            key={item.indicator}
            style={{ width: `${(item.points / (total || 1)) * 100}%` }}
            title={`${indicatorLabel(item.indicator)}: ${formatScoreValue(item.points)} composite points`}
          />
        ))}
      </div>
      <ul className="contribution-legend">
        {explained.map((item, index) => (
          <li key={item.indicator}>
            <i data-contribution={index + 1} />
            <span><b>{indicatorLabel(item.indicator)}</b><small>{formatScoreValue(item.score)} signal × {Math.round((item.weight ?? 0) * 100)}% weight · {item.source || "Source unavailable"}</small></span>
            <span className="contribution-result"><strong>{formatScoreValue(item.points)} pts</strong><span className="signal-badge" data-quality={item.quality}>{qualityLabel(item.quality)}</span></span>
          </li>
        ))}
      </ul>
      <p className="contribution-formula">Composite contribution = normalized signal score × effective model weight.</p>
    </div>
  );
}

function HistoricalComparison({ rows }: { rows: HistoricalRow[] }): JSX.Element {
  const grouped = rows.reduce<Record<string, HistoricalRow[]>>((groups, row) => {
    const parsed = new Date(row.period);
    const year = Number.isNaN(parsed.getTime()) ? row.period.slice(0, 4) || "Other" : String(parsed.getUTCFullYear());
    (groups[year] ??= []).push(row);
    return groups;
  }, {});
  return (
    <table className="history-table">
      <thead><tr><th>Indicator</th><th>Current</th><th>Baseline</th><th>Delta</th></tr></thead>
      {Object.entries(grouped).sort(([left], [right]) => right.localeCompare(left)).map(([year, yearRows]) => (
        <tbody key={year} className="history-year-group">
          <tr className="history-year"><th colSpan={4} scope="rowgroup">{year}</th></tr>
          {yearRows.map((row) => (
            <tr key={`${row.period}-${row.indicator}`}>
              <th scope="row"><strong>{row.indicator}</strong><small>{formatPeriodWithoutYear(row.period)}</small></th>
              <td>{formatMeasuredValue(row.current)}</td>
              <td>{formatMeasuredValue(row.historical)}</td>
              <td><span className="delta-badge" data-direction={deltaDirection(row.difference)}>{formatMeasuredValue(row.difference)}</span></td>
            </tr>
          ))}
        </tbody>
      ))}
    </table>
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

interface AdministrativeFeature {
  type: "Feature";
  properties: { shapeName: string; shapeISO: string; shapeID: string };
  geometry: GeoJsonGeometry;
}

interface AdministrativeFeatureCollection {
  type: "FeatureCollection";
  features: AdministrativeFeature[];
}

interface RiskFeature {
  type: "Feature";
  properties: { region: RegionRisk; boundaryName: string; interactiveAnchor: boolean };
  geometry: GeoJsonGeometry;
}

interface RiskFeatureCollection {
  type: "FeatureCollection";
  features: RiskFeature[];
}

const ADMIN_BOUNDARY_ASSETS: Record<string, string> = {
  dji: "/maps/DJI-ADM1.geojson",
  eri: "/maps/ERI-ADM1.geojson",
  eth: "/maps/ETH-ADM1.geojson",
  ken: "/maps/KEN-ADM1.geojson",
  sdn: "/maps/SDN-ADM1.geojson",
  som: "/maps/SOM-ADM1.geojson",
  ssd: "/maps/SSD-ADM1.geojson",
  uga: "/maps/UGA-ADM1.geojson"
};

const ADMIN_MAP_VIEWS: Record<string, { center: [number, number]; scale: number }> = {
  dji: { center: [42.55, 11.75], scale: 8200 },
  eri: { center: [39.7, 15.2], scale: 2500 },
  eth: { center: [40.4, 8.9], scale: 1450 },
  ken: { center: [37.75, 0.35], scale: 2150 },
  sdn: { center: [30.2, 15.4], scale: 1350 },
  som: { center: [46.1, 5.45], scale: 1800 },
  ssd: { center: [30.4, 7.7], scale: 1800 },
  uga: { center: [32.35, 1.35], scale: 3200 }
};

function formatMapMetric(value: number | null, suffix = ""): string {
  return value === null ? "—" : `${value.toLocaleString("en-GB", { maximumFractionDigits: 2 })}${suffix}`;
}

function formatPeriodLabel(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });
}

function formatPeriodWithoutYear(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", timeZone: "UTC" });
}

function formatTrendPeriod(value: string): string {
  const candidate = value.split(" to ").at(-1) ?? value;
  if (!/^\d{4}-\d{2}-\d{2}/.test(candidate)) return value;
  const date = new Date(candidate);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("en-GB", { month: "short", year: "2-digit", timeZone: "UTC" });
}

function formatMeasuredValue(value: string): string {
  const match = value.match(/^([+-]?\d+(?:\.\d+)?)(.*)$/);
  if (!match) return value;
  const number = Number(match[1]);
  const prefix = match[1].startsWith("+") && number > 0 ? "+" : "";
  return `${prefix}${number.toLocaleString("en-GB", { maximumFractionDigits: 2 })}${match[2]}`;
}

function deltaDirection(value: string): "positive" | "negative" | "neutral" {
  const number = Number.parseFloat(value);
  return number > 0 ? "positive" : number < 0 ? "negative" : "neutral";
}

function formatScoreValue(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("en-GB", { maximumFractionDigits: 1 });
}

function countryDisplayName(region: RegionRisk): string {
  const countries: Record<string, string> = {
    dji: "Djibouti",
    eri: "Eritrea",
    eth: "Ethiopia",
    ken: "Kenya",
    sdn: "Sudan",
    som: "Somalia",
    ssd: "South Sudan",
    uga: "Uganda"
  };
  return countries[region.id] ?? region.name;
}

function normalizeAdministrativeRings(collection: AdministrativeFeatureCollection): AdministrativeFeatureCollection {
  const signedArea = (ring: number[][]): number => ring.slice(0, -1).reduce(
    (area, point, index) => area + point[0] * ring[index + 1][1] - ring[index + 1][0] * point[1],
    0
  ) / 2;
  const normalizePolygon = (polygon: number[][][]): number[][][] => polygon.map((ring, index) => {
    const area = signedArea(ring);
    const shouldReverse = index === 0 ? area > 0 : area < 0;
    return shouldReverse ? [...ring].reverse() : ring;
  });
  return {
    ...collection,
    features: collection.features.map((feature) => ({
      ...feature,
      geometry: feature.geometry.type === "Polygon"
        ? { ...feature.geometry, coordinates: normalizePolygon(feature.geometry.coordinates as number[][][]) }
        : { ...feature.geometry, coordinates: (feature.geometry.coordinates as number[][][][]).map(normalizePolygon) }
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

function qualityMapFill(quality: string): string {
  if (quality === "ok" || quality === "normal") return "#247a53";
  if (quality === "degraded" || quality === "watch") return "#d5a72f";
  return "#c4c9d1";
}

function metricByLabel(metrics: Metric[], label: string): Metric | undefined {
  return metrics.find((metric) => metric.label.toLowerCase().includes(label.toLowerCase()));
}

function comparisonForMetric(metric: Metric, rows: HistoricalRow[]): string | null {
  const label = metric.label.toLowerCase();
  const indicator = label.includes("ndvi") ? "ndvi" : label.includes("rainfall") ? "rainfall" : label.includes("lst") || label.includes("temperature") ? "lst" : "";
  if (!indicator) return null;
  const row = rows.find((item) => item.indicator.toLowerCase().includes(indicator));
  if (!row) return null;
  const year = row.period.match(/\d{4}/)?.[0];
  return `${formatMeasuredValue(row.difference)}${year ? ` vs ${year}` : ""}`;
}

function indicatorLabel(indicator: string): string {
  return ({ ndvi: "NDVI anomaly", rainfall_mm: "Rainfall anomaly", lst_c: "Temperature anomaly" } as Record<string, string>)[indicator] ?? indicator;
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

function severityPriority(severity: Severity): number {
  return ({ unknown: 0, normal: 1, watch: 2, warning: 3, critical: 4 } as Record<Severity, number>)[severity];
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

function localizedSeverity(language: Language, severity: Severity): string {
  const keys: Record<Severity, "low" | "watch" | "alert" | "severe" | "notAssessed"> = {
    normal: "low", watch: "watch", warning: "alert", critical: "severe", unknown: "notAssessed"
  };
  return t(language, keys[severity]);
}

function localizedQuality(language: Language, value: string): string {
  const quality = qualityLabel(value);
  if (quality === "High") return t(language, "high");
  if (quality === "Medium") return t(language, "medium");
  if (quality === "Insufficient") return t(language, "insufficient");
  return quality;
}

function alertId(alert: Alert): string {
  if (alert.id) return alert.id;
  const stable = `${alert.title}-${alert.period}`.replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 24).toUpperCase();
  return `ALT-${alert.regionId.toUpperCase()}-${stable || "ALERT"}`;
}

function downloadUrl(path: string, regionId: string, period: string, format?: "csv" | "json"): string {
  const query = new URLSearchParams({ region: regionId, period });
  if (format) query.set("format", format);
  return `${path}?${query.toString()}`;
}

function alertNarrative(alert: Alert, region: RegionRisk): string {
  const score = region.score === null ? "no published composite score" : `a composite score of ${region.score}`;
  return `${alert.region} is classified as ${severityLabel(alert.severity).toLowerCase()} for ${alert.period}, with ${score}. ${alert.title}. Recommendations are decision support and should be validated with local knowledge.`;
}

function OverviewRiskMap({
  data,
  language,
  selectedRegion,
  onSelectRegion
}: {
  data: DashboardData;
  language: Language;
  selectedRegion: RegionRisk;
  onSelectRegion: (id: string) => void;
}): JSX.Element {
  const [geography, setGeography] = useState<RiskFeatureCollection | null>(null);
  const [geometryError, setGeometryError] = useState(false);
  const [layer, setLayer] = useState<"risk" | "quality">("risk");
  const [hoveredRegionId, setHoveredRegionId] = useState(selectedRegion.id);
  const [mapZoom, setMapZoom] = useState(1);
  const tooltipRegion = data.regions.find((region) => region.id === hoveredRegionId) ?? selectedRegion;
  const tooltipProfile = data.profiles.find((profile) => profile.id === tooltipRegion.id);
  const setZoom = (zoom: number): void => setMapZoom(Math.max(1, Math.min(4, zoom)));
  const resetMap = (): void => setMapZoom(1);

  useEffect(() => {
    let active = true;
    setGeometryError(false);
    void import("./maps/overviewBoundaries")
      .then(({ buildOverviewRiskFeatures }) => {
        if (active) setGeography(buildOverviewRiskFeatures(data.regions, selectedRegion.period));
      })
      .catch(() => {
        if (active) {
          setGeography(null);
          setGeometryError(true);
        }
      });
    return () => { active = false; };
  }, [data.regions, selectedRegion.period]);

  const hasGeometry = Boolean(geography?.features.length);

  return (
    <section className="overview-map-panel">
      <div className="section-heading">
        <div><p className="eyebrow">{t(language, "igadSituation")}</p><h2>{t(language, "riskMap")}</h2></div>
        <span className="info-dot" title={t(language, "riskMapHelp")}>i</span>
      </div>
      <div className="overview-map-stage" aria-label={t(language, "overviewRiskMap")}>
        {hasGeometry ? (
          <ComposableMap
            projection="geoMercator"
            projectionConfig={{ center: [38, 8], scale: 760 }}
            width={760}
            height={360}
            className="region-svg-map"
          >
            <g transform={`translate(${380 * (1 - mapZoom)} ${180 * (1 - mapZoom)}) scale(${mapZoom})`}>
              <Geographies geography={geography as RiskFeatureCollection}>
                {({ geographies }) => geographies.map((geo) => {
                  const region = geo.properties.region as RegionRisk;
                  const regionIsAvailable = data.regions.some((item) => item.id === region.id);
                  const interactiveAnchor = Boolean(geo.properties.interactiveAnchor) && regionIsAvailable;
                  const fill = layer === "risk" ? mapFill(region.level) : qualityMapFill(region.quality);
                  const hoverFill = layer === "risk" ? mapHoverFill(region.level) : fill;
                  return (
                    <Geography
                      aria-hidden={!interactiveAnchor}
                      aria-label={interactiveAnchor ? `${region.name}: ${region.score ?? t(language, "noData")}, ${localizedSeverity(language, region.level)}, ${t(language, "quality")} ${localizedQuality(language, region.quality)}` : undefined}
                      data-country={region.id}
                      geography={geo}
                      key={geo.rsmKey}
                      onBlur={() => setHoveredRegionId(selectedRegion.id)}
                      onClick={() => { if (regionIsAvailable) onSelectRegion(region.id); }}
                      onFocus={() => setHoveredRegionId(region.id)}
                      onKeyDown={(event) => { if (regionIsAvailable && (event.key === "Enter" || event.key === " ")) onSelectRegion(region.id); }}
                      onMouseEnter={() => setHoveredRegionId(region.id)}
                      onMouseLeave={() => setHoveredRegionId(selectedRegion.id)}
                      role={interactiveAnchor ? "button" : undefined}
                      style={{
                        default: {
                          fill,
                          stroke: region.id === selectedRegion.id ? "#163f31" : "#ffffff",
                          strokeWidth: region.id === selectedRegion.id ? 1.25 : 0.65,
                          outline: "none"
                        },
                        hover: { fill: hoverFill, outline: "none" },
                        pressed: { fill: hoverFill, outline: "none" }
                      }}
                      tabIndex={interactiveAnchor ? 0 : -1}
                    />
                  );
                })}
              </Geographies>
            </g>
          </ComposableMap>
        ) : (
          <Placeholder
            title={geometryError ? t(language, "atlasUnavailable") : t(language, "atlasLoading")}
            detail={geometryError ? t(language, "atlasError") : t(language, "atlasPreparing")}
          />
        )}
        {hasGeometry ? <div className="overview-map-tooltip" aria-live="polite">
          <span>{layer === "risk" ? t(language, "risk") : t(language, "dataQuality")}</span>
          <strong>{tooltipRegion.name}</strong>
          <b>{tooltipRegion.score ?? t(language, "noData")}{tooltipRegion.score === null ? "" : "/100"} · {localizedSeverity(language, tooltipRegion.level)}</b>
          <small>{localizedQuality(language, tooltipRegion.quality)} {t(language, "quality")} · {tooltipRegion.period}</small>
          <small>{tooltipProfile?.metrics.slice(0, 3).map((metric) => `${metric.label}: ${metric.value}${metric.unit}`).join(" · ") || t(language, "indicatorsUnavailable")}</small>
          <em>{data.source}</em>
        </div> : null}
        <div className="map-controls" aria-label={t(language, "mapControls")}>
          <button aria-label={t(language, "home")} onClick={resetMap} type="button" title={t(language, "home")}>⌂</button>
          <button aria-label={t(language, "zoomIn")} disabled={mapZoom >= 4} onClick={() => setZoom(mapZoom + 0.5)} type="button">+</button>
          <button aria-label={t(language, "zoomOut")} disabled={mapZoom <= 1} onClick={() => setZoom(mapZoom - 0.5)} type="button">−</button>
          <label><span>{t(language, "layer")}</span><select aria-label={t(language, "layer")} onChange={(event) => setLayer(event.target.value as "risk" | "quality")} value={layer}><option value="risk">{t(language, "risk")}</option><option value="quality">{t(language, "dataQuality")}</option></select></label>
        </div>
      </div>
      <p className="overview-map-attribution">{t(language, "boundaryAttribution")}</p>
      <div className="map-legend" aria-label={`${layer} legend`}>
        {layer === "risk" ? <><span data-severity="normal">{t(language, "low")}</span><span data-severity="watch">{t(language, "watch")}</span><span data-severity="warning">{t(language, "alert")}</span><span data-severity="critical">{t(language, "severe")}</span><span data-severity="unknown">{t(language, "notAssessed")}</span></> : <><span data-quality="ok">{t(language, "high")}</span><span data-quality="degraded">{t(language, "medium")}</span><span data-quality="unknown">{t(language, "insufficient")}</span></>}
      </div>
      <p className="muted">{layer === "risk" ? t(language, "riskMapHelp") : t(language, "qualityMapHelp")}</p>
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
  const alertsUrl = `/alerts?region=${encodeURIComponent(selectedRegion.id)}&period=${encodeURIComponent(selectedRegion.period)}&status=active`;
  const reportUrl = downloadUrl("/api/v1/reports/executive", selectedRegion.id, selectedRegion.period);
  const csvUrl = downloadUrl("/api/v1/exports/snapshot", selectedRegion.id, selectedRegion.period, "csv");
  const jsonUrl = downloadUrl("/api/v1/exports/snapshot", selectedRegion.id, selectedRegion.period, "json");
  const availableRegionIds = new Set(data.regions.map((region) => region.id));
  const regionalRegions = IGAD_COUNTRIES.map(({ id, name }) => data.regions.find((region) => region.id === id) ?? {
    id,
    name,
    score: null,
    level: "unknown" as Severity,
    quality: "unknown",
    period: selectedRegion.period
  }).sort((left, right) => severityRank[right.level] - severityRank[left.level] || left.name.localeCompare(right.name));
  const assessedRegionCount = regionalRegions.filter((region) => region.score !== null && region.level !== "unknown").length;

  return (
    <section className="overview-screen" aria-label={t(language, "overview")}>
      <div className="overview-top-grid">
        <OverviewRiskMap data={data} language={language} selectedRegion={selectedRegion} onSelectRegion={onSelectRegion} />
        <section className="overview-alerts">
          <div className="section-heading">
            <div><p className="eyebrow">{t(language, "priorityQueue")}</p><h2>{t(language, "activeAlerts")}</h2></div>
            <a className="text-link" href={alertsUrl}>{t(language, "viewAllAlerts")}</a>
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
                <a href={`/alerts/${encodeURIComponent(alertId(alert))}`}>{t(language, "viewDetails")}</a>
              </article>
            )) : (
              <Placeholder title={t(language, "noActiveAlerts")} detail={t(language, "noActiveAlertsDetail")} />
            )}
          </div>
        </section>
      </div>

      <section className="regional-coverage-panel">
        <div className="section-heading">
          <div><p className="eyebrow">{t(language, "igadCoverage")}</p><h2>{t(language, "regionalSituation")}</h2></div>
          <span className="regional-coverage-count"><strong>{assessedRegionCount}</strong> / {regionalRegions.length} {t(language, "assessed")}</span>
        </div>
        <div className="regional-country-grid">
          {regionalRegions.map((region) => {
            const isAvailable = availableRegionIds.has(region.id);
            const regionAlertCount = activeAlerts.filter((alert) => alert.regionId === region.id).length;
            const profile = data.profiles.find((candidate) => candidate.id === region.id);
            const regionalIndicators = [
              { label: "NDVI", metric: metricByLabel(profile?.metrics ?? [], "NDVI") },
              { label: "Rain", metric: metricByLabel(profile?.metrics ?? [], "Rainfall") },
              { label: "LST", metric: metricByLabel(profile?.metrics ?? [], "LST") }
            ];
            const trendPointCount = profile?.trends.reduce((maximum, trend) => Math.max(maximum, trend.points.length), 0) ?? 0;
            return (
              <button
                aria-label={`${t(language, "inspect")} ${region.name}`}
                data-selected={region.id === selectedRegion.id ? "true" : "false"}
                disabled={!isAvailable}
                key={region.id}
                onClick={() => onSelectRegion(region.id)}
                type="button"
              >
                <span className="regional-country-name"><strong>{region.name}</strong><small>{regionAlertCount} {t(language, regionAlertCount === 1 ? "activeAlert" : "activeAlertsCount")}</small></span>
                <span className="regional-country-score">{region.score === null ? "—" : region.score.toLocaleString("en-GB", { maximumFractionDigits: 1 })}<small>{region.score === null ? t(language, "noData") : "/100"}</small></span>
                <span className="severity-badge" data-severity={region.level}>{localizedSeverity(language, region.level)}</span>
                <small className="regional-country-quality">{localizedQuality(language, region.quality)}</small>
                <span className="regional-country-indicators" aria-label={`${region.name} ${t(language, "currentIndicators")}`}>
                  {regionalIndicators.map(({ label, metric }) => (
                    <span key={label}><small>{label}</small><strong>{metric ? `${metric.value}${metric.unit}` : "—"}</strong></span>
                  ))}
                </span>
                <small className="regional-country-history">{trendPointCount} {t(language, "trendPoints")}</small>
              </button>
            );
          })}
        </div>
      </section>

      <section className="selected-region-panel">
        <div className="section-heading selected-heading">
          <div><p className="eyebrow">{t(language, "focusedAnalysis")}</p><h2>{t(language, "selectedRegion")}: <strong>{selectedRegion.name}</strong></h2></div>
          <label>
            <span>{t(language, "changeRegion")}</span>
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
              <small className="metric-delta">{comparisonForMetric(metric, selectedProfile.historicalRows) ?? t(language, "noComparison")}</small>
            </article>
          ))}
        </div>
      </section>

      <div className="overview-bottom-grid">
        <TrendPanel language={language} title={`${t(language, "trends")} (${selectedRegion.name})`} trends={selectedProfile.trends} />
        <aside className="overview-decision-rail" aria-label={t(language, "overviewActions")}>
          <section className="overview-actions">
            <p className="eyebrow">{t(language, "decisionSupport")}</p>
            <h2>{t(language, "earlyActions")}</h2>
            <ul className="action-list">
              {(selectedProfile.recommendations.length ? selectedProfile.recommendations : data.recommendations).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <a className="text-link" href={alertsUrl}>{t(language, "guidance")}</a>
          </section>
          <section className="overview-share">
            <a className="report-cta" download href={reportUrl}>
              <span className="report-cta-copy"><strong>{t(language, "report")}</strong><small>{data.reportFilename}</small></span>
              <span aria-hidden="true" className="report-cta-arrow">↓</span>
            </a>
            <div className="export-box">
              <h2>{t(language, "exportData")}</h2>
              <a download href={csvUrl}><strong>CSV</strong><span>{data.exportFilenames.csv}</span></a>
              <a download href={jsonUrl}><strong>JSON</strong><span>{data.exportFilenames.json}</span></a>
            </div>
          </section>
        </aside>
      </div>

      <footer className="overview-footer">
        <p>{t(language, "footerDecision")}</p>
        <p>{t(language, "footerBuilt")}</p>
      </footer>
    </section>
  );
}

function TrendChart({ trend }: { trend: TrendSeries }): JSX.Element {
  const chartPoints = trend.points.map((point, index) => ({
    ...point,
    anomaly: point.value === null || point.baseline === null ? null : point.value - point.baseline,
    x: 42 + (trend.points.length === 1 ? 139 : (index / (trend.points.length - 1)) * 278)
  }));
  const maxAbs = Math.max(0.01, ...chartPoints.map((point) => Math.abs(point.anomaly ?? 0)));
  const y = (value: number): number => 16 + ((maxAbs - value) / (maxAbs * 2)) * 94;
  const segments: Array<Array<(typeof chartPoints)[number]>> = [];
  chartPoints.forEach((point) => {
    if (point.anomaly === null) return;
    const previous = chartPoints[chartPoints.indexOf(point) - 1];
    if (!previous || previous.anomaly === null) segments.push([]);
    segments[segments.length - 1].push(point);
  });
  const scaleLabel = (value: number): string => value.toLocaleString("en-GB", { maximumFractionDigits: Math.abs(value) < 10 ? 2 : 0 });
  return (
    <div className="trend-chart-wrap">
      <span className="trend-baseline-label">Difference from baseline · {trend.baselineLabel ?? "source baseline"}</span>
      <svg className="trend-chart" viewBox="0 0 340 148" role="img" aria-label={`${trend.label} anomaly chart with zero baseline`}>
        <line className="trend-grid-line" x1="42" x2="320" y1="16" y2="16" />
        <line className="trend-zero-line" x1="42" x2="320" y1={y(0)} y2={y(0)} />
        <line className="trend-grid-line" x1="42" x2="320" y1="110" y2="110" />
        <text className="trend-axis-label" x="36" y="20" textAnchor="end">+{scaleLabel(maxAbs)}</text>
        <text className="trend-axis-label" x="36" y={y(0) + 4} textAnchor="end">0</text>
        <text className="trend-axis-label" x="36" y="114" textAnchor="end">−{scaleLabel(maxAbs)}</text>
        {segments.map((segment, index) => (
          <polyline className="trend-line" key={index} points={segment.map((point) => `${point.x},${y(point.anomaly ?? 0)}`).join(" ")} />
        ))}
        {chartPoints.map((point) => point.anomaly === null ? null : (
          <circle
            aria-label={`${point.label}: ${scaleLabel(point.anomaly)} ${trend.unit} from baseline`}
            className="trend-point"
            cx={point.x}
            cy={y(point.anomaly)}
            key={point.label}
            r="4.5"
            tabIndex={0}
          >
            <title>{`${point.label} · value ${point.value} ${trend.unit} · baseline ${point.baseline} ${trend.unit} · difference ${scaleLabel(point.anomaly)} ${trend.unit}`}</title>
          </circle>
        ))}
        {chartPoints.map((point, index) => (trend.points.length <= 4 || index === 0 || index === trend.points.length - 1) ? (
          <text className="trend-date-label" key={`${point.label}-date`} x={point.x} y="136" textAnchor={index === 0 ? "start" : index === trend.points.length - 1 ? "end" : "middle"}>{formatTrendPeriod(point.label)}</text>
        ) : null)}
      </svg>
    </div>
  );
}

function TrendPanel({ trends, title = "Indicator Trends", language = "en" }: { trends: TrendSeries[]; title?: string; language?: Language }): JSX.Element {
  return (
    <section>
      <h2>{title}</h2>
      <div className="trend-grid">
        {trends.length ? trends.map((trend) => (
          <article className="trend" key={trend.indicator}>
            <h3>{trend.label}</h3>
            <p>{trend.unit} | {trend.source}</p>
            <TrendChart trend={trend} />
          </article>
        )) : (
          <Placeholder title={t(language, "trendPending")} detail={t(language, "trendPendingDetail")} />
        )}
      </div>
    </section>
  );
}

function LowBandwidthView({
  data,
  language,
  activeAlerts,
  onSelectRegion,
  route,
  selectedProfile,
  selectedRegion
}: {
  data: DashboardData;
  language: Language;
  activeAlerts: DashboardData["alerts"];
  onSelectRegion: (regionId: string) => void;
  route: string;
  selectedProfile: RegionProfile;
  selectedRegion: RegionRisk;
}): JSX.Element {
  const [selectedUnitId, setSelectedUnitId] = useState("");
  const liteAlertParams = useMemo(() => new URLSearchParams(window.location.search), []);
  const [liteQuery, setLiteQuery] = useState(liteAlertParams.get("q") ?? "");
  const [liteRegion, setLiteRegion] = useState(liteAlertParams.get("region") ?? "all");
  const [liteSeverity, setLiteSeverity] = useState(liteAlertParams.get("severity") ?? "all");
  const [liteStatus, setLiteStatus] = useState(liteAlertParams.get("status") ?? "all");
  const [litePeriod, setLitePeriod] = useState(liteAlertParams.get("period") ?? "all");
  const administrativeUnits = selectedProfile.administrativeUnits ?? [];
  const selectedUnit = administrativeUnits.find((unit) => unit.regionId === selectedUnitId);
  const litePeriods = Array.from(new Set(data.alerts.map((alert) => alert.period))).sort().reverse();
  const liteFilteredAlerts = data.alerts.filter((alert) => {
    const text = `${alertId(alert)} ${alert.region} ${alert.title} ${alert.action}`.toLowerCase();
    return (!liteQuery || text.includes(liteQuery.toLowerCase()))
      && (liteRegion === "all" || alert.regionId === liteRegion)
      && (liteSeverity === "all" || alert.severity === liteSeverity)
      && (liteStatus === "all" || alert.status === liteStatus)
      && (litePeriod === "all" || alert.period === litePeriod);
  });
  useEffect(() => setSelectedUnitId(""), [selectedRegion.id]);
  useEffect(() => {
    if (!route.startsWith("/alerts") || route.startsWith("/alerts/")) return;
    const params = new URLSearchParams();
    if (liteQuery) params.set("q", liteQuery);
    if (liteRegion !== "all") params.set("region", liteRegion);
    if (liteSeverity !== "all") params.set("severity", liteSeverity);
    if (liteStatus !== "all") params.set("status", liteStatus);
    if (litePeriod !== "all") params.set("period", litePeriod);
    const query = params.toString();
    window.history.replaceState({}, "", `/alerts${query ? `?${query}` : ""}`);
  }, [litePeriod, liteQuery, liteRegion, liteSeverity, liteStatus, route]);

  if (route.startsWith("/alerts")) {
    const requestedAlertId = route.startsWith("/alerts/") ? decodeURIComponent(route.slice("/alerts/".length)) : undefined;
    const requestedAlert = requestedAlertId ? data.alerts.find((alert) => alertId(alert) === requestedAlertId) : undefined;
    const visibleAlerts = requestedAlert ? [requestedAlert] : liteFilteredAlerts;
    const exportParams = new URLSearchParams();
    if (liteQuery) exportParams.set("q", liteQuery);
    if (liteRegion !== "all") exportParams.set("region", liteRegion);
    if (liteSeverity !== "all") exportParams.set("severity", liteSeverity);
    if (liteStatus !== "all") exportParams.set("status", liteStatus);
    if (litePeriod !== "all") exportParams.set("period", litePeriod);
    const exportQuery = exportParams.toString();
    const activeCount = visibleAlerts.filter((alert) => alert.status === "active").length;
    const severeCount = visibleAlerts.filter((alert) => alert.severity === "critical").length;
    const simulatedCount = visibleAlerts.reduce((count, alert) => count + (alert.notifications?.length ?? 0), 0);
    return (
      <section className="lite-view lite-alerts-view" aria-label="Low bandwidth Alerts Center">
        <div className="section-heading">
          <div><p className="eyebrow">Operational alerts</p><h2>Alerts Center · Low bandwidth</h2></div>
          <span>{visibleAlerts.length} alerts loaded</span>
        </div>
        <p>All alert evidence is supplied by the API. Notification entries below are simulations and do not represent real delivery.</p>
        {!requestedAlert ? <div className="alerts-filters" aria-label="Low bandwidth alert filters">
          <input aria-label="Search low bandwidth alerts" onChange={(event) => setLiteQuery(event.target.value)} placeholder="Search alerts" value={liteQuery} />
          <select aria-label="Low bandwidth country or region" onChange={(event) => setLiteRegion(event.target.value)} value={liteRegion}><option value="all">All regions</option>{data.regions.map((region) => <option key={region.id} value={region.id}>{region.name}</option>)}</select>
          <select aria-label="Low bandwidth severity" onChange={(event) => setLiteSeverity(event.target.value)} value={liteSeverity}><option value="all">All severities</option><option value="critical">Severe</option><option value="warning">Alert</option><option value="watch">Watch</option><option value="normal">Green</option><option value="unknown">Unknown</option></select>
          <select aria-label="Low bandwidth status" onChange={(event) => setLiteStatus(event.target.value)} value={liteStatus}><option value="all">All statuses</option><option value="active">Active</option><option value="monitoring">Monitoring</option><option value="preventive">Preventive</option><option value="resolved">Resolved</option><option value="superseded">Superseded</option></select>
          <select aria-label="Low bandwidth period" onChange={(event) => setLitePeriod(event.target.value)} value={litePeriod}><option value="all">All periods</option>{litePeriods.map((period) => <option key={period} value={period}>{period}</option>)}</select>
        </div> : null}
        <dl className="alert-status-band" aria-label="Low bandwidth alert summary"><div><dt>Results</dt><dd>{visibleAlerts.length}</dd></div><div><dt>Active</dt><dd>{activeCount}</dd></div><div><dt>Severe</dt><dd>{severeCount}</dd></div><div><dt>Simulated notifications</dt><dd>{simulatedCount}</dd></div></dl>
        <nav className="lite-downloads" aria-label="Alert downloads">
          <a download href={`/api/v1/exports/alerts?${exportQuery ? `${exportQuery}&` : ""}format=csv`}>CSV</a>
          <a download href={`/api/v1/exports/alerts?${exportQuery ? `${exportQuery}&` : ""}format=json`}>JSON</a>
          <a download href={`/api/v1/reports/alerts${exportQuery ? `?${exportQuery}` : ""}`}>PDF</a>
        </nav>
        {requestedAlertId && !requestedAlert ? <Placeholder title="Alert not found" detail="The requested alert is not present in the loaded snapshot." /> : null}
        {visibleAlerts.length ? <table>
          <thead><tr><th>ID</th><th>Region</th><th>Severity</th><th>Status</th><th>Issued</th><th>Recommended action</th></tr></thead>
          <tbody>{visibleAlerts.map((alert) => <tr key={alertId(alert)}><td><a href={`/alerts/${encodeURIComponent(alertId(alert))}`}>{alertId(alert)}</a></td><td>{alert.region}</td><td>{severityLabel(alert.severity)}</td><td>{alert.status}</td><td>{alert.issuedAt ?? alert.period}</td><td>{alert.action}</td></tr>)}</tbody>
        </table> : <p>No alerts are available in the loaded snapshot.</p>}
        {requestedAlert ? <>
          <h3>Evidence</h3>
          <table><thead><tr><th>Signal</th><th>Value</th></tr></thead><tbody>{requestedAlert.evidence.map(([label, value]) => <tr key={`${label}-${value}`}><td>{label}</td><td>{value}</td></tr>)}</tbody></table>
          <h3>Recommendations</h3>
          <ol>{requestedAlert.recommendations?.length ? requestedAlert.recommendations.map((item) => <li key={item.action}>{item.action}{item.suggestedActor ? ` · ${item.suggestedActor}` : ""}{item.urgency ? ` · ${item.urgency}` : ""}</li>) : <li>{requestedAlert.action}</li>}</ol>
          <h3>Lifecycle</h3>
          <ol>{(requestedAlert.events ?? []).map((event, index) => <li key={`${event.eventType}-${event.createdAt}-${index}`}>{event.createdAt}: {event.eventType} ({event.status})</li>)}</ol>
          <h3>Simulated notification outbox</h3>
          <ul>{(requestedAlert.notifications ?? []).map((item) => <li key={item.id}>{item.channel}: {item.recipientMasked} · {item.status}</li>)}</ul>
          <a href="/alerts">Back to Alerts Center</a>
        </> : null}
      </section>
    );
  }

  if (route === "/region") {
    return (
      <section className="lite-view lite-region-view" aria-label="Low bandwidth Region Explorer">
        <div className="section-heading">
          <div><p className="eyebrow">Region</p><h2>Region Explorer · Low bandwidth</h2></div>
          <span>{administrativeUnits.length} ADM1 areas loaded</span>
        </div>
        <div className="lite-region-controls">
          <label><span>Country</span><select value={selectedRegion.id} onChange={(event) => onSelectRegion(event.target.value)}>{data.regions.map((region) => <option key={region.id} value={region.id}>{countryDisplayName(region)}</option>)}</select></label>
          <label><span>Administrative area</span><select value={selectedUnitId} onChange={(event) => setSelectedUnitId(event.target.value)}><option value="">National view</option>{administrativeUnits.map((unit) => <option key={unit.regionId} value={unit.regionId}>{unit.name}</option>)}</select></label>
        </div>
        <section className="lite-selected-area">
          <h3>{selectedUnit?.name ?? countryDisplayName(selectedRegion)}</h3>
          <table>
            <tbody>
              <tr><th scope="row">Level</th><td>{selectedUnit ? "ADM1" : "Country"}</td></tr>
              <tr><th scope="row">Composite score</th><td>{formatScoreValue(selectedUnit?.score ?? selectedRegion.score)}</td></tr>
              <tr><th scope="row">Alert level</th><td>{severityLabel(selectedUnit?.level ?? selectedRegion.level)}</td></tr>
              <tr><th scope="row">Data quality</th><td>{qualityLabel(selectedUnit?.quality ?? selectedRegion.quality)}</td></tr>
              {selectedUnit ? <><tr><th scope="row">NDVI</th><td>{formatMapMetric(selectedUnit.ndvi)}</td></tr><tr><th scope="row">Rainfall</th><td>{formatMapMetric(selectedUnit.rainfallMm, " mm")}</td></tr><tr><th scope="row">LST</th><td>{formatMapMetric(selectedUnit.lstC, " °C")}</td></tr></> : null}
            </tbody>
          </table>
        </section>
        <details>
          <summary>Subnational ranking ({administrativeUnits.length})</summary>
          <table>
            <thead><tr><th>#</th><th>Area</th><th>Level</th><th>Score</th><th>Quality</th></tr></thead>
            <tbody>{administrativeUnits.map((unit) => <tr key={unit.regionId}><td>{unit.rank}</td><td><button className="ranking-select" type="button" onClick={() => setSelectedUnitId(unit.regionId)}>{unit.name}</button></td><td>{severityLabel(unit.level)}</td><td>{formatScoreValue(unit.score)}</td><td>{qualityLabel(unit.quality)}</td></tr>)}</tbody>
          </table>
        </details>
        <h2>{t(language, "activeAlerts")}</h2>
        <ul>{activeAlerts.filter((alert) => alert.regionId === selectedRegion.id).map((alert) => <li key={`${alert.regionId}-${alert.title}`}>{alert.title} — {alert.action}</li>)}</ul>
      </section>
    );
  }

  return (
    <section className="lite-view" aria-label="Low bandwidth Overview">
      <div className="section-heading"><div><p className="eyebrow">{t(language, "overview")}</p><h2>{t(language, "lowBandwidth")}</h2></div><label><span>{t(language, "changeRegion")}</span><select aria-label={t(language, "selectedRegion")} onChange={(event) => onSelectRegion(event.target.value)} value={selectedRegion.id}>{data.regions.map((region) => <option key={region.id} value={region.id}>{region.name}</option>)}</select></label></div>
      <p><strong>{selectedRegion.name}</strong> · {formatScoreValue(selectedRegion.score)} · {localizedSeverity(language, selectedRegion.level)} · {localizedQuality(language, selectedRegion.quality)} {t(language, "quality")} · {selectedRegion.period}</p>
      <h2>{t(language, "regionalSituation")}</h2>
      <table>
        <thead><tr><th>{t(language, "regions")}</th><th>{t(language, "value")}</th><th>{t(language, "risk")}</th><th>{t(language, "dataQuality")}</th></tr></thead>
        <tbody>{data.regions.map((region) => <tr key={region.id}><th scope="row"><button className="ranking-select" onClick={() => onSelectRegion(region.id)} type="button">{region.name}</button></th><td>{formatScoreValue(region.score)}</td><td>{localizedSeverity(language, region.level)}</td><td>{localizedQuality(language, region.quality)}</td></tr>)}</tbody>
      </table>
      <table>
        <thead><tr><th>{t(language, "indicator")}</th><th>{t(language, "value")}</th><th>{t(language, "comparison")}</th><th>{t(language, "detail")}</th></tr></thead>
        <tbody>
          {(selectedProfile.metrics.length ? selectedProfile.metrics : data.metrics).map((metric) => (
            <tr key={metric.label}><td>{metric.label}</td><td>{metric.value} {metric.unit}</td><td>{comparisonForMetric(metric, selectedProfile.historicalRows) ?? t(language, "noComparison")}</td><td>{metric.detail}</td></tr>
          ))}
        </tbody>
      </table>
      <h2>{t(language, "activeAlerts")}</h2>
      <ul>
        {activeAlerts.filter((alert) => alert.regionId === selectedRegion.id).map((alert) => (
          <li key={`${alert.regionId}-${alert.title}`}><a href={`/alerts/${encodeURIComponent(alertId(alert))}`}>{alert.region}: {alert.title}</a> — {alert.action}</li>
        ))}
      </ul>
      <h2>{t(language, "indicatorTrends")}</h2>
      {selectedProfile.trends.length ? selectedProfile.trends.map((trend) => <table key={trend.indicator}><caption>{trend.label} · {trend.source}</caption><thead><tr><th>{t(language, "period")}</th><th>{t(language, "value")}</th><th>{t(language, "baseline")}</th></tr></thead><tbody>{trend.points.map((point) => <tr key={point.label}><td>{formatTrendPeriod(point.label)}</td><td>{point.value ?? t(language, "gap")}</td><td>{point.baseline ?? t(language, "gap")}</td></tr>)}</tbody></table>) : <p>{t(language, "trendPending")}</p>}
      <h2>{t(language, "earlyActions")}</h2>
      <ul>{(selectedProfile.recommendations.length ? selectedProfile.recommendations : data.recommendations).map((item) => <li key={item}>{item}</li>)}</ul>
      <nav className="lite-downloads" aria-label={t(language, "snapshotDownloads")}><a download href={downloadUrl("/api/v1/reports/executive", selectedRegion.id, selectedRegion.period)}>{t(language, "report")}</a><a download href={downloadUrl("/api/v1/exports/snapshot", selectedRegion.id, selectedRegion.period, "csv")}>CSV</a><a download href={downloadUrl("/api/v1/exports/snapshot", selectedRegion.id, selectedRegion.period, "json")}>JSON</a></nav>
      <p className="muted">{t(language, "snapshotSource")}: <code>/api/v1/snapshots/latest</code></p>
    </section>
  );
}
