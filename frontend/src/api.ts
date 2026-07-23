import { demoDashboard } from "./fixtures";
import type {
  Alert,
  AboutStatusResponse,
  AdminConfigResponse,
  AdminConfiguration,
  DashboardData,
  Metric,
  PublicAlertsResponse,
  PublicForecastsResponse,
  PublicReportsResponse,
  PublicSnapshotResponse,
  RegionProfile,
  RegionRisk,
  RiskContribution,
  TechnicalStatusResponse
} from "./types";

let inFlightDashboard: Promise<DashboardData> | null = null;
let inFlightSnapshot: Promise<DashboardData> | null = null;
let inFlightDetails: Promise<DashboardData> | null = null;
let apiRequestSequence = 0;

async function getJson<T>(path: string, headers: Record<string, string> = {}): Promise<T> {
  const requestId = ++apiRequestSequence;
  const started = performance.now();
  apiLog("fetch start", { requestId, path });
  try {
    const response = await fetch(path, { headers: { accept: "application/json", ...headers } });
    const elapsedMs = Math.round(performance.now() - started);
    apiLog("fetch response", { requestId, path, status: response.status, ok: response.ok, elapsedMs });
    if (!response.ok) {
      throw new Error(`Request failed: ${path}`);
    }
    const payload = await response.json() as T;
    apiLog("fetch parsed", { requestId, path, elapsedMs: Math.round(performance.now() - started) });
    return payload;
  } catch (error) {
    apiLog("fetch error", { requestId, path, elapsedMs: Math.round(performance.now() - started), error: errorMessage(error) });
    throw error;
  }
}

async function postJson<T>(path: string, body: unknown, headers: Record<string, string> = {}): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { accept: "application/json", "content-type": "application/json", ...headers },
    body: JSON.stringify(body)
  });
  const payload = await response.json() as T;
  if (!response.ok) {
    throw new Error(errorDetail(payload) || `Request failed: ${path}`);
  }
  return payload;
}

function errorDetail(payload: unknown): string {
  if (payload && typeof payload === "object" && "error" in payload) {
    const error = (payload as { error?: { message?: string; details?: string[] } }).error;
    if (error?.details?.length) {
      return error.details.join("; ");
    }
    return error?.message ?? "";
  }
  return "";
}

export async function loadAdminConfig(): Promise<AdminConfigResponse> {
  return getJson<AdminConfigResponse>("/api/v1/admin/config");
}

export async function saveAdminConfig(configuration: AdminConfiguration): Promise<AdminConfigResponse> {
  return postJson<AdminConfigResponse>("/api/v1/admin/config", { configuration });
}

export async function activateAdminConfig(versionId: string): Promise<AdminConfigResponse> {
  return postJson<AdminConfigResponse>("/api/v1/admin/config/activate", { version_id: versionId });
}

export async function loadTechnicalStatus(): Promise<TechnicalStatusResponse> {
  return getJson<TechnicalStatusResponse>("/api/v1/observability");
}

export async function loadAboutStatus(): Promise<AboutStatusResponse> {
  return getJson<AboutStatusResponse>("/api/v1/about/status");
}

export async function loadApiDashboard(): Promise<DashboardData> {
  apiLog("dashboard load requested", { inFlight: Boolean(inFlightDashboard) });
  inFlightDashboard ??= loadApiDashboardOnce().finally(() => {
    apiLog("dashboard in-flight cleared");
    inFlightDashboard = null;
  });
  return inFlightDashboard;
}

async function loadApiDashboardOnce(): Promise<DashboardData> {
  const base = await loadApiDashboardSnapshot();
  return loadApiDashboardDetails(base);
}

export async function loadApiDashboardSnapshot(): Promise<DashboardData> {
  if (inFlightSnapshot) {
    apiLog("snapshot load reused");
    return inFlightSnapshot;
  }
  inFlightSnapshot = loadApiDashboardSnapshotOnce().finally(() => {
    apiLog("snapshot in-flight cleared");
    inFlightSnapshot = null;
  });
  return inFlightSnapshot;
}

