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
        'const currentLiveBlockerLabel = runtimeStatusPending',
        'humanizeCurrentLiveBlockerLabel(currentLiveBlocker || "unavailable")',
        'const primaryRuntimeMessage = runtimeStatusPending',
        'humanizeExecutionReason(',
        'const metadataFreshnessLabel = runtimeStatusPending',
        'const reconciliationCoverageLimited = isExecutionReconciliationLimitedEvidence(',
        'const reconciliationStatusLabel = runtimeStatusPending',
        'humanizeExecutionReconciliationStatusLabel(',
        'const venueBlockersLabel = runtimeStatusPending',
        'const executionStatusSymbolLabel = runtimeStatusPending ? "同步中" : (runtimeStatus?.symbol || "BTCUSDT");',
        'const executionStatusModeLabel = runtimeStatusPending',
        'const executionStatusVenueLabel = runtimeStatusPending ? "同步中" : (executionSummary?.venue || "unknown");',
        'const automationStatusLabel = runtimeStatusPending ? "automation 同步中" : `automation ${runtimeStatus?.automation ? "ON" : "OFF"}`;',
        'const liveReadinessStatusLabel = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");',
        'const liveReadinessMetricValue = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可進場" : "仍阻塞");',
        '<ExecutionPill>{executionStatusSymbolLabel}</ExecutionPill>',
        '<ExecutionPill>{executionStatusModeLabel}</ExecutionPill>',
        '<ExecutionPill>{executionStatusVenueLabel}</ExecutionPill>',
        '<ExecutionPill className={runtimeStatusPending ? getStatusTone("pending") : getStatusTone(runtimeStatus?.automation ? "ok" : "warning")}>',
        '{automationStatusLabel}',
        '{liveReadinessStatusLabel}',
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
        'value={liveReadinessMetricValue}',
        'venue blockers {venueBlockersLabel}',
    ]
    for snippet in required_snippets:
        assert snippet in page_source


