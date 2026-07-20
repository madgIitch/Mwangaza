import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { loadApiDashboard } from "../../frontend/src/api";
import { App } from "../../frontend/src/App";
import { demoDashboard } from "../../frontend/src/fixtures";

const somaliaAdm1 = JSON.parse(readFileSync(resolve("frontend/public/maps/SOM-ADM1.geojson"), "utf8"));

function mockAdministrativeMap(): void {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => somaliaAdm1 }));
}

describe("React PWA dashboard", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("renders the main operational dashboard without Streamlit", () => {
    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Mwangaza" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Risk Map - IGAD" })).toBeInTheDocument();
    expect(screen.getByText("Selected region:")).toBeInTheDocument();
    expect(screen.getByText("Drought risk escalation")).toBeInTheDocument();
    expect(screen.getByText("Generate Executive PDF Report")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Export data" })).toBeInTheDocument();
  });

  it("renders Overview as a dedicated /overview page route", () => {
    window.history.pushState({}, "", "/overview");

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("data-active", "true");
    expect(screen.getByRole("heading", { name: "Risk Map - IGAD" })).toBeInTheDocument();
    expect(screen.getByLabelText("Overview risk map")).toBeInTheDocument();
  });

  it("keeps the explicit demo route isolated from the live API", () => {
    window.history.pushState({}, "", "/overview?demo=1&api=1");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(screen.getByRole("status")).toHaveTextContent("Demo data");
    expect(screen.getByRole("status")).toHaveTextContent("mwangaza-offline-demo-v1");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("renders Region Explorer as an internal app screen on /region", async () => {
    window.history.pushState({}, "", "/region");
    mockAdministrativeMap();

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Region Explorer" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Somalia" })).toBeInTheDocument();
    expect(screen.getByLabelText("Regions map")).toBeInTheDocument();
    expect(screen.getByText(/score shown above is national/i)).toBeInTheDocument();
    expect(document.querySelector(".map-readout")).not.toBeInTheDocument();
    await waitFor(() => expect(document.querySelector(".region-svg-map")).toBeInTheDocument());
    await waitFor(() => expect(document.querySelectorAll(".region-svg-map path").length).toBe(18));
    expect([...document.querySelectorAll<SVGPathElement>(".region-svg-map path")].every((path) => path.style.fill !== "#f08c2e")).toBe(true);
    expect(screen.getByText("Why this region is at risk")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Subnational ranking" })).toBeInTheDocument();
    expect(screen.getByText("Methodology page pending")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Subregion / District" })).toBeEnabled();
    expect(screen.getByRole("link", { name: "View all alerts" })).toHaveAttribute(
      "href",
      "/alerts?region=som&period=2026-07-01+to+2026-07-15&status=active"
    );
    expect(screen.queryByText(/Placeholder contribution weights/)).not.toBeInTheDocument();
    expect(screen.getByText("NDVI anomaly", { selector: ".contribution-row span" })).toBeInTheDocument();
  });

  it("switches Region Explorer into an available pilot view", () => {
    window.history.pushState({}, "", "/region");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    render(<App initialData={demoDashboard} skipApiLoad />);

    fireEvent.change(screen.getByRole("combobox", { name: "Subregion / District" }), { target: { value: "somalia-pilot" } });
    expect(screen.getByRole("button", { name: "Pilot subnational view" })).toHaveAttribute("data-active", "true");
    expect(screen.getAllByText("Somalia Pilot Area").length).toBeGreaterThan(0);
  });

  it("colors an ADM1 boundary only from an exact API boundary ISO", async () => {
    window.history.pushState({}, "", "/region");
    mockAdministrativeMap();
    const withAdm1 = {
      ...demoDashboard,
      profiles: demoDashboard.profiles.map((profile) => profile.id === "som" ? {
        ...profile,
        administrativeUnits: [{
          regionId: "adm1-so-hi",
          boundaryId: "83879307B66756469447496",
          boundaryIso: "SO-HI",
          name: "Hiiraan",
          parentId: "som",
          adminLevel: "adm1",
          score: 76,
          level: "critical" as const,
          quality: "ok",
          periodStart: "2026-07-01T00:00:00Z",
          periodEnd: "2026-07-15T00:00:00Z",
          sourceMode: "live",
          geometrySource: "geoBoundaries gbOpen wmgeolab/geoBoundaries@9469f09",
          ndvi: 0.18,
          rainfallMm: 3.1,
          lstC: 31.2,
          rank: 1
        }]
      } : profile)
    };

    render(<App initialData={withAdm1} skipApiLoad />);

    const hiiraan = await screen.findByLabelText("Hiiraan: 76 critical");
    expect(hiiraan).toHaveStyle({ fill: "#d92d20" });
    expect(screen.getByRole("option", { name: "Hiiraan" })).toBeInTheDocument();
  });

  it("uses page routes instead of hash anchors in the sidebar", () => {
    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("href", "/overview");
    expect(screen.getByRole("link", { name: "Regions" })).toHaveAttribute("href", "/region");
    expect(screen.getByRole("link", { name: "Active alerts" })).toHaveAttribute("href", "/alerts");
    expect(screen.getByRole("link", { name: "Reports and export" })).toHaveAttribute("href", "/reports");
    expect(screen.getByRole("link", { name: "About" })).toHaveAttribute("href", "/about");
    expect(screen.getByRole("link", { name: "Admin" })).toHaveAttribute("href", "/admin");
  });

  it("removes legacy hash anchors from the browser URL", () => {
    window.history.pushState({}, "", "/#regional-risk");

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(window.location.pathname).toBe("/");
    expect(window.location.hash).toBe("");
    expect(screen.getByRole("heading", { name: "Risk Map - IGAD" })).toBeInTheDocument();
  });

  it("renders alerts as a standalone center instead of scrolling inside Overview", () => {
    window.history.pushState({}, "", "/alerts");

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Alerts Center" })).toBeInTheDocument();
    expect(screen.getByLabelText("Search alerts")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Active alerts queue" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Somalia - Severe" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Notification outbox/ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Risk Map - IGAD" })).not.toBeInTheDocument();
  });

  it("renders reports as a standalone export center instead of scrolling inside Overview", () => {
    window.history.pushState({}, "", "/reports");

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Reports Center" })).toBeInTheDocument();
    expect(screen.getByLabelText("Search reports")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Generated reports queue" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Somalia - Executive PDF Report" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Recent exports" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Report preview" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Report contents" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Risk Map - IGAD" })).not.toBeInTheDocument();
  });

  it("renders about as a standalone methodology and project information screen", () => {
    window.history.pushState({}, "", "/about");

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "About Mwangaza" })).toBeInTheDocument();
    expect(screen.getByText(/satellite-powered drought early warning/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Data Sources" })).toBeInTheDocument();
    expect(screen.getByText("Google Earth Engine")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "How Mwangaza Works" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Limitations" })).toBeInTheDocument();
    expect(screen.getByText("Privacy Policy pending")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Risk Map - IGAD" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Data provenance and methodology" })).toHaveAttribute("href", "/about/provenance");
  });

  it("renders canonical data provenance with lineage and responsible-use definitions", () => {
    window.history.pushState({}, "", "/about/provenance");
    render(<App initialData={demoDashboard} skipApiLoad />);
    expect(screen.getByRole("heading", { name: "Data provenance and methodology" })).toBeInTheDocument();
    expect(screen.getByText("MODIS/061/MOD13Q1")).toBeInTheDocument();
    expect(screen.getByText(/potentially exposed population, not confirmed affected people/)).toBeInTheDocument();
    expect(screen.getByLabelText("Data lineage")).toHaveTextContent("Source → Transformation and QA → Cache → API → UI → Report");
  });

  it("does not draw synthetic risk geometry while administrative boundaries are loading", () => {
    window.history.pushState({}, "", "/region");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    const loadingRegionData = {
      ...demoDashboard,
      dataMode: "cache" as const,
      source: "Loading public API",
      regions: demoDashboard.regions.map(({ id, name, score, level, quality, period }) => ({
        id,
        name,
        score,
        level,
        quality,
        period
      }))
    };

    render(<App initialData={loadingRegionData} skipApiLoad />);

    expect(screen.getByText("Loading administrative boundaries…")).toBeInTheDocument();
    expect(document.querySelector(".region-svg-map")).not.toBeInTheDocument();
  });

  it("selects Northern Kenya districts and keeps report and notification aligned", () => {
    window.history.pushState({}, "", "/region");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    render(<App initialData={demoDashboard} skipApiLoad />);
    fireEvent.change(screen.getByLabelText("Country", { selector: "select" }), { target: { value: "ken" } });
    expect(screen.getByRole("heading", { name: "Northern Kenya subnational scenario" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Marsabit/ }));
    expect(screen.getByRole("heading", { name: "Marsabit · KEN-010" })).toBeInTheDocument();
    expect(screen.getByText(/report-KEN-010-demo/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Notification language"), { target: { value: "sw" } });
    expect(screen.getByText(/Kagua upatikanaji wa maji katika Marsabit/)).toBeInTheDocument();
  });

  it("renders a low-bandwidth table shell", () => {
    render(<App initialData={demoDashboard} initialLowBandwidth skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Low bandwidth" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Indicator" })).toBeInTheDocument();
    expect(screen.getByText("/api/v1/snapshots/latest")).toBeInTheDocument();
    expect(document.querySelector(".risk-map")).not.toBeInTheDocument();
  });

  it("switches i18n labels", () => {
    render(<App initialData={demoDashboard} initialLanguage="sw" skipApiLoad />);

    expect(screen.getByRole("link", { name: "Maeneo" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tahadhari hai" })).toBeInTheDocument();
  });

  it("shows an honest offline shell with the latest timestamp", () => {
    render(<App initialData={demoDashboard} initialOffline skipApiLoad />);

    expect(screen.getByRole("alert")).toHaveTextContent("Offline shell");
    expect(screen.getByRole("alert")).toHaveTextContent("2026-07-15 16:00 UTC");
    expect(screen.getByRole("alert")).toHaveTextContent("data are not live");
  });

  it("consumes the public API contract and falls back to normalized dashboard data", async () => {
    const fetchMock = vi.fn(async (path: RequestInfo | URL) => {
      const url = String(path);
      if (url.startsWith("/api/v1/snapshots/latest")) {
        return jsonResponse({
          schema_version: "mwangaza.api.v1",
          data_mode: "live",
          snapshot: {
            region_id: "som",
            region_label: "Somalia",
            period: "2026-07-15",
            rows: [{
              row_type: "metric",
              name: "Composite score",
              value: 81,
              unit: "/100",
              quality: "critical",
              source: "Google Earth Engine live query"
            }],
            regional_risk: [
              {
                id: "som",
                name: "Somalia",
                score: 81,
                level: "emergency",
                color_level: "red",
                quality: "ok",
                period_start: "2026-07-01T00:00:00Z",
                period_end: "2026-07-15T00:00:00Z",
                selected: true,
                source_mode: "live"
              },
              {
                id: "ken",
                name: "Kenya",
                score: 52,
                level: "watch",
                color_level: "yellow",
                quality: "ok",
                period_start: "2026-07-01T00:00:00Z",
                period_end: "2026-07-15T00:00:00Z",
                selected: false,
                source_mode: "live"
              }
            ],
            source_metadata: { source: "test" }
          }
        });
      }
      if (url.startsWith("/api/v1/alerts")) {
        return jsonResponse({
          schema_version: "mwangaza.api.v1",
          items: [{
            region_id: "som",
            region: "Somalia",
            severity: "critical",
            status: "active",
            title: "API alert",
            period: "Jul 2026",
            quality_flag: "ok",
            recommended_action: "Check API contract."
          }]
        });
      }
      return jsonResponse({
        schema_version: "mwangaza.api.v1",
        available: false,
        message: "Forecasts are not available yet",
        items: []
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const data = await loadApiDashboard();

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/snapshots/latest", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/alerts?limit=20", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/forecasts", expect.any(Object));
    expect(data.message).toBe("Loaded from /api/v1/**");
    expect(data.alerts[0].title).toBe("API alert");
    expect(data.metrics[0].value).toBe("81");
    expect(data.metrics[0].detail).toBe("Google Earth Engine live query");
    expect(data.regions[0]).toMatchObject({ id: "som", score: 81, level: "critical" });
    expect(data.regions[1]).toMatchObject({ id: "ken", score: 52, level: "watch" });
  });

  it("has an installable manifest shape", () => {
    const manifest = JSON.parse(readFileSync(resolve("frontend/public/manifest.webmanifest"), "utf8")) as {
      name: string;
      short_name: string;
      start_url: string;
      display: string;
      icons: unknown[];
    };

    expect(manifest.name).toContain("Mwangaza");
    expect(manifest.short_name).toBe("Mwangaza");
    expect(manifest.start_url).toBe("/");
    expect(manifest.display).toBe("standalone");
    expect(manifest.icons.length).toBeGreaterThan(0);
  });

  it("does not precache API data in the service worker shell", () => {
    const sw = readFileSync(resolve("frontend/public/sw.js"), "utf8");

    expect(sw).toContain("SHELL_ASSETS");
    expect(sw).toContain('url.pathname.startsWith("/api/")');
    expect(sw).not.toMatch(/SHELL_ASSETS[\s\S]*\/api\/v1/);
  });

  it("renders API fallback when public API requests fail", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new Error("network down");
    }));

    render(<App skipApiLoad={false} />);

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("API unavailable"));
  });

  it("loads the complete admin panel without credentials", async () => {
    window.history.pushState({}, "", "/admin");
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(adminResponse())));

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Admin Configuration" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Public demo mode. Changes are available without credentials.")).toBeInTheDocument());
    expect(screen.getByLabelText("Warning action")).toBeEnabled();
    expect(screen.queryByLabelText("Demo admin credential")).not.toBeInTheDocument();
    expect(screen.getByText(/institutional identity and authorization/i)).toBeInTheDocument();
  });

  it("edits warning action and saves an append-only version without credentials", async () => {
    window.history.pushState({}, "", "/admin");
    const fetchMock = vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      const url = String(path);
      if (url === "/api/v1/admin/config" && init?.method !== "POST") {
        return jsonResponse(adminResponse());
      }
      if (url === "/api/v1/admin/config" && init?.method === "POST") {
        return jsonResponse(adminResponse("cfg-saved-002", "draft", "Brief partners from admin panel"));
      }
      return jsonResponse(adminResponse());
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App initialData={demoDashboard} skipApiLoad />);

    await waitFor(() => expect(screen.getByDisplayValue("Preposition supplies and brief partners")).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Warning action"), { target: { value: "Brief partners from admin panel" } });
    fireEvent.click(screen.getByRole("button", { name: "Save new version" }));

    await waitFor(() => expect(screen.getByText(/Saved append-only version cfg-saved-002/)).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/admin/config", expect.objectContaining({ method: "POST" }));
    expect(JSON.stringify(fetchMock.mock.calls)).not.toContain("authorization");
    expect(screen.getByText("No refresh, forecast or Earth Engine call is triggered.")).toBeInTheDocument();
  });

  it("keeps admin history usable in low-bandwidth mode", async () => {
    window.history.pushState({}, "", "/admin");
    vi.stubGlobal("fetch", vi.fn(async () => {
      return jsonResponse(adminResponse());
    }));

    render(<App initialData={demoDashboard} initialLowBandwidth skipApiLoad />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "Version history" })).toBeInTheDocument());
    expect(screen.getByRole("columnheader", { name: "Version" })).toBeInTheDocument();
    expect(screen.getAllByText("cfg-active-001").length).toBeGreaterThan(0);
  });

  it("shows technical readiness and metrics on a separate route", async () => {
    window.history.pushState({}, "", "/technical");
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      schema_version: "mwangaza.api.v1",
      run_id: "judge-run-123",
      status: "operational",
      readiness: { status: "ready", ready: true, checks: { database: "ok", cache: "optional" } },
      metrics: {
        requests_total: 12,
        duration_ms_total: 240,
        duration_ms_average: 20,
        cache_hits: 3,
        cache_misses: 1,
        cache_hit_ratio: 0.75,
        regions_processed: 8,
        errors_total: 0,
        active_alerts: 2
      }
    })));

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Technical status" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("operational")).toBeInTheDocument());
    expect(screen.getByText("judge-run-123")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Dependency" })).toBeInTheDocument();
  });
});

