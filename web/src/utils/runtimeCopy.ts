import { getSenseConfig } from "../config/senses";

const EXECUTION_REASON_MAPPINGS: Array<[string, string]> = [
  ["live exchange credential 尚未驗證", "交易所憑證尚未驗證。"],
  ["order ack lifecycle 尚未驗證", "委託確認流程尚未驗證。"],
  ["fill lifecycle 尚未驗證", "成交回補流程尚未驗證。"],
  ["live exchange credential", "交易所憑證尚未驗證。"],
  ["order ack lifecycle", "委託確認流程尚未驗證。"],
  ["fill lifecycle", "成交回補流程尚未驗證。"],
  ["under_minimum_exact_live_structure_bucket_blocks_trade", "目前精準樣本已開始累積，但仍低於最小可部署門檻，暫不交易。"],
  ["under_minimum_exact_live_structure_bucket", "目前精準樣本已開始累積，但仍低於最小可部署門檻。"],
  ["unsupported_exact_live_structure_bucket_blocks_trade", "目前精準樣本尚未建立，暫不交易。"],
  ["unsupported_exact_live_structure_bucket", "目前精準樣本尚未建立。"],
  ["unsupported_live_structure_bucket_blocks_trade", "目前 live bucket 支持仍不足，暫不交易。"],
  ["unsupported_live_structure_bucket", "目前 live bucket 支持仍不足。"],
  ["decision_quality_below_trade_floor", "目前決策品質不足，暫不建議進場。"],
  ["recent_distribution_pathology_blocks_trade", "近期分佈病態，暫不交易。"],
  ["circuit_breaker_blocks_trade", "目前觸發保護機制，暫不交易。"],
  ["circuit_breaker_active", "目前觸發保護機制，暫停部署。"],
  ["deployment_guardrail_blocks_trade", "部署保護欄阻擋交易。"],
  ["patch_inactive_or_blocked", "目前 patch 尚未啟用，或仍被其他條件阻擋。"],
  ["patch_active_but_execution_blocked", "目前 patch 已套用，但 execution 仍被 blocker 擋住。"],
  ["support_closed_but_trade_floor_blocked", "精準樣本已閉環，但交易門檻仍未通過。"],
  ["exact_bucket_present_but_below_minimum", "目前精準樣本已出現，但仍低於可部署最低門檻。"],
  ["exact_live_bucket_present_but_below_minimum", "目前精準樣本已開始累積，但仍低於可部署最低門檻。"],
  ["exact_bucket_unsupported_block", "目前精準樣本尚未建立，僅能保留治理參考。"],
  ["exact_bucket_missing_proxy_reference_only", "目前只有近似樣本參考，仍不可直接部署。"],
  ["exact_bucket_missing_exact_lane_proxy_only", "目前只有精準路徑近似樣本參考，仍不可直接部署。"],
  ["no_support_proxy", "目前沒有可用近似樣本。"],
  ["regime_gate_block", "目前市場閘門仍阻塞。"],
  ["runtime_governance_visibility_only", "目前僅提供執行治理可視化。"],
  ["stalled_under_minimum", "目前最小樣本門檻仍未達標。"],
  ["unsupported", "目前條件尚未通過可部署檢查。"],
];

const CURRENT_LIVE_BLOCKER_LABEL_MAPPINGS: Array<[string, string]> = [
  ["under_minimum_exact_live_structure_bucket", "精準樣本未達最小門檻"],
  ["unsupported_exact_live_structure_bucket", "精準樣本尚未建立"],
  ["decision_quality_below_trade_floor", "決策品質未達門檻"],
  ["circuit_breaker_active", "風控熔斷中"],
  ["unsupported_live_structure_bucket", "目前 live bucket 支持不足"],
  ["exact_live_lane_toxic_sub_bucket_current_bucket", "精準路徑毒性子 bucket"],
];

const SUPPORT_ROUTE_LABEL_MAPPINGS: Array<[string, string]> = [
  ["exact_bucket_supported", "精準樣本已就緒"],
  ["exact_bucket_present_but_below_minimum", "精準樣本未達最小門檻"],
  ["exact_bucket_missing_exact_lane_proxy_only", "精準樣本缺口僅能參考精準路徑近似樣本"],
  ["exact_bucket_missing_proxy_reference_only", "精準樣本缺口僅能參考近似樣本"],
  ["exact_bucket_unsupported_block", "精準樣本尚未建立"],
  ["unsupported_exact_live_structure_bucket", "精準樣本尚未建立"],
  ["under_minimum_exact_live_structure_bucket", "精準樣本未達最小門檻"],
  ["no_rows", "目前沒有可用歷史列"],
];

