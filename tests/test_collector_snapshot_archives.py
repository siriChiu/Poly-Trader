import json

from data_ingestion import collector


BASE_BODY = {"raw_roc": 123.0, "body_label": "trend", "oi_roc": 0.12}
BASE_TONGUE = {"feat_tongue_sentiment": 0.3, "volatility": 0.2, "fear_greed_index": 44}
BASE_NOSE = {"funding_rate_raw": 0.001}
BASE_EYE = {"current_price": 68000.0, "volume": 12345.0, "feat_eye_up": 0.11}
BASE_EAR = {"prob": 0.62}
BASE_DERIV = {"lsr_ratio": 1.1, "gsr_ratio": 1.0, "taker_ratio": 0.98, "oi_value": 123456.0}
BASE_MACRO = {"vix_value": 18.2, "dxy_value": 101.3, "nq_value": 17890.0, "nq_history": [1, 2, 3, 4]}


def _patch_sources(monkeypatch, *, claw=None, fang=None, fin=None, web=None, scales=None, nest=None):
    monkeypatch.setattr(collector, "get_body_feature", lambda: BASE_BODY)
    monkeypatch.setattr(collector, "get_tongue_feature", lambda: BASE_TONGUE)
    monkeypatch.setattr(collector, "get_nose_feature", lambda: BASE_NOSE)
    monkeypatch.setattr(collector, "get_eye_feature", lambda: BASE_EYE)
    monkeypatch.setattr(collector, "get_ear_feature", lambda: BASE_EAR)
    monkeypatch.setattr(collector, "get_derivatives_features", lambda symbol: BASE_DERIV)
    monkeypatch.setattr(collector, "fetch_macro_latest", lambda: BASE_MACRO)
    monkeypatch.setattr(collector, "compute_nq_features", lambda history: {"feat_nq_return_1h": -0.01, "feat_nq_return_24h": -0.02})
    monkeypatch.setattr(collector, "get_claw_feature", lambda: claw if claw is not None else {
        "feat_claw": 0.2,
        "feat_claw_intensity": 0.4,
        "claw_long_liq": 10.0,
        "claw_short_liq": 5.0,
        "claw_ratio": 2.0,
    })
    monkeypatch.setattr(collector, "get_fang_feature", lambda: fang if fang is not None else {
        "feat_fang_pcr": 0.1,
        "feat_fang_skew": 0.05,
        "fang_raw_pcr": 1.25,
        "fang_iv_skew_raw": 0.5,
    })
    monkeypatch.setattr(collector, "get_fin_feature", lambda: fin if fin is not None else {
        "feat_fin_netflow": -0.2,
        "fin_raw_netflow": -123456789.0,
    })
    monkeypatch.setattr(collector, "get_web_feature", lambda: web if web is not None else {
        "feat_web_whale": -0.3,
        "feat_web_density": 0.8,
        "web_large_trades": 77,
        "web_sell_ratio": 0.61,
    })
    monkeypatch.setattr(collector, "get_scales_feature", lambda: scales if scales is not None else {
        "feat_scales_ssr": 0.04,
        "scales_total_stablecap_m": 123456.0,
    })
    monkeypatch.setattr(collector, "get_nest_feature", lambda: nest if nest is not None else {
        "feat_nest_pred": 0.12,
        "nest_raw_prob": 0.62,
    })


def test_collect_all_senses_archives_sparse_source_snapshots_as_json(monkeypatch):
    _patch_sources(monkeypatch)

    record = collector.collect_all_senses("BTCUSDT")

    assert record.claw_liq_total == 15.0

    by_subtype = {event.subtype: event for event in record._raw_events}
    for subtype in [
        "claw_snapshot",
        "fang_snapshot",
        "fin_snapshot",
        "web_snapshot",
        "scales_snapshot",
        "nest_snapshot",
        "macro_snapshot",
    ]:
        assert subtype in by_subtype

    claw_payload = json.loads(by_subtype["claw_snapshot"].payload_json)
    assert claw_payload["status"] == "ok"
    assert claw_payload["snapshot"]["claw_ratio"] == 2.0
    assert by_subtype["claw_snapshot"].value == 2.0

    price_payload = json.loads(by_subtype["price"].payload_json)
    assert price_payload["current_price"] == 68000.0
    assert by_subtype["macro_snapshot"].value == 18.2


def test_collect_all_senses_preserves_missing_sparse_source_values(monkeypatch):
    _patch_sources(
        monkeypatch,
        claw={
            "feat_claw": None,
            "feat_claw_intensity": None,
            "claw_long_liq": None,
            "claw_short_liq": None,
            "claw_ratio": None,
        },
        fang={
            "feat_fang_pcr": None,
            "feat_fang_skew": None,
            "fang_raw_pcr": None,
            "fang_iv_skew_raw": None,
        },
    )

    record = collector.collect_all_senses("BTCUSDT")

    assert record.claw_liq_total is None

    by_subtype = {event.subtype: event for event in record._raw_events}
    claw_payload = json.loads(by_subtype["claw_snapshot"].payload_json)
    fang_payload = json.loads(by_subtype["fang_snapshot"].payload_json)

    assert by_subtype["claw_snapshot"].quality_score == 0.0
    assert by_subtype["claw_snapshot"].value is None
    assert claw_payload["status"] == "missing"
    assert fang_payload["status"] == "missing"
