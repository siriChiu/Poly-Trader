from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "web" / "src"


def _read(relative_path: str) -> str:
    return (WEB_SRC / relative_path).read_text(encoding="utf-8")


def test_app_redirects_backtest_to_lab_and_keeps_current_nav_items():
    source = _read("App.tsx")
    assert "{ to: '/lab', label: '🧪 策略實驗室' }" in source
    assert '<Route path="/backtest" element={<Navigate to="/lab" replace />} />' in source
    assert "📊 儀表板" in source


def test_dashboard_keeps_live_decision_quality_and_execution_guardrails_surfaces():
    source = _read("pages/Dashboard.tsx")
    required_snippets = [
        '<ConfidenceIndicator',
        'decisionQualityScore={confidenceData.decision_quality_score}',
        'expectedDrawdownPenalty={confidenceData.expected_drawdown_penalty}',
        'expectedTimeUnderwater={confidenceData.expected_time_underwater}',
        'allowedLayers={confidenceData.allowed_layers}',
        'const { data: runtimeStatus, refresh: refreshRuntimeStatus } = useApi<RuntimeStatusResponse>("/api/status", 60000);',
        'await refreshRuntimeStatus();',
        'const metadataSmoke = runtimeStatus?.execution_metadata_smoke ?? null;',
        'const lastRejectContext = lastReject?.context ?? null;',
        'const lastRejectRuleLines = formatGuardrailRules(lastRejectContext?.rules);',
        '手動交易即時回饋',
        'normalized qty',
        'normalized price',
        'Metadata smoke 摘要',
        'public metadata contract 驗證通過',
        'smoke freshness',
        'artifact age',
        'stale/unavailable policy 已啟用',
        'getSmokeFreshnessTone',
        'getSmokeFreshnessLabel',
        'getSmokeGovernanceTone',
        'const metadataSmokeFreshness = metadataSmoke?.freshness ?? null;',
        'const metadataSmokeGovernance = metadataSmoke?.governance ?? null;',
        'const metadataSmokeAutoRefresh = metadataSmokeGovernance?.auto_refresh ?? null;',
        'const metadataSmokeBackgroundMonitor = metadataSmokeGovernance?.background_monitor ?? null;',
        'const metadataSmokeExternalMonitor = metadataSmokeGovernance?.external_monitor ?? null;',
        'const externalMonitorInstallContract = metadataSmokeExternalMonitor?.install_contract ?? null;',
        'stale governance',
        'auto refresh',
        'background monitor',
        'external monitor',
        'refresh command:',
        'external monitor command:',
        'preferred host lane:',
        'install status',
        'active lane',
        'install checked at:',
        'install command:',
        'install verify:',
        'crontab verify stdout:',
        'fallback contract:',
        'fallback command:',
        'systemd user timer:',
        'escalation:',
        'Guardrail context 面板',
        'raw → adjusted → delta → rules',
        'const guardrails = executionSummary?.guardrails ?? null;',
        '最近拒單',
        '最近失敗',
        '最近委託',
        'Execution 狀態面板',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_signal_banner_declares_dashboard_as_canonical_execution_route_until_upgraded():
    source = _read("components/SignalBanner.tsx")
    required_snippets = [
        'SignalBanner 目前只提供快捷下單 / 自動交易切換；完整 Execution 狀態面板、Guardrail context 與 stale governance 仍以 Dashboard 為 canonical execution route。',
        'fetch("/api/trade", {',
        'fetch("/api/automation/toggle", {',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_strategy_lab_keeps_decision_quality_summary_surfaces():
    source = _read("pages/StrategyLab.tsx")
    required_snippets = [
        'avg_decision_quality_score',
        'avg_expected_drawdown_penalty',
        'avg_expected_time_underwater',
        'avg_allowed_layers',
        'activeSortSemantics',
        'selectedStrategy?.decision_contract',
        '⚠️ canonical DQ 缺失，暫退回 legacy ROI',
        'Decision Quality',
        'DQ {formatDecimal(activeResult?.avg_decision_quality_score, 3)}',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_candlestick_chart_uses_stable_empty_prop_defaults_to_avoid_render_loops():
    source = _read("components/CandlestickChart.tsx")
    required_snippets = [
        'const EMPTY_TRADE_MARKERS: TradeMarkerInput[] = [];',
        'const EMPTY_EQUITY_CURVE: EquityPoint[] = [];',
        'const EMPTY_SCORE_SERIES: ScorePoint[] = [];',
        'tradeMarkers = EMPTY_TRADE_MARKERS,',
        'equityCurve = EMPTY_EQUITY_CURVE,',
        'scoreSeries = EMPTY_SCORE_SERIES,',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_fetch_api_formats_structured_reject_payloads_for_trade_guardrails():
    source = _read("hooks/useApi.ts")
    required_snippets = [
        'function formatApiErrorDetail(detail: unknown): string {',
        'const code = typeof payload.code === "string" ? payload.code : null;',
        'const message = typeof payload.message === "string" ? payload.message : null;',
        'return [code ? `[${code}]` : null, message].filter(Boolean).join(" ");',
        'throw new Error(formatApiErrorDetail(err.detail ?? err) || `${resp.status}`);',
    ]
    for snippet in required_snippets:
        assert snippet in source
