import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../frontend/src/App";
import { demoDashboard } from "../../frontend/src/fixtures";

const routes = [
  ["/overview", "Risk Map - IGAD"],
  ["/region", "Region Explorer"],
  ["/alerts", "Alerts Center"],
  ["/about", "About Mwangaza"]
] as const;

describe("canonical React route smoke", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it.each(routes)("opens %s with deterministic fixtures", (route, heading) => {
    window.history.pushState({}, "", route);
    if (route === "/region") vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    render(<App initialData={demoDashboard} skipApiLoad />);
    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Demo data");
    expect(screen.getByRole("status")).toHaveTextContent("mwangaza-offline-demo-v1");
  });

  it("opens technical status with deterministic metrics", async () => {
    window.history.pushState({}, "", "/technical");
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      schema_version: "mwangaza.api.v1",
      run_id: "smoke-run-001",
      status: "operational",
      readiness: { status: "ready", ready: true, checks: { database: "ok", cache: "optional" } },
      metrics: { requests_total: 1, duration_ms_total: 10, duration_ms_average: 10, cache_hits: 0, cache_misses: 0, cache_hit_ratio: 0, regions_processed: 0, errors_total: 0, active_alerts: 0 }
    })));
    render(<App initialData={demoDashboard} skipApiLoad />);
    await waitFor(() => expect(screen.getByText("operational")).toBeInTheDocument());
    expect(screen.getByRole("status")).toHaveTextContent("Demo data");
  });

  it("keeps essential data visible in low-bandwidth mode", () => {
    window.history.pushState({}, "", "/overview");
    render(<App initialData={demoDashboard} initialLowBandwidth skipApiLoad />);
    expect(screen.getByRole("heading", { name: "Low bandwidth" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Indicator" })).toBeInTheDocument();
  });
});

function jsonResponse(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as Response;
}