const SUPPORT_GOVERNANCE_ROUTE_LABEL_MAPPINGS: Array<[string, string]> = [
  ["no_support_proxy", "目前沒有可用近似樣本"],
  ["exact_live_bucket_proxy_available", "已有精準 bucket 近似樣本"],
  ["exact_live_bucket_supported", "精準樣本已就緒"],
  ["exact_bucket_present_but_below_minimum", "精準樣本已開始累積"],
  ["exact_live_bucket_present_but_below_minimum", "精準樣本已開始累積"],
  ["exact_bucket_supported_proxy_not_required", "精準樣本已就緒，不需近似樣本"],
  ["proxy_governance_reference_only_exact_support_blocked", "近似樣本僅供治理參考"],
  ["exact_bucket_missing_proxy_reference_only", "近似樣本僅供治理參考"],
  ["exact_bucket_missing_exact_lane_proxy_only", "精準路徑近似樣本僅供治理參考"],
];

const RUNTIME_CLOSURE_STATE_LABEL_MAPPINGS: Array<[string, string]> = [
  ["deployment_guardrail_blocks_trade", "部署保護欄阻擋交易"],
  ["patch_active_but_execution_blocked", "patch 已套用但 execution 仍阻塞"],
  ["patch_inactive_or_blocked", "僅保留治理參考"],
  ["support_closed_but_trade_floor_blocked", "精準樣本已閉環但交易門檻仍阻塞"],
  ["circuit_breaker_active", "風控熔斷中"],
  ["capacity_opened_signal_hold", "容量已開但訊號仍 HOLD"],
  ["runtime_visible_preview", "runtime 預覽中"],
];

const SUPPORT_PROGRESS_STATUS_LABEL_MAPPINGS: Array<[string, string]> = [
  ["exact_supported", "精準樣本已就緒"],
  ["regressed_under_minimum", "精準樣本從已就緒回落到未達門檻"],
  ["stalled_under_minimum", "最小門檻尚未達標"],
  ["deployable", "已達可部署條件"],
  ["ready", "已就緒"],
  ["pending", "持續累積中"],
  ["accumulating", "持續累積中"],
  ["unsupported", "尚未建立"],
];

type SupportProgressLike = {
  status?: string | null;
  current_rows?: number | null;
  delta_vs_previous?: number | null;
  regressed_from_supported?: boolean | null;
  recent_supported_rows?: number | null;
  recent_supported_heartbeat?: string | null;
  delta_vs_recent_supported?: number | null;
};

const EXECUTION_MODE_LABEL_MAPPINGS: Array<[string, string]> = [
  ["paper", "模擬倉"],
  ["dry_run", "模擬委託"],
  ["live_canary", "實盤 Canary"],
  ["live", "實盤"],
  ["unknown", "未提供"],
];

const EXECUTION_VENUE_LABEL_MAPPINGS: Array<[string, string]> = [
  ["binance", "Binance"],
  ["okx", "OKX"],
  ["unknown", "未提供"],
];

const TRADE_REASON_LABEL_MAPPINGS: Array<[string, string]> = [
  ["tp_turning_point", "頂部轉折止盈"],
  ["take_profit", "止盈"],
  ["tp_fixed", "固定止盈"],
  ["stop_loss", "停損"],
  ["signal_exit", "訊號出場"],
  ["time_exit", "時間到期出場"],
];

const Q15_FLOOR_CROSS_VERDICT_LABEL_MAPPINGS: Array<[string, string]> = [
  ["math_cross_possible_but_illegal_without_exact_support", "數學上可跨 floor，但 exact support 未就緒"],
  ["legal_to_relax_runtime_gate", "可合法放寬 runtime gate"],
  ["reference_only", "僅供治理參考"],
];

const Q15_COMPONENT_EXPERIMENT_VERDICT_LABEL_MAPPINGS: Array<[string, string]> = [
  ["reference_only_until_exact_support_ready", "exact support 就緒前僅供參考"],
  ["exact_supported_component_experiment_ready", "可進入 exact-supported 元件驗證"],
  ["runtime_patch_no_material_improvement", "runtime patch 無明顯改善"],
  ["not_applicable", "目前不適用"],
];

const FEATURE_KEY_ALIAS_MAPPINGS: Record<string, string> = {
  "4h_dist_swing_low": "4h_dist_sl",
};

const FEATURE_KEY_LABEL_OVERRIDES: Record<string, { name: string; shortLabel: string }> = {
  local_bottom_score: { name: "局部底部分數", shortLabel: "局部底部" },
  local_top_score: { name: "局部頂部分數", shortLabel: "局部頂部" },
  "4h_dist_swing_high": { name: "4H 壓力距離", shortLabel: "4H壓力" },
};

