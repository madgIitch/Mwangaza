export type Severity = "normal" | "watch" | "warning" | "critical" | "unknown";
export type DataMode = "live" | "cache" | "demo" | "offline";
export type Language = "en" | "es" | "sw";

export interface Metric {
  label: string;
  value: string;
  unit: string;
  severity: Severity;
  detail: string;
}

export interface RegionRisk {
  id: string;
  name: string;
  score: number | null;
  level: Severity;
  quality: string;
  period: string;
  uiGeometry?: GeoJsonGeometry;
}

export interface GeoJsonGeometry {
  type: string;
  coordinates: unknown;
}

export interface Alert {
  regionId: string;
  region: string;
  severity: Severity;
  title: string;
  period: string;
  action: string;
  quality: string;
  status: string;
  evidence: Array<[string, string]>;
}

export interface TrendPoint {
  label: string;
  value: number | null;
  baseline: number | null;
}

export interface TrendSeries {
  indicator: string;
  label: string;
  unit: string;
  source: string;
  baselineLabel?: string;
  points: TrendPoint[];
}

export interface HistoricalRow {
  period: string;
  indicator: string;
  current: string;
  historical: string;
  difference: string;
  version: string;
}

export interface RiskContribution {
  indicator: string;
  weight: number | null;
  score: number | null;
  weightedContribution?: number | null;
  shareOfComposite?: number | null;
  source: string;
  quality: string;
}

export interface AdministrativeUnit {
  regionId: string;
  boundaryId: string;
  boundaryIso: string;
  name: string;
  parentId: string;
  adminLevel: string;
  score: number | null;
  level: Severity;
  quality: string;
  periodStart: string;
  periodEnd: string;
  sourceMode: string;
  geometrySource: string;
  ndvi: number | null;
  rainfallMm: number | null;
  lstC: number | null;
  contributions?: RiskContribution[];
  rank: number;
}

export interface RegionProfile {
  id: string;
  name: string;
  metrics: Metric[];
  alerts: Alert[];
  recommendations: string[];
  pilotUnits: string[];
  pilotRows?: Array<{ id: string; name: string; adminLevel: string; score: number | null; level: Severity; quality: string; rank: number }>;
  administrativeUnits?: AdministrativeUnit[];
  contributions?: RiskContribution[];
  trends: TrendSeries[];
  historicalRows: HistoricalRow[];
}

export interface DashboardData {
  project: string;
  tagline: string;
  dataMode: DataMode;
  isDemo?: boolean;
  referenceDate?: string;
  snapshotId?: string;
  source: string;
  lastUpdated: string;
  message: string;
  selectedRegionId: string;
  regions: RegionRisk[];
  metrics: Metric[];
  alerts: Alert[];
  recommendations: string[];
  profiles: RegionProfile[];
  periods?: Array<{ key: string; label: string; regions: RegionRisk[]; profiles: RegionProfile[] }>;
  exposureNote: string;
  reportFilename: string;
  exportFilenames: { csv: string; json: string };
  forecastDiagnostics: {
    available: boolean;
    message: string;
    modelVersion: string;
    confidence: string;
  };
}

export interface PublicSnapshotResponse {
  schema_version: "mwangaza.api.v1";
  data_mode: string;
  snapshot: {
    region_id: string;
    region_label: string;
    period: string;
    rows: Array<{
      row_type?: string;
      name?: string;
      period?: string;
      region_id?: string;
      region_label?: string;
      value?: string | number | null;
      unit?: string;
      quality?: string;
      source?: string;
    }>;
    regional_risk?: Array<{
      id: string;
      name: string;
      score: number | null;
      level: string;
      color_level: string;
      quality: string;
      period_start: string;
      period_end: string;
      selected: boolean;
      source_mode: string;
      ui_geometry?: GeoJsonGeometry | null;
    }>;
    region_profiles?: Array<{
      id: string;
      name: string;
      status: string;
      metrics: Metric[];
      pilot_units: Array<{ id: string; name: string; admin_level: string; score: number | null; level: string; quality: string; rank: number }>;
      administrative_units?: Array<{
        region_id: string;
        boundary_id: string;
        boundary_iso: string;
        name: string;
        parent_id: string;
        admin_level: string;
        score: number | null;
        level: string;
        quality: string;
        period_start: string;
        period_end: string;
        source_mode: string;
        geometry_source: string;
        metrics: { ndvi: number | null; rainfall_mm: number | null; lst_c: number | null };
        contributions?: Array<{ indicator: string; weight: number | null; score: number | null; weighted_contribution?: number | null; share_of_composite?: number | null; source: string; quality: string }>;
        rank: number;
      }>;
      trends: Array<{ indicator: string; label: string; unit: string; source: string; baseline_label?: string; points: Array<{ period: string; value: number | null; baseline: number | null }> }>;
      historical_rows: HistoricalRow[];
      recommendations: string[];
      contributions: Array<{ indicator: string; weight: number | null; score: number | null; weighted_contribution?: number | null; share_of_composite?: number | null; source: string; quality: string }>;
    }>;
    periods?: Array<{
      key: string;
      label: string;
      regions: PublicSnapshotResponse["snapshot"]["regional_risk"];
      profiles: NonNullable<PublicSnapshotResponse["snapshot"]["region_profiles"]>;
    }>;
    source_metadata: Record<string, unknown>;
  };
}

export interface PublicAlertsResponse {
  schema_version: "mwangaza.api.v1";
  items: Array<{
    region_id: string;
    region: string;
    severity: string;
    status: string;
    title: string;
    period: string;
    quality_flag: string;
    recommended_action: string;
  }>;
}

export interface PublicForecastsResponse {
  schema_version: "mwangaza.api.v1";
  available: boolean;
  message: string;
  items: unknown[];
}

export interface AdminConfiguration {
  schema_version: "mwangaza.admin.v1";
  thresholds: {
    threshold_version: string;
    domain_min: number;
    domain_max: number;
    bands: Array<{ level: string; minimum: number; maximum: number }>;
    is_official: boolean;
    label: string;
  };
  actions: {
    recommendation_version: string;
    templates: Record<string, {
      level: string;
      action: string;
      suggested_actor: string;
      urgency: string;
    }>;
  };
}

export interface AdminConfigurationVersion {
  version_id: string;
  created_at: string;
  created_by: string;
  status: string;
  content_hash: string;
  configuration: AdminConfiguration;
  validation_errors: string[];
}

export interface AdminConfigResponse {
  schema_version: "mwangaza.api.v1";
  admin_schema_version: "mwangaza.admin.v1";
  active_version: AdminConfigurationVersion | null;
  saved_version: AdminConfigurationVersion | null;
  versions: AdminConfigurationVersion[];
  security: {
    access: "public";
    auth: string;
    institutional_auth: boolean;
  };
  recalculation: {
    triggered: boolean;
    message: string;
  };
}

export interface AdminStatusResponse {
  schema_version: "mwangaza.api.v1";
  admin: {
    access: "public";
    auth: string;
    institutional_auth: boolean;
  };
}

export interface TechnicalStatusResponse {
  schema_version: "mwangaza.api.v1";
  run_id: string;
  status: "operational" | "degraded";
  readiness: {
    status: "ready" | "not_ready";
    ready: boolean;
    checks: Record<string, "ok" | "optional" | "unavailable">;
  };
  metrics: {
    requests_total: number;
    duration_ms_total: number;
    duration_ms_average: number;
    cache_hits: number;
    cache_misses: number;
    cache_hit_ratio: number;
    regions_processed: number;
    errors_total: number;
    active_alerts: number;
  };
}
