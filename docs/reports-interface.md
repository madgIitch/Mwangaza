# Reports Interface Target

`/reports` is the center for generating, reviewing, exporting and tracing executive drought reports across IGAD.

## Visual Thesis

Document operations console: table-first discovery, selected-report validation, preview-centered review and explicit distribution traceability.

## Content Plan

1. Global shell: persistent brand, navigation, source, update time and freshness.
2. Reports Center header: title, description, report templates placeholder and generate-report placeholder.
3. Filter layer: search, region, report type, period and status.
4. Summary layer: generated, scheduled, pending review, downloaded and shared counts.
5. Queue: generated reports table.
6. Detail: selected report metadata, indicators, narrative and actions.
7. Review and distribution: recent exports, report preview, contents, distribution and template metadata.

## Interaction Thesis

- Selecting a report updates detail and preview from already-loaded dashboard/API data.
- Generating reports must use processed snapshots, never arbitrary direct Earth Engine queries from the browser.
- Download/share/export controls are explicit placeholders until file-generation and distribution contracts exist.

## Required Sections

### Header

- Title: `Reports Center`.
- Description: `Generate, review, and export executive drought reports across IGAD`.
- Buttons:
  - Report templates.
  - Generate new report.

Current implementation generates the selected materialized report through the public API. Template management remains disabled as `pending_contract` until authentication and permissions exist.

### Filters

Target filters:

- Search by region, type or ID.
- Region / country.
- Report type.
- Time period.
- Status.

Current implementation filters local generated report rows derived from loaded dashboard data.

### Tabs

Target tabs:

- Generated.
- Scheduled.
- Templates.
- All reports.

Current implementation exposes tab controls. Scheduled/templates show explicit placeholders until backend contracts exist.

### Summary Cards

Cards:

- Generated this month.
- Scheduled reports.
- Pending review.
- Downloaded.
- Shared with partners.

Current implementation computes generated reports from visible rows and marks scheduled/review/download/share counts as placeholders.

### Generated Reports Queue

Table columns:

- Rank.
- Report ID.
- Region / Country.
- Type.
- Period.
- Generated on.
- Status.
- Action.

Current implementation consumes stable backend records for all eight IGAD countries. IDs, timestamps, snapshot IDs, lifecycle status and available formats are backend-owned.

### Selected Report

Shows:

- Report ID.
- Region and report type.
- Status/severity.
- Quality.
- Generated date.
- Based-on snapshot.
- Language.
- Indicator summary.
- Conservative narrative.
- Open preview, download PDF, share and export data actions.

Current implementation downloads non-empty PDF, CSV and JSON artifacts from the selected report record. Sharing remains disabled as `pending_contract`.

### Recent Exports

Target state: audit-style export/distribution history with format, report ID, channel, destination, date and action.

Current implementation renders only real downloadable formats for the selected report and records append-only download audit events. It does not simulate distribution.

### Report Preview

Target state: real PDF viewer with page navigation, zoom, full-screen, print/download and table of contents.

Current implementation renders a faithful HTML preview from the selected snapshot and labels it HTML. The generated PDF is a separate valid downloadable artifact with print support.

### Report Contents

Target contents:

- Overview.
- Current indicators.
- Historical comparison.
- Early action recommendations.
- Methodology.

Current implementation displays this outline as non-scrolling placeholders.

### Distribution

Target state: dashboard availability, email summary, partner download and distribution details.

Current implementation marks email and partner distribution `pending_contract`; it exposes no public delivery mutation.

### Template Used

Target state: immutable template ID/version stored with each generated report.

Current implementation shows `Executive PDF` as a template placeholder.

## Implemented Now

- The Northern Kenya demo exposes a stable simulated report reference keyed by the selected `unit_id`.
- `/reports` route renders Reports Center as an independent screen.
- Search, region, report type and status filters operate on local report rows.
- Selecting a report updates selected detail, preview, recent exports and metadata.
- PDF/CSV/JSON filenames from `DashboardData` are displayed without pretending to download.
- Preview, contents, distribution and template panels degrade explicitly where contracts are missing.

## Pending Contract

- Scheduled reports and report template mutations require authentication and approved roles.
- Email, partner sharing and distribution require approved adapters and permissions.

## Future Scope

- Multi-page PDF viewer controls, partner acknowledgement and schedule execution remain future work.