const RUNTIME_DETAIL_TOKEN_REPLACEMENTS: Array<[string, string]> = [
  ["top-level live baseline", "頂層 live 基準"],
  ["component-experiment readiness", "元件實驗就緒"],
  ["component experiment readiness", "元件實驗就緒"],
  ["Consecutive loss streak:", "連續虧損筆數："],
  ["Recent 50-sample win rate", "最近 50 筆勝率"],
  ["recent 50 win rate", "最近 50 筆勝率"],
  ["release condition =", "解除條件："],
  ["streak < 50", "連續虧損筆數 < 50"],
  ["Release Circuit Breaker Then Rerun Q35 Scaling Audit", "先解除風控熔斷，再重跑 q35 分段校準審核"],
  ["defer_until_circuit_breaker_releases", "待風控熔斷解除後再處理"],
  ["defer until circuit breaker releases", "待風控熔斷解除後再處理"],
  ["runtime_blocker_preempts_q35_scaling", "風控熔斷優先，暫不處理 q35 分段校準"],
  ["q35 scaling audit", "q35 分段校準審核"],
  ["q35 scaling", "q35 分段校準"],
  ["q35 formula / calibration", "q35 公式 / 校準"],
  ["canonical circuit breaker", "正式風控熔斷"],
  ["circuit breaker", "風控熔斷"],
  ["exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade", "精準路徑毒性子 bucket 阻擋交易"],
  ["exact_live_lane_toxic_sub_bucket_current_bucket", "精準路徑毒性子 bucket"],
  ["unsupported_exact_live_structure_bucket_blocks_trade", "精準樣本尚未建立，暫不交易"],
  ["under_minimum_exact_live_structure_bucket_blocks_trade", "精準樣本未達最小門檻，暫不交易"],
  ["unsupported_live_structure_bucket_blocks_trade", "live bucket 支持不足，暫不交易"],
  ["recent_distribution_pathology_blocks_trade", "近期分佈病態，暫不交易"],
  ["circuit_breaker_blocks_trade", "風控熔斷中，暫不交易"],
  ["deployment_guardrail_blocks_trade", "部署保護欄阻擋交易"],
  ["exact-lane", "精準路徑"],
  ["exact_supported_component_experiment_ready", "精準樣本元件實驗就緒"],
  ["exact_live_bucket_supported", "精準樣本已就緒"],
  ["exact live bucket supported", "精準樣本已就緒"],
  ["exact_live_bucket_proxy_available", "已有精準 bucket 近似樣本"],
  ["exact_live_lane_proxy_available", "已有精準路徑近似樣本"],
  ["current_structure_quality", "目前結構分數"],
  ["component scoring", "元件評分"],
  ["boundary tweak", "邊界微調"],
  ["toxic sub-bucket", "毒性子 bucket"],
  ["hold-only", "僅觀察"],
  ["entry_quality >= 0.55 and allowed_layers > 0 without q35 applicability / support / guardrail regression", "進場品質 >= 0.55，且允許層數 > 0，同時不得出現 q35 適用性 / 樣本支持 / 保護欄回歸"],
  ["entry_quality=", "進場分數="],
  ["entry_quality", "進場分數"],
  ["core_plus_macro_plus_all_4h", "核心 + 宏觀 + 全部 4H"],
  ["feat_4h_bias50_formula", "4H bias50 公式"],
  ["signal_banner", "訊號橫幅"],
  ["spot-long", "現貨多單"],
  ["label_imbalance", "標籤失衡"],
  ["constant_target", "目標值固定"],
  ["regime_shift", "市場狀態切換"],
  ["regime_concentration", "市場狀態過度集中"],
  ["exact support", "精準樣本"],
  ["support-aware", "支援樣本感知"],
  ["base-stack redesign", "基礎堆疊重設"],
  ["base-stack", "基礎堆疊"],
  ["discriminative", "保留辨別力"],
  ["trade floor", "交易門檻"],
  ["no-deploy", "不可部署"],
  ["closure", "閉環"],
  ["uplift", "上修"],
  ["support 補滿前", "精準樣本補滿前"],
  ["support 閉環", "精準樣本閉環"],
  ["runtime 只能維持", "執行期只能維持"],
  ["primary sleeves", "主要倉位腿"],
  ["current row", "當前資料列"],
  ["這條 lane", "這條路徑"],
  ["formula review", "公式複核"],
  ["verify next", "下一步驗證"],
  ["governance blocker", "治理阻塞"],
  ["exact support 未達 minimum", "精準樣本未達最小門檻"],
  ["exact support 已開始累積", "精準樣本已開始累積"],
  ["exact support 尚未建立", "精準樣本尚未建立"],
  ["PAPER", "模擬倉"],
  ["同 quality 寬 scope", "同品質寬範圍"],
  ["同 QUALITY 寬 SCOPE", "同品質寬範圍"],
  ["同 regime 寬 scope", "同市場狀態較寬範圍"],
  ["QUALITY", "品質"],
  ["SCOPE", "範圍"],
  ["dashboard", "儀表板"],
  ["no_runtime_order", "尚無執行期委託"],
  ["no_recent_runtime_order", "尚無近期執行期委託"],
  ["unsupported_exact_live_structure_bucket", "精準樣本尚未建立"],
  ["under_minimum_exact_live_structure_bucket", "精準樣本未達最小門檻"],
  ["decision_quality_below_trade_floor", "決策品質未達門檻"],
  ["circuit_breaker_active", "風控熔斷中"],
  ["patch_inactive_or_blocked", "僅保留治理參考"],
  ["patch_active_but_execution_blocked", "patch 已套用但 execution 仍阻塞"],
  ["support_closed_but_trade_floor_blocked", "精準樣本已閉環，但仍被交易門檻擋住"],
  ["capacity_opened_signal_hold", "容量已開但訊號仍 HOLD"],
  ["unsupported_live_structure_bucket", "live bucket 支持不足"],
  ["exact_bucket_unsupported_block", "精準樣本尚未建立"],
  ["exact_bucket_present_but_below_minimum", "精準樣本未達最小門檻"],
  ["exact_live_bucket_present_but_below_minimum", "精準樣本已開始累積"],
  ["exact_bucket_missing_proxy_reference_only", "近似樣本僅供治理參考"],
  ["exact_bucket_missing_exact_lane_proxy_only", "精準路徑近似樣本僅供治理參考"],
  ["no_support_proxy", "目前沒有可用近似樣本"],
  ["reference_only_non_current_live_scope", "範圍不同，僅作治理參考"],
  ["reference_only_until_exact_support_ready", "先當治理參考，不可直接放行"],
  ["reference_only_while_deployment_blocked", "blocker 未清前僅作治理參考"],
  ["runtime_governance_visibility_only", "執行治理可視化"],
  ["regime_gate_block", "市場閘門阻塞"],
  ["regime gate", "市場閘門"],
  ["stalled_under_minimum", "最小門檻尚未達標"],
  ["runtime_has_not_recorded_an_order_yet", "執行期尚未記錄任何委託"],
  ["no_recent_runtime_order", "尚無近期執行期委託"],
  ["capture_first_runtime_order", "先捕捉第一筆執行期委託"],
  ["not-upgraded", "尚未升級"],
];

