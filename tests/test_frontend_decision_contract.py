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
        'const automationStatusLabel = runtimeStatusPending ? "自動交易同步中" : `自動交易 ${runtimeStatus?.automation ? "開啟" : "關閉"}`;',
        'const liveReadinessStatusLabel = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");',
        'const liveReadinessMetricValue = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可進場" : "仍阻塞");',
        '<ExecutionPill>{executionStatusSymbolLabel}</ExecutionPill>',
        '<ExecutionPill>{executionStatusModeLabel}</ExecutionPill>',
        '<ExecutionPill>{executionStatusVenueLabel}</ExecutionPill>',
        '<ExecutionPill className={runtimeStatusPending ? getStatusTone("pending") : getStatusTone(runtimeStatus?.automation ? "ok" : "warning")}>',
        '{automationStatusLabel}',
        '{liveReadinessStatusLabel}',
        '執行狀態 / 診斷',
        '先看 blocker，再決定是否介入',
        '回到 Bot 營運',
        '可部署',
        '資料新鮮度',
        '對帳狀態',
        '詳細對帳與恢復',
        '場館通道',
        '時間線',
        '營運入口',
        '營運入口 {humanizeRuntimeDetailText(operationsSurface?.label || "Bot 營運")} · {operationsSurface?.route || "/execution"}',
        '診斷入口 {humanizeRuntimeDetailText(diagnosticsSurface?.label || "執行狀態")} · {diagnosticsSurface?.route || "/execution/status"}',
        'detail={`阻塞點 ${currentLiveBlockerLabel} · ${primaryRuntimeMessage} · 治理範圍 ${readinessScopeLabel}`}',
        'value={liveReadinessMetricValue}',
        '場館阻塞 {venueBlockersLabel}',
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
        '尚未提供部署狀態訊息。',
        'const totalUnrealizedPnl = runLedgerPreviews.reduce(',
        'const totalCapitalInUse = runLedgerPreviews.reduce(',
        'const profitableRuns = executionRunRecords.filter(',
        'const rawPrimaryBlockedReason = liveRuntimeTruth?.deployment_blocker_reason',
        'const blockedReasonSummary = runtimeStatusPending',
        'const deploymentStatusDetail = runtimeStatusPending',
        'liveRuntimeTruth?.runtime_closure_summary || liveRuntimeTruth?.deployment_blocker_reason || primaryBlockedReason',
        'Bot 營運 / 執行工作台',
        '先看我的 Bot、資金使用與盈虧預覽',
        '選策略',
        '執行狀態',
        '共享盈虧預覽',
        '資金使用中',
        '可部署資金',
        '運行中 Run',
        '我的 Bot',
        '運行中',
        '自然語句操作',
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
        '目前阻塞點啟動中：買入指令暫停；減碼 / 模式切換 / 查看阻塞原因仍可使用。',
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
        'const deploymentStatusLabel = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");',
        '正在向 /api/status 取得目前阻塞點 / 部署閉環摘要。',
        'const executionModeLabel = runtimeStatusPending ? "同步中" : humanizeExecutionModeLabel(executionModeRaw);',
        'const executionVenueLabel = runtimeStatusPending ? "同步中" : humanizeExecutionVenueLabel(executionSummary?.venue || "unknown");',
        'const automationStatusLabel = runtimeStatusPending ? "自動交易同步中" : `自動交易 ${automationEnabled ? "開啟" : "關閉"}`;',
        'const liveReadyStatusLabel = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");',
        'const executionStrategySummaryLabel = overviewPending',
        '正在向 /api/execution/overview 取得策略 / 倉位腿覆蓋。',
        'const executionProfileCardsEmptyState = overviewPending',
        '正在向 /api/execution/overview 取得 Bot 卡片。',
        'const executionRunsEmptyState = runsPending',
        '正在向 /api/execution/runs 取得 run 控制 / 事件。',
        'const liveReadinessSummary = runtimeStatusPending',
        '正在向 /api/status 取得部署狀態。',
        '尚未提供部署狀態訊息。',
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
        '僅元資料快照',
        '待私有餘額',
        '僅同步公開元資料；私有餘額待交易所憑證。',
        '需私有餘額後才能計算 Bot 預算與可部署資金。',
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
        'const profileRoutingReasonLabel = humanizeRuntimeDetailText(card.routing_reason || null);',
        'const profileStartReasonLabel = humanizeRuntimeDetailText(card.control_contract?.start_reason || null);',
        'const profileLatestEventMessageLabel = humanizeRuntimeDetailText(',
        'const profileSummaryLabel = card.summary || profileStrategyBinding?.summary || profileRoutingReasonLabel || "尚未提供策略摘要";',
        '路由 {profileRoutingReasonLabel || "—"}',
        '啟動條件 {profileStartReasonLabel || "—"}',
        '最新事件 {profileLatestEventMessageLabel || "尚未建立 Bot 事件"}',
    ]
    for snippet in required_console_snippets:
        assert snippet in console_source

    required_runtime_copy_snippets = [
        '["blocked_preview", "阻塞中"]',
        '["inactive_preview", "待條件恢復"]',
        '["not-started", "尚未啟動"]',
        '["no event", "尚無事件"]',
        '["waiting", "等待首筆事件"]',
        '["equal_split_active_sleeves", "啟用倉位腿均分"]',
        'const spacedToken = token.replace(/_/g, " ");',
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
    assert 'liveReadyBlockers.join(" · ") || primaryBlockedReason' not in console_source


def test_execution_console_operator_surface_avoids_raw_english_runtime_tokens():
    source = _read("pages/ExecutionConsole.tsx")
    runtime_copy_source = _read("utils/runtimeCopy.ts")

    for snippet in [
        '執行期 / 校準',
        '支持路徑 {supportRouteVerdictLabel}',
        '治理路徑 {supportGovernanceRouteLabel}',
        '啟用倉位腿',
        '擷取時間 {formatTime(accountSummary?.captured_at)}',
        '數量 {formatNumber(lastOrder?.qty)} · 價格 {formatNumber(lastOrder?.price)}',
        'lastReject?.code || "無"',
        'lastFailure?.message || "無"',
        '["exact_live_bucket_present_but_below_minimum", "目前 exact support 已開始累積"]',
        '["deployment-grade minimum support", "可部署最低樣本"]',
    ]:
        assert snippet in source or snippet in runtime_copy_source

    assert 'kill switch ' not in source
    assert 'failure halt ' not in source
    assert 'daily halt ' not in source
    assert 'Active sleeves' not in source
    assert 'captured ' not in source
    assert 'qty {formatNumber(lastOrder?.qty)}' not in source
    assert 'price {formatNumber(lastOrder?.price)}' not in source
    assert 'lastReject?.code || "none"' not in source
    assert 'lastFailure?.message || "none"' not in source


def test_execution_status_and_live_pathology_cards_use_chinese_support_alignment_labels():
    status_source = _read("pages/ExecutionStatus.tsx")
    pathology_source = _read("components/LivePathologySummaryCard.tsx")

    for snippet in [
        '? "執行期 / 校準 同步中"',
        ': `執行期 / 校準 ${liveRuntimeTruth?.runtime_exact_support_rows ?? "—"} / ${liveRuntimeTruth?.calibration_exact_lane_rows ?? "—"}`;',
        '支持路徑 {supportRouteVerdictLabel}',
        '治理路徑 {supportGovernanceRouteLabel}',
        '`執行期 / 校準 ${runtimeExactSupportRows ?? "—"} / ${calibrationExactLaneRows ?? "—"}`',
        '{supportAlignmentCountsLabel || "執行期 / 校準 — / —"}',
    ]:
        assert snippet in status_source or snippet in pathology_source

    assert 'runtime/calibration' not in status_source
    assert 'runtime/calibration' not in pathology_source


def test_execution_status_prioritizes_overall_execution_posture_before_freshness_and_account_visibility():
    source = _read("pages/ExecutionStatus.tsx")
    required_snippets = [
        'const reconciliationCoverageLimited = isExecutionReconciliationLimitedEvidence(',
        'const reconciliationHeadlineLabel = runtimeStatusPending',
        'humanizeExecutionReconciliationStatusLabel(',
        'const accountVisibilityMetricValue = runtimeStatusPending',
        'const executionStatusPostureLabel = runtimeStatusPending',
        'const executionStatusPostureSummary = runtimeStatusPending',
        '資料新鮮、對帳正常只代表觀測層狀態，不代表可部署。',
        '正在向 /api/status 取得對帳 / 恢復摘要。',
        '正在向 /api/status 取得帳戶快照。',
        '正在同步 /api/status；在執行期真相到位前，不要把資料新鮮或對帳正常誤讀成可部署狀態。',
        'title="帳戶可見性"',
        '場館前提與新鮮度',
        '進階診斷（介面契約 / 時間線；需要時再展開）',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_runtime_copy_and_execution_surfaces_use_humanized_chinese_operator_copy():
    runtime_copy = _read("utils/runtimeCopy.ts")
    status_source = _read("pages/ExecutionStatus.tsx")
    dashboard_source = _read("pages/Dashboard.tsx")
    console_source = _read("pages/ExecutionConsole.tsx")
    lab_source = _read("pages/StrategyLab.tsx")

    required_runtime_copy_snippets = [
        'return "證據有限";',
        'return normalized ? humanizeExecutionReason(normalized) : "尚未提供";',
        'return "尚未提供";',
        '["current live structure bucket", "當前 live 結構 bucket"]',
        '["exact live lane", "精準路徑"]',
        '["runtime truth", "執行期真相"]',
    ]
    for snippet in required_runtime_copy_snippets:
        assert snippet in runtime_copy

    required_status_snippets = [
        '整體部署態勢',
        '證據有限',
        '僅公開資料 / 元資料觀測',
        '僅元資料快照',
        '餘額暫不可用',
    ]
    for snippet in required_status_snippets:
        assert snippet in status_source

    assert '"overall execution posture"' not in status_source
    assert '"limited evidence"' not in runtime_copy
    assert '"public-only / metadata only"' not in status_source
    assert '"metadata-only snapshot"' not in status_source
    assert 'reconciliation / recovery' not in status_source
    assert 'account snapshot' not in status_source
    assert 'runtime truth' not in status_source
    assert 'readiness。' not in status_source

    for source in (dashboard_source, console_source):
        assert '僅公開資料 / 元資料觀測' in source or '僅元資料快照' in source
        assert '"public-only / metadata only"' not in source
        assert '"metadata-only snapshot"' not in source

    assert '策略工作區' in lab_source
    assert '"Strategy workspace"' not in lab_source


def test_drift_and_live_pathology_cards_do_not_leak_raw_internal_english_tokens():
    drift_card_source = _read("components/RecentCanonicalDriftCard.tsx")
    pathology_card_source = _read("components/LivePathologySummaryCard.tsx")
    runtime_copy = _read("utils/runtimeCopy.ts")

    required_drift_snippets = [
        'function humanizeRecentDriftInterpretationLabel(',
        '最新視窗',
        '阻塞視窗',
        '分布病態',
        '市場狀態過度集中',
    ]
    for snippet in required_drift_snippets:
        assert snippet in drift_card_source

    assert 'latest ${latestInterpretation}' not in drift_card_source
    assert 'blocker ${blockingInterpretation}' not in drift_card_source
    assert 'distribution_pathology' not in drift_card_source
    assert 'regime_concentration' not in drift_card_source

    required_pathology_snippets = [
        '精準路徑',
        '外溢口袋',
        '外溢樣本',
        '焦點範圍樣本',
        '當前外溢',
        '參考 patch',
        '支持路徑',
        '治理路徑',
        '4H 主偏移',
        '下一步',
    ]
    for snippet in required_pathology_snippets:
        assert snippet in runtime_copy

    forbidden_pathology_tokens = [
        'exact lane',
        'spillover rows',
        'focus scope rows',
        'live spillover',
        'reference patch',
        'support route',
        'governance route',
        'top 4H shifts',
    ]
    for token in forbidden_pathology_tokens:
        assert token not in pathology_card_source

    assert '摘要版只保留目前精準路徑、外溢口袋與 patch 治理真相；完整診斷請看執行狀態。' in pathology_card_source
    assert '不要把精準路徑與更寬範圍的外溢口袋混成同一個目前 live 真相。' in pathology_card_source

    assert 'function humanizeRecentDriftInterpretationLabel(' in drift_card_source


def test_runtime_copy_humanizes_patch_profiles_embedded_blockers_and_verify_instructions():
    runtime_copy = _read("utils/runtimeCopy.ts")
    lab_source = _read("pages/StrategyLab.tsx")
    status_source = _read("pages/ExecutionStatus.tsx")
    pathology_card_source = _read("components/LivePathologySummaryCard.tsx")

    required_runtime_copy_snippets = [
        '["live exchange credential 尚未驗證", "交易所憑證尚未驗證。"]',
        '["order ack lifecycle 尚未驗證", "委託確認流程尚未驗證。"]',
        '["fill lifecycle 尚未驗證", "成交回補流程尚未驗證。"]',
        '["core_plus_macro_plus_all_4h", "核心 + 宏觀 + 全部 4H"]',
        '["feat_4h_bias50_formula", "4H bias50 公式"]',
        '["entry_quality >= 0.55 and allowed_layers > 0 without q35 applicability / support / guardrail regression", "進場品質 >= 0.55，且允許層數 > 0，同時不得出現 q35 適用性 / support / 保護欄回歸"]',
    ]
    for snippet in required_runtime_copy_snippets:
        assert snippet in runtime_copy

    required_lab_snippets = [
        'if (source === "feature_group_ablation.recommended_profile") return "全域 shrinkage 勝出配置";',
        'if (source === "bull_4h_pocket_ablation.exact_supported_profile") return "bull exact-supported 正式配置";',
        'if (source === "bull_4h_pocket_ablation.support_aware_profile") return "support-aware 正式配置";',
        'if (role === "global_shrinkage_winner") return "全域 shrinkage 勝出配置";',
        'if (role === "bull_exact_supported_production_profile") return "bull exact-supported 正式配置";',
        'if (role === "support_aware_production_profile") return "support-aware 正式配置";',
        '候選 patch {humanizeRuntimeDetailText(currentBucketRootCause?.candidate_patch_feature || "—")} · {currentBucketRootCauseActionLabel}',
    ]
    for snippet in required_lab_snippets:
        assert snippet in lab_source

    required_status_snippets = [
        '候選 patch {humanizeRuntimeDetailText(currentBucketRootCause?.candidate_patch_feature || "—")} · {currentBucketRootCauseActionLabel}',
    ]
    for snippet in required_status_snippets:
        assert snippet in status_source

    required_pathology_snippets = [
        'const compactPatchLabel = humanizeRuntimeDetailText(',
        'const patchProfileLabel = humanizeRuntimeDetailText(recommendedPatch?.recommended_profile || "未提供 profile");',
        '{patchProfileLabel}',
    ]
    for snippet in required_pathology_snippets:
        assert snippet in pathology_card_source

    assert 'return "global shrinkage winner";' not in lab_source
    assert 'return "bull exact-supported production";' not in lab_source
    assert 'return "support-aware production";' not in lab_source
    assert 'return "role unknown";' not in lab_source
    assert '候選 patch {currentBucketRootCause?.candidate_patch_feature || "—"} · {currentBucketRootCauseActionLabel}' not in status_source
    assert '候選 patch {currentBucketRootCause?.candidate_patch_feature || "—"} · {currentBucketRootCauseActionLabel}' not in lab_source
    assert '{recommendedPatch.recommended_profile || "未提供 profile"}' not in pathology_card_source
    assert 'function humanizeLivePathologyLabel(' in runtime_copy


def test_execution_surfaces_show_current_bucket_support_and_runtime_vs_calibration_counts_together():
    status_source = _read("pages/ExecutionStatus.tsx")
    console_source = _read("pages/ExecutionConsole.tsx")

    shared_snippets = [
        'const supportRowsLabel = runtimeStatusPending',
        'const supportRouteVerdictLabel = runtimeStatusPending',
        'const supportGovernanceRouteLabel = runtimeStatusPending',
        'const supportAlignmentCountsLabel = runtimeStatusPending',
        'const supportAlignmentSummaryLabel = runtimeStatusPending',
        '執行期 / 校準 ${liveRuntimeTruth?.runtime_exact_support_rows ?? "—"} / ${liveRuntimeTruth?.calibration_exact_lane_rows ?? "—"}`;',
        '{supportAlignmentCountsLabel}',
    ]
    for snippet in shared_snippets:
        assert snippet in status_source
        assert snippet in console_source

    for snippet in [
        '支持樣本 {supportRowsLabel}',
        '支持路徑 {supportRouteVerdictLabel}',
        '治理路徑 {supportGovernanceRouteLabel}',
        '對齊 {supportAlignmentSummaryLabel}',
    ]:
        assert snippet in status_source

    for snippet in [
        '>{supportRowsLabel}</div>',
        '支持路徑 {supportRouteVerdictLabel}',
        '治理路徑 {supportGovernanceRouteLabel}',
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
        '尚未有執行期委託，因此目前只能確認「沒有發現明顯對帳落差」，不可視為完整實單驗證。',
        'const continuityLabel = runtimeStatusPending',
        'const venueChecks = Array.isArray(metadataSmoke?.venues) ? metadataSmoke.venues : [];',
        'VenueReadinessSummary',
        '💼 Execution 摘要',
        'Dashboard 只保留 4 張 Bot 營運摘要卡；若要查看目前阻塞點詳情、元資料明細與恢復脈絡，請前往「執行狀態」。',
        'const liveScopePathologySummary =',
        'liveRuntimeTruth?.decision_quality_scope_pathology_summary',
        'LivePathologySummaryCard',
        '🧬 精準路徑 / 外溢口袋對照',
        'const recentCanonicalDrift = runtimeStatus?.execution?.recent_canonical_drift ?? executionSurfaceContract?.recent_canonical_drift ?? runtimeStatus?.recent_canonical_drift ?? null;',
        'RecentCanonicalDriftCard',
        'summary={recentCanonicalDrift}',
        'pending={runtimeStatusPending && !recentCanonicalDrift}',
        'title="📉 最近 canonical drift"',
        '前往 Bot 營運 →',
        '前往執行狀態 →',
        '部署狀態',
        '資金 / 曝險',
        '元資料新鮮度',
        '對帳 / 恢復',
        '🩹 啟動檢查 / 連續性',
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
        'humanizeSupportRouteLabel',
        'humanizeSupportGovernanceRouteLabel',
        'const dashboardPrimaryRuntimeMessage = liveRuntimeTruth?.deployment_blocker_reason',
        'const dashboardPrimaryRuntimeMessageLabel = runtimeStatusPending',
        'humanizeExecutionReason(',
        'const dashboardVenueBlockers = Array.isArray(executionSurfaceContract?.live_ready_blockers)',
        'const dashboardVenueBlockersLabel = runtimeStatusPending',
        'dashboardVenueBlockers.map((item) => humanizeExecutionReason(item)).join(" · ")',
        'const dashboardSupportRouteVerdictLabel = runtimeStatusPending',
        'humanizeSupportRouteLabel(liveRuntimeTruth?.support_route_verdict || null)',
        'const dashboardSupportGovernanceRouteLabel = runtimeStatusPending',
        'humanizeSupportGovernanceRouteLabel(liveRuntimeTruth?.support_governance_route || null)',
        'const dashboardSupportRowsLabel = runtimeStatusPending',
        'const dashboardSupportGapLabel = runtimeStatusPending',
        'const executionModeLabel = runtimeStatusPending ? "同步中" : (executionSummary?.mode || accountSummary?.mode || "unknown");',
        'const executionVenueLabel = runtimeStatusPending ? "同步中" : (executionSummary?.venue || accountSummary?.venue || "—");',
        'const dashboardExecutionStatusValue = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");',
        'value={dashboardExecutionStatusValue}',
        '目前阻塞點 {dashboardCurrentLiveBlockerLabel}',
        '當前 bucket {dashboardSupportRowsLabel} · gap {dashboardSupportGapLabel} · 支持路徑 {dashboardSupportRouteVerdictLabel} · 治理路徑 {dashboardSupportGovernanceRouteLabel}',
        '場館阻塞 {dashboardVenueBlockersLabel}',
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


def test_execution_status_humanizes_readiness_scope_with_shared_runtime_copy():
    status_source = _read("pages/ExecutionStatus.tsx")

    required_snippets = [
        'const readinessScopeLabel = runtimeStatusPending',
        'humanizeRuntimeDetailText(executionSurfaceContract?.readiness_scope || "runtime_governance_visibility_only")',
        '治理範圍 ${readinessScopeLabel}',
    ]
    for snippet in required_snippets:
        assert snippet in status_source

    assert 'scope ${executionSurfaceContract?.readiness_scope || "runtime_governance_visibility_only"}' not in status_source


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
        'Dashboard 正在同步目前阻塞點；在 /api/status 完成前不把方向訊號當成可操作 CTA。',
        '目前阻塞點：${blockerLabel}。在阻塞解除前，Dashboard 只保留分析摘要與導流，不把方向訊號包裝成可操作建議。',
        '<div className="text-sm text-slate-200 leading-relaxed">{displaySummary}</div>',
        'Dashboard 建議卡暫不提供快捷下單，避免目前阻塞點真相尚未到位前出現誤導 CTA。',
        '目前只保留分析摘要與阻塞後續動作；若要查看目前阻塞點詳情與恢復脈絡，請改到執行狀態 / Bot 營運頁。',
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
        'SignalBanner 目前只提供快捷下單 / 自動交易切換；完整阻塞點、Guardrail context、治理狀態與恢復脈絡請到執行狀態頁查看。',
        '前往執行狀態頁 →',
        'href="/execution/status"',
        'fetch("/api/trade", {',
        'fetch("/api/automation/toggle", {',
        'fetch("/api/predict/confidence")',
        'humanizeExecutionReason',
        'humanizeRuntimeClosureStateLabel',
        'humanizeRuntimeDetailText',
        'const deploymentBlockerDetails = runtimeDecision?.deployment_blocker_details ?? null;',
        'const breakerRecentWindow = deploymentBlockerDetails?.recent_window ?? null;',
        'const breakerRelease = deploymentBlockerDetails?.release_condition ?? null;',
        'const circuitBreakerActive = runtimeDecision?.deployment_blocker === "circuit_breaker_active";',
        'const runtimeAllowedLayersRawReasonLabel = humanizeExecutionReason(runtimeDecision?.allowed_layers_raw_reason || null);',
        'const runtimeAllowedLayersReasonLabel = humanizeRuntimeDetailText(runtimeDecision?.allowed_layers_reason || null);',
        'const runtimeClosureStateLabel = humanizeRuntimeClosureStateLabel(',
        'const runtimeClosureSummaryLabel = humanizeRuntimeDetailText(',
        '部署閉環 {runtimeClosureStateLabel}',
        'circuit breaker：recent 50 release window',
        '不要把 support / component patch 當成 breaker release 替代品。',
        'SignalBanner 只同步 release math，不可把這裡的快捷面板誤讀成 deployment readiness。',
        '原始原因 {runtimeAllowedLayersRawReasonLabel}',
        '最終原因 {runtimeAllowedLayersReasonLabel}',
        'capacity opened but signal still HOLD',
        'patch active but execution still blocked',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_confidence_indicator_distinguishes_capacity_opened_vs_patch_blocked_states():
    source = _read("components/ConfidenceIndicator.tsx")
    required_snippets = [
        'humanizeCurrentLiveBlockerLabel',
        'humanizeExecutionReason',
        'humanizeQ15FloorCrossVerdictLabel',
        'humanizeQ15ComponentExperimentVerdictLabel',
        'humanizeQ15BucketRootCauseAction',
        'humanizeQ15BucketRootCauseLabel',
        'humanizeSupportProgressStatusLabel',
        'const q15PatchExecutionBlocked = Boolean(',
        'const q15PatchCapacityOpened = Boolean(',
        'const q15SupportAuditApplicable = bucketKey === "q15" || bucketKey.endsWith("|q15");',
        'const q15FloorCrossLabel = q15SupportAuditApplicable',
        'humanizeQ15FloorCrossVerdictLabel(floorCrossVerdict || "—")',
        'const q15ComponentExperimentLabel = q15SupportAuditApplicable',
        'humanizeQ15ComponentExperimentVerdictLabel(componentExperimentVerdict || "—")',
        '目前 bucket ${currentLiveStructureBucket || "—"}；q15 floor-cross drill-down 只保留 reference-only，不代表 /api/status 缺資料。',
        '目前 live row 已離開 q15 lane；請改看 current live blocker 與 current bucket root cause，而不是把 q15 experiment 空值誤讀成 blocker truth。',
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
        'q15 floor-cross legality',
        'q15 component experiment',
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
        '掃描結果升格為程式內建配置',
        '無交易 placeholder',
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
        'humanizeSupportRouteLabel',
        'humanizeSupportGovernanceRouteLabel',
        'humanizeRuntimeClosureStateLabel',
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
        'const runtimeClosureStateLabel = liveExecutionSyncPending',
        'humanizeRuntimeClosureStateLabel(',
        'const liveSupportRouteVerdict = liveDecisionStatus?.support_route_verdict ?? liveRuntimeTruth?.support_route_verdict ?? null;',
        'const liveSupportGovernanceRoute = liveDecisionStatus?.support_governance_route ?? liveRuntimeTruth?.support_governance_route ?? null;',
        'const liveSupportRouteVerdictLabel = liveExecutionSyncPending',
        'humanizeSupportRouteLabel(liveSupportRouteVerdict)',
        'const liveSupportGovernanceRouteLabel = liveExecutionSyncPending',
        'humanizeSupportGovernanceRouteLabel(liveSupportGovernanceRoute)',
        'const liveSupportRowsLabel = liveExecutionSyncPending',
        'const liveSupportGapLabel = liveExecutionSyncPending',
        'const liveSupportRouteSummaryLabel = liveExecutionSyncPending',
        '當前 bucket ${liveSupportRowsLabel} · gap ${liveSupportGapLabel} · 支持路徑 ${liveSupportRouteVerdictLabel} · 治理路徑 ${liveSupportGovernanceRouteLabel}`;',
        'const liveRouting = liveRuntimeTruth?.sleeve_routing ?? null;',
        'const liveActiveSleeves = Array.isArray(liveRouting?.active_sleeves) ? liveRouting.active_sleeves : [];',
        'const liveInactiveSleeves = Array.isArray(liveRouting?.inactive_sleeves) ? liveRouting.inactive_sleeves : [];',
        '🎯 決策品質',
        'DQ {formatDecimal(activeResult?.avg_decision_quality_score, 3)}',
        '策略模組選擇',
        '先選 1 個主 preset，再疊加 modifier；只看摘要，不先讀長說明。',
        '已選取',
        '即時部署同步',
        'subtitle={liveExecutionSyncSubtitle}',
        '目前阻塞點 {currentLiveBlockerLabel}',
        '{reconciliationBadgeLabel} · {reconciliationCheckedAtLabel}',
        'const liveScopePathologySummary =',
        'liveRuntimeTruth?.decision_quality_scope_pathology_summary',
        'const currentLiveBlocker =',
        'const venueReadinessBlockers = liveExecutionBlockers;',
        'const currentLiveBlockerSummary =',
        'LivePathologySummaryCard',
        '🧬 精準路徑 / 外溢口袋對照',
        '目前阻塞點',
        '場館阻塞',
        '部署閉環',
        '啟用倉位腿',
        '元資料新鮮度',
        '前往 Bot 營運 →',
        '前往執行狀態 →',
        '診斷頁面 {humanizeRuntimeDetailText(executionDiagnosticsSurface?.label || "執行狀態")}',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert 'Execution runtime blocker sync' not in source
    assert 'Live 部署同步' not in source


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
        '目前阻塞點 {currentLiveBlockerLabel}',
        '當前 bucket {liveSupportRowsLabel} · gap {liveSupportGapLabel}',
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
        'title="📉 最近 canonical drift"',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert source.index('LivePathologySummaryCard') < source.index('RecentCanonicalDriftCard')


def test_recent_canonical_drift_card_surfaces_latest_and_blocking_windows():
    source = _read("components/RecentCanonicalDriftCard.tsx")
    required_snippets = [
        'type RecentCanonicalDriftWindowPayload = {',
        'blocking_window?: RecentCanonicalDriftWindowPayload | null;',
        'const blockingWindow = summary?.blocking_window ?? null;',
        'const hasDistinctBlockingWindow = Boolean(',
        'const latestInterpretationLabel = humanizeRecentDriftInterpretationLabel(latestWindowSummary?.drift_interpretation || "unavailable");',
        'const blockingInterpretationLabel = humanizeRecentDriftInterpretationLabel(blockingWindowSummary?.drift_interpretation || "unavailable");',
        '`最新視窗 · ${latestInterpretationLabel}`',
        '`阻塞視窗 · ${blockingInterpretationLabel}`',
        '最新 recent-window',
        '當前 blocker pocket',
    ]
    for snippet in required_snippets:
        assert snippet in source


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
        '當前 bucket 根因',
        '當前 bucket {currentBucketRootCauseBucket}',
        '候選 patch {humanizeRuntimeDetailText(currentBucketRootCause?.candidate_patch_feature || "—")} · {currentBucketRootCauseActionLabel}',
        '近邊界樣本 {currentBucketRootCause?.near_boundary_rows ?? "—"}',
        '下一步請驗證 {humanizeRuntimeDetailText(currentBucketRootCause?.verify_next || "—")}',
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
        '當前 bucket 根因',
        '當前 bucket {currentBucketRootCauseBucket}',
        '候選 patch {humanizeRuntimeDetailText(currentBucketRootCause?.candidate_patch_feature || "—")} · {currentBucketRootCauseActionLabel}',
        '近邊界樣本 {currentBucketRootCause?.near_boundary_rows ?? "—"}',
        '下一步請驗證 {humanizeRuntimeDetailText(currentBucketRootCause?.verify_next || "—")}',
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
        'humanizeSupportRouteLabel',
        'humanizeSupportGovernanceRouteLabel',
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
        'const patchProfileLabel = humanizeRuntimeDetailText(recommendedPatch?.recommended_profile || "未提供 profile");',
        'recommendedPatch.reference_patch_scope',
        'recommendedPatch.reference_source',
        'support_governance_route?: string | null;',
        'const supportRouteLabel = supportRouteVerdict || recommendedPatch?.support_route_verdict || null;',
        'const supportGovernanceRouteLabel = supportGovernanceRoute || recommendedPatch?.support_governance_route || null;',
        'const supportRouteDisplayLabel = humanizeSupportRouteLabel(supportRouteLabel);',
        'const supportGovernanceRouteDisplayLabel = humanizeSupportGovernanceRouteLabel(supportGovernanceRouteLabel);',
        '{supportRouteLabel ? ` · ${PATHOLOGY_LABELS.supportRoute} ${supportRouteDisplayLabel}` : ""}',
        '{supportGovernanceRouteLabel ? ` · ${PATHOLOGY_LABELS.governanceRoute} ${supportGovernanceRouteDisplayLabel}` : ""}',
        'recommendedPatch.recommended_action',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_live_pathology_summary_card_surfaces_focus_scope_vs_spillover_context():
    source = _read("components/LivePathologySummaryCard.tsx")
    required_snippets = [
        'const focusScopeLabel = humanizeRuntimeDetailText(summary.focus_scope_label || summary.focus_scope || "範圍");',
        'const spilloverLabel = summary.focus_scope_label',
        '${humanizeRuntimeDetailText(summary.focus_scope_label)} ${PATHOLOGY_LABELS.spilloverPocket}',
        '較寬範圍 ${PATHOLOGY_LABELS.spilloverPocket}',
        '{PATHOLOGY_LABELS.focusScopeRows} {summary.focus_scope_rows ?? "—"}',
        '${PATHOLOGY_LABELS.spilloverRows} ${spillover.extra_rows}',
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
        'const compactPatchLabel = humanizeRuntimeDetailText(',
        'const compactPatchStatusLabel = recommendedPatch ? formatPatchStatus(recommendedPatch.status) : null;',
        'const currentBucketSupportRows = recommendedPatch?.current_live_structure_bucket_rows ?? exactLane?.current_live_structure_bucket_rows;',
        'const currentBucketSupportMinimum = recommendedPatch?.minimum_support_rows ?? null;',
        'const currentBucketSupportLabel = currentBucketSupportRows != null',
        'const exactLaneRowsLabel = exactLane?.rows != null',
        'const exactLaneHistoricalBucket = exactLane?.dominant_structure_bucket || null;',
        'PATHOLOGY_LABELS.currentBucketSupport',
        'PATHOLOGY_LABELS.exactLaneCohort',
        'PATHOLOGY_LABELS.historicalLaneBucket',
        'const supportAlignmentStatusLabel = formatSupportAlignmentStatus(supportAlignmentStatus);',
        'const supportAlignmentCountsLabel = runtimeExactSupportRows != null || calibrationExactLaneRows != null',
        '執行期 / 校準 ${runtimeExactSupportRows ?? "—"} / ${calibrationExactLaneRows ?? "—"}',
        '{exactLaneRowsLabel}',
        '{currentBucketSupportLabel}',
        '{compactPatchStatusLabel || "patch 狀態未提供"}',
        '{supportRouteLabel ? ` · ${PATHOLOGY_LABELS.supportRoute} ${supportRouteDisplayLabel}` : ""}',
        '{supportAlignmentStatusLabel ? ` · ${supportAlignmentStatusLabel}` : ""}',
    ]
    for snippet in required_snippets:
        assert snippet in source
def test_runtime_copy_humanizes_support_and_runtime_route_tokens_for_operator_surfaces():
    runtime_copy_source = _read("utils/runtimeCopy.ts")
    for snippet in [
        'const SUPPORT_ROUTE_LABEL_MAPPINGS',
        'const RUNTIME_CLOSURE_STATE_LABEL_MAPPINGS',
        '["exact_bucket_unsupported_block", "exact support 尚未建立"]',
        '["no_support_proxy", "目前沒有可用 proxy"]',
        '["patch_inactive_or_blocked", "僅保留治理參考"]',
        'export function humanizeSupportRouteLabel(value?: string | null): string {',
        'export function humanizeSupportGovernanceRouteLabel(value?: string | null): string {',
        'export function humanizeRuntimeClosureStateLabel(value?: string | null, fallback?: string | null): string {',
    ]:
        assert snippet in runtime_copy_source


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
        'return "公開資料";',
        'return "停用";',
        'const blockerSummary = (item.blockers?.length ? item.blockers : defaultProofSummary)',
        '.map((entry) => humanizeExecutionReason(entry))',
        '設定 {item.enabled_in_config ? "啟用" : "停用"}',
        '憑證 {item.credentials_configured ? "已配置" : "僅公開資料"}',
        '元資料契約 {item.ok ? "正常" : "失敗"}',
        '待補實單證據',
        'step {item.contract?.step_size ?? "—"}',
        'tick {item.contract?.tick_size ?? "—"}',
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_venue_readiness_summary_supports_compact_operator_summary_mode():
    source = _read("components/VenueReadinessSummary.tsx")
    required_snippets = [
        'if (compact) {',
        '待補實單證據 · {blockerSummary}',
        '設定 {item.enabled_in_config ? "啟用" : "停用"} · 憑證 {item.credentials_configured ? "已配置" : "僅公開資料"} · 元資料 {item.ok ? "正常" : "失敗"}',
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
        '"observed-ticking": "已觀察到自然排程觸發"',
        'const hostSchedulerSummary = buildHostSchedulerSummary(governance);',
        'hostSchedulerSummary ? `外部監看 ${hostSchedulerSummary}` : null,',
        'governance?.operator_message || "尚未取得治理訊息。"',
        'return <div>正在向 /api/status 取得元資料檢查。</div>;',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert '已觀察到自然 ticking' not in source


def test_runtime_copy_humanizes_execution_governance_without_raw_runtime_english():
    source = _read("utils/runtimeCopy.ts")
    required_snippets = [
        '["runtime_governance_visibility_only", "目前僅提供執行治理可視化。"]',
        '["runtime_governance_visibility_only", "執行治理可視化"]',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert 'runtime 治理可視化' not in source


def test_execution_status_humanizes_hidden_diagnostics_runtime_order_and_timeline_tokens():
    runtime_copy = _read("utils/runtimeCopy.ts")
    status_source = _read("pages/ExecutionStatus.tsx")

    required_runtime_copy_snippets = [
        '["signal_banner", "訊號橫幅"]',
        '["dashboard", "儀表板"]',
        '["no_runtime_order", "尚無執行期委託"]',
        '["required", "需要補重播"]',
    ]
    for snippet in required_runtime_copy_snippets:
        assert snippet in runtime_copy

    required_status_snippets = [
        'function humanizeLifecycleList(values?: Array<string | null | undefined>, emptyLabel = "無"): string {',
        'status ? humanizeLifecycleDiagnosticLabel(status) : null,',
        'if (!Array.isArray(records) || records.length === 0) return "無";',
        'qty !== null ? `數量 ${formatNumber(qty, 4)}` : null,',
        'price !== null ? `價格 ${formatNumber(price, 2)}` : null,',
        'humanizeRuntimeDetailText(accountSummary?.operator_message || accountSummary?.recovery_hint || accountSummary?.health?.error || "—")',
        'canonical 路由 {humanizeRuntimeDetailText(executionSurfaceContract?.canonical_execution_route || "dashboard")}',
        '快捷入口 {humanizeRuntimeDetailText(executionSurfaceContract?.shortcut_surface?.name || "signal_banner")} · {humanizeLifecycleDiagnosticLabel(executionSurfaceContract?.shortcut_surface?.status || "available")}',
        '原因 {humanizeRuntimeDetailText(executionReconciliation?.open_order_alignment?.reason || "—")}',
        '階段 {humanizeLifecycleDiagnosticLabel(lifecycleAudit?.stage || "unknown")}',
        '缺少生命週期事件 {humanizeLifecycleList(lifecycleContract?.missing_event_types, "無")}',
        '下一個產物 {humanizeRuntimeDetailText(lifecycleContract?.operator_next_artifact || "—")}',
        'humanizeRuntimeDetailText(lifecycleContract?.venue_lanes_summary || "尚未提供場館通道摘要。")',
        '重播 {humanizeLifecycleDiagnosticLabel(lane.restart_replay_status || "unknown")}',
        '最新事件 {humanizeRuntimeDetailText(executionReconciliation?.lifecycle_timeline?.latest_event?.event_type || "—")} · {humanizeLifecycleDiagnosticLabel(executionReconciliation?.lifecycle_timeline?.latest_event?.order_state || "unknown")}',
        'humanizeRuntimeDetailText(event.summary || event.source || "—")',
    ]
    for snippet in required_status_snippets:
        assert snippet in status_source

    assert '尚無 runtime order' not in runtime_copy
    assert '需要補 replay' not in runtime_copy
    assert 'if (!Array.isArray(records) || records.length === 0) return "none";' not in status_source
    assert 'qty !== null ? `qty ${formatNumber(qty, 4)}` : null,' not in status_source
    assert 'price !== null ? `price ${formatNumber(price, 2)}` : null,' not in status_source
    assert '快捷入口 {executionSurfaceContract?.shortcut_surface?.name || "signal_banner"} · {executionSurfaceContract?.shortcut_surface?.status || "available"}' not in status_source
    assert '狀態 {executionReconciliation?.open_order_alignment?.status || "unknown"}' not in status_source
    assert '缺少生命週期事件 {(lifecycleContract?.missing_event_types || []).join(" / ") || "none"}' not in status_source


def test_execution_status_reuses_shared_venue_readiness_component_and_explains_public_only_balances():
    source = _read("pages/ExecutionStatus.tsx")
    required_snippets = [
        'import VenueReadinessSummary from "../components/VenueReadinessSummary";',
        '<VenueReadinessSummary venues={venueChecks} className="mt-4" />',
        'const accountBalanceUnavailableLabel = !accountCredentialsConfigured',
        '尚未配置交易所憑證，因此私有餘額暫不可見。',
    ]
    for snippet in required_snippets:
        assert snippet in source
    assert 'item.ok ? "OK" : "FAIL"' not in source


def test_dashboard_execution_summary_explains_public_only_balance_unavailability():
    source = _read("pages/Dashboard.tsx")
    required_snippets = [
        'const accountBalanceUnavailableLabel = !accountCredentialsConfigured',
        '尚未配置交易所憑證，因此私有餘額暫不可見。',
        'accountBalanceSummaryValue',
        'accountBalanceSummaryTotal',
        '總額 {accountBalanceSummaryTotal} · 倉位 {positionCount} · 掛單 {openOrderCount}',
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
        'type ApiBaseHealthProbe = {',
        'window.localStorage.setItem(ACTIVE_API_BASE_STORAGE_KEY, base);',
        'async function probeApiBaseHealth(base: string): Promise<ApiBaseHealthProbe> {',
        'const resp = await fetch(buildApiUrlForBase("/health", base), {',
        'const runtimeBuild = payload?.runtime_build && typeof payload.runtime_build === "object"',
        'headSyncStatus: typeof runtimeBuild?.head_sync_status === "string" ? runtimeBuild.head_sync_status : null,',
        'function scoreApiBaseHealthProbe(probe: ApiBaseHealthProbe): number {',
        'if (probe.headSyncStatus === "current_head_commit") score += 5;',
        'if (probe.headSyncStatus === "stale_head_commit") score -= 5;',
        'function scoreApiBaseRuntimeContract(payload: unknown): number {',
        'const recentCanonicalDrift = execution?.recent_canonical_drift',
        'async function probeApiBaseRuntimeContractScore(base: string): Promise<number> {',
        'const resp = await fetch(buildApiUrlForBase("/api/status", base), {',
        'const capabilityResults = await Promise.all(healthyCandidates.map(async (probe) => {',
        'const healthScore = scoreApiBaseHealthProbe(probe);',
        'const runtimeContractScore = await probeApiBaseRuntimeContractScore(probe.base);',
        'totalScore: healthScore + runtimeContractScore,',
        'if (probe.totalScore > best.totalScore) return probe;',
        'persistActiveApiBase(bestCapability?.base ?? healthyCandidates[0]?.base ?? null);',
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
