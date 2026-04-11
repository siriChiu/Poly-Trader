from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "web" / "src"


def _read(relative_path: str) -> str:
    return (WEB_SRC / relative_path).read_text(encoding="utf-8")


def test_app_exposes_real_backtest_route_and_nav_entry():
    source = _read("App.tsx")

    assert "{ to: '/backtest', label: '🔬 回測引擎' }" in source
    assert '<Route path="/backtest" element={<Backtest />} />' in source
    assert 'Navigate to="/lab"' not in source


def test_dashboard_keeps_live_and_backtest_cards_on_canonical_decision_contract():
    source = _read("pages/Dashboard.tsx")

    required_snippets = [
        '<ConfidenceIndicator',
        'decisionQualityScore={confidenceData.decision_quality_score}',
        'expectedDrawdownPenalty={confidenceData.expected_drawdown_penalty}',
        'expectedTimeUnderwater={confidenceData.expected_time_underwater}',
        'allowedLayers={confidenceData.allowed_layers}',
        '主決策以 live decision-quality contract 為準；以下 4H 指標僅作背景解讀。',
        'const canonicalGate = confidenceData?.regime_gate ||',
        'const canonicalDecisionText = confidenceData',
        '若 4H raw 結構與 canonical gate 不一致，應以 decision-quality contract 為主，而不是手寫 bias 規則。',
        '<BacktestSummary',
        'avgDecisionQualityScore={backtestData.avg_decision_quality_score}',
        'avgExpectedDrawdownPenalty={backtestData.avg_expected_drawdown_penalty}',
        'avgExpectedTimeUnderwater={backtestData.avg_expected_time_underwater}',
        'decisionContract={backtestData.decision_contract}',
    ]

    for snippet in required_snippets:
        assert snippet in source


def test_backtest_page_retains_canonical_trade_quality_surface():
    source = _read("pages/Backtest.tsx")

    required_snippets = [
        'decisionContract={result.decision_contract}',
        'result.decision_contract?.target_col || "simulated_pyramid_win"',
        'result.decision_contract?.sort_semantics',
        'Gate / Layers',
        'Entry Quality',
        'trade.regime_gate || "—"',
        'trade.entry_quality_label || "—"',
        'trade.allowed_layers',
    ]

    for snippet in required_snippets:
        assert snippet in source


def test_strategy_lab_compare_and_active_summary_use_decision_quality_fields():
    source = _read("pages/StrategyLab.tsx")

    required_snippets = [
        'const comparisonRows = [',
        'label: "Decision Quality"',
        'label: "預期勝率"',
        'label: "回撤懲罰"',
        'label: "深套時間"',
        'label: "允許層數"',
        'avg_decision_quality_score',
        'avg_expected_drawdown_penalty',
        'avg_expected_time_underwater',
        'avg_allowed_layers',
        'activeSortSemantics',
        'selectedStrategy?.decision_contract',
        '⚠️ canonical DQ 缺失，暫退回 legacy ROI',
        'Legacy execution metrics（僅輔助 / tie-breaker）',
        '若這裡掉回 legacy ROI 文案，代表 decision-quality contract 漏接，應視為回歸而不是正常摘要。',
    ]

    for snippet in required_snippets:
        assert snippet in source
