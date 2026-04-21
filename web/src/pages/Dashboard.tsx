/**
 * Dashboard v2.0 — 使用者體驗增強版
 */
import { useState, useEffect, useCallback } from "react";
import RadarChart from "../components/RadarChart";
import AdviceCard from "../components/AdviceCard";
import FeatureChart from "../components/FeatureChart";
import CandlestickChart from "../components/CandlestickChart";
import LivePathologySummaryCard, { type DecisionQualityScopePathologySummary } from "../components/LivePathologySummaryCard";
import RecentCanonicalDriftCard, { type RecentCanonicalDriftSummary } from "../components/RecentCanonicalDriftCard";
import VenueReadinessSummary from "../components/VenueReadinessSummary";
import { ExecutionWorkspaceMetric, ExecutionWorkspaceSummary } from "../components/execution/ExecutionWorkspaceSummary";
import { buildWsCandidateUrls, rememberActiveApiBaseFromWsUrl, useApi, fetchApi, prewarmActiveApiBase } from "../hooks/useApi";
import ConfidenceIndicator from "../components/ConfidenceIndicator";
import { ALL_SENSES, getSenseConfig } from "../config/senses";
import {
  humanizeCurrentLiveBlockerLabel,
  humanizeExecutionReason,
  humanizeExecutionReconciliationStatusLabel,
  isExecutionReconciliationLimitedEvidence,
} from "../utils/runtimeCopy";

interface SensesResponse {
  senses: Record<string, any>;
  scores: Record<string, number>;
  raw?: Record<string, number>;
  recommendation: {
    score: number;
    summary: string;
    descriptions: string[];
    action: string;
    timestamp?: string;
  };
}

interface FeatureCoverageResponse {
  maturity_counts?: {
    core: number;
    research: number;
    blocked: number;
  };
}

interface ModelStats {
  model_loaded: boolean;
  sample_count: number;
  label_distribution: Record<string, number>;
  cv_accuracy: number | null;
  feature_importance: Record<string, number>;
  ic_values: Record<string, number>;
  model_params: Record<string, any>;
}

type LiveRuntimeTruth = {
  runtime_closure_state?: string | null;
  runtime_closure_summary?: string | null;
  signal?: string | null;
  confidence?: number | null;
  allowed_layers?: number | null;
  allowed_layers_raw?: number | null;
  allowed_layers_raw_reason?: string | null;
  allowed_layers_reason?: string | null;
  deployment_blocker?: string | null;
  deployment_blocker_reason?: string | null;
  execution_guardrail_reason?: string | null;
  support_rows_text?: string | null;
  support_route_verdict?: string | null;
  support_governance_route?: string | null;
  support_progress?: {
    gap_to_minimum?: number | null;
  } | null;
  current_live_structure_bucket_gap_to_minimum?: number | null;
  q15_exact_supported_component_patch_applied?: boolean | null;
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
  decision_quality_scope_pathology_summary?: DecisionQualityScopePathologySummary | null;
};

interface RuntimeStatusResponse {
  automation: boolean;
  dry_run: boolean;
  symbol: string;
  timestamp: string;
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
      role?: string;
      status?: string;
      message?: string;
      upgrade_prerequisite?: string;
    } | null;
    readiness_scope?: string;
    live_ready?: boolean;
    live_ready_blockers?: string[];
    operator_message?: string;
    live_runtime_truth?: LiveRuntimeTruth | null;
    recent_canonical_drift?: RecentCanonicalDriftSummary | null;
  } | null;
  execution_metadata_smoke?: {
    available?: boolean;
    artifact_path?: string;
    generated_at?: string;
    symbol?: string;
    all_ok?: boolean;
    ok_count?: number;
    venues_checked?: number;
    error?: string;
    freshness?: {
      status?: "fresh" | "stale" | "unavailable" | string;
      label?: string;
      reason?: string;
      age_minutes?: number | null;
      stale_after_minutes?: number | null;
    } | null;
    governance?: {
      status?: string;
      operator_action?: string;
      operator_message?: string;
      refresh_command?: string;
      escalation_message?: string | null;
      auto_refresh?: {
        attempted_at?: string | null;
        completed_at?: string | null;
        status?: string;
        reason?: string;
        next_retry_at?: string | null;
        error?: string | null;
        cooldown_seconds?: number | null;
      } | null;
      background_monitor?: {
        status?: string;
        reason?: string;
        checked_at?: string | null;
        freshness_status?: string | null;
        governance_status?: string | null;
        error?: string | null;
        interval_seconds?: number | null;
      } | null;
      external_monitor?: {
        available?: boolean;
        artifact_path?: string;
        source?: string;
        status?: string;
        reason?: string;
        checked_at?: string | null;
        freshness_status?: string | null;
        governance_status?: string | null;
        error?: string | null;
        interval_seconds?: number | null;
        command?: string | null;
        install_contract?: {
          preferred_host_lane?: string;
          generator_command?: string;
          manual_run_command?: string;
          install_status?: {
            status?: string;
            installed?: boolean;
            active_lane?: string | null;
            checked_at?: string | null;
            lanes?: {
              user_crontab?: {
                installed?: boolean;
                verify_command?: string;
                stdout?: string;
                stderr?: string;
              } | null;
              systemd_user?: {
                installed?: boolean;
                verify_command?: string;
                stdout?: string;
                stderr?: string;
              } | null;
            } | null;
          } | null;
          fallback?: {
            reason?: string;
            command?: string;
            verify_command?: string;
          } | null;
          user_crontab?: {
            schedule?: string;
            entry?: string;
            install_command?: string;
            verify_command?: string;
          } | null;
          systemd_user?: {
            service_file?: string;
            timer_file?: string;
            verify_command?: string;
          } | null;
        } | null;
        freshness?: {
          status?: "fresh" | "stale" | "unavailable" | string;
          label?: string;
          reason?: string;
          age_minutes?: number | null;
          stale_after_minutes?: number | null;
        } | null;
        ticking_state?: {
          status?: "install-ready" | "installed" | "observed-ticking" | "installed-but-not-ticking" | string;
          reason?: string;
          message?: string;
          installed?: boolean;
          active_lane?: string | null;
          checked_at?: string | null;
          freshness_status?: string | null;
          age_minutes?: number | null;
          stale_after_minutes?: number | null;
        } | null;
      } | null;
    } | null;
    venues?: Array<{
      venue?: string;
      ok?: boolean;
      enabled_in_config?: boolean;
      credentials_configured?: boolean;
      error?: string | null;
      contract?: {
        symbol?: string;
        min_qty?: number | null;
        min_cost?: number | null;
        step_size?: string | number | null;
        tick_size?: string | number | null;
      } | null;
    }>;
  } | null;
  execution?: {
    mode?: string;
    venue?: string;
    live_enabled?: boolean;
    kill_switch?: boolean;
    health?: {
      connected?: boolean;
      credentials_configured?: boolean;
      [key: string]: unknown;
    } | null;
    live_runtime_truth?: LiveRuntimeTruth | null;
    recent_canonical_drift?: RecentCanonicalDriftSummary | null;
    guardrails?: {
      kill_switch?: boolean;
      max_daily_loss_pct?: number;
      daily_loss_ratio?: number | null;
      daily_loss_halt?: boolean;
      max_consecutive_failures?: number;
      consecutive_failures?: number;
      failure_halt?: boolean;
      last_failure?: { message?: string; timestamp?: string } | null;
      last_reject?: {
        code?: string;
        message?: string;
        timestamp?: string;
        context?: {
          field?: string;
          raw_value?: number | null;
          adjusted_value?: number | null;
          delta?: number | null;
          step_size?: string | number | null;
          precision?: string | number | null;
          rules?: Record<string, unknown> | null;
        } | null;
      } | null;
      last_order?: {
        venue?: string;
        symbol?: string;
        side?: string;
        qty?: number;
        price?: number | null;
        status?: string;
        timestamp?: number;
        order_id?: string | null;
        client_order_id?: string | null;
        normalization?: {
          requested?: { qty?: number | null; price?: number | null; symbol?: string; side?: string; type?: string } | null;
          normalized?: {
            qty?: number | null;
            price?: number | null;
            symbol?: string;
            side?: string;
            type?: string;
            qty_changed?: boolean;
            price_changed?: boolean;
          } | null;
          contract?: {
            step_size?: string | number | null;
            tick_size?: string | number | null;
            min_qty?: number | null;
            min_cost?: number | null;
          } | null;
        } | null;
      } | null;
      live_runtime_truth?: LiveRuntimeTruth | null;
    } | null;
  } | null;
  recent_canonical_drift?: RecentCanonicalDriftSummary | null;
  account?: {
    venue?: string;
    mode?: string;
    dry_run?: boolean;
    requested_symbol?: string | null;
    normalized_symbol?: string | null;
    captured_at?: string | null;
    degraded?: boolean;
    operator_message?: string | null;
    recovery_hint?: string | null;
    error?: string | null;
    position_count?: number;
    open_order_count?: number;
    balance?: {
      free?: number;
      total?: number;
      currency?: string;
      [key: string]: unknown;
    } | null;
    positions?: Array<Record<string, unknown>>;
    open_orders?: Array<Record<string, unknown>>;
    health?: {
      connected?: boolean;
      credentials_configured?: boolean;
      error?: string;
      [key: string]: unknown;
    } | null;
  } | null;
  execution_reconciliation?: {
    status?: string;
    summary?: string;
    checked_at?: string;
    issues?: string[];
    account_snapshot?: {
      captured_at?: string | null;
      degraded?: boolean;
      position_count?: number;
      open_order_count?: number;
      freshness?: {
        status?: string;
        reason?: string;
        age_minutes?: number | null;
        stale_after_minutes?: number | null;
      } | null;
    } | null;
    symbol_scope?: {
      config_symbol?: string;
      requested_symbol?: string | null;
      normalized_symbol?: string | null;
      status?: string;
      reason?: string;
    } | null;
    runtime_last_order?: {
      status?: string;
      order?: {
        symbol?: string;
        side?: string;
        status?: string;
        order_id?: string | null;
        client_order_id?: string | null;
      } | null;
    } | null;
    trade_history_alignment?: {
      status?: string;
      reason?: string;
      latest_trade?: {
        timestamp?: string | null;
        symbol?: string | null;
        exchange?: string | null;
        action?: string | null;
        order_id?: string | null;
        client_order_id?: string | null;
        order_status?: string | null;
        is_dry_run?: boolean | null;
      } | null;
    } | null;
    open_order_alignment?: {
      status?: string;
      reason?: string;
      matched_open_order?: {
        id?: string | null;
        symbol?: string | null;
        status?: string | null;
      } | null;
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
      event_type_counts?: Record<string, number>;
      event_types_seen?: string[];
      required_event_types?: string[];
      missing_event_types?: string[];
      replay_key_ready?: boolean;
      replay_readiness?: string;
      replay_readiness_reason?: string;
      replay_verdict?: string;
      replay_verdict_reason?: string;
      replay_verdict_summary?: string;
      baseline_contract_status?: string;
      partial_fill_observed?: boolean;
      cancel_observed?: boolean;
      terminal_state_observed?: boolean;
      artifact_coverage?: string;
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
      replay_key?: {
        order_id?: string | null;
        client_order_id?: string | null;
      } | null;
      latest_event?: {
        timestamp?: string | null;
        event_type?: string | null;
        order_state?: string | null;
        summary?: string | null;
      } | null;
      events?: Array<{
        timestamp?: string | null;
        event_type?: string | null;
        order_state?: string | null;
        source?: string | null;
        summary?: string | null;
        order_id?: string | null;
        client_order_id?: string | null;
      }>;
    } | null;
  } | null;
  raw_continuity?: {
    status?: "clean" | "repaired" | "error" | string;
    checked_at?: string;
    error?: string;
    continuity_repair?: {
      inserted_total?: number;
      coarse_inserted?: number;
      fine_inserted?: number;
      bridge_inserted?: number;
      used_bridge?: boolean;
      used_fine_grain?: boolean;
    };
  } | null;
  feature_continuity?: {
    status?: "clean" | "repaired" | "error" | string;
    checked_at?: string;
    error?: string;
    continuity_repair?: {
      inserted_total?: number;
      remaining_missing?: number;
    };
  } | null;
}

