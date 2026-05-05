from data_ingestion.okx_public import normalize_okx_inst_id


def test_normalize_okx_inst_id_accepts_legacy_binance_symbols():
    assert normalize_okx_inst_id("BTCUSDT") == "BTC-USDT"
    assert normalize_okx_inst_id("BTCUSDT", swap=True) == "BTC-USDT-SWAP"
    assert normalize_okx_inst_id("BTC-USDT-SWAP") == "BTC-USDT-SWAP"
    assert normalize_okx_inst_id("ETH_USDC") == "ETH-USDC"
