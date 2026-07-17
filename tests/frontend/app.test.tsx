import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { loadApiDashboard } from "../../frontend/src/api";
import { App } from "../../frontend/src/App";
import { demoDashboard } from "../../frontend/src/fixtures";

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

  it("renders Region Explorer as an internal app screen on /region", () => {
    window.history.pushState({}, "", "/region");

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Region Explorer" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Somalia Risk Map" })).toBeInTheDocument();
    expect(screen.getByLabelText("Regions map")).toBeInTheDocument();
    expect(screen.getByText("Why this region is at risk")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Subnational ranking" })).toBeInTheDocument();
    expect(screen.getByText("Methodology page pending")).toBeInTheDocument();
  });

  it("uses page routes instead of hash anchors in the sidebar", () => {
    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("href", "/overview");
    expect(screen.getByRole("link", { name: "Regions" })).toHaveAttribute("href", "/region");
    expect(screen.getByRole("link", { name: "Active alerts" })).toHaveAttribute("href", "/alerts");
    expect(screen.getByRole("link", { name: "Reports and export" })).toHaveAttribute("href", "/reports");
    expect(screen.getByRole("link", { name: "About" })).toHaveAttribute("href", "/about");
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

  it("does not draw provisional geography while the public API is loading on /region", () => {
    window.history.pushState({}, "", "/region");
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

    expect(screen.getByText("Map geometry pending")).toBeInTheDocument();
    expect(document.querySelector(".region-svg-map")).not.toBeInTheDocument();
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
});

function jsonResponse(body: unknown): Response {
  return {
    ok: true,
    json: async () => body
  } as Response;
}
