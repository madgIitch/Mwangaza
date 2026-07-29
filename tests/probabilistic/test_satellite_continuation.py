from __future__ import annotations

from dataclasses import asdict

import pytest

from mwangaza.contracts.drought_continuation import DroughtContinuationProbability
from mwangaza.probabilistic.satellite_continuation import (
    SatelliteConditionConfig,
    SatelliteContinuationError,
    SatelliteServingBundle,
    SatelliteStatePoint,
    build_satellite_samples,
    derive_satellite_states,
    materialize_satellite_snapshot,
)

HASH = "sha256:" + "a" * 64


def test_state_is_homogeneous_hysteretic_and_targets_use_future_only_for_scoring() -> None:
    config = _config()
    payloads = [
        _payload("2020-01-20", spi=0.0, anomaly=0.0, persistence=0, slope=0.1, soil=0.5),
        _payload("2021-01-10", spi=-1.2, anomaly=-0.04, persistence=2, slope=-0.1, soil=0.1),
        _payload("2021-01-20", spi=-1.1, anomaly=-0.03, persistence=3, slope=-0.1, soil=0.1),
        _payload("2021-01-31", spi=0.2, anomaly=0.01, persistence=0, slope=0.1, soil=0.7),
        _payload("2021-02-10", spi=0.2, anomaly=0.01, persistence=0, slope=0.1, soil=0.7),
        _payload("2021-02-20", spi=0.2, anomaly=0.01, persistence=0, slope=0.1, soil=0.7),
    ]

    states = derive_satellite_states(payloads, config, expected_region_ids=("adm1-ke-01",))
    assert [point.active for point in states] == [False, True, True, False, False]
    assert states[1].episode_start == "2021-01-10"
    assert states[1].signal_freshness["spi_3m"]["observed_at"] == "2021-01-20T00:00:00Z"
    samples = build_satellite_samples(states)
    assert samples[0].period_end == "2021-01-20"
    assert samples[0].targets[30] == 0


def test_future_available_signal_is_rejected() -> None:
    config = _config()
    payload = _payload(
        "2021-01-10", spi=-1.2, anomaly=-0.04, persistence=2, slope=-0.1, soil=0.1
    )
    payload["signals"]["spi_3m"]["available_at"] = "2021-02-01T00:00:00Z"

    with pytest.raises(SatelliteContinuationError, match="future feature leakage"):
        derive_satellite_states(
            (_payload("2020-01-20", spi=0.0, anomaly=0.0, persistence=0, slope=0.1, soil=0.5), payload),
            config,
            expected_region_ids=("adm1-ke-01",),
        )


def test_materialization_requires_and_emits_121_by_four() -> None:
    region_ids = tuple(f"adm1-x-{index:03d}" for index in range(121))
    states = tuple(_state(region_id, active=index == 0) for index, region_id in enumerate(region_ids))
    bundle = _bundle()

    snapshot = materialize_satellite_snapshot(
        bundle,
        states,
        generated_at="2026-07-29T00:00:00Z",
        bundle_sha256=HASH,
        expected_region_ids=region_ids,
    )

    assert snapshot["analysis_as_of"] == "2026-07-20"
    assert snapshot["coverage"] == {
        "adm1_count": 121,
        "kenya_adm1_count": 0,
        "result_count": 484,
    }
    assert len(snapshot["items"]) == 484
    active = [item for item in snapshot["items"] if item["current_drought_status"] == "active"]
    assert len(active) == 4
    assert all(item["status"] == "available" for item in active)
    assert all(DroughtContinuationProbability.from_mapping(item) for item in snapshot["items"])


def _config() -> SatelliteConditionConfig:
    return SatelliteConditionConfig(
        reference_end="2020-12-31",
        state_start="2021-01-01",
        soil_reference_minimum=1,
        max_signal_age_days={name: 90 for name in (
            "spi_3m", "spei_3m", "ndvi_anomaly",
            "ndvi_decline_persistence_dekads", "ndvi_slope_3dekad",
            "soil_moisture_rootzone",
        )},
    )


def _payload(
    period_end: str,
    *,
    spi: float,
    anomaly: float,
    persistence: int,
    slope: float,
    soil: float,
) -> dict[str, object]:
    as_of = f"{period_end}T00:00:00Z"
    def signal(value: float | int) -> dict[str, object]:
        return {
            "value": value,
            "quality": "observed",
            "observed_at": as_of,
            "available_at": as_of,
            "age_days": 0,
            "source_collection": "test",
            "source_version": "test-v1",
            "missing_reason": None,
        }
    return {
        "region_id": "adm1-ke-01",
        "parent_iso3": "KEN",
        "period_end": period_end,
        "as_of": as_of,
        "signals": {
            "spi_3m": signal(spi),
            "spei_3m": signal(spi),
            "ndvi_anomaly": signal(anomaly),
            "ndvi_decline_persistence_dekads": signal(persistence),
            "ndvi_slope_3dekad": signal(slope),
            "soil_moisture_rootzone": signal(soil),
        },
    }


def _state(region_id: str, *, active: bool) -> SatelliteStatePoint:
    return SatelliteStatePoint(
        region_id=region_id,
        parent_iso3="TST",
        period_end="2026-07-20",
        as_of="2026-07-21T00:00:00Z",
        raw_condition=active,
        active=active,
        episode_id="episode" if active else None,
        episode_start="2026-07-10" if active else None,
        elapsed_days=10 if active else None,
        trend="persistent" if active else "stable",
        family_states={"meteorological": active, "vegetation": active, "soil_moisture": active},
        signal_freshness={
            "spi_3m": {
                "quality": "derived", "observed_at": "2026-06-30T00:00:00Z",
                "available_at": "2026-07-21T00:00:00Z", "age_days": 21,
            }
        },
        features={"elapsed_days": 10.0, "spi_3m": -1.0},
    )


def _bundle() -> SatelliteServingBundle:
    config = _config()
    baselines = {
        str(horizon): {
            "global": {"probability": probability, "known_count": 100, "episode_count": 20},
            "elapsed_bins": {},
        }
        for horizon, probability in ((30, 0.8), (60, 0.6), (90, 0.4), (180, 0.2))
    }
    return SatelliteServingBundle(
        estimator=None,
        baselines=baselines,
        validation={
            "status": "inconclusive",
            "qualified_for_experimental_serving": False,
            "reason_codes": ["satellite_ml_gate_not_met"],
            "bootstrap_delta_brier_ci95": [-0.01, 0.01],
        },
        input_hashes={"features": HASH},
        numeric_ranges={"elapsed_days": (0.0, 100.0), "spi_3m": (-3.0, 3.0)},
        training_regions=("adm1-x-000",),
        training_row_count=100,
        trained_through="2023-12-31",
        config=asdict(config),
        run_hash=HASH,
    )
