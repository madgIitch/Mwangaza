import type { DashboardData, GeoJsonGeometry, RiskContribution } from "./types";

const uiGeometryByRegion: Record<string, GeoJsonGeometry> = {
  ken: { type: "Polygon", coordinates: [[[34.2, -4.4], [41.3, -4.4], [41.3, 4.8], [34.2, 4.8], [34.2, -4.4]]] },
  eth: { type: "Polygon", coordinates: [[[33.6, 3.5], [47.4, 3.5], [47.4, 14.3], [33.6, 14.3], [33.6, 3.5]]] },
  som: { type: "Polygon", coordinates: [[[41.4, -1.4], [50.9, -1.4], [50.9, 11.7], [41.4, 11.7], [41.4, -1.4]]] },
  sdn: { type: "Polygon", coordinates: [[[22.5, 9.2], [37.9, 9.2], [37.9, 21.6], [22.5, 21.6], [22.5, 9.2]]] },
  ssd: { type: "Polygon", coordinates: [[[24.6, 3.9], [35.4, 3.9], [35.4, 11.8], [24.6, 11.8], [24.6, 3.9]]] },
  uga: { type: "Polygon", coordinates: [[[29.9, -1.2], [34.7, -1.2], [34.7, 3.9], [29.9, 3.9], [29.9, -1.2]]] },
  dji: { type: "Polygon", coordinates: [[[41.9, 11.1], [43.3, 11.1], [43.3, 12.6], [41.9, 12.6], [41.9, 11.1]]] },
  eri: { type: "Polygon", coordinates: [[[36.9, 12.7], [42.7, 12.7], [42.7, 17.6], [36.9, 17.6], [36.9, 12.7]]] }
};

export const demoDashboard: DashboardData = {
  project: "Mwangaza",
  tagline: "Bringing Light to Early Action",
  dataMode: "demo",
  isDemo: true,
  referenceDate: "2026-07-15",
  snapshotId: "mwangaza-offline-demo-v1",
  source: "Demo fixture",
  lastUpdated: "2026-07-15 16:00 UTC",
  message: "Data is current",
  selectedRegionId: "som",
  regions: [
    { id: "som", name: "Somalia", score: 82, level: "critical", quality: "ok", period: "2026-07-01 to 2026-07-15", uiGeometry: uiGeometryByRegion.som },
    { id: "ken", name: "Northern Kenya", score: 64, level: "warning", quality: "ok", period: "2026-07-01 to 2026-07-15", uiGeometry: uiGeometryByRegion.ken },
    { id: "eth", name: "Ethiopia", score: 43, level: "watch", quality: "degraded", period: "2026-07-01 to 2026-07-15", uiGeometry: uiGeometryByRegion.eth },
    { id: "uga", name: "Uganda", score: 22, level: "normal", quality: "ok", period: "2026-07-01 to 2026-07-15", uiGeometry: uiGeometryByRegion.uga }
  ],
  metrics: [
    { label: "NDVI anomaly", value: "-0.18", unit: "z", severity: "warning", detail: "Vegetation stress" },
    { label: "Rainfall anomaly", value: "-42", unit: "%", severity: "critical", detail: "Below seasonal baseline" },
    { label: "LST anomaly", value: "+2.4", unit: "C", severity: "warning", detail: "Surface heat elevated" },
    { label: "Composite score", value: "78", unit: "/100", severity: "critical", detail: "High drought risk" },
    { label: "Data quality", value: "Good", unit: "", severity: "normal", detail: "Most indicators available" },
    { label: "potentially_exposed", value: "1.1M-1.3M", unit: "est.", severity: "watch", detail: "demo/synthetic population grid" }
  ],
  alerts: [
    {
      id: "ALT-SOM-DEMO-202607",
      regionId: "som",
      region: "Somalia",
      severity: "critical",
      title: "Drought risk escalation",
      period: "Jul 2026",
      action: "Activate urgent coordination review.",
      quality: "ok",
      status: "active",
      evidence: [["Model Version", "demo-risk-v1"], ["Source", "Demo fixture"]]
    },
    {
      id: "ALT-KEN-DEMO-202607",
      regionId: "ken",
      region: "Northern Kenya",
      severity: "warning",
      title: "Rainfall deficit watch",
      period: "Jul 2026",
      action: "Pre-position livestock feed.",
      quality: "ok",
      status: "active",
      evidence: [["Model Version", "demo-risk-v1"], ["Source", "Demo fixture"]]
    },
    {
      id: "ALT-ETH-DEMO-202607",
      regionId: "eth",
      region: "Ethiopia",
      severity: "watch",
      title: "Vegetation stress emerging",
      period: "Jul 2026",
      action: "Prepare early action checklist.",
      quality: "degraded",
      status: "active",
      evidence: [["Model Version", "demo-risk-v1"], ["Quality", "degraded"]]
    }
  ],
  recommendations: [
    "Prioritize water trucking readiness in high-risk districts.",
    "Pre-position livestock feed in pastoral corridors.",
    "Coordinate district verification before publishing alerts."
  ],
  profiles: [],
  exposureNote: "potentially_exposed | source demo-population-grid | year 2024 | 1 km | demo/synthetic",
  reportFilename: "mwangaza-executive-report-som-2026-07-15.pdf",
  exportFilenames: {
    csv: "mwangaza-visible-snapshot-som-2026-07-15.csv",
    json: "mwangaza-visible-snapshot-som-2026-07-15.json"
  },
  forecastDiagnostics: {
    available: false,
    message: "Forecasts are not available yet",
    modelVersion: "forecast-demo-v1",
    confidence: "Prototype diagnostics only"
  }
};

