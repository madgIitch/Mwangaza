# Analytical Cache

Sprint 15 adds a local analytical cache for already sanitized payloads.

Use `mwangaza.cache.AnalyticalCache` with a `CacheKey` built from region,
indicator, period, source, algorithm version and data type. A valid cache hit
returns the cached entry without invoking the producer.

Entries are serialized as deterministic JSON and published with a temp-file plus
atomic replace. Corrupt files are treated as misses so callers can regenerate the
payload.

TTL is configured per data type. Payloads or metadata containing fields such as
`private_key`, `service_account`, `token`, `secret` or `password` are rejected.
