from datetime import date

from autocrypto_lab.etf import default_etf_windows, source_urls


def test_etf_registry_has_required_windows_and_sources():
    windows = default_etf_windows()
    names = {w.name for w in windows}
    assert {"approval_7d", "first_trading_14d", "initial_flow_stabilization_60d"}.issubset(names)
    assert any(w.anchor_date == date(2024, 1, 10) for w in windows)
    assert any(w.anchor_date == date(2024, 1, 11) for w in windows)
    urls = source_urls()
    assert any("sec.gov" in url for url in urls)
    assert any("nasdaq.com" in url for url in urls)
    assert any("cboe.com" in url for url in urls)


def test_windows_have_non_empty_interpretation():
    for window in default_etf_windows():
        assert window.start <= window.anchor_date <= window.end
        assert window.interpretation
        assert window.sources