async function loadApiDashboardSnapshotOnce(): Promise<DashboardData> {
  apiLog("snapshot load start");
  const snapshot = await getJson<PublicSnapshotResponse>("/api/v1/snapshots/latest");
  if (snapshot.schema_version !== "mwangaza.api.v1") {
    throw new Error("Unsupported API schema");
  }
  const dataMode = normalizeMode(snapshot.data_mode);
  const metrics = metricsFromSnapshot(snapshot) || demoDashboard.metrics;
  const regions = regionsFromSnapshot(snapshot, dataMode);
  const profiles = profilesFromSnapshot(snapshot, metrics, regions, dataMode);
  apiLog("snapshot normalized", {
    dataMode,
    source: sourceFromSnapshot(snapshot),
    regionId: snapshot.snapshot.region_id,
    period: snapshot.snapshot.period,
    rows: snapshot.snapshot.rows.length,
    regionalRisk: snapshot.snapshot.regional_risk?.length ?? 0,
    metrics: metrics.length,
    regions: regions.length
  });
  return {
    ...demoDashboard,
    dataMode,
    source: sourceFromSnapshot(snapshot),
    selectedRegionId: snapshot.snapshot.region_id,
    lastUpdated: snapshot.snapshot.period || demoDashboard.lastUpdated,
    message: dataMode === "cache"
      ? "Refreshing live data in background; showing the last materialized snapshot"
      : "Loaded snapshot from /api/v1/snapshots/latest",
    regions,
    metrics,
    alerts: [],
    recommendations: profiles[0]?.recommendations ?? [],
    profiles,
    periods: (snapshot.snapshot.periods ?? []).map((period) => ({
      key: period.key,
      label: period.label,
      regions: (period.regions ?? []).map(apiRegion),
      profiles: profilesFromApi(period.profiles)
    })),
    exposureNote: exposureNoteFromSnapshot(snapshot),
    reportFilename: reportFilenameFromSnapshot(snapshot),
    exportFilenames: exportFilenamesFromSnapshot(snapshot),
    forecastDiagnostics: {
      available: false,
      message: "Loading forecast diagnostics",
      modelVersion: "api-v1",
      confidence: "Waiting for /api/v1/forecasts"
    }
  };
}

export async function loadApiDashboardDetails(base: DashboardData): Promise<DashboardData> {
  if (inFlightDetails) {
    apiLog("details load reused", { selectedRegionId: base.selectedRegionId });
    return inFlightDetails;
  }
  inFlightDetails = loadApiDashboardDetailsOnce(base).finally(() => {
    apiLog("details in-flight cleared");
    inFlightDetails = null;
  });
  return inFlightDetails;
}

async function loadApiDashboardDetailsOnce(base: DashboardData): Promise<DashboardData> {
  apiLog("details load start", { baseMode: base.dataMode, selectedRegionId: base.selectedRegionId });
  const [alertsResult, forecastsResult, reportsResult] = await Promise.allSettled([
    getJson<PublicAlertsResponse>("/api/v1/alerts?limit=20"),
    getJson<PublicForecastsResponse>("/api/v1/forecasts"),
    getJson<PublicReportsResponse>("/api/v1/reports?limit=100")
  ]);
  apiLog("details load settled", {
    alerts: alertsResult.status,
    forecasts: forecastsResult.status,
    alertsError: alertsResult.status === "rejected" ? errorMessage(alertsResult.reason) : undefined,
    forecastsError: forecastsResult.status === "rejected" ? errorMessage(forecastsResult.reason) : undefined
  });
  const alerts = alertsResult.status === "fulfilled" ? normalizeAlerts(alertsResult.value) : base.alerts;
  const forecasts = forecastsResult.status === "fulfilled" ? alertsForecastDiagnostics(forecastsResult.value) : base.forecastDiagnostics;
  const reports = reportsResult.status === "fulfilled" ? reportsResult.value.items.map((item) => ({
    id: item.id, generatedAt: item.generated_at, updatedAt: item.updated_at, expiresAt: item.expires_at,
    status: item.status, regionId: item.region_id, region: item.region, periodStart: item.period_start,
    periodEnd: item.period_end, templateId: item.template_id, language: item.language, author: item.author,
    snapshotId: item.snapshot_id, formats: item.formats, error: item.error
  })) : base.reports;
  const profiles = mergeAlertsIntoProfiles(base.profiles, alerts, base.selectedRegionId);
  apiLog("details normalized", { alerts: alerts.length, forecastAvailable: forecasts.available, profiles: profiles.length });
  return {
    ...base,
    message: base.dataMode === "cache" ? base.message : "Loaded from /api/v1/**",
    alerts,
    recommendations: profiles[0]?.recommendations ?? base.recommendations,
    profiles,
    reports,
    forecastDiagnostics: forecasts
  };
}