interface ConfidenceData {
  error?: string;
  confidence: number;
  signal: string;
  confidence_level: string;
  should_trade: boolean;
  regime_gate?: string | null;
  structure_bucket?: string | null;
  current_live_structure_bucket?: string | null;
  entry_quality?: number | null;
  entry_quality_label?: string | null;
  allowed_layers?: number | null;
  allowed_layers_reason?: string | null;
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
      streak_must_be_below?: number | null;
      current_streak?: number | null;
      recent_window?: number | null;
      recent_win_rate_must_be_at_least?: number | null;
      current_recent_window_win_rate?: number | null;
      current_recent_window_wins?: number | null;
      required_recent_window_wins?: number | null;
      additional_recent_window_wins_needed?: number | null;
    } | null;
  } | null;
  support_route_verdict?: string | null;
  support_route_deployable?: boolean | null;
  support_progress?: {
    status?: string | null;
    current_rows?: number | null;
    minimum_support_rows?: number | null;
    gap_to_minimum?: number | null;
    delta_vs_previous?: number | null;
  } | null;
  minimum_support_rows?: number | null;
  current_live_structure_bucket_gap_to_minimum?: number | null;
  floor_cross_verdict?: string | null;
  legal_to_relax_runtime_gate?: boolean | null;
  remaining_gap_to_floor?: number | null;
  best_single_component?: string | null;
  best_single_component_required_score_delta?: number | null;
  component_experiment_verdict?: string | null;
  q15_exact_supported_component_patch_applied?: boolean | null;
  decision_quality_horizon_minutes?: number | null;
  decision_quality_calibration_scope?: string | null;
  decision_quality_sample_size?: number | null;
  expected_win_rate?: number | null;
  expected_pyramid_quality?: number | null;
  expected_drawdown_penalty?: number | null;
  expected_time_underwater?: number | null;
  decision_quality_score?: number | null;
  decision_quality_label?: string | null;
  decision_profile_version?: string | null;
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
  timestamp: string;
}

interface DashboardScorePoint {
  timestamp: string;
  score?: number | null;
}

interface TradeFeedbackState {
  tone: "success" | "error" | "pending";
  title: string;
  detail: string;
  timestamp: string;
}

interface FeatureHistoryRow {
  timestamp: string;
  [key: string]: string | number | null | undefined;
}

const DASHBOARD_SCORE_WEIGHTS: Record<string, number> = {
  pulse: 0.18,
  eye: 0.12,
  nose: 0.12,
  tongue: 0.08,
  body: 0.06,
  bb_pct_b: 0.10,
  nw_slope: 0.08,
  adx: 0.05,
  vix: 0.04,
  dxy: 0.04,
  "4h_bias50": 0.07,
  "4h_dist_swing_low": 0.04,
  "4h_rsi14": 0.02,
};

function computeDashboardCompositeScore(row: Record<string, string | number | null | undefined>): number | null {
  let weightedSum = 0;
  let weightTotal = 0;
  for (const [key, weight] of Object.entries(DASHBOARD_SCORE_WEIGHTS)) {
    const value = row[key];
    if (typeof value !== "number" || !Number.isFinite(value)) continue;
    weightedSum += value * weight;
    weightTotal += weight;
  }
  if (weightTotal <= 0) return null;
  return Math.max(0, Math.min(1, weightedSum / weightTotal));
}

function formatGuardrailValue(value: unknown, digits = 6): string {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "—";
    return value.toFixed(digits).replace(/\.?0+$/, "");
  }
  if (typeof value === "string" && value.trim()) return value;
  return "—";
}