const GENERIC_OPERATOR_PHRASE_REPLACEMENTS: Array<[string, string]> = [
  ["current live structure bucket", "當前 live 結構 bucket"],
  ["current-live structure bucket", "當前 live 結構 bucket"],
  ["current live bucket", "當前 live bucket"],
  ["current-live bucket", "當前 live bucket"],
  ["current live blocker", "目前阻塞點"],
  ["current-live blocker", "目前阻塞點"],
  ["deployment-grade minimum support", "可部署最低樣本"],
  ["deployment grade minimum support", "可部署最低樣本"],
  ["exact support", "精準樣本"],
  ["support-aware", "支援樣本感知"],
  ["base-stack redesign", "基礎堆疊重設"],
  ["base-stack", "基礎堆疊"],
  ["discriminative", "保留辨別力"],
  ["trade floor", "交易門檻"],
  ["no-deploy", "不可部署"],
  ["closure", "閉環"],
  ["uplift", "上修"],
  ["support 補滿前", "精準樣本補滿前"],
  ["support 閉環", "精準樣本閉環"],
  ["runtime 只能維持", "執行期只能維持"],
  ["primary sleeves", "主要倉位腿"],
  ["current row", "當前資料列"],
  ["這條 lane", "這條路徑"],
  ["exact live bucket present but below minimum", "目前 exact support 已開始累積"],
  ["exact rows", "精準樣本"],
  ["exact live lane", "精準路徑"],
  ["exact lane", "精準路徑"],
  ["broader / proxy rows", "較寬範圍 / 近似樣本"],
  ["proxy rows", "近似樣本"],
  ["reference-only", "僅供治理參考"],
  ["reference only", "僅供治理參考"],
  ["recommended patch", "建議 patch"],
  ["deployment closure", "部署閉環"],
  ["deployment blocker", "部署 blocker"],
  ["deployment", "部署"],
  ["runtime last order", "執行期最新委託"],
  ["runtime order", "執行期委託"],
  ["runtime mirror", "執行期鏡像"],
  ["runtime truth", "執行期真相"],
  ["account snapshot", "帳戶快照"],
  ["trade history", "交易歷史"],
  ["open orders", "未成交掛單"],
  ["spillover", "外溢"],
  ["recent-window", "近期視窗"],
  ["scope 不同", "範圍不同"],
  ["runtime / calibration", "執行期 / 校準"],
  ["runtime 精準樣本", "執行期精準樣本"],
  ["calibration 精準路徑", "校準精準路徑"],
  ["runtime ", "執行期 "],
  ["proxy", "近似樣本"],
  ["guardrail", "保護欄"],
  ["Diagnostics", "診斷"],
  ["installed-but-not-ticking", "已安裝但尚未觀察到自然排程觸發"],
  ["observed-ticking", "已觀察到自然排程觸發"],
  ["installed_but_artifact_not_fresh", "已安裝但產物未維持新鮮"],
  ["ticking", "排程觸發"],
];

