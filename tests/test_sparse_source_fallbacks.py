from data_ingestion import fin_etf, fang_options, scales_ssr, nest_polymarket, web_whale


class _BoomResponse:
    def __enter__(self):
        raise OSError("network down")

    def __exit__(self, exc_type, exc, tb):
        return False


def _boom(*args, **kwargs):
    return _BoomResponse()


def test_sparse_external_sources_return_none_on_fetch_failure(monkeypatch):
    monkeypatch.setattr(fin_etf, "urlopen", _boom)
    monkeypatch.setattr(fang_options, "urlopen", _boom)
    monkeypatch.setattr(scales_ssr, "urlopen", _boom)
    monkeypatch.setattr(nest_polymarket, "urlopen", _boom)
    monkeypatch.setattr(web_whale, "urlopen", _boom)

    assert fin_etf.get_fin_feature() == {
        "feat_fin_netflow": None,
        "fin_raw_netflow": None,
    }
    assert fang_options.get_fang_feature() == {
        "feat_fang_pcr": None,
        "feat_fang_skew": None,
        "fang_raw_pcr": None,
        "fang_iv_skew_raw": None,
    }
    assert scales_ssr.get_scales_feature() == {
        "feat_scales_ssr": None,
        "scales_total_stablecap_m": None,
    }
    assert nest_polymarket.get_nest_feature() == {
        "feat_nest_pred": None,
        "nest_raw_prob": None,
    }
    assert web_whale.get_web_feature() == {
        "feat_web_whale": None,
        "feat_web_density": None,
        "web_large_trades": None,
        "web_sell_ratio": None,
    }
