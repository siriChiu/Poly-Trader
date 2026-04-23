const EXECUTION_REASON_MAPPINGS: Array<[string, string]> = [
  ["live exchange credential 尚未驗證", "交易所憑證尚未驗證。"],
  ["order ack lifecycle 尚未驗證", "委託確認流程尚未驗證。"],
  ["fill lifecycle 尚未驗證", "成交回補流程尚未驗證。"],
  ["live exchange credential", "交易所憑證尚未驗證。"],
  ["order ack lifecycle", "委託確認流程尚未驗證。"],
  ["fill lifecycle", "成交回補流程尚未驗證。"],
  ["under_minimum_exact_live_structure_bucket", "目前 exact support 已開始累積，但仍低於最小可部署樣本。"],
  ["unsupported_exact_live_structure_bucket", "目前結構 bucket 尚未通過可部署條件。"],
  ["decision_quality_below_trade_floor", "目前決策品質不足，暫不建議進場。"],
  ["circuit_breaker_active", "目前觸發保護機制，暫停部署。"],
  ["patch_inactive_or_blocked", "目前 patch 尚未啟用，或仍被其他條件阻擋。"],
  ["patch_active_but_execution_blocked", "目前 patch 已套用，但 execution 仍被 blocker 擋住。"],
  ["support_closed_but_trade_floor_blocked", "support 已 closure，但 trade floor 仍未通過。"],
  ["unsupported_live_structure_bucket", "目前 live bucket 支持仍不足。"],
  ["exact_bucket_present_but_below_minimum", "目前 exact support 已出現，但仍低於可部署最低樣本。"],
  ["exact_live_bucket_present_but_below_minimum", "目前 exact support 已開始累積，但仍低於可部署最低樣本。"],
  ["exact_bucket_unsupported_block", "目前 exact support 尚未建立，僅能保留治理參考。"],
  ["exact_bucket_missing_proxy_reference_only", "目前只有 proxy 參考，仍不可直接部署。"],
  ["exact_bucket_missing_exact_lane_proxy_only", "目前只有 exact-lane proxy 參考，仍不可直接部署。"],
  ["no_support_proxy", "目前沒有可用 proxy。"],
  ["regime_gate_block", "目前 regime gate 仍阻塞。"],
  ["runtime_governance_visibility_only", "目前僅提供執行治理可視化。"],
  ["stalled_under_minimum", "目前 minimum support 仍未達標。"],
  ["unsupported", "目前條件尚未通過可部署檢查。"],
];

const CURRENT_LIVE_BLOCKER_LABEL_MAPPINGS: Array<[string, string]> = [
  ["under_minimum_exact_live_structure_bucket", "exact support 未達最小樣本"],
  ["unsupported_exact_live_structure_bucket", "exact support 尚未建立"],
  ["decision_quality_below_trade_floor", "決策品質未達門檻"],
  ["circuit_breaker_active", "風控熔斷中"],
  ["unsupported_live_structure_bucket", "live bucket 支持不足"],
  ["exact_live_lane_toxic_sub_bucket_current_bucket", "精準路徑毒性子 bucket"],
];

const SUPPORT_ROUTE_LABEL_MAPPINGS: Array<[string, string]> = [
  ["exact_bucket_supported", "exact support 已就緒"],
  ["exact_bucket_present_but_below_minimum", "exact support 未達 minimum"],
  ["exact_bucket_missing_exact_lane_proxy_only", "exact support 缺口僅能參考 exact-lane proxy"],
  ["exact_bucket_missing_proxy_reference_only", "exact support 缺口僅能參考 proxy"],
  ["exact_bucket_unsupported_block", "exact support 尚未建立"],
  ["unsupported_exact_live_structure_bucket", "exact support 尚未建立"],
  ["under_minimum_exact_live_structure_bucket", "exact support 未達 minimum"],
  ["no_rows", "目前沒有可用歷史列"],
];

