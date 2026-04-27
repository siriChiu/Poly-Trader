import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "backfill_4h_distance.py"
spec = importlib.util.spec_from_file_location("backfill_4h_distance_test_module", SCRIPT_PATH)
backfill_4h_distance = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(backfill_4h_distance)


def test_resolve_4h_fetch_start_uses_earliest_feature_timestamp_minus_warmup():
    start = backfill_4h_distance._resolve_4h_fetch_start([
        "2024-04-21 13:00:00.000000",
        "2024-04-21 14:00:00.000000",
    ], warmup_days=400)

    assert start.strftime("%Y-%m-%d %H:%M:%S") == "2023-03-18 13:00:00"
