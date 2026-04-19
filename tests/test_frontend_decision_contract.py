from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "web" / "src"


def _read(relative_path: str) -> str:
    return (WEB_SRC / relative_path).read_text(encoding="utf-8")


def test_app_redirects_backtest_to_lab_and_keeps_current_nav_items():
    source = _read("App.tsx")
    required_snippets = [
        "React.lazy(() => import('./pages/Dashboard'))",
        "React.lazy(() => import('./pages/Senses'))",
        "React.lazy(() => import('./pages/StrategyLab'))",
        "React.lazy(() => import('./pages/ExecutionConsole'))",
        "React.lazy(() => import('./pages/ExecutionStatus'))",
        "<React.Suspense",
        "頁面載入中",
        "⚡ Bot 營運",
        "🩺 執行狀態",
        "🧪 策略實驗室",
        '<Route path="/execution" element={<ExecutionConsole />} />',
        '<Route path="/execution/status" element={<ExecutionStatus />} />',
        '<Route path="/backtest" element={<Navigate to="/lab" replace />} />',
        "📊 儀表板",
    ]
    for snippet in required_snippets:
        assert snippet in source

def test_execution_status_route_and_page_contract():
    app_source = _read("App.tsx")
    page_source = _read("pages/ExecutionStatus.tsx")
    assert "React.lazy(() => import('./pages/ExecutionStatus'))" in app_source
    assert '<Route path="/execution/status" element={<ExecutionStatus />} />' in app_source
    required_snippets = [
        'const { data: runtimeStatus, loading, error, refresh } = useApi<ExecutionStatusResponse>("/api/status", 60000);',
        'const runtimeStatusPending = loading && !runtimeStatus && !error;',
        'const currentLiveBlocker = liveRuntimeTruth?.deployment_blocker || null;',
        'const currentLiveBlockerLabel = runtimeStatusPending ? "同步中" : (currentLiveBlocker || "unavailable");',
        'const primaryRuntimeMessage = runtimeStatusPending',
        'const metadataFreshnessLabel = runtimeStatusPending',
        'const reconciliationStatusLabel = runtimeStatusPending ? "同步中" : (executionReconciliation?.status || "unavailable");',
        'const venueBlockersLabel = runtimeStatusPending',
        '執行狀態 / Diagnostics',
        '先看 blocker，再決定是否介入',
        '回到 Bot 營運',
        '可部署',
        '資料新鮮度',
        '對帳狀態',
        '詳細對帳與恢復',
        'Venue lanes',
        'Timeline',
        '營運入口',
        'operations {operationsSurface?.label || "Bot 營運"}',
        'diagnostics {diagnosticsSurface?.label || "Execution 狀態"}',
        'detail={`blocker ${currentLiveBlockerLabel} · ${primaryRuntimeMessage} · scope ${executionSurfaceContract?.readiness_scope || "runtime_governance_visibility_only"}`}',
        'venue blockers {venueBlockersLabel}',
    ]
    for snippet in required_snippets:
        assert snippet in page_source