def test_use_api_cancels_superseded_requests_and_ignores_stale_timeouts():
    source = _read("hooks/useApi.ts")
    required_snippets = [
        'import { useEffect, useState, useCallback, useRef } from "react";',
        'const requestSeqRef = useRef(0);',
        'const activeControllerRef = useRef<AbortController | null>(null);',
        'const cancelActiveRequest = useCallback(() => {',
        'requestSeqRef.current += 1;',
        'activeControllerRef.current?.abort();',
        'const requestSeq = requestSeqRef.current;',
        'const controller = new AbortController();',
        'activeControllerRef.current = controller;',
        'const json = await fetchJsonTracked<T>(endpoint, { signal: controller.signal });',
        'if (controller.signal.aborted || requestSeq !== requestSeqRef.current) return;',
        'if (activeControllerRef.current === controller) {',
        'cancelActiveRequest();',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_execution_console_consumes_runtime_status_and_uses_exchange_like_layout():
    source = _read("pages/ExecutionConsole.tsx")
    required_snippets = [
        'const { data: runtimeStatus, loading, error, refresh: refreshRuntimeStatus } = useApi<ExecutionConsoleRuntimeStatusResponse>("/api/status", 60000);',
        'const { data: executionOverview, loading: overviewLoading, error: overviewError, refresh: refreshExecutionOverview } = useApi<ExecutionOverviewResponse>("/api/execution/overview", 60000);',
        'const { data: executionRuns, loading: runsLoading, error: runsError, refresh: refreshExecutionRuns } = useApi<ExecutionRunsResponse>("/api/execution/runs", 60000);',
        'function formatSignedNumber(value: number | null | undefined, digits = 2): string {',
        'humanizeExecutionOperatorLabel',
        'humanizeExecutionReason',
        'humanizeExecutionReconciliationStatusLabel',
        'isExecutionReconciliationLimitedEvidence',
        'const liveReadinessSummary = runtimeStatusPending',
        'liveRuntimeTruth?.deployment_blocker_reason',
        '尚未提供 readiness 訊息。',
        'const totalUnrealizedPnl = runLedgerPreviews.reduce(',
        'const totalCapitalInUse = runLedgerPreviews.reduce(',
        'const profitableRuns = executionRunRecords.filter(',
        'const rawPrimaryBlockedReason = liveRuntimeTruth?.deployment_blocker_reason',
        'const blockedReasonSummary = runtimeStatusPending',
        'const deploymentStatusDetail = runtimeStatusPending',
        'liveRuntimeTruth?.runtime_closure_summary || liveRuntimeTruth?.deployment_blocker_reason || primaryBlockedReason',
        'Bot 營運 / Live Ops',
        '先看我的 Bot、資金使用與盈虧預覽',
        '選策略',
        '執行狀態',
        '共享盈虧預覽',
        '資金使用中',
        '可部署資金',
        '運行中 Run',
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


def test_execution_console_disables_manual_buy_shortcuts_when_current_live_blocker_is_active():
    source = _read("pages/ExecutionConsole.tsx")
    required_snippets = [
        'const manualBuyBlocked = hasBlockedState && Boolean(rawPrimaryBlockedReason);',
        'const manualBuyBlockedMessage = manualBuyBlocked',
        'current live blocker 啟動中：買入指令暫停；減碼 / 模式切換 / 查看阻塞原因仍可使用。',
        'const operatorQuickCommands = [',
        '{ label: "買入 0.001 BTC", disabled: operatorActionState.tone === "pending" || manualBuyBlocked },',
        '{ label: "減碼 0.001 BTC", disabled: operatorActionState.tone === "pending" },',
        'if (side === "buy" && manualBuyBlocked) {',
        '{manualBuyBlockedMessage && (',
        '{operatorQuickCommands.map((command) => (',
        'disabled={command.disabled}',
    ]
    for snippet in required_snippets:
        assert snippet in source



def test_execution_console_keeps_initial_sync_copy_until_status_overview_and_runs_finish_loading():
    source = _read("pages/ExecutionConsole.tsx")
    required_snippets = [
        'const runtimeStatusPending = loading && !runtimeStatus && !error;',
        'const overviewPending = overviewLoading && !executionOverview && !overviewError;',
        'const runsPending = runsLoading && !executionRuns && !runsError;',
        'const executionConsoleInitialSyncPending = runtimeStatusPending || overviewPending || runsPending;',
        'const hasBlockedState = !runtimeStatusPending && !executionSurfaceContract?.live_ready;',
        'const primaryBlockedReason = runtimeStatusPending ? "正在同步 /api/status" : humanizeExecutionReason(rawPrimaryBlockedReason);',
        'const deploymentStatusLabel = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "Ready" : "Blocked");',
        '正在向 /api/status 取得 current live blocker / runtime closure。',
        'const executionModeLabel = runtimeStatusPending ? "同步中" : (executionSummary?.mode || (dryRunEnabled ? "dry_run" : "paper"));',
        'const executionVenueLabel = runtimeStatusPending ? "同步中" : (executionSummary?.venue || "unknown");',
        'const automationStatusLabel = runtimeStatusPending ? "automation 同步中" : `automation ${automationEnabled ? "ON" : "OFF"}`;',
        'const liveReadyStatusLabel = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");',
        'const executionStrategySummaryLabel = overviewPending',
        '正在向 /api/execution/overview 取得 strategy / sleeve coverage。',
        'const executionProfileCardsEmptyState = overviewPending',
        '正在向 /api/execution/overview 取得 bot profile cards。',
        'const executionRunsEmptyState = runsPending',
        '正在向 /api/execution/runs 取得 run control / events。',
        'const liveReadinessSummary = runtimeStatusPending',
        '正在向 /api/status 取得 live readiness。',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_execution_console_explains_public_only_balance_and_capital_unavailability():
    source = _read("pages/ExecutionConsole.tsx")
    required_snippets = [
        'const accountCredentialsConfigured = Boolean(accountSummary?.health?.credentials_configured ?? executionSummary?.health?.credentials_configured);',
        'const accountBalanceUnavailableLabel = !accountCredentialsConfigured',
        'const accountSnapshotUnavailableLabel = !accountCredentialsConfigured',
        'const sharedLedgerUnavailableLabel = !accountCredentialsConfigured',
        'metadata-only snapshot',
        '待 private balance',
        '僅同步公開 metadata；private balance 待交易所憑證。',
        '需 private balance 後才能計算 bot 預算與 deployable capital。',
        'balanceTotal !== null',
        'accountBalanceUnavailableLabel',
        'accountBalanceUnavailableReason',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_execution_console_bot_cards_do_not_render_null_capital_as_em_dash_usdt():
    source = _read("pages/ExecutionConsole.tsx")
    required_snippets = [
        'const profileSharedPreviewValue = typeof ledgerPreview?.unrealized_pnl === "number"',
        'const profileSharedPreviewDetail = typeof ledgerPreview?.capital_in_use === "number"',
        'const profileBudgetValue = typeof card.planned_budget_amount === "number"',
        'const profileBudgetDetail = typeof card.planned_budget_amount === "number"',
        'const runBudgetValue = typeof run.budget_amount === "number"',
        'const runSharedPreviewValue = typeof ledgerPreview?.unrealized_pnl === "number"',
        'const runSharedPreviewDetail = typeof ledgerPreview?.capital_in_use === "number"',
        '尚無共享預覽',
        '未啟動 run',
        '先啟動 run 才會建立共享帳戶預覽',
        'run 已建立，但尚未鏡像共享資金占用',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert '{formatSignedNumber(ledgerPreview?.unrealized_pnl)} {ledgerPreview?.currency || balanceCurrency}' not in source
    assert '{formatNumber(card.planned_budget_amount)} {balanceCurrency}' not in source
    assert '{formatNumber(run.budget_amount)} {run.capital_currency || balanceCurrency}' not in source
    assert '"preview unavailable"' not in source
    assert '"資金使用中 preview unavailable"' not in source


def test_execution_console_humanizes_raw_control_plane_placeholders_on_bot_cards():
    console_source = _read("pages/ExecutionConsole.tsx")
    runtime_copy_source = _read("utils/runtimeCopy.ts")

    required_console_snippets = [
        'humanizeExecutionOperatorLabel',
        'const allocationRuleLabel =',
        'const profileLifecycleLabel =',
        'const profileLatestEventLabel =',
        'const profilePositionStatusLabel =',
        'const profileNextActionLabel =',
        'const profileNextActionEventLabel =',
        'const profilePreviewStatusLabel =',
    ]
    for snippet in required_console_snippets:
        assert snippet in console_source

    required_runtime_copy_snippets = [
        '["blocked_preview", "阻塞中"]',
        '["inactive_preview", "待條件恢復"]',
        '["not-started", "尚未啟動"]',
        '["no event", "尚無事件"]',
        '["waiting", "等待首筆事件"]',
        '["equal_split_active_sleeves", "active sleeves 均分"]',
    ]
    for snippet in required_runtime_copy_snippets:
        assert snippet in runtime_copy_source

    assert 'blocked_preview' not in console_source
    assert 'inactive_preview' not in console_source
    assert '"no event"' not in console_source
    assert '"not-started"' not in console_source
    assert '"equal_split_active_sleeves"' not in console_source


def test_execution_surfaces_keep_current_live_blocker_ahead_of_venue_readiness_copy():
    status_source = _read("pages/ExecutionStatus.tsx")
    console_source = _read("pages/ExecutionConsole.tsx")

    assert status_source.index('liveRuntimeTruth?.deployment_blocker_reason') < status_source.index('liveReadyBlockers[0]')
    assert console_source.index('liveRuntimeTruth?.deployment_blocker_reason') < console_source.index('liveReadyBlockers[0]')
    assert 'liveReadyBlockers.length > 0 ? liveReadyBlockers.join(" · ") : primaryRuntimeMessage' not in status_source


def test_execution_status_contextualizes_observability_signals_under_blocked_posture():
    source = _read("pages/ExecutionStatus.tsx")
    required_snippets = [
        'const reconciliationCoverageLimited = isExecutionReconciliationLimitedEvidence(',
        'const reconciliationHeadlineLabel = runtimeStatusPending',
        'humanizeExecutionReconciliationStatusLabel(',
        'limited evidence',
        'const accountVisibilityMetricValue = runtimeStatusPending',
        'metadata-only snapshot',
        'const executionStatusPostureLabel = runtimeStatusPending',
        'const executionStatusPostureSummary = runtimeStatusPending',
        'fresh / healthy 只代表觀測層正常，不代表可部署。',
        'title="帳戶可見性"',
        '場館前提與新鮮度',
        '進階診斷（Surface contract / timeline；需要時再展開）',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_execution_surfaces_show_current_bucket_support_and_runtime_vs_calibration_counts_together():
    status_source = _read("pages/ExecutionStatus.tsx")
    console_source = _read("pages/ExecutionConsole.tsx")

    shared_snippets = [
        'const supportRowsLabel = runtimeStatusPending',
        'const supportRouteVerdictLabel = runtimeStatusPending',
        'const supportGovernanceRouteLabel = runtimeStatusPending',
        'const supportAlignmentCountsLabel = runtimeStatusPending',
        'const supportAlignmentSummaryLabel = runtimeStatusPending',
        'runtime/calibration ${liveRuntimeTruth?.runtime_exact_support_rows ?? "—"} / ${liveRuntimeTruth?.calibration_exact_lane_rows ?? "—"}`;',
        '{supportAlignmentCountsLabel}',
    ]
    for snippet in shared_snippets:
        assert snippet in status_source
        assert snippet in console_source

    for snippet in [
        'support {supportRowsLabel}',
        'support route {supportRouteVerdictLabel}',
        'governance route {supportGovernanceRouteLabel}',
        'alignment {supportAlignmentSummaryLabel}',
    ]:
        assert snippet in status_source

    for snippet in [
        '>{supportRowsLabel}</div>',
        'support route {supportRouteVerdictLabel}',
        'governance route {supportGovernanceRouteLabel}',
        '>{supportAlignmentSummaryLabel}</div>',
    ]:
        assert snippet in console_source

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
        'ExecutionMetadataFreshnessDetail',
        'const reconciliationCoverageLimited = isExecutionReconciliationLimitedEvidence(',
        'const reconciliationStatusLabel = runtimeStatusPending',
        'humanizeExecutionReconciliationStatusLabel(',
        '尚未有 runtime order，因此目前只能確認「沒有發現明顯對帳落差」，不可視為完整實單驗證。',
        'const continuityLabel = runtimeStatusPending',
        'const venueChecks = Array.isArray(metadataSmoke?.venues) ? metadataSmoke.venues : [];',
        'VenueReadinessSummary',
        '💼 Execution 摘要',
        'Dashboard 只保留 4 張 Bot 營運摘要卡；若要查看 current live blocker 詳情、metadata 明細與 recovery 脈絡，請前往「執行狀態」。',
        'const liveScopePathologySummary =',
        'liveRuntimeTruth?.decision_quality_scope_pathology_summary',
        'LivePathologySummaryCard',
        '🧬 Live lane / spillover 對照',
        'const recentCanonicalDrift = runtimeStatus?.execution?.recent_canonical_drift ?? executionSurfaceContract?.recent_canonical_drift ?? runtimeStatus?.recent_canonical_drift ?? null;',
        'RecentCanonicalDriftCard',
        'summary={recentCanonicalDrift}',
        'pending={runtimeStatusPending && !recentCanonicalDrift}',
        'title="📉 Recent canonical drift"',
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
        'const dashboardCurrentLiveBlockerLabel = runtimeStatusPending',
        'humanizeCurrentLiveBlockerLabel(dashboardCurrentLiveBlocker || "unavailable")',
        'const dashboardPrimaryRuntimeMessage = liveRuntimeTruth?.deployment_blocker_reason',
        'const dashboardPrimaryRuntimeMessageLabel = runtimeStatusPending',
        'humanizeExecutionReason(',
        'const dashboardVenueBlockers = Array.isArray(executionSurfaceContract?.live_ready_blockers)',
        'const dashboardVenueBlockersLabel = runtimeStatusPending',
        'dashboardVenueBlockers.map((item) => humanizeExecutionReason(item)).join(" · ")',
        'const dashboardSupportRouteVerdictLabel = runtimeStatusPending',
        'const dashboardSupportGovernanceRouteLabel = runtimeStatusPending',
        'const dashboardSupportRowsLabel = runtimeStatusPending',
        'const dashboardSupportGapLabel = runtimeStatusPending',
        'const executionModeLabel = runtimeStatusPending ? "同步中" : (executionSummary?.mode || accountSummary?.mode || "unknown");',
        'const executionVenueLabel = runtimeStatusPending ? "同步中" : (executionSummary?.venue || accountSummary?.venue || "—");',
        'const dashboardExecutionStatusValue = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "Ready" : "Blocked");',
        'value={dashboardExecutionStatusValue}',
        'current live blocker {dashboardCurrentLiveBlockerLabel}',
        'current bucket {dashboardSupportRowsLabel} · gap {dashboardSupportGapLabel} · support route {dashboardSupportRouteVerdictLabel} · governance route {dashboardSupportGovernanceRouteLabel}',
        'venue blockers {dashboardVenueBlockersLabel}',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert source.index('liveRuntimeTruth?.deployment_blocker_reason') < source.index('executionSurfaceContract?.live_ready_blockers')


def test_dashboard_header_does_not_claim_offline_when_snapshot_data_is_loaded():
    source = _read("pages/Dashboard.tsx")
    required_snippets = [
        'const hasDashboardSnapshotData = Boolean(',
        'const dashboardTransportMode: "live" | "syncing" | "snapshot" | "offline" = wsConnected',
        'const dashboardTransportLabel = dashboardTransportMode === "live"',
        '? "即時連線"',
        '? "同步中"',
        '? "快照模式"',
        ': "離線";',
        'const dashboardTransportTone = dashboardTransportMode === "live"',
        'const dashboardTransportDotTone = dashboardTransportMode === "live"',
        '{dashboardTransportLabel}',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert '{wsConnected ? "即時連線" : "離線"}' not in source


def test_execution_surfaces_humanize_blocker_labels_and_reasons_via_shared_runtime_copy():
    runtime_copy_source = _read("utils/runtimeCopy.ts")
    required_runtime_copy_snippets = [
        'export function humanizeExecutionReason(value?: string | null): string {',
        'export function isExecutionReconciliationLimitedEvidence(',
        'export function humanizeExecutionReconciliationStatusLabel(',
        'export function humanizeCurrentLiveBlockerLabel(value?: string | null): string {',
        '"under_minimum_exact_live_structure_bucket"',
        '"exact support 未達最小樣本"',
        '"unsupported_exact_live_structure_bucket"',
        '"exact support 尚未建立"',
        '"decision_quality_below_trade_floor"',
        '"決策品質未達門檻"',
    ]
    for snippet in required_runtime_copy_snippets:
        assert snippet in runtime_copy_source

    dashboard_source = _read("pages/Dashboard.tsx")
    execution_console_source = _read("pages/ExecutionConsole.tsx")
    execution_status_source = _read("pages/ExecutionStatus.tsx")
    strategy_lab_source = _read("pages/StrategyLab.tsx")

    assert 'humanizeCurrentLiveBlockerLabel' in dashboard_source
    assert 'humanizeExecutionReason' in dashboard_source
    assert 'humanizeExecutionReconciliationStatusLabel' in dashboard_source
    assert 'isExecutionReconciliationLimitedEvidence' in dashboard_source
    assert 'humanizeExecutionOperatorLabel' in execution_console_source
    assert 'humanizeExecutionReason' in execution_console_source
    assert 'humanizeExecutionReconciliationStatusLabel' in execution_console_source
    assert 'isExecutionReconciliationLimitedEvidence' in execution_console_source
    assert 'humanizeCurrentLiveBlockerLabel' in execution_status_source
    assert 'humanizeExecutionReason' in execution_status_source
    assert 'humanizeExecutionReconciliationStatusLabel' in execution_status_source
    assert 'isExecutionReconciliationLimitedEvidence' in execution_status_source
    assert 'humanizeCurrentLiveBlockerLabel' in strategy_lab_source
    assert 'humanizeExecutionReason' in strategy_lab_source
    assert 'humanizeExecutionReconciliationStatusLabel' in strategy_lab_source
    assert 'isExecutionReconciliationLimitedEvidence' in strategy_lab_source

    assert 'const dashboardCurrentLiveBlockerLabel = runtimeStatusPending ? "同步中" : (dashboardCurrentLiveBlocker || "unavailable");' not in dashboard_source
    assert 'function humanizeExecutionReason(value?: string | null): string {' not in execution_console_source
    assert 'const liveReadinessSummary = runtimeStatusPending' in execution_console_source
    assert 'liveRuntimeTruth?.deployment_blocker_reason' in execution_console_source
    assert 'const currentLiveBlockerLabel = runtimeStatusPending ? "同步中" : (currentLiveBlocker || "unavailable");' not in execution_status_source
    assert 'const currentLiveBlockerLabel = liveExecutionSyncPending ? "同步中" : (currentLiveBlocker || "unknown");' not in strategy_lab_source


def test_dashboard_advice_card_downgrades_trade_ctas_until_runtime_is_ready():
    dashboard_source = _read("pages/Dashboard.tsx")
    advice_source = _read("components/AdviceCard.tsx")

    dashboard_snippets = [
        'const adviceCardExecutionActionState: "syncing" | "blocked" | "ready" = runtimeStatusPending || !liveRuntimeTruth',
        'const adviceCardExecutionBlockerReason = runtimeStatusPending',
        'executionActionState={adviceCardExecutionActionState}',
        'executionBlockerLabel={dashboardCurrentLiveBlockerLabel}',
        'executionBlockerReason={adviceCardExecutionBlockerReason}',
    ]
    advice_snippets = [
        'executionActionState?: "syncing" | "blocked" | "ready";',
        'executionBlockerLabel?: string;',
        'executionBlockerReason?: string;',
        'const tradeActionsDisabled = executionActionState !== "ready" || isSubmittingTrade;',
        'const blockerLabel = executionBlockerLabel || "blocked";',
        'const signalConfig = ACTION_CONFIG[action] || ACTION_CONFIG.hold;',
        'const displayConfig = executionActionState === "ready"',
        'text: "先同步 runtime blocker",',
        'text: `先解除 blocker · ${blockerLabel}`',
        'const summaryWithoutDirectionalCall = summary.replace(/\\s*綜合建議：.*$/u, "").trim();',
        'const displaySummary = executionActionState === "ready"',
        'Dashboard 正在同步 current live blocker；在 /api/status 完成前不把方向訊號當成可操作 CTA。',
        'current live blocker：${blockerLabel}。在 blocker 解除前，Dashboard 只保留分析摘要與導流，不把方向訊號包裝成可操作建議。',
        '<div className="text-sm text-slate-200 leading-relaxed">{displaySummary}</div>',
        'Dashboard 建議卡暫不提供快捷下單，避免 current live blocker truth 尚未到位前出現誤導 CTA。',
        '目前只保留分析摘要與阻塞後續動作；若要查看 current live blocker 詳情與恢復脈絡，請改到執行狀態 / Bot 營運頁。',
        '⏳ 快捷交易同步中',
        '🚫 Dashboard 快捷交易已停用',
        '訊號分析仍為：{signalConfig.icon} {signalConfig.text}',
        'href="/execution/status"',
        '查看阻塞原因',
        'href="/execution"',
        '前往 Bot 營運',
        '指令已交由 Bot 營運處理，請以下方 execution feedback 為準。',
    ]
    for snippet in dashboard_snippets:
        assert snippet in dashboard_source
    for snippet in advice_snippets:
        assert snippet in advice_source
    assert advice_source.count('const blockerLabel = executionBlockerLabel || "blocked";') == 1
    assert 'strong_buy: { text: "強烈建議買入 — 可考慮金字塔進場"' in advice_source
    assert 'buy: { text: "偏多格局 — 等待確認後買入"' in advice_source
    assert 'hold: { text: "建議觀望 — 方向不明"' in advice_source
    assert 'hold_long: { text: "弱勢格局 — 暫停新增部位"' in advice_source
    assert 'reduce: { text: "偏弱格局 — 保守減碼"' in advice_source


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
        'import { humanizeCurrentLiveBlockerLabel, humanizeExecutionReason } from "../utils/runtimeCopy";',
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
        'humanizeExecutionReason(deploymentBlockerReason || deploymentBlocker)',
        'humanizeCurrentLiveBlockerLabel(deploymentBlocker)',
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
        'const currentLiveBlockerLabel = liveExecutionSyncPending',
        'humanizeCurrentLiveBlockerLabel(currentLiveBlocker || "unknown")',
        'const currentLiveBlockerSummaryLabel = liveExecutionSyncPending',
        'humanizeExecutionReason(currentLiveBlockerSummary)',
        'const liveDeployStatusLabel = liveExecutionSyncPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");',
        'const reconciliationCoverageLimited = isExecutionReconciliationLimitedEvidence(',
        'const reconciliationStatusLabel = runtimeStatusPending',
        'humanizeExecutionReconciliationStatusLabel(',
        'const reconciliationBadgeLabel = runtimeStatusPending ? "對帳同步中" : `對帳 ${reconciliationStatusLabel}`;',
        'const liveExecutionSyncSubtitle = liveExecutionSyncPending',
        'const metadataSmokeFreshnessLabel = runtimeStatusPending',
        'const venueChecks = Array.isArray(metadataSmoke?.venues) ? metadataSmoke.venues : [];',
        'ExecutionMetadataFreshnessDetail',
        'VenueReadinessSummary',
        'const liveRuntimeClosureState = liveDecisionStatus?.runtime_closure_state ?? liveRuntimeTruth?.runtime_closure_state ?? null;',
        'const liveRuntimeClosureSummary = liveDecisionStatus?.runtime_closure_summary ?? liveRuntimeTruth?.runtime_closure_summary ?? null;',
        'const liveSupportRouteVerdict = liveDecisionStatus?.support_route_verdict ?? liveRuntimeTruth?.support_route_verdict ?? null;',
        'const liveSupportGovernanceRoute = liveDecisionStatus?.support_governance_route ?? liveRuntimeTruth?.support_governance_route ?? null;',
        'const liveSupportRowsLabel = liveExecutionSyncPending',
        'const liveSupportGapLabel = liveExecutionSyncPending',
        'const liveSupportRouteSummaryLabel = liveExecutionSyncPending',
        'current bucket ${liveSupportRowsLabel} · gap ${liveSupportGapLabel} · support route ${liveSupportRouteVerdict || "—"} · governance route ${liveSupportGovernanceRoute || "—"}`;',
        'const liveRouting = liveRuntimeTruth?.sleeve_routing ?? null;',
        'const liveActiveSleeves = Array.isArray(liveRouting?.active_sleeves) ? liveRouting.active_sleeves : [];',
        'const liveInactiveSleeves = Array.isArray(liveRouting?.inactive_sleeves) ? liveRouting.inactive_sleeves : [];',
        'Decision Quality',
        'DQ {formatDecimal(activeResult?.avg_decision_quality_score, 3)}',
        '策略模組選擇',
        '先選 1 個主 preset，再疊加 modifier；只看摘要，不先讀長說明。',
        '已選取',
        'Live 部署同步',
        'subtitle={liveExecutionSyncSubtitle}',
        'current live blocker {currentLiveBlockerLabel}',
        '{reconciliationBadgeLabel} · {reconciliationCheckedAtLabel}',
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


def test_strategy_lab_live_sync_card_keeps_blocked_status_ahead_of_reconciliation_health():
    source = _read("pages/StrategyLab.tsx")
    required_snippets = [
        'const liveDeployStatusLabel = liveExecutionSyncPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");',
        'const reconciliationCoverageLimited = isExecutionReconciliationLimitedEvidence(',
        'const reconciliationStatusLabel = runtimeStatusPending',
        'humanizeExecutionReconciliationStatusLabel(',
        'const reconciliationBadgeLabel = runtimeStatusPending ? "對帳同步中" : `對帳 ${reconciliationStatusLabel}`;',
        'const liveExecutionSyncSubtitle = liveExecutionSyncPending',
        'subtitle={liveExecutionSyncSubtitle}',
        'pending: liveExecutionSyncPending,',
        'liveReady: Boolean(executionSurfaceContract?.live_ready),',
        'blocker: currentLiveBlocker,',
        'reconciliationStatus: executionReconciliation?.status,',
        '{liveDeployStatusLabel}',
        'current live blocker {currentLiveBlockerLabel}',
        'current bucket {liveSupportRowsLabel} · gap {liveSupportGapLabel}',
        '{reconciliationBadgeLabel} · {reconciliationCheckedAtLabel}',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert source.index('liveDeployStatusLabel') < source.index('reconciliationBadgeLabel')


def test_strategy_lab_surfaces_recent_canonical_drift_summary_beside_live_lane_truth():
    source = _read("pages/StrategyLab.tsx")
    required_snippets = [
        'const recentCanonicalDrift = runtimeStatus?.execution?.recent_canonical_drift ?? executionSurfaceContract?.recent_canonical_drift ?? runtimeStatus?.recent_canonical_drift ?? null;',
        'RecentCanonicalDriftCard',
        'summary={recentCanonicalDrift}',
        'pending={runtimeStatusPending && !recentCanonicalDrift}',
        'title="📉 Recent canonical drift"',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert source.index('LivePathologySummaryCard') < source.index('RecentCanonicalDriftCard')


def test_strategy_lab_recovers_empty_leaderboard_after_initial_backend_timeout():
    source = _read("pages/StrategyLab.tsx")
    required_snippets = [
        'const extractStrategyLeaderboardList = (payload: any): StrategyEntry[] => {',
        'const fetchStrategyLabEndpointJson = async (endpoint: string) => {',
        'const sameOriginResponse = await window.fetch(endpoint, {',
        'credentials: "same-origin"',
        'return fetchApi(endpoint);',
        'const res = await fetchStrategyLabEndpointJson(endpoint) as any;',
        'const nextStrategies = extractStrategyLeaderboardList(res);',
        'const detail = await fetchStrategyLabEndpointJson(`/api/strategies/${encodeURIComponent(strategyName)}`) as StrategyEntry;',
        'const data = await fetchStrategyLabEndpointJson("/api/strategy_data_range")',
        'if (initialLoading || strategies.length > 0) {',
        'loadLeaderboard(false);',
        'if (selectedStrategy || loadingStrategyName || strategies.length === 0) {',
        'void selectStrategyByName(strategies[0].name);',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_execution_status_and_strategy_lab_surface_q15_bucket_root_cause_candidate():
    execution_status_source = _read("pages/ExecutionStatus.tsx")
    strategy_lab_source = _read("pages/StrategyLab.tsx")
    runtime_copy_source = _read("utils/runtimeCopy.ts")

    for snippet in [
        'type Q15BucketRootCauseSummary = {',
        'humanizeQ15BucketRootCauseLabel',
        'q15_bucket_root_cause?: Q15BucketRootCauseSummary | null;',
        'current_bucket_root_cause?: Q15BucketRootCauseSummary | null;',
        'const currentBucketRootCause = liveRuntimeTruth?.current_bucket_root_cause ?? liveRuntimeTruth?.q15_bucket_root_cause ?? null;',
        'const currentBucketRootCauseLabel = runtimeStatusPending',
        'const currentBucketRootCauseSummary = runtimeStatusPending',
        'current bucket root cause',
        'bucket {currentBucketRootCauseBucket}',
        'candidate {currentBucketRootCause?.candidate_patch_feature || "—"}',
        'near-boundary {currentBucketRootCause?.near_boundary_rows ?? "—"}',
        'next {currentBucketRootCause?.verify_next || "—"}',
    ]:
        assert snippet in execution_status_source

    for snippet in [
        'interface Q15BucketRootCauseSummary {',
        'humanizeQ15BucketRootCauseLabel',
        'q15_bucket_root_cause?: Q15BucketRootCauseSummary | null;',
        'current_bucket_root_cause?: Q15BucketRootCauseSummary | null;',
        'const currentBucketRootCause = liveDecisionStatus?.current_bucket_root_cause',
        'const currentBucketRootCauseLabel = liveExecutionSyncPending',
        'const currentBucketRootCauseSummary = liveExecutionSyncPending',
        'current bucket root cause',
        'bucket {currentBucketRootCauseBucket}',
        'candidate {currentBucketRootCause?.candidate_patch_feature || "—"}',
        'near-boundary {currentBucketRootCause?.near_boundary_rows ?? "—"}',
        'next {currentBucketRootCause?.verify_next || "—"}',
    ]:
        assert snippet in strategy_lab_source

    assert 'boundary_sensitivity_candidate' in runtime_copy_source
    assert 'bucket_boundary_review' in runtime_copy_source
    assert 'current_bucket_exact_support_already_closed' in runtime_copy_source
    assert 'deployment_blocker_verification' in runtime_copy_source
    assert '尚未取得 current bucket 根因' in runtime_copy_source


def test_live_pathology_summary_card_surfaces_recommended_patch_contract():
    source = _read("components/LivePathologySummaryCard.tsx")
    required_snippets = [
        'type RecommendedPatchSummary = {',
        'recommended_patch?: RecommendedPatchSummary | null;',
        'const recommendedPatch = summary.recommended_patch ?? null;',
        'const formatPatchStatus = (status?: string | null) => {',
        'reference_patch_scope?: string | null;',
        'reference_source?: string | null;',
        'current_live_regime_gate?: string | null;',
        'patch_scope_matches_live?: boolean | null;',
        'reference_only_cause?: string | null;',
        'reference_only_until_exact_support_ready',
        'reference_only_non_current_live_scope',
        'reference_only_while_deployment_blocked',
        '先當治理參考，不可直接放行',
        'scope 不同，僅作治理參考',
        'blocker 未清前僅作治理參考',
        'const patchSectionTitle = isReferenceOnlyPatchStatus(recommendedPatch?.status)',
        '治理 / 訓練 patch 參考',
        '建議正式 patch',
        'recommendedPatch.recommended_profile',
        'recommendedPatch.reference_patch_scope',
        'recommendedPatch.reference_source',
        'support_governance_route?: string | null;',
        'const supportRouteLabel = supportRouteVerdict || recommendedPatch?.support_route_verdict || null;',
        'const supportGovernanceRouteLabel = supportGovernanceRoute || recommendedPatch?.support_governance_route || null;',
        'support route {supportRouteLabel || "—"}',
        'governance route ${supportGovernanceRouteLabel}',
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


def test_live_pathology_summary_card_supports_compact_summary_mode_for_workspace_surfaces():
    source = _read("components/LivePathologySummaryCard.tsx")
    required_snippets = [
        'compact?: boolean;',
        'supportAlignmentStatus?: string | null;',
        'supportAlignmentSummary?: string | null;',
        'runtimeExactSupportRows?: number | null;',
        'calibrationExactLaneRows?: number | null;',
        'dominant_structure_bucket?: string | null;',
        'compact = false,',
        'if (compact) {',
        'const compactTopShifts = topShifts.slice(0, 2);',
        'const compactPatchLabel = recommendedPatch?.recommended_profile',
        'const compactPatchStatusLabel = recommendedPatch ? formatPatchStatus(recommendedPatch.status) : null;',
        'const currentBucketSupportRows = recommendedPatch?.current_live_structure_bucket_rows ?? exactLane?.current_live_structure_bucket_rows;',
        'const currentBucketSupportMinimum = recommendedPatch?.minimum_support_rows ?? null;',
        'const currentBucketSupportLabel = currentBucketSupportRows != null',
        'const exactLaneRowsLabel = exactLane?.rows != null',
        'const exactLaneHistoricalBucket = exactLane?.dominant_structure_bucket || null;',
        'current bucket support',
        'exact lane cohort',
        'historical lane bucket',
        'const supportAlignmentStatusLabel = formatSupportAlignmentStatus(supportAlignmentStatus);',
        'const supportAlignmentCountsLabel = runtimeExactSupportRows != null || calibrationExactLaneRows != null',
        'runtime/calibration ${runtimeExactSupportRows ?? "—"} / ${calibrationExactLaneRows ?? "—"}',
        '{exactLaneRowsLabel}',
        '{currentBucketSupportLabel}',
        '{compactPatchStatusLabel || "patch 狀態未提供"}',
        'support route ${supportRouteLabel}',
        '{supportAlignmentStatusLabel ? ` · ${supportAlignmentStatusLabel}` : ""}',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_dashboard_and_strategy_lab_pass_support_alignment_to_compact_live_pathology_cards():
    dashboard_source = _read("pages/Dashboard.tsx")
    strategy_lab_source = _read("pages/StrategyLab.tsx")
    for snippet in [
        'supportAlignmentStatus={liveRuntimeTruth?.support_alignment_status ?? null}',
        'supportAlignmentSummary={liveRuntimeTruth?.support_alignment_summary ?? null}',
        'runtimeExactSupportRows={liveRuntimeTruth?.runtime_exact_support_rows ?? null}',
        'calibrationExactLaneRows={liveRuntimeTruth?.calibration_exact_lane_rows ?? null}',
        'supportRouteVerdict={liveRuntimeTruth?.support_route_verdict ?? null}',
        'supportGovernanceRoute={liveRuntimeTruth?.support_governance_route ?? null}',
    ]:
        assert snippet in dashboard_source
    for snippet in [
        'supportAlignmentStatus={liveSupportAlignmentStatus}',
        'supportAlignmentSummary={liveSupportAlignmentSummary}',
        'runtimeExactSupportRows={liveRuntimeExactSupportRows}',
        'calibrationExactLaneRows={liveCalibrationExactLaneRows}',
        'supportRouteVerdict={liveSupportRouteVerdict}',
        'supportGovernanceRoute={liveSupportGovernanceRoute}',
    ]:
        assert snippet in strategy_lab_source


def test_dashboard_and_strategy_lab_use_compact_live_pathology_cards_on_summary_surfaces():
    dashboard_source = _read("pages/Dashboard.tsx")
    strategy_lab_source = _read("pages/StrategyLab.tsx")
    assert 'LivePathologySummaryCard' in dashboard_source
    assert 'compact' in dashboard_source.split('LivePathologySummaryCard', 1)[1]
    assert 'LivePathologySummaryCard' in strategy_lab_source
    assert 'compact' in strategy_lab_source.split('LivePathologySummaryCard', 1)[1]


def test_venue_readiness_summary_component_surfaces_per_venue_contract():
    source = _read("components/VenueReadinessSummary.tsx")
    required_snippets = [
        'type VenueReadinessItem = {',
        'type VenueReadinessSummaryProps = {',
        'const readinessTone = (item: VenueReadinessItem) => {',
        'const readinessLabel = (item: VenueReadinessItem) => {',
        'const readinessBadgeLabel = (item: VenueReadinessItem) => {',
        'return "READ-ONLY";',
        'return "DISABLED";',
        'const blockerSummary = item.blockers?.length ? item.blockers.join(" · ") : defaultProofSummary;',
        'config {item.enabled_in_config ? "enabled" : "disabled"}',
        'creds {item.credentials_configured ? "configured" : "public-only"}',
        'metadata contract {item.ok ? "OK" : "FAIL"}',
        'missing runtime proof',
        'step {item.contract?.step_size ?? "—"}',
        'tick {item.contract?.tick_size ?? "—"}',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_venue_readiness_summary_supports_compact_operator_summary_mode():
    source = _read("components/VenueReadinessSummary.tsx")
    required_snippets = [
        'if (compact) {',
        'proof pending · {blockerSummary}',
        'config {item.enabled_in_config ? "enabled" : "disabled"} · creds {item.credentials_configured ? "configured" : "public-only"} · metadata {item.ok ? "OK" : "FAIL"}',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_execution_metadata_freshness_detail_component_surfaces_external_monitor_ticking_state():
    source = _read("components/ExecutionMetadataFreshnessDetail.tsx")
    required_snippets = [
        'type MetadataFreshness = {',
        'type MetadataGovernance = {',
        'type ExecutionMetadataFreshnessDetailProps = {',
        'function buildHostSchedulerSummary(governance?: MetadataGovernance): string | null {',
        'const hostSchedulerSummary = buildHostSchedulerSummary(governance);',
        'hostSchedulerSummary ? `external monitor ${hostSchedulerSummary}` : null,',
        'governance?.operator_message || "尚未取得 governance 訊息。"',
        'return <div>正在向 /api/status 取得 metadata smoke。</div>;',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_execution_status_reuses_shared_venue_readiness_component_and_explains_public_only_balances():
    source = _read("pages/ExecutionStatus.tsx")
    required_snippets = [
        'import VenueReadinessSummary from "../components/VenueReadinessSummary";',
        '<VenueReadinessSummary venues={venueChecks} className="mt-4" />',
        'const accountBalanceUnavailableLabel = !accountCredentialsConfigured',
        'private balance unavailable until exchange credentials are configured',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert 'item.ok ? "OK" : "FAIL"' not in source


def test_dashboard_execution_summary_explains_public_only_balance_unavailability():
    source = _read("pages/Dashboard.tsx")
    required_snippets = [
        'const accountBalanceUnavailableLabel = !accountCredentialsConfigured',
        'private balance unavailable until exchange credentials are configured',
        'accountBalanceSummaryValue',
        'accountBalanceSummaryTotal',
        'total {accountBalanceSummaryTotal} · 倉位 {positionCount} · 掛單 {openOrderCount}',
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
        ' · 固定視窗 730 天（約 24 個月），降低短窗策略過擬合。',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert source.count('排行榜回測固定使用最近兩年') == 1
    assert source.count('{LEADERBOARD_BACKTEST_POLICY_LABEL}') == 1
    assert '{LEADERBOARD_BACKTEST_POLICY_LABEL} · 固定視窗 {LEADERBOARD_BACKTEST_WINDOW_DAYS} 天。' not in source
    assert '排行榜回測固定使用最近兩年最近 730 天' not in source


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



def test_candlestick_chart_promotes_strategy_score_overlay_over_model_confidence_line():
    source = _read("components/CandlestickChart.tsx")
    required_snippets = [
        'title: "策略分數",',
        'title: "進場品質",',
        'const strategyScoreData = toScoreLine((point) => point.score);',
        'const entryQualityData = toScoreLine((point) => point.entry_quality);',
        'scoreSeriesRef.current?.setData(strategyScoreData);',
        'confidenceSeriesRef.current?.setData(entryQualityData);',
        '上圖疊加策略分數與進場品質',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert 'title: "模型信心",' not in source
    assert 'confidenceSeriesRef.current?.setData(confidenceData);' not in source



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
        'const DEV_API_DISCOVERY_TIMEOUT_MS = 1200;',
        'const DEV_API_STATUS_DISCOVERY_TIMEOUT_MS = 2000;',
        'let prewarmActiveApiBasePromise: Promise<void> | null = null;',
        'window.localStorage.setItem(ACTIVE_API_BASE_STORAGE_KEY, base);',
        'async function probeApiBaseHealth(base: string): Promise<boolean> {',
        'const resp = await fetch(buildApiUrlForBase("/health", base), {',
        'function scoreApiBaseRuntimeContract(payload: unknown): number {',
        'const recentCanonicalDrift = execution?.recent_canonical_drift',
        'async function probeApiBaseRuntimeContractScore(base: string): Promise<number> {',
        'const resp = await fetch(buildApiUrlForBase("/api/status", base), {',
        'const capabilityResults = await Promise.all(healthyCandidates.map(async (base) => ({',
        'runtimeContractScore: await probeApiBaseRuntimeContractScore(base),',
        'const bestCapability = capabilityResults.reduce<{ base: string; runtimeContractScore: number } | null>(',
        'probe.runtimeContractScore > best.runtimeContractScore',
        'persistActiveApiBase(bestCapability?.base ?? healthyCandidates[0] ?? null);',
        'async function prewarmDevApiBase(): Promise<void> {',
        'export async function prewarmActiveApiBase(): Promise<string | null> {',
        'await prewarmDevApiBase();',
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
    assert 'const url = buildWsUrl("/ws/live");' in source or 'const wsCandidates = buildWsCandidateUrls("/ws/live");' in source
    assert 'prewarmActiveApiBase' in source
    assert source.index('const connect = () => {') < source.index('const connectAttempt = (attemptIndex: number) => {') if 'const connectAttempt = (attemptIndex: number) => {' in source else source.index('const connect = () => {') < source.index('const url = buildWsUrl("/ws/live");')


def test_use_api_exposes_websocket_candidate_urls_for_dev_backend_failover():
    source = _read("hooks/useApi.ts")
    required_snippets = [
        'function toWebSocketUrl(base: string | null, path: string): string {',
        'export function buildWsCandidateUrls(path: string): string[] {',
        'return devCandidates.map((candidate) => toWebSocketUrl(candidate, path));',
        'return [toWebSocketUrl(preferredBase, path)];',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_dashboard_websocket_falls_back_to_next_candidate_when_handshake_stalls():
    source = _read("pages/Dashboard.tsx")
    required_snippets = [
        'buildWsCandidateUrls',
        'prewarmActiveApiBase',
        'void prewarmActiveApiBase().catch(() => null).then(() => {',
        'const wsCandidates = buildWsCandidateUrls("/ws/live");',
        'const connectAttempt = (attemptIndex: number) => {',
        'const openTimeout = window.setTimeout(() => {',
        'connectAttempt(attemptIndex + 1);',
        'window.clearTimeout(openTimeout);',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_dashboard_websocket_bootstrap_is_strict_mode_safe():
    source = _read("pages/Dashboard.tsx")
    main_source = _read("main.tsx")
    required_dashboard_snippets = [
        'let connectBootstrapTimer = 0;',
        'const closeSocketWithoutHandshakeNoise = (socket: WebSocket | null) => {',
        'if (socket.readyState !== WebSocket.OPEN) return;',
        'closeSocketWithoutHandshakeNoise(candidate);',
        'closeSocketWithoutHandshakeNoise(ws);',
        'connectBootstrapTimer = window.setTimeout(() => {',
        'window.clearTimeout(connectBootstrapTimer);',
        'closed before the connection is established',
    ]
    for snippet in required_dashboard_snippets:
        assert snippet in source
    assert '<React.StrictMode>' in main_source