function normalizeAlerts(alerts: PublicAlertsResponse): Alert[] {
  return alerts.items.map((item) => ({
    id: item.id ?? fallbackAlertId(item.region_id, item.title, item.period),
    regionId: item.region_id,
    region: item.region,
    severity: normalizeSeverity(item.severity),
    title: item.title,
    period: item.period,
    action: item.recommended_action,
    quality: item.quality_flag,
    status: item.status,
    alertType: item.alert_type ?? "drought",
    issuedAt: item.issued_at ?? item.period,
    updatedAt: item.updated_at ?? item.period,
    resolvedAt: item.resolved_at,
    evidence: item.evidence?.length
      ? item.evidence.map((entry) => [entry.label, entry.value] as [string, string])
      : [["API", "/api/v1/alerts"]],
    events: (item.events ?? []).map((event) => ({
      eventType: event.event_type,
      status: event.status,
      createdAt: event.created_at,
      fromSeverity: event.from_severity,
      toSeverity: event.to_severity
    })),
    notifications: (item.notifications ?? []).map((notification) => ({
      id: notification.id,
      channel: notification.channel,
      recipientMasked: notification.recipient_masked,
      content: notification.content,
      status: notification.status,
      createdAt: notification.created_at,
      isSimulated: notification.is_simulated
    })),
    recommendations: (item.recommendations ?? []).map((recommendation) => ({
      action: recommendation.action,
      suggestedActor: recommendation.suggested_actor,
      urgency: recommendation.urgency,
      horizon: recommendation.horizon,
      recommendationVersion: recommendation.recommendation_version
    }))
  }));
}

function fallbackAlertId(regionId: string, title: string, period: string): string {
  const stable = `${title}-${period}`.replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 24).toUpperCase();
  return `ALT-${regionId.toUpperCase()}-${stable || "ALERT"}`;
}

function alertsForecastDiagnostics(forecasts: PublicForecastsResponse): DashboardData["forecastDiagnostics"] {
  return {
    available: forecasts.available,
    message: forecasts.message,
    modelVersion: "api-v1",
    confidence: forecasts.available ? "Available from API" : "Not yet available"
  };
}

function sourceFromSnapshot(snapshot: PublicSnapshotResponse): string {
  const source = snapshot.snapshot.source_metadata.data_source ?? snapshot.snapshot.source_metadata.source;
  return typeof source === "string" && source.trim() ? source : "Public API";
}

function regionsFromSnapshot(snapshot: PublicSnapshotResponse, dataMode: DashboardData["dataMode"]): RegionRisk[] {
  if (dataMode === "demo") {
    return demoDashboard.regions;
  }
  const regionalRisk = snapshot.snapshot.regional_risk ?? [];
  if (regionalRisk.length) {
    return regionalRisk.map((region) => ({
      id: region.id,
      name: region.name || region.id.toUpperCase(),
      score: numericValue(region.score),
      level: normalizeRiskLevel(region.level, region.color_level),
      quality: region.quality || "unknown",
      period: periodLabel(region.period_start, region.period_end),
      uiGeometry: region.ui_geometry ?? undefined
    }));
  }
  const selectedId = snapshot.snapshot.region_id;
  const selectedName = snapshot.snapshot.region_label || selectedId.toUpperCase();
  const composite = metricRow(snapshot, "Composite score");
  const score = numericValue(composite?.value);
  const level = normalizeSeverity(composite?.quality ?? "unknown");
  return [
    {
      id: selectedId,
      name: selectedName,
      score,
      level,
      quality: qualityLabel(composite?.quality),
      period: snapshot.snapshot.period || "No period"
    },
    ...demoDashboard.regions
      .filter((region) => region.id !== selectedId)
      .map((region) => ({
        ...region,
        score: null,
        level: "unknown" as const,
        quality: "not in live snapshot",
        period: "No live snapshot"
      }))
  ];
}

