from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mwangaza.contracts import ContractValidationError
from mwangaza.contracts.drought_continuation import DroughtContinuationProbability

FIXTURE = Path("demo_data/drought-continuation-probabilities.json")


def test_dual_30_day_and_long_reference_contracts_are_valid() -> None:
    values = json.loads(FIXTURE.read_text(encoding="utf-8"))["items"]

    thirty = DroughtContinuationProbability.from_mapping(values[0])
    sixty = DroughtContinuationProbability.from_mapping(values[1])
    inactive = DroughtContinuationProbability.from_mapping(values[-1])

    assert [item.kind for item in thirty.estimates] == [
        "experimental_ml_prediction",
        "historical_reference",
    ]
    assert [item.kind for item in sixty.estimates] == ["historical_reference"]
    assert inactive.status == "not_applicable"


def test_ml_must_remain_inconclusive_non_operational_and_bounded() -> None:
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))["items"][0]

    operational = copy.deepcopy(value)
    operational["estimates"][0]["operational_use"] = True
    relabelled = copy.deepcopy(value)
    relabelled["estimates"][0]["validation"]["status"] = "validated"
    invalid_probability = copy.deepcopy(value)
    invalid_probability["estimates"][0]["probability"] = 1.2

    with pytest.raises(ContractValidationError, match="not operational"):
        DroughtContinuationProbability.from_mapping(operational)
    with pytest.raises(ContractValidationError, match="inconclusive"):
        DroughtContinuationProbability.from_mapping(relabelled)
    with pytest.raises(ContractValidationError, match="between zero and one"):
        DroughtContinuationProbability.from_mapping(invalid_probability)


def test_long_horizon_rejects_ml_and_not_applicable_rejects_probability() -> None:
    values = json.loads(FIXTURE.read_text(encoding="utf-8"))["items"]
    long_value = copy.deepcopy(values[1])
    long_value["estimates"].append(copy.deepcopy(values[0]["estimates"][0]))
    inactive = copy.deepcopy(values[-1])
    inactive["estimates"] = [copy.deepcopy(values[0]["estimates"][1])]

    with pytest.raises(ContractValidationError, match="long horizons"):
        DroughtContinuationProbability.from_mapping(long_value)
    with pytest.raises(ContractValidationError, match="known inactive"):
        DroughtContinuationProbability.from_mapping(inactive)
