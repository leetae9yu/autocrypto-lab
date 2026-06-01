import pytest

from autocrypto_lab.safety import (
    ReadOnlyAccountAdapter,
    ReadOnlyExchangePolicy,
    SafetyViolation,
    assert_no_forbidden_adapter_methods,
    assert_no_forbidden_config_keys,
)


def test_read_only_policy_allows_private_reads():
    ReadOnlyExchangePolicy(allow_private_read=True, allow_trading=False, minimum_cadence_minutes=60).validate()


def test_policy_rejects_trading_permission():
    with pytest.raises(SafetyViolation, match="forbids trading"):
        ReadOnlyExchangePolicy(allow_trading=True).validate()


def test_policy_rejects_sub_hour_cadence():
    with pytest.raises(SafetyViolation, match="sub-hour"):
        ReadOnlyExchangePolicy(minimum_cadence_minutes=15).validate()


def test_read_only_adapter_exposes_no_forbidden_methods():
    assert_no_forbidden_adapter_methods(ReadOnlyAccountAdapter())


def test_config_keys_reject_order_like_terms():
    with pytest.raises(SafetyViolation):
        assert_no_forbidden_config_keys(["symbol", "create_order"])
