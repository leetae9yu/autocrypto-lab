import pytest

from autocrypto_lab.safety import (
    ReadOnlyAccountAdapter,
    ReadOnlyExchangePolicy,
    SafetyViolation,
    assert_public_route,
    assert_no_forbidden_adapter_methods,
    assert_no_forbidden_config_keys,
)


def test_read_only_policy_allows_private_reads():
    ReadOnlyExchangePolicy(allow_private_read=True, allow_trading=False, minimum_cadence_minutes=60).validate()


def test_policy_rejects_trading_permission():
    with pytest.raises(SafetyViolation, match="forbids trading"):
        ReadOnlyExchangePolicy(allow_trading=True).validate()


def test_public_only_policy_rejects_private_reads():
    with pytest.raises(SafetyViolation, match="public-only"):
        ReadOnlyExchangePolicy(allow_private_read=True, public_only=True).validate()
    ReadOnlyExchangePolicy(allow_private_read=False, public_only=True, minimum_cadence_minutes=60).validate()


def test_policy_rejects_sub_hour_cadence():
    with pytest.raises(SafetyViolation, match="sub-hour"):
        ReadOnlyExchangePolicy(minimum_cadence_minutes=15).validate()


def test_read_only_adapter_exposes_no_forbidden_methods():
    assert_no_forbidden_adapter_methods(ReadOnlyAccountAdapter())


def test_config_keys_reject_order_like_terms():
    with pytest.raises(SafetyViolation):
        assert_no_forbidden_config_keys(["symbol", "create_order"])


def test_config_keys_reject_private_credentials():
    with pytest.raises(SafetyViolation, match="private"):
        assert_no_forbidden_config_keys(["api_key"])


def test_public_route_rejects_signed_private_or_mutating_routes():
    assert_public_route("GET", "/fapi/v1/klines")
    assert_public_route("GET", "/fapi/v1/klines?symbol=BTCUSDT&interval=1h")
    with pytest.raises(SafetyViolation, match="POST"):
        assert_public_route("POST", "/fapi/v1/klines")
    with pytest.raises(SafetyViolation, match="route"):
        assert_public_route("GET", "/fapi/v1/order")
    with pytest.raises(SafetyViolation, match="approved public endpoints"):
        assert_public_route("GET", "/fapi/v1/userTrades")
    with pytest.raises(SafetyViolation, match="query keys"):
        assert_public_route("GET", "/fapi/v1/klines?signature=abc")
    with pytest.raises(SafetyViolation, match="auth headers"):
        assert_public_route("GET", "/fapi/v1/klines", headers={"X-MBX-APIKEY": "x"})
