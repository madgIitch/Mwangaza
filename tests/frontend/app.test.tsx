import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { compatibleDroughtContinuation, loadApiDashboard, loadApiDashboardSnapshot } from "../../frontend/src/api";
import { App } from "../../frontend/src/App";
import { demoDashboard } from "../../frontend/src/fixtures";

const somaliaAdm1 = JSON.parse(readFileSync(resolve("frontend/public/maps/SOM-ADM1.geojson"), "utf8"));
const hiiraanUnit = {
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
  contributions: [
    { indicator: "ndvi", weight: 0.4, score: 80, weightedContribution: 32, shareOfComposite: 32 / 76, source: "GEE ADM1", quality: "ok" },
    { indicator: "rainfall_mm", weight: 0.4, score: 70, weightedContribution: 28, shareOfComposite: 28 / 76, source: "GEE ADM1", quality: "ok" },
    { indicator: "lst_c", weight: 0.2, score: 80, weightedContribution: 16, shareOfComposite: 16 / 76, source: "GEE ADM1", quality: "ok" }
  ],
  rank: 1
};

function mockAdministrativeMap(): void {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => somaliaAdm1 }));
}
describe("React PWA dashboard", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/");
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("renders the main operational dashboard without Streamlit", () => {
    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Mwangaza" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Risk Map - IGAD" })).toBeInTheDocument();
    expect(screen.getByText("Selected region:")).toBeInTheDocument();
    expect(screen.getByText("Drought risk escalation")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Export data" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /PDF|Report/i })).not.toBeInTheDocument();
  });

  it("renders Overview as a dedicated /overview page route", () => {
    window.history.pushState({}, "", "/overview");

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("data-active", "true");
    expect(screen.getByRole("heading", { name: "Risk Map - IGAD" })).toBeInTheDocument();
    expect(screen.getByLabelText("Overview risk map")).toBeInTheDocument();
  });

  it("keeps all IGAD countries visible and uses country selection only as drill-down", () => {
    window.history.pushState({}, "", "/overview");
    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Regional situation" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Inspect Sudan" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Inspect Djibouti" })).toBeDisabled();
    const kenya = screen.getByRole("button", { name: "Inspect Northern Kenya" });
    fireEvent.click(kenya);
    expect(screen.getByRole("heading", { name: /Selected region: Northern Kenya/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Trends (Northern Kenya)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Inspect Somalia" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Inspect Ethiopia" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Inspect Uganda" })).toBeInTheDocument();
    expect(screen.getByLabelText("Northern Kenya current indicators")).toHaveTextContent("NDVI-0.18z");
    expect(screen.getByLabelText("Ethiopia current indicators")).toHaveTextContent("Rain-42%");
    expect(kenya).toHaveTextContent("3 trend points");
  });

  it("operates Overview map zoom, home and data-quality layers from loaded data", async () => {
    window.history.pushState({}, "", "/overview");
    const { container } = render(<App initialData={demoDashboard} skipApiLoad />);

    const zoomIn = screen.getByRole("button", { name: "Zoom in" });
    const zoomOut = screen.getByRole("button", { name: "Zoom out" });
    expect(zoomOut).toBeDisabled();
    fireEvent.click(zoomIn);
    expect(zoomOut).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Home" }));
    expect(zoomOut).toBeDisabled();

    const somalia = await screen.findByRole("button", { name: /Somalia: 82, Severe, quality High/i });
    const somaliaGeometry = container.querySelector('[data-country="som"]');
    expect(somaliaGeometry).toBeInTheDocument();
    expect(somaliaGeometry?.getAttribute("d")?.length).toBeGreaterThan(100);
    expect(somalia).toHaveStyle({ fill: "#d92d20" });
    fireEvent.change(screen.getByRole("combobox", { name: "Layer" }), { target: { value: "quality" } });
    expect(somalia).toHaveStyle({ fill: "#247a53" });
    fireEvent.focus(somalia);
    expect(screen.getByText(/NDVI anomaly: -0.18z/)).toBeInTheDocument();
    expect(screen.getAllByText("Demo fixture").length).toBeGreaterThan(0);
  });

  it("shows persistent episodes across IGAD in Overview and links to the regional layer", async () => {
    window.history.pushState({}, "", "/overview");
    const sourceItem = demoDashboard.droughtContinuation!.items.find((item) =>
      item.current_drought_status === "active" && item.horizon_days === 30
    )!;
    const overviewEpisodes = {
      ...demoDashboard,
      profiles: demoDashboard.profiles.map((profile) => profile.id === "som" ? {
        ...profile,
        administrativeUnits: [hiiraanUnit]
      } : profile),
      droughtContinuation: {
        ...demoDashboard.droughtContinuation!,
        analysis_as_of: "2026-07-20",
        items: [{ ...sourceItem, region_id: hiiraanUnit.regionId }],
        total: 1
      }
    };

    render(<App initialData={overviewEpisodes} skipApiLoad />);
    fireEvent.change(screen.getByRole("combobox", { name: "Layer" }), { target: { value: "episodes" } });

    expect(screen.getByRole("heading", { name: "Persistent Episodes - IGAD" })).toBeInTheDocument();
    const somalia = await screen.findByRole("button", { name: "Somalia: 1 active episodes, 1 ADM1 evaluated" });
    expect(somalia).toHaveStyle({ fill: "#7656c7" });
    expect(screen.getByText("Hiiraan")).toBeInTheDocument();
    expect(screen.getByLabelText("episodes legend")).toHaveTextContent("Persistent episode");
    expect(screen.getByRole("link", { name: /Open persistent episodes · Somalia/ })).toHaveAttribute(
      "href",
      "/region?country=som&layer=episodes"
    );
  });

  it("opens a persistent-episode deep link with country and layer preserved", () => {
    window.history.pushState({}, "", "/region?country=ken&layer=episodes");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("combobox", { name: "Country" })).toHaveValue("ken");
    expect(screen.getByRole("button", { name: "Persistent episodes" })).toHaveAttribute("data-active", "true");
  });

  it("links Overview alerts and downloads to stable context-aware routes", () => {
    window.history.pushState({}, "", "/overview");
    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getAllByRole("link", { name: "View details" })[0]).toHaveAttribute("href", "/alerts/ALT-SOM-DEMO-202607");
    expect(screen.getByRole("link", { name: "View all alerts" })).toHaveAttribute("href", "/alerts?region=som&period=2026-07-01%20to%202026-07-15&status=active");
    expect(screen.getByRole("link", { name: /CSV/ })).toHaveAttribute("href", "/api/v1/exports/snapshot?region=som&period=2026-07-01+to+2026-07-15&format=csv");
    expect(screen.getByRole("link", { name: /JSON/ })).toHaveAttribute("href", "/api/v1/exports/snapshot?region=som&period=2026-07-01+to+2026-07-15&format=json");
  });

  it("renders stable alert detail routes and a sanitized missing state", () => {
    window.history.pushState({}, "", "/alerts/ALT-SOM-DEMO-202607");
    const { unmount } = render(<App initialData={demoDashboard} skipApiLoad />);
    expect(screen.getByLabelText("Alert ALT-SOM-DEMO-202607")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Decision context" })).toBeInTheDocument();
    expect(screen.getByText("Activate urgent coordination review.")).toBeInTheDocument();
    unmount();

    window.history.pushState({}, "", "/alerts/ALT-MISSING");
    render(<App initialData={demoDashboard} skipApiLoad />);
    expect(screen.getByRole("heading", { name: "Alert not found" })).toBeInTheDocument();
    expect(screen.getByText("404")).toBeInTheDocument();
  });

  it("offers Somali as an operational locale while preserving Spanish", () => {
    window.history.pushState({}, "", "/overview");
    render(<App initialData={demoDashboard} skipApiLoad />);

    fireEvent.click(screen.getByRole("button", { name: "SO" }));
    expect(screen.getByRole("link", { name: "Dulmar" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Khariidadda khatarta - IGAD" })).toBeInTheDocument();
    expect(screen.queryByText("Ogeysiisyo lama heli karo")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ES" })).toBeInTheDocument();
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

  it("polls a materialized snapshot until the background live refresh is available", async () => {
    vi.useFakeTimers();
    let snapshotRequests = 0;
    vi.stubGlobal("fetch", vi.fn(async (path: RequestInfo | URL) => {
      const url = String(path);
      if (url.startsWith("/api/v1/snapshots/latest")) {
        snapshotRequests += 1;
        return jsonResponse(refreshSnapshotResponse(snapshotRequests === 1 ? "cache" : "live"));
      }
      if (url.startsWith("/api/v1/alerts")) {
        return jsonResponse({ schema_version: "mwangaza.api.v1", items: [], limit: 20, offset: 0, total: 0 });
      }
      return jsonResponse({ schema_version: "mwangaza.api.v1", available: false, message: "Not available", items: [] });
    }));

    render(<App skipApiLoad={false} />);
    await act(async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); });
    expect(screen.getByText("CACHE", { selector: ".status-strip span" })).toBeInTheDocument();

    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });

    expect(snapshotRequests).toBe(2);
    expect(screen.getByText("LIVE QUERY", { selector: ".status-strip span" })).toBeInTheDocument();
  });

  it("renders Region Explorer as an internal app screen on /region", async () => {
    window.history.pushState({}, "", "/region");
    mockAdministrativeMap();

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Region Explorer" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Somalia" })).toHaveLength(2);
    expect(screen.getByLabelText("Regions map")).toBeInTheDocument();
    expect(screen.getByText(/score shown above is national/i)).toBeInTheDocument();
    expect(document.querySelector(".map-readout")).not.toBeInTheDocument();
    await waitFor(() => expect(document.querySelector(".region-svg-map")).toBeInTheDocument());
    await waitFor(() => expect(document.querySelectorAll(".region-svg-map path").length).toBe(18));
    expect([...document.querySelectorAll<SVGPathElement>(".region-svg-map path")].every((path) => path.style.fill !== "#f08c2e")).toBe(true);
    expect(screen.getByText("Why this region is at risk")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Subnational ranking/ })).toBeInTheDocument();
    expect(screen.queryByText("Methodology page pending")).not.toBeInTheDocument();
    expect(screen.getByText(/Methodology documentation will be linked/)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Subregion / District" })).toBeEnabled();
    expect(screen.getByRole("link", { name: "View all alerts" })).toHaveAttribute(
      "href",
      "/alerts?region=som&period=2026-07-01+to+2026-07-15&status=active"
    );
    expect(screen.queryByText(/Placeholder contribution weights/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Composite score contributions for Somalia")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /NDVI anomaly .* points/ })).toBeInTheDocument();
    expect(screen.getByText(/Composite contribution = normalized signal score/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "NDVI trend anomaly chart with zero baseline" })).toBeInTheDocument();
    expect(document.querySelectorAll(".trend-zero-line")).toHaveLength(2);
    expect(screen.getByText("2025", { selector: ".history-year th" })).toBeInTheDocument();
    expect(screen.getByText("-13 mm", { selector: ".delta-badge" })).toBeInTheDocument();
  });

  it("switches Region Explorer into an available pilot view", () => {
    window.history.pushState({}, "", "/region");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    render(<App initialData={demoDashboard} skipApiLoad />);

    fireEvent.change(screen.getByRole("combobox", { name: "Subregion / District" }), { target: { value: "somalia-pilot" } });
    expect(screen.getByRole("button", { name: "Subnational view" })).toHaveAttribute("data-active", "true");
    expect(screen.getAllByText("Somalia Pilot Area").length).toBeGreaterThan(0);
    expect(screen.getByText(/has not provided an attributable composite-score breakdown for Somalia Pilot Area/)).toBeInTheDocument();
  });

  it("shows only the highest-severity regional action", () => {
    window.history.pushState({}, "", "/region");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    const baseAlert = demoDashboard.alerts[0];
    const withPriorities = {
      ...demoDashboard,
      alerts: [
        { ...baseAlert, severity: "watch" as const, title: "Monitor conditions", action: "Review next month." },
        { ...baseAlert, severity: "critical" as const, title: "Immediate response", action: "Mobilize water access now." }
      ]
    };

    render(<App initialData={withPriorities} skipApiLoad />);

    expect(screen.getByText("Highest-priority active alert")).toBeInTheDocument();
    expect(screen.getByText("Mobilize water access now.")).toBeInTheDocument();
    expect(screen.queryByText("Review next month.")).not.toBeInTheDocument();
  });

  it("renders compact monthly trend dates and the effective baseline label", () => {
    window.history.pushState({}, "", "/region");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    const withMonthlyTrend = {
      ...demoDashboard,
      profiles: demoDashboard.profiles.map((profile) => profile.id === "som" ? {
        ...profile,
        trends: [{
          ...profile.trends[0],
          baselineLabel: "Mean of 24 available monthly points in this series.",
          points: [
            { label: "2024-06-01T00:00:00Z to 2024-06-30T00:00:00Z", value: 0.12, baseline: 0.2 },
            { label: "2025-06-01T00:00:00Z to 2025-06-30T00:00:00Z", value: 0.2, baseline: 0.2 },
            { label: "2026-06-01T00:00:00Z to 2026-06-30T00:00:00Z", value: 0.28, baseline: 0.2 }
          ]
        }]
      } : profile)
    };

    render(<App initialData={withMonthlyTrend} skipApiLoad />);

    expect(screen.getByText(/Mean of 24 available monthly points/)).toBeInTheDocument();
    expect(screen.getByText("Jun 24", { selector: ".trend-date-label" })).toBeInTheDocument();
    expect(screen.getByText("Jun 26", { selector: ".trend-date-label" })).toBeInTheDocument();
  });

  it("colors an ADM1 boundary only from an exact API boundary ISO", async () => {
    window.history.pushState({}, "", "/region");
    mockAdministrativeMap();
    const withAdm1 = {
      ...demoDashboard,
      profiles: demoDashboard.profiles.map((profile) => profile.id === "som" ? {
        ...profile,
        administrativeUnits: [hiiraanUnit]
      } : profile)
    };

    render(<App initialData={withAdm1} skipApiLoad />);

    const hiiraan = await screen.findByLabelText("Hiiraan: 76 critical");
    expect(hiiraan).toHaveStyle({ fill: "#d92d20" });
    expect(screen.getByRole("option", { name: "Hiiraan" })).toBeInTheDocument();
    fireEvent.click(hiiraan);
    expect(screen.getByRole("combobox", { name: "Subregion / District" })).toHaveValue("adm1-so-hi");
    expect(screen.getByText("Selected ADM1")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hiiraan" })).toBeInTheDocument();
    expect(screen.getByLabelText("Composite score contributions for Hiiraan")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /^NDVI anomaly 32 points,/ })).toBeInTheDocument();
    expect(hiiraan).toHaveAttribute("aria-current", "true");
    fireEvent.click(screen.getByRole("button", { name: "Return to national view" }));
    fireEvent.keyDown(hiiraan, { key: "Enter" });
    expect(screen.getByRole("combobox", { name: "Subregion / District" })).toHaveValue("adm1-so-hi");

    const rankingToggle = screen.getByRole("button", { name: /Subnational ranking/ });
    expect(rankingToggle).toHaveAttribute("aria-expanded", "false");
    expect(rankingToggle).toHaveAttribute("aria-controls", "subnational-ranking-table");
    fireEvent.click(rankingToggle);
    expect(rankingToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: "Hiiraan" })).toBeInTheDocument();
    expect(document.querySelector(".rank-marker[data-top='true']")).toHaveTextContent("1");
    expect(document.querySelector(".ranking-scroll .signal-badge[data-severity='critical']")).toHaveTextContent("Severe");
    expect(document.querySelector(".ranking-scroll .signal-badge[data-quality='ok']")).toHaveTextContent("High");
  });

  it("switches the ADM1 map from current risk to persistent episodes without losing selection", async () => {
    window.history.pushState({}, "", "/region");
    mockAdministrativeMap();
    const sourceItem = demoDashboard.droughtContinuation!.items.find((item) =>
      item.current_drought_status === "active" && item.horizon_days === 30
    )!;
    const withEpisodeLayer = {
      ...demoDashboard,
      profiles: demoDashboard.profiles.map((profile) => profile.id === "som" ? {
        ...profile,
        administrativeUnits: [hiiraanUnit]
      } : profile),
      droughtContinuation: {
        ...demoDashboard.droughtContinuation!,
        items: [{
          ...sourceItem,
          region_id: hiiraanUnit.regionId,
          target: "observed_drought_condition_continues" as const,
          current_phase: "satellite_condition_active",
          elapsed_days: 20
        }],
        total: 1
      }
    };

    render(<App initialData={withEpisodeLayer} skipApiLoad />);

    const riskHiiraan = await screen.findByLabelText("Hiiraan: 76 critical");
    fireEvent.click(riskHiiraan);
    fireEvent.click(screen.getByRole("button", { name: "Persistent episodes" }));

    const episodeHiiraan = screen.getByLabelText("Hiiraan: persistent episode active");
    expect(episodeHiiraan).toHaveStyle({ fill: "#7656c7" });
    expect(episodeHiiraan).toHaveAttribute("aria-current", "true");
    expect(screen.getByText("Active episodes")).toBeInTheDocument();
    expect(screen.getByText(/1 evaluated ·/)).toBeInTheDocument();
    expect(screen.getByLabelText("Persistent episode legend")).toHaveTextContent("Evaluated · no active episode");

    fireEvent.mouseEnter(episodeHiiraan);
    const tooltip = screen.getByText("Persistent episode active").closest(".map-tooltip") as HTMLElement;
    expect(within(tooltip).getByText("20 active days observed")).toBeInTheDocument();
    expect(within(tooltip).getByText(/30 days · .* ML .* historical/)).toBeInTheDocument();
  });

  it("uses page routes instead of hash anchors in the sidebar", () => {
    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("href", "/overview");
    expect(screen.getByRole("link", { name: "Regions" })).toHaveAttribute("href", "/region");
    expect(screen.getByRole("link", { name: "Active alerts" })).toHaveAttribute("href", "/alerts");
    expect(screen.getByRole("link", { name: "About" })).toHaveAttribute("href", "/about");
    expect(screen.queryByRole("link", { name: /Reports|Admin/i })).not.toBeInTheDocument();
  });

  it.each(["/reports", "/admin"])("redirects the retired %s route to Overview", (route) => {
    window.history.pushState({}, "", route);
    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Risk Map - IGAD" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/overview");
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
    expect(screen.getByRole("heading", { name: "Alerts queue" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Somalia - Severe" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Notification outbox/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Export CSV" })).toHaveAttribute("href", "/api/v1/exports/alerts?format=csv");
    expect(screen.getByRole("button", { name: "Alert settings unavailable" })).toBeDisabled();
    expect(screen.queryByRole("heading", { name: "Risk Map - IGAD" })).not.toBeInTheDocument();
  });

  it("persists Alerts Center filters in the URL", () => {
    window.history.pushState({}, "", "/alerts");
    render(<App initialData={demoDashboard} skipApiLoad />);

    fireEvent.change(screen.getByLabelText("Severity"), { target: { value: "critical" } });
    fireEvent.change(screen.getByLabelText("Search alerts"), { target: { value: "Somalia" } });

    expect(window.location.search).toContain("severity=critical");
    expect(window.location.search).toContain("q=Somalia");
  });

  it("keeps alert evidence available in low bandwidth mode", () => {
    window.history.pushState({}, "", "/alerts");
    render(<App initialData={demoDashboard} skipApiLoad />);

    fireEvent.click(screen.getByLabelText("Low bandwidth"));

    expect(screen.getByRole("heading", { name: "Alerts Center · Low bandwidth" })).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "CSV" })).toHaveAttribute("href", "/api/v1/exports/alerts?format=csv");
  });

  it("renders about as a standalone methodology and project information screen", () => {
    window.history.pushState({}, "", "/about");

    render(<App initialData={demoDashboard} skipApiLoad />);

    expect(screen.getByRole("heading", { name: "About Mwangaza" })).toBeInTheDocument();
    expect(screen.getByText(/satellite-powered drought early warning/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Two climate analysts reviewing satellite drought observations" })).toHaveAttribute("src", "/about-climate-analysts.png");
    expect(screen.getByRole("heading", { name: "Data Sources" })).toBeInTheDocument();
    expect(screen.getByText("Google Earth Engine")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "How Mwangaza Works" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Limitations" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Privacy Policy" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Terms of Use" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Contact" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Risk Map - IGAD" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Data provenance and methodology" })).toHaveAttribute("href", "/about/provenance");
  });

  it("omits the About photograph in low-bandwidth mode", () => {
    window.history.pushState({}, "", "/about");
    render(<App initialData={demoDashboard} skipApiLoad />);
    fireEvent.click(screen.getByLabelText("Low bandwidth"));
    expect(screen.queryByRole("img", { name: "Two climate analysts reviewing satellite drought observations" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "About Mwangaza" })).toBeInTheDocument();
  });

  it("persists the global theme and links the brand to Overview", () => {
    window.history.pushState({}, "", "/about");
    render(<App initialData={demoDashboard} skipApiLoad />);

    const brandLink = screen.getByRole("link", { name: "Mwangaza — go to Overview" });
    expect(brandLink).toHaveAttribute("href", "/overview");
    expect(brandLink.querySelector("img")).toHaveAttribute("src", "/icons/icon.svg");
    fireEvent.click(screen.getByRole("button", { name: "Switch to dark theme" }));
    expect(window.localStorage.getItem("mwangaza-theme")).toBe("dark");
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
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

  it("selects Northern Kenya districts and keeps operational context aligned", () => {
    window.history.pushState({}, "", "/region");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    render(<App initialData={demoDashboard} skipApiLoad />);
    fireEvent.change(screen.getByLabelText("Country", { selector: "select" }), { target: { value: "ken" } });
    expect(screen.getByRole("heading", { name: "Northern Kenya subnational scenario" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Marsabit/ }));
    expect(screen.getByRole("heading", { name: "Marsabit · KEN-010" })).toBeInTheDocument();
    expect(screen.getByText(/Operational area:/).closest("p")).toHaveTextContent("KEN-010");
    fireEvent.change(screen.getByLabelText("Notification language"), { target: { value: "sw" } });
    expect(screen.getByText(/Kagua upatikanaji wa maji katika Marsabit/)).toBeInTheDocument();
  });

  it("does not mix the Northern Kenya demo scenario into live ADM1 coverage", () => {
    window.history.pushState({}, "", "/region");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    render(<App initialData={{ ...demoDashboard, dataMode: "live", isDemo: false }} skipApiLoad />);

    fireEvent.change(screen.getByLabelText("Country", { selector: "select" }), { target: { value: "ken" } });

    expect(screen.queryByRole("heading", { name: "Northern Kenya subnational scenario" })).not.toBeInTheDocument();
    expect(screen.queryByText("Simulated notification")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "About administrative coverage" })).toBeInTheDocument();
  });

  it("renders a low-bandwidth table shell", () => {
    render(<App initialData={demoDashboard} initialLowBandwidth skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Low bandwidth" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Indicator" })).toBeInTheDocument();
    expect(screen.getByText("/api/v1/snapshots/latest")).toBeInTheDocument();
    expect(document.querySelector(".risk-map")).not.toBeInTheDocument();
  });

  it("keeps ADM1 selection and detail in low-bandwidth Region Explorer", () => {
    window.history.pushState({}, "", "/region");
    const withAdm1 = {
      ...demoDashboard,
      profiles: demoDashboard.profiles.map((profile) => profile.id === "som"
        ? { ...profile, administrativeUnits: [hiiraanUnit] }
        : profile)
    };

    render(<App initialData={withAdm1} initialLowBandwidth skipApiLoad />);

    expect(screen.getByRole("heading", { name: "Region Explorer · Low bandwidth" })).toBeInTheDocument();
    expect(document.querySelector(".region-svg-map")).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: "Administrative area" }), { target: { value: "adm1-so-hi" } });
    expect(screen.getByRole("heading", { name: "Hiiraan" })).toBeInTheDocument();
    expect(screen.getAllByRole("cell", { name: "76" })).toHaveLength(2);
  });

  it("binds the continuation module to the exact selected ADM1 in both region modes", () => {
    window.history.pushState({}, "", "/region");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    const { unmount } = render(<App initialData={demoDashboard} skipApiLoad />);
    fireEvent.change(screen.getByLabelText("Country", { selector: "select" }), { target: { value: "ken" } });
    fireEvent.change(screen.getByLabelText("Subregion / District"), { target: { value: "adm1-ke-43" } });

    expect(screen.getByRole("region", { name: "Drought continuation" })).toHaveTextContent("78.0%");
    expect(screen.getByRole("region", { name: "Drought continuation" })).toHaveTextContent("86.2%");
    unmount();

    render(<App initialData={demoDashboard} initialLowBandwidth skipApiLoad />);
    fireEvent.change(screen.getByLabelText("Country", { selector: "select" }), { target: { value: "ken" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Administrative area" }), { target: { value: "adm1-ke-01" } });
    expect(screen.getByRole("region", { name: "Drought continuation" })).toHaveTextContent("No active official drought episode");
    expect(screen.getByRole("region", { name: "Drought continuation" })).not.toHaveTextContent("0.0%");
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
      if (url.startsWith("/api/v1/drought-continuation-probabilities")) {
        return jsonResponse({ ...demoDashboard.droughtContinuation, is_demo: false, total: 204 });
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
    expect(fetchMock).not.toHaveBeenCalledWith("/api/v1/reports?limit=100", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/drought-continuation-probabilities?limit=100&offset=0", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/drought-continuation-probabilities?limit=100&offset=100", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/drought-continuation-probabilities?limit=100&offset=200", expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/forecasts", expect.any(Object));
    expect(data.message).toBe("Loaded from /api/v1/**");
    expect(data.alerts[0].title).toBe("API alert");
    expect(data.metrics[0].value).toBe("81");
    expect(data.metrics[0].detail).toBe("Google Earth Engine live query");
    expect(data.regions[0]).toMatchObject({ id: "som", score: 81, level: "critical" });
    expect(data.regions[1]).toMatchObject({ id: "ken", score: 52, level: "watch" });
    expect(data.droughtContinuation?.is_demo).toBe(false);
  });

  it("fails closed when dashboard and continuation evidence use different modes", () => {
    const demoContinuation = demoDashboard.droughtContinuation;
    expect(compatibleDroughtContinuation("live", demoContinuation)).toBeUndefined();
    expect(compatibleDroughtContinuation("cache", demoContinuation)).toBeUndefined();
    expect(compatibleDroughtContinuation("demo", demoContinuation)).toBe(demoContinuation);
    expect(compatibleDroughtContinuation("live", { ...demoContinuation!, is_demo: false })).toHaveProperty("is_demo", false);
  });

  it("keeps selectable continuation ADM1 fixtures when the demo API profile is national-only", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      schema_version: "mwangaza.api.v1",
      data_mode: "demo",
      snapshot: {
        region_id: "ken",
        region_label: "Kenya",
        period: "2026-07-15",
        rows: [],
        region_profiles: [{
          id: "ken", name: "Kenya", status: "available", metrics: [], pilot_units: [],
          administrative_units: [], trends: [], historical_rows: [], recommendations: [], contributions: []
        }],
        source_metadata: { source: "Demo fixture" }
      }
    })));

    const data = await loadApiDashboardSnapshot();
    const kenya = data.profiles.find((profile) => profile.id === "ken");
    expect(kenya?.administrativeUnits?.map((unit) => unit.regionId)).toEqual(["adm1-ke-43", "adm1-ke-01"]);
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
    expect(manifest.icons).toEqual(expect.arrayContaining([expect.objectContaining({ src: "/icons/icon.svg", type: "image/svg+xml" })]));
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

function refreshSnapshotResponse(dataMode: "cache" | "live") {
  const score = dataMode === "live" ? 61 : null;
  return {
    schema_version: "mwangaza.api.v1",
    data_mode: dataMode,
    snapshot: {
      region_id: "som",
      region_label: "Somalia",
      period: "2026-06-12 to 2026-06-26",
      rows: [{
        row_type: "metric",
        name: "Composite score",
        value: score,
        unit: "/100",
        quality: dataMode === "live" ? "warning" : "unknown",
        source: dataMode === "live" ? "Google Earth Engine live query" : "Materialized observed data"
      }],
      regional_risk: [{
        id: "som",
        name: "Somalia",
        score,
        level: dataMode === "live" ? "warning" : "unknown",
        color_level: dataMode === "live" ? "orange" : "unknown",
        quality: dataMode === "live" ? "ok" : "invalid",
        period_start: "2026-06-12T00:00:00Z",
        period_end: "2026-06-26T00:00:00Z",
        selected: true,
        source_mode: dataMode
      }],
      source_metadata: { source: dataMode === "live" ? "Google Earth Engine live query" : "Materialized observed data" }
    }
  };
}
