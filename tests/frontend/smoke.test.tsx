import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../frontend/src/App";
import { demoDashboard } from "../../frontend/src/fixtures";

const routes = [
  ["/overview", "Risk Map - IGAD"],
  ["/region", "Region Explorer"],
  ["/alerts", "Alerts Center"],
  ["/reports", "Reports Center"],
  ["/about", "About Mwangaza"]
] as const;

describe("canonical React route smoke", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it.each(routes)("opens %s with deterministic fixtures", (route, heading) => {
    window.history.pushState({}, "", route);
    render(<App initialData={demoDashboard} skipApiLoad />);
    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
  });

  it("opens admin with a deterministic API fixture", async () => {
    window.history.pushState({}, "", "/admin");
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(adminFixture())));
    render(<App initialData={demoDashboard} skipApiLoad />);
    await waitFor(() => expect(screen.getByText("Public demo mode. Changes are available without credentials.")).toBeInTheDocument());
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

function adminFixture() {
  const configuration = {
    schema_version: "mwangaza.admin.v1",
    thresholds: { threshold_version: "v1", domain_min: 0, domain_max: 100, bands: [], is_official: false, label: "smoke" },
    actions: { recommendation_version: "v1", templates: { warning: { level: "warning", action: "Review", suggested_actor: "Analyst", urgency: "review" } } }
  };
  const version = { version_id: "cfg-smoke", created_at: "2026-07-18T12:00:00Z", created_by: "system", status: "active", content_hash: "1234567890abcdef", configuration, validation_errors: [] };
  return { schema_version: "mwangaza.api.v1", admin_schema_version: "mwangaza.admin.v1", active_version: version, saved_version: null, versions: [version], security: { access: "public", auth: "none", institutional_auth: false }, recalculation: { triggered: false, message: "No recalculation" } };
}
