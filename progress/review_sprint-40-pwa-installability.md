# Sprint 40 - React PWA Migration Review

Verdict: review_pending.

Automated checks passed:

- Backend compile lint via `make lint`.
- Backend compile typecheck via `make typecheck`.
- Backend regression suite via `make test`: 212 tests OK.
- Frontend lint via `npm run lint`.
- Frontend typecheck via `npm run typecheck`.
- Frontend tests via `npm test`: 8 tests OK.
- Frontend production build via `npm run build`.
- API live-mode unit coverage via `uv run python -m unittest tests.api.test_public_api`: 7 tests OK.

Human smoke suggested:

- Start `uvicorn mwangaza.api.app:app --reload`.
- For real GEE API mode, export credentials and set `MWANGAZA_API_DATA_MODE=live`, then start `uvicorn mwangaza.api.app:app --reload`.
- Start `npm run dev:api`.
- Open the Vite URL, verify installability in a compatible browser, toggle low-bandwidth mode, switch language, and test offline/devtools network offline behavior.