const SUPPORT_GOVERNANCE_ROUTE_LABEL_MAPPINGS: Array<[string, string]> = [
  ["no_support_proxy", "目前沒有可用 proxy"],
  ["exact_live_bucket_proxy_available", "已有 exact-bucket proxy"],
  ["exact_bucket_present_but_below_minimum", "exact support 已開始累積"],
  ["exact_live_bucket_present_but_below_minimum", "目前 exact support 已開始累積"],
  ["exact_bucket_supported_proxy_not_required", "exact support 已就緒，不需 proxy"],
  ["proxy_governance_reference_only_exact_support_blocked", "proxy 僅供治理參考"],
  ["exact_bucket_missing_proxy_reference_only", "proxy 僅供治理參考"],
  ["exact_bucket_missing_exact_lane_proxy_only", "exact-lane proxy 僅供治理參考"],
];

const RUNTIME_CLOSURE_STATE_LABEL_MAPPINGS: Array<[string, string]> = [
  ["patch_active_but_execution_blocked", "patch 已套用但 execution 仍阻塞"],
  ["patch_inactive_or_blocked", "僅保留治理參考"],
  ["circuit_breaker_active", "風控熔斷中"],
  ["capacity_opened_signal_hold", "容量已開但訊號仍 HOLD"],
  ["runtime_visible_preview", "runtime 預覽中"],
];

