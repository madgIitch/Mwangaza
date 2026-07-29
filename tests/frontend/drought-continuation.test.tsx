import { fireEvent, render, screen, within } from "@testing-library/react";
import { DroughtContinuation } from "../../frontend/src/components/DroughtContinuation";
import { demoDashboard } from "../../frontend/src/fixtures";
import type { DroughtContinuationResponse } from "../../frontend/src/types";

const response = demoDashboard.droughtContinuation as DroughtContinuationResponse;

describe("Drought continuation UI", () => {
  it("keeps experimental ML and the historical reference separate at 30 days", () => {
    render(<DroughtContinuation regionId="adm1-ke-43" response={response} />);

    expect(screen.getByText("Experimental ML prediction")).toBeInTheDocument();
    expect(screen.getByText("Historical reference")).toBeInTheDocument();
    expect(screen.getByText("78.0%")).toBeInTheDocument();
    expect(screen.getByText("86.2%")).toBeInTheDocument();
    expect(screen.getByText("Inconclusive validation")).toBeInTheDocument();
    expect(screen.getByText("Not for operational use")).toBeInTheDocument();
    expect(screen.getByText("Demo fixture")).toBeInTheDocument();
    expect(screen.getAllByText(/Association, not a causal effect/)).toHaveLength(3);
  });

  it("shows only the historical reference at long horizons", () => {
    render(<DroughtContinuation regionId="adm1-ke-43" response={response} />);
    fireEvent.click(screen.getByRole("button", { name: "60 days" }));

    const module = screen.getByRole("region", { name: "Drought continuation" });
    expect(within(module).getByText("Historical reference")).toBeInTheDocument();
    expect(within(module).getByText("75.0%")).toBeInTheDocument();
    expect(within(module).queryByText("Experimental ML prediction")).not.toBeInTheDocument();
  });

  it("labels non-demo probabilities as materialized GEE-derived evidence", () => {
    render(<DroughtContinuation regionId="adm1-ke-43" response={{ ...response, is_demo: false }} />);

    expect(screen.getByText("Materialized GEE-derived evidence")).toBeInTheDocument();
    expect(screen.queryByText("Demo fixture")).not.toBeInTheDocument();
  });

  it("shows the satellite target, analysis cut, query time and per-signal freshness", () => {
    const satellite: DroughtContinuationResponse = {
      ...response,
      is_demo: false,
      analysis_as_of: "2026-07-20",
      query_generated_at: "2026-07-29T08:30:00Z",
      items: response.items.map((item) => item.region_id === "adm1-ke-43"
        ? {
            ...item,
            as_of: "2026-07-20",
            target: "observed_drought_condition_continues",
            current_phase: "satellite_multisignal_active",
            condition_basis: "meteorological+vegetation",
            state_version: "satellite-multisignal-hysteresis-v1",
            signal_freshness: {
              spi_3m: {
                observed_at: "2026-06-30T00:00:00Z",
                available_at: "2026-07-11T00:00:00Z",
                age_days: 20,
                quality: "derived"
              }
            }
          }
        : item)
    };

    render(<DroughtContinuation regionId="adm1-ke-43" response={satellite} />);

    expect(screen.getByText("Observed drought condition")).toBeInTheDocument();
    expect(screen.getByText("Analysis as of 2026-07-20")).toBeInTheDocument();
    expect(screen.getByText("Query generated 2026-07-29")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Observation dates and freshness"));
    expect(screen.getByRole("rowheader", { name: "spi_3m" })).toBeInTheDocument();
    expect(screen.getByText("20 days")).toBeInTheDocument();
  });

  it("renders not applicable without inventing a zero percentage", () => {
    render(<DroughtContinuation regionId="adm1-ke-01" response={response} />);

    expect(screen.getByText("No active official drought episode")).toBeInTheDocument();
    expect(screen.queryByText("0.0%")).not.toBeInTheDocument();
  });

  it("keeps an unavailable ML slot while preserving an available baseline", () => {
    const unavailable: DroughtContinuationResponse = {
      ...response,
      items: response.items.map((item) => item.region_id === "adm1-ke-43" && item.horizon_days === 30
        ? {
            ...item,
            estimates: item.estimates.map((estimate) => estimate.kind === "experimental_ml_prediction"
              ? { ...estimate, status: "unavailable", probability: undefined, reason_codes: ["model_hash_mismatch"] }
              : estimate)
          }
        : item)
    };
    render(<DroughtContinuation regionId="adm1-ke-43" response={unavailable} />);

    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getByText("model_hash_mismatch")).toBeInTheDocument();
    expect(screen.getByText("86.2%")).toBeInTheDocument();
  });

  it("preserves the same distinction in low-bandwidth mode", () => {
    render(<DroughtContinuation regionId="adm1-ke-43" response={response} variant="lite" />);

    expect(screen.getByRole("columnheader", { name: "Estimate" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Experimental ML prediction" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Historical reference" })).toBeInTheDocument();
    expect(screen.getByText(/Inconclusive validation · Not for operational use/)).toBeInTheDocument();
  });
});
