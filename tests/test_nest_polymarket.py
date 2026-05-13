import json
import ssl
from urllib.error import URLError

from data_ingestion import nest_polymarket


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()


def test_get_nest_feature_parses_stringified_outcome_lists(monkeypatch):
    payload = [
        {
            "question": "Will bitcoin hit $1m before GTA VI?",
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.4885", "0.5115"]',
        }
    ]

    monkeypatch.setattr(
        nest_polymarket,
        "urlopen",
        lambda req, context=None, timeout=10: _FakeResponse(payload),
    )

    result = nest_polymarket.get_nest_feature()

    assert result["_meta"]["status"] == "ok"
    assert result["nest_raw_prob"] == 0.5115
    assert abs(result["feat_nest_pred"] - 0.0115) < 1e-9


def test_get_nest_feature_classifies_tls_verify_failure_without_insecure_fallback(monkeypatch):
    def _raise_tls_failure(*args, **kwargs):
        raise URLError(ssl.SSLCertVerificationError("certificate verify failed: self-signed certificate"))

    monkeypatch.setattr(nest_polymarket, "urlopen", _raise_tls_failure)

    result = nest_polymarket.get_nest_feature()

    assert result["feat_nest_pred"] is None
    assert result["nest_raw_prob"] is None
    meta = result["_meta"]
    assert meta["status"] == "tls_verify_failed"
    assert meta["source"] == "polymarket_gamma"
    assert meta["trust_policy"] == "tls_verify_required_no_insecure_fallback"
    assert meta["tls_verification"] == "required"
    assert "refusing insecure fallback" in meta["message"]
    assert "Do not disable TLS verification in production" in meta["operator_action"]
