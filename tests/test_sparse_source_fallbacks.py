from data_ingestion import fin_etf, fang_options, scales_ssr, nest_polymarket, web_whale


class _BoomResponse:
    def __enter__(self):
        raise OSError("network down")

    def __exit__(self, exc_type, exc, tb):
        return False


def _boom(*args, **kwargs):
    return _BoomResponse()


def _assert_none_fields(payload, *fields):
    for field in fields:
        assert payload[field] is None


def test_sparse_external_sources_return_none_on_fetch_failure(monkeypatch):
    monkeypatch.setattr(fin_etf, "urlopen", _boom)
    monkeypatch.setattr(fang_options, "urlopen", _boom)
    monkeypatch.setattr(scales_ssr, "urlopen", _boom)
    monkeypatch.setattr(nest_polymarket, "urlopen", _boom)
    monkeypatch.setattr(web_whale, "fetch_trades", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("network down")))

    fin = fin_etf.get_fin_feature()
    _assert_none_fields(fin, "feat_fin_netflow", "fin_raw_netflow")
    assert fin.get("_meta", {}).get("status") in {"auth_missing", "fetch_error"}

    fang = fang_options.get_fang_feature()
    _assert_none_fields(fang, "feat_fang_pcr", "feat_fang_skew", "fang_raw_pcr", "fang_iv_skew_raw")

    scales = scales_ssr.get_scales_feature()
    _assert_none_fields(scales, "feat_scales_ssr", "scales_total_stablecap_m")

    nest = nest_polymarket.get_nest_feature()
    _assert_none_fields(nest, "feat_nest_pred", "nest_raw_prob")
    assert nest["_meta"]["status"] == "fetch_error"
    assert nest["_meta"]["trust_policy"] == "tls_verify_required_no_insecure_fallback"

    web = web_whale.get_web_feature()
    _assert_none_fields(web, "feat_web_whale", "feat_web_density", "web_large_trades", "web_sell_ratio")
