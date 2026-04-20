from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "web" / "src"


def _read(relative_path: str) -> str:
    return (WEB_SRC / relative_path).read_text(encoding="utf-8")


def test_strategy_lab_prefers_run_specific_backtest_range_after_initial_override_before_global_range():
    source = _read("pages/StrategyLab.tsx")

    start_override = 'const availableRangeStart = availableRangeOverride?.start'
    start_backtest = '|| backtestRange.start'
    start_requested = '|| resultRange?.requested?.start'
    start_strategy_data = '|| strategyDataRange?.start'

    end_override = 'const availableRangeEnd = availableRangeOverride?.end'
    end_backtest = '|| backtestRange.end'
    end_requested = '|| resultRange?.requested?.end'
    end_strategy_data = '|| strategyDataRange?.end'

    for snippet in [
        start_override,
        start_backtest,
        start_requested,
        start_strategy_data,
        end_override,
        end_backtest,
        end_requested,
        end_strategy_data,
    ]:
        assert snippet in source

    assert source.index(start_override) < source.index(start_backtest) < source.index(start_requested) < source.index(start_strategy_data)
    assert source.index(end_override) < source.index(end_backtest) < source.index(end_requested) < source.index(end_strategy_data)


def test_strategy_lab_does_not_force_chart_inputs_back_to_latest_two_year_range_after_result_sync():
    source = _read("pages/StrategyLab.tsx")

    assert 'strategyDataRange?.start || activeResult?.backtest_range?.effective?.start || activeResult?.chart_context?.start || null' not in source
    assert 'strategyDataRange?.end || activeResult?.backtest_range?.effective?.end || activeResult?.chart_context?.end || null' not in source


def test_strategy_lab_uses_local_datetime_formatter_for_editor_range_strings():
    source = _read("pages/StrategyLab.tsx")

    required_snippets = [
        'const formatDateTimeLocal = (date: Date) => {',
        'return formatDateTimeLocal(date);',
        'return { start: formatDateTimeLocal(floor), end: formatDateTimeLocal(end) };',
        'return { start: formatDateTimeLocal(start), end: formatDateTimeLocal(end) };',
        'setChartStart(availableStart ? formatDateTimeLocal(availableStart) : "");',
        'setChartEnd(formatDateTimeLocal(availableEnd));',
        'setChartStart(nextStart.toISOString().slice(0, 16));',
    ]
    for snippet in required_snippets[:-1]:
        assert snippet in source
    assert required_snippets[-1] not in source


def test_strategy_lab_actual_range_display_falls_back_to_requested_or_definition_range():
    source = _read("pages/StrategyLab.tsx")

    assert 'const activeBacktestDisplayRange = useMemo(() => {' in source
    assert 'activeResult?.backtest_range?.effective?.start' in source
    assert 'activeResult?.backtest_range?.requested?.start' in source
    assert 'selectedStrategy?.definition?.params?.backtest_range' in source
    assert 'activeBacktestDisplayRange.start' in source
    assert 'activeBacktestDisplayRange.end' in source



def test_strategy_lab_stale_warning_compares_editor_inputs_against_requested_range_before_effective_range():
    source = _read("pages/StrategyLab.tsx")

    assert 'const activeBacktestSyncRange = useMemo(() => {' in source
    sync_block = source[source.index('const activeBacktestSyncRange = useMemo(() => {'):source.index('const activeSyncRangeInput = {')]
    assert sync_block.index('activeResult?.backtest_range?.requested?.start') < sync_block.index('activeResult?.backtest_range?.effective?.start')
    assert sync_block.index('activeResult?.backtest_range?.requested?.end') < sync_block.index('activeResult?.backtest_range?.effective?.end')
    assert 'const activeSyncRangeInput = {' in source
    assert 'start: toDateTimeLocalValue(activeBacktestSyncRange.start)' in source
    assert 'end: toDateTimeLocalValue(activeBacktestSyncRange.end)' in source
    assert '&& ((chartStart || "") !== (activeSyncRangeInput.start || "") || (chartEnd || "") !== (activeSyncRangeInput.end || ""))' in source