function formatPct(value: number | null | undefined, digits = 1): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

function formatGuardrailRules(rules: Record<string, unknown> | null | undefined): string[] {
  if (!rules) return [];
  return Object.entries(rules)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => `${key}: ${formatGuardrailValue(value)}`);
}

function readRecordString(record: Record<string, unknown> | null | undefined, keys: string[]): string | null {
  if (!record) return null;
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return null;
}

function readRecordNumber(record: Record<string, unknown> | null | undefined, keys: string[]): number | null {
  if (!record) return null;
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
  }
  return null;
}

function getSmokeFreshnessTone(status: string | undefined | null): string {
  if (status === "fresh") return "border-emerald-700/40 bg-emerald-950/20 text-emerald-200";
  if (status === "stale") return "border-amber-700/40 bg-amber-950/20 text-amber-200";
  return "border-slate-700/40 bg-slate-950/20 text-slate-300";
}

function getSmokeFreshnessLabel(status: string | undefined | null): string {
  if (status === "fresh") return "FRESH";
  if (status === "stale") return "STALE";
  return "UNAVAILABLE";
}

function getSmokeGovernanceTone(status: string | undefined | null): string {
  if (status === "healthy") return "border-emerald-700/40 bg-emerald-950/20 text-emerald-200";
  if (status === "refresh_required") return "border-amber-700/40 bg-amber-950/20 text-amber-200";
  return "border-red-700/40 bg-red-950/20 text-red-200";
}

function getExternalMonitorTickingTone(status: string | undefined | null): string {
  if (status === "observed-ticking") return "border-emerald-700/40 bg-emerald-950/20 text-emerald-200";
  if (status === "installed") return "border-sky-700/40 bg-sky-950/20 text-sky-200";
  if (status === "install-ready") return "border-slate-700/40 bg-slate-950/20 text-slate-300";
  return "border-amber-700/40 bg-amber-950/20 text-amber-200";
}

function getReconciliationTone(status: string | undefined | null): string {
  if (status === "healthy") return "border-emerald-700/40 bg-emerald-950/20 text-emerald-200";
  if (status === "degraded") return "border-red-700/40 bg-red-950/20 text-red-200";
  if (status === "warning") return "border-amber-700/40 bg-amber-950/20 text-amber-200";
  return "border-slate-700/40 bg-slate-950/20 text-slate-200";
}

function getLifecycleChecklistTone(status: string | undefined | null): string {
  if (status === "observed" || status === "ready") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
  if (status === "missing" || status === "blocked") return "border-red-500/30 bg-red-500/10 text-red-100";
  if (status === "pending" || status === "pending_optional" || status === "waiting_baseline") return "border-amber-500/30 bg-amber-500/10 text-amber-100";
  return "border-white/10 bg-slate-950/20 text-slate-200";
}