def test_execution_console_consumes_runtime_status_and_uses_exchange_like_layout():
    source = _read("pages/ExecutionConsole.tsx")
    required_snippets = [
        'const { data: runtimeStatus, loading, error, refresh: refreshRuntimeStatus } = useApi<ExecutionConsoleRuntimeStatusResponse>("/api/status", 60000);',
        'const { data: executionOverview, loading: overviewLoading, error: overviewError, refresh: refreshExecutionOverview } = useApi<ExecutionOverviewResponse>("/api/execution/overview", 60000);',
        'const { data: executionRuns, loading: runsLoading, error: runsError, refresh: refreshExecutionRuns } = useApi<ExecutionRunsResponse>("/api/execution/runs", 60000);',
        'function formatSignedNumber(value: number | null | undefined, digits = 2): string {',
        'function humanizeExecutionReason(value?: string | null): string {',
        '交易所憑證尚未驗證。',
        '目前結構 bucket 尚未通過可部署條件。',
        '目前決策品質不足，暫不建議進場。',
        'const totalUnrealizedPnl = runLedgerPreviews.reduce(',
        'const totalCapitalInUse = runLedgerPreviews.reduce(',
        'const profitableRuns = executionRunRecords.filter(',
        'const rawPrimaryBlockedReason = liveRuntimeTruth?.deployment_blocker_reason',
        'const blockedReasonSummary = Array.from(new Set([',
        'const deploymentStatusDetail = executionSurfaceContract?.live_ready',
        'liveRuntimeTruth?.runtime_closure_summary || liveRuntimeTruth?.deployment_blocker_reason || primaryBlockedReason',
        'Bot 營運 / Live Ops',
        '先看我的 Bot、資金使用與盈虧預覽',
        '選策略',
        '執行狀態',
        '共享盈虧預覽',
        '資金使用中',
        '可部署資金',
        '運行中 Bot',
        '我的 Bot',
        '運行中',
        '應急手動操作',
        '部署狀態',
        '帳戶與成交',
        '共享預覽',
        '先解除 blocker，再做操作',
        '查看阻塞原因',
        'fetchApi<any>("/api/trade", {',
        'fetchApi<{ automation?: boolean; message?: string }>("/api/automation/toggle", {',
        '買入 0.001 BTC',
        '減碼 0.001 BTC',
        '切到手動模式',
        '切到自動模式',
        '啟動 / 恢復',
        '恢復',
        '暫停',
        '停止',
        'href="/execution/status"',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert 'Bot 市集' not in source
    assert '進階診斷（需要時再展開）' not in source


def test_execution_surfaces_keep_current_live_blocker_ahead_of_venue_readiness_copy():
    status_source = _read("pages/ExecutionStatus.tsx")
    console_source = _read("pages/ExecutionConsole.tsx")

    assert status_source.index('liveRuntimeTruth?.deployment_blocker_reason') < status_source.index('liveReadyBlockers[0]')
    assert console_source.index('liveRuntimeTruth?.deployment_blocker_reason') < console_source.index('liveReadyBlockers[0]')
    assert 'liveReadyBlockers.length > 0 ? liveReadyBlockers.join(" · ") : primaryRuntimeMessage' not in status_source

def test_dashboard_keeps_live_decision_quality_and_execution_guardrails_surfaces():
    source = _read("pages/Dashboard.tsx")
    required_snippets = [
        '<ConfidenceIndicator',
        'decisionQualityScore={confidenceData.decision_quality_score}',
        'expectedDrawdownPenalty={confidenceData.expected_drawdown_penalty}',
        'expectedTimeUnderwater={confidenceData.expected_time_underwater}',
        'allowedLayers={confidenceData.allowed_layers}',
        'deploymentBlocker={confidenceData.deployment_blocker}',
        'supportProgress={confidenceData.support_progress}',
        'const { data: runtimeStatus, loading: runtimeStatusLoading, error: runtimeStatusError, refresh: refreshRuntimeStatus } = useApi<RuntimeStatusResponse>("/api/status", 60000);',
        'const runtimeStatusPending = runtimeStatusLoading && !runtimeStatus && !runtimeStatusError;',
        'await refreshRuntimeStatus();',
        'const executionSurfaceContract = runtimeStatus?.execution_surface_contract ?? null;',
        'const executionOperationsSurface = executionSurfaceContract?.operations_surface ?? null;',
        'const executionDiagnosticsSurface = executionSurfaceContract?.diagnostics_surface ?? null;',
        'const executionReconciliation = runtimeStatus?.execution_reconciliation ?? null;',
        'const metadataSmoke = runtimeStatus?.execution_metadata_smoke ?? null;',
        'const metadataSmokeFreshnessLabel = runtimeStatusPending',
        'const reconciliationStatusLabel = runtimeStatusPending ? "同步中" : (executionReconciliation?.status || "unavailable");',
        'const continuityLabel = runtimeStatusPending',
        'const venueChecks = Array.isArray(metadataSmoke?.venues) ? metadataSmoke.venues : [];',
        'VenueReadinessSummary',
        '💼 Execution 摘要',
        'Dashboard 只保留 Bot 營運摘要',
        'const liveScopePathologySummary =',
        'liveRuntimeTruth?.decision_quality_scope_pathology_summary',
        'LivePathologySummaryCard',
        '🧬 Live lane / spillover 對照',
        '前往 Bot 營運 →',
        '前往執行狀態 →',
        '部署狀態',
        '資金 / 曝險',
        'Metadata freshness',
        'Reconciliation / recovery',
        '🩹 啟動檢查 / continuity',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert 'Execution 狀態面板' not in source


def test_dashboard_execution_summary_keeps_current_live_blocker_ahead_of_venue_readiness_copy():
    source = _read("pages/Dashboard.tsx")
    required_snippets = [
        'const dashboardCurrentLiveBlocker = liveRuntimeTruth?.deployment_blocker || null;',
        'const dashboardCurrentLiveBlockerLabel = runtimeStatusPending ? "同步中" : (dashboardCurrentLiveBlocker || "unavailable");',
        'const dashboardPrimaryRuntimeMessage = liveRuntimeTruth?.deployment_blocker_reason',
        'const dashboardPrimaryRuntimeMessageLabel = runtimeStatusPending',
        'const dashboardVenueBlockers = Array.isArray(executionSurfaceContract?.live_ready_blockers)',
        'const dashboardVenueBlockersLabel = runtimeStatusPending',
        'current live blocker {dashboardCurrentLiveBlockerLabel}',
        'venue blockers {dashboardVenueBlockersLabel}',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert source.index('liveRuntimeTruth?.deployment_blocker_reason') < source.index('executionSurfaceContract?.live_ready_blockers')

def test_signal_banner_declares_dashboard_as_canonical_execution_route_until_upgraded():
    source = _read("components/SignalBanner.tsx")
    required_snippets = [
        'SignalBanner 目前只提供快捷下單 / 自動交易切換；完整 blocker、Guardrail context、stale governance 與 recovery 請到執行狀態頁查看。',
        '前往執行狀態頁 →',
        'href="/execution/status"',
        'fetch("/api/trade", {',
        'fetch("/api/automation/toggle", {',
        'fetch("/api/predict/confidence")',
        'const deploymentBlockerDetails = runtimeDecision?.deployment_blocker_details ?? null;',
        'const breakerRecentWindow = deploymentBlockerDetails?.recent_window ?? null;',
        'const breakerRelease = deploymentBlockerDetails?.release_condition ?? null;',
        'const circuitBreakerActive = runtimeDecision?.deployment_blocker === "circuit_breaker_active";',
        'runtime closure {runtimeDecision.runtime_closure_state || "—"}',
        'circuit breaker：recent 50 release window',
        '不要把 support / component patch 當成 breaker release 替代品。',
        'SignalBanner 只同步 release math，不可把這裡的快捷面板誤讀成 deployment readiness。',
        'raw reason {runtimeDecision.allowed_layers_raw_reason || "—"}',
        'final reason {runtimeDecision.allowed_layers_reason || "—"}',
        'capacity opened but signal still HOLD',
        'patch active but execution still blocked',
    ]
    for snippet in required_snippets:
        assert snippet in source

def test_confidence_indicator_distinguishes_capacity_opened_vs_patch_blocked_states():
    source = _read("components/ConfidenceIndicator.tsx")
    required_snippets = [
        'const q15PatchExecutionBlocked = Boolean(',
        'const q15PatchCapacityOpened = Boolean(',
        'const breakerRecentWindow = deploymentBlockerDetails?.recent_window ?? null;',
        'const breakerRelease = deploymentBlockerDetails?.release_condition ?? null;',
        'const circuitBreakerActive = deploymentBlocker === "circuit_breaker_active";',
        'recent 50 release window',
        '至少還差 {breakerWinsGap ?? "—"} 勝',
        '不要把 support / component patch 當成 breaker release 替代品。',
        'capacity opened but signal still HOLD',
        'patch active 只證明 runtime floor-cross 元件已落地，不等於目前可部署',
        'q15 patch 已經吃到 current live row，但 execution 仍被 exact live bucket blocker / guardrail 壓住',
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
        'leaderboard_warning',
        'placeholder_rows',
        'strategy_param_scan',
        'best_strategy_candidates',
        'selected_deployment_profile_label',
        'selected_deployment_profile_source',
        'selected_feature_profile',
        'selected_feature_profile_source',
        'leaderboard_governance',
        'profile_split',
        'governance_contract',
        'featureProfileDisplayName(model)',
        'featureProfileSourceLabel(model)',
        'Global 排名',
        'Production 配置',
        'deploymentProfileDisplayName(model)',
        'deploymentProfileSourceLabel(model)',
        'code-backed promoted from scan',
        'No-trade placeholder',
        '目前沒有可比較的模型排行榜列',
        'placeholder-only fallback：策略參數重掃候選',
        'canonical model leaderboard 仍是 placeholder-only；請改看策略參數重掃候選。',
        '載入候選 →',
        'const snapshotHistoryKey = (prefix: "strategy" | "model", row: LeaderboardHistoryRow, index: number) => {',
        'return `${prefix}-${row.id ?? row.created_at ?? row.updated_at ?? `row-${index}`}`;',
        'const snapshotHistoryLabel = (prefix: "策略" | "模型", row: LeaderboardHistoryRow, index: number) => {',
        'return `${prefix} 快照 · ${new Date(createdAt).toLocaleString("zh-TW")}`;',
        'const { data: runtimeStatus, loading: runtimeStatusLoading, error: runtimeStatusError } = useApi<StrategyLabRuntimeStatusResponse>("/api/status", 60000);',
        'const { data: liveDecisionStatus, loading: liveDecisionStatusLoading, error: liveDecisionStatusError } = useApi<StrategyLabLiveDecisionResponse>("/api/predict/confidence", 60000);',
        'const executionReconciliation = runtimeStatus?.execution_reconciliation ?? null;',
        'const executionSurfaceContract = runtimeStatus?.execution_surface_contract ?? null;',
        'const executionOperationsSurface = executionSurfaceContract?.operations_surface ?? null;',
        'const executionDiagnosticsSurface = executionSurfaceContract?.diagnostics_surface ?? null;',
        'const metadataSmoke = runtimeStatus?.execution_metadata_smoke ?? null;',
        'const runtimeStatusPending = runtimeStatusLoading && !runtimeStatus && !runtimeStatusError;',
        'const liveExecutionSyncPending = runtimeStatusPending && liveRuntimePending;',
        'const currentLiveBlockerLabel = liveExecutionSyncPending ? "同步中" : (currentLiveBlocker || "unknown");',
        'const currentLiveBlockerSummaryLabel = liveExecutionSyncPending',
        'const metadataSmokeFreshnessLabel = runtimeStatusPending',
        'const venueChecks = Array.isArray(metadataSmoke?.venues) ? metadataSmoke.venues : [];',
        'VenueReadinessSummary',
        'const liveRuntimeClosureState = liveDecisionStatus?.runtime_closure_state ?? liveRuntimeTruth?.runtime_closure_state ?? null;',
        'const liveRuntimeClosureSummary = liveDecisionStatus?.runtime_closure_summary ?? liveRuntimeTruth?.runtime_closure_summary ?? null;',
        'const liveRouting = liveRuntimeTruth?.sleeve_routing ?? null;',
        'const liveActiveSleeves = Array.isArray(liveRouting?.active_sleeves) ? liveRouting.active_sleeves : [];',
        'const liveInactiveSleeves = Array.isArray(liveRouting?.inactive_sleeves) ? liveRouting.inactive_sleeves : [];',
        'Decision Quality',
        'DQ {formatDecimal(activeResult?.avg_decision_quality_score, 3)}',
        '策略模組選擇',
        '先選 1 個主 preset，再疊加 modifier；只看摘要，不先讀長說明。',
        '已選取',
        'Live 部署同步',
        '只同步 live truth；blocked 與 recovery 請到「執行狀態」。',
        'const liveScopePathologySummary =',
        'liveRuntimeTruth?.decision_quality_scope_pathology_summary',
        'const currentLiveBlocker =',
        'const venueReadinessBlockers = liveExecutionBlockers;',
        'const currentLiveBlockerSummary =',
        'LivePathologySummaryCard',
        '🧬 Live lane / spillover 對照',
        'current live blocker',
        'venue blockers',
        'runtime closure',
        'active sleeves',
        'metadata freshness',
        '前往 Bot 營運 →',
        '前往執行狀態 →',
        'diagnostics surface {executionDiagnosticsSurface?.label || "執行狀態"}',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert 'Execution runtime blocker sync' not in source


def test_live_pathology_summary_card_surfaces_recommended_patch_contract():
    source = _read("components/LivePathologySummaryCard.tsx")
    required_snippets = [
        'type RecommendedPatchSummary = {',
        'recommended_patch?: RecommendedPatchSummary | null;',
        'const recommendedPatch = summary.recommended_patch ?? null;',
        'const formatPatchStatus = (status?: string | null) => {',
        'reference_patch_scope?: string | null;',
        'reference_source?: string | null;',
        'reference_only_until_exact_support_ready',
        '先當治理參考，不可直接放行',
        '建議正式 patch',
        'recommendedPatch.recommended_profile',
        'recommendedPatch.reference_patch_scope',
        'recommendedPatch.reference_source',
        'recommendedPatch.support_route_verdict',
        'recommendedPatch.recommended_action',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_live_pathology_summary_card_surfaces_focus_scope_vs_spillover_context():
    source = _read("components/LivePathologySummaryCard.tsx")
    required_snippets = [
        'const spilloverLabel = summary.focus_scope_label',
        'spillover pocket',
        'focus scope rows {summary.focus_scope_rows ?? "—"}',
        'spillover rows ${spillover.extra_rows}',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_venue_readiness_summary_component_surfaces_per_venue_contract():
    source = _read("components/VenueReadinessSummary.tsx")
    required_snippets = [
        'type VenueReadinessItem = {',
        'type VenueReadinessSummaryProps = {',
        'const readinessTone = (item: VenueReadinessItem) => {',
        'const readinessLabel = (item: VenueReadinessItem) => {',
        'const blockerSummary = item.blockers?.length ? item.blockers.join(" · ") : defaultProofSummary;',
        'config {item.enabled_in_config ? "enabled" : "disabled"}',
        'creds {item.credentials_configured ? "configured" : "public-only"}',
        'metadata {item.ok ? "OK" : "FAIL"}',
        'missing runtime proof',
        'step {item.contract?.step_size ?? "—"}',
        'tick {item.contract?.tick_size ?? "—"}',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_global_styles_use_premium_exchange_visual_tokens():
    css_source = _read("index.css")
    tailwind_source = (ROOT / "web" / "tailwind.config.js").read_text(encoding="utf-8")
    required_css = [
        'radial-gradient(circle at top',
        '.exchange-panel',
        '.exchange-subpanel',
        '.exchange-chip',
        '.btn-secondary',
        '.app-shell',
        '.app-page-shell',
        '.app-page-header',
        '.app-surface-card',
        '.app-surface-muted',
        '.app-segmented-control',
        '.app-segmented-button',
        '.app-control-input',
        '.app-button-primary',
        '.app-button-secondary',
    ]
    for snippet in required_css:
        assert snippet in css_source
    assert "accent: '#7132f5'" in tailwind_source



def test_frontend_pages_share_unified_shell_and_surface_classes():
    app_source = _read("App.tsx")
    dashboard_source = _read("pages/Dashboard.tsx")
    strategy_lab_source = _read("pages/StrategyLab.tsx")
    senses_source = _read("pages/Senses.tsx")
    execution_console_source = _read("pages/ExecutionConsole.tsx")
    execution_status_source = _read("pages/ExecutionStatus.tsx")
    component_sources = [
        _read("components/BacktestSummary.tsx"),
        _read("components/VenueReadinessSummary.tsx"),
        _read("components/LivePathologySummaryCard.tsx"),
        _read("components/FeatureChart.tsx"),
        _read("components/AdviceCard.tsx"),
        _read("components/ConfidenceIndicator.tsx"),
        _read("components/SenseModule.tsx"),
    ]

    assert 'className="app-shell' in app_source
    assert 'app-nav-link' in app_source
    for source in [dashboard_source, strategy_lab_source, senses_source, execution_console_source, execution_status_source]:
        assert 'app-page-shell' in source
        assert 'app-page-header' in source
    assert any('app-surface-card' in source for source in component_sources)



def test_strategy_lab_surfaces_two_year_leaderboard_backtest_policy():
    source = _read("pages/StrategyLab.tsx")
    required_snippets = [
        'const LEADERBOARD_BACKTEST_WINDOW_MONTHS = 24;',
        'const LEADERBOARD_BACKTEST_WINDOW_DAYS = 730;',
        'const LEADERBOARD_BACKTEST_POLICY_LABEL = "排行榜回測固定使用最近兩年";',
        'applyBacktestPreset("2y")',
        '排行榜回測固定使用最近兩年，降低短窗策略過擬合。',
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



def test_candlestick_chart_guards_resize_observer_after_dispose():
    source = _read("components/CandlestickChart.tsx")
    required_snippets = [
        'const chartsDisposedRef = useRef(false);',
        'const resizeFrameRef = useRef<number | null>(null);',
        'if (chartsDisposedRef.current) return;',
        'resizeFrameRef.current = window.requestAnimationFrame(() => {',
        'resizeObserver.unobserve(priceContainer);',
        'resizeObserver.unobserve(equityContainer);',
        'visibleRangeUnsubscribers.forEach((unsubscribe) => unsubscribe());',
        'priceChart.remove();',
        'equityChart.remove();',
    ]
    for snippet in required_snippets:
        assert snippet in source



def test_candlestick_chart_hover_uses_raw_score_values_for_percent_labels():
    source = _read("components/CandlestickChart.tsx")
    required_snippets = [
        'const scoreRawLookupRef = useRef<Map<number, number>>(new Map());',
        'const entryQualityRawLookupRef = useRef<Map<number, number>>(new Map());',
        'const confidenceRawLookupRef = useRef<Map<number, number>>(new Map());',
        'const scoreRaw = candlePoint ? scoreRawLookupRef.current.get(candlePoint.time) : undefined;',
        'const entryQualityRaw = candlePoint ? entryQualityRawLookupRef.current.get(candlePoint.time) : undefined;',
        'const confidenceRaw = candlePoint ? confidenceRawLookupRef.current.get(candlePoint.time) : undefined;',
        'scoreText: formatPct(scoreRaw),',
        'entryQualityText: formatPct(entryQualityRaw),',
        'confidenceText: formatPct(confidenceRaw),',
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


def test_use_api_supports_local_backend_timeout_fallback_for_dev_runtime():
    source = _read("hooks/useApi.ts")
    required_snippets = [
        'const ACTIVE_API_BASE_STORAGE_KEY = "poly_trader.active_api_base";',
        'const DEV_LOCAL_API_CANDIDATE_PORTS = [8000, 8001] as const;',
        'window.localStorage.setItem(ACTIVE_API_BASE_STORAGE_KEY, base);',
        'const requestCandidates = getApiRequestCandidates();',
        'const timeoutMs = getRequestTimeoutMs(endpoint);',
        'export async function fetchApiResponse(endpoint: string, options?: RequestInit): Promise<Response> {',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_candlestick_chart_uses_fetch_api_response_for_kline_requests():
    source = _read("components/CandlestickChart.tsx")
    required_snippets = [
        'import { fetchApiResponse } from "../hooks/useApi";',
        'const incrementalResp = await fetchApiResponse(`/api/chart/klines?${incrementalParams.toString()}`);',
        'const resp = await fetchApiResponse(`/api/chart/klines?${params.toString()}`);',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_dashboard_websocket_recomputes_ws_url_on_each_retry():
    source = _read("pages/Dashboard.tsx")
    assert 'const url = buildWsUrl("/ws/live");' in source
    assert source.index('const connect = () => {') < source.index('const url = buildWsUrl("/ws/live");')
