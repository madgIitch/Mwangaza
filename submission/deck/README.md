# Mwangaza pitch deck

Audience: IGAD Hackathon 2026 jury.

Communication job: show that Mwangaza turns homogeneous satellite observations into a
prioritized view of drought episodes that may remain active at the next decision window,
while keeping experimental ML claims bounded and auditable.

## Deliverables

- `mwangaza-pitch-deck.pptx`: editable 16:9 presentation with speaker notes.
- `mwangaza-pitch-deck.pdf`: presentation-ready PDF exported from the PPTX.

## Configured run of show

The target duration is **5:00 (300 seconds)**. Timings are also embedded in the speaker
notes.

| Slide | Narrative job | Time |
| --- | --- | ---: |
| 1 | Open with the decision Mwangaza supports | 0:20 |
| 2 | Explain the gap left by current-risk maps | 0:30 |
| 3 | Show the operating flow | 0:35 |
| 4 | Establish coverage and freshness | 0:35 |
| 5 | Define continuation semantics | 0:45 |
| 6 | Run the three-click demo | 0:55 |
| 7 | Bound the experimental ML evidence | 0:30 |
| 8 | Explain the serving architecture | 0:25 |
| 9 | State limitations and external validation | 0:15 |
| 10 | Ask for a regional analyst pilot | 0:10 |
| **Total** |  | **5:00** |

## Demo story

1. Open `/landing` and state the promise and coverage.
2. Open `/overview?layer=episodes` and show the persistent-episode shortlist across IGAD.
3. Open an active ADM1 from the map and compare 30/60/90/180-day continuation evidence,
   then expand observation dates and freshness.

If the live query is unavailable, reset and use the offline fixture documented by Sprint 47.
The final screenshot fallback is tracked in `assets/pitch/README.md`.

## Evidence provenance

- Coverage, materialization cut and model evidence: `progress/current.md` and
  `progress/impl_sprint-65-probability-ui-integration.md`.
- Continuation semantics and anti-lookahead: `docs/probabilistic-risk.md`.
- API and active/inactive contracts: `docs/contracts.md` and `docs/public-api.md`.
- Product imagery: `frontend/public/landing/hero-northern-kenya.png`.
- Brand mark: `frontend/public/icons/icon.svg`.

The metrics on slide 7 are explicitly labelled experimental. They describe the current
episode-weighted backtest, not observed humanitarian impact or operational performance.

