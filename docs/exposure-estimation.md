# Exposure Estimation

Sprint 30 adds cautious exposure estimates to the dashboard payload.

The public metric name is `potentially_exposed`. It is an estimate of people or
livelihood units that may overlap with a drought-risk area; it is not a measured
impact count.

Every available estimate carries:

- source;
- source year;
- resolution;
- method;
- quality flag;
- `is_demo` marker.

Demo or synthetic data must remain visibly labelled. If sources from different
years are combined, the estimate carries a warning. If no valid dataset exists,
the dashboard shows `No data` and does not invent a value.

Values are rounded or shown as ranges according to the available precision. The
supported methods are `regional_fixture_sum`, `weighted_overlap` and
`not_available`.
