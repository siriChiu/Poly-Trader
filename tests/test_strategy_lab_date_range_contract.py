from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "web" / "src"


def _read(relative_path: str) -> str:
    return (WEB_SRC / relative_path).read_text(encoding="utf-8")


def test_strategy_lab_prefers_latest_strategy_data_range_over_saved_strategy_snapshot_dates():
    source = _read("pages/StrategyLab.tsx")
    start_anchor = 'const availableRangeStart = strategyDataRange?.start'
    end_anchor = 'const availableRangeEnd = strategyDataRange?.end'
    stale_start = 'backtestRange.start'
    stale_end = 'backtestRange.end'

    assert start_anchor in source
    assert end_anchor in source
    assert stale_start in source
    assert stale_end in source
    assert source.index(start_anchor) < source.index(stale_start)
    assert source.index(end_anchor) < source.index(stale_end)


def test_strategy_lab_actual_range_display_falls_back_to_requested_or_definition_range():
    source = _read("pages/StrategyLab.tsx")

    assert 'const activeBacktestDisplayRange = useMemo(() => {' in source
    assert 'activeResult?.backtest_range?.effective?.start' in source
    assert 'activeResult?.backtest_range?.requested?.start' in source
    assert 'selectedStrategy?.definition?.params?.backtest_range' in source
    assert 'activeBacktestDisplayRange.start' in source
    assert 'activeBacktestDisplayRange.end' in source