const Q15_BUCKET_ROOT_CAUSE_LABEL_MAPPINGS: Array<[string, string]> = [
  ["current_bucket_exact_support_already_closed", "exact support 已 closure"],
  ["current_row_already_above_q35_boundary", "已越過 q35 邊界"],
  ["same_lane_neighbor_bucket_dominates", "鄰近 bucket 主導"],
  ["no_exact_live_lane_rows", "exact lane 尚未生成"],
  ["runtime_blocker_preempts_bucket_root_cause", "runtime blocker 優先"],
  ["runtime_blocker_preempts_q35_scaling", "風控熔斷優先，暫不處理 q35 分段校準"],
  ["missing_structure_quality", "缺少 structure quality"],
  ["boundary_sensitivity_candidate", "q15↔q35 邊界候選"],
  ["structure_scoring_gap_not_boundary", "結構評分缺口"],
  ["live_row_projection_missing_4h_inputs", "4H 投影缺值"],
  ["bias50_formula_may_be_too_harsh", "bias50 公式過嚴"],
  ["base_stack_redesign_candidate_grid_empty", "基礎堆疊重設尚未就緒"],
  ["missing_live_probe", "缺少 live probe"],
  ["insufficient_scope_data", "scope 資料不足"],
];

const Q15_BUCKET_ROOT_CAUSE_ACTION_MAPPINGS: Array<[string, string]> = [
  ["deployment_blocker_verification", "回到 blocker 驗證"],
  ["support_accumulation", "等待 support 累積"],
  ["structure_component_scoring", "結構元件校準"],
  ["live_row_projection", "修 4H 投影"],
  ["scope_generation", "補 exact lane scope"],
  ["bucket_boundary_review", "邊界複核"],
  ["exact_lane_formula_review", "bias50 公式複核"],
  ["base_stack_redesign", "基礎堆疊重設"],
  ["defer_until_circuit_breaker_releases", "待風控熔斷解除後再處理"],
  ["release_circuit_breaker_then_rerun_q35_scaling_audit", "先解除風控熔斷，再重跑 q35 分段校準審核"],
];

const EXECUTION_OPERATOR_LABEL_MAPPINGS: Record<string, Array<[string, string]>> = {
  status: [
    ["blocked_preview", "阻塞中"],
    ["inactive_preview", "待條件恢復"],
    ["ready_control_plane", "可建立 run"],
    ["resume_available", "可恢復 run"],
    ["not-started", "尚未啟動"],
    ["running", "運行中"],
    ["paused", "已暫停"],
    ["stopped", "已停止"],
  ],
  start_status: [
    ["blocked_preview", "目前阻塞"],
    ["inactive_preview", "待條件恢復"],
    ["ready_control_plane", "可建立 run"],
    ["resume_available", "可恢復 run"],
    ["already_running", "run 進行中"],
  ],
  event: [
    ["no event", "尚無事件"],
    ["waiting", "等待首筆事件"],
    ["started", "已啟動"],
    ["resumed", "已恢復"],
    ["paused", "已暫停"],
    ["stopped", "已停止"],
  ],
  preview: [
    ["unavailable", "待建立"],
    ["shared_symbol_preview_only", "共享帳戶預覽"],
    ["warning_commitment_unpriced", "共享預覽待補價"],
  ],
  allocation_rule: [
    ["equal_split_active_sleeves", "啟用倉位腿均分"],
  ],
};

const RECENT_DRIFT_INTERPRETATION_LABEL_MAPPINGS: Array<[string, string]> = [
  ["supported_extreme_trend", "受支持的極端趨勢"],
  ["distribution_pathology", "分布病態"],
  ["regime_concentration", "市場狀態過度集中"],
  ["healthy", "健康"],
  ["unavailable", "未提供"],
];

const LIVE_PATHOLOGY_LABEL_MAPPINGS: Array<[string, string]> = [
  ["exact_lane", "精準路徑"],
  ["spillover_pocket", "外溢口袋"],
  ["spillover_rows", "外溢樣本"],
  ["focus_scope_rows", "焦點範圍樣本"],
  ["current_spillover", "當前外溢"],
  ["reference_patch", "參考 patch"],
  ["support_route", "支持路徑"],
  ["governance_route", "治理路徑"],
  ["top_4h_shifts", "4H 主偏移"],
  ["next_action", "下一步"],
  ["current_bucket_support", "當前 bucket 樣本"],
  ["exact_lane_cohort", "精準路徑樣本"],
  ["historical_lane_bucket", "歷史 lane bucket"],
  ["no_spillover", "沒有外溢口袋"],
  ["patch", "治理 patch"],
];

