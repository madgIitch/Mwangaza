import { useEffect, useMemo, useState } from "react";
import { loadApiDashboardDetails, loadApiDashboardSnapshot } from "./api";
import { demoDashboard } from "./fixtures";
import { normalizeLanguage, t } from "./i18n";
import type { DashboardData, Language, RegionProfile, RegionRisk, Severity, TrendSeries } from "./types";
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

  const selectedRegion = data.regions.find((region) => region.id === selectedRegionId) ?? data.regions[0];
  const selectedProfile = data.profiles.find((profile) => profile.id === selectedRegion.id) ?? data.profiles[0];
  const activeAlerts = useMemo(
    () => data.alerts.filter((alert) => alert.status === "active").sort((a, b) => severityRank[b.severity] - severityRank[a.severity]),
    [data.alerts]
  );

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
          <a href="#overview">{t(language, "overview")}</a>
          <a href="#regional-risk">{t(language, "regionalRisk")}</a>
          <a href="#alerts">{t(language, "activeAlerts")}</a>
          <a href="#reports">{t(language, "reports")}</a>
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

        {lowBandwidth ? (
          <LowBandwidthView data={data} language={language} activeAlerts={activeAlerts} />
        ) : (
          <FullDashboard
            data={data}
            language={language}
            selectedRegion={selectedRegion}
            selectedProfile={selectedProfile}
            activeAlerts={activeAlerts}
            onSelectRegion={setSelectedRegionId}
          />
        )}
      </main>
    </div>
  );
}

function loadingApiDashboard(): DashboardData {
  return {
    ...demoDashboard,
    dataMode: "cache",
    source: "Loading public API",
    message: "Waiting for /api/v1/**",
    alerts: [],
    metrics: demoDashboard.metrics.map((metric) => ({ ...metric, detail: "Waiting for API response" }))
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

function FullDashboard({
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
  return (
    <>
      <section id="overview" className="metric-grid" aria-label={t(language, "overview")}>
        {data.metrics.map((metric) => (
          <article key={metric.label} className="metric" data-severity={metric.severity}>
            <span>{metric.label}</span>
            <strong>{metric.value}<small>{metric.unit}</small></strong>
            <p>{metric.detail}</p>
          </article>
        ))}
      </section>

      <section className="workspace">
        <section id="regional-risk" className="risk-area" aria-label={t(language, "regionalRisk")}>
          <div className="section-heading">
            <h2>{t(language, "regionalRisk")}</h2>
            <select value={selectedRegion.id} onChange={(event) => onSelectRegion(event.target.value)} aria-label={t(language, "selectedRegion")}>
              {data.regions.map((region) => (
                <option key={region.id} value={region.id}>{region.name}</option>
              ))}
            </select>
          </div>
          <div className="risk-map" role="list">
            {data.regions.map((region) => (
              <button
                className="risk-cell"
                data-severity={region.level}
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
          <div className="drilldown">
            <h3>{selectedProfile.name}</h3>
            <p>{selectedRegion.period} | score {selectedRegion.score ?? "No data"} | {selectedRegion.level}</p>
            <ul>
              {selectedProfile.recommendations.map((item) => <li key={item}>{item}</li>)}
            </ul>
            <p className="muted">{selectedProfile.pilotUnits.length ? selectedProfile.pilotUnits.join(", ") : "IGAD coverage remains national here."}</p>
          </div>
        </section>

        <aside className="side-panel">
          <section id="alerts">
            <h2>{t(language, "activeAlerts")}</h2>
            <div className="alert-list">
              {activeAlerts.map((alert) => (
                <article className="alert-item" data-severity={alert.severity} key={`${alert.regionId}-${alert.title}`}>
                  <h3>{alert.title}</h3>
                  <p>{alert.region} | {alert.period} | quality {alert.quality}</p>
                  <strong>{alert.action}</strong>
                  <small>{alert.evidence.map(([label, value]) => `${label}: ${value}`).join(" | ")}</small>
                </article>
              ))}
            </div>
          </section>
          <section id="reports">
            <h2>{t(language, "reports")}</h2>
            <p>{data.reportFilename}</p>
            <p>{data.exportFilenames.csv}</p>
            <p>{data.exportFilenames.json}</p>
          </section>
        </aside>
      </section>

      <section className="detail-grid">
        <TrendPanel trends={selectedProfile.trends} />
        <section>
          <h2>{t(language, "historicalComparison")}</h2>
          <table>
            <thead><tr><th>Period</th><th>Indicator</th><th>Current</th><th>Historical</th><th>Difference</th></tr></thead>
            <tbody>
              {selectedProfile.historicalRows.map((row) => (
                <tr key={`${row.period}-${row.indicator}`}>
                  <td>{row.period}</td><td>{row.indicator}</td><td>{row.current}</td><td>{row.historical}</td><td>{row.difference}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section>
          <h2>{t(language, "exposure")}</h2>
          <p>{data.exposureNote}</p>
          <h2>{t(language, "forecastDiagnostics")}</h2>
          <p>{data.forecastDiagnostics.message} | {data.forecastDiagnostics.modelVersion} | {data.forecastDiagnostics.confidence}</p>
        </section>
      </section>
    </>
  );
}

function TrendPanel({ trends }: { trends: TrendSeries[] }): JSX.Element {
  return (
    <section>
      <h2>Indicator Trends</h2>
      <div className="trend-grid">
        {trends.map((trend) => (
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
        ))}
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
