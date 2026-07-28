import { useEffect, useMemo, useState } from "react";
import type { ContinuationEstimate, DroughtContinuationItem, DroughtContinuationResponse } from "../types";

const HORIZONS = [30, 60, 90, 180] as const;

interface DroughtContinuationProps {
  response?: DroughtContinuationResponse;
  regionId?: string;
  variant?: "inspector" | "lite";
}

export function DroughtContinuation({ response, regionId, variant = "inspector" }: DroughtContinuationProps): JSX.Element {
  const [horizon, setHorizon] = useState<(typeof HORIZONS)[number]>(30);
  useEffect(() => setHorizon(30), [regionId]);
  const item = useMemo(
    () => response?.items.find((candidate) => candidate.region_id === regionId && candidate.horizon_days === horizon),
    [horizon, regionId, response]
  );

  if (!regionId) {
    return <ContinuationShell variant={variant}><p className="continuation-empty">Select an ADM1 area to check whether an officially active drought episode may continue.</p></ContinuationShell>;
  }
  if (!item) {
    return <ContinuationShell variant={variant}><p className="continuation-empty">No materialized continuation assessment is available for <code>{regionId}</code>.</p></ContinuationShell>;
  }

  return (
    <ContinuationShell variant={variant}>
      <HorizonPicker horizon={horizon} onChange={setHorizon} />
      <div className="continuation-context">
        <span>As of {formatDate(item.as_of)}</span>
        <span>Phase <code>{item.current_phase}</code></span>
        {item.elapsed_days === null ? null : <span>{item.elapsed_days} active days observed</span>}
      </div>
      {item.status === "not_applicable" ? (
        <Abstention item={item} title="No active official drought episode" />
      ) : item.status === "unavailable" ? (
        <Abstention item={item} title="Probability unavailable" />
      ) : variant === "lite" ? (
        <LiteEstimates item={item} />
      ) : (
        <div className="continuation-estimates" data-horizon={horizon}>
          {item.estimates.map((estimate) => <EstimatePanel estimate={estimate} key={estimate.kind} />)}
        </div>
      )}
      <p className="continuation-disclaimer">Estimates whether the same active episode continues through the selected horizon. It does not predict drought onset, exact duration or human impact.</p>
    </ContinuationShell>
  );
}

function ContinuationShell({ children, variant }: { children: React.ReactNode; variant: "inspector" | "lite" }): JSX.Element {
  return (
    <section className="drought-continuation" data-variant={variant} aria-label="Drought continuation">
      <header>
        <div><p className="eyebrow">Same active episode</p><h3>Drought continuation</h3></div>
        <span className="continuation-target">30–180 days</span>
      </header>
      {children}
    </section>
  );
}

function HorizonPicker({ horizon, onChange }: { horizon: number; onChange: (value: 30 | 60 | 90 | 180) => void }): JSX.Element {
  return (
    <div className="continuation-horizons" role="group" aria-label="Continuation horizon">
      {HORIZONS.map((value) => (
        <button type="button" data-active={horizon === value ? "true" : "false"} key={value} onClick={() => onChange(value)}>{value} days</button>
      ))}
    </div>
  );
}

function EstimatePanel({ estimate }: { estimate: ContinuationEstimate }): JSX.Element {
  const ml = estimate.kind === "experimental_ml_prediction";
  return (
    <article className="continuation-estimate" data-kind={estimate.kind} data-status={estimate.status}>
      <div className="estimate-heading">
        <span>{ml ? "Experimental ML prediction" : "Historical reference"}</span>
        <small>{ml ? "Inconclusive validation" : "Descriptive baseline"}</small>
      </div>
      {estimate.status === "available" && estimate.probability !== undefined ? (
        <strong className="continuation-probability">{formatProbability(estimate.probability)}</strong>
      ) : (
        <strong className="continuation-unavailable">Unavailable</strong>
      )}
      <dl>
        <div><dt>Method</dt><dd><code>{estimate.model}</code></dd></div>
        <div><dt>Quality</dt><dd>{String(estimate.quality.status ?? "unknown")}</dd></div>
        {ml ? <><div><dt>Skill</dt><dd>{formatSkill(estimate.validation.episode_weighted_brier_skill_score)}</dd></div><div><dt>Use</dt><dd>Not for operational use</dd></div></> : null}
      </dl>
      {estimate.reason_codes.length ? <ReasonCodes codes={estimate.reason_codes} /> : null}
      {ml ? (estimate.status === "available" ? <MlEvidence estimate={estimate} /> : null) : <BaselineEvidence estimate={estimate} />}
    </article>
  );
}