const SUPPORT_PROGRESS_STATUS_LABEL_MAPPINGS: Array<[string, string]> = [
  ["stalled_under_minimum", "minimum 尚未達標"],
  ["deployable", "已達 deployable 條件"],
  ["ready", "已就緒"],
  ["pending", "仍在累積"],
  ["unsupported", "尚未建立"],
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

const RUNTIME_DETAIL_TOKEN_REPLACEMENTS: Array<[string, string]> = [
  ["entry_quality >= 0.55 and allowed_layers > 0 without q35 applicability / support / guardrail regression", "進場品質 >= 0.55，且允許層數 > 0，同時不得出現 q35 適用性 / support / 保護欄回歸"],
  ["core_plus_macro_plus_all_4h", "核心 + 宏觀 + 全部 4H"],
  ["feat_4h_bias50_formula", "4H bias50 公式"],
  ["signal_banner", "訊號橫幅"],
  ["dashboard", "儀表板"],
  ["no_runtime_order", "尚無執行期委託"],
  ["no_recent_runtime_order", "尚無近期執行期委託"],
  ["unsupported_exact_live_structure_bucket", "exact support 尚未建立"],
  ["under_minimum_exact_live_structure_bucket", "exact support 未達 minimum"],
  ["decision_quality_below_trade_floor", "決策品質未達門檻"],
  ["circuit_breaker_active", "風控熔斷中"],
  ["patch_inactive_or_blocked", "僅保留治理參考"],
  ["patch_active_but_execution_blocked", "patch 已套用但 execution 仍阻塞"],
  ["support_closed_but_trade_floor_blocked", "support 已 closure，但仍被 trade floor 擋住"],
  ["capacity_opened_signal_hold", "容量已開但訊號仍 HOLD"],
  ["unsupported_live_structure_bucket", "live bucket 支持不足"],
  ["exact_bucket_unsupported_block", "exact support 尚未建立"],
  ["exact_bucket_present_but_below_minimum", "exact support 未達 minimum"],
  ["exact_live_bucket_present_but_below_minimum", "目前 exact support 已開始累積"],
  ["exact_bucket_missing_proxy_reference_only", "proxy 僅供治理參考"],
  ["exact_bucket_missing_exact_lane_proxy_only", "exact-lane proxy 僅供治理參考"],
  ["no_support_proxy", "目前沒有可用 proxy"],
  ["reference_only_non_current_live_scope", "scope 不同，僅作治理參考"],
  ["reference_only_until_exact_support_ready", "先當治理參考，不可直接放行"],
  ["reference_only_while_deployment_blocked", "blocker 未清前僅作治理參考"],
  ["runtime_governance_visibility_only", "執行治理可視化"],
  ["regime_gate_block", "regime gate 阻塞"],
  ["stalled_under_minimum", "minimum 尚未達標"],
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
  ["exact live bucket present but below minimum", "目前 exact support 已開始累積"],
  ["exact rows", "精準樣本"],
  ["exact live lane", "精準路徑"],
  ["exact lane", "精準路徑"],
  ["broader / proxy rows", "較寬範圍 / proxy 樣本"],
  ["proxy rows", "proxy 樣本"],
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
  ["guardrail", "保護欄"],
  ["Diagnostics", "診斷"],
  ["ticking", "排程觸發"],
];

const Q15_BUCKET_ROOT_CAUSE_LABEL_MAPPINGS: Array<[string, string]> = [
  ["current_bucket_exact_support_already_closed", "exact support 已 closure"],
  ["current_row_already_above_q35_boundary", "已越過 q35 邊界"],
  ["same_lane_neighbor_bucket_dominates", "鄰近 bucket 主導"],
  ["no_exact_live_lane_rows", "exact lane 尚未生成"],
  ["runtime_blocker_preempts_bucket_root_cause", "runtime blocker 優先"],
  ["missing_structure_quality", "缺少 structure quality"],
  ["boundary_sensitivity_candidate", "q15↔q35 邊界候選"],
  ["structure_scoring_gap_not_boundary", "結構評分缺口"],
  ["live_row_projection_missing_4h_inputs", "4H 投影缺值"],
  ["bias50_formula_may_be_too_harsh", "bias50 公式過嚴"],
  ["base_stack_redesign_candidate_grid_empty", "base-stack redesign 尚未就緒"],
  ["missing_live_probe", "缺少 live probe"],
  ["insufficient_scope_data", "scope 資料不足"],
];

const Q15_BUCKET_ROOT_CAUSE_ACTION_MAPPINGS: Array<[string, string]> = [
  ["deployment_blocker_verification", "回到 blocker 驗證"],
  ["support_accumulation", "等待 support 累積"],
  ["structure_component_scoring", "結構 component 校準"],
  ["live_row_projection", "修 4H 投影"],
  ["scope_generation", "補 exact lane scope"],
  ["bucket_boundary_review", "邊界複核"],
  ["exact_lane_formula_review", "bias50 公式複核"],
  ["base_stack_redesign", "base-stack redesign"],
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
  ["absent", "缺失"],
  ["idle", "待命"],
  ["not-upgraded", "尚未升級"],
  ["unknown", "未知"],
  ["none", "無"],
];

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function applyOperatorPhraseReplacements(value: string): string {
  let output = value;
  for (const [token, label] of GENERIC_OPERATOR_PHRASE_REPLACEMENTS) {
    output = output.replace(new RegExp(escapeRegExp(token), "gi"), label);
  }
  return output.replace(/\s{2,}/g, " ").trim();
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

export function humanizeExecutionReason(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "尚未提供 blocker 摘要。";
  const lower = normalized.toLowerCase();
  const normalizedWords = normalized.replace(/[_|]+/g, " ").trim().toLowerCase();
  for (const [token, message] of EXECUTION_REASON_MAPPINGS) {
    const spacedToken = token.replace(/_/g, " ");
    if (lower === token || normalizedWords === spacedToken) return message;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
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
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
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
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
}

export function humanizeSupportGovernanceRouteLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "—";
  const lower = normalized.toLowerCase();
  for (const [token, label] of SUPPORT_GOVERNANCE_ROUTE_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
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
  if (!normalized) return "unknown";
  const lower = normalized.toLowerCase();
  for (const [token, label] of SUPPORT_PROGRESS_STATUS_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return applyOperatorPhraseReplacements(normalized.replace(/[_|]+/g, " ").trim());
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

  let output = normalized;
  for (const [token, label] of RUNTIME_DETAIL_TOKEN_REPLACEMENTS) {
    output = output.split(token).join(label);
    const spacedToken = token.replace(/_/g, " ");
    if (spacedToken !== token) {
      output = output.split(spacedToken).join(label);
    }
  }

  return applyOperatorPhraseReplacements(output
    .split("recommended_patch=").join("建議 patch ")
    .split("exact-vs-spillover=").join("exact 與 spillover 對照：")
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
