import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import CandlestickChart from "../components/CandlestickChart";
import LivePathologySummaryCard, { type DecisionQualityScopePathologySummary } from "../components/LivePathologySummaryCard";
import VenueReadinessSummary from "../components/VenueReadinessSummary";
import { ExecutionWorkspaceMetric, ExecutionWorkspaceSummary } from "../components/execution/ExecutionWorkspaceSummary";
import { fetchApi, useApi } from "../hooks/useApi";
import { useGlobalProgressTask } from "../hooks/useGlobalProgress";
import { getSenseConfig } from "../config/senses";

interface RegimeBreakdownEntry {
  regime: string;
  trades: number;
  wins: number;
  losses: number;
  roi?: number | null;
  win_rate?: number | null;
  profit_factor?: number | null;
  total_pnl?: number | null;
}

interface BenchmarkEntry {
  label: string;
  roi?: number | null;
  win_rate?: number | null;
  total_pnl?: number | null;
  total_trades?: number | null;
  profit_factor?: number | null;
}

interface StrategyTrade {
  timestamp?: string;
  entry_timestamp?: string;
  entry?: number;
  exit?: number;
  pnl?: number;
  roi?: number;
  layers?: number;
  reason?: string;
  entry_regime?: string;
  regime_gate?: string;
  entry_quality?: number;
  allowed_layers?: number;
}

interface EquityPoint {
  timestamp: string;
  equity: number;
}

interface ScoreSeriesPoint {
  timestamp: string;
  score?: number | null;
  entry_quality?: number | null;
  model_confidence?: number | null;
}

interface ChartContext {
  symbol?: string;
  interval?: string;
  start?: string | null;
  end?: string | null;
  limit?: number;
}

interface BacktestRangeMeta {
  requested_start?: string | null;
  requested_end?: string | null;
  requested_span_days?: number | null;
  coverage_ok?: boolean;
  backfill_required?: boolean;
  missing_start_days?: number | null;
  missing_end_days?: number | null;
  available?: {
    start?: string | null;
    end?: string | null;
    count?: number;
    span_days?: number | null;
  };
  effective?: {
    start?: string | null;
    end?: string | null;
    count?: number;
    span_days?: number | null;
  };
}

interface StrategyMetadata {
  title?: string;
  description?: string;
  strategy_type?: string;
  model_name?: string;
  model_summary?: string;
  primary_sleeve_key?: string;
  primary_sleeve_label?: string;
  sleeve_keys?: string[];
  sleeve_labels?: string[];
  sleeve_summary?: string;
}

interface DecisionContractMeta {
  target_col?: string | null;
  target_label?: string | null;
  sort_semantics?: string | null;
  decision_quality_horizon_minutes?: number | null;
}

interface SleeveRoutingEntry {
  key?: string | null;
  label?: string | null;
  status?: string | null;
  why?: string | null;
}

interface SleeveRoutingState {
  current_regime?: string | null;
  current_regime_gate?: string | null;
  current_structure_bucket?: string | null;
  active_count?: number | null;
  total_count?: number | null;
  active_ratio_text?: string | null;
  active_sleeves?: SleeveRoutingEntry[] | null;
  inactive_sleeves?: SleeveRoutingEntry[] | null;
  summary?: string | null;
}

interface StrategyLabLiveDecisionResponse {
  signal?: string | null;
  confidence?: number | null;
  regime_label?: string | null;
  regime_gate?: string | null;
  structure_bucket?: string | null;
  should_trade?: boolean;
  entry_quality?: number | null;
  entry_quality_label?: string | null;
  allowed_layers_raw?: number | null;
  allowed_layers_raw_reason?: string | null;
  allowed_layers?: number | null;
  allowed_layers_reason?: string | null;
  execution_guardrail_reason?: string | null;
  current_live_structure_bucket?: string | null;
  deployment_blocker?: string | null;
  deployment_blocker_reason?: string | null;
  deployment_blocker_details?: {
    recent_window?: {
      window_size?: number | null;
      wins?: number | null;
      win_rate?: number | null;
      floor?: number | null;
    } | null;
    release_condition?: {
      recent_window?: number | null;
      current_recent_window_wins?: number | null;
      current_recent_window_win_rate?: number | null;
      required_recent_window_wins?: number | null;
      additional_recent_window_wins_needed?: number | null;
      recent_win_rate_must_be_at_least?: number | null;
      current_streak?: number | null;
      streak_must_be_below?: number | null;
    } | null;
  } | null;
  runtime_closure_state?: string | null;
  runtime_closure_summary?: string | null;
  q15_exact_supported_component_patch_applied?: boolean | null;
  support_route_verdict?: string | null;
  support_progress?: {
    status?: string | null;
    current_rows?: number | null;
    minimum_support_rows?: number | null;
    gap_to_minimum?: number | null;
    delta_vs_previous?: number | null;
  } | null;
  floor_cross_verdict?: string | null;
  best_single_component?: string | null;
  best_single_component_required_score_delta?: number | null;
  component_experiment_verdict?: string | null;
  runtime_exact_support_rows?: number | null;
  calibration_exact_lane_rows?: number | null;
  calibration_exact_lane_alerts?: string[] | null;
  support_alignment_status?: string | null;
  support_alignment_summary?: string | null;
  decision_quality_recent_pathology_applied?: boolean | null;
  decision_quality_recent_pathology_reason?: string | null;
  decision_quality_recent_pathology_window?: number | null;
  decision_quality_recent_pathology_alerts?: string[] | null;
  decision_quality_recent_pathology_summary?: {
    win_rate?: number | null;
    avg_pnl?: number | null;
    avg_quality?: number | null;
    avg_drawdown_penalty?: number | null;
    avg_time_underwater?: number | null;
    start_timestamp?: string | null;
    end_timestamp?: string | null;
  } | null;
}

interface StrategyLabRuntimeStatusResponse {
  execution_surface_contract?: {
    canonical_execution_route?: string;
    canonical_surface_label?: string;
    operations_surface?: {
      route?: string;
      label?: string;
      role?: string;
      status?: string;
      message?: string;
      upgrade_prerequisite?: string;
    } | null;
    diagnostics_surface?: {
      route?: string;
      label?: string;
      role?: string;
      status?: string;
      message?: string;
    } | null;
    shortcut_surface?: {
      name?: string;
      message?: string;
      upgrade_prerequisite?: string;
    } | null;
    readiness_scope?: string;
    live_ready?: boolean;
    live_ready_blockers?: string[];
    operator_message?: string;
    live_runtime_truth?: {
      runtime_closure_state?: string | null;
      runtime_closure_summary?: string | null;
      deployment_blocker?: string | null;
      deployment_blocker_reason?: string | null;
      regime_label?: string | null;
      regime_gate?: string | null;
      structure_bucket?: string | null;
      sleeve_routing?: SleeveRoutingState | null;
      runtime_exact_support_rows?: number | null;
      calibration_exact_lane_rows?: number | null;
      support_alignment_status?: string | null;
      support_alignment_summary?: string | null;
      calibration_exact_lane_alerts?: string[] | null;
      decision_quality_recent_pathology_applied?: boolean | null;
      decision_quality_recent_pathology_reason?: string | null;
      decision_quality_recent_pathology_window?: number | null;
      decision_quality_recent_pathology_alerts?: string[] | null;
      decision_quality_recent_pathology_summary?: {
        win_rate?: number | null;
        avg_pnl?: number | null;
        avg_quality?: number | null;
        avg_drawdown_penalty?: number | null;
        avg_time_underwater?: number | null;
        start_timestamp?: string | null;
        end_timestamp?: string | null;
      } | null;
      decision_quality_scope_pathology_summary?: DecisionQualityScopePathologySummary | null;
    } | null;
  } | null;
  execution_metadata_smoke?: {
    generated_at?: string;
    freshness?: {
      status?: string;
      label?: string;
      age_minutes?: number | null;
    } | null;
    venues?: Array<{
      venue?: string;
      ok?: boolean;
      enabled_in_config?: boolean;
      credentials_configured?: boolean;
      error?: string | null;
      contract?: {
        step_size?: string | number | null;
        tick_size?: string | number | null;
        min_qty?: number | null;
        min_cost?: number | null;
      } | null;
    }>;
  } | null;
  execution_reconciliation?: {
    status?: string;
    summary?: string;
    checked_at?: string;
    issues?: string[];
    account_snapshot?: {
      freshness?: {
        status?: string;
        age_minutes?: number | null;
      } | null;
      degraded?: boolean;
    } | null;
    trade_history_alignment?: {
      status?: string;
      reason?: string;
    } | null;
    open_order_alignment?: {
      status?: string;
      reason?: string;
    } | null;
    lifecycle_audit?: {
      stage?: string;
      reason?: string;
      runtime_state?: string;
      trade_history_state?: string;
      matched_open_order_state?: string;
      restart_replay_required?: boolean;
      operator_action?: string;
      evidence?: {
        runtime_order_timestamp?: string | null;
        trade_history_timestamp?: string | null;
      } | null;
    } | null;
    recovery_state?: {
      status?: string;
      reason?: string;
      summary?: string;
      operator_action?: string;
      restart_replay_required?: boolean;
    } | null;
    lifecycle_contract?: {
      status?: string;
      summary?: string;
      baseline_contract_status?: string;
      replay_readiness?: string;
      replay_verdict?: string;
      replay_verdict_reason?: string;
      replay_verdict_summary?: string;
      artifact_coverage?: string;
      missing_event_types?: string[];
      operator_next_artifact?: string;
      artifact_checklist_summary?: string;
      artifact_provenance_summary?: string;
      artifact_checklist?: Array<{
        key?: string;
        label?: string;
        status?: string;
        required?: boolean;
        observed?: boolean;
        count?: number;
        summary?: string;
        provenance_level?: string;
        provenance_summary?: string;
        venue_backed?: boolean;
        proof_chain_summary?: string;
        proof_chain?: Array<{
          timestamp?: string | null;
          event_type?: string | null;
          order_state?: string | null;
          source?: string | null;
          exchange?: string | null;
          provenance_level?: string | null;
        }>;
        evidence?: Record<string, unknown> | null;
      }>;
      venue_lanes_summary?: string;
      venue_lanes?: Array<{
        venue?: string;
        label?: string;
        status?: string;
        summary?: string;
        baseline_ready?: boolean;
        baseline_observed?: number;
        baseline_required?: number;
        path_observed?: number;
        path_expected?: number;
        restart_replay_status?: string;
        operator_next_artifact?: string;
        operator_action_summary?: string;
        operator_instruction?: string;
        verify_instruction?: string;
        operator_next_check?: string;
        remediation_focus?: string;
        remediation_priority?: string;
        missing_required_artifacts?: string[];
        artifact_count?: number;
        artifact_keys?: string[];
        artifact_drilldown_summary?: string;
        timeline_count?: number;
        timeline_summary?: string;
        timeline_events?: Array<{
          timestamp?: string | null;
          event_type?: string | null;
          order_state?: string | null;
          source?: string | null;
          exchange?: string | null;
          provenance_level?: string | null;
        }>;
        provenance_counts?: {
          venue_backed?: number;
          dry_run_only?: number;
          internal_only?: number;
          missing_or_not_applicable?: number;
        } | null;
        artifacts?: Array<{
          key?: string;
          status?: string;
          provenance_level?: string;
        }>;
      }>;
    } | null;
    lifecycle_timeline?: {
      status?: string;
      total_events?: number;
      latest_event?: {
        event_type?: string | null;
        order_state?: string | null;
        timestamp?: string | null;
      } | null;
      events?: Array<{
        timestamp?: string | null;
        event_type?: string | null;
        order_state?: string | null;
        source?: string | null;
        summary?: string | null;
      }>;
    } | null;
  } | null;
}

interface StrategyResult {
  roi: number;
  win_rate: number;
  total_trades: number;
  investment_horizon?: "short" | "medium" | "long" | string | null;
  capital_mode?: "classic_pyramid" | "reserve_90" | string | null;
  wins: number;
  losses: number;
  max_drawdown: number;
  profit_factor: number;
  total_pnl: number;
  max_consecutive_losses?: number;
  overall_score?: number | null;
  reliability_score?: number | null;
  return_power_score?: number | null;
  risk_control_score?: number | null;
  capital_efficiency_score?: number | null;
  rank_delta?: number | null;
  avg_entry_quality?: number | null;
  avg_allowed_layers?: number | null;
  dominant_regime_gate?: string | null;
  regime_gate_summary?: Record<string, number>;
  decision_quality_horizon_minutes?: number | null;
  avg_expected_win_rate?: number | null;
  avg_expected_pyramid_pnl?: number | null;
  avg_expected_pyramid_quality?: number | null;
  avg_expected_drawdown_penalty?: number | null;
  avg_expected_time_underwater?: number | null;
  avg_decision_quality_score?: number | null;
  decision_quality_label?: string | null;
  decision_quality_sample_size?: number | null;
  target_col?: string | null;
  target_label?: string | null;
  sort_semantics?: string | null;
  regime_breakdown?: RegimeBreakdownEntry[];
  benchmarks?: {
    buy_hold?: BenchmarkEntry;
    blind_pyramid?: BenchmarkEntry;
  };
  equity_curve?: EquityPoint[];
  trades?: StrategyTrade[];
  score_series?: ScoreSeriesPoint[];
  chart_context?: ChartContext;
  backtest_range?: BacktestRangeMeta;
  run_at?: string;
}

interface StrategyEntry {
  name: string;
  created_at: string;
  definition: { type: string; params: Record<string, any> };
  metadata?: StrategyMetadata;
  last_results?: StrategyResult;
  decision_contract?: DecisionContractMeta;
  run_count: number;
  rank_delta?: number | null;
  stability_score?: number | null;
  stability_label?: string;
  overfit_risk?: "low" | "medium" | "high" | "unknown";
  trade_sufficiency?: "high" | "medium" | "low" | "unknown";
  risk_reasons?: string[];
}

interface ModelLeaderboardEntry {
  model_name: string;
  model_tier?: "core" | "control" | "research" | string;
  model_tier_label?: string;
  model_tier_reason?: string;
  deployment_profile?: string;
  deployment_profile_label?: string;
  deployment_profile_source?: string;
  selected_deployment_profile?: string;
  selected_deployment_profile_label?: string;
  selected_deployment_profile_source?: string;
  feature_profile?: string;
  feature_profile_source?: string;
  selected_feature_profile?: string;
  selected_feature_profile_source?: string;
  selected_feature_profile_blocker_applied?: boolean;
  selected_feature_profile_blocker_reason?: string | null;
  avg_roi: number;
  avg_win_rate: number;
  avg_trades: number;
  avg_max_dd: number;
  std_roi: number;
  profit_factor: number;
  train_acc: number;
  test_acc: number;
  train_test_gap: number;
  composite: number;
  rank_delta?: number;
  overall_score?: number;
  reliability_score?: number;
  return_power_score?: number;
  risk_control_score?: number;
  capital_efficiency_score?: number;
  time_underwater_score?: number;
  decision_quality_component?: number;
  avg_entry_quality?: number;
  avg_allowed_layers?: number;
  avg_trade_quality?: number;
  avg_decision_quality_score?: number;
  avg_expected_win_rate?: number;
  avg_expected_pyramid_quality?: number;
  avg_expected_drawdown_penalty?: number;
  avg_expected_time_underwater?: number;
  regime_stability_score?: number;
  max_drawdown_score?: number;
  profit_factor_score?: number;
  overfit_penalty?: number;
  trade_count_score?: number;
  ranking_eligible?: boolean;
  ranking_status?: string;
  ranking_warning?: string | null;
  placeholder_reason?: string | null;
  raw_rank?: number | null;
  is_overfit?: boolean;
  overfit_reason?: string | null;
  folds: Array<{ fold: number; roi: number; win_rate: number; trades: number; max_dd: number; profit_factor: number }>;
}

interface ScoreDimensionMeta {
  key: string;
  label: string;
  description: string;
}

interface QuadrantPoint {
  model_name: string;
  x: number;
  y: number;
  overall_score?: number;
  risk_control_score?: number;
  capital_efficiency_score?: number;
  avg_roi?: number;
  avg_max_dd?: number;
}

interface TargetComparisonEntry {
  target_col: string;
  label: string;
  is_canonical?: boolean;
  usage_note?: string;
  samples: number;
  positive_ratio: number;
  models_evaluated: number;
  best_model: ModelLeaderboardEntry | null;
}

interface LeaderboardGlobalMetrics {
  train_accuracy?: number;
  cv_accuracy?: number;
  cv_std?: number;
  n_samples?: number;
  trained_at?: string;
}

interface RegimeMetricsEntry {
  cv_accuracy?: number;
  train_accuracy?: number;
  n_samples?: number;
}

interface SkippedModel {
  model_name: string;
  status?: string;
  reason?: string | null;
  detail?: string | null;
}

interface LeaderboardHistoryRow {
  id?: number;
  created_at: string;
  target_col?: string | null;
  model_count?: number | null;
  updated_at?: string | number | null;
}

interface StrategyParamScanCandidate {
  name?: string | null;
  model_name?: string | null;
  roi?: number | null;
  win_rate?: number | null;
  total_trades?: number | null;
}

interface StrategyParamScanVariant {
  model_name?: string | null;
  variant?: string | null;
  roi?: number | null;
  win_rate?: number | null;
  max_drawdown?: number | null;
  profit_factor?: number | null;
  total_trades?: number | null;
}

interface StrategyParamScanSummary {
  generated_at?: string | null;
  saved_strategy_count?: number | null;
  best_strategy_candidates?: StrategyParamScanCandidate[];
  combined_top_variants?: StrategyParamScanVariant[];
  source_artifact?: string | null;
  warning?: string | null;
}

