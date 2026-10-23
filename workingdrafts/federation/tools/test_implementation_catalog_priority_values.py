"""Catalog priorities use nonnegative integer values rather than numeric spelling."""

from decimal import Decimal
import json

from jsonschema import Draft202012Validator
import pytest

from workingdrafts.federation.tools.federation_examples import (
    FederationError, select_profile, validate_profile,
)


@pytest.mark.parametrize("literal", ["0.0", "1e0", "-0.00e5", "100e-2", "9007199254740993.00"])
def test_priority_accepts_integer_values_admitted_by_json_schema(literal):
    Draft202012Validator({"type": "integer", "minimum": 0}).validate(json.loads(literal))
    value = json.loads(literal, parse_float=Decimal, parse_int=Decimal)
    advertisement = {"name": "http", "endpoint": "https://example.test/", "priority": value}
    validate_profile(advertisement)
    assert advertisement["priority"] is value


def test_priority_selection_preserves_exact_values_and_original_tie_order():
    entry = {"federationprofiles": [
        {"name": "http", "endpoint": "https://first.test/", "priority": Decimal("9007199254740993.00")},
        {"name": "http", "endpoint": "https://second.test/", "priority": Decimal("9007199254740992e0")},
    ]}
    assert select_profile(entry, {"http"}) is entry["federationprofiles"][1]
    entry["federationprofiles"][0]["priority"] = Decimal("100e-2")
    entry["federationprofiles"][1]["priority"] = Decimal("1.00")
    assert select_profile(entry, {"http"}) is entry["federationprofiles"][0]


@pytest.mark.parametrize("value", [Decimal("0.5"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity"), True, "0"])
def test_fractional_negative_nonfinite_and_wrong_kind_priorities_remain_invalid(value):
    with pytest.raises(FederationError) as error:
        validate_profile({"name": "http", "endpoint": "https://example.test/", "priority": value})
    assert error.value.code == "invalid_package"
