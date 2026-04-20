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