function profilesFromSnapshot(
  snapshot: PublicSnapshotResponse,
  metrics: Metric[],
  regions: RegionRisk[],
  dataMode: DashboardData["dataMode"]
): RegionProfile[] {
  const apiProfiles = snapshot.snapshot.region_profiles ?? [];
  if (apiProfiles.length) {
    return profilesFromApi(apiProfiles);
  }
  if (dataMode === "demo") {
    return demoDashboard.profiles;
  }
  const selected = regions[0];
  const alertRows = snapshot.snapshot.rows.filter((row) => row.row_type === "alert");
  const recommendations = alertRows.length ? alertRows.map((row) => row.name ?? "Prepare early action checklist.") : [];
  return [
    {
      id: selected.id,
      name: selected.name,
      metrics,
      alerts: [],
      recommendations,
      pilotUnits: [],
      trends: [],
      historicalRows: []
    },
    ...regions.slice(1).map((region) => ({
      id: region.id,
      name: region.name,
      metrics: [],
      alerts: [],
      recommendations: [],
      pilotUnits: [],
      trends: [],
      historicalRows: []
    }))
  ];
}

function profilesFromApi(apiProfiles: NonNullable<PublicSnapshotResponse["snapshot"]["region_profiles"]>): RegionProfile[] {
  return apiProfiles.map((profile) => ({
      id: profile.id,
      name: profile.name,
      metrics: profile.metrics,
      alerts: [],
      recommendations: profile.recommendations,
      pilotUnits: profile.pilot_units.map((unit) => unit.name),
      pilotRows: profile.pilot_units.map((unit) => ({
        id: unit.id,
        name: unit.name,
        adminLevel: unit.admin_level,
        score: unit.score,
        level: normalizeRiskLevel(unit.level, ""),
        quality: unit.quality,
        rank: unit.rank
      })),
      administrativeUnits: (profile.administrative_units ?? []).map((unit) => ({
        regionId: unit.region_id,
        boundaryId: unit.boundary_id,
        boundaryIso: unit.boundary_iso,
        name: unit.name,
        parentId: unit.parent_id,
        adminLevel: unit.admin_level,
        score: unit.score,
        level: normalizeSeverity(unit.level),
        quality: unit.quality,
        periodStart: unit.period_start,
        periodEnd: unit.period_end,
        sourceMode: unit.source_mode,
        geometrySource: unit.geometry_source,
        ndvi: unit.metrics.ndvi,
        rainfallMm: unit.metrics.rainfall_mm,
        lstC: unit.metrics.lst_c,
        contributions: (unit.contributions ?? []).map(normalizeContribution),
        rank: unit.rank
      })),
      trends: profile.trends.map((trend) => ({
        indicator: trend.indicator,
        label: trend.label,
        unit: trend.unit,
        source: trend.source,
        baselineLabel: trend.baseline_label,
        points: trend.points.map((point) => ({ label: point.period, value: point.value, baseline: point.baseline }))
      })),
      historicalRows: profile.historical_rows,
      contributions: profile.contributions.map(normalizeContribution)
    }));
}

function apiRegion(region: NonNullable<PublicSnapshotResponse["snapshot"]["regional_risk"]>[number]): RegionRisk {
  return {
    id: region.id,
    name: region.name || region.id.toUpperCase(),
    score: numericValue(region.score),
    level: normalizeRiskLevel(region.level, region.color_level),
    quality: region.quality || "unknown",
    period: periodLabel(region.period_start, region.period_end),
    uiGeometry: region.ui_geometry ?? undefined
  };
}

function mergeAlertsIntoProfiles(profiles: RegionProfile[], alerts: Alert[], selectedRegionId: string): RegionProfile[] {
  return profiles.map((profile) => {
    const profileAlerts = alerts.filter((alert) => alert.regionId === profile.id);
    const recommendations = profile.id === selectedRegionId && profileAlerts.length
      ? profileAlerts.map((alert) => alert.action)
      : profile.recommendations;
    return { ...profile, alerts: profileAlerts, recommendations };
  });
}

