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

export interface RegionProfile {
  id: string;
  name: string;
  metrics: Metric[];
  alerts: Alert[];
  recommendations: string[];
  pilotUnits: string[];
  trends: TrendSeries[];
  historicalRows: HistoricalRow[];
}

export interface DashboardData {
  project: string;
  tagline: string;
  dataMode: DataMode;
  source: string;
  lastUpdated: string;
  message: string;
  selectedRegionId: string;
  regions: RegionRisk[];
  metrics: Metric[];
  alerts: Alert[];
  recommendations: string[];
  profiles: RegionProfile[];
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
