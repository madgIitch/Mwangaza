# Mwangaza UI mockup

A dependency-free HTML/CSS/JavaScript reconstruction of the supplied desktop dashboard reference (`1672 × 941`).

## Run

Open `index.html` directly, or serve the folder locally:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Files

- `index.html`: semantic dashboard structure, inline SVG icon sprite and simplified IGAD map.
- `styles.css`: visual tokens and pixel-oriented desktop layout.
- `script.js`: mock regional data, rendering, chart generation, filters, alerts and data export.

## Where Codex should adapt the prototype

Search the code for `CODEX ADAPTATION NOTE`.

The main integration seam is the `regions` object in `script.js`. Replace it with API/GEE output while preserving this conceptual shape:

```js
{
  risk,
  riskLabel,
  ndvi,
  rainfall,
  temperature,
  score,
  quality,
  exposed,
  ndviCurrent,
  ndviBaseline,
  rainCurrent,
  rainBaseline,
  recommendations
}
```

For production:

1. Replace the inline SVG map with Leaflet, Mapbox or `geemap`.
2. Move each major card into its own component.
3. Load translations from proper locale files.
4. Generate reports server-side rather than relying on `window.print()`.
5. Add backend validation and authorization before exporting data.
6. Preserve the footer disclaimer and expose data timestamps/quality metadata.

## Interaction included

- Country and region selection.
- Dynamic metric cards and line charts.
- Alert detail modal.
- Language and low-bandwidth controls.
- CSV/JSON export.
- Browser print-to-PDF report action.