const LIFECYCLE_DIAGNOSTIC_LABEL_MAPPINGS: Array<[string, string]> = [
  ["no_runtime_order", "尚無執行期委託"],
  ["no_recent_runtime_order", "尚無近期執行期委託"],
  ["not_applicable", "目前不適用"],
  ["not-required", "暫不需要"],
  ["required", "需要補重播"],
  ["healthy", "正常"],
  ["degraded", "降級"],
  ["fresh", "新鮮"],
  ["stale", "已過期"],
  ["pending", "等待中"],
  ["blocked", "阻塞中"],
  ["ready", "已就緒"],
  ["available", "可用"],
  ["present", "已提供"],
  ["clean", "正常"],
  ["repaired", "已修復"],
  ["absent", "缺失"],
  ["idle", "待命"],
  ["not-upgraded", "尚未升級"],
  ["unknown", "未知"],
  ["none", "無"],
];

const STRUCTURE_BUCKET_TOKEN_REPLACEMENTS: Array<[string, string]> = [
  ["bull_q15_bias50_overextended_block", "牛市 q15 bias50 過熱阻塞"],
  ["bull_high_bias200_overheat_block", "牛市高 bias200 過熱阻塞"],
  ["structure_quality_caution", "結構品質觀察"],
  ["structure_quality_block", "結構品質阻塞"],
  ["base_caution_regime_or_bias", "基線觀察（市場狀態 / 偏離）"],
  ["base_allow", "基線放行"],
];

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function replaceTokenPairEverywhere(value: string, token: string, label: string): string {
  let output = value.split(token).join(label);
  const spacedToken = token.replace(/_/g, " ");
  if (spacedToken !== token) {
    output = output.split(spacedToken).join(label);
  }
  return output;
}

function applyStructureBucketPhraseReplacements(value: string): string {
  let output = value;
  for (const [token, label] of STRUCTURE_BUCKET_TOKEN_REPLACEMENTS) {
    output = replaceTokenPairEverywhere(output, token, label);
  }
  output = output
    .replace(/\bBLOCK\b/g, "阻塞")
    .replace(/\bCAUTION\b/g, "觀察")
    .replace(/\bALLOW\b/g, "放行")
    .replace(/\bbull\b/gi, "牛市")
    .replace(/\bbear\b/gi, "熊市")
    .replace(/\bchop\b/gi, "盤整")
    .replace(/\bneutral\b/gi, "中性")
    .replace(/\|/g, "｜");
  return output;
}

function applyOperatorPhraseReplacements(value: string): string {
  let output = value;
  for (const [token, label] of GENERIC_OPERATOR_PHRASE_REPLACEMENTS) {
    output = output.replace(new RegExp(escapeRegExp(token), "gi"), label);
  }
  return output.replace(/\s{2,}/g, " ").trim();
}

export function humanizeFeatureKey(
  value?: string | null,
  options: { preferShortLabel?: boolean } = {},
): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "—";

  const canonicalKey = normalized.replace(/^feat_/i, "");
  const override = FEATURE_KEY_LABEL_OVERRIDES[canonicalKey];
  if (override) return options.preferShortLabel ? override.shortLabel : override.name;

  const lookupKey = FEATURE_KEY_ALIAS_MAPPINGS[canonicalKey] || canonicalKey;
  const sense = getSenseConfig(lookupKey);
  const preferredLabel = options.preferShortLabel ? sense.shortLabel || sense.name : sense.name || sense.shortLabel;
  return preferredLabel || applyOperatorPhraseReplacements(normalized.replace(/^feat_/i, "").replace(/_/g, " ").trim());
}

export function humanizePatchTargetLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "—";
  if (normalized.toLowerCase().startsWith("feat_")) {
    return humanizeFeatureKey(normalized);
  }
  const lower = normalized.toLowerCase();
  for (const [token] of Q15_BUCKET_ROOT_CAUSE_ACTION_MAPPINGS) {
    if (lower.includes(token)) return humanizeQ15BucketRootCauseAction(normalized);
  }
  return humanizeRuntimeDetailText(normalized.replace(/[_|]+/g, " ").trim());
}

export function humanizeRegimeGateLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "—";
  return applyOperatorPhraseReplacements(
    applyStructureBucketPhraseReplacements(normalized).replace(/[_|]+/g, " ").trim(),
  );
}

export function humanizeTradeReasonLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "—";
  const lower = normalized.toLowerCase();
  for (const [token, label] of TRADE_REASON_LABEL_MAPPINGS) {
    if (lower === token) return label;
  }
  return humanizeRuntimeDetailText(normalized.replace(/[_|]+/g, " ").trim());
}

export function humanizeLifecycleDiagnosticLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "未提供";
  const lower = normalized.toLowerCase();
  for (const [token, label] of LIFECYCLE_DIAGNOSTIC_LABEL_MAPPINGS) {
    if (lower === token) return label;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
}

export function humanizeStructureBucketLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "—";
  return applyOperatorPhraseReplacements(
    applyStructureBucketPhraseReplacements(normalized).replace(/_/g, " ").trim(),
  );
}

