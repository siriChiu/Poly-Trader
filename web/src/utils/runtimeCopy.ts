const EXECUTION_REASON_MAPPINGS: Array<[string, string]> = [
  ["live exchange credential", "交易所憑證尚未驗證。"],
  ["order ack lifecycle", "委託確認流程尚未驗證。"],
  ["fill lifecycle", "成交回補流程尚未驗證。"],
  ["under_minimum_exact_live_structure_bucket", "目前 exact support 已開始累積，但尚未達到最小可部署樣本。"],
  ["unsupported_exact_live_structure_bucket", "目前結構 bucket 尚未通過可部署條件。"],
  ["decision_quality_below_trade_floor", "目前決策品質不足，暫不建議進場。"],
  ["circuit_breaker_active", "目前觸發保護機制，暫停部署。"],
  ["patch_inactive_or_blocked", "目前 patch 尚未啟用，或仍被其他條件阻擋。"],
  ["unsupported_live_structure_bucket", "目前 live bucket 支持仍不足。"],
  ["exact_bucket_present_but_below_minimum", "目前 exact support 已出現，但仍低於 deployment-grade minimum。"],
  ["exact_bucket_unsupported_block", "目前 exact support 尚未建立，僅能保留治理參考。"],
  ["unsupported", "目前條件尚未通過可部署檢查。"],
];

const CURRENT_LIVE_BLOCKER_LABEL_MAPPINGS: Array<[string, string]> = [
  ["under_minimum_exact_live_structure_bucket", "exact support 未達最小樣本"],
  ["unsupported_exact_live_structure_bucket", "exact support 尚未建立"],
  ["decision_quality_below_trade_floor", "決策品質未達門檻"],
  ["circuit_breaker_active", "風控熔斷中"],
  ["unsupported_live_structure_bucket", "live bucket 支持不足"],
  ["exact_live_lane_toxic_sub_bucket_current_bucket", "exact lane toxic bucket"],
];

const Q15_BUCKET_ROOT_CAUSE_LABEL_MAPPINGS: Array<[string, string]> = [
  ["boundary_sensitivity_candidate", "q15↔q35 邊界候選"],
  ["structure_scoring_gap_not_boundary", "結構評分缺口"],
  ["live_row_projection_missing_4h_inputs", "4H 投影缺值"],
  ["missing_live_probe", "缺少 live probe"],
];

const Q15_BUCKET_ROOT_CAUSE_ACTION_MAPPINGS: Array<[string, string]> = [
  ["bucket_boundary_review", "邊界複核"],
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
    ["equal_split_active_sleeves", "active sleeves 均分"],
  ],
};

export function humanizeExecutionReason(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "尚未提供 blocker 摘要。";
  const lower = normalized.toLowerCase();
  for (const [token, message] of EXECUTION_REASON_MAPPINGS) {
    if (lower.includes(token)) return message;
  }
  return normalized.replace(/[_|]+/g, " ").trim();
}

export function humanizeCurrentLiveBlockerLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "unavailable";
  const lower = normalized.toLowerCase();
  for (const [token, label] of CURRENT_LIVE_BLOCKER_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return normalized.replace(/[_|]+/g, " ").trim();
}

export function humanizeQ15BucketRootCauseLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "尚未取得 current bucket 根因";
  const lower = normalized.toLowerCase();
  for (const [token, label] of Q15_BUCKET_ROOT_CAUSE_LABEL_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return normalized.replace(/[_|]+/g, " ").trim();
}

export function humanizeQ15BucketRootCauseAction(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "尚未提供候選 patch";
  const lower = normalized.toLowerCase();
  for (const [token, label] of Q15_BUCKET_ROOT_CAUSE_ACTION_MAPPINGS) {
    if (lower.includes(token)) return label;
  }
  return normalized.replace(/[_|]+/g, " ").trim();
}

export function humanizeExecutionOperatorLabel(
  value?: string | null,
  kind: "status" | "start_status" | "event" | "preview" | "allocation_rule" = "status",
): string {
  const normalized = String(value || "").trim();
  if (!normalized) {
    if (kind === "event") return "尚無事件";
    if (kind === "preview") return "待建立";
    if (kind === "allocation_rule") return "active sleeves 均分";
    if (kind === "start_status") return "待條件恢復";
    if (kind === "status") return "尚未啟動";
    return "—";
  }
  const lower = normalized.toLowerCase();
  for (const [token, label] of EXECUTION_OPERATOR_LABEL_MAPPINGS[kind] || []) {
    if (lower.includes(token)) return label;
  }
  return normalized.replace(/[_|]+/g, " ").trim();
}