interface LeaderboardGovernanceSummary {
  generated_at?: string | null;
  source_artifact?: string | null;
  dual_profile_state?: string | null;
  train_selected_profile?: string | null;
  train_selected_profile_source?: string | null;
  leaderboard_selected_profile?: string | null;
  leaderboard_selected_profile_source?: string | null;
  live_current_structure_bucket?: string | null;
  live_current_structure_bucket_rows?: number | null;
  minimum_support_rows?: number | null;
  current_alignment_inputs_stale?: boolean;
  profile_split?: {
    global_profile?: string | null;
    global_profile_role?: string | null;
    production_profile?: string | null;
    production_profile_role?: string | null;
    split_required?: boolean;
    verdict?: string | null;
    reason?: string | null;
  } | null;
  governance_contract?: {
    verdict?: string | null;
    treat_as_parity_blocker?: boolean;
    current_closure?: string | null;
    reason?: string | null;
    recommended_action?: string | null;
    support_governance_route?: string | null;
    live_current_structure_bucket_rows?: number | null;
    minimum_support_rows?: number | null;
    support_progress?: {
      status?: string | null;
      current_rows?: number | null;
      minimum_support_rows?: number | null;
      gap_to_minimum?: number | null;
    } | null;
  } | null;
}

interface ModelLeaderboardMeta {
  refreshing?: boolean;
  cached?: boolean;
  stale?: boolean;
  updated_at?: string | null;
  cache_age_sec?: number | null;
  warning?: string | null;
  leaderboard_warning?: string | null;
  error?: string | null;
  target_col?: string | null;
  target_label?: string | null;
  comparable_count?: number | null;
  placeholder_count?: number | null;
  evaluated_row_count?: number | null;
  placeholder_rows?: ModelLeaderboardEntry[];
  global_metrics?: LeaderboardGlobalMetrics | null;
  regime_metrics?: Record<string, RegimeMetricsEntry> | null;
  skipped_models?: SkippedModel[];
  score_dimensions?: ScoreDimensionMeta[];
  storage?: { canonical_store?: string; cache_store?: string } | null;
  snapshot_history?: LeaderboardHistoryRow[];
  strategy_param_scan?: StrategyParamScanSummary | null;
  leaderboard_governance?: LeaderboardGovernanceSummary | null;
}

interface StrategyQuadrantPoint {
  strategy_name: string;
  x: number;
  y: number;
  overall_score?: number | null;
  risk_control_score?: number | null;
  capital_efficiency_score?: number | null;
  rank_delta?: number | null;
}

interface StrategyLeaderboardMeta {
  target_col?: string | null;
  target_label?: string | null;
  sort_semantics?: string | null;
  score_dimensions?: ScoreDimensionMeta[];
  snapshot_history?: LeaderboardHistoryRow[];
}

interface ModelStatsResponse {
  model_loaded?: boolean;
  sample_count?: number;
  cv_accuracy?: number | null;
  feature_importance?: Record<string, number>;
  ic_values?: Record<string, number>;
}

interface StrategyJobStep {
  key: string;
  label: string;
  status: "pending" | "running" | "completed" | "failed" | string;
}

interface BackgroundStage {
  mode: "initial" | "select_strategy" | "run_strategy" | "model_refresh";
  label: string;
  detail: string;
  progress: number;
  stageKey?: string | null;
  stageLabel?: string | null;
  steps?: StrategyJobStep[] | null;
}

interface CompetitiveFeatureRow {
  key: string;
  label: string;
  description: string;
  ic: number | null;
  importance: number | null;
  score: number;
  bucket: "short" | "4h";
}

const DEFAULT_PARAMS = {
  entry: {
    bias50_max: 0.0,
    nose_max: 0.4,
    pulse_min: 0.0,
    layer2_bias_max: -1.0,
    layer3_bias_max: -3.0,
    confidence_min: 0.52,
    entry_quality_min: 0.5,
    top_k_percent: 0,
    allowed_regimes: ["bull", "chop"],
  },
  layers: [0.25, 0.25, 0.5],
  capital_management: {
    mode: "classic_pyramid",
    base_entry_fraction: 0.10,
    reserve_trigger_drawdown: 0.10,
  },
  stop_loss: -0.03,
  take_profit_bias: 999.0,
  take_profit_roi: 999.0,
  turning_point: {
    enabled: true,
    bottom_score_min: 0.62,
    top_score_take_profit: 0.8,
    min_profit_pct: 0.0,
  },
};

const MODEL_OPTIONS = ["rule_baseline", "logistic_regression", "xgboost", "lightgbm", "catboost", "random_forest", "mlp", "svm"] as const;

const AUTO_STRATEGY_PREFIX = "Auto Leaderboard · ";
const LEADERBOARD_BACKTEST_WINDOW_MONTHS = 24;
const LEADERBOARD_BACKTEST_WINDOW_DAYS = 730;
const LEADERBOARD_BACKTEST_POLICY_LABEL = "排行榜回測固定使用最近兩年";

const isFiniteNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const toDateTimeLocalValue = (value?: string | null) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString().slice(0, 16);
};
const resolveLatestTwoYearBacktestRange = (availableStart?: string | null, availableEnd?: string | null) => {
  if (!availableEnd) {
    return { start: "", end: "" };
  }
  const end = new Date(availableEnd);
  if (Number.isNaN(end.getTime())) {
    return { start: "", end: "" };
  }
  const start = new Date(end);
  start.setMonth(start.getMonth() - LEADERBOARD_BACKTEST_WINDOW_MONTHS);
  if (availableStart) {
    const floor = new Date(availableStart);
    if (!Number.isNaN(floor.getTime()) && start < floor) {
      return { start: floor.toISOString().slice(0, 16), end: end.toISOString().slice(0, 16) };
    }
  }
  return { start: start.toISOString().slice(0, 16), end: end.toISOString().slice(0, 16) };
};

