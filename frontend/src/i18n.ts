import type { Language } from "./types";

const labels: Record<Language, Record<string, string>> = {
  en: {
    overview: "Overview",
    regionalRisk: "Regional risk",
    selectedRegion: "Selected region",
    activeAlerts: "Active alerts",
    historicalComparison: "Historical comparison",
    exposure: "Potential exposure",
    reports: "Reports and export",
    forecastDiagnostics: "Forecast diagnostics",
    lowBandwidth: "Low bandwidth",
    offline: "Offline",
    offlineWarning: "Offline shell. Showing the latest timestamp available; data are not live.",
    apiFallback: "API unavailable. Demo fixtures are shown.",
    liveClaim: "Current source",
    installable: "Installable PWA"
  },
  es: {
    overview: "Resumen",
    regionalRisk: "Riesgo regional",
    selectedRegion: "Region seleccionada",
    activeAlerts: "Alertas activas",
    historicalComparison: "Comparacion historica",
    exposure: "Exposicion potencial",
    reports: "Reportes y export",
    forecastDiagnostics: "Diagnostico de forecast",
    lowBandwidth: "Bajo ancho de banda",
    offline: "Sin conexion",
    offlineWarning: "Shell offline. Se muestra el ultimo timestamp disponible; los datos no son live.",
    apiFallback: "API no disponible. Se muestran fixtures demo.",
    liveClaim: "Origen actual",
    installable: "PWA instalable"
  },
  sw: {
    overview: "Muhtasari",
    regionalRisk: "Hatari ya kikanda",
    selectedRegion: "Eneo lililochaguliwa",
    activeAlerts: "Tahadhari hai",
    historicalComparison: "Ulinganisho wa historia",
    exposure: "Waliopo hatarini",
    reports: "Ripoti na export",
    forecastDiagnostics: "Uchunguzi wa utabiri",
    lowBandwidth: "Mtandao mdogo",
    offline: "Nje ya mtandao",
    offlineWarning: "Shell iko nje ya mtandao. Muda wa mwisho unaonyeshwa; data si live.",
    apiFallback: "API haipatikani. Fixtures demo zinaonyeshwa.",
    liveClaim: "Chanzo cha sasa",
    installable: "PWA inayosakinishwa"
  }
};

export function t(language: Language, key: keyof typeof labels.en): string {
  return labels[language][key] ?? labels.en[key];
}

export function normalizeLanguage(value: string | null): Language {
  return value === "es" || value === "sw" ? value : "en";
}