function exposureNoteFromSnapshot(snapshot: PublicSnapshotResponse): string {
  const exposure = metricRow(snapshot, "potentially_exposed");
  if (!exposure) {
    return "No exposure row in public API snapshot";
  }
  const value = exposure.value === null || exposure.value === undefined ? "No data" : String(exposure.value);
  return `${exposure.name ?? "potentially_exposed"} | ${value} | ${exposure.source ?? "Public API snapshot"}`;
}

function reportFilenameFromSnapshot(snapshot: PublicSnapshotResponse): string {
  return `mwangaza-executive-report-${snapshot.snapshot.region_id}-${snapshot.snapshot.period.replaceAll(" ", "_")}.pdf`;
}

function exportFilenamesFromSnapshot(snapshot: PublicSnapshotResponse): DashboardData["exportFilenames"] {
  const base = `mwangaza-visible-snapshot-${snapshot.snapshot.region_id}-${snapshot.snapshot.period.replaceAll(" ", "_")}`;
  return { csv: `${base}.csv`, json: `${base}.json` };
}

function metricRow(snapshot: PublicSnapshotResponse, name: string): PublicSnapshotResponse["snapshot"]["rows"][number] | undefined {
  return snapshot.snapshot.rows.find((row) => row.row_type === "metric" && row.name === name);
}

function numericValue(value: string | number | null | undefined): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function qualityLabel(value: string | undefined): string {
  return value && value !== "unknown" ? value : "unknown";
}

function normalizeRiskLevel(level: string, colorLevel: string): RegionRisk["level"] {
  const normalized = level === "emergency" ? "critical" : level === "low" ? "normal" : level;
  if (normalized === "normal" || normalized === "watch" || normalized === "warning" || normalized === "critical") {
    return normalized;
  }
  if (colorLevel === "green") {
    return "normal";
  }
  if (colorLevel === "yellow") {
    return "watch";
  }
  if (colorLevel === "orange") {
    return "warning";
  }
  if (colorLevel === "red") {
    return "critical";
  }
  return "unknown";
}

function normalizeContribution(contribution: {
  indicator: string;
  weight: number | null;
  score: number | null;
  weighted_contribution?: number | null;
  share_of_composite?: number | null;
  source: string;
  quality: string;
}): RiskContribution {
  return {
    indicator: contribution.indicator,
    weight: numericValue(contribution.weight),
    score: numericValue(contribution.score),
    weightedContribution: numericValue(contribution.weighted_contribution),
    shareOfComposite: numericValue(contribution.share_of_composite),
    source: contribution.source,
    quality: contribution.quality
  };
}

function periodLabel(periodStart: string, periodEnd: string): string {
  if (periodStart && periodEnd) {
    return `${periodStart.slice(0, 10)} to ${periodEnd.slice(0, 10)}`;
  }
  return periodEnd ? periodEnd.slice(0, 10) : "No live snapshot";
}

function metricsFromSnapshot(snapshot: PublicSnapshotResponse): Metric[] | null {
  const rows = snapshot.snapshot.rows.filter((row) => row.row_type === "metric" && row.name);
  if (!rows.length) {
    return null;
  }
  return rows.map((row) => ({
    label: String(row.name),
    value: row.value === null || row.value === undefined ? "No data" : String(row.value),
    unit: row.unit ?? "",
    severity: normalizeSeverity(row.quality ?? "unknown"),
    detail: row.source ?? "Public API snapshot"
  }));
}

function normalizeSeverity(value: string): Alert["severity"] {
  if (value === "normal" || value === "watch" || value === "warning" || value === "critical") {
    return value;
  }
  return "unknown";
}

function normalizeMode(value: string): DashboardData["dataMode"] {
  if (value === "live" || value === "cache" || value === "demo") {
    return value;
  }
  return "demo";
}

function apiLog(message: string, fields: Record<string, unknown> = {}): void {
  if (!apiDebugEnabled()) {
    return;
  }
  console.info("[mwangaza.frontend.api]", message, fields);
}

function apiDebugEnabled(): boolean {
  const params = new URLSearchParams(window.location.search);
  return import.meta.env.MODE === "api" || params.get("debug") === "1";
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