function MlEvidence({ estimate }: { estimate: ContinuationEstimate }): JSX.Element {
  const interval = estimate.validation.bootstrap_delta_brier_ci95;
  return (
    <details>
      <summary>Associations and validation</summary>
      {Array.isArray(interval) && interval.length === 2 ? <p>95% interval for Brier difference: [{formatMetric(interval[0])}, {formatMetric(interval[1])}]</p> : null}
      <ul>{estimate.drivers.slice(0, 3).map((driver) => <li key={driver.feature}><code>{driver.feature}</code> · {humanDirection(driver.direction)}. Association, not a causal effect.</li>)}</ul>
    </details>
  );
}

function BaselineEvidence({ estimate }: { estimate: ContinuationEstimate }): JSX.Element {
  const phase = estimate.evidence?.current_phase;
  const elapsed = estimate.evidence?.elapsed_days;
  if (phase === undefined && elapsed === undefined) return <p className="estimate-evidence">Historical frequency for comparable phase and elapsed duration.</p>;
  return <p className="estimate-evidence">Descriptive evidence: phase <code>{String(phase)}</code>{elapsed === undefined ? "" : ` after ${String(elapsed)} observed days`}.</p>;
}

function LiteEstimates({ item }: { item: DroughtContinuationItem }): JSX.Element {
  return (
    <table className="continuation-table">
      <thead><tr><th>Estimate</th><th>Probability</th><th>Method</th><th>Validation / quality</th></tr></thead>
      <tbody>{item.estimates.map((estimate) => (
        <tr key={estimate.kind}>
          <th scope="row">{estimate.kind === "experimental_ml_prediction" ? "Experimental ML prediction" : "Historical reference"}</th>
          <td>{estimate.status === "available" && estimate.probability !== undefined ? formatProbability(estimate.probability) : "Unavailable"}</td>
          <td><code>{estimate.model}</code></td>
          <td>{estimate.kind === "experimental_ml_prediction" ? "Inconclusive validation · Not for operational use" : `Historical reference · ${String(estimate.quality.status ?? "unknown")}`}</td>
        </tr>
      ))}</tbody>
    </table>
  );
}

function Abstention({ item, title }: { item: DroughtContinuationItem; title: string }): JSX.Element {
  return <div className="continuation-abstention"><strong>{title}</strong><p>{item.reason_codes.length ? item.reason_codes.join(" · ") : "No percentage is shown without an applicable, supported estimate."}</p></div>;
}

function ReasonCodes({ codes }: { codes: string[] }): JSX.Element {
  return <p className="continuation-reasons">{codes.map((code) => <code key={code}>{code}</code>)}</p>;
}

function formatProbability(value: number): string {
  return new Intl.NumberFormat("en", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value);
}

function formatSkill(value: unknown): string {
  return typeof value === "number" ? `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}% BSS` : "Inconclusive";
}

function formatMetric(value: unknown): string {
  return typeof value === "number" ? value.toFixed(4) : "unknown";
}

function formatDate(value: string): string {
  return value.slice(0, 10);
}

function humanDirection(direction: string): string {
  return direction === "higher_continuation_probability" ? "associated with higher continuation probability" : direction === "lower_continuation_probability" ? "associated with lower continuation probability" : direction.replaceAll("_", " ");
}