export default function Dashboard() {
  const [interval, setInterval] = useState("4h");
  const [days, setDays] = useState(14);
  const [selectedSense, setSelectedSense] = useState<string | null>(null);
  const [showFeatureHistory, setShowFeatureHistory] = useState(false);
  const [dashboardScoreSeries, setDashboardScoreSeries] = useState<DashboardScorePoint[]>([]);
  // Build initial scores from ALL known features (8 core + 2 macro + 5 TI + 6 P0/P1 + 10 4H)
  const defaultScores: Record<string, number> = {};
  const allFeatures = [...Object.keys(ALL_SENSES)];
  for (const key of allFeatures) {
    defaultScores[key] = 0.5;
  }

  const [liveScores, setLiveScores] = useState<Record<string, number>>(defaultScores);
  const [liveAdvice, setLiveAdvice] = useState<any>(null);
  const [lastUpdate, setLastUpdate] = useState<string>();
  const [wsConnected, setWsConnected] = useState(false);
  const [tradeFeedback, setTradeFeedback] = useState<TradeFeedbackState | null>(null);

  const { data: sensesData, error: apiError, refresh: refreshSenses } = useApi<SensesResponse>("/api/senses", 30000);
  const { data: featureCoverageData } = useApi<FeatureCoverageResponse>("/api/features/coverage?days=30", 60000);
  const { data: confidenceData } = useApi<ConfidenceData>("/api/predict/confidence", 60000);
  const { data: modelStats } = useApi<ModelStats>("/api/model/stats", 60000);
  const { data: runtimeStatus, loading: runtimeStatusLoading, error: runtimeStatusError, refresh: refreshRuntimeStatus } = useApi<RuntimeStatusResponse>("/api/status", 60000);

  // WebSocket
  useEffect(() => {
    let ws: WebSocket | null = null;
    let connectBootstrapTimer = 0;
    let reconnectTimer = 0;
    let disposed = false;

    const closeSocketWithoutHandshakeNoise = (socket: WebSocket | null) => {
      if (!socket) return;
      if (socket.readyState !== WebSocket.OPEN) return;
      try {
        socket.close();
      } catch {}
    };

    const scheduleReconnect = () => {
      if (disposed) return;
      window.clearTimeout(reconnectTimer);
      reconnectTimer = window.setTimeout(connect, 5000);
    };

    const connect = () => {
      void prewarmActiveApiBase().catch(() => null).then(() => {
        if (disposed) return;
        const wsCandidates = buildWsCandidateUrls("/ws/live");
        const connectAttempt = (attemptIndex: number) => {
          if (disposed) return;
          if (attemptIndex >= wsCandidates.length) {
            scheduleReconnect();
            return;
          }

          const url = wsCandidates[attemptIndex];
          const candidate = new WebSocket(url);
          ws = candidate;
          let opened = false;
          let advanced = false;

          const openTimeout = window.setTimeout(() => {
            if (disposed || opened || advanced) return;
            advanced = true;
            closeSocketWithoutHandshakeNoise(candidate);
            connectAttempt(attemptIndex + 1);
          }, 1500);

          candidate.onopen = () => {
            if (disposed || advanced) {
              candidate.close();
              return;
            }
            opened = true;
            window.clearTimeout(openTimeout);
            rememberActiveApiBaseFromWsUrl(url);
            setWsConnected(true);
          };

          candidate.onmessage = (event) => {
            try {
              const msg = JSON.parse(event.data);
              if (msg.type === "senses_update" || msg.type === "connected") {
                const data = msg.data;
                if (data?.scores) setLiveScores(data.scores);
                if (data?.recommendation) setLiveAdvice(data.recommendation);
                if (data?.timestamp) setLastUpdate(new Date(data.timestamp).toLocaleTimeString("zh-TW"));
              }
            } catch {}
          };

          candidate.onerror = () => {
            setWsConnected(false);
            if (disposed || opened || advanced) return;
            advanced = true;
            window.clearTimeout(openTimeout);
            closeSocketWithoutHandshakeNoise(candidate);
            connectAttempt(attemptIndex + 1);
          };

          candidate.onclose = () => {
            if (ws === candidate) {
              ws = null;
            }
            setWsConnected(false);
            window.clearTimeout(openTimeout);
            if (disposed) return;
            if (!opened) {
              if (!advanced) {
                advanced = true;
                connectAttempt(attemptIndex + 1);
              }
              return;
            }
            scheduleReconnect();
          };
        };

        connectAttempt(0);
      });
    };

    // Defer the first socket open by one macrotask so React.StrictMode's
    // development-only mount→cleanup→mount probe can cancel the bootstrap
    // timer before a real handshake starts. This keeps dev console output free
    // of self-inflicted "closed before the connection is established" noise.
    connectBootstrapTimer = window.setTimeout(() => {
      connect();
    }, 0);
    return () => {
      disposed = true;
      window.clearTimeout(connectBootstrapTimer);
      window.clearTimeout(reconnectTimer);
      closeSocketWithoutHandshakeNoise(ws);
    };
  }, []);

  // 更新最後更新時間
  useEffect(() => {
    if (sensesData?.recommendation?.timestamp) {
      setLastUpdate(new Date(sensesData.recommendation.timestamp).toLocaleTimeString("zh-TW"));
    }
  }, [sensesData]);

  useEffect(() => {
    let cancelled = false;
    const loadScoreSeries = async () => {
      try {
        const rows = await fetchApi(`/api/features?days=${days}`) as FeatureHistoryRow[];
        const nextSeries = (rows || []).map((row) => ({
          timestamp: row.timestamp,
          score: computeDashboardCompositeScore(row),
        }));
        if (!cancelled) {
          setDashboardScoreSeries(nextSeries);
        }
      } catch (error) {
        if (!cancelled) {
          setDashboardScoreSeries([]);
        }
      }
    };
    loadScoreSeries();
    return () => {
      cancelled = true;
    };
  }, [days]);

  // 合併 live data 與 API data
  const scores = liveScores.eye !== 0.5 || liveScores.ear !== 0.5
    ? liveScores
    : sensesData?.scores || liveScores;

  const advice = liveAdvice || sensesData?.recommendation;
  const maturitySummary = featureCoverageData?.maturity_counts ?? null;
  const runtimeStatusPending = runtimeStatusLoading && !runtimeStatus && !runtimeStatusError;
  const hasDashboardSnapshotData = Boolean(
    lastUpdate
    || sensesData
    || runtimeStatus
    || confidenceData
    || featureCoverageData
  );
  const dashboardTransportMode: "live" | "syncing" | "snapshot" | "offline" = wsConnected
    ? "live"
    : (runtimeStatusPending && !hasDashboardSnapshotData)
      ? "syncing"
      : hasDashboardSnapshotData
        ? "snapshot"
        : "offline";
  const dashboardTransportLabel = dashboardTransportMode === "live"
    ? "即時連線"
    : dashboardTransportMode === "syncing"
      ? "同步中"
      : dashboardTransportMode === "snapshot"
        ? "快照模式"
        : "離線";
  const dashboardTransportTone = dashboardTransportMode === "live"
    ? "text-green-400"
    : dashboardTransportMode === "syncing"
      ? "text-amber-300"
      : dashboardTransportMode === "snapshot"
        ? "text-sky-300"
        : "text-orange-400";
  const dashboardTransportDotTone = dashboardTransportMode === "live"
    ? "bg-green-400"
    : dashboardTransportMode === "syncing"
      ? "bg-amber-300"
      : dashboardTransportMode === "snapshot"
        ? "bg-sky-300"
        : "bg-orange-400";
  const executionSummary = runtimeStatus?.execution ?? null;
  const accountSummary = runtimeStatus?.account ?? null;
  const executionReconciliation = runtimeStatus?.execution_reconciliation ?? null;
  const executionSurfaceContract = runtimeStatus?.execution_surface_contract ?? null;
  const executionOperationsSurface = executionSurfaceContract?.operations_surface ?? null;
  const executionDiagnosticsSurface = executionSurfaceContract?.diagnostics_surface ?? null;
  const liveRuntimeTruth = executionSummary?.live_runtime_truth ?? executionSurfaceContract?.live_runtime_truth ?? null;
  const recentCanonicalDrift = runtimeStatus?.execution?.recent_canonical_drift ?? executionSurfaceContract?.recent_canonical_drift ?? runtimeStatus?.recent_canonical_drift ?? null;
  const liveRecentPathologyApplied = Boolean(
    liveRuntimeTruth?.decision_quality_recent_pathology_applied ?? confidenceData?.decision_quality_recent_pathology_applied
  );
  const liveRecentPathologyReason =
    liveRuntimeTruth?.decision_quality_recent_pathology_reason
    ?? confidenceData?.decision_quality_recent_pathology_reason
    ?? null;
  const liveRecentPathologyWindow =
    liveRuntimeTruth?.decision_quality_recent_pathology_window
    ?? confidenceData?.decision_quality_recent_pathology_window
    ?? null;
  const liveRecentPathologyAlerts =
    liveRuntimeTruth?.decision_quality_recent_pathology_alerts
    ?? confidenceData?.decision_quality_recent_pathology_alerts
    ?? [];
  const liveRecentPathologySummary =
    liveRuntimeTruth?.decision_quality_recent_pathology_summary
    ?? confidenceData?.decision_quality_recent_pathology_summary
    ?? null;
  const liveScopePathologySummary =
    liveRuntimeTruth?.decision_quality_scope_pathology_summary
    ?? null;
  const deploymentBlockerDetails = confidenceData?.deployment_blocker_details ?? null;
  const breakerRecentWindow = deploymentBlockerDetails?.recent_window ?? null;
  const breakerRelease = deploymentBlockerDetails?.release_condition ?? null;
  const circuitBreakerActive = confidenceData?.deployment_blocker === "circuit_breaker_active";
  const breakerWindow = typeof breakerRelease?.recent_window === "number"
    ? breakerRelease.recent_window
    : (typeof breakerRecentWindow?.window_size === "number" ? breakerRecentWindow.window_size : null);
  const breakerWins = typeof breakerRelease?.current_recent_window_wins === "number"
    ? breakerRelease.current_recent_window_wins
    : (typeof breakerRecentWindow?.wins === "number" ? breakerRecentWindow.wins : null);
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
  const liveRuntimeSupportAlignmentTone = liveRuntimeTruth?.support_alignment_status === "runtime_ahead_of_calibration"
    ? "text-amber-200"
    : liveRuntimeTruth?.support_alignment_status === "aligned"
      ? "text-emerald-200"
      : "text-slate-300";
  const metadataSmoke = runtimeStatus?.execution_metadata_smoke ?? null;
  const dashboardCurrentLiveBlocker = liveRuntimeTruth?.deployment_blocker || null;
  const dashboardPrimaryRuntimeMessage = liveRuntimeTruth?.deployment_blocker_reason
    || liveRuntimeTruth?.deployment_blocker
    || liveRuntimeTruth?.execution_guardrail_reason
    || executionSurfaceContract?.operator_message
    || null;
  const dashboardCurrentLiveBlockerLabel = runtimeStatusPending
    ? "同步中"
    : humanizeCurrentLiveBlockerLabel(dashboardCurrentLiveBlocker || "unavailable");
  const dashboardPrimaryRuntimeMessageLabel = runtimeStatusPending
    ? "正在同步 /api/status"
    : humanizeExecutionReason(
      dashboardPrimaryRuntimeMessage || (runtimeStatusError ? `無法取得 /api/status：${runtimeStatusError}` : "目前沒有額外 blocker 摘要")
    );
  const dashboardVenueBlockers = Array.isArray(executionSurfaceContract?.live_ready_blockers)
    ? executionSurfaceContract.live_ready_blockers
    : [];
  const dashboardVenueBlockersLabel = runtimeStatusPending
    ? "同步中"
    : (dashboardVenueBlockers.length > 0 ? dashboardVenueBlockers.map((item) => humanizeExecutionReason(item)).join(" · ") : "none");
  const dashboardSupportRouteVerdictLabel = runtimeStatusPending
    ? "同步中"
    : (liveRuntimeTruth?.support_route_verdict || "—");
  const dashboardSupportGovernanceRouteLabel = runtimeStatusPending
    ? "同步中"
    : (liveRuntimeTruth?.support_governance_route || "—");
  const dashboardSupportRowsLabel = runtimeStatusPending
    ? "同步中"
    : (liveRuntimeTruth?.support_rows_text || "—");
  const dashboardSupportGapLabel = runtimeStatusPending
    ? "同步中"
    : (typeof liveRuntimeTruth?.current_live_structure_bucket_gap_to_minimum === "number"
      ? liveRuntimeTruth.current_live_structure_bucket_gap_to_minimum.toFixed(0)
      : (typeof liveRuntimeTruth?.support_progress?.gap_to_minimum === "number"
        ? liveRuntimeTruth.support_progress.gap_to_minimum.toFixed(0)
        : "—"));
  const adviceCardExecutionActionState: "syncing" | "blocked" | "ready" = runtimeStatusPending || !liveRuntimeTruth
    ? "syncing"
    : (dashboardCurrentLiveBlocker ? "blocked" : "ready");
  const adviceCardExecutionBlockerReason = runtimeStatusPending
    ? "正在同步 /api/status；Dashboard 建議卡暫不提供快捷下單，避免 current live blocker truth 尚未到位前出現誤導 CTA。"
    : dashboardPrimaryRuntimeMessageLabel;
  const venueChecks = Array.isArray(metadataSmoke?.venues) ? metadataSmoke.venues : [];
  const metadataSmokeFreshness = metadataSmoke?.freshness ?? null;
  const metadataSmokeGovernance = metadataSmoke?.governance ?? null;
  const metadataSmokeAutoRefresh = metadataSmokeGovernance?.auto_refresh ?? null;
  const metadataSmokeBackgroundMonitor = metadataSmokeGovernance?.background_monitor ?? null;
  const metadataSmokeExternalMonitor = metadataSmokeGovernance?.external_monitor ?? null;
  const externalMonitorInstallContract = metadataSmokeExternalMonitor?.install_contract ?? null;
  const externalMonitorTickingState = metadataSmokeExternalMonitor?.ticking_state ?? null;
  const metadataSmokeFreshnessTone = getSmokeFreshnessTone(metadataSmokeFreshness?.status);
  const metadataSmokeFreshnessLabel = runtimeStatusPending
    ? "同步中"
    : (metadataSmokeFreshness?.label || metadataSmokeFreshness?.status || "UNAVAILABLE");
  const metadataSmokeGovernanceTone = getSmokeGovernanceTone(metadataSmokeGovernance?.status);
  const externalMonitorTickingTone = getExternalMonitorTickingTone(externalMonitorTickingState?.status);
  const rawContinuity = runtimeStatus?.raw_continuity ?? null;
  const featureContinuity = runtimeStatus?.feature_continuity ?? null;
  const executionModeLabel = runtimeStatusPending ? "同步中" : (executionSummary?.mode || accountSummary?.mode || "unknown");
  const executionVenueLabel = runtimeStatusPending ? "同步中" : (executionSummary?.venue || accountSummary?.venue || "—");
  const executionHealth = executionSummary?.health ?? accountSummary?.health ?? null;
  const balanceFree = typeof accountSummary?.balance?.free === "number" ? accountSummary.balance.free : null;
  const balanceTotal = typeof accountSummary?.balance?.total === "number" ? accountSummary.balance.total : null;
  const balanceCurrency = typeof accountSummary?.balance?.currency === "string" ? accountSummary.balance.currency : "USDT";
  const accountCredentialsConfigured = Boolean(accountSummary?.health?.credentials_configured ?? executionHealth?.credentials_configured);
  const accountBalanceUnavailableLabel = !accountCredentialsConfigured
    ? "public-only / metadata only"
    : "balance unavailable";
  const accountBalanceUnavailableReason = !accountCredentialsConfigured
    ? "private balance unavailable until exchange credentials are configured"
    : "balance unavailable in latest account snapshot";
  const accountBalanceSummaryValue = balanceFree !== null
    ? `free ${balanceFree.toFixed(2)} ${balanceCurrency}`
    : accountBalanceUnavailableLabel;
  const accountBalanceSummaryTotal = balanceTotal !== null
    ? `${balanceTotal.toFixed(2)} ${balanceCurrency}`
    : accountBalanceUnavailableReason;
  const positions = Array.isArray(accountSummary?.positions) ? accountSummary.positions : [];
  const openOrders = Array.isArray(accountSummary?.open_orders) ? accountSummary.open_orders : [];
  const openOrderCount = typeof accountSummary?.open_order_count === "number" ? accountSummary.open_order_count : openOrders.length;
  const positionCount = typeof accountSummary?.position_count === "number" ? accountSummary.position_count : positions.length;
  const accountRequestedSymbol = accountSummary?.requested_symbol ?? null;
  const accountNormalizedSymbol = accountSummary?.normalized_symbol ?? null;
  const accountCapturedAt = accountSummary?.captured_at ?? null;
  const accountDegraded = Boolean(accountSummary?.degraded);
  const accountOperatorMessage = accountSummary?.operator_message ?? null;
  const accountRecoveryHint = accountSummary?.recovery_hint ?? null;
  const accountHealthError = accountSummary?.health?.error ?? accountSummary?.error ?? null;
  const guardrails = executionSummary?.guardrails ?? null;
  const lastReject = guardrails?.last_reject ?? null;
  const lastRejectContext = lastReject?.context ?? null;
  const lastRejectRuleLines = formatGuardrailRules(lastRejectContext?.rules);
  const lastFailure = guardrails?.last_failure ?? null;
  const lastOrder = guardrails?.last_order ?? null;
  const reconciliationLifecycleAudit = executionReconciliation?.lifecycle_audit ?? null;
  const reconciliationRecoveryState = executionReconciliation?.recovery_state ?? null;
  const reconciliationLifecycleContract = executionReconciliation?.lifecycle_contract ?? null;
  const reconciliationCoverageLimited = isExecutionReconciliationLimitedEvidence(
    executionReconciliation?.status,
    reconciliationLifecycleAudit?.stage,
    reconciliationLifecycleContract?.artifact_coverage,
  );
  const reconciliationTone = getReconciliationTone(reconciliationCoverageLimited ? "warning" : executionReconciliation?.status);
  const reconciliationIssues = Array.isArray(executionReconciliation?.issues) ? executionReconciliation.issues : [];
  const reconciliationLatestTrade = executionReconciliation?.trade_history_alignment?.latest_trade ?? null;
  const reconciliationMatchedOpenOrder = executionReconciliation?.open_order_alignment?.matched_open_order ?? null;
  const reconciliationFreshness = executionReconciliation?.account_snapshot?.freshness ?? null;
  const reconciliationArtifactChecklist = Array.isArray(reconciliationLifecycleContract?.artifact_checklist)
    ? reconciliationLifecycleContract.artifact_checklist
    : [];
  const reconciliationVenueLanes = Array.isArray(reconciliationLifecycleContract?.venue_lanes)
    ? reconciliationLifecycleContract.venue_lanes
    : [];
  const reconciliationTimeline = executionReconciliation?.lifecycle_timeline ?? null;
  const reconciliationTimelineEvents = Array.isArray(reconciliationTimeline?.events) ? reconciliationTimeline.events : [];
  const tradeFeedbackTone = tradeFeedback?.tone === "success"
    ? "border-emerald-700/40 bg-emerald-950/20 text-emerald-200"
    : tradeFeedback?.tone === "error"
      ? "border-red-700/40 bg-red-950/20 text-red-200"
      : "border-sky-700/40 bg-sky-950/20 text-sky-200";
  const executionTone = executionSummary?.kill_switch || guardrails?.daily_loss_halt || guardrails?.failure_halt
    ? "border-red-700/40 bg-red-950/30 text-red-200"
    : executionModeLabel === "live"
      ? "border-emerald-700/40 bg-emerald-950/30 text-emerald-200"
      : executionModeLabel === "live_canary"
        ? "border-amber-700/40 bg-amber-950/30 text-amber-200"
        : "border-slate-700/40 bg-slate-950/30 text-slate-300";
  const continuityTone = rawContinuity?.status === "clean"
    ? "border-emerald-700/40 bg-emerald-950/30 text-emerald-200"
    : rawContinuity?.status === "repaired"
      ? "border-amber-700/40 bg-amber-950/30 text-amber-200"
      : rawContinuity?.status === "error"
        ? "border-red-700/40 bg-red-950/30 text-red-200"
        : "border-slate-700/40 bg-slate-950/30 text-slate-300";
  const reconciliationStatusLabel = runtimeStatusPending
    ? "同步中"
    : humanizeExecutionReconciliationStatusLabel(
      executionReconciliation?.status,
      reconciliationLifecycleAudit?.stage,
      reconciliationLifecycleContract?.artifact_coverage,
    );
  const reconciliationSummaryLabel = runtimeStatusPending
    ? "正在向 /api/status 取得 reconciliation / recovery 摘要。"
    : reconciliationCoverageLimited
      ? `${executionReconciliation?.summary || "尚未收到 reconciliation 摘要。"} · 尚未有 runtime order，因此目前只能確認「沒有發現明顯對帳落差」，不可視為完整實單驗證。`
      : (executionReconciliation?.summary || "尚未收到 reconciliation 摘要。");
  const continuityLabel = runtimeStatusPending
    ? "同步 /api/status 中"
    : rawContinuity?.status === "clean"
      ? "raw 連續性正常"
      : rawContinuity?.status === "repaired"
        ? "啟動時已自動回填資料斷點"
        : rawContinuity?.status === "error"
          ? "啟動檢查失敗"
          : "尚未收到啟動檢查結果";
  const dashboardExecutionStatusValue = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "Ready" : "Blocked");

  const handleTrade = useCallback(async (side: string) => {
    if (side === "hold") return;
    const label = side === "buy" ? "買入" : side === "reduce" ? "減碼" : side.toUpperCase();
    setTradeFeedback({
      tone: "pending",
      title: `${label} 指令送出中`,
      detail: "正在提交 /api/trade，完成後會主動刷新 execution status。",
      timestamp: new Date().toLocaleString("zh-TW"),
    });
    try {
      const resp = await fetchApi("/api/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ side, symbol: "BTCUSDT", qty: 0.001 }),
      });
      await refreshRuntimeStatus();
      const data = resp as any;
      const mode = data?.order?.mode || (data?.dry_run ? "dry_run" : "live");
      const qty = typeof data?.order?.qty === "number" ? data.order.qty : null;
      const venue = data?.venue || "unknown";
      const normalizedQty = typeof data?.normalization?.normalized?.qty === "number" ? data.normalization.normalized.qty : qty;
      const normalizedPrice = typeof data?.normalization?.normalized?.price === "number" ? data.normalization.normalized.price : null;
      const stepSize = data?.normalization?.contract?.step_size;
      const tickSize = data?.normalization?.contract?.tick_size;
      const contractSummary = [
        stepSize != null ? `step ${formatGuardrailValue(stepSize)}` : null,
        tickSize != null ? `tick ${formatGuardrailValue(tickSize)}` : null,
      ].filter(Boolean).join(" · ");
      setTradeFeedback({
        tone: "success",
        title: `${label} 指令已提交`,
        detail: `模式 ${mode} · 場館 ${venue}${normalizedQty != null ? ` · normalized qty ${formatGuardrailValue(normalizedQty)}` : ""}${normalizedPrice != null ? ` · normalized price ${formatGuardrailValue(normalizedPrice)}` : ""}${contractSummary ? ` · contract ${contractSummary}` : ""}。已主動刷新 /api/status。`,
        timestamp: new Date().toLocaleString("zh-TW"),
      });
    } catch (e: any) {
      await refreshRuntimeStatus();
      const detail = typeof e?.message === "string" ? e.message : "未知錯誤";
      setTradeFeedback({
        tone: "error",
        title: `${label} 指令被拒絕或失敗`,
        detail: `${detail}。已主動刷新 /api/status，請檢查下方 Guardrail context 面板。`,
        timestamp: new Date().toLocaleString("zh-TW"),
      });
    }
  }, [refreshRuntimeStatus]);

  // 判斷資料新鮮度
  const isDataStale = !lastUpdate && !wsConnected && !sensesData;

  return (
    <div className="app-page-shell">
      {/* Top bar */}
      <div className="app-page-header">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-bold text-slate-300">🐰 Poly-Trader</span>
            {/* 狀態指示器 */}
            <span className={`flex items-center gap-1 ${dashboardTransportTone}`}>
              <span className={`w-2 h-2 rounded-full ${dashboardTransportDotTone}`} />
              {dashboardTransportLabel}
            </span>
            {lastUpdate && (
              <span className="text-slate-500">更新: {lastUpdate}</span>
            )}
            {/* 模型準確率 — show top IC features dynamically */}
            {modelStats?.ic_values && Object.keys(modelStats.ic_values).length > 0 && (
              <span className="flex items-center gap-1 text-slate-400">
                📊 樣本:{modelStats.sample_count}
                {(() => {
                  const topIcs = Object.entries(modelStats.ic_values)
                    .filter(([k, v]) => typeof v === "number")
                    .sort((a, b) => Math.abs(b[1] as number) - Math.abs(a[1] as number))
                    .slice(0, 3);
                  return topIcs.map(([name, val]) => (
                    <span key={name} className="text-xs opacity-70">
                      | {name.replace("4h_", "4H ")} IC: {(val as number) > 0 ? '+' : ''}{(val as number).toFixed(3)}
                    </span>
                  ));
                })()}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-slate-500">
            {apiError && <span className="text-red-400">API 連線異常</span>}
          </div>
        </div>
      </div>

      <ExecutionWorkspaceSummary
        title="💼 Execution 摘要"
        subtitle="Dashboard 只保留 4 張 Bot 營運摘要卡；若要查看 current live blocker 詳情、metadata 明細與 recovery 脈絡，請前往「執行狀態」。"
        className={executionTone}
        actions={(
          <>
            <a
              href={executionOperationsSurface?.route || "/execution"}
              className="app-button-secondary"
            >
              前往 Bot 營運 →
            </a>
            <a
              href="/execution/status"
              className="app-button-secondary"
            >
              前往執行狀態 →
            </a>
          </>
        )}
        footer={(
          <>
            <LivePathologySummaryCard
              summary={liveScopePathologySummary}
              className="mt-1"
              title="🧬 Live lane / spillover 對照"
              compact
              supportAlignmentStatus={liveRuntimeTruth?.support_alignment_status ?? null}
              supportAlignmentSummary={liveRuntimeTruth?.support_alignment_summary ?? null}
              runtimeExactSupportRows={liveRuntimeTruth?.runtime_exact_support_rows ?? null}
              calibrationExactLaneRows={liveRuntimeTruth?.calibration_exact_lane_rows ?? null}
              supportRouteVerdict={liveRuntimeTruth?.support_route_verdict ?? null}
              supportGovernanceRoute={liveRuntimeTruth?.support_governance_route ?? null}
            />
            <RecentCanonicalDriftCard
              summary={recentCanonicalDrift}
              pending={runtimeStatusPending && !recentCanonicalDrift}
              className="mt-3"
              title="📉 Recent canonical drift"
            />
          </>
        )}
      >
        <ExecutionWorkspaceMetric
          label="部署狀態"
          value={dashboardExecutionStatusValue}
          detail={(
            <>
              <div>{executionSummary?.mode?.toUpperCase() || executionModeLabel.toUpperCase()} · {executionVenueLabel}</div>
              <div>current live blocker {dashboardCurrentLiveBlockerLabel} · {dashboardPrimaryRuntimeMessageLabel}</div>
              <div className="opacity-70">current bucket {dashboardSupportRowsLabel} · gap {dashboardSupportGapLabel} · support route {dashboardSupportRouteVerdictLabel} · governance route {dashboardSupportGovernanceRouteLabel}</div>
              <div className="opacity-70">venue blockers {dashboardVenueBlockersLabel}</div>
            </>
          )}
          extra={<VenueReadinessSummary venues={venueChecks} className="mt-2" compact />}
        />
        <ExecutionWorkspaceMetric
          label="資金 / 曝險"
          value={accountBalanceSummaryValue}
          detail={<div>total {accountBalanceSummaryTotal} · 倉位 {positionCount} · 掛單 {openOrderCount}</div>}
        />
        <ExecutionWorkspaceMetric
          label="Metadata freshness"
          value={metadataSmokeFreshnessLabel}
          detail={runtimeStatusPending ? "正在向 /api/status 取得 metadata smoke。" : (metadataSmoke?.generated_at ? new Date(metadataSmoke.generated_at).toLocaleString("zh-TW") : "尚未產生 smoke artifact")}
        />
        <ExecutionWorkspaceMetric
          label="Reconciliation / recovery"
          value={reconciliationStatusLabel}
          detail={reconciliationSummaryLabel}
        />
      </ExecutionWorkspaceSummary>

      <div className={`rounded-xl border px-4 py-3 text-xs ${continuityTone}`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="font-semibold">🩹 啟動檢查 / continuity</div>
          <div className="text-[11px] opacity-80">
            {runtimeStatusPending
              ? "正在向 /api/status 取得啟動檢查結果"
              : (rawContinuity?.checked_at ? `檢查時間 ${new Date(rawContinuity.checked_at).toLocaleString("zh-TW")}` : "等待啟動檢查結果")}
          </div>
        </div>
        <div className="mt-1 leading-5">{continuityLabel}</div>
        {rawContinuity?.continuity_repair && (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] opacity-90">
            <span>總補回 {rawContinuity.continuity_repair.inserted_total ?? 0}</span>
            <span>4h {rawContinuity.continuity_repair.coarse_inserted ?? 0}</span>
            <span>1h {rawContinuity.continuity_repair.fine_inserted ?? 0}</span>
            <span>bridge {rawContinuity.continuity_repair.bridge_inserted ?? 0}</span>
            {rawContinuity.continuity_repair.used_bridge && <span className="text-amber-300">⚠️ 依賴 bridge fallback</span>}
          </div>
        )}
        {featureContinuity?.continuity_repair && (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] opacity-90">
            <span>feature 狀態 {featureContinuity.status ?? "unknown"}</span>
            <span>補回 {featureContinuity.continuity_repair.inserted_total ?? 0}</span>
            <span>remaining missing {featureContinuity.continuity_repair.remaining_missing ?? 0}</span>
          </div>
        )}
        {rawContinuity?.error && (
          <div className="mt-2 text-[11px] text-red-200">錯誤：{rawContinuity.error}</div>
        )}
        {featureContinuity?.error && (
          <div className="mt-2 text-[11px] text-red-200">Feature 錯誤：{featureContinuity.error}</div>
        )}
      </div>

      {/* Row 1: Radar + Advice */}
      <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-4 items-stretch">
        {/* Left: Radar */}
        <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-5 flex h-full flex-col items-center">
          <div className="flex items-center justify-between w-full mb-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-300">🎯 多特徵雷達圖</h2>
              <div className="text-xs text-slate-500 mt-1">已改用市場語義短標籤，避免舊人格化命名與文字重疊。</div>
              {maturitySummary && (
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] font-semibold">
                  <span className="rounded-full border border-emerald-700/40 bg-emerald-950/40 px-2 py-0.5 text-emerald-300">
                    核心 {maturitySummary.core}
                  </span>
                  <span className="rounded-full border border-sky-700/40 bg-sky-950/40 px-2 py-0.5 text-sky-300">
                    研究 {maturitySummary.research}
                  </span>
                  <span className="rounded-full border border-amber-700/40 bg-amber-950/30 px-2 py-0.5 text-amber-300">
                    阻塞 {maturitySummary.blocked}
                  </span>
                  <span className="text-slate-500">
                    雷達保留研究/阻塞 overlay 供觀察；主決策請搭配下方建議卡與 FeatureChart 成熟度資訊。
                  </span>
                </div>
              )}
            </div>
            <span className="text-xs text-slate-500 cursor-pointer hover:text-slate-300"
              onClick={() => setSelectedSense(null)}>
              點擊特徵看走勢
            </span>
          </div>
          {isDataStale ? (
            <div className="py-12 text-center text-slate-500">
              <div className="animate-pulse mb-2">🔄 等待資料...</div>
              <div className="text-xs text-slate-600">確認後端有啟動</div>
              <button onClick={refreshSenses} className="mt-3 px-3 py-1 text-xs bg-blue-600 rounded hover:bg-blue-500">
                手動刷新
              </button>
            </div>
          ) : (
            <RadarChart scores={scores} size={380} onSenseClick={setSelectedSense} />
          )}
        </div>

        {/* Right: Advice Card */}
        <div className="h-full">
          {advice ? (
            <div className="h-full">
              <AdviceCard
                score={advice.score}
                summary={advice.summary}
                descriptions={advice.descriptions}
                action={advice.action}
                timestamp={advice.timestamp || lastUpdate}
                onTrade={handleTrade}
                executionActionState={adviceCardExecutionActionState}
                executionBlockerLabel={dashboardCurrentLiveBlockerLabel}
                executionBlockerReason={adviceCardExecutionBlockerReason}
                maturitySummary={maturitySummary || undefined}
              />
            </div>
          ) : apiError ? (
            <div className="bg-red-900/20 border border-red-700/50 rounded-xl p-8 text-center h-full min-h-[420px] flex flex-col items-center justify-center">
              <div className="text-red-400 text-lg mb-2">⚠️ 無法連線</div>
              <p className="text-slate-400 text-sm">{apiError}</p>
              <button onClick={refreshSenses} className="mt-4 px-4 py-2 text-sm bg-red-600 rounded hover:bg-red-500">
                重試
              </button>
            </div>
          ) : (
            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-8 flex h-full min-h-[420px] items-center justify-center">
              <div className="text-slate-500 animate-pulse text-center">
                <div className="text-2xl mb-2">🤔</div>
                <div>分析中...</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Row 1.5: Confidence Indicator */}
      {confidenceData && !confidenceData.error && (
        <ConfidenceIndicator
          confidence={confidenceData.confidence}
          signal={confidenceData.signal}
          confidenceLevel={confidenceData.confidence_level}
          shouldTrade={confidenceData.should_trade}
          regimeGate={confidenceData.regime_gate}
          entryQuality={confidenceData.entry_quality}
          entryQualityLabel={confidenceData.entry_quality_label}
          allowedLayers={confidenceData.allowed_layers}
          decisionQualityScore={confidenceData.decision_quality_score}
          decisionQualityLabel={confidenceData.decision_quality_label}
          expectedWinRate={confidenceData.expected_win_rate}
          expectedPyramidQuality={confidenceData.expected_pyramid_quality}
          expectedDrawdownPenalty={confidenceData.expected_drawdown_penalty}
          expectedTimeUnderwater={confidenceData.expected_time_underwater}
          decisionQualitySampleSize={confidenceData.decision_quality_sample_size}
          decisionQualityHorizonMinutes={confidenceData.decision_quality_horizon_minutes}
          decisionProfileVersion={confidenceData.decision_profile_version}
          currentLiveStructureBucket={confidenceData.current_live_structure_bucket ?? confidenceData.structure_bucket}
          deploymentBlocker={confidenceData.deployment_blocker}
          deploymentBlockerReason={confidenceData.deployment_blocker_reason ?? confidenceData.allowed_layers_reason}
          deploymentBlockerDetails={confidenceData.deployment_blocker_details}
          supportProgress={confidenceData.support_progress}
          minimumSupportRows={confidenceData.minimum_support_rows}
          currentLiveStructureBucketGapToMinimum={confidenceData.current_live_structure_bucket_gap_to_minimum}
          floorCrossVerdict={confidenceData.floor_cross_verdict}
          bestSingleComponent={confidenceData.best_single_component}
          bestSingleComponentRequiredScoreDelta={confidenceData.best_single_component_required_score_delta}
          componentExperimentVerdict={confidenceData.component_experiment_verdict}
          q15ExactSupportedComponentPatchApplied={confidenceData.q15_exact_supported_component_patch_applied}
          timestamp={confidenceData.timestamp}
        />
      )}

      {/* ─── 4H Structure Panel ─── */}
      {sensesData?.raw && Object.keys(sensesData.raw).length > 0 && (() => {
        const raw = sensesData.raw as Record<string, number>;
        const bias50 = raw['4h_bias50'] ?? null;
        const bias20 = raw['4h_bias20'] ?? null;
        const rsi14 = raw['4h_rsi14'] ?? null;
        const macd = raw['4h_macd_hist'] ?? null;
        const swingDist = raw['4h_dist_sl'] ?? null;
        const maOrder = raw['4h_ma_order'] ?? 0;

        // 牛市/熊市判斷
        const regime = bias50 !== null ? (bias50 >= 0 ? 'bull' : 'bear') : 'unknown';
        const regimeLabel = regime === 'bull' ? '🟢 牛市格局' : '🔴 熊市格局';
        const regimeColor = regime === 'bull' ? 'text-green-400' : 'text-red-400';

        // 判斷: 靠近支撐? 靠近壓力?
        let zone = '觀望';
        let zoneColor = 'text-slate-400';
        if (bias50 !== null) {
          if (bias50 <= -5) { zone = '極端超賣'; zoneColor = 'text-green-400'; }
          else if (bias50 <= -3) { zone = '超賣區'; zoneColor = 'text-green-400'; }
          else if (bias50 <= -1) { zone = '回調區'; zoneColor = 'text-yellow-400'; }
          else if (bias50 >= 5) { zone = '極端超買'; zoneColor = 'text-red-400'; }
          else if (bias50 >= 3) { zone = '超買區'; zoneColor = 'text-red-400'; }
          else if (bias50 >= 0) { zone = '正常偏強'; zoneColor = 'text-slate-300'; }
          else { zone = '正常偏弱'; zoneColor = 'text-slate-300'; }
        }

        // Context-only structural note. Canonical trade action must come from the
        // live decision-quality contract (regime_gate + entry_quality + allowed_layers).
        let contextAction = '';
        if (regime === 'bull' && bias50! <= -3) contextAction = '背景偏多，價格接近支撐。';
        else if (regime === 'bull' && bias50! <= -1) contextAction = '背景偏多，正在回調區。';
        else if (regime === 'bull' && bias50! >= 5) contextAction = '背景偏熱，已進入超買帶。';
        else if (regime === 'bull') contextAction = '背景偏多，但仍需等 live gate / quality 確認。';
        else contextAction = '背景偏保守，先觀察 4H 結構是否改善。';

        const canonicalGate = confidenceData?.regime_gate || '—';
        const canonicalEntryQuality = typeof confidenceData?.entry_quality === 'number'
          ? confidenceData.entry_quality.toFixed(2)
          : '—';
        const canonicalEntryLabel = confidenceData?.entry_quality_label || '—';
        const canonicalLayers = typeof confidenceData?.allowed_layers === 'number'
          ? `${confidenceData.allowed_layers.toFixed(0)} / 3`
          : '—';
        const canonicalDecisionText = confidenceData
          ? `主決策：4H Gate ${canonicalGate} · Entry ${canonicalEntryQuality} (${canonicalEntryLabel}) · Layers ${canonicalLayers}`
          : '主決策：等待 live decision-quality contract 載入';

        return (
        <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-5">
          <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
            <div>
              <h2 className="text-sm font-semibold text-slate-300">📐 4H 結構線儀表板</h2>
              <div className="mt-1 text-[11px] text-slate-500">主決策以 live decision-quality contract 為準；以下 4H 指標僅作背景解讀。</div>
            </div>
            <span className={`text-xs font-bold ${regimeColor} px-2 py-0.5 rounded bg-slate-800`}>{regimeLabel}</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
            <div className="bg-slate-800/50 rounded-lg p-3">
              <div className="text-xs text-slate-500 mb-1">偏離 MA50</div>
              <div className={`text-xl font-bold ${bias50! <= -3 ? 'text-green-400' : bias50! >= 3 ? 'text-red-400' : 'text-slate-200'}`}>
                {bias50 !== null ? `${bias50 > 0 ? '+' : ''}${bias50.toFixed(2)}%` : '—'}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3">
              <div className="text-xs text-slate-500 mb-1">距離支撐線</div>
              <div className={`text-xl font-bold ${swingDist! < 3 && swingDist! >= 0 ? 'text-green-400' : 'text-slate-200'}`}>
                {swingDist !== null ? `${swingDist > 0 ? '+' : ''}${swingDist.toFixed(2)}%` : '—'}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3">
              <div className="text-xs text-slate-500 mb-1">4H RSI</div>
              <div className={`text-xl font-bold ${rsi14! < 30 ? 'text-green-400' : rsi14! > 70 ? 'text-red-400' : 'text-slate-200'}`}>
                {rsi14 !== null ? rsi14.toFixed(1) : '—'}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3">
              <div className="text-xs text-slate-500 mb-1">位置</div>
              <div className={`text-xl font-bold ${zoneColor}`}>{zone}</div>
            </div>
          </div>

          {/* Secondary metrics */}
          <div className="grid grid-cols-3 gap-3 text-xs text-slate-400 mb-3">
            <div>偏離 MA20: <span className="text-slate-200">{bias20 !== null ? `${bias20 > 0 ? '+' : ''}${bias20.toFixed(2)}%` : '—'}</span></div>
            <div>MACD-H: <span className={macd! > 0 ? 'text-green-400' : 'text-red-400'}>{macd !== null ? macd.toFixed(1) : '—'}</span></div>
            <div>MA排列: <span className={maOrder > 0 ? 'text-green-400' : maOrder < 0 ? 'text-red-400' : 'text-slate-400'}>
              {maOrder > 0.5 ? '📈 多頭' : maOrder < -0.5 ? '📉 空頭' : '📊 盤整'}
            </span></div>
          </div>

          {/* Canonical decision contract first; raw 4H metrics are context only. */}
          <div className="space-y-2">
            <div className="bg-cyan-950/20 rounded-lg px-4 py-3 text-sm text-cyan-100 border border-cyan-700/30">
              <div className="font-semibold">{canonicalDecisionText}</div>
              <div className="mt-1 text-xs text-cyan-200/80">
                若 4H raw 結構與 canonical gate 不一致，應以 decision-quality contract 為主，而不是手寫 bias 規則。
              </div>
            </div>
            <div className="bg-slate-800/30 rounded-lg px-4 py-2 text-sm text-slate-300 border border-slate-700/30">
              <div className="font-medium text-slate-200">結構背景</div>
              <div className="mt-1">{contextAction}</div>
            </div>
          </div>
        </div>
        );
      })()}

      {/* Row 2: TradingView-style BTC/USDT + composite score */}
      <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-slate-300">📈 BTC/USDT × 綜合分數走勢</div>
            <div className="mt-1 text-xs text-slate-500">主圖只保留價格與綜合分數，讓使用者用 TradingView 風格直接對照市場與策略強弱。</div>
          </div>
          <div className="flex items-center gap-2">
            {[
              { label: "4H", iv: "4h", d: 14 },
              { label: "1D", iv: "1d", d: 90 },
            ].map((opt) => (
              <button
                key={opt.iv}
                onClick={() => { setInterval(opt.iv); setDays(opt.d); }}
                className={`px-3 py-1 text-xs rounded-lg transition ${interval === opt.iv ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}
              >
                {opt.label}
              </button>
            ))}
            <button
              onClick={() => setShowFeatureHistory((prev) => !prev)}
              className={`px-3 py-1 text-xs rounded-lg transition ${showFeatureHistory ? "bg-cyan-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}
            >
              {showFeatureHistory ? "隱藏多特徵" : "顯示多特徵"}
            </button>
          </div>
        </div>
        <CandlestickChart
          symbol="BTCUSDT"
          interval={interval}
          days={days}
          scoreSeries={dashboardScoreSeries}
          title="BTC/USDT（綜合分數指標）"
        />
      </div>

      {showFeatureHistory && (
        <FeatureChart selectedFeature={selectedSense} days={days} onClear={() => setSelectedSense(null)} />
      )}
    </div>
  );
}