const formatStrategyDisplayName = (strategy?: Pick<StrategyEntry, "name" | "metadata"> | null) => {
  const raw = strategy?.metadata?.title || strategy?.name || "—";
  return raw.startsWith(AUTO_STRATEGY_PREFIX) ? raw.slice(AUTO_STRATEGY_PREFIX.length) : raw;
};
const formatPct = (value: number | null | undefined, digits = 1, signed = false) => {
  if (!isFiniteNumber(value)) return "—";
  const prefix = signed && value > 0 ? "+" : "";
  return `${prefix}${(value * 100).toFixed(digits)}%`;
};
const formatDecimal = (value: number | null | undefined, digits = 2) => (isFiniteNumber(value) ? value.toFixed(digits) : "—");
const formatMoney = (value: number | null | undefined) => (isFiniteNumber(value) ? `USDT ${value > 0 ? "+" : ""}${value.toFixed(0)}` : "—");
const formatPenaltyHint = (value: number | null | undefined) => {
  if (!isFiniteNumber(value)) return "—";
  return value <= 0 ? "低" : value <= 0.2 ? "可控" : value <= 0.4 ? "偏高" : "高";
};
const formatDelta = (value: number | null | undefined, digits = 3, suffix = "") => {
  if (!isFiniteNumber(value)) return "—";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(digits)}${suffix}`;
};
const deltaTone = (value: number | null | undefined, preferLower = false) => {
  if (!isFiniteNumber(value) || value === 0) return "text-slate-400";
  const improved = preferLower ? value < 0 : value > 0;
  return improved ? "text-emerald-300" : "text-red-300";
};
const decisionQualityTone = (value: number | null | undefined) => {
  if (!isFiniteNumber(value)) return "text-slate-300";
  if (value >= 0.45) return "text-emerald-300";
  if (value >= 0.3) return "text-yellow-300";
  return "text-red-300";
};
const executionSyncTone = ({
  pending,
  liveReady,
  blocker,
  reconciliationStatus,
}: {
  pending: boolean;
  liveReady: boolean;
  blocker?: string | null;
  reconciliationStatus?: string | null;
}) => {
  if (pending) return "border-slate-700/40 bg-slate-950/20 text-slate-200";
  if (!liveReady || blocker) return "border-rose-700/40 bg-rose-950/20 text-rose-100";
  if (reconciliationStatus === "healthy") return "border-emerald-700/40 bg-emerald-950/20 text-emerald-100";
  if (reconciliationStatus === "warning") return "border-amber-700/40 bg-amber-950/20 text-amber-100";
  if (reconciliationStatus === "degraded") return "border-red-700/40 bg-red-950/20 text-red-100";
  return "border-slate-700/40 bg-slate-950/20 text-slate-200";
};
const metadataFreshnessTone = (status?: string | null) => {
  if (status === "fresh") return "text-emerald-300";
  if (status === "stale") return "text-amber-300";
  if (status === "unavailable") return "text-red-300";
  return "text-slate-400";
};
const modelTierOrder: Record<string, number> = { core: 0, control: 1, research: 2 };
const modelTierBadgeTone: Record<string, string> = {
  core: "border-emerald-700/40 bg-emerald-900/20 text-emerald-200",
  control: "border-cyan-700/40 bg-cyan-900/20 text-cyan-200",
  research: "border-amber-700/40 bg-amber-900/20 text-amber-200",
};
const defaultModelTierMeta = (modelName: string) => {
  const normalized = String(modelName || "").trim().toLowerCase();
  if (["rule_baseline", "random_forest", "xgboost", "logistic_regression"].includes(normalized)) {
    return {
      model_tier: "core",
      model_tier_label: "核心模型",
      model_tier_reason: "最符合目前 Poly-Trader 的多特徵、低頻高信念、可解釋與穩定度優先主線。",
    };
  }
  if (["lightgbm", "catboost", "ensemble"].includes(normalized)) {
    return {
      model_tier: "control",
      model_tier_label: "對照模型",
      model_tier_reason: "適合作為 XGBoost / RandomForest 的對照與補充，不是當前第一主線。",
    };
  }
  if (["mlp", "svm"].includes(normalized)) {
    return {
      model_tier: "research",
      model_tier_label: "研究模型",
      model_tier_reason: "目前保留在研究層，用來觀察是否有額外訊號，不建議當前主線優先投入。",
    };
  }
  return {
    model_tier: "control",
    model_tier_label: "對照模型",
    model_tier_reason: "未明確歸類，預設先放在對照層，避免過早升為主線。",
  };
};
const modelTierMetaForRow = (model: Pick<ModelLeaderboardEntry, "model_name" | "model_tier" | "model_tier_label" | "model_tier_reason">) => {
  const fallback = defaultModelTierMeta(model.model_name);
  return {
    model_tier: model.model_tier || fallback.model_tier,
    model_tier_label: model.model_tier_label || fallback.model_tier_label,
    model_tier_reason: model.model_tier_reason || fallback.model_tier_reason,
  };
};
const modelTierLabel = (model: Pick<ModelLeaderboardEntry, "model_name" | "model_tier" | "model_tier_label" | "model_tier_reason">) => modelTierMetaForRow(model).model_tier_label;
const describeRankingReason = (model: ModelLeaderboardEntry) => {
  if (model.ranking_status === "no_trade_placeholder") {
    return model.ranking_warning || "⚠️ 當前 deployment profile 沒有產生任何交易，這列只是 placeholder，不代表可比較排名。";
  }
  const reasons: string[] = [];
  if (isFiniteNumber(model.avg_decision_quality_score)) {
    reasons.push(`決策品質 ${model.avg_decision_quality_score.toFixed(3)}`);
  }
  if (isFiniteNumber(model.avg_expected_win_rate)) {
    reasons.push(`預期勝率 ${formatPct(model.avg_expected_win_rate)}`);
  }
  if (isFiniteNumber(model.avg_expected_drawdown_penalty)) {
    reasons.push(`回撤懲罰 ${formatPct(model.avg_expected_drawdown_penalty)}`);
  }
  if (isFiniteNumber(model.avg_expected_time_underwater)) {
    reasons.push(`深套時間 ${formatPct(model.avg_expected_time_underwater)}`);
  }
  if (isFiniteNumber(model.avg_allowed_layers)) {
    reasons.push(`平均層數 ${model.avg_allowed_layers.toFixed(1)}`);
  }
  if (reasons.length > 0) {
    return reasons.slice(0, 3).join(" · ");
  }
  return `⚠️ canonical DQ 缺失，暫退回 legacy ROI ${formatPct(model.avg_roi, 1, true)} · 最大回撤 ${formatPct(model.avg_max_dd)} · 勝率 ${formatPct(model.avg_win_rate)}（僅參考）`;
};
const deploymentProfileDisplayName = (model: ModelLeaderboardEntry) => (
  model.selected_deployment_profile_label
  || model.deployment_profile_label
  || model.selected_deployment_profile
  || model.deployment_profile
  || "standard"
);
const deploymentProfileSourceLabel = (model: ModelLeaderboardEntry) => {
  const source = model.selected_deployment_profile_source || model.deployment_profile_source || null;
  if (source === "code_backed_promoted_from_scan") return "code-backed promoted from scan";
  if (source === "artifact_scan") return "artifact scan";
  if (source === "code_backed") return "code-backed";
  return source || "source unknown";
};
const featureProfileDisplayName = (model: ModelLeaderboardEntry) => (
  model.selected_feature_profile
  || model.feature_profile
  || "current_full"
);
const featureProfileSourceLabel = (model: ModelLeaderboardEntry) => {
  const source = model.selected_feature_profile_source || model.feature_profile_source || null;
  if (source === "feature_group_ablation.recommended_profile") return "global shrinkage winner";
  if (source === "bull_4h_pocket_ablation.exact_supported_profile") return "bull exact-supported production";
  if (source === "bull_4h_pocket_ablation.support_aware_profile") return "support-aware production";
  return source || "source unknown";
};
const governanceRoleLabel = (role?: string | null) => {
  if (role === "global_shrinkage_winner") return "global shrinkage winner";
  if (role === "bull_exact_supported_production_profile") return "bull exact-supported production";
  if (role === "support_aware_production_profile") return "support-aware production";
  return role || "role unknown";
};
const governanceSupportRows = (governance?: LeaderboardGovernanceSummary | null) => {
  const supportProgress = governance?.governance_contract?.support_progress;
  const currentRows = supportProgress?.current_rows ?? governance?.live_current_structure_bucket_rows ?? governance?.governance_contract?.live_current_structure_bucket_rows;
  const minimumRows = supportProgress?.minimum_support_rows ?? governance?.minimum_support_rows ?? governance?.governance_contract?.minimum_support_rows;
  if (!isFiniteNumber(currentRows) || !isFiniteNumber(minimumRows)) return "support —";
  return `support ${formatDecimal(currentRows, 0)} / ${formatDecimal(minimumRows, 0)}`;
};
const describeStrategyRankingReason = (result?: StrategyResult | null) => {
  if (!result) return "尚未回測，無 canonical decision-quality ranking evidence";
  const reasons: string[] = [];
  if (isFiniteNumber(result.avg_decision_quality_score)) {
    const label = result.decision_quality_label ? ` (${result.decision_quality_label})` : "";
    reasons.push(`DQ ${result.avg_decision_quality_score.toFixed(3)}${label}`);
  }
  if (isFiniteNumber(result.avg_expected_win_rate)) {
    reasons.push(`預期勝率 ${formatPct(result.avg_expected_win_rate)}`);
  }
  if (isFiniteNumber(result.avg_expected_drawdown_penalty)) {
    reasons.push(`回撤懲罰 ${formatPct(result.avg_expected_drawdown_penalty)}`);
  }
  if (isFiniteNumber(result.avg_expected_time_underwater)) {
    reasons.push(`深套時間 ${formatPct(result.avg_expected_time_underwater)}`);
  }
  if (isFiniteNumber(result.avg_allowed_layers)) {
    reasons.push(`平均層數 ${formatDecimal(result.avg_allowed_layers, 1)}`);
  }
  if (reasons.length > 0) {
    return reasons.slice(0, 3).join(" · ");
  }
  return `⚠️ canonical DQ 缺失，暫退回 legacy ROI ${formatPct(result.roi, 1, true)} · 最大回撤 ${formatPct(result.max_drawdown)} · 勝率 ${formatPct(result.win_rate)}（僅參考）`;
};
const regimeLabelMap: Record<string, string> = { bull: "牛市", bear: "熊市", chop: "盤整", unknown: "未知" };
const strategyRiskTone: Record<string, string> = {
  low: "text-emerald-300 bg-emerald-900/20 border-emerald-700/30",
  medium: "text-yellow-300 bg-yellow-900/20 border-yellow-700/30",
  high: "text-red-300 bg-red-900/20 border-red-700/30",
  unknown: "text-slate-300 bg-slate-800/50 border-slate-700/40",
};
const strategyRiskLabel: Record<string, string> = { low: "低", medium: "中", high: "高", unknown: "—" };
const sufficiencyLabel: Record<string, string> = { high: "充足", medium: "普通", low: "不足", unknown: "—" };

const allowedRegimeOptions = {
  all: ["bull", "chop", "bear", "unknown"],
  bull_chop: ["bull", "chop"],
  bull_only: ["bull"],
  bear_only: ["bear"],
} as const;

const allowedRegimeLabels: Record<keyof typeof allowedRegimeOptions, string> = {
  all: "全部 regime",
  bull_chop: "bull + chop",
  bull_only: "bull only",
  bear_only: "bear only",
};

const investmentHorizonLabels = {
  short: "短期",
  medium: "中期",
  long: "長期",
} as const;

type EditorModuleId = "pyramid_sl_tp" | "fib_layers" | "high_win_low_freq" | "reserve_90" | "storm_unwind" | "turning_point";

type EditorScenario = {
  strategyType: "rule_based" | "hybrid";
  modelName: string;
  bias50Max: number;
  noseMax: number;
  layer2Bias: number;
  layer3Bias: number;
  confidenceMin: number;
  qualityMin: number;
  topKPercent: number;
  allowedRegimesMode: keyof typeof allowedRegimeOptions;
  capitalMode: "classic_pyramid" | "reserve_90";
  baseEntryFractionPct: number;
  reserveTriggerDrawdownPct: number;
  stopLoss: number;
  tpBias: number;
  tpRoi: number;
  l1: number;
  l2: number;
  l3: number;
  investmentHorizon: keyof typeof investmentHorizonLabels;
};

const EDITOR_MODULES: Array<{
  id: EditorModuleId;
  label: string;
  emoji: string;
  summary: string;
  explainer: string;
  badge: string;
  category: "core" | "signal" | "risk" | "research";
}> = [
  {
    id: "pyramid_sl_tp",
    label: "金字塔 + SL/TP",
    emoji: "🔥",
    badge: "底層模組",
    category: "core",
    summary: "標準三層分批進場，配合止損 / 止盈做風險回收。",
    explainer: "適合當作主骨架：先建立多層承接，再用明確 SL/TP 限制深套時間。",
  },
  {
    id: "fib_layers",
    label: "Fib 23/38/39",
    emoji: "🌀",
    badge: "加碼節奏",
    category: "core",
    summary: "把三層倉位改成 23/38/39，偏向回調承接而非一次押滿。",
    explainer: "如果你想讓低位補倉更平滑，這個模組會把加碼節奏改成更保守的 Fib 式分配。",
  },
  {
    id: "high_win_low_freq",
    label: "高勝率低頻",
    emoji: "🎯",
    badge: "訊號過濾",
    category: "signal",
    summary: "只保留最強訊號，交易次數下降，但每筆把握度提高。",
    explainer: "會提高信心 / 進場品質門檻，並打開 top-k 篩選，避免雜訊單太多。",
  },
  {
    id: "reserve_90",
    label: "10/90 後守",
    emoji: "🛡️",
    badge: "資金防守",
    category: "risk",
    summary: "先用 10% 試單，確認市場真的更差時才啟用後續資金。",
    explainer: "讓資金分兩段投入，避免一開始就把子彈用完，更適合震盪 / 不確定環境。",
  },
  {
    id: "storm_unwind",
    label: "風暴斬倉（研究）",
    emoji: "🌪️",
    badge: "解套代理版",
    category: "research",
    summary: "把低位循環盈利的一部分，持續釋放高位被套資金。",
    explainer: "本版先用『更快落袋 + 後守資金』近似你描述的解套邏輯；真正逐筆對最高套牢倉同步減碼，下一版再接入回測引擎。",
  },
  {
    id: "turning_point",
    label: "頂部轉折出場",
    emoji: "🧭",
    badge: "預設 exit",
    category: "signal",
    summary: "用 local-top 分數抓區域高點，取代一般固定 TP 當主出場邏輯。",
    explainer: "目前最佳默認候選：在 bull + chop 中，用較嚴格的底部進場 + 頂部轉折出場來提高 ROI / PF 與回撤表現。",
  },
];

const normalizeModuleSelection = (moduleIds: EditorModuleId[]): EditorModuleId[] => {
  const selected = new Set(moduleIds.length ? moduleIds : ["pyramid_sl_tp"]);
  return EDITOR_MODULES.map((module) => module.id).filter((id): id is EditorModuleId => selected.has(id));
};

const buildScenarioFromModules = (moduleIds: EditorModuleId[]): EditorScenario => {
  const orderedModules = normalizeModuleSelection(moduleIds);
  const scenario: EditorScenario = {
    strategyType: "hybrid",
    modelName: "xgboost",
    bias50Max: 0.0,
    noseMax: 0.4,
    layer2Bias: -1.0,
    layer3Bias: -3.0,
    confidenceMin: 52,
    qualityMin: 50,
    topKPercent: 0,
    allowedRegimesMode: "bull_chop",
    capitalMode: "classic_pyramid",
    baseEntryFractionPct: 10,
    reserveTriggerDrawdownPct: 10,
    stopLoss: -3,
    tpBias: 999,
    tpRoi: 999,
    l1: 25,
    l2: 25,
    l3: 50,
    investmentHorizon: "medium",
  };
  for (const moduleId of orderedModules) {
    switch (moduleId) {
      case "pyramid_sl_tp":
        scenario.capitalMode = "classic_pyramid";
        scenario.stopLoss = -3;
        scenario.tpBias = 999;
        scenario.tpRoi = 999;
        scenario.l1 = 25;
        scenario.l2 = 25;
        scenario.l3 = 50;
        break;
      case "fib_layers":
        scenario.bias50Max = -1.0;
        scenario.noseMax = 0.35;
        scenario.layer2Bias = -2.8;
        scenario.layer3Bias = -5.0;
        scenario.qualityMin = Math.max(scenario.qualityMin, 68);
        scenario.allowedRegimesMode = scenario.allowedRegimesMode === "bear_only" ? "bear_only" : "bull_chop";
        scenario.l1 = 23;
        scenario.l2 = 38;
        scenario.l3 = 39;
        scenario.tpBias = 4.5;
        break;
      case "high_win_low_freq":
        scenario.strategyType = "hybrid";
        scenario.modelName = "random_forest";
        scenario.confidenceMin = Math.max(scenario.confidenceMin, 75);
        scenario.qualityMin = Math.max(scenario.qualityMin, 68);
        scenario.topKPercent = Math.max(scenario.topKPercent, 5);
        scenario.allowedRegimesMode = "bear_only";
        break;
      case "reserve_90":
        scenario.capitalMode = "reserve_90";
        scenario.baseEntryFractionPct = 10;
        scenario.reserveTriggerDrawdownPct = 10;
        scenario.stopLoss = Math.min(scenario.stopLoss, -7);
        scenario.bias50Max = Math.min(scenario.bias50Max, 0.5);
        scenario.noseMax = Math.min(scenario.noseMax, 0.35);
        scenario.layer2Bias = Math.min(scenario.layer2Bias, -2.5);
        scenario.layer3Bias = Math.min(scenario.layer3Bias, -4.5);
        break;
      case "storm_unwind":
        scenario.capitalMode = "reserve_90";
        scenario.baseEntryFractionPct = 10;
        scenario.reserveTriggerDrawdownPct = 8;
        scenario.tpBias = Math.min(scenario.tpBias, 3.2);
        scenario.tpRoi = Math.min(scenario.tpRoi, 6);
        scenario.stopLoss = Math.min(scenario.stopLoss, -4);
        scenario.allowedRegimesMode = scenario.allowedRegimesMode === "bear_only" ? "bear_only" : "bull_chop";
        break;
      case "turning_point":
        scenario.strategyType = "hybrid";
        scenario.modelName = "xgboost";
        scenario.bias50Max = 0.0;
        scenario.noseMax = 0.4;
        scenario.layer2Bias = -1.0;
        scenario.layer3Bias = -3.0;
        scenario.confidenceMin = 52;
        scenario.qualityMin = 50;
        scenario.allowedRegimesMode = "bull_chop";
        scenario.stopLoss = -3;
        scenario.tpBias = 999;
        scenario.tpRoi = 999;
        scenario.l1 = 25;
        scenario.l2 = 25;
        scenario.l3 = 50;
        break;
      default:
        break;
    }
  }
  return scenario;
};

const inferModulesFromStrategy = (strategy?: StrategyEntry | null): EditorModuleId[] => {
  const params = strategy?.definition?.params ?? {};
  if (Array.isArray(params.editor_modules) && params.editor_modules.length) {
    return normalizeModuleSelection(
      params.editor_modules.filter((value: unknown): value is EditorModuleId => typeof value === "string" && EDITOR_MODULES.some((module) => module.id === value))
    );
  }
  const entry = params.entry ?? {};
  const layers = Array.isArray(params.layers) ? params.layers.map((value: number) => Math.round(Number(value) * 100)) : [];
  const active: EditorModuleId[] = [];
  const fibLike = layers.join(",") === "23,38,39";
  active.push(fibLike ? "fib_layers" : "pyramid_sl_tp");
  if ((strategy?.definition?.type === "hybrid") || Number(entry.top_k_percent || 0) > 0 || Number(entry.confidence_min || 0) >= 0.7) {
    active.push("high_win_low_freq");
  }
  if ((params.capital_management?.mode || "classic_pyramid") === "reserve_90") {
    active.push("reserve_90");
  }
  if ((params.capital_management?.mode || "") === "reserve_90" && Number(params.take_profit_roi || 0) <= 0.06) {
    active.push("storm_unwind");
  }
  return normalizeModuleSelection(active);
};

const toStageProgress = (completed: number, total: number) => {
  if (total <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((completed / total) * 100)));
};

const STAGE_TOTALS = {
  initial: 4,
  select_strategy: 3,
  run_strategy: 5,
} as const;

const STRATEGY_JOB_POLL_INTERVAL_MS = 1000;
const strategyJobStepTone: Record<string, string> = {
  pending: "border-slate-700/40 bg-slate-950/30 text-slate-500",
  running: "border-cyan-600/40 bg-cyan-950/20 text-cyan-100",
  completed: "border-emerald-600/30 bg-emerald-950/20 text-emerald-200",
  failed: "border-red-600/40 bg-red-950/20 text-red-200",
};
const strategyJobStepDotTone: Record<string, string> = {
  pending: "bg-slate-600",
  running: "bg-cyan-400 animate-pulse",
  completed: "bg-emerald-400",
  failed: "bg-red-400",
};
const formatStrategyJobStepStatus = (status?: string | null) => {
  switch (status) {
    case "running": return "進行中";
    case "completed": return "完成";
    case "failed": return "失敗";
    default: return "待命";
  }
};

const STRATEGY_JOB_MAX_WAIT_MS = 45 * 60 * 1000;

const MODEL_LB_STALE_SEC = 60 * 60 * 6;

const toModelFreshnessProgress = (cacheAgeSec?: number | null) => {
  if (!isFiniteNumber(cacheAgeSec) || cacheAgeSec < 0) return null;
  return Math.max(0, Math.min(100, Math.round((1 - cacheAgeSec / MODEL_LB_STALE_SEC) * 100)));
};

const toMillis = (value?: string | null) => {
  if (!value) return null;
  const ms = new Date(value).getTime();
  return Number.isFinite(ms) ? ms : null;
};

const STRATEGY_LAB_CACHE_KEY = "polytrader.strategylab.cache.v1";
const STRATEGY_LAB_MEMORY_CACHE: {
  strategies?: StrategyEntry[];
  strategyMeta?: StrategyLeaderboardMeta;
  strategyQuadrantPoints?: StrategyQuadrantPoint[];
  modelLeaderboard?: ModelLeaderboardEntry[];
  modelQuadrantPoints?: QuadrantPoint[];
  modelMeta?: ModelLeaderboardMeta;
  modelStats?: ModelStatsResponse | null;
  selectedStrategy?: StrategyEntry | null;
  updatedAt?: number;
} = {};

const loadStrategyLabCache = () => {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(STRATEGY_LAB_CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const saveStrategyLabCache = (payload: typeof STRATEGY_LAB_MEMORY_CACHE) => {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STRATEGY_LAB_CACHE_KEY, JSON.stringify({ ...payload, updatedAt: Date.now() }));
  } catch {
    // ignore quota / serialization failures
  }
};

const extractStrategyLeaderboardList = (payload: any): StrategyEntry[] => {
  if (Array.isArray(payload?.strategies)) return payload.strategies;
  if (Array.isArray(payload?.data?.strategies)) return payload.data.strategies;
  return Array.isArray(payload) ? payload : [];
};

const fetchStrategyLeaderboardPayload = async (endpoint: string) => {
  let primaryPayload: any = null;
  try {
    primaryPayload = await fetchApi(endpoint);
  } catch {
    primaryPayload = null;
  }

  if (extractStrategyLeaderboardList(primaryPayload).length > 0 || typeof window === "undefined") {
    return primaryPayload;
  }

  try {
    const fallbackResponse = await window.fetch(endpoint, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!fallbackResponse.ok) {
      return primaryPayload;
    }
    const fallbackPayload = await fallbackResponse.json();
    if (extractStrategyLeaderboardList(fallbackPayload).length > 0) {
      return fallbackPayload;
    }
    return primaryPayload ?? fallbackPayload;
  } catch {
    return primaryPayload;
  }
};

const snapshotHistoryKey = (prefix: "strategy" | "model", row: LeaderboardHistoryRow, index: number) => {
  return `${prefix}-${row.id ?? row.created_at ?? row.updated_at ?? `row-${index}`}`;
};

const snapshotHistoryLabel = (prefix: "策略" | "模型", row: LeaderboardHistoryRow, index: number) => {
  const createdAt = row.created_at || (typeof row.updated_at === "string" ? row.updated_at : null);
  if (!createdAt) {
    return `${prefix} 快照 #${row.id ?? index + 1}`;
  }
  if (row.id != null) {
    return `${prefix} #${row.id} · ${new Date(createdAt).toLocaleString("zh-TW")}`;
  }
  return `${prefix} 快照 · ${new Date(createdAt).toLocaleString("zh-TW")}`;
};

