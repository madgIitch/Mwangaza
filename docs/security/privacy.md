# Privacy Baseline

Mwangaza processes regional environmental indicators and administrative-area summaries. The prototype does not request or persist names, telephone numbers, personal identifiers, device geolocation or household/community coordinates.

Operational rate limiting uses an in-memory client key only for the active process window. It is not written to SQLite, cache, logs or metrics. Observability exposes aggregate counts rather than client-level records.

The public admin panel is a hackathon demonstration surface. Its configuration history records the generic actor `public-admin`, not a person's identity. Production use requires a separate privacy review together with institutional authentication and retention policies.
