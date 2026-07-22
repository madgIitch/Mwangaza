# Alerts Interface Target

`/alerts` is the operational center for drought alerts. It supports triage, explanation, recommended action, simulated communication and lifecycle traceability.

## Visual Thesis

Dense alert operations console: quiet layout, strong severity signals, table-first scanning and a detail panel that turns one selected alert into evidence and action.

## Content Plan

1. Global shell: persistent brand, routes, data source, last update and freshness.
2. Alerts Center header: title, description, filtered exports and an explicitly unavailable settings control.
3. Filter layer: search, severity, country/region, status and period.
4. Summary layer: active, severe, preventive, resolved and notification counts.
5. Work queue: active alerts table with row selection.
6. Detail layer: selected alert metadata, indicators, narrative and actions.
7. Communication and traceability: simulated notification outbox, lifecycle and resolved/recent history.

## Interaction Thesis

- Selecting an alert updates the detail, recommended actions, outbox and lifecycle without fetching Earth Engine from the browser.
- Search and filters operate on the already-loaded API/cache payload.
- Alert routes are independent page routes; `/alerts` must not be a hash section inside Overview.

## Required Sections

### Header

- Title: `Alerts Center`.
- Description: `Track active, preventive, and resolved drought alerts across IGAD`.
- Buttons:
  - Export.
  - Alert settings.

CSV, JSON and PDF exports preserve the active filters. Alert settings remain disabled because authentication and mutation permissions are outside the public prototype.

### Filters

Target filters:

- Search.
- Severity.
- Country / region.
- Status.
- Time period.

Search, severity, country, status and time period operate on loaded rows, persist in the URL and are also accepted by the alerts API and export endpoints.

### Status Tabs

Target tabs:

- Active.
- Preventive.
- Resolved.
- All alerts.

Tabs synchronize with the status filter. Empty preventive or resolved views state that the repository has no matching history rather than inventing rows.

### Status Band

Compact counters:

- Active alerts.
- Severe alerts.
- Preventive alerts.
- Resolved this month.
- Simulated notifications.

All counters are computed from the alert payload. Notifications are always marked as simulated and never imply real delivery.

### Active Alerts Queue

Table columns:

- Row selector.
- Rank.
- Severity.
- Region / Country.
- Alert type.
- Trigger / evidence summary.
- Date issued.
- Status.
- Action.

Rows are derived from loaded active and historical alerts. Persisted repository rows use stable backend IDs; demo rows use a deterministic fallback ID.

### Selected Alert

Shows:

- Stable alert ID.
- Region and severity.
- Title/description.
- Quality.
- Issued and last updated.
- Indicator cards from the selected region profile.
- Narrative explanation.
- `View full region analysis`.
- `Generate PDF report`.

The selected alert is deep-linkable at `/alerts/{alert_id}`. It reuses the selected region profile and visible alert evidence; narrative text is rule-based and conservative.

### Recommended Early Actions

Uses the backend recommendation payload when present, including suggested actor, urgency, horizon, evidence and catalog version. A conservative profile recommendation is the fallback.

### Notification Outbox

Target state: simulated messages across SMS, email, Telegram and dashboard broadcast, with masked recipients and status.

The API exposes deterministic SMS, email, Telegram and dashboard simulations. Recipients are masked, every row carries `is_simulated=true`, and no external send occurs.

### Alert Lifecycle

Target state: timeline of trigger, escalation, actions generated, notifications simulated and active/resolved state.

Persisted lifecycle events are returned by the backend. A conservative triggered/current-status pair is used only for fixture rows without repository history.

### Resolved & Recent

Target state: recently resolved, downgraded or superseded alerts.

The repository query includes resolved and superseded history. If no rows exist, the interface exposes an honest empty state.

## Implemented Now

- `/alerts` route renders Alerts Center as an independent screen.
- Search, severity, country and status filters work on loaded alert payloads.
- The compact status band computes active, severe, preventive, resolved and simulated-notification totals.
- Selecting a row updates detail, evidence, region link, filtered PDF link, recommendations, simulated outbox and lifecycle.
- Low-bandwidth mode still preserves essential alert information in the table-first shell.

## Public safety boundary

- Alert reads and filtered downloads are public prototype capabilities.
- No endpoint sends a notification.
- Alert settings and lifecycle mutations remain unavailable until institutional authentication and authorization exist.
