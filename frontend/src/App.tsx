import { useEffect, useMemo, useState } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { loadApiDashboardDetails, loadApiDashboardSnapshot } from "./api";
import { demoDashboard } from "./fixtures";
import { normalizeLanguage, t } from "./i18n";
import type { DashboardData, GeoJsonGeometry, Language, Metric, RegionProfile, RegionRisk, Severity, TrendSeries } from "./types";
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
          <a data-active={route === "/" ? "true" : "false"} href="/">{t(language, "overview")}</a>
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
          <StandalonePage title={t(language, "activeAlerts")} detail="Dedicated alerts page pending. This route is separate from Overview and will host alert filtering." />
        ) : route === "/reports" ? (
          <StandalonePage title={t(language, "reports")} detail="Dedicated reports page pending. This route is separate from Overview and will host exports." />
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

function StandalonePage({ title, detail }: { title: string; detail: string }): JSX.Element {
  return (
    <section className="standalone-page" aria-label={title}>
      <p className="eyebrow">Section</p>
      <h2>{title}</h2>
      <Placeholder title="Page shell pending" detail={detail} />
    </section>
  );
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
        <section id="regions" className="risk-area" aria-label={t(language, "regions")}>
          <div className="section-heading">
            <h2>{t(language, "regions")}</h2>
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
