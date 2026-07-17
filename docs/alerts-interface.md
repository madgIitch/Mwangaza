# Alerts Interface Target

`/alerts` is the operational center for drought alerts. It supports triage, explanation, recommended action, simulated communication and lifecycle traceability.

## Visual Thesis

Dense alert operations console: quiet layout, strong severity signals, table-first scanning and a detail panel that turns one selected alert into evidence and action.

## Content Plan

1. Global shell: persistent brand, routes, data source, last update and freshness.
2. Alerts Center header: title, description, export placeholder and alert-settings placeholder.
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

Current implementation renders both buttons as placeholders because export/settings contracts are not approved yet.

### Filters

Target filters:

- Search.
- Severity.
- Country / region.
- Status.
- Time period.

Current implementation supports search, severity, country and status against loaded alert rows. Time period is visible but not wired to historical API payloads.

### Status Tabs

Target tabs:

- Active.
- Preventive.
- Resolved.
- All alerts.

Current implementation exposes tab controls. Preventive/resolved views show placeholders unless the payload contains matching rows.

### Summary Cards

Cards:

- Active alerts.
- Severe alerts.
- Preventive alerts.
- Resolved this month.
- Notifications queued.

Current implementation computes active/severe from loaded alerts. Preventive, resolved and queued notification totals are simulated placeholders and must be replaced by backend contracts.

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

Rows are derived from loaded active alerts. Stable alert IDs are currently generated from visible fields and must be replaced by backend IDs.

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

Current implementation reuses the selected region profile and visible alert evidence. Narrative text is rule-based and conservative.

### Recommended Early Actions

Uses the selected region profile recommendations. Detailed action metadata such as actor, priority, horizon, evidence and catalog version is pending.

### Notification Outbox

Target state: simulated messages across SMS, email, Telegram and dashboard broadcast, with masked recipients and status.

Current implementation renders a simulated outbox placeholder and explicitly states that no real messages are sent.

### Alert Lifecycle

Target state: timeline of trigger, escalation, actions generated, notifications simulated and active/resolved state.

Current implementation renders a deterministic placeholder timeline from the selected alert period.

### Resolved & Recent

Target state: recently resolved, downgraded or superseded alerts.

Current implementation shows an explicit placeholder because the current public API does not expose resolved-alert history.

## Implemented Now

- `/alerts` route renders Alerts Center as an independent screen.
- Search, severity, country and status filters work on loaded alert payloads.
- Summary cards compute available active/severe counts and mark missing totals as placeholders.
- Selecting a row updates selected alert detail, evidence, region link, PDF link placeholder, recommendations, simulated outbox and lifecycle.
- Low-bandwidth mode still preserves essential alert information in the table-first shell.

## Future Sprint Notes

- Stable backend alert IDs, issued timestamps and last-updated timestamps are tracked by `sprint-58-alerts-center-completion`.
- Export filtered alerts and alert settings are tracked by `sprint-58-alerts-center-completion`.
- Preventive/resolved alert payloads and status history are tracked by `sprint-58-alerts-center-completion`.
- Notification outbox contracts, masking rules and audit actions are tracked by `sprint-58-alerts-center-completion`.
- Alert detail deep-links, full alert pages and region-filter propagation are tracked by `sprint-58-alerts-center-completion`.
- Detailed action metadata and full recommended-action view are tracked by `sprint-58-alerts-center-completion`.
