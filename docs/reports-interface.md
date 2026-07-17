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

Current implementation renders both controls as placeholders.

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

Current implementation derives deterministic rows from current regions and filenames. Stable backend report records are pending.

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

Current implementation links actions to existing routes/placeholders and does not claim a real file download.

### Recent Exports

Target state: audit-style export/distribution history with format, report ID, channel, destination, date and action.

Current implementation renders deterministic export rows from visible filenames and labels distribution as local/simulated where appropriate.

### Report Preview

Target state: real PDF viewer with page navigation, zoom, full-screen, print/download and table of contents.

Current implementation renders a structured preview from the selected dashboard snapshot. Viewer controls are placeholders.

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

Current implementation marks email/partner distribution as simulated/pending.

### Template Used

Target state: immutable template ID/version stored with each generated report.

Current implementation shows `Executive PDF` as a template placeholder.

## Implemented Now

- `/reports` route renders Reports Center as an independent screen.
- Search, region, report type and status filters operate on local report rows.
- Selecting a report updates selected detail, preview, recent exports and metadata.
- PDF/CSV/JSON filenames from `DashboardData` are displayed without pretending to download.
- Preview, contents, distribution and template panels degrade explicitly where contracts are missing.

## Future Sprint Notes

- Stable report records, IDs, generated timestamps, template IDs and immutable language metadata are tracked by `sprint-59-reports-center-completion`.
- Real PDF generation, preview, download and print controls are tracked by `sprint-59-reports-center-completion`.
- CSV/JSON export endpoints and filtered export history are tracked by `sprint-59-reports-center-completion`.
- Scheduled reports and report template management are tracked by `sprint-59-reports-center-completion`.
- Share/distribution channels, masking, audit trail and partner download state are tracked by `sprint-59-reports-center-completion`.