export function humanizeExecutionReason(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "尚未提供 blocker 摘要。";
  const lower = normalized.toLowerCase();
  const normalizedWords = normalized.replace(/[_|]+/g, " ").trim().toLowerCase();
  for (const [token, message] of EXECUTION_REASON_MAPPINGS) {
    const spacedToken = token.replace(/_/g, " ");
    if (lower === token || normalizedWords === spacedToken) return message;
  }
  return humanizeRuntimeDetailText(normalized);
}

export function isExecutionReconciliationLimitedEvidence(
  status?: string | null,
  lifecycleStage?: string | null,
  artifactCoverage?: string | null,
): boolean {
  const normalizedStatus = String(status || "").trim().toLowerCase();
  if (normalizedStatus !== "healthy") return false;

  const normalizedStage = String(lifecycleStage || "").trim().toLowerCase();
  const normalizedCoverage = String(artifactCoverage || "").trim().toLowerCase();
  return normalizedStage === "no_runtime_order" || normalizedCoverage === "not_applicable";
}

export function humanizeExecutionReconciliationStatusLabel(
  status?: string | null,
  lifecycleStage?: string | null,
  artifactCoverage?: string | null,
): string {
  if (isExecutionReconciliationLimitedEvidence(status, lifecycleStage, artifactCoverage)) {
    return "證據有限";
  }
  const normalized = String(status || "").trim();
  return normalized ? humanizeExecutionReason(normalized) : "尚未提供";
}

export function humanizeCurrentLiveBlockerLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "尚未提供";
  const lower = normalized.toLowerCase();
  for (const [token, label] of CURRENT_LIVE_BLOCKER_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(
    applyStructureBucketPhraseReplacements(normalized).replace(/_/g, " ").trim(),
  );
}

export function humanizeRecentDriftInterpretation(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "未提供";
  const lower = normalized.toLowerCase();
  for (const [token, label] of RECENT_DRIFT_INTERPRETATION_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
}

export function humanizeLivePathologyLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "未提供";
  const lower = normalized.toLowerCase();
  for (const [token, label] of LIVE_PATHOLOGY_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
}

export function humanizeSupportRouteLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "—";
  const lower = normalized.toLowerCase();
  for (const [token, label] of SUPPORT_ROUTE_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(
    applyStructureBucketPhraseReplacements(normalized).replace(/_/g, " ").trim(),
  );
}

export function humanizeSupportGovernanceRouteLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "—";
  const lower = normalized.toLowerCase();
  for (const [token, label] of SUPPORT_GOVERNANCE_ROUTE_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(
    applyStructureBucketPhraseReplacements(normalized).replace(/_/g, " ").trim(),
  );
}

export function humanizeRuntimeClosureStateLabel(value?: string | null, fallback?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return applyOperatorPhraseReplacements(String(fallback || "unknown").trim() || "unknown");
  const lower = normalized.toLowerCase();
  for (const [token, label] of RUNTIME_CLOSURE_STATE_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
}

export function humanizeSupportProgressStatusLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "未提供";
  const lower = normalized.toLowerCase();
  for (const [token, label] of SUPPORT_PROGRESS_STATUS_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
}

function normalizeSupportProgressCount(value?: number | null): number | null {
  return typeof value === "number" && Number.isFinite(value) ? Math.round(value) : null;
}

function formatSupportProgressDelta(value: number): string {
  return `${value > 0 ? "+" : ""}${value}`;
}

export function humanizeSupportProgressDeltaLabel(progress?: SupportProgressLike | null): string {
  const normalized = progress ?? null;
  if (!normalized) return "—";

  const status = String(normalized.status || "").trim().toLowerCase();
  const currentRows = normalizeSupportProgressCount(normalized.current_rows);
  const deltaVsPrevious = normalizeSupportProgressCount(normalized.delta_vs_previous);
  const recentSupportedRows = normalizeSupportProgressCount(normalized.recent_supported_rows);
  const deltaVsRecentSupported = normalizeSupportProgressCount(normalized.delta_vs_recent_supported);
  const regressedFromSupported = Boolean(normalized.regressed_from_supported) || status === "regressed_under_minimum";

  // Regressions should be measured relative to the latest supported cohort,
  // not the immediately previous stagnant heartbeat.
  if (regressedFromSupported && deltaVsRecentSupported !== null) {
    if (recentSupportedRows !== null && currentRows !== null) {
      return `相對最近已就緒 ${formatSupportProgressDelta(deltaVsRecentSupported)}（${recentSupportedRows} → ${currentRows}）`;
    }
    return `相對最近已就緒 ${formatSupportProgressDelta(deltaVsRecentSupported)}`;
  }

  if (deltaVsPrevious !== null) {
    return formatSupportProgressDelta(deltaVsPrevious);
  }

  return "—";
}

export function humanizeSupportProgressReferenceLabel(progress?: SupportProgressLike | null): string {
  const normalized = progress ?? null;
  if (!normalized) return "—";

  const status = String(normalized.status || "").trim().toLowerCase();
  const regressedFromSupported = Boolean(normalized.regressed_from_supported) || status === "regressed_under_minimum";
  const recentSupportedRows = normalizeSupportProgressCount(normalized.recent_supported_rows);
  if (!regressedFromSupported || recentSupportedRows === null) return "—";

  const recentSupportedHeartbeat = String(normalized.recent_supported_heartbeat || "").trim();
  return recentSupportedHeartbeat
    ? `#${recentSupportedHeartbeat} · ${recentSupportedRows} 筆`
    : `${recentSupportedRows} 筆`;
}

export function humanizeExecutionModeLabel(value?: string | null): string {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) return "未提供";
  for (const [token, label] of EXECUTION_MODE_LABEL_MAPPINGS) {
    if (normalized === token) return label;
  }
  return applyOperatorPhraseReplacements(String(value || "").trim());
}

export function humanizeExecutionVenueLabel(value?: string | null): string {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized || normalized === "—") return "未提供";
  for (const [token, label] of EXECUTION_VENUE_LABEL_MAPPINGS) {
    if (normalized === token) return label;
  }
  return applyOperatorPhraseReplacements(String(value || "").trim());
}

