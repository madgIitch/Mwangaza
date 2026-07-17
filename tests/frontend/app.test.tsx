import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { loadApiDashboard } from "../../frontend/src/api";
import { App } from "../../frontend/src/App";
import { demoDashboard } from "../../frontend/src/fixtures";

describe("React PWA dashboard", () => {
  it("renders the main operational dashboard without Streamlit", () => {
    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Mwangaza" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Regional risk" })).toBeInTheDocument();
    expect(screen.getByText("Drought risk escalation")).toBeInTheDocument();
    expect(screen.getByText("mwangaza-executive-report-som-2026-07-15.pdf")).toBeInTheDocument();
    expect(screen.getByText(/Forecasts are not available yet/)).toBeInTheDocument();
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

    expect(screen.getByRole("heading", { name: "Hatari ya kikanda" })).toBeInTheDocument();
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
          data_mode: "demo",
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