export default function StrategyLab() {
  const [strategies, setStrategies] = useState<StrategyEntry[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyEntry | null>(null);
  const [strategyMeta, setStrategyMeta] = useState<StrategyLeaderboardMeta>({});
  const [strategyQuadrantPoints, setStrategyQuadrantPoints] = useState<StrategyQuadrantPoint[]>([]);
  const [strategySortKey, setStrategySortKey] = useState<keyof StrategyResult | "name">("overall_score");
  const [strategySortDirection, setStrategySortDirection] = useState<"asc" | "desc">("desc");
  const [modelLeaderboard, setModelLeaderboard] = useState<ModelLeaderboardEntry[]>([]);
  const [modelQuadrantPoints, setModelQuadrantPoints] = useState<QuadrantPoint[]>([]);
  const [modelMeta, setModelMeta] = useState<ModelLeaderboardMeta>({});
  const [modelSortKey, setModelSortKey] = useState<keyof ModelLeaderboardEntry>("overall_score");
  const [modelSortDirection, setModelSortDirection] = useState<"asc" | "desc">("desc");
  const [modelStats, setModelStats] = useState<ModelStatsResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [loadingStrategyName, setLoadingStrategyName] = useState<string | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [backgroundStage, setBackgroundStage] = useState<BackgroundStage | null>(null);
  const [runResult, setRunResult] = useState<StrategyResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("My Strategy");
  const [strategyType, setStrategyType] = useState<"rule_based" | "hybrid">("hybrid");
  const [selectedModelName, setSelectedModelName] = useState<string>("xgboost");
  const [bias50Max, setBias50Max] = useState(DEFAULT_PARAMS.entry.bias50_max);
  const [noseMax, setNoseMax] = useState(DEFAULT_PARAMS.entry.nose_max);
  const [layer2Bias, setLayer2Bias] = useState(DEFAULT_PARAMS.entry.layer2_bias_max);
  const [layer3Bias, setLayer3Bias] = useState(DEFAULT_PARAMS.entry.layer3_bias_max);
  const [layer1, setLayer1] = useState(Math.round(DEFAULT_PARAMS.layers[0] * 100));
  const [layer2, setLayer2] = useState(Math.round(DEFAULT_PARAMS.layers[1] * 100));
  const [layer3, setLayer3] = useState(Math.round(DEFAULT_PARAMS.layers[2] * 100));
  const [confidenceMin, setConfidenceMin] = useState(Math.round(DEFAULT_PARAMS.entry.confidence_min * 100));
  const [entryQualityMin, setEntryQualityMin] = useState(Math.round(DEFAULT_PARAMS.entry.entry_quality_min * 100));
  const [topKPercent, setTopKPercent] = useState(DEFAULT_PARAMS.entry.top_k_percent);
  const [allowedRegimesMode, setAllowedRegimesMode] = useState<"all" | "bull_chop" | "bull_only" | "bear_only">("bull_chop");
  const [capitalMode, setCapitalMode] = useState<"classic_pyramid" | "reserve_90">("classic_pyramid");
  const [baseEntryFractionPct, setBaseEntryFractionPct] = useState(Math.round(DEFAULT_PARAMS.capital_management.base_entry_fraction * 100));
  const [reserveTriggerDrawdownPct, setReserveTriggerDrawdownPct] = useState(Math.round(DEFAULT_PARAMS.capital_management.reserve_trigger_drawdown * 100));
  const [stopLoss, setStopLoss] = useState(Math.round(DEFAULT_PARAMS.stop_loss * 100));
  const [tpBias, setTpBias] = useState(DEFAULT_PARAMS.take_profit_bias);
  const [tpRoi, setTpRoi] = useState(Math.round(DEFAULT_PARAMS.take_profit_roi * 100));
  const [initialCapital, setInitialCapital] = useState(10000);
  const [chartStart, setChartStart] = useState<string>("");
  const [chartEnd, setChartEnd] = useState<string>("");
  const [strategyDataRange, setStrategyDataRange] = useState<BacktestRangeMeta["available"] | null>(null);
  const [investmentHorizon, setInvestmentHorizon] = useState<keyof typeof investmentHorizonLabels>("medium");
  const [activeTab, setActiveTab] = useState<"workspace" | "leaderboard">("workspace");
  const [capitalModeFilter, setCapitalModeFilter] = useState<"all" | "classic_pyramid" | "reserve_90">("all");
  const [strategySleeveFilter, setStrategySleeveFilter] = useState<string>("all");
  const [activeModules, setActiveModules] = useState<EditorModuleId[]>(["pyramid_sl_tp", "turning_point"]);
  const { data: runtimeStatus, loading: runtimeStatusLoading, error: runtimeStatusError } = useApi<StrategyLabRuntimeStatusResponse>("/api/status", 60000);
  const { data: liveDecisionStatus, loading: liveDecisionStatusLoading, error: liveDecisionStatusError } = useApi<StrategyLabLiveDecisionResponse>("/api/predict/confidence", 60000);

  useEffect(() => {
    const cached = Object.keys(STRATEGY_LAB_MEMORY_CACHE).length ? STRATEGY_LAB_MEMORY_CACHE : loadStrategyLabCache();
    if (!cached) return;
    if (Array.isArray(cached.strategies)) setStrategies(cached.strategies);
    if (cached.strategyMeta) setStrategyMeta(cached.strategyMeta);
    if (Array.isArray(cached.strategyQuadrantPoints)) setStrategyQuadrantPoints(cached.strategyQuadrantPoints);
    if (Array.isArray(cached.modelLeaderboard)) setModelLeaderboard(cached.modelLeaderboard);
    if (Array.isArray(cached.modelQuadrantPoints)) setModelQuadrantPoints(cached.modelQuadrantPoints);
    if (cached.modelMeta) setModelMeta(cached.modelMeta);
    if (cached.modelStats) setModelStats(cached.modelStats);
    if (cached.selectedStrategy) setSelectedStrategy(cached.selectedStrategy);
    setInitialLoading(false);
  }, []);

  const activeResult = runResult ?? selectedStrategy?.last_results ?? null;
  const activeMeta = selectedStrategy?.metadata ?? {
    title: name,
    strategy_type: strategyType,
    model_name: selectedModelName,
    model_summary: strategyType === "hybrid" ? `${selectedModelName}：模型+規則混合進場。` : "rule_based：僅使用規則回測。",
    description: "調整左側參數，或點擊排行榜中的策略快速載入設定。",
  };
  const sortedModelLeaderboard = useMemo(() => {
    const rows = [...modelLeaderboard];
    rows.sort((a, b) => {
      const aTier = modelTierOrder[String(a.model_tier || "control")] ?? 99;
      const bTier = modelTierOrder[String(b.model_tier || "control")] ?? 99;
      if (aTier !== bTier) return aTier - bTier;
      const aValue = a[modelSortKey];
      const bValue = b[modelSortKey];
      if (typeof aValue === "string" || typeof bValue === "string") {
        const compared = String(aValue ?? "").localeCompare(String(bValue ?? ""));
        return modelSortDirection === "desc" ? -compared : compared;
      }
      const aComparable = typeof aValue === "number" ? aValue : Number.NEGATIVE_INFINITY;
      const bComparable = typeof bValue === "number" ? bValue : Number.NEGATIVE_INFINITY;
      if (aComparable === bComparable) return String(a.model_name).localeCompare(String(b.model_name));
      return modelSortDirection === "desc" ? bComparable - aComparable : aComparable - bComparable;
    });
    return rows;
  }, [modelLeaderboard, modelSortDirection, modelSortKey]);
  const groupedModelLeaderboard = useMemo(() => {
    const groups = [
      { key: "core", label: "核心模型", description: "目前最適合 Poly-Trader 主線：規則對照 + 穩健 production 候選 + 乾淨 sanity baseline。" },
      { key: "control", label: "對照模型", description: "適合做樹模型 / boosting 對照與補充比較，不建議壓過核心模型。" },
      { key: "research", label: "研究模型", description: "保留在研究層觀察額外訊號，目前不建議優先投入主線。" },
    ] as const;
    return groups
      .map((group) => ({ ...group, rows: sortedModelLeaderboard.filter((row) => String(row.model_tier || "control") === group.key) }))
      .filter((group) => group.rows.length > 0);
  }, [sortedModelLeaderboard]);
  const placeholderModelRows = Array.isArray(modelMeta.placeholder_rows) ? modelMeta.placeholder_rows : [];
  const modelStrategyParamScan = modelMeta.strategy_param_scan ?? null;
  const leaderboardGovernance = modelMeta.leaderboard_governance ?? null;
  const governanceContract = leaderboardGovernance?.governance_contract ?? null;
  const profileSplit = leaderboardGovernance?.profile_split ?? null;
  const modelFallbackCandidates = Array.isArray(modelStrategyParamScan?.best_strategy_candidates)
    ? modelStrategyParamScan.best_strategy_candidates.filter((candidate) => Boolean(candidate))
    : [];
  const strategyCapitalMode = useCallback((entry: StrategyEntry) => {
    const fromResults = entry.last_results?.capital_mode;
    if (fromResults === "reserve_90" || fromResults === "classic_pyramid") {
      return fromResults;
    }
    const fromParams = entry.definition?.params?.capital_management?.mode;
    return fromParams === "reserve_90" ? "reserve_90" : "classic_pyramid";
  }, []);
  const strategyPrimarySleeveKey = (entry: StrategyEntry) => entry.metadata?.primary_sleeve_key || "uncategorized";
  const strategySleeveOptions = useMemo(() => {
    const counts = new Map<string, number>();
    for (const entry of strategies) {
      const key = strategyPrimarySleeveKey(entry);
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    return [
      { key: "all", label: "全部 sleeves", count: strategies.length },
      ...Array.from(counts.entries()).map(([key, count]) => ({
        key,
        label: strategies.find((entry) => strategyPrimarySleeveKey(entry) === key)?.metadata?.primary_sleeve_label || "未分類 sleeve",
        count,
      })),
    ];
  }, [strategies]);

  const sleeveFilteredStrategies = useMemo(() => {
    if (strategySleeveFilter === "all") return strategies;
    return strategies.filter((entry) => strategyPrimarySleeveKey(entry) === strategySleeveFilter);
  }, [strategySleeveFilter, strategies]);

  const filteredStrategies = useMemo(() => {
    if (capitalModeFilter === "all") return sleeveFilteredStrategies;
    return sleeveFilteredStrategies.filter((entry) => strategyCapitalMode(entry) === capitalModeFilter);
  }, [capitalModeFilter, sleeveFilteredStrategies, strategyCapitalMode]);

  const sortedStrategies = useMemo(() => {
    const rows = [...filteredStrategies];
    rows.sort((a, b) => {
      const aValue = strategySortKey === "name" ? a.name : a.last_results?.[strategySortKey];
      const bValue = strategySortKey === "name" ? b.name : b.last_results?.[strategySortKey];
      if (typeof aValue === "string" || typeof bValue === "string") {
        const compared = String(aValue ?? "").localeCompare(String(bValue ?? ""));
        return strategySortDirection === "desc" ? -compared : compared;
      }
      const aComparable = typeof aValue === "number" ? aValue : Number.NEGATIVE_INFINITY;
      const bComparable = typeof bValue === "number" ? bValue : Number.NEGATIVE_INFINITY;
      if (aComparable === bComparable) return String(a.name).localeCompare(String(b.name));
      return strategySortDirection === "desc" ? bComparable - aComparable : aComparable - bComparable;
    });
    return rows;
  }, [filteredStrategies, strategySortDirection, strategySortKey]);
  const competitiveIndicators = useMemo<CompetitiveFeatureRow[]>(() => {
    const featureImportance = modelStats?.feature_importance || {};
    const icValues = modelStats?.ic_values || {};
    const technicalKeys = [
      "rsi14",
      "macd_hist",
      "atr_pct",
      "vwap_dev",
      "bb_pct_b",
      "nw_width",
      "nw_slope",
      "adx",
      "choppiness",
      "donchian_pos",
      "4h_bias50",
      "4h_bias20",
      "4h_bias200",
      "4h_macd_hist",
      "4h_rsi14",
      "4h_ma_order",
      "4h_dist_swing_low",
    ];
    return technicalKeys
      .map((key) => {
        const meta = getSenseConfig(key);
        const importance = featureImportance[`feat_${key}`] ?? featureImportance[key] ?? null;
        const ic = icValues[key] ?? icValues[`feat_${key}`] ?? null;
        const score = (importance ? importance * 100 : 0) + (ic ? Math.abs(ic) * 100 : 0);
        return {
          key,
          label: meta.name,
          description: meta.description,
          importance,
          ic,
          score,
          bucket: (key.startsWith("4h_") ? "4h" : "short") as "4h" | "short",
        };
      })
      .filter((row) => row.importance !== null || row.ic !== null)
      .sort((a, b) => b.score - a.score);
  }, [modelStats]);

  const shortTermCompetitiveIndicators = useMemo(
    () => competitiveIndicators.filter((row) => row.bucket === "short").slice(0, 4),
    [competitiveIndicators]
  );

  const structureCompetitiveIndicators = useMemo(
    () => competitiveIndicators.filter((row) => row.bucket === "4h").slice(0, 4),
    [competitiveIndicators]
  );

  const updateBackgroundStage = (stage: BackgroundStage) => {
    setBackgroundStage(stage);
  };

  const clearBackgroundStage = (mode?: BackgroundStage["mode"]) => {
    setBackgroundStage((current) => {
      if (!current) return null;
      if (mode && current.mode !== mode) return current;
      return null;
    });
  };

  const applyStrategyToForm = (strategy: StrategyEntry) => {
    const params = strategy.definition?.params ?? {};
    const entry = params.entry ?? {};
    setName(strategy.name);
    setStrategyType((strategy.definition?.type as "rule_based" | "hybrid") || "rule_based");
    setSelectedModelName(params.model_name || strategy.metadata?.model_name || "xgboost");
    setBias50Max(entry.bias50_max ?? DEFAULT_PARAMS.entry.bias50_max);
    setNoseMax(entry.nose_max ?? DEFAULT_PARAMS.entry.nose_max);
    setLayer2Bias(entry.layer2_bias_max ?? DEFAULT_PARAMS.entry.layer2_bias_max);
    setLayer3Bias(entry.layer3_bias_max ?? DEFAULT_PARAMS.entry.layer3_bias_max);
    const layers = Array.isArray(params.layers) ? params.layers : DEFAULT_PARAMS.layers;
    const capitalManagement = typeof params.capital_management === "object" && params.capital_management ? params.capital_management : DEFAULT_PARAMS.capital_management;
    setLayer1(Math.round((layers[0] ?? DEFAULT_PARAMS.layers[0]) * 100));
    setLayer2(Math.round((layers[1] ?? DEFAULT_PARAMS.layers[1]) * 100));
    setLayer3(Math.round((layers[2] ?? DEFAULT_PARAMS.layers[2]) * 100));
    setConfidenceMin(Math.round((entry.confidence_min ?? DEFAULT_PARAMS.entry.confidence_min) * 100));
    setEntryQualityMin(Math.round((entry.entry_quality_min ?? DEFAULT_PARAMS.entry.entry_quality_min) * 100));
    setTopKPercent(Math.round(entry.top_k_percent ?? DEFAULT_PARAMS.entry.top_k_percent ?? 0));
    setCapitalMode((capitalManagement.mode as "classic_pyramid" | "reserve_90") ?? DEFAULT_PARAMS.capital_management.mode);
    setBaseEntryFractionPct(Math.round((capitalManagement.base_entry_fraction ?? DEFAULT_PARAMS.capital_management.base_entry_fraction) * 100));
    setReserveTriggerDrawdownPct(Math.round((capitalManagement.reserve_trigger_drawdown ?? DEFAULT_PARAMS.capital_management.reserve_trigger_drawdown) * 100));
    const allowedRegimes = Array.isArray(entry.allowed_regimes) ? entry.allowed_regimes.map((v: string) => String(v).toLowerCase()).sort().join(",") : "";
    setAllowedRegimesMode(
      allowedRegimes === "bear" ? "bear_only" : allowedRegimes === "bull" ? "bull_only" : allowedRegimes === "bull,chop" ? "bull_chop" : "all"
    );
    setStopLoss(Math.round((params.stop_loss ?? DEFAULT_PARAMS.stop_loss) * 100));
    setTpBias(params.take_profit_bias ?? DEFAULT_PARAMS.take_profit_bias);
    setTpRoi(Math.round((params.take_profit_roi ?? DEFAULT_PARAMS.take_profit_roi) * 100));
    setInitialCapital(Math.round(Number(params.initial_capital ?? 10000)));
    const backtestRange = typeof params.backtest_range === "object" && params.backtest_range ? params.backtest_range : {};
    const resultRange = strategy.last_results?.backtest_range ?? null;
    const availableRangeStart = strategyDataRange?.start
      || backtestRange.start
      || resultRange?.available?.start
      || resultRange?.effective?.start
      || strategy.last_results?.chart_context?.start
      || "";
    const availableRangeEnd = strategyDataRange?.end
      || backtestRange.end
      || resultRange?.available?.end
      || resultRange?.effective?.end
      || strategy.last_results?.chart_context?.end
      || "";
    const latestTwoYearRange = resolveLatestTwoYearBacktestRange(availableRangeStart, availableRangeEnd);
    setChartStart(latestTwoYearRange.start);
    setChartEnd(latestTwoYearRange.end);
    setInvestmentHorizon((params.investment_horizon as keyof typeof investmentHorizonLabels) || "medium");
    setActiveModules(inferModulesFromStrategy(strategy));
  };

  const applyModuleSelection = (moduleIds: EditorModuleId[]) => {
    const normalized = normalizeModuleSelection(moduleIds);
    const scenario = buildScenarioFromModules(normalized);
    setActiveModules(normalized);
    setStrategyType(scenario.strategyType);
    setSelectedModelName(scenario.modelName);
    setBias50Max(scenario.bias50Max);
    setNoseMax(scenario.noseMax);
    setLayer2Bias(scenario.layer2Bias);
    setLayer3Bias(scenario.layer3Bias);
    setConfidenceMin(scenario.confidenceMin);
    setEntryQualityMin(scenario.qualityMin);
    setTopKPercent(scenario.topKPercent);
    setAllowedRegimesMode(scenario.allowedRegimesMode);
    setCapitalMode(scenario.capitalMode);
    setBaseEntryFractionPct(scenario.baseEntryFractionPct);
    setReserveTriggerDrawdownPct(scenario.reserveTriggerDrawdownPct);
    setStopLoss(scenario.stopLoss);
    setTpBias(scenario.tpBias);
    setTpRoi(scenario.tpRoi);
    setLayer1(scenario.l1);
    setLayer2(scenario.l2);
    setLayer3(scenario.l3);
    setInvestmentHorizon(scenario.investmentHorizon);
  };

  const toggleModule = (moduleId: EditorModuleId) => {
    const next = activeModules.includes(moduleId)
      ? activeModules.filter((id) => id !== moduleId)
      : [...activeModules, moduleId];
    applyModuleSelection(next);
  };

  const applyBacktestPreset = (preset: "6m" | "1y" | "2y" | "max") => {
    const availableEnd = strategyDataRange?.end ? new Date(strategyDataRange.end) : new Date();
    const availableStart = strategyDataRange?.start ? new Date(strategyDataRange.start) : null;
    if (preset === "max") {
      setChartStart(availableStart ? availableStart.toISOString().slice(0, 16) : "");
      setChartEnd(availableEnd.toISOString().slice(0, 16));
      return;
    }
    const months = preset === "6m" ? 6 : preset === "1y" ? 12 : LEADERBOARD_BACKTEST_WINDOW_MONTHS;
    const nextStart = new Date(availableEnd);
    nextStart.setMonth(nextStart.getMonth() - months);
    if (availableStart && nextStart < availableStart) {
      setChartStart(availableStart.toISOString().slice(0, 16));
      setChartEnd(availableEnd.toISOString().slice(0, 16));
      return;
    }
    setChartStart(nextStart.toISOString().slice(0, 16));
    setChartEnd(availableEnd.toISOString().slice(0, 16));
  };

  const selectStrategyByName = async (strategyName: string) => {
    setLoadingStrategyName(strategyName);
    updateBackgroundStage({
      mode: "select_strategy",
      label: `正在載入策略：${strategyName}`,
      detail: "準備讀取已儲存參數、圖表上下文與交易明細。",
      progress: toStageProgress(0, STAGE_TOTALS.select_strategy),
    });
    try {
      const detail = await fetchApi(`/api/strategies/${encodeURIComponent(strategyName)}`) as StrategyEntry;
      updateBackgroundStage({
        mode: "select_strategy",
        label: `正在載入策略：${strategyName}`,
        detail: "後端資料已回來，正在套用左側設定。",
        progress: toStageProgress(1, STAGE_TOTALS.select_strategy),
      });
      setSelectedStrategy(detail);
      setRunResult(null);
      STRATEGY_LAB_MEMORY_CACHE.selectedStrategy = detail;
      saveStrategyLabCache(STRATEGY_LAB_MEMORY_CACHE);
      applyStrategyToForm(detail);
      updateBackgroundStage({
        mode: "select_strategy",
        label: `正在載入策略：${strategyName}`,
        detail: "表單與工作區已同步，正在完成最後畫面更新。",
        progress: toStageProgress(2, STAGE_TOTALS.select_strategy),
      });
      updateBackgroundStage({
        mode: "select_strategy",
        label: `策略已切換：${strategyName}`,
        detail: "策略明細、價格圖與權益圖已完成同步。",
        progress: toStageProgress(3, STAGE_TOTALS.select_strategy),
      });
    } catch (err: any) {
      setError(err.message || "讀取策略失敗");
    } finally {
      setLoadingStrategyName((current) => (current === strategyName ? null : current));
      window.setTimeout(() => clearBackgroundStage("select_strategy"), 250);
    }
  };

  const loadLeaderboard = async (forceRefresh = false) => {
    const endpoint = `/api/strategies/leaderboard${forceRefresh ? "?refresh=true" : ""}`;
    try {
      const res = await fetchStrategyLeaderboardPayload(endpoint) as any;
      const nextStrategies = extractStrategyLeaderboardList(res);
      const nextQuadrantPoints = Array.isArray(res?.quadrant_points) ? res.quadrant_points : [];
      const nextMeta = {
        target_col: res?.target_col ?? res?.data?.target_col ?? "simulated_pyramid_win",
        target_label: res?.target_label ?? res?.data?.target_label ?? "Canonical Decision Quality",
        sort_semantics: res?.sort_semantics ?? res?.data?.sort_semantics ?? null,
        score_dimensions: Array.isArray(res?.score_dimensions) ? res.score_dimensions : [],
        snapshot_history: Array.isArray(res?.snapshot_history) ? res.snapshot_history : [],
      };
      setStrategies(nextStrategies);
      setStrategyQuadrantPoints(nextQuadrantPoints);
      setStrategyMeta(nextMeta);
      STRATEGY_LAB_MEMORY_CACHE.strategies = nextStrategies;
      STRATEGY_LAB_MEMORY_CACHE.strategyQuadrantPoints = nextQuadrantPoints;
      STRATEGY_LAB_MEMORY_CACHE.strategyMeta = nextMeta;
      saveStrategyLabCache(STRATEGY_LAB_MEMORY_CACHE);
      return nextStrategies;
    } catch (err: any) {
      console.error("Leaderboard error:", err);
      return [];
    }
  };

  const loadModelLeaderboard = async (forceRefresh = false) => {
    try {
      const data = await fetchApi(`/api/models/leaderboard${forceRefresh ? "?refresh=true" : ""}`) as any;
      const nextModelLeaderboard = Array.isArray(data?.leaderboard) ? data.leaderboard : [];
      const nextModelQuadrants = Array.isArray(data?.quadrant_points) ? data.quadrant_points : [];
      const nextModelMeta = {
        refreshing: !!data?.refreshing,
        cached: !!data?.cached,
        stale: !!data?.stale,
        updated_at: data?.updated_at ?? null,
        cache_age_sec: data?.cache_age_sec ?? null,
        warning: data?.warning ?? null,
        leaderboard_warning: data?.leaderboard_warning ?? null,
        error: data?.error ?? null,
        target_col: data?.target_col ?? null,
        target_label: data?.target_label ?? null,
        comparable_count: data?.comparable_count ?? null,
        placeholder_count: data?.placeholder_count ?? null,
        evaluated_row_count: data?.evaluated_row_count ?? null,
        placeholder_rows: Array.isArray(data?.placeholder_rows) ? data.placeholder_rows : [],
        global_metrics: data?.global_metrics ?? null,
        regime_metrics: data?.regime_metrics ?? null,
        skipped_models: Array.isArray(data?.skipped_models) ? data.skipped_models : [],
        score_dimensions: Array.isArray(data?.score_dimensions) ? data.score_dimensions : [],
        storage: data?.storage ?? null,
        snapshot_history: Array.isArray(data?.snapshot_history) ? data.snapshot_history : [],
        strategy_param_scan: data?.strategy_param_scan ?? null,
        leaderboard_governance: data?.leaderboard_governance ?? null,
      };
      setModelLeaderboard(nextModelLeaderboard);
      setModelQuadrantPoints(nextModelQuadrants);
      setModelMeta(nextModelMeta);
      STRATEGY_LAB_MEMORY_CACHE.modelLeaderboard = nextModelLeaderboard;
      STRATEGY_LAB_MEMORY_CACHE.modelQuadrantPoints = nextModelQuadrants;
      STRATEGY_LAB_MEMORY_CACHE.modelMeta = nextModelMeta;
      saveStrategyLabCache(STRATEGY_LAB_MEMORY_CACHE);
    } catch (err) {
      console.error("Model leaderboard error:", err);
      setModelMeta({ error: "模型排行榜載入失敗" });
    }
  };

  const loadModelStats = async () => {
    try {
      const data = await fetchApi("/api/model/stats") as ModelStatsResponse;
      setModelStats(data);
      STRATEGY_LAB_MEMORY_CACHE.modelStats = data;
      saveStrategyLabCache(STRATEGY_LAB_MEMORY_CACHE);
    } catch (err) {
      console.error("Model stats error:", err);
    }
  };

  const loadStrategyDataRange = async () => {
    try {
      const data = await fetchApi("/api/strategy_data_range") as { start?: string | null; end?: string | null; count?: number; span_days?: number | null };
      setStrategyDataRange(data ?? null);
      if (data?.end) {
        applyBacktestPreset("2y");
      }
      return data;
    } catch (err) {
      console.error("Strategy data range error:", err);
      return null;
    }
  };

  useEffect(() => {
    let cancelled = false;
    updateBackgroundStage({
      mode: "initial",
      label: "策略實驗室初始化中",
      detail: "準備同步排行榜、模型資料與預設策略明細。",
      progress: toStageProgress(0, STAGE_TOTALS.initial),
    });
    (async () => {
      try {
        const list = await loadLeaderboard();
        updateBackgroundStage({
          mode: "initial",
          label: "策略實驗室初始化中",
          detail: `策略排行榜已載入 ${list.length} 筆，正在同步模型排行榜。`,
          progress: toStageProgress(1, STAGE_TOTALS.initial),
        });
        await loadModelLeaderboard();
        updateBackgroundStage({
          mode: "initial",
          label: "策略實驗室初始化中",
          detail: "模型排行榜已同步，正在載入模型統計、技術競爭力與資料區間。",
          progress: toStageProgress(2, STAGE_TOTALS.initial),
        });
        await Promise.all([loadModelStats(), loadStrategyDataRange()]);
        updateBackgroundStage({
          mode: "initial",
          label: "策略實驗室初始化中",
          detail: "模型統計已到位，正在掛載預設策略工作區。",
          progress: toStageProgress(3, STAGE_TOTALS.initial),
        });
        if (!selectedStrategy && list.length) {
          await selectStrategyByName(list[0].name);
        }
        updateBackgroundStage({
          mode: "initial",
          label: "策略實驗室已就緒",
          detail: "主要工作區、價格圖與權益圖已完成初始化。",
          progress: toStageProgress(4, STAGE_TOTALS.initial),
        });
      } finally {
        if (!cancelled) {
          setInitialLoading(false);
          window.setTimeout(() => clearBackgroundStage("initial"), 250);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (initialLoading || strategies.length > 0) {
      return;
    }
    const timer = window.setInterval(() => {
      loadLeaderboard(false);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [initialLoading, strategies.length]);

  useEffect(() => {
    if (selectedStrategy || loadingStrategyName || strategies.length === 0) {
      return;
    }
    void selectStrategyByName(strategies[0].name);
  }, [loadingStrategyName, selectedStrategy, strategies]);

  useEffect(() => {
    if (!modelMeta.refreshing) {
      clearBackgroundStage("model_refresh");
      return;
    }
    updateBackgroundStage({
      mode: "model_refresh",
      label: "模型排行榜背景重算中",
      detail: modelMeta.cache_age_sec != null
        ? `目前快取年齡 ${modelMeta.cache_age_sec} 秒，系統持續輪詢最新結果。`
        : "正在輪詢最新 leaderboard 與模型統計。",
      progress: toModelFreshnessProgress(modelMeta.cache_age_sec) ?? 0,
    });
    const timer = window.setInterval(() => {
      loadModelLeaderboard(false);
      loadModelStats();
    }, 15000);
    return () => window.clearInterval(timer);
  }, [modelMeta.refreshing, modelMeta.cache_age_sec]);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    updateBackgroundStage({
      mode: "run_strategy",
      label: `正在執行回測：${name}`,
      detail: "正在整理參數並準備送出回測請求。",
      progress: toStageProgress(0, STAGE_TOTALS.run_strategy),
    });
    try {
      const fallbackTwoYearRange = resolveLatestTwoYearBacktestRange(strategyDataRange?.start, strategyDataRange?.end);
      const effectiveChartStart = chartStart || fallbackTwoYearRange.start;
      const effectiveChartEnd = chartEnd || fallbackTwoYearRange.end;
      const body = {
        name,
        type: strategyType,
        initial_capital: initialCapital,
        auto_backfill: true,
        backtest_range: {
          start: effectiveChartStart ? new Date(effectiveChartStart).toISOString() : null,
          end: effectiveChartEnd ? new Date(effectiveChartEnd).toISOString() : null,
        },
        params: {
          model_name: selectedModelName,
          initial_capital: initialCapital,
          investment_horizon: investmentHorizon,
          editor_modules: activeModules,
          backtest_range: {
            start: effectiveChartStart ? new Date(effectiveChartStart).toISOString() : null,
            end: effectiveChartEnd ? new Date(effectiveChartEnd).toISOString() : null,
          },
          entry: {
            bias50_max: bias50Max,
            nose_max: noseMax,
            pulse_min: 0,
            layer2_bias_max: layer2Bias,
            layer3_bias_max: layer3Bias,
            confidence_min: confidenceMin / 100,
            entry_quality_min: entryQualityMin / 100,
            top_k_percent: topKPercent,
            allowed_regimes: allowedRegimeOptions[allowedRegimesMode],
          },
          layers: [layer1 / 100, layer2 / 100, layer3 / 100].filter((value) => value > 0),
          stop_loss: stopLoss / 100,
          take_profit_bias: tpBias,
          take_profit_roi: tpRoi / 100,
          capital_management: {
            mode: capitalMode,
            base_entry_fraction: baseEntryFractionPct / 100,
            reserve_trigger_drawdown: reserveTriggerDrawdownPct / 100,
          },
          turning_point: activeModules.includes("turning_point") ? {
            enabled: true,
            bottom_score_min: DEFAULT_PARAMS.turning_point.bottom_score_min,
            top_score_take_profit: DEFAULT_PARAMS.turning_point.top_score_take_profit,
            min_profit_pct: DEFAULT_PARAMS.turning_point.min_profit_pct,
          } : { enabled: false },
        },
      };
      const kickoff = await fetchApi("/api/strategies/run_async", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }) as any;
      const jobId = kickoff?.job_id;
      if (!jobId) {
        throw new Error("回測任務未建立成功");
      }

      let data: any = null;
      const pollStartedAt = Date.now();
      while (Date.now() - pollStartedAt < STRATEGY_JOB_MAX_WAIT_MS) {
        let job: any;
        try {
          job = await fetchApi(`/api/strategies/jobs/${jobId}`) as any;
        } catch (pollErr: any) {
          const message = String(pollErr?.message || pollErr || "");
          if (message.includes("not found")) {
            updateBackgroundStage({
              mode: "run_strategy",
              label: `正在執行回測：${name}`,
              detail: "背景 job 狀態遺失，正在改用已儲存策略結果恢復工作區。",
              progress: 90,
            });
            try {
              await loadLeaderboard();
              await selectStrategyByName(name);
              data = { results: STRATEGY_LAB_MEMORY_CACHE.selectedStrategy?.last_results ?? null };
              break;
            } catch {
              throw new Error("背景回測 job 狀態遺失；可能是後端重啟。請重新執行一次回測。")
            }
          }
          throw pollErr;
        }
        updateBackgroundStage({
          mode: "run_strategy",
          label: `正在執行回測：${name}`,
          detail: job?.detail || "背景回測執行中。",
          progress: typeof job?.progress === "number" ? job.progress : toStageProgress(1, STAGE_TOTALS.run_strategy),
          stageKey: job?.stage_key || null,
          stageLabel: job?.stage_label || null,
          steps: Array.isArray(job?.steps) ? job.steps : null,
        });
        if (job?.status === "completed") {
          data = job?.result;
          break;
        }
        if (job?.status === "failed") {
          throw new Error(job?.error || job?.detail || "回測失敗");
        }
        await new Promise((resolve) => window.setTimeout(resolve, STRATEGY_JOB_POLL_INTERVAL_MS));
      }

      if (!data) {
        throw new Error("回測逾時：兩年資料回填可能需要較久，請稍後重試，或先縮短區間確認流程正常。");
      }
      if (data?.error) {
        setError(data.error);
      } else {
        updateBackgroundStage({
          mode: "run_strategy",
          label: `正在執行回測：${name}`,
          detail: "回測結果已返回，正在同步價格圖、權益圖與交易明細。",
          progress: 82,
        });
        const result = data?.results ?? data?.result ?? data?.run_result ?? null;
        const enrichedResult = result
          ? {
              ...result,
              equity_curve: Array.isArray(data?.equity_curve) ? data.equity_curve : result.equity_curve,
              trades: Array.isArray(data?.trades) ? data.trades : result.trades,
              score_series: Array.isArray(data?.score_series) ? data.score_series : result.score_series,
              chart_context: data?.chart_context ?? result?.chart_context,
            }
          : null;
        setRunResult(enrichedResult);
        updateBackgroundStage({
          mode: "run_strategy",
          label: `正在執行回測：${name}`,
          detail: "工作區已載入最新回測結果，正在刷新排行榜。",
          progress: 88,
        });
        await loadLeaderboard();
        updateBackgroundStage({
          mode: "run_strategy",
          label: `正在執行回測：${name}`,
          detail: "策略排行榜已刷新，正在同步模型統計。",
          progress: 93,
        });
        await loadModelStats();
        updateBackgroundStage({
          mode: "run_strategy",
          label: `正在執行回測：${name}`,
          detail: "模型統計已同步，正在把最新策略詳情掛回工作區。",
          progress: 96,
        });
        await selectStrategyByName(name);
        updateBackgroundStage({
          mode: "run_strategy",
          label: `回測完成：${name}`,
          detail: "最新結果、價格圖、分數指標與權益曲線都已同步完成。",
          progress: 100,
        });
      }
    } catch (err: any) {
      setError(err.message || "Execution failed");
    } finally {
      setRunning(false);
      window.setTimeout(() => clearBackgroundStage("run_strategy"), 300);
    }
  };

  const activeModuleDetails = EDITOR_MODULES.filter((module) => activeModules.includes(module.id));
  const moduleCategoryMeta = {
    core: { label: "主 preset", description: "先選主要進出場骨架" },
    signal: { label: "訊號 modifier", description: "再補強進出場品質" },
    risk: { label: "風控 modifier", description: "最後補上資金防守" },
    research: { label: "研究模組", description: "需要時再開" },
  } as const;
  const groupedEditorModules = (Object.keys(moduleCategoryMeta) as Array<keyof typeof moduleCategoryMeta>).map((key) => ({
    key,
    ...moduleCategoryMeta[key],
    modules: EDITOR_MODULES.filter((module) => module.category === key),
  }));
  const editorSummary = buildScenarioFromModules(activeModules);
  const compositeModuleLabel = activeModuleDetails.length > 1
    ? `複合策略：${activeModuleDetails.map((module) => module.label).join(" ＋ ")}`
    : `單一策略：${activeModuleDetails[0]?.label || "未選擇"}`;
  const dynamicHighlights = [
    `${editorSummary.strategyType === "hybrid" ? "Hybrid" : "Rule"} · ${editorSummary.modelName}`,
    capitalMode === "reserve_90" ? `10/90 後守 ${baseEntryFractionPct}%` : `層數 ${layer1}/${layer2}/${layer3}`,
    `信心 ${confidenceMin}% · 品質 ${entryQualityMin}%`,
    investmentHorizonLabels[investmentHorizon],
  ];

  useEffect(() => {
    const latestTwoYearRange = resolveLatestTwoYearBacktestRange(
      strategyDataRange?.start || activeResult?.backtest_range?.effective?.start || activeResult?.chart_context?.start || null,
      strategyDataRange?.end || activeResult?.backtest_range?.effective?.end || activeResult?.chart_context?.end || null,
    );
    setChartStart(latestTwoYearRange.start);
    setChartEnd(latestTwoYearRange.end);
  }, [
    activeResult?.backtest_range?.effective?.start,
    activeResult?.backtest_range?.effective?.end,
    activeResult?.chart_context?.start,
    activeResult?.chart_context?.end,
    strategyDataRange?.start,
    strategyDataRange?.end,
  ]);

  const benchmarkCards = [
    activeResult?.benchmarks?.buy_hold,
    activeResult?.benchmarks?.blind_pyramid,
    activeResult ? { label: "你的策略", roi: activeResult.roi, win_rate: activeResult.win_rate, total_pnl: activeResult.total_pnl, profit_factor: activeResult.profit_factor } : null,
  ].filter(Boolean) as BenchmarkEntry[];

  const capitalModeComparison = useMemo(() => {
    const modes: Array<"classic_pyramid" | "reserve_90"> = ["classic_pyramid", "reserve_90"];
    return modes.map((mode) => {
      const rows = strategies.filter((entry) => strategyCapitalMode(entry) === mode);
      const metrics = rows.map((entry) => entry.last_results).filter(Boolean) as StrategyResult[];
      const avg = (values: Array<number | null | undefined>) => {
        const nums = values.filter((value): value is number => typeof value === "number" && Number.isFinite(value));
        if (!nums.length) return null;
        return nums.reduce((sum, value) => sum + value, 0) / nums.length;
      };
      return {
        mode,
        count: rows.length,
        avgOverall: avg(metrics.map((result) => result.overall_score)),
        avgReliability: avg(metrics.map((result) => result.reliability_score)),
        avgRoi: avg(metrics.map((result) => result.roi)),
        avgMaxDd: avg(metrics.map((result) => result.max_drawdown)),
      };
    });
  }, [strategies, strategyCapitalMode]);

  const activeDecisionContract = activeResult ?? selectedStrategy?.decision_contract ?? null;
  const loadingStrategy = Boolean(loadingStrategyName);
  const modelFreshnessProgress = toModelFreshnessProgress(modelMeta.cache_age_sec);
  const workspaceBusy = running || loadingStrategy || initialLoading;
  const actionProgressStage = running || loadingStrategy || initialLoading ? backgroundStage : null;
  const modelProgressStage = modelMeta.refreshing
    ? {
        mode: "model_refresh" as const,
        label: "模型排行榜背景重算中",
        detail: modelMeta.cache_age_sec != null
          ? `快取年齡 ${modelMeta.cache_age_sec} 秒，背景正在重算最新結果。`
          : "背景正在重算最新排行榜。",
        progress: modelFreshnessProgress ?? null,
      }
    : null;
  useGlobalProgressTask(!!actionProgressStage, actionProgressStage
    ? {
        label: actionProgressStage.label,
        detail: actionProgressStage.detail,
        progress: actionProgressStage.progress,
        tone: running ? "blue" : loadingStrategy ? "cyan" : "violet",
        priority: 70,
        kind: "manual",
      }
    : null);

  useGlobalProgressTask(!!modelProgressStage, modelProgressStage
    ? {
        label: modelProgressStage.label,
        detail: modelProgressStage.detail,
        progress: modelProgressStage.progress,
        tone: "cyan",
        priority: 40,
        kind: "manual",
      }
    : null);

  const activeTargetLabel = activeResult?.target_label || selectedStrategy?.decision_contract?.target_label || strategyMeta.target_label || "Canonical Decision Quality";
  const runStrategyProgressCard = actionProgressStage?.mode === "run_strategy" ? actionProgressStage : null;
  const activeSortSemantics = activeResult?.sort_semantics || selectedStrategy?.decision_contract?.sort_semantics || strategyMeta.sort_semantics || "ROI -> lower max_drawdown -> avg_decision_quality_score -> profit_factor (win_rate reference only)";
  const activeHorizonMinutes = activeResult?.decision_quality_horizon_minutes || selectedStrategy?.decision_contract?.decision_quality_horizon_minutes || activeDecisionContract?.decision_quality_horizon_minutes || 1440;
  const executionReconciliation = runtimeStatus?.execution_reconciliation ?? null;
  const executionSurfaceContract = runtimeStatus?.execution_surface_contract ?? null;
  const executionOperationsSurface = executionSurfaceContract?.operations_surface ?? null;
  const executionDiagnosticsSurface = executionSurfaceContract?.diagnostics_surface ?? null;
  const liveRuntimeTruth = executionSurfaceContract?.live_runtime_truth ?? null;
  const liveRouting = liveRuntimeTruth?.sleeve_routing ?? null;
  const liveActiveSleeves = Array.isArray(liveRouting?.active_sleeves) ? liveRouting.active_sleeves : [];
  const liveInactiveSleeves = Array.isArray(liveRouting?.inactive_sleeves) ? liveRouting.inactive_sleeves : [];
  const liveSupportAlignmentStatus = liveDecisionStatus?.support_alignment_status ?? liveRuntimeTruth?.support_alignment_status ?? null;
  const liveSupportAlignmentSummary = liveDecisionStatus?.support_alignment_summary ?? liveRuntimeTruth?.support_alignment_summary ?? null;
  const liveRuntimeExactSupportRows = liveDecisionStatus?.runtime_exact_support_rows ?? liveRuntimeTruth?.runtime_exact_support_rows ?? null;
  const liveCalibrationExactLaneRows = liveDecisionStatus?.calibration_exact_lane_rows ?? liveRuntimeTruth?.calibration_exact_lane_rows ?? null;
  const liveRuntimeClosureState = liveDecisionStatus?.runtime_closure_state ?? liveRuntimeTruth?.runtime_closure_state ?? null;
  const liveRuntimeClosureSummary = liveDecisionStatus?.runtime_closure_summary ?? liveRuntimeTruth?.runtime_closure_summary ?? null;
  const liveRecentPathologyApplied = Boolean(
    liveDecisionStatus?.decision_quality_recent_pathology_applied ?? liveRuntimeTruth?.decision_quality_recent_pathology_applied
  );
  const liveRecentPathologyReason =
    liveDecisionStatus?.decision_quality_recent_pathology_reason
    ?? liveRuntimeTruth?.decision_quality_recent_pathology_reason
    ?? null;
  const liveRecentPathologyWindow =
    liveDecisionStatus?.decision_quality_recent_pathology_window
    ?? liveRuntimeTruth?.decision_quality_recent_pathology_window
    ?? null;
  const liveRecentPathologyAlerts =
    liveDecisionStatus?.decision_quality_recent_pathology_alerts
    ?? liveRuntimeTruth?.decision_quality_recent_pathology_alerts
    ?? [];
  const liveRecentPathologySummary =
    liveDecisionStatus?.decision_quality_recent_pathology_summary
    ?? liveRuntimeTruth?.decision_quality_recent_pathology_summary
    ?? null;
  const liveScopePathologySummary =
    liveRuntimeTruth?.decision_quality_scope_pathology_summary
    ?? null;
  const liveDeploymentBlockerDetails = liveDecisionStatus?.deployment_blocker_details ?? null;
  const breakerRecentWindow = liveDeploymentBlockerDetails?.recent_window ?? null;
  const breakerRelease = liveDeploymentBlockerDetails?.release_condition ?? null;
  const circuitBreakerActive = liveDecisionStatus?.deployment_blocker === "circuit_breaker_active";
  const breakerWindow = typeof breakerRelease?.recent_window === "number"
    ? breakerRelease.recent_window
    : (typeof breakerRecentWindow?.window_size === "number" ? breakerRecentWindow.window_size : null);
  const breakerWins = typeof breakerRelease?.current_recent_window_wins === "number"
    ? breakerRelease.current_recent_window_wins
    : (typeof breakerRecentWindow?.wins === "number" ? breakerRecentWindow.wins : null);
  const breakerRequiredWins = typeof breakerRelease?.required_recent_window_wins === "number"
    ? breakerRelease.required_recent_window_wins
    : null;
  const breakerWinsGap = typeof breakerRelease?.additional_recent_window_wins_needed === "number"
    ? breakerRelease.additional_recent_window_wins_needed
    : null;
  const breakerRecentWinRate = typeof breakerRelease?.current_recent_window_win_rate === "number"
    ? breakerRelease.current_recent_window_win_rate
    : (typeof breakerRecentWindow?.win_rate === "number" ? breakerRecentWindow.win_rate : null);
  const breakerFloor = typeof breakerRelease?.recent_win_rate_must_be_at_least === "number"
    ? breakerRelease.recent_win_rate_must_be_at_least
    : (typeof breakerRecentWindow?.floor === "number" ? breakerRecentWindow.floor : null);
  const breakerCurrentStreak = typeof breakerRelease?.current_streak === "number" ? breakerRelease.current_streak : null;
  const breakerStreakLimit = typeof breakerRelease?.streak_must_be_below === "number" ? breakerRelease.streak_must_be_below : null;
  const liveSupportAlignmentTone = liveSupportAlignmentStatus === "runtime_ahead_of_calibration"
    ? "text-amber-200"
    : liveSupportAlignmentStatus === "aligned"
      ? "text-emerald-200"
      : "text-slate-200";
  const metadataSmoke = runtimeStatus?.execution_metadata_smoke ?? null;
  const venueChecks = Array.isArray(metadataSmoke?.venues) ? metadataSmoke.venues : [];
  const lifecycleTimeline = executionReconciliation?.lifecycle_timeline ?? null;
  const lifecycleTimelineEvents = Array.isArray(lifecycleTimeline?.events) ? lifecycleTimeline.events : [];
  const runtimeSyncIssues = Array.isArray(executionReconciliation?.issues) ? executionReconciliation.issues : [];
  const liveExecutionBlockers = Array.isArray(executionSurfaceContract?.live_ready_blockers) ? executionSurfaceContract.live_ready_blockers : [];
  const venueReadinessBlockers = liveExecutionBlockers;
  const runtimeStatusPending = runtimeStatusLoading && !runtimeStatus && !runtimeStatusError;
  const liveRuntimePending = liveDecisionStatusLoading && !liveDecisionStatus && !liveDecisionStatusError;
  const liveExecutionSyncPending = runtimeStatusPending && liveRuntimePending;
  const currentLiveBlocker = liveDecisionStatus?.deployment_blocker ?? liveRuntimeTruth?.deployment_blocker ?? null;
  const currentLiveBlockerSummary =
    liveDecisionStatus?.deployment_blocker_reason
    ?? liveRuntimeTruth?.deployment_blocker_reason
    ?? liveRuntimeClosureSummary
    ?? "尚未取得 current live blocker。";
  const metadataSmokeFreshness = metadataSmoke?.freshness ?? null;
  const currentLiveBlockerLabel = liveExecutionSyncPending ? "同步中" : (currentLiveBlocker || "unknown");
  const currentLiveBlockerSummaryLabel = liveExecutionSyncPending
    ? "正在同步 live blocker / runtime closure"
    : currentLiveBlockerSummary;
  const liveDeployStatusLabel = liveExecutionSyncPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");
  const reconciliationStatusLabel = runtimeStatusPending ? "同步中" : (executionReconciliation?.status || "unavailable");
  const reconciliationBadgeLabel = runtimeStatusPending ? "對帳同步中" : `對帳 ${reconciliationStatusLabel}`;
  const reconciliationCheckedAtLabel = runtimeStatusPending
    ? "正在向 /api/status 取得 execution sync 狀態"
    : (executionReconciliation?.checked_at ? new Date(executionReconciliation.checked_at).toLocaleString("zh-TW") : "尚未取得 /api/status");
  const runtimeClosureStateLabel = liveExecutionSyncPending ? "同步中" : (liveRuntimeClosureState || "unknown");
  const runtimeClosureSummaryLabel = liveExecutionSyncPending
    ? "正在同步 runtime closure summary。"
    : (liveRuntimeClosureSummary || "尚未取得 runtime closure summary。");
  const activeSleevesLabel = liveExecutionSyncPending ? "同步中" : (liveRouting?.active_ratio_text || "0/0");
  const activeSleevesSummaryLabel = liveExecutionSyncPending
    ? "正在同步 regime / gate 路由"
    : `${liveRouting?.current_regime || liveDecisionStatus?.regime_label || "—"} · gate ${liveRouting?.current_regime_gate || liveDecisionStatus?.regime_gate || "—"}`;
  const metadataSmokeFreshnessLabel = runtimeStatusPending
    ? "同步中"
    : (metadataSmokeFreshness?.label || metadataSmokeFreshness?.status || "unavailable");
  const venueReadinessBlockersLabel = liveExecutionSyncPending
    ? "同步中"
    : (venueReadinessBlockers.length ? venueReadinessBlockers.join(" · ") : executionSurfaceContract?.operator_message || "目前沒有額外 venue blocker 摘要");
  const lifecycleAudit = executionReconciliation?.lifecycle_audit ?? null;
  const lifecycleContract = executionReconciliation?.lifecycle_contract ?? null;
  const lifecycleArtifactChecklist = Array.isArray(lifecycleContract?.artifact_checklist)
    ? lifecycleContract.artifact_checklist
    : [];
  const lifecycleVenueLanes = Array.isArray(lifecycleContract?.venue_lanes)
    ? lifecycleContract.venue_lanes
    : [];
  const recoveryState = executionReconciliation?.recovery_state ?? null;
  const lifecycleChecklistTone = (status?: string | null) => {
    if (status === "observed" || status === "ready") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
    if (status === "missing" || status === "blocked") return "border-red-500/30 bg-red-500/10 text-red-100";
    if (status === "pending" || status === "pending_optional" || status === "waiting_baseline") return "border-amber-500/30 bg-amber-500/10 text-amber-100";
    return "border-white/10 bg-slate-950/20 text-slate-200";
  };

  return (
    <div className="app-page-shell">
      <div className="app-page-header">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="app-page-kicker">Strategy workspace</div>
            <h2 className="app-page-title">🧪 策略實驗室</h2>
            <span className="text-sm text-slate-400">點排行榜可快速載入</span>
          </div>
          <div className="app-segmented-control text-sm">
            <button
              type="button"
              onClick={() => setActiveTab("workspace")}
              className={`app-segmented-button ${activeTab === "workspace" ? "app-segmented-button-active" : ""}`}
            >
              工作區
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("leaderboard")}
              className={`app-segmented-button ${activeTab === "leaderboard" ? "app-segmented-button-active" : ""}`}
            >
              排行榜
            </button>
          </div>
        </div>
        <div className="mt-4 rounded-2xl border border-cyan-500/20 bg-cyan-500/8 px-4 py-3 text-sm leading-6 text-cyan-50/90">
          <span className="font-semibold text-cyan-100">{LEADERBOARD_BACKTEST_POLICY_LABEL}</span>
          <span className="ml-2 text-cyan-100/80">排行榜回測固定使用最近兩年，降低短窗策略過擬合。</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[360px,minmax(0,1fr)] 2xl:grid-cols-[380px,minmax(0,1fr)] gap-4 items-start">
        <div className="space-y-4 self-start min-w-0">
          <div className="app-surface-card">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-300">⚙️ 策略編輯器</h3>
                <div className="mt-1 text-[11px] leading-5 text-slate-500">只保留必要設定，其他資訊交給右側摘要。</div>
              </div>
              <div className="app-surface-muted text-right">
                <div className="text-[10px] text-slate-500">目前策略</div>
                <div className="text-sm font-semibold text-slate-100">{formatStrategyDisplayName(selectedStrategy)}</div>
                <div className="text-[11px] text-emerald-300">{activeMeta.model_name || "rule_based"}</div>
              </div>
            </div>
            <div className="mt-3 space-y-3">
              <div>
                <label className="text-xs text-slate-500">實驗名稱（僅工作區）</label>
                <input value={name} onChange={(e) => setName(e.target.value)} className="app-control-input mt-1" />
              </div>

              <div className="rounded-xl border border-cyan-700/30 bg-cyan-950/10 px-3 py-3 text-[11px] leading-5 text-cyan-100 space-y-2">
                <div className="font-medium">策略模組選擇</div>
                <div>先選 1 個主 preset，再疊加 modifier；只看摘要，不先讀長說明。</div>
              </div>

              <div className="space-y-4">
                {groupedEditorModules.map((group) => (
                  <div key={group.key} className="space-y-2">
                    <div className="flex items-center justify-between px-1">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{group.label}</div>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {group.modules.map((module) => {
                        const active = activeModules.includes(module.id);
                        return (
                          <button
                            key={module.id}
                            type="button"
                            onClick={() => toggleModule(module.id)}
                            className={`app-target-card ${active ? "app-target-card-active" : ""}`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="flex items-center gap-2 text-sm font-semibold text-slate-100">
                                  <span>{module.emoji}</span>
                                  <span>{module.label}</span>
                                </div>
                                <div className="mt-1 text-[11px] leading-5 text-slate-400">{module.summary}</div>
                              </div>
                              <div className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] ${active ? "border-[#7132f5]/50 bg-[#7132f5]/12 text-[#e3d9ff]" : "border-white/10 text-slate-500"}`}>
                                {active ? "已選取" : module.badge}
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              <div className="app-surface-muted px-3 py-3 text-xs text-slate-300 space-y-3">
                <div>
                  <div className="text-slate-500">目前組合</div>
                  <div className="mt-1 font-semibold text-slate-100">{compositeModuleLabel}</div>
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  {dynamicHighlights.map((item) => (
                    <div key={item} className="rounded-lg border border-slate-700/40 bg-slate-900/40 px-3 py-2 text-slate-200">
                      {item}
                    </div>
                  ))}
                </div>
                {activeModuleDetails.length > 1 && (
                  <div className="rounded-lg border border-cyan-700/30 bg-cyan-950/10 px-3 py-2 text-cyan-100">
                    <div className="font-medium">模組已合成</div>
                    <div className="mt-1 leading-5">{activeModuleDetails.map((module) => module.label).join(" ＋ ")}</div>
                  </div>
                )}
                {activeModules.includes("storm_unwind") && (
                  <div className="rounded-lg border border-amber-700/30 bg-amber-950/10 px-3 py-2 text-amber-100">
                    <div className="font-medium">風暴斬倉已啟用</div>
                    <div className="mt-1 leading-5">低位盈利會優先拿來釋放高位套牢倉。</div>
                  </div>
                )}
              </div>

              <button onClick={handleRun} disabled={workspaceBusy} className={`${workspaceBusy ? "app-button-secondary text-slate-400" : "app-button-primary"} w-full font-semibold text-sm`}>
                {running ? "⏳ 回測中..." : loadingStrategy ? "⏳ 載入策略中..." : initialLoading ? "⏳ 初始化中..." : "▶ 執行回測"}
              </button>
              {runStrategyProgressCard && (
                <div className="rounded-xl border border-cyan-700/30 bg-cyan-950/10 p-3 text-xs text-cyan-50 space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-[11px] text-cyan-200/80">長作業分段進度</div>
                      <div className="mt-1 text-sm font-semibold text-cyan-100">{runStrategyProgressCard.stageLabel || runStrategyProgressCard.label}</div>
                      <div className="mt-1 text-[11px] leading-5 text-cyan-100/80">{runStrategyProgressCard.detail}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-bold text-cyan-100">{Math.round(runStrategyProgressCard.progress)}%</div>
                      <div className="text-[10px] text-cyan-200/70">{runStrategyProgressCard.stageKey || "run_strategy"}</div>
                    </div>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-900/70">
                    <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 transition-all duration-500" style={{ width: `${Math.max(4, runStrategyProgressCard.progress)}%` }} />
                  </div>
                  <div className="grid gap-2">
                    {(runStrategyProgressCard.steps || []).map((step) => {
                      const tone = strategyJobStepTone[step.status] || strategyJobStepTone.pending;
                      const dot = strategyJobStepDotTone[step.status] || strategyJobStepDotTone.pending;
                      return (
                        <div key={step.key} className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 ${tone}`}>
                          <div className="flex items-center gap-2">
                            <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
                            <span className="font-medium">{step.label}</span>
                          </div>
                          <span className="text-[10px]">{formatStrategyJobStepStatus(step.status)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-700/50 bg-slate-950/40 p-3 text-xs leading-5 text-slate-400">
            <div className="font-semibold text-slate-200">策略摘要</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {activeModuleDetails.map((module) => (
                <span key={module.id} className="inline-flex rounded-full border border-cyan-700/40 bg-cyan-950/20 px-2 py-0.5 text-[10px] text-cyan-100">
                  {module.emoji} {module.label}
                </span>
              ))}
            </div>
            <div className="mt-2 border-t border-slate-800/80 pt-2 text-[11px] text-slate-500">{activeMeta.model_summary}</div>
          </div>
        </div>

        <div className="space-y-4 min-w-0">
          {error && <div className="bg-red-900/20 border border-red-700/50 rounded-xl p-4 text-red-400 text-sm">{error}</div>}

          <div className={activeTab === "workspace" ? "space-y-4" : "hidden"}>
            <div className="app-surface-card space-y-4">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-end gap-3">
                    <div>
                      <div className="text-[11px] text-slate-500">回測開始</div>
                      <input type="datetime-local" value={chartStart} onChange={(e) => setChartStart(e.target.value)} className="app-control-input mt-1 text-xs" />
                    </div>
                    <div>
                      <div className="text-[11px] text-slate-500">回測結束</div>
                      <input type="datetime-local" value={chartEnd} onChange={(e) => setChartEnd(e.target.value)} className="app-control-input mt-1 text-xs" />
                    </div>
                    <div>
                      <div className="text-[11px] text-slate-500">起始資金 ($)</div>
                      <input type="number" min="100" step="100" value={initialCapital} onChange={(e) => setInitialCapital(parseInt(e.target.value || "0", 10))} className="app-control-input mt-1 w-[140px] text-xs" />
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                    <span className="text-slate-500">快速區間</span>
                    <div className="app-segmented-control">
                      {[
                        ["6m", "近 6 個月"],
                        ["1y", "近 1 年"],
                        ["2y", "近 2 年"],
                        ["max", "全部可用資料"],
                      ].map(([preset, label]) => (
                        <button key={preset} type="button" onClick={() => applyBacktestPreset(preset as "6m" | "1y" | "2y" | "max")} className="app-segmented-button">
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className={`rounded-lg border px-3 py-2 text-[11px] ${activeResult?.backtest_range?.backfill_required ? "border-amber-700/40 bg-amber-950/10 text-amber-100" : "border-slate-700/50 bg-slate-950/30 text-slate-400"}`}>
                    <div>可用特徵資料：{strategyDataRange?.start ? new Date(strategyDataRange.start).toLocaleDateString("zh-TW") : "—"} → {strategyDataRange?.end ? new Date(strategyDataRange.end).toLocaleDateString("zh-TW") : "—"}</div>
                    <div className="mt-1 text-cyan-100/85">{LEADERBOARD_BACKTEST_POLICY_LABEL} · 最近 {LEADERBOARD_BACKTEST_WINDOW_DAYS} 天。</div>
                    <div>
                      {activeResult?.backtest_range?.backfill_required
                        ? `缺少約 ${Math.round(activeResult.backtest_range.missing_start_days || 0)} 天較早資料，需先回填。`
                        : "資料不足時會直接標示，不會用短資料假裝跑完。"}
                    </div>
                  </div>
                </div>
                <div className="grid min-w-[280px] gap-2 text-[11px] text-slate-400 sm:grid-cols-2">
                  <div className="rounded-lg border border-slate-700/50 bg-slate-950/40 px-3 py-2">
                    <div>回測完成：{activeResult?.run_at ? new Date(activeResult.run_at).toLocaleString("zh-TW") : "—"}</div>
                    <div>交易筆數：{activeResult?.total_trades ?? "—"}</div>
                    <div>實際區間：{activeResult?.backtest_range?.effective?.start ? new Date(activeResult.backtest_range.effective.start).toLocaleDateString("zh-TW") : "—"} → {activeResult?.backtest_range?.effective?.end ? new Date(activeResult.backtest_range.effective.end).toLocaleDateString("zh-TW") : "—"}</div>
                  </div>
                  <div className="rounded-lg border border-cyan-700/30 bg-cyan-950/10 px-3 py-2 text-cyan-100">
                    <div className="font-medium">圖表提示</div>
                    <div>上圖看價格與訊號，下圖看權益與持倉；hover 會同步。</div>
                  </div>
                </div>
              </div>
              <CandlestickChart
                symbol={activeResult?.chart_context?.symbol || "BTCUSDT"}
                interval={activeResult?.chart_context?.interval || "4h"}
                days={14}
                since={toMillis(chartStart) || toMillis(activeResult?.chart_context?.start) || undefined}
                until={toMillis(chartEnd) || toMillis(activeResult?.chart_context?.end) || undefined}
                tradeMarkers={activeResult?.trades || []}
                equityCurve={activeResult?.equity_curve || []}
                scoreSeries={activeResult?.score_series || []}
                title="BTC/USDT 價格圖"
              />
            </div>

            <ExecutionWorkspaceSummary
              title="Live 部署同步"
              subtitle="current live blocker 優先；對帳 healthy 只代表對帳 / runtime mirror 健康，不等於目前可部署。"
              className={executionSyncTone({
                pending: liveExecutionSyncPending,
                liveReady: Boolean(executionSurfaceContract?.live_ready),
                blocker: currentLiveBlocker,
                reconciliationStatus: executionReconciliation?.status,
              })}
              gridClassName="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5"
              aside={(
                <div className="text-right text-xs">
                  <div className="font-semibold">{liveDeployStatusLabel}</div>
                  <div className="opacity-70">current live blocker {currentLiveBlockerLabel}</div>
                  <div className="mt-1 opacity-60">{reconciliationBadgeLabel} · {reconciliationCheckedAtLabel}</div>
                </div>
              )}
              actions={(
                <>
                  <a href={executionOperationsSurface?.route || "/execution"} className="app-button-secondary">
                    前往 Bot 營運 →
                  </a>
                  <a href="/execution/status" className="app-button-secondary">
                    前往執行狀態 →
                  </a>
                </>
              )}
              footer={<div className="text-xs opacity-80">diagnostics surface {executionDiagnosticsSurface?.label || "執行狀態"} · {executionDiagnosticsSurface?.route || "/execution/status"}</div>}
            >
              <ExecutionWorkspaceMetric
                label="current live blocker"
                value={currentLiveBlockerLabel}
                detail={currentLiveBlockerSummaryLabel}
              />
              <ExecutionWorkspaceMetric
                label="venue blockers"
                value={venueReadinessBlockersLabel}
                extra={<VenueReadinessSummary venues={venueChecks} className="mt-2" compact />}
              />
              <ExecutionWorkspaceMetric
                label="runtime closure"
                value={runtimeClosureStateLabel}
                detail={runtimeClosureSummaryLabel}
              />
              <ExecutionWorkspaceMetric
                label="active sleeves"
                value={activeSleevesLabel}
                detail={activeSleevesSummaryLabel}
              />
              <ExecutionWorkspaceMetric
                label="metadata freshness"
                value={<span className={metadataFreshnessTone(metadataSmokeFreshness?.status)}>{metadataSmokeFreshnessLabel}</span>}
                detail={runtimeStatusPending ? "正在向 /api/status 取得 metadata smoke。" : `generated ${metadataSmoke?.generated_at ? new Date(metadataSmoke.generated_at).toLocaleString("zh-TW") : "—"}`}
              />
            </ExecutionWorkspaceSummary>
            <LivePathologySummaryCard
              summary={liveScopePathologySummary}
              title="🧬 Live lane / spillover 對照"
            />

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-slate-300">🧭 綜合能力</div>
                    <div className="text-[11px] text-slate-500">五維能力摘要。</div>
                  </div>
                  <div className={`text-right text-lg font-bold ${decisionQualityTone(activeResult?.avg_decision_quality_score)}`}>
                    {formatDecimal(activeResult?.overall_score, 3)}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {[
                    { label: "Reliability", value: formatDecimal(activeResult?.reliability_score, 3), color: "text-cyan-300" },
                    { label: "Return", value: formatDecimal(activeResult?.return_power_score, 3), color: "text-violet-300" },
                    { label: "Risk", value: formatDecimal(activeResult?.risk_control_score, 3), color: "text-amber-300" },
                    { label: "Capital", value: formatDecimal(activeResult?.capital_efficiency_score, 3), color: "text-fuchsia-300" },
                  ].map((card) => (
                    <div key={card.label} className="rounded-lg bg-slate-800/40 px-3 py-2">
                      <div className="text-[10px] text-slate-500">{card.label}</div>
                      <div className={`text-base font-semibold ${card.color}`}>{card.value}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <div className="text-sm font-semibold text-slate-300">🎯 Decision Quality</div>
                <div className={`text-2xl font-bold ${decisionQualityTone(activeResult?.avg_decision_quality_score)}`}>
                  DQ {formatDecimal(activeResult?.avg_decision_quality_score, 3)}
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-slate-800/40 px-3 py-2"><div className="text-[10px] text-slate-500">預期勝率</div><div className="text-emerald-300 font-semibold">{formatPct(activeResult?.avg_expected_win_rate)}</div></div>
                  <div className="rounded-lg bg-slate-800/40 px-3 py-2"><div className="text-[10px] text-slate-500">預期品質</div><div className="text-cyan-300 font-semibold">{formatDecimal(activeResult?.avg_expected_pyramid_quality, 3)}</div></div>
                  <div className="rounded-lg bg-slate-800/40 px-3 py-2"><div className="text-[10px] text-slate-500">回撤懲罰</div><div className="text-amber-300 font-semibold">{formatPct(activeResult?.avg_expected_drawdown_penalty)}</div></div>
                  <div className="rounded-lg bg-slate-800/40 px-3 py-2"><div className="text-[10px] text-slate-500">深套時間</div><div className="text-orange-300 font-semibold">{formatPct(activeResult?.avg_expected_time_underwater)}</div></div>
                </div>
              </div>

              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <div className="text-sm font-semibold text-slate-300">📈 執行結果</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-slate-800/40 px-3 py-2"><div className="text-[10px] text-slate-500">ROI</div><div className={`${isFiniteNumber(activeResult?.roi) && (activeResult?.roi ?? 0) >= 0 ? "text-green-400" : "text-red-400"} text-lg font-semibold`}>{formatPct(activeResult?.roi, 1, true)}</div></div>
                  <div className="rounded-lg bg-slate-800/40 px-3 py-2"><div className="text-[10px] text-slate-500">Max DD</div><div className="text-red-300 text-lg font-semibold">{formatPct(activeResult?.max_drawdown)}</div></div>
                  <div className="rounded-lg bg-slate-800/40 px-3 py-2"><div className="text-[10px] text-slate-500">PF</div><div className="text-violet-300 text-lg font-semibold">{formatDecimal(activeResult?.profit_factor)}</div></div>
                  <div className="rounded-lg bg-slate-800/40 px-3 py-2"><div className="text-[10px] text-slate-500">Trades</div><div className="text-slate-100 text-lg font-semibold">{activeResult?.total_trades ?? "—"}</div></div>
                </div>
              </div>

              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <div className="text-sm font-semibold text-slate-300">🧠 模型 / Gate 摘要</div>
                <div className="rounded-lg bg-slate-800/40 px-3 py-2 text-xs">
                  <div className="text-[10px] text-slate-500">交易模型</div>
                  <div className="text-emerald-300 font-semibold">{activeMeta.model_name || "rule_based"}</div>
                  <div className="mt-1 text-slate-500">主 gate：{activeResult?.dominant_regime_gate || "—"} · 平均允許層數 {formatDecimal(activeResult?.avg_allowed_layers, 1)}</div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  {[
                    { gate: "ALLOW", color: "text-emerald-300" },
                    { gate: "CAUTION", color: "text-yellow-300" },
                    { gate: "BLOCK", color: "text-red-300" },
                  ].map(({ gate, color }) => (
                    <div key={gate} className="rounded bg-slate-800/40 p-2">
                      <div className="text-slate-500">{gate}</div>
                      <div className={`text-base font-semibold ${color}`}>{activeResult?.regime_gate_summary?.[gate] ?? 0}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr),320px] gap-4">
              <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
                <h3 className="text-sm font-semibold text-slate-300 mb-3">🧾 最近交易</h3>
                <div className="space-y-2 max-h-[340px] overflow-auto text-xs">
                  {(activeResult?.trades || []).slice(-12).reverse().map((trade, idx) => (
                    <div key={`${trade.timestamp || trade.entry_timestamp}-${idx}`} className="rounded border border-slate-700/40 bg-slate-800/20 p-3">
                      <div className="flex justify-between gap-3">
                        <span className="text-slate-200">{trade.entry_timestamp || trade.timestamp ? new Date((trade.entry_timestamp || trade.timestamp) as string).toLocaleString("zh-TW") : "—"}</span>
                        <span className={`${isFiniteNumber(trade.pnl) && (trade.pnl ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>{isFiniteNumber(trade.pnl) ? `${trade.pnl! >= 0 ? "+" : ""}${trade.pnl!.toFixed(2)}` : "—"}</span>
                      </div>
                      <div className="mt-1 text-slate-500">進場 {isFiniteNumber(trade.entry) ? trade.entry!.toFixed(2) : "—"} → 出場 {isFiniteNumber(trade.exit) ? trade.exit!.toFixed(2) : "—"}</div>
                      <div className="mt-1 text-slate-500">原因 {trade.reason || "—"} · 層數 {trade.layers ?? "—"} · Gate {trade.regime_gate || "—"}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <h3 className="text-sm font-semibold text-slate-300">📌 參考摘要</h3>
                <div className="grid grid-cols-1 gap-3 text-xs">
                  {benchmarkCards.map((card) => (
                    <div key={card.label} className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/40">
                      <div className="text-slate-400">{card.label}</div>
                      <div className={`mt-2 text-xl font-bold ${isFiniteNumber(card.roi) && (card.roi ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>{formatPct(card.roi, 1, true)}</div>
                      <div className="mt-1 text-[11px] text-slate-500">勝率 {formatPct(card.win_rate, 1)} · PF {formatDecimal(card.profit_factor)}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className={activeTab === "leaderboard" ? "space-y-4" : "hidden"}>
            <div className="grid grid-cols-1 2xl:grid-cols-[minmax(0,1.1fr),minmax(0,0.9fr)] gap-4">
              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-300">🏆 策略排行榜</h3>
                    <div className="text-[11px] text-slate-500">自動搜尋最佳組合，點一下就能回填設定。</div>
                  </div>
                  <button onClick={() => loadLeaderboard(true)} className="text-xs text-blue-400 hover:text-blue-300">🔄 重新搜尋</button>
                </div>
                <div className="rounded-lg border border-slate-700/40 bg-slate-950/20 p-3 text-xs space-y-2">
                  <div className="font-semibold text-slate-300">多 sleeve 結構</div>
                  <div className="flex flex-wrap gap-2">
                    {strategySleeveOptions.map((option) => (
                      <button
                        key={option.key}
                        type="button"
                        onClick={() => setStrategySleeveFilter(option.key)}
                        className={`rounded-full border px-3 py-1 ${strategySleeveFilter === option.key ? "border-cyan-400/60 bg-cyan-500/15 text-cyan-200" : "border-slate-700/50 text-slate-400 hover:text-slate-200"}`}
                      >
                        {option.label} · {option.count}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="overflow-auto rounded-lg border border-slate-700/40">
                  <table className="w-full text-xs min-w-[980px]">
                    <thead className="bg-slate-950/30 text-slate-500 border-b border-slate-800">
                      <tr>
                        {[
                          { key: "name", label: "策略" },
                          { key: "overall_score", label: "Overall" },
                          { key: "reliability_score", label: "Reliability" },
                          { key: "return_power_score", label: "Return" },
                          { key: "risk_control_score", label: "Risk" },
                          { key: "capital_efficiency_score", label: "Capital" },
                          { key: "roi", label: "ROI" },
                          { key: "win_rate", label: "勝率" },
                          { key: "max_drawdown", label: "Max DD" },
                          { key: "profit_factor", label: "PF" },
                          { key: "total_trades", label: "Trades" },
                        ].map((col) => (
                          <th key={col.key} className="text-right py-2 px-2 first:text-left">
                            <button
                              type="button"
                              className="inline-flex items-center gap-1 hover:text-slate-300"
                              onClick={() => {
                                const key = col.key as keyof StrategyResult | "name";
                                if (strategySortKey === key) {
                                  setStrategySortDirection((current) => (current === "desc" ? "asc" : "desc"));
                                } else {
                                  setStrategySortKey(key);
                                  setStrategySortDirection("desc");
                                }
                              }}
                            >
                              <span>{col.label}</span>
                              {strategySortKey === col.key && <span>{strategySortDirection === "desc" ? "↓" : "↑"}</span>}
                            </button>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {sortedStrategies.map((strategy) => {
                        const r = strategy.last_results;
                        const selected = strategy.name === selectedStrategy?.name;
                        return (
                          <tr key={strategy.name} onClick={() => selectStrategyByName(strategy.name)} className={`cursor-pointer border-b border-slate-800/50 ${selected ? "bg-sky-950/30" : "hover:bg-slate-800/30"}`}>
                            <td className="py-2 px-2 text-slate-200 font-medium align-top text-left">
                              <div>{formatStrategyDisplayName(strategy)}</div>
                              <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px] text-slate-500">
                                <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-cyan-200">{strategy.metadata?.primary_sleeve_label || "未分類 sleeve"}</span>
                                <span>{strategy.metadata?.model_name || strategy.definition?.type} · {investmentHorizonLabels[(strategy.definition?.params?.investment_horizon as keyof typeof investmentHorizonLabels) || "medium"]} · 變化 {typeof strategy.rank_delta === "number" ? (strategy.rank_delta > 0 ? `↑${strategy.rank_delta}` : strategy.rank_delta < 0 ? `↓${Math.abs(strategy.rank_delta)}` : "—") : "—"}</span>
                              </div>
                              <div className="mt-1 text-[10px] text-slate-500">{strategy.metadata?.sleeve_labels?.join(" · ") || "單一路徑"}</div>
                            </td>
                            <td className="py-2 px-2 text-right text-emerald-300 font-semibold">{formatDecimal(r?.overall_score, 3)}</td>
                            <td className="py-2 px-2 text-right text-cyan-300">{formatDecimal(r?.reliability_score, 3)}</td>
                            <td className="py-2 px-2 text-right text-violet-300">{formatDecimal(r?.return_power_score, 3)}</td>
                            <td className="py-2 px-2 text-right text-amber-300">{formatDecimal(r?.risk_control_score, 3)}</td>
                            <td className="py-2 px-2 text-right text-fuchsia-300">{formatDecimal(r?.capital_efficiency_score, 3)}</td>
                            <td className={`py-2 px-2 text-right ${isFiniteNumber(r?.roi) && (r?.roi ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>{formatPct(r?.roi, 1, true)}</td>
                            <td className="py-2 px-2 text-right text-emerald-300">{formatPct(r?.win_rate)}</td>
                            <td className="py-2 px-2 text-right text-red-300">{formatPct(r?.max_drawdown)}</td>
                            <td className="py-2 px-2 text-right text-violet-300">{formatDecimal(r?.profit_factor, 2)}</td>
                            <td className="py-2 px-2 text-right text-slate-300">{r?.total_trades ?? "—"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-300">🤖 模型排行榜</h3>
                    <div className="text-[11px] text-slate-500">保留 LLM leaderboard 風格，但濃縮成一個主卡。</div>
                  </div>
                  <div className="text-[11px] text-slate-500">{modelMeta.updated_at ? `更新 ${new Date(modelMeta.updated_at).toLocaleString("zh-TW")}` : "尚未建立快取"}</div>
                </div>
                <div className="space-y-3">
                  {modelMeta.warning && (
                    <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                      {modelMeta.warning}
                    </div>
                  )}
                  {modelMeta.leaderboard_warning && (
                    <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-3 py-3 text-xs text-yellow-100 space-y-1">
                      <div className="font-semibold text-yellow-200">排行榜治理提示</div>
                      <div>{modelMeta.leaderboard_warning}</div>
                      <div className="text-[11px] text-yellow-200/80">
                        可比較 {modelMeta.comparable_count ?? modelLeaderboard.length} · placeholder {modelMeta.placeholder_count ?? placeholderModelRows.length} · evaluated {modelMeta.evaluated_row_count ?? ((modelMeta.comparable_count ?? modelLeaderboard.length) + (modelMeta.placeholder_count ?? placeholderModelRows.length))}
                      </div>
                    </div>
                  )}
                  {profileSplit?.split_required && governanceContract && (
                    <div className={`rounded-lg border px-3 py-3 text-xs space-y-2 ${governanceContract.treat_as_parity_blocker ? "border-rose-500/30 bg-rose-500/10 text-rose-50" : "border-cyan-500/30 bg-cyan-500/10 text-cyan-50"}`}>
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold">排行榜治理同步</div>
                          <div className="mt-1 text-[11px] opacity-80">{governanceContract.reason || profileSplit.reason || "目前排行榜需要把 global ranking 與 production profile split 顯式同步到 operator surface。"}</div>
                        </div>
                        <div className="text-right text-[11px] opacity-80">
                          <div>{leaderboardGovernance?.generated_at ? `generated ${new Date(leaderboardGovernance.generated_at).toLocaleString("zh-TW")}` : "generated —"}</div>
                          <div>{governanceSupportRows(leaderboardGovernance)}</div>
                        </div>
                      </div>
                      <div className="grid gap-2 xl:grid-cols-2">
                        <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                          <div className="text-[11px] text-slate-300">Global 排名</div>
                          <div className="mt-1 font-medium text-slate-100">{profileSplit.global_profile || leaderboardGovernance?.leaderboard_selected_profile || "—"}</div>
                          <div className="mt-1 text-[11px] text-slate-400">{governanceRoleLabel(profileSplit.global_profile_role)}</div>
                        </div>
                        <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                          <div className="text-[11px] text-slate-300">Production 配置</div>
                          <div className="mt-1 font-medium text-slate-100">{profileSplit.production_profile || leaderboardGovernance?.train_selected_profile || "—"}</div>
                          <div className="mt-1 text-[11px] text-slate-400">{governanceRoleLabel(profileSplit.production_profile_role)}</div>
                        </div>
                      </div>
                      <div className="text-[11px] opacity-80">
                        closure：{governanceContract.current_closure || leaderboardGovernance?.dual_profile_state || "—"}
                        {leaderboardGovernance?.live_current_structure_bucket ? ` · live bucket ${leaderboardGovernance.live_current_structure_bucket}` : ""}
                      </div>
                    </div>
                  )}
                  {(modelMeta.comparable_count ?? modelLeaderboard.length) === 0 && modelFallbackCandidates.length > 0 && (
                    <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-3 text-xs text-cyan-50 space-y-3">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold text-cyan-100">placeholder-only fallback：策略參數重掃候選</div>
                          <div className="mt-1 text-[11px] text-cyan-200/80">
                            {modelStrategyParamScan?.warning || "canonical model leaderboard 仍是 placeholder-only；請改看策略參數重掃候選。"}
                          </div>
                        </div>
                        <div className="text-right text-[11px] text-cyan-200/80">
                          <div>已儲存策略 {modelStrategyParamScan?.saved_strategy_count ?? modelFallbackCandidates.length}</div>
                          <div>
                            {modelStrategyParamScan?.generated_at
                              ? `generated ${new Date(modelStrategyParamScan.generated_at).toLocaleString("zh-TW")}`
                              : "generated —"}
                          </div>
                        </div>
                      </div>
                      <div className="grid gap-2 xl:grid-cols-2">
                        {modelFallbackCandidates.slice(0, 4).map((candidate) => (
                          <div
                            key={`${candidate.name || "candidate"}-${candidate.model_name || "unknown"}`}
                            className="rounded-lg border border-cyan-400/20 bg-slate-950/30 px-3 py-3"
                          >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div className="min-w-0 flex-1">
                                <div className="truncate font-medium text-cyan-50">{candidate.name || "未命名候選"}</div>
                                <div className="mt-1 text-[11px] text-cyan-200/80">
                                  {(candidate.model_name || "unknown model")} · ROI {formatPct(candidate.roi, 1, true)} · 勝率 {formatPct(candidate.win_rate)} · Trades {formatDecimal(candidate.total_trades, 0)}
                                </div>
                              </div>
                              <button
                                type="button"
                                disabled={!candidate.name}
                                onClick={async () => {
                                  if (!candidate.name) return;
                                  await selectStrategyByName(candidate.name);
                                  setActiveTab("workspace");
                                }}
                                className={`rounded-lg border px-3 py-1.5 text-[11px] font-medium ${candidate.name ? "border-cyan-400/30 bg-cyan-400/10 text-cyan-100 hover:border-cyan-300/60 hover:text-cyan-50" : "border-slate-700/50 bg-slate-900/50 text-slate-500"}`}
                              >
                                載入候選 →
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="text-[11px] text-cyan-200/80">
                        這批候選來自 strategy_param_scan；先載入可交易策略，再回頭決定是否要繼續放寬 model deployment profile。
                      </div>
                    </div>
                  )}
                  {groupedModelLeaderboard.length > 0 ? groupedModelLeaderboard.map((group) => (
                    <div key={group.key} className="overflow-auto rounded-lg border border-slate-700/40">
                      <div className="border-b border-slate-800 bg-slate-950/30 px-3 py-2">
                        <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                          <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${modelTierBadgeTone[group.key] || modelTierBadgeTone.control}`}>{group.label}</span>
                          <span className="text-[11px] text-slate-500">{group.description}</span>
                        </div>
                      </div>
                      <table className="w-full min-w-[860px] text-xs">
                        <thead className="bg-slate-950/20 text-slate-500 border-b border-slate-800">
                          <tr>
                            {[
                              { key: "model_name", label: "Model" },
                              { key: "overall_score", label: "Overall" },
                              { key: "reliability_score", label: "Reliability" },
                              { key: "return_power_score", label: "Return" },
                              { key: "avg_roi", label: "ROI" },
                              { key: "avg_max_dd", label: "Max DD" },
                              { key: "avg_trades", label: "Trades" },
                            ].map((col) => (
                              <th key={`${group.key}-${col.key}`} className="px-2 py-2 text-right first:text-left">
                                <button
                                  type="button"
                                  className="inline-flex items-center gap-1 hover:text-slate-300"
                                  onClick={() => {
                                    const key = col.key as keyof ModelLeaderboardEntry;
                                    if (modelSortKey === key) {
                                      setModelSortDirection((current) => (current === "desc" ? "asc" : "desc"));
                                    } else {
                                      setModelSortKey(key);
                                      setModelSortDirection("desc");
                                    }
                                  }}
                                >
                                  <span>{col.label}</span>
                                  {modelSortKey === col.key && <span>{modelSortDirection === "desc" ? "↓" : "↑"}</span>}
                                </button>
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {group.rows.map((model, idx) => (
                            <tr key={`${group.key}-${model.model_name}`} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                              <td className="px-2 py-2 text-left text-slate-200 font-medium">
                                <div className="flex items-center gap-2">
                                  <span>#{idx + 1} {model.model_name}</span>
                                  <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] ${modelTierBadgeTone[String(model.model_tier || group.key)] || modelTierBadgeTone.control}`}>{modelTierLabel(model)}</span>
                                </div>
                                <div className="mt-1 text-[10px] text-slate-500">{model.model_tier_reason || describeRankingReason(model)}</div>
                                <div className="mt-1 text-[10px] text-slate-600">deployment: {deploymentProfileDisplayName(model)} · {deploymentProfileSourceLabel(model)} · {typeof model.rank_delta === "number" ? (model.rank_delta > 0 ? `↑${model.rank_delta}` : model.rank_delta < 0 ? `↓${Math.abs(model.rank_delta)}` : "—") : "—"}</div>
                                <div className="mt-1 text-[10px] text-slate-600">feature: {featureProfileDisplayName(model)} · {featureProfileSourceLabel(model)}{model.selected_feature_profile_blocker_applied && model.selected_feature_profile_blocker_reason ? ` · blocker ${model.selected_feature_profile_blocker_reason}` : ""}</div>
                              </td>
                              <td className="px-2 py-2 text-right text-emerald-300">{formatDecimal(model.overall_score, 3)}</td>
                              <td className="px-2 py-2 text-right text-cyan-300">{formatDecimal(model.reliability_score, 3)}</td>
                              <td className="px-2 py-2 text-right text-violet-300">{formatDecimal(model.return_power_score, 3)}</td>
                              <td className={`px-2 py-2 text-right ${isFiniteNumber(model.avg_roi) && model.avg_roi >= 0 ? "text-green-400" : "text-red-400"}`}>{formatPct(model.avg_roi, 1, true)}</td>
                              <td className="px-2 py-2 text-right text-red-300">{formatPct(model.avg_max_dd)}</td>
                              <td className="px-2 py-2 text-right text-slate-300">{formatDecimal(model.avg_trades, 0)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )) : (
                    <div className="rounded-lg border border-slate-700/40 bg-slate-950/20 px-3 py-4 text-sm text-slate-300">
                      目前沒有可比較的模型排行榜列；請先查看下方 no-trade placeholder，確認 deployment profile 是否過嚴或仍需研究調參。
                    </div>
                  )}
                  {placeholderModelRows.length > 0 && (
                    <div className="overflow-auto rounded-lg border border-amber-500/20 bg-amber-500/5">
                      <div className="border-b border-amber-500/20 bg-amber-500/10 px-3 py-2">
                        <div className="flex items-center gap-2 text-sm font-semibold text-amber-100">
                          <span className="inline-flex rounded-full border border-amber-400/30 px-2 py-0.5 text-[11px]">No-trade placeholder</span>
                          <span className="text-[11px] text-amber-200/80">這些模型在當前 deployment profile 下沒有產生任何交易，因此已從正式排行榜分離。</span>
                        </div>
                      </div>
                      <table className="w-full min-w-[860px] text-xs">
                        <thead className="bg-slate-950/20 text-slate-500 border-b border-slate-800">
                          <tr>
                            <th className="px-2 py-2 text-left">Model</th>
                            <th className="px-2 py-2 text-right">Placeholder rank</th>
                            <th className="px-2 py-2 text-right">Overall</th>
                            <th className="px-2 py-2 text-right">ROI</th>
                            <th className="px-2 py-2 text-right">Trades</th>
                          </tr>
                        </thead>
                        <tbody>
                          {placeholderModelRows.map((model) => (
                            <tr key={`placeholder-${model.model_name}-${model.raw_rank ?? "na"}`} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                              <td className="px-2 py-2 text-left text-slate-200 font-medium">
                                <div className="flex items-center gap-2">
                                  <span>{model.model_name}</span>
                                  <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] ${modelTierBadgeTone[String(model.model_tier || "control")] || modelTierBadgeTone.control}`}>{modelTierLabel(model)}</span>
                                </div>
                                <div className="mt-1 text-[10px] text-slate-500">{describeRankingReason(model)}</div>
                                <div className="mt-1 text-[10px] text-slate-600">deployment: {deploymentProfileDisplayName(model)} · {deploymentProfileSourceLabel(model)}</div>
                                <div className="mt-1 text-[10px] text-slate-600">feature: {featureProfileDisplayName(model)} · {featureProfileSourceLabel(model)}{model.selected_feature_profile_blocker_applied && model.selected_feature_profile_blocker_reason ? ` · blocker ${model.selected_feature_profile_blocker_reason}` : ""}</div>
                              </td>
                              <td className="px-2 py-2 text-right text-amber-200">{typeof model.raw_rank === "number" ? `#${model.raw_rank}` : "—"}</td>
                              <td className="px-2 py-2 text-right text-amber-200">{formatDecimal(model.overall_score, 3)}</td>
                              <td className={`px-2 py-2 text-right ${isFiniteNumber(model.avg_roi) && model.avg_roi >= 0 ? "text-green-400" : "text-red-400"}`}>{formatPct(model.avg_roi, 1, true)}</td>
                              <td className="px-2 py-2 text-right text-amber-100">{formatDecimal(model.avg_trades, 0)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-[280px,minmax(0,1fr)] gap-4">
              <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4 space-y-3 text-xs">
                <div className="text-sm font-semibold text-slate-300">資金模式比較</div>
                <div className="inline-flex rounded-lg border border-slate-700/60 bg-slate-950/50 p-1 text-[11px]">
                  {[
                    { key: "all", label: "全部" },
                    { key: "classic_pyramid", label: "經典金字塔" },
                    { key: "reserve_90", label: "10/90 後守" },
                  ].map((option) => (
                    <button
                      key={option.key}
                      type="button"
                      onClick={() => setCapitalModeFilter(option.key as typeof capitalModeFilter)}
                      className={`rounded-md px-3 py-1.5 ${capitalModeFilter === option.key ? "bg-fuchsia-500/20 text-fuchsia-200" : "text-slate-400 hover:text-slate-200"}`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
                {capitalModeComparison.map((row) => (
                  <div key={row.mode} className={`rounded-lg border px-3 py-3 ${row.mode === "reserve_90" ? "border-fuchsia-700/40 bg-fuchsia-950/10" : "border-slate-700/40 bg-slate-950/20"}`}>
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-medium text-slate-100">{row.mode === "reserve_90" ? "10/90 後守" : "經典金字塔"}</div>
                      <div className="text-slate-500">{row.count} 策略</div>
                    </div>
                    <div className="mt-2 space-y-1 text-slate-400">
                      <div>平均 Overall：<span className="text-emerald-300">{formatDecimal(row.avgOverall, 3)}</span></div>
                      <div>平均 Reliability：<span className="text-cyan-300">{formatDecimal(row.avgReliability, 3)}</span></div>
                      <div>平均 ROI：<span className="text-violet-300">{formatPct(row.avgRoi, 1, true)}</span></div>
                      <div>平均 Max DD：<span className="text-red-300">{formatPct(row.avgMaxDd)}</span></div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <div className="text-sm font-semibold text-slate-300">指標與快照摘要</div>
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                  <div className="rounded-xl border border-slate-700/40 bg-slate-950/30 p-3 space-y-2">
                    <div className="text-sm font-semibold text-slate-300">⚔️ 技術指標競爭力</div>
                    {[
                      { title: "短線節奏 Top", tone: "text-cyan-300", rows: shortTermCompetitiveIndicators },
                      { title: "4H 結構 Top", tone: "text-fuchsia-300", rows: structureCompetitiveIndicators },
                    ].map((section) => (
                      <div key={section.title} className="rounded-lg border border-slate-700/30 bg-slate-800/20 p-3">
                        <div className={`text-xs font-semibold ${section.tone}`}>{section.title}</div>
                        {section.rows.slice(0, 3).map((row) => (
                          <div key={row.key} className="mt-2 text-xs text-slate-400">
                            <div className="text-slate-200">{row.label}</div>
                            <div>IC {row.ic !== null ? row.ic.toFixed(3) : "—"} · Imp {row.importance !== null ? row.importance.toFixed(3) : "—"}</div>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                  <div className="rounded-xl border border-slate-700/40 bg-slate-950/30 p-3 space-y-3 text-xs text-slate-400">
                    <div className="text-sm font-semibold text-slate-300">排行榜快照</div>
                    {(strategyMeta.snapshot_history || []).slice(0, 3).map((row, index) => (
                      <div key={snapshotHistoryKey("strategy", row, index)} className="rounded border border-slate-700/30 bg-slate-800/20 p-2">{snapshotHistoryLabel("策略", row, index)}</div>
                    ))}
                    {(modelMeta.snapshot_history || []).slice(0, 3).map((row, index) => (
                      <div key={snapshotHistoryKey("model", row, index)} className="rounded border border-slate-700/30 bg-slate-800/20 p-2">{snapshotHistoryLabel("模型", row, index)}</div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
