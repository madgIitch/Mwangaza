# React PWA Migration

Sprint 40 makes the React/Vite app under `frontend/` the canonical dashboard.
The browser consumes public `/api/v1/**` contracts and falls back to demo
fixtures when the API is unavailable in local/demo use. It never calls Earth
Engine directly and does not receive backend secrets.

## Development

```bash
npm install
npm run dev
uvicorn mwangaza.api.app:app --reload
```

`npm run dev` uses demo fixtures by default so the UI can run without backend
noise. To consume the local ASGI API, start the backend and run:

```bash
uvicorn mwangaza.api.app:app --reload
npm run dev:api
```

You can also append `?api=1` to the Vite URL. The Vite dev server proxies
`/api` and `/health` to the local ASGI API. The legacy `streamlit run app.py`
command now shows a migration notice only.

To make the API attempt live GEE data, export credentials and set:

```bash
MWANGAZA_API_DATA_MODE=live
```

Then start `uvicorn mwangaza.api.app:app --reload` and `npm run dev:api`.

## PWA behavior

- `frontend/public/manifest.webmanifest` defines name, short_name, start_url,
  display standalone, theme colors and icon metadata.
- `frontend/public/sw.js` caches only shell/assets. It deliberately bypasses
  `/api/**` and `/health` so sensitive or stale data are not cached
  indefinitely.
- Offline UI shows the latest timestamp available and states that data are not
  live.

## Verification

```bash
npm run lint
npm run typecheck
npm test
npm run build
```