function jsonResponse(body: unknown): Response {
  return {
    ok: true,
    json: async () => body
  } as Response;
}

function adminResponse(versionId = "cfg-active-001", status = "active", warningAction = "Preposition supplies and brief partners") {
  const configuration = {
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
        warning: { level: "warning", action: warningAction, suggested_actor: "Operations lead", urgency: "prepositioning" },
        emergency: { level: "emergency", action: "Activate urgent coordination review", suggested_actor: "Incident lead", urgency: "urgent_activation" },
        unknown: { level: "unknown", action: "Review data quality before intervention", suggested_actor: "Data lead", urgency: "data_review" }
      }
    }
  };
  const version = {
    version_id: versionId,
    created_at: "2026-07-17T20:00:00+00:00",
    created_by: "demo-admin",
    status,
    content_hash: "1234567890abcdef",
    configuration,
    validation_errors: []
  };
  return {
    schema_version: "mwangaza.api.v1",
    admin_schema_version: "mwangaza.admin.v1",
    active_version: status === "active" ? version : { ...version, version_id: "cfg-active-001", status: "active" },
    saved_version: status === "draft" ? version : null,
    versions: [version],
    security: { access: "public", auth: "none", institutional_auth: false },
    recalculation: { triggered: false, message: "Configuration changes do not refresh indicators, cache, forecasts or alerts." }
  };
}