export function humanizeQ15FloorCrossVerdictLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "—";
  const lower = normalized.toLowerCase();
  for (const [token, label] of Q15_FLOOR_CROSS_VERDICT_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
}

export function humanizeQ15ComponentExperimentVerdictLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "—";
  const lower = normalized.toLowerCase();
  for (const [token, label] of Q15_COMPONENT_EXPERIMENT_VERDICT_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
}

export function humanizeRuntimeDetailText(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "—";

  let output = applyStructureBucketPhraseReplacements(normalized);
  for (const [token, label] of RUNTIME_DETAIL_TOKEN_REPLACEMENTS) {
    output = output.split(token).join(label);
    const spacedToken = token.replace(/_/g, " ");
    if (spacedToken !== token) {
      output = output.split(spacedToken).join(label);
    }
  }

  output = output.replace(/\bfeat_[a-z0-9_]+\b/gi, (token) => humanizeFeatureKey(token));

  return applyOperatorPhraseReplacements(output
    .split("recommended_patch=").join("建議 patch ")
    .split("exact-vs-spillover=").join("精準路徑 / 外溢對照：")
    .split("support route").join("支持路徑")
    .split("governance route").join("治理路徑")
    .split("route=").join("支持路徑 ")
    .split("governance=").join("治理路徑 ")
    .split("blocker=").join("阻塞點 ")
    .split("current live blocker").join("目前阻塞點")
    .split("current-live blocker").join("目前阻塞點")
    .split("current live structure bucket").join("目前 live 結構 bucket")
    .split("current bucket root cause").join("當前 bucket 根因")
    .split("current bucket").join("當前 bucket")
    .split("base-mix experiment").join("base-mix 實驗")
    .split("active sleeves").join("啟用倉位腿")
    .split("inactive sleeves").join("待命倉位腿")
    .split("private balance").join("私有餘額")
    .split("runtime closure").join("部署閉環")
    .split("runtime closure summary").join("部署閉環摘要")
    .split("rows=").join("樣本：")
    .split("win_rate=").join("勝率：")
    .split("quality=").join("品質：")
    .split("avg_pnl=").join("平均損益：")
    .split("regime=").join("市場狀態：")
    .split("gate=").join("閘門：")
    .split("bucket=").join("當前 bucket：")
    .split("blocks trade").join("阻擋交易")
    .replace(/(?:_|\s)blocks[_ ]trade\b/gi, " 阻擋交易")
    .replace(/\bWR\b/g, "勝率")
    .replace(/\bPnL\b/g, "損益")
    .replace(/\bDD\b/g, "回撤")
    .replace(/\b(\d+)\s+rows\b/g, "$1 筆樣本")
    .replace(/\s{2,}/g, " ")
    .trim());
}

export function humanizeQ15BucketRootCauseLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "尚未取得 current bucket 根因";
  const lower = normalized.toLowerCase();
  for (const [token, label] of Q15_BUCKET_ROOT_CAUSE_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
}

export function humanizeQ15BucketRootCauseAction(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "尚未提供候選 patch";
  const lower = normalized.toLowerCase();
  for (const [token, label] of Q15_BUCKET_ROOT_CAUSE_ACTION_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
}

export function humanizeExecutionOperatorLabel(
  value?: string | null,
  kind: "status" | "start_status" | "event" | "preview" | "allocation_rule" = "status",
): string {
  const normalized = String(value || "").trim();
  if (!normalized) {
    if (kind === "event") return "尚無事件";
    if (kind === "preview") return "待建立";
    if (kind === "allocation_rule") return "啟用倉位腿均分";
    if (kind === "start_status") return "待條件恢復";
    if (kind === "status") return "尚未啟動";
    return "—";
  }
  const lower = normalized.toLowerCase();
  for (const [token, label] of EXECUTION_OPERATOR_LABEL_MAPPINGS[kind] || []) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
}
