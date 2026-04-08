import json

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