function demoContributions(compositeScore: number | null): RiskContribution[] {
  const target = compositeScore ?? 0;
  const scale = target / 75.2;
  const raw = [
    { indicator: "ndvi", weight: 0.4, score: 72 * scale, source: "Demo fixture", quality: "ok" },
    { indicator: "rainfall_mm", weight: 0.4, score: 84 * scale, source: "Demo fixture", quality: "ok" },
    { indicator: "lst_c", weight: 0.2, score: 64 * scale, source: "Demo fixture", quality: "ok" }
  ];
  const total = raw.reduce((sum, item) => sum + item.weight * item.score, 0);
  return raw.map((item) => ({
    ...item,
    weightedContribution: item.weight * item.score,
    shareOfComposite: total > 0 ? item.weight * item.score / total : 0
  }));
}

demoDashboard.profiles = demoDashboard.regions.map((region) => ({
  id: region.id,
  name: region.name,
  metrics: region.id === "som" ? demoDashboard.metrics : demoDashboard.metrics.map((metric) => ({
    ...metric,
    value: metric.label === "Composite score" ? String(region.score ?? "No data") : metric.value,
    severity: region.level
  })),
  alerts: demoDashboard.alerts.filter((alert) => alert.regionId === region.id),
  recommendations: region.id === "som" ? demoDashboard.recommendations : ["Prepare early action checklist."],
  pilotUnits: region.id === "som" ? ["Somalia Pilot Area"] : region.id === "ken" ? ["Northern Kenya Pilot Area"] : [],
  pilotRows: region.id === "som"
    ? [{ id: "somalia-pilot", name: "Somalia Pilot Area", adminLevel: "pilot_area", score: 78, level: "critical", quality: "ok", rank: 1 }]
    : region.id === "ken"
      ? [{ id: "northern-kenya-pilot", name: "Northern Kenya Pilot Area", adminLevel: "pilot_area", score: 61, level: "warning", quality: "ok", rank: 1 }]
      : [],
  contributions: demoContributions(region.score),
  trends: [
    {
      indicator: "ndvi",
      label: "NDVI trend",
      unit: "index",
      source: "MODIS/061/MOD13Q1",
      points: [
        { label: "Jun 15", value: 0.3, baseline: 0.28 },
        { label: "Jun 30", value: 0.24, baseline: 0.28 },
        { label: "Jul 15", value: 0.18, baseline: 0.27 }
      ]
    },
    {
      indicator: "rainfall_mm",
      label: "Rainfall trend",
      unit: "mm",
      source: "UCSB-CHG/CHIRPS/DAILY",
      points: [
        { label: "Jun 15", value: 26, baseline: 30 },
        { label: "Jun 30", value: 19, baseline: 30 },
        { label: "Jul 15", value: 18, baseline: 30 }
      ]
    }
  ],
  historicalRows: [
    { period: "2025-07-15", indicator: "Rainfall", current: "18 mm", historical: "31 mm", difference: "-13 mm", version: "demo-history-v1" },
    { period: "2024-07-15", indicator: "NDVI", current: "0.18 index", historical: "0.23 index", difference: "-0.05 index", version: "demo-history-v1" },
    { period: "2023-07-15", indicator: "LST", current: "29.4 C", historical: "28.6 C", difference: "+0.8 C", version: "demo-history-v1" }
  ]
}));
