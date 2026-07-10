import { useState } from "react";
import { fetchApi, useApi } from "../hooks/useApi";
import { ExecutionHero, ExecutionMetricCard, ExecutionPill, ExecutionSectionCard } from "../components/execution/ExecutionSurface";
import VenueReadinessSummary from "../components/VenueReadinessSummary";
import {
  humanizeExecutionOperatorLabel,
  humanizeExecutionReason,
  humanizeExecutionReconciliationStatusLabel,
  humanizeRuntimeClosureStateLabel,
  humanizeRuntimeDetailText,
  humanizeStructureBucketLabel,
  humanizeCurrentLiveSupportScopeLabel,
  humanizeSupportGovernanceRouteLabel,
  humanizeSupportProgressDeltaLabel,
  humanizeSupportProgressReferenceLabel,
  humanizeSupportProgressStatusLabel,
  humanizeSupportRouteLabel,
  isExecutionReconciliationLimitedEvidence,
} from "../utils/runtimeCopy";

const EXECUTION_MODE_LABELS: Record<string, string> = {
  paper: "模擬倉",
  paper_shadow: "影子觀察",
  dry_run: "模擬委託",
  live: "實盤",
};

const EXECUTION_VENUE_LABELS: Record<string, string> = {
  okx: "OKX",
  unsupported_legacy_venue: "舊場館（已停用）",
  unknown: "未提供",
};

type SurfaceInfo = {
  route?: string;
  label?: string;
  role?: string;
  status?: string;
  message?: string;
  upgrade_prerequisite?: string;
};

type SleeveRoutingItem = {
  key?: string;
  label?: string;
  why?: string;
};

type SleeveRoutingState = {
  current_regime?: string | null;
  current_regime_gate?: string | null;
  current_structure_bucket?: string | null;
  active_ratio_text?: string | null;
  summary?: string | null;
  active_sleeves?: SleeveRoutingItem[] | null;
  inactive_sleeves?: SleeveRoutingItem[] | null;
};

type RangeChopPlaybook = {
  key?: string | null;
  status?: string | null;
  summary?: string | null;
  market_problem?: string | null;
  shadow_available?: boolean | null;
  shadow_mode?: string | null;
  risk_reduction_allowed?: boolean | null;
  buy_add_requires_current_live_gate?: boolean | null;
  risk_on_order_enabled?: boolean | null;
  order_submission_enabled?: boolean | null;
  operator_message?: string | null;
  next_operator_action?: string | null;
  support_summary?: string | null;
  support_context?: {
    current_rows?: number | null;
    minimum_rows?: number | null;
    gap_to_minimum?: number | null;
    support_progress_status?: string | null;
    stagnant_run_count?: number | null;
    stalled_support_accumulation?: boolean | null;
  } | null;
  allowed_operator_actions?: string[] | null;
  blocked_operator_actions?: string[] | null;
  release_prerequisites?: string[] | null;
};

type ReadinessGate = {
  key?: string | null;
  label?: string | null;
  status?: string | null;
  raw_status?: string | null;
  passed?: boolean | null;
  shadow_ready?: boolean | null;
  current?: number | null;
  required?: number | null;
  gap?: number | null;
  candidate_decisions?: number | null;
  pending_outcomes?: number | null;
  resolved_outcomes?: number | null;
  awaiting_label_replay?: number | null;
  jsonl_backed?: boolean | null;
  next_reconcile_at?: string | null;
  pending_hours_remaining_min?: number | null;
  order_submission_enabled?: boolean | null;
  risk_on_order_enabled?: boolean | null;
  live_order_submitted?: boolean | null;
  release_ready?: boolean | null;
  release_condition?: Record<string, unknown> | null;
  release_evidence_lane?: {
    status?: string | null;
    release_ready?: boolean | null;
    blocked_by?: string[] | null;
    horizon_minutes?: number | null;
    recent_window?: number | null;
    current_recent_window_wins?: number | null;
    required_recent_window_wins?: number | null;
    wins_needed?: number | null;
    current_recent_window_win_rate?: number | null;
    current_streak?: number | null;
    streak_must_be_below?: number | null;
    next_validation_artifact?: string | null;
    verify_next?: string | null;
    order_submission_enabled?: boolean | null;
    risk_on_order_enabled?: boolean | null;
    live_order_submitted?: boolean | null;
    operator_message?: string | null;
  } | null;
  next_validation_artifact?: string | null;
  verify_next?: string | null;
  summary?: string | null;
  next_action?: string | null;
  blockers?: string[] | null;
  sub_gate_of?: string | null;
  sub_gates?: ReadinessGate[] | null;
  actionability?: string | null;
  paper_shadow_available?: boolean | null;
  paper_shadow_buy_candidate_ready?: boolean | null;
  live_buy_add_allowed?: boolean | null;
  live_exposure_allowed?: boolean | null;
  forecast_edge_bps?: number | null;
  required_edge_bps?: number | null;
  reference_edge_proxy_bps?: number | null;
};

type TimeToEvidence = {
  status?: string | null;
  summary?: string | null;
  current_rows?: number | null;
  minimum_support_rows?: number | null;
  gap_to_minimum?: number | null;
  delta_vs_previous?: number | null;
  previous_rows?: number | null;
  stagnant_run_count?: number | null;
  stalled_support_accumulation?: boolean | null;
  estimated_heartbeats_to_support?: number | null;
  heartbeat_interval_assumption_hours?: number | null;
  estimated_hours_at_hourly_heartbeat?: number | null;
  estimated_days_at_hourly_heartbeat?: number | null;
  alternative_solution_required?: boolean | null;
  operator_message?: string | null;
};

type AlternativeSolutionReview = {
  status?: string | null;
  trigger?: string | null;
  primary_alternative?: string | null;
  live_exposure_allowed?: boolean | null;
  order_submission_enabled?: boolean | null;
  allowed_today?: string[] | null;
  not_allowed?: string[] | null;
  next_review_trigger?: string | null;
  operator_message?: string | null;
};

type MilestoneProgression = {
  status?: string | null;
  current_milestone?: string | null;
  active_lane?: string | null;
  active_lane_label?: string | null;
  blocked_live_gate_key?: string | null;
  blocked_live_gate_label?: string | null;
  auto_adjustment_applied?: boolean | null;
  auto_adjustment_reason?: string | null;
  operator_message?: string | null;
  preferred_entrypoint?: Record<string, unknown> | null;
  fallback_entrypoint?: Record<string, unknown> | null;
  safe_entry_lanes?: Array<Record<string, unknown>> | null;
  live_runner_24h_shadow_gate?: ReadinessGate | null;
  milestones?: Array<Record<string, unknown>> | null;
};

type ExecutionReadiness = {
  status?: string | null;
  stage_label?: string | null;
  canary_ready?: boolean | null;
  live_ready?: boolean | null;
  risk_on_order_enabled?: boolean | null;
  order_submission_enabled?: boolean | null;
  blocking_gate_key?: string | null;
  blocking_gate_label?: string | null;
  operator_message?: string | null;
  gates?: ReadinessGate[] | null;
  live_runner_24h_shadow_gate?: ReadinessGate | null;
  what_can_do_now?: string[] | null;
  what_cannot_do_now?: string[] | null;
  time_to_evidence?: TimeToEvidence | null;
  alternative_solution_review?: AlternativeSolutionReview | null;
  milestone_progression?: MilestoneProgression | null;
  next_release_condition?: string | null;
};

type ShadowTradeLedgerEntry = {
  id?: string | null;
  signal_time?: string | null;
  candidate_model?: string | null;
  candidate_threshold?: string | null;
  confidence?: number | null;
  regime?: string | null;
  hypothetical_entry?: {
    symbol?: string | null;
    side?: string | null;
    entry_source?: string | null;
    order_submission_enabled?: boolean | null;
    operator_copy?: string | null;
  } | null;
  outcome_24h?: {
    status?: string | null;
    window_hours?: number | null;
    pnl_pct?: number | null;
    pyramid_win?: boolean | null;
  } | null;
  pyramid_win?: boolean | null;
  operator_note?: string | null;
};

type ShadowTradeLedger = {
  status?: string | null;
  mode?: string | null;
  order_submission_enabled?: boolean | null;
  schema?: string[] | null;
  entries?: ShadowTradeLedgerEntry[] | null;
  operator_message?: string | null;
};

type VenueDryRunProof = {
  artifact?: string | null;
  artifact_path?: string | null;
  generated_at?: string | null;
  status?: string | null;
  venue?: string | null;
  credential_present?: boolean | null;
  secrets_redacted?: boolean | null;
  runtime_ready?: boolean | null;
  runtime_ready_count?: number | null;
  venues_checked?: number | null;
  proof_state?: string | null;
  blockers?: string[] | null;
  operator_next_action?: string | null;
  verify_next?: string | null;
  order_preview?: Record<string, unknown> | null;
  ack_simulation?: Record<string, unknown> | null;
  cancel_simulation?: Record<string, unknown> | null;
  fill_simulation?: Record<string, unknown> | null;
  reconciliation_check?: Record<string, unknown> | null;
};

type CanaryGapAnswers = {
  canary_ready?: boolean | null;
  distance_to_canary?: string[] | null;
  drills_available_today?: string[] | null;
  blocked_gate_key?: string | null;
  blocking_gate?: string | null;
  blocked_gate_summary?: string | null;
  time_to_evidence?: TimeToEvidence | null;
  alternative_solution_review?: AlternativeSolutionReview | null;
  milestone_progression?: MilestoneProgression | null;
  live_runner_24h_shadow_gate?: ReadinessGate | null;
  first_canary_plan_if_all_gates_pass?: {
    exposure_pct_max?: number | null;
    pyramid_layer?: string | null;
    symbol?: string | null;
    mode?: string | null;
    order_type?: string | null;
    add_exposure_enabled?: boolean | null;
    required_shadow_evidence_gate?: string | null;
    stop_conditions?: string[] | null;
  } | null;
};

type LiveRuntimeTruth = {
  runtime_closure_state?: string | null;
  runtime_closure_summary?: string | null;
  regime_label?: string | null;
  regime_gate?: string | null;
  structure_bucket?: string | null;
  allowed_layers?: number | null;
  allowed_layers_raw?: number | null;
  allowed_layers_reason?: string | null;
  allowed_layers_raw_reason?: string | null;
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
      release_ready?: boolean | null;
      blocked_by?: string[] | null;
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
  execution_guardrail_reason?: string | null;
  support_alignment_status?: string | null;
  support_alignment_summary?: string | null;
  support_rows_text?: string | null;
  support_route_verdict?: string | null;
  support_governance_route?: string | null;
  current_live_structure_bucket_gap_to_minimum?: number | null;
  current_live_structure_bucket?: string | null;
  support_progress?: {
    status?: string | null;
    current_rows?: number | null;
    minimum_support_rows?: number | null;
    gap_to_minimum?: number | null;
    delta_vs_previous?: number | null;
    regressed_from_supported?: boolean | null;
    recent_supported_rows?: number | null;
    recent_supported_heartbeat?: string | null;
    delta_vs_recent_supported?: number | null;
  } | null;
  runtime_exact_support_rows?: number | null;
  calibration_exact_lane_rows?: number | null;
  sleeve_routing?: SleeveRoutingState | null;
};

type ExecutionConsoleRuntimeStatusResponse = {
  symbol?: string;
  timestamp?: string;
  automation?: boolean;
  dry_run?: boolean;
  execution_surface_contract?: {
    canonical_execution_route?: string;
    canonical_surface_label?: string;
    operations_surface?: SurfaceInfo | null;
    diagnostics_surface?: SurfaceInfo | null;
    shortcut_surface?: SurfaceInfo | null;
    readiness_scope?: string;
    live_ready?: boolean;
    live_ready_blockers?: string[];
    operator_message?: string;
    live_runtime_truth?: LiveRuntimeTruth | null;
    range_chop_playbook?: RangeChopPlaybook | null;
  } | null;
  execution?: {
    venue?: string;
    mode?: string;
    live_enabled?: boolean;
    kill_switch?: boolean;
    health?: {
      connected?: boolean;
      credentials_configured?: boolean;
      error?: string;
    } | null;
    live_runtime_truth?: LiveRuntimeTruth | null;
    range_chop_playbook?: RangeChopPlaybook | null;
    guardrails?: {
      kill_switch?: boolean;
      daily_loss_halt?: boolean;
      failure_halt?: boolean;
      consecutive_failures?: number;
      last_reject?: {
        code?: string;
        message?: string;
        timestamp?: string;
      } | null;
      last_failure?: {
        message?: string;
        timestamp?: string;
      } | null;
      last_order?: {
        venue?: string;
        symbol?: string;
        side?: string;
        qty?: number;
        price?: number | null;
        status?: string;
        order_id?: string | null;
        client_order_id?: string | null;
      } | null;
    } | null;
  } | null;
  account?: {
    captured_at?: string | null;
    degraded?: boolean;
    operator_message?: string | null;
    recovery_hint?: string | null;
    requested_symbol?: string | null;
    normalized_symbol?: string | null;
    position_count?: number;
    open_order_count?: number;
    balance?: {
      free?: number;
      total?: number;
      currency?: string;
    } | null;
    health?: {
      connected?: boolean;
      credentials_configured?: boolean;
      error?: string;
    } | null;
    positions?: Array<Record<string, unknown>>;
    open_orders?: Array<Record<string, unknown>>;
  } | null;
  execution_reconciliation?: {
    status?: string;
    summary?: string;
    checked_at?: string;
    issues?: string[];
    recovery_state?: {
      operator_action?: string;
      status?: string;
    } | null;
    lifecycle_audit?: {
      stage?: string;
      runtime_state?: string;
      trade_history_state?: string;
      restart_replay_required?: boolean;
      operator_action?: string;
    } | null;
    lifecycle_contract?: {
      summary?: string;
      replay_verdict?: string;
      artifact_coverage?: string;
      baseline_contract_status?: string;
      venue_lanes_summary?: string;
      venue_lanes?: Array<{
        venue?: string;
        summary?: string;
        operator_action_summary?: string;
        remediation_focus?: string;
        remediation_priority?: string;
        restart_replay_status?: string;
      }>;
    } | null;
  } | null;
  execution_metadata_smoke?: {
    generated_at?: string;
    freshness?: {
      status?: string;
      label?: string;
      age_minutes?: number | null;
    } | null;
    governance?: {
      status?: string;
      operator_message?: string;
      escalation_message?: string | null;
    } | null;
    venues?: Array<{
      venue?: string;
      ok?: boolean;
      enabled_in_config?: boolean;
      credentials_configured?: boolean;
      error?: string | null;
      blockers?: string[] | null;
      proof_state?: string | null;
      readiness_scope?: string | null;
      operator_next_action?: string | null;
      verify_next?: string | null;
      contract?: {
        step_size?: string | number | null;
        tick_size?: string | number | null;
        min_qty?: number | null;
        min_cost?: number | null;
      } | null;
    }>;
  } | null;
};

type ExecutionStrategyBundleSummary = {
  bundle_id?: string | null;
  bundle_hash?: string | null;
  freeze_status?: string | null;
  deployability_status?: string | null;
  feature_schema_hash?: string | null;
  model_artifact_status?: string | null;
  live_buy_add_status?: string | null;
  order_submission_enabled?: boolean | null;
  parity_blockers?: string[] | null;
  operator_action?: string | null;
};

type ExecutionWorkerControl = {
  status?: string | null;
  state?: string | null;
  backend_worker_bound?: boolean | null;
  worker_kind?: string | null;
  order_submission_enabled?: boolean | null;
  risk_on_order_enabled?: boolean | null;
  bundle_hash_match?: boolean | null;
  last_poll_at?: string | null;
  poll_count?: number | null;
  latest_order_proposal?: Record<string, unknown> | null;
  last_blocker?: string | null;
  last_error?: string | null;
  cancel_open_orders_status?: string | null;
  latest_command?: string | null;
  latest_command_at?: string | null;
  next_min_gap?: string | null;
  operator_action?: string | null;
};

type ExecutionStrategyBinding = {
  status?: string | null;
  strategy_name?: string | null;
  strategy_slug?: string | null;
  strategy_source?: string | null;
  strategy_hash?: string | null;
  schema_version?: string | null;
  updated_at?: string | null;
  created_at?: string | null;
  run_count?: number | null;
  primary_sleeve_key?: string | null;
  primary_sleeve_label?: string | null;
  strategy_type?: string | null;
  model_name?: string | null;
  title?: string | null;
  description?: string | null;
  sleeve_summary?: string | null;
  decision_quality_label?: string | null;
  avg_decision_quality_score?: number | null;
  avg_expected_win_rate?: number | null;
  roi?: number | null;
  profit_factor?: number | null;
  total_trades?: number | null;
  summary?: string | null;
  operator_action?: string | null;
  strategy_bundle?: ExecutionStrategyBundleSummary | null;
  strategy_bundle_status?: string | null;
  strategy_bundle_hash?: string | null;
  strategy_bundle_path?: string | null;
};

type HighConvictionTopKSupportContext = {
  current_live_structure_bucket_rows?: number | null;
  current_rows?: number | null;
  minimum_support_rows?: number | null;
  current_live_structure_bucket_gap_to_minimum?: number | null;
  gap_to_minimum?: number | null;
  gap?: number | null;
};

type HighConvictionTopKRuntimeContract = {
  support_summary?: string | null;
  risk_qualified_count?: number | null;
  runtime_blocked_candidate_count?: number | null;
  deployable_count?: number | null;
  operator_message?: string | null;
  support_context?: HighConvictionTopKSupportContext | null;
};

type ExecutionOverviewProfileCard = {
  key?: string;
  profile_id?: string;
  label?: string;
  summary?: string;
  activation_status?: string;
  lifecycle_status?: string;
  routing_reason?: string;
  planned_budget_amount?: number | null;
  planned_budget_ratio_of_balance?: number | null;
  next_operator_action?: string | null;
  symbol_scoped_position_count?: number;
  symbol_scoped_open_order_count?: number;
  current_run_state?: string | null;
  current_run?: ExecutionRunRecord | null;
  strategy_binding?: ExecutionStrategyBinding | null;
  control_contract?: {
    mode?: string;
    start_status?: string;
    start_reason?: string;
    pause_status?: string;
    stop_status?: string;
    latest_event_type?: string | null;
    latest_event_message?: string | null;
    shadow_only?: boolean | null;
    risk_on_order_enabled?: boolean | null;
    order_submission_enabled?: boolean | null;
    risk_reduction_allowed?: boolean | null;
    buy_add_requires_current_live_gate?: boolean | null;
    shadow_mode?: string | null;
    range_chop_playbook?: RangeChopPlaybook | null;
    high_conviction_topk?: HighConvictionTopKRuntimeContract | null;
    upgrade_prerequisite?: string;
  } | null;
};

type LiveRunnerOverview = {
  status?: string | null;
  source?: string | null;
  jsonl_root?: string | null;
  summary?: {
    total_runs?: number | null;
    running_runs?: number | null;
    stopped_runs?: number | null;
    failed_runs?: number | null;
    status_counts?: Record<string, number> | null;
    total_decisions?: number | null;
    candidate_decisions?: number | null;
    jsonl_backed?: boolean | null;
    order_submission_enabled?: boolean | null;
    risk_on_order_enabled?: boolean | null;
    live_order_submitted?: boolean | null;
  } | null;
  latest_run?: {
    run_id?: string | null;
    strategy_name?: string | null;
    strategy_hash?: string | null;
    symbol?: string | null;
    venue?: string | null;
    mode?: string | null;
    status?: string | null;
    started_at?: string | null;
    stopped_at?: string | null;
    last_heartbeat_at?: string | null;
    jsonl?: {
      exists?: boolean | null;
      path?: string | null;
      line_count?: number | null;
      latest_record?: Record<string, unknown> | null;
    } | null;
  } | null;
  latest_decision?: {
    decision_id?: number | string | null;
    run_id?: string | null;
    strategy_name?: string | null;
    symbol?: string | null;
    venue?: string | null;
    feature_timestamp?: string | null;
    created_at?: string | null;
    signal?: string | null;
    action?: string | null;
    side?: string | null;
    qty?: number | null;
    quote_amount?: number | null;
    order_submitted?: boolean | null;
    dry_run?: boolean | null;
    live_order_submitted?: boolean | null;
    model_confidence?: number | null;
    entry_quality?: number | null;
    reason?: string | null;
  } | null;
  shadow_evidence_gate?: {
    status?: string | null;
    source?: string | null;
    window_hours?: number | null;
    candidate_decisions?: number | null;
    pending_outcomes?: number | null;
    resolved_outcomes?: number | null;
    awaiting_label_replay?: number | null;
    next_reconcile_at?: string | null;
    pending_hours_remaining_min?: number | null;
    latest_entry?: Record<string, unknown> | null;
    order_submission_enabled?: boolean | null;
    risk_on_order_enabled?: boolean | null;
    live_order_submitted?: boolean | null;
    blocked_live_actions?: string[] | null;
    operator_message?: string | null;
  } | null;
  operator_message?: string | null;
};


type ShadowEvidenceDaemonOverview = {
  status?: string | null;
  updated_at?: string | null;
  operator_message?: string | null;
  summary?: {
    cycles_completed?: number | null;
    total_decisions?: number | null;
    candidate_decisions?: number | null;
    pending_outcomes?: number | null;
    resolved_outcomes?: number | null;
    awaiting_label_replay?: number | null;
    jsonl_backed?: boolean | null;
    live_order_submitted?: boolean | null;
  } | null;
  operator_review?: {
    confirmation_due?: boolean | null;
    next_operator_review_at?: string | null;
    operator_action?: string | null;
  } | null;
  guardrail?: {
    order_submission_enabled?: boolean | null;
    risk_on_order_enabled?: boolean | null;
    live_order_submitted?: boolean | null;
  } | null;
  latest_decision?: {
    action?: string | null;
    signal?: string | null;
    reason?: string | null;
    created_at?: string | null;
    feature_timestamp?: string | null;
    model_confidence?: number | null;
    entry_quality?: number | null;
  } | null;
};


type ExecutionOverviewResponse = {
  controls_mode?: string;
  operator_message?: string;
  upgrade_prerequisite?: string;
  summary?: {
    total_profiles?: number;
    active_profiles?: number;
    blocked_profiles?: number;
    standby_profiles?: number;
    monitoring_profiles?: number;
    running_runs?: number;
    paused_runs?: number;
    stopped_runs?: number;
    total_runs?: number;
    allocation_rule?: string;
    operator_message?: string;
  } | null;
  capital_plan?: {
    deployable_capital?: number | null;
    per_active_profile_budget?: number | null;
    allocation_rule?: string;
    operator_message?: string;
    max_position_ratio?: number | null;
    confidence?: number | null;
  } | null;
  strategy_source_summary?: {
    route?: string | null;
    strategy_count?: number | null;
    covered_sleeves?: number | null;
    total_sleeves?: number | null;
    missing_sleeves?: string[] | null;
    operator_message?: string | null;
  } | null;
  range_chop_playbook?: RangeChopPlaybook | null;
  execution_readiness?: ExecutionReadiness | null;
  shadow_trade_ledger?: ShadowTradeLedger | null;
  venue_dry_run_proof?: VenueDryRunProof | null;
  canary_gap_answers?: CanaryGapAnswers | null;
  live_runner?: LiveRunnerOverview | null;
  shadow_evidence_daemon?: ShadowEvidenceDaemonOverview | null;
  paper_shadow_outcome_reconciliation?: PaperShadowOutcomeReconciliationResponse | null;
  profile_cards?: ExecutionOverviewProfileCard[] | null;
};

type ExecutionRunEvent = {
  event_id?: number;
  run_id?: string;
  profile_id?: string;
  event_type?: string;
  level?: string;
  message?: string;
  payload?: Record<string, unknown> | null;
  created_at?: string;
};

type ExecutionRunBindingContract = {
  status?: string | null;
  scope?: string | null;
  summary?: string | null;
  operator_action?: string | null;
  shadow_only?: boolean | null;
  high_conviction_topk?: HighConvictionTopKRuntimeContract | null;
  ownership_boundary?: {
    ledger_scope?: string | null;
    capital_attribution?: string | null;
    position_attribution?: string | null;
    open_order_attribution?: string | null;
    pnl_attribution?: string | null;
    summary?: string | null;
  } | null;
};

type ExecutionRunPreviewRecord = Record<string, unknown>;

type ExecutionRunLedgerPreview = {
  scope?: string | null;
  ownership_status?: string | null;
  summary?: string | null;
  budget_alignment_status?: string | null;
  budget_alignment_summary?: string | null;
  pricing_complete?: boolean | null;
  position_count?: number | null;
  open_order_count?: number | null;
  position_priced_count?: number | null;
  open_order_priced_count?: number | null;
  gross_position_notional?: number | null;
  net_position_notional?: number | null;
  open_order_notional?: number | null;
  total_known_commitment?: number | null;
  unrealized_pnl?: number | null;
  capital_in_use?: number | null;
  budget_amount?: number | null;
  budget_gap?: number | null;
  commitment_vs_budget_ratio?: number | null;
  currency?: string | null;
};

type ExecutionRunBindingSnapshot = {
  account_snapshot?: {
    captured_at?: string | null;
    position_count?: number | null;
    open_order_count?: number | null;
  } | null;
  capital_preview?: {
    allocation_scope?: string | null;
    ownership_status?: string | null;
    budget_amount?: number | null;
    budget_ratio?: number | null;
    balance_total?: number | null;
    balance_free?: number | null;
    currency?: string | null;
    summary?: string | null;
  } | null;
  shared_symbol_preview?: {
    scope?: string | null;
    ownership_status?: string | null;
    ownership_summary?: string | null;
    captured_at?: string | null;
    positions_total_count?: number | null;
    open_orders_total_count?: number | null;
    balance?: {
      total?: number | null;
      free?: number | null;
      currency?: string | null;
    } | null;
    positions?: ExecutionRunPreviewRecord[] | null;
    open_orders?: ExecutionRunPreviewRecord[] | null;
  } | null;
  shared_symbol_ledger_preview?: ExecutionRunLedgerPreview | null;
  reconciliation?: {
    status?: string | null;
    summary?: string | null;
  } | null;
  guardrails?: {
    last_order?: {
      order_id?: string | null;
      status?: string | null;
    } | null;
  } | null;
};

type ExecutionRunRecord = {
  run_id?: string;
  profile_id?: string;
  label?: string;
  state?: string;
  state_label?: string;
  mode?: string;
  control_mode?: string;
  runtime_binding_status?: string;
  budget_amount?: number | null;
  budget_ratio?: number | null;
  capital_currency?: string | null;
  start_time?: string | null;
  stop_time?: string | null;
  stop_reason?: string | null;
  last_event_type?: string | null;
  last_event_message?: string | null;
  last_event_at?: string | null;
  latest_event?: ExecutionRunEvent | null;
  recent_events?: ExecutionRunEvent[] | null;
  strategy_binding?: ExecutionStrategyBinding | null;
  runtime_binding_contract?: ExecutionRunBindingContract | null;
  runtime_binding_snapshot?: ExecutionRunBindingSnapshot | null;
  strategy_bundle_hash?: string | null;
  strategy_bundle_path?: string | null;
  strategy_bundle_status?: string | null;
  worker_status?: string | null;
  worker_control?: ExecutionWorkerControl | null;
  action_contract?: {
    can_pause?: boolean;
    can_resume?: boolean;
    can_stop?: boolean;
    order_submission_enabled?: boolean | null;
    risk_on_order_enabled?: boolean | null;
    worker_control?: ExecutionWorkerControl | null;
    upgrade_prerequisite?: string;
  } | null;
};

type ExecutionRunsResponse = {
  controls_mode?: string;
  operator_message?: string;
  upgrade_prerequisite?: string;
  summary?: {
    total_profiles?: number;
    active_profiles?: number;
    blocked_profiles?: number;
    standby_profiles?: number;
    running_runs?: number;
    paused_runs?: number;
    stopped_runs?: number;
    total_runs?: number;
  } | null;
  runs?: ExecutionRunRecord[] | null;
};

type PaperShadowRehearsalProof = {
  status?: string | null;
  artifact_status?: string | null;
  can_poll_workers?: boolean | null;
  can_reconcile_outcomes?: boolean | null;
  poll_blocked_by_pending_outcome?: boolean | null;
  next_reconcile_at?: string | null;
  pending_hours_remaining_min?: number | null;
  resolution_due_count?: number | null;
  order_submission_enabled?: boolean | null;
  risk_on_order_enabled?: boolean | null;
  live_order_submitted?: boolean | null;
  next_operator_action?: string | null;
  operator_message?: string | null;
  run_counts?: {
    running?: number | null;
    paused?: number | null;
    stopped?: number | null;
    total?: number | null;
  } | null;
  latest_run?: {
    run_id?: string | null;
    profile_id?: string | null;
    state?: string | null;
    worker_status?: string | null;
    last_event_type?: string | null;
    last_event_at?: string | null;
    strategy_bundle_hash?: string | null;
  } | null;
  chain?: Array<{
    key?: string | null;
    label?: string | null;
    status?: string | null;
    count?: number | null;
  }> | null;
  blocked_live_actions?: string[] | null;
};

type PaperShadowOutcomeReconciliationResponse = {
  artifact_path?: string | null;
  persisted?: boolean | null;
  artifact?: {
    status?: string | null;
    generated_at?: string | null;
    mode?: string | null;
    source?: string | null;
    order_submission_enabled?: boolean | null;
    risk_on_order_enabled?: boolean | null;
    operator_message?: string | null;
    rehearsal_proof?: PaperShadowRehearsalProof | null;
    summary?: {
      worker_poll_events?: number | null;
      resolved_outcomes?: number | null;
      pending_outcomes?: number | null;
      awaiting_label_replay?: number | null;
      parity_blocked_events?: number | null;
      entries?: number | null;
      live_runner_total_runs?: number | null;
      live_runner_total_decisions?: number | null;
      live_runner_candidate_decisions?: number | null;
      live_runner_pending_outcomes?: number | null;
      live_runner_resolved_outcomes?: number | null;
      live_runner_awaiting_label_replay?: number | null;
      live_runner_jsonl_backed?: boolean | null;
      live_order_submitted?: boolean | null;
    } | null;
    live_runner?: LiveRunnerOverview | null;
    live_runner_shadow_gate?: LiveRunnerOverview["shadow_evidence_gate"] | null;
  } | null;
};

type ExecutionWorkerPollResponse = {
  status?: string | null;
  operator_message?: string | null;
  pending_outcome_gates?: Array<{
    status?: string | null;
    window_end?: string | null;
    hours_remaining?: number | null;
    operator_action?: string | null;
  }> | null;
  outcome_reconciliation?: PaperShadowOutcomeReconciliationResponse | null;
};

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function formatPercent(value: number | null | undefined, digits = 1): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

function formatSignedNumber(value: number | null | undefined, digits = 2): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(digits)}`;
}

function formatTime(value?: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("zh-TW");
}

function toMaybeNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function pickPreviewText(record: ExecutionRunPreviewRecord, keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key];
    if (value === null || value === undefined) continue;
    const text = String(value).trim();
    if (text) return text;
  }
  return null;
}

function humanizeExecutionModeLabel(value?: string | null): string {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized || normalized === "unknown") return "未提供";
  return EXECUTION_MODE_LABELS[normalized] || String(value).trim();
}

function humanizeExecutionVenueLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "未提供";
  const lower = normalized.toLowerCase();
  return EXECUTION_VENUE_LABELS[lower] || normalized;
}

function humanizeMetadataFreshnessLabel(value?: string | null): string {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized || normalized === "unavailable") return "未提供";
  if (normalized === "fresh") return "新鮮";
  if (normalized === "stale") return "已過期";
  return humanizeRuntimeDetailText(value);
}

function humanizeTradeSideLabel(value?: string | null): string {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) return "—";
  if (["buy", "bid", "long"].includes(normalized)) return "買入";
  if (["sell", "ask", "short"].includes(normalized)) return "賣出";
  if (["reduce", "close"].includes(normalized)) return "減碼";
  return humanizeRuntimeDetailText(value);
}

function summarizePreviewRecord(record: ExecutionRunPreviewRecord): string {
  const symbol = pickPreviewText(record, ["symbol", "instId", "market", "pair"]) || "未提供";
  const side = humanizeTradeSideLabel(pickPreviewText(record, ["side", "positionSide"]));
  const qty = toMaybeNumber(record.size ?? record.qty ?? record.amount ?? record.contracts ?? record.positionAmt);
  const price = toMaybeNumber(record.price ?? record.entryPrice ?? record.avgPrice ?? record.markPrice);
  const status = humanizeRuntimeDetailText(pickPreviewText(record, ["status", "state"]));
  return [
    symbol,
    side,
    qty !== null ? `數量 ${formatNumber(qty, 4)}` : null,
    price !== null ? `價格 ${formatNumber(price, 2)}` : null,
    status,
  ].filter(Boolean).join(" · ");
}

function summarizePreviewRecords(records?: ExecutionRunPreviewRecord[] | null): string {
  if (!Array.isArray(records) || records.length === 0) return "無";
  return records.map((record) => summarizePreviewRecord(record)).join(" ｜ ");
}

function getStatusTone(status?: string | null): string {
  const normalized = String(status || "").toLowerCase();
  if (["ok", "healthy", "aligned", "fresh", "running", "connected"].some((item) => normalized.includes(item))) {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
  }
  if (["stale", "warning", "degraded", "attention", "beta", "operator", "replay"].some((item) => normalized.includes(item))) {
    return "border-amber-500/30 bg-amber-500/10 text-amber-100";
  }
  if (["fail", "error", "blocked", "halt", "missing", "not"].some((item) => normalized.includes(item))) {
    return "border-rose-500/30 bg-rose-500/10 text-rose-100";
  }
  return "border-cyan-500/30 bg-cyan-500/10 text-cyan-100";
}

function readRecordString(record: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function readRecordNumber(record: Record<string, unknown>, keys: string[]): number | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return null;
}

function getValueTone(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value) || value === 0) return "text-white";
  return value > 0 ? "text-emerald-300" : "text-rose-300";
}

function buildWorkerPollGuardMessage(resp: ExecutionWorkerPollResponse): string | null {
  if (resp?.status !== "pending_outcome_blocked") return null;
  const gate = Array.isArray(resp.pending_outcome_gates) ? resp.pending_outcome_gates[0] : null;
  const proof = resp.outcome_reconciliation?.artifact?.rehearsal_proof ?? null;
  const windowEnd = gate?.window_end || proof?.next_reconcile_at || null;
  const hoursRemaining = typeof gate?.hours_remaining === "number"
    ? gate.hours_remaining
    : proof?.pending_hours_remaining_min != null
      ? proof.pending_hours_remaining_min / 60
      : null;
  const eta = windowEnd
    ? `ETA ${windowEnd}${hoursRemaining != null ? `，約 ${formatNumber(hoursRemaining, 2)}h` : ""}`
    : "ETA 尚未建立";
  return `${resp.operator_message || "24h paper/shadow outcome 還在觀察窗，本次沒有重複寫入 worker poll event。"} ${eta}`;
}

function currentSupportSummaryFromRuntimeContract(contract?: HighConvictionTopKRuntimeContract | null): string | null {
  if (!contract) return null;
  if (contract.support_summary) return humanizeRuntimeDetailText(contract.support_summary);
  const support = contract.support_context ?? null;
  const rows = support?.current_live_structure_bucket_rows ?? support?.current_rows ?? null;
  const minimum = support?.minimum_support_rows ?? null;
  const gap = support?.current_live_structure_bucket_gap_to_minimum ?? support?.gap_to_minimum ?? support?.gap ?? null;
  if (typeof rows === "number" && typeof minimum === "number") {
    const gapLabel = typeof gap === "number" ? `，缺 ${formatNumber(gap, 0)}` : "";
    return `即時精準支持 ${formatNumber(rows, 0)}/${formatNumber(minimum, 0)}${gapLabel}；影子觀察只記錄決策，不送單、不加倉。`;
  }
  return contract.operator_message ? humanizeRuntimeDetailText(contract.operator_message) : null;
}

export default function ExecutionConsole() {
  const { data: runtimeStatus, loading, error, refresh: refreshRuntimeStatus } = useApi<ExecutionConsoleRuntimeStatusResponse>("/api/status", 60000);
  const { data: executionOverview, loading: overviewLoading, error: overviewError, refresh: refreshExecutionOverview } = useApi<ExecutionOverviewResponse>("/api/execution/overview", 60000);
  const { data: executionRuns, loading: runsLoading, error: runsError, refresh: refreshExecutionRuns } = useApi<ExecutionRunsResponse>("/api/execution/runs", 60000);
  const { data: workerOutcomes, loading: workerOutcomesLoading, error: workerOutcomesError, refresh: refreshWorkerOutcomes } = useApi<PaperShadowOutcomeReconciliationResponse>("/api/execution/workers/outcomes", 60000);
  const [runActionState, setRunActionState] = useState<{ tone: "idle" | "pending" | "success" | "warning" | "error"; message: string }>({
    tone: "idle",
    message: "",
  });
  const [operatorActionState, setOperatorActionState] = useState<{ tone: "idle" | "pending" | "success" | "error"; message: string }>({
    tone: "idle",
    message: "",
  });
  const [naturalCommand, setNaturalCommand] = useState("");

  const refreshExecutionWorkspace = async () => {
    await Promise.all([refreshRuntimeStatus(), refreshExecutionOverview(), refreshExecutionRuns(), refreshWorkerOutcomes()]);
  };

  const handleRunAction = async (endpoint: string, pendingLabel: string, successLabel: string) => {
    setRunActionState({ tone: "pending", message: pendingLabel });
    try {
      const resp = await fetchApi<ExecutionWorkerPollResponse>(endpoint, { method: "POST" });
      await refreshExecutionWorkspace();
      const guardedMessage = buildWorkerPollGuardMessage(resp);
      setRunActionState({
        tone: guardedMessage ? "warning" : "success",
        message: guardedMessage || resp.operator_message || successLabel,
      });
    } catch (err: any) {
      setRunActionState({ tone: "error", message: err?.message || "運行操作失敗" });
    }
  };

  const executionSurfaceContract = runtimeStatus?.execution_surface_contract ?? null;
  const operationsSurface = executionSurfaceContract?.operations_surface ?? null;
  const diagnosticsSurface = executionSurfaceContract?.diagnostics_surface ?? null;
  const liveRuntimeTruth = runtimeStatus?.execution?.live_runtime_truth ?? executionSurfaceContract?.live_runtime_truth ?? null;
  const rangeChopPlaybook = executionOverview?.range_chop_playbook || executionSurfaceContract?.range_chop_playbook || runtimeStatus?.execution?.range_chop_playbook || null;
  const rangeChopPlaybookVisible = Boolean(rangeChopPlaybook?.shadow_available || rangeChopPlaybook?.risk_reduction_allowed);
  const rangeChopSupportSummaryLabel = humanizeRuntimeDetailText(rangeChopPlaybook?.support_summary || null) || "等待精準支持累積";
  const rangeChopOperatorMessageLabel = humanizeRuntimeDetailText(rangeChopPlaybook?.operator_message || null) || "不是永遠不能實戰；先用影子觀察與減風險把高低震盪拆成可驗證流程。";
  const rangeChopNextActionLabel = humanizeRuntimeDetailText(rangeChopPlaybook?.next_operator_action || null) || "先做影子觀察 / 減風險先行；買入 / 加倉仍等即時部署門檻。";
  const liveRouting = liveRuntimeTruth?.sleeve_routing ?? null;
  const liveActiveSleeves = Array.isArray(liveRouting?.active_sleeves) ? liveRouting.active_sleeves : [];
  const liveInactiveSleeves = Array.isArray(liveRouting?.inactive_sleeves) ? liveRouting.inactive_sleeves : [];
  const executionSummary = runtimeStatus?.execution ?? null;
  const guardrails = executionSummary?.guardrails ?? null;
  const accountSummary = runtimeStatus?.account ?? null;
  const executionReconciliation = runtimeStatus?.execution_reconciliation ?? null;
  const lifecycleAudit = executionReconciliation?.lifecycle_audit ?? null;
  const lifecycleContract = executionReconciliation?.lifecycle_contract ?? null;
  const venueLanes = Array.isArray(lifecycleContract?.venue_lanes) ? lifecycleContract.venue_lanes : [];
  const metadataSmoke = runtimeStatus?.execution_metadata_smoke ?? null;
  const metadataSmokeFreshness = metadataSmoke?.freshness ?? null;
  const metadataSmokeGovernance = metadataSmoke?.governance ?? null;
  const runtimeStatusPending = loading && !runtimeStatus && !error;
  const overviewPending = overviewLoading && !executionOverview && !overviewError;
  const runsPending = runsLoading && !executionRuns && !runsError;
  const executionConsoleInitialSyncPending = runtimeStatusPending || overviewPending || runsPending;
  const metadataSmokeFreshnessLabel = runtimeStatusPending
    ? "同步中"
    : humanizeMetadataFreshnessLabel(metadataSmokeFreshness?.label || metadataSmokeFreshness?.status || null);
  const reconciliationCoverageLimited = isExecutionReconciliationLimitedEvidence(
    executionReconciliation?.status,
    lifecycleAudit?.stage,
    lifecycleContract?.artifact_coverage,
  );
  const reconciliationStatusLabel = runtimeStatusPending
    ? "同步中"
    : humanizeExecutionReconciliationStatusLabel(
      executionReconciliation?.status,
      lifecycleAudit?.stage,
      lifecycleContract?.artifact_coverage,
    );
  const reconciliationSummaryLabel = runtimeStatusPending
    ? "正在向 /api/status 取得對帳 / 恢復摘要。"
    : reconciliationCoverageLimited
      ? `${humanizeRuntimeDetailText(executionReconciliation?.summary || lifecycleContract?.summary || "尚未取得對帳摘要。")} · 尚未有執行期委託，因此目前只能確認「沒有發現明顯對帳落差」，不可視為完整實單驗證。`
      : humanizeRuntimeDetailText(executionReconciliation?.summary || lifecycleContract?.summary || "尚未取得對帳摘要。");
  const supportAlignmentLabel = runtimeStatusPending ? "同步中" : (liveRuntimeTruth?.support_alignment_status || "unavailable");
  const runtimeClosureStateLabel = runtimeStatusPending
    ? "同步中"
    : humanizeRuntimeClosureStateLabel(
      liveRuntimeTruth?.runtime_closure_state,
      liveRuntimeTruth?.runtime_closure_summary,
    );
  const supportRowsLabel = runtimeStatusPending
    ? "同步中"
    : (liveRuntimeTruth?.support_rows_text || "—");
  const supportGapLabel = runtimeStatusPending
    ? "同步中"
    : (typeof liveRuntimeTruth?.current_live_structure_bucket_gap_to_minimum === "number"
      ? liveRuntimeTruth.current_live_structure_bucket_gap_to_minimum.toFixed(0)
      : (typeof liveRuntimeTruth?.support_progress?.gap_to_minimum === "number"
        ? liveRuntimeTruth.support_progress.gap_to_minimum.toFixed(0)
        : "—"));
  const supportProgressStatusLabel = runtimeStatusPending
    ? "同步中"
    : humanizeSupportProgressStatusLabel(liveRuntimeTruth?.support_progress?.status || null);
  const supportDeltaLabel = runtimeStatusPending
    ? "同步中"
    : humanizeSupportProgressDeltaLabel(liveRuntimeTruth?.support_progress || null);
  const supportReferenceLabel = runtimeStatusPending
    ? "同步中"
    : humanizeSupportProgressReferenceLabel(liveRuntimeTruth?.support_progress || null);
  const supportRouteVerdictLabel = runtimeStatusPending
    ? "同步中"
    : humanizeSupportRouteLabel(liveRuntimeTruth?.support_route_verdict || null);
  const supportGovernanceRouteLabel = runtimeStatusPending
    ? "同步中"
    : humanizeSupportGovernanceRouteLabel(liveRuntimeTruth?.support_governance_route || null);
  const supportAlignmentCountsLabel = runtimeStatusPending
    ? "執行期 / 校準 同步中"
    : `執行期 / 校準 ${liveRuntimeTruth?.runtime_exact_support_rows ?? "—"} / ${liveRuntimeTruth?.calibration_exact_lane_rows ?? "—"}`;
  const supportAlignmentSummaryLabel = runtimeStatusPending
    ? "正在同步執行期 / 校準樣本對齊。"
    : humanizeRuntimeDetailText(liveRuntimeTruth?.support_alignment_summary || supportAlignmentLabel || "—");
  const rawAllowedLayersReasonLabel = runtimeStatusPending
    ? "同步中"
    : humanizeRuntimeDetailText(liveRuntimeTruth?.allowed_layers_raw_reason || null);
  const finalAllowedLayersReasonLabel = runtimeStatusPending
    ? "同步中"
    : humanizeRuntimeDetailText(liveRuntimeTruth?.allowed_layers_reason || null);

  const positions = Array.isArray(accountSummary?.positions) ? accountSummary.positions : [];
  const openOrders = Array.isArray(accountSummary?.open_orders) ? accountSummary.open_orders : [];
  const balanceCurrency = accountSummary?.balance?.currency || "USDT";
  const balanceFree = typeof accountSummary?.balance?.free === "number" ? accountSummary.balance.free : null;
  const balanceTotal = typeof accountSummary?.balance?.total === "number" ? accountSummary.balance.total : null;
  const accountCredentialsConfigured = Boolean(accountSummary?.health?.credentials_configured ?? executionSummary?.health?.credentials_configured);
  const accountSnapshotUnavailableLabel = !accountCredentialsConfigured
    ? "僅元資料快照"
    : "餘額暫不可用";
  const accountSnapshotUnavailableReason = !accountCredentialsConfigured
    ? "僅同步公開元資料；私有餘額待交易所憑證。"
    : "最新帳戶快照暫無餘額資料。";
  const accountBalanceUnavailableLabel = !accountCredentialsConfigured
    ? "待私有餘額"
    : "餘額暫不可用";
  const accountBalanceUnavailableReason = !accountCredentialsConfigured
    ? "需私有餘額後才能計算 Bot 預算與可部署資金。"
    : "最新執行快照暫無餘額資料。";
  const sharedLedgerUnavailableLabel = !accountCredentialsConfigured
    ? "尚無運行帳本"
    : "共享帳本暫不可用";
  const allocatedCapital = balanceTotal != null && balanceFree != null ? Math.max(balanceTotal - balanceFree, 0) : null;
  const lastOrder = guardrails?.last_order ?? null;
  const lastReject = guardrails?.last_reject ?? null;
  const lastFailure = guardrails?.last_failure ?? null;
  const liveReadyBlockers = Array.isArray(executionSurfaceContract?.live_ready_blockers) ? executionSurfaceContract.live_ready_blockers : [];
  const venueChecks = Array.isArray(metadataSmoke?.venues) ? metadataSmoke.venues : [];
  const executionOverviewSummary = executionOverview?.summary ?? null;
  const executionCapitalPlan = executionOverview?.capital_plan ?? null;
  const executionStrategySummary = executionOverview?.strategy_source_summary ?? null;
  const executionProfileCards = Array.isArray(executionOverview?.profile_cards) ? executionOverview.profile_cards : [];
  const executionReadiness = executionOverview?.execution_readiness || null;
  const shadowTradeLedger = executionOverview?.shadow_trade_ledger || null;
  const venueDryRunProof = executionOverview?.venue_dry_run_proof || null;
  const canaryGapAnswers = executionOverview?.canary_gap_answers || null;
  const readinessGates = Array.isArray(executionReadiness?.gates) ? executionReadiness.gates : [];
  const readinessGateByKey = new Map(readinessGates.map((gate) => [gate.key || gate.label || "", gate]));
  const readinessStageLabel = executionReadiness?.stage_label || "Shadow / Reduce-only";
  const readinessBlockingGateLabel = executionReadiness?.blocking_gate_label || canaryGapAnswers?.blocking_gate || "同步中";
  const readinessCanDo = Array.isArray(executionReadiness?.what_can_do_now) ? executionReadiness.what_can_do_now : [];
  const readinessCannotDo = Array.isArray(executionReadiness?.what_cannot_do_now) ? executionReadiness.what_cannot_do_now : [];
  const canaryDistance = Array.isArray(canaryGapAnswers?.distance_to_canary) ? canaryGapAnswers.distance_to_canary : [];
  const canaryDrills = Array.isArray(canaryGapAnswers?.drills_available_today) ? canaryGapAnswers.drills_available_today : [];
  const shadowLedgerEntries = Array.isArray(shadowTradeLedger?.entries) ? shadowTradeLedger.entries : [];
  const firstShadowLedgerEntry = shadowLedgerEntries[0] || null;
  const canaryPlan = canaryGapAnswers?.first_canary_plan_if_all_gates_pass || null;
  const timeToEvidence = executionReadiness?.time_to_evidence || canaryGapAnswers?.time_to_evidence || null;
  const alternativeSolutionReview = executionReadiness?.alternative_solution_review || canaryGapAnswers?.alternative_solution_review || null;
  const alternativeSolutionAllowed = Array.isArray(alternativeSolutionReview?.allowed_today) ? alternativeSolutionReview.allowed_today : [];
  const alternativeSolutionNotAllowed = Array.isArray(alternativeSolutionReview?.not_allowed) ? alternativeSolutionReview.not_allowed : [];
  const milestoneProgression = executionReadiness?.milestone_progression || canaryGapAnswers?.milestone_progression || null;
  const milestonePreferredEntry = milestoneProgression?.preferred_entrypoint || null;
  const milestonePreferredPayload = milestonePreferredEntry?.payload && typeof milestonePreferredEntry.payload === "object" && !Array.isArray(milestonePreferredEntry.payload)
    ? milestonePreferredEntry.payload as Record<string, unknown>
    : null;
  const milestonePreferredEndpoint = typeof milestonePreferredEntry?.endpoint === "string" ? milestonePreferredEntry.endpoint : null;
  const milestonePreferredCommand = typeof milestonePreferredEntry?.command === "string" ? milestonePreferredEntry.command : null;
  const milestonePreferredSide = typeof milestonePreferredPayload?.side === "string" ? milestonePreferredPayload.side : null;
  const milestonePreferredQty = typeof milestonePreferredPayload?.qty === "number" ? milestonePreferredPayload.qty : null;
  const milestoneSafeLanes = Array.isArray(milestoneProgression?.safe_entry_lanes) ? milestoneProgression.safe_entry_lanes : [];
  const milestoneVisibleLanes = milestoneSafeLanes.slice(0, 3);
  const timeToEvidenceEtaLabel = typeof timeToEvidence?.estimated_heartbeats_to_support === "number"
    ? `${timeToEvidence.estimated_heartbeats_to_support} 輪 / 約 ${formatNumber(timeToEvidence.estimated_days_at_hourly_heartbeat, 2)} 天`
    : "無可靠完成時間";
  const venueProofChecks = [
    { label: "credential present", value: venueDryRunProof?.credential_present ? "已確認" : "待 runtime proof" },
    { label: "order preview", value: String(venueDryRunProof?.order_preview?.status || "待演練") },
    { label: "ack simulation", value: String(venueDryRunProof?.ack_simulation?.status || "待演練") },
    { label: "cancel simulation", value: String(venueDryRunProof?.cancel_simulation?.status || "待演練") },
    { label: "fill simulation", value: String(venueDryRunProof?.fill_simulation?.status || "待演練") },
    { label: "reconciliation check", value: String(venueDryRunProof?.reconciliation_check?.status || "待演練") },
  ];
  const readinessStatusTone = executionReadiness?.canary_ready ? "ok" : (executionReadiness?.status === "shadow_reduce_only" ? "warning" : "blocked");
  const executionRunsSummary = executionRuns?.summary ?? null;
  const executionRunRecords = Array.isArray(executionRuns?.runs) ? executionRuns.runs : [];
  const workerOutcomeArtifact = workerOutcomes?.artifact ?? null;
  const workerOutcomeSummary = workerOutcomeArtifact?.summary ?? null;
  const workerRehearsalProof = workerOutcomeArtifact?.rehearsal_proof ?? null;
  const workerOutcomeStatusLabel = workerOutcomesLoading && !workerOutcomes && !workerOutcomesError
    ? "同步中"
    : humanizeRuntimeDetailText(workerOutcomeArtifact?.status || "尚無 worker outcome");
  const workerRehearsalStatusLabel = workerOutcomesLoading && !workerOutcomes && !workerOutcomesError
    ? "同步中"
    : humanizeRuntimeDetailText(workerRehearsalProof?.status || "尚未建立 rehearsal proof");
  const workerOutcomeSummaryLabel = workerOutcomesLoading && !workerOutcomes && !workerOutcomesError
    ? "正在取得 paper/shadow outcome reconciliation。"
    : workerOutcomesError
      ? `Outcome 載入失敗：${workerOutcomesError}`
      : `resolved ${workerOutcomeSummary?.resolved_outcomes ?? 0} · pending ${workerOutcomeSummary?.pending_outcomes ?? 0} · label replay ${workerOutcomeSummary?.awaiting_label_replay ?? 0}`;
  const workerOutcomeNextActionLabel = workerOutcomesLoading && !workerOutcomes && !workerOutcomesError
    ? "正在同步 rehearsal proof。"
    : workerOutcomesError
      ? "先確認 /api/execution/workers/outcomes 是否可用。"
      : humanizeRuntimeDetailText(workerRehearsalProof?.next_operator_action || workerOutcomeArtifact?.operator_message || "先啟動 paper/shadow run，再同步 worker。");
  const workerOutcomeEtaLabel = workerRehearsalProof?.poll_blocked_by_pending_outcome
    ? `next reconcile ${workerRehearsalProof.next_reconcile_at || "待定"} · 約 ${formatNumber(workerRehearsalProof.pending_hours_remaining_min, 2)}h`
    : workerRehearsalProof?.next_reconcile_at
      ? `next reconcile ${workerRehearsalProof.next_reconcile_at}`
      : "reconcile ETA 尚未建立";
  const liveRunnerOverview = executionOverview?.live_runner || workerOutcomeArtifact?.live_runner || null;
  const liveRunnerSummary = liveRunnerOverview?.summary ?? null;
  const liveRunnerGate = liveRunnerOverview?.shadow_evidence_gate || workerOutcomeArtifact?.live_runner_shadow_gate || null;
  const liveRunnerLatestRun = liveRunnerOverview?.latest_run ?? null;
  const liveRunnerLatestDecision = liveRunnerOverview?.latest_decision ?? null;
  const liveRunnerStatusLabel = overviewPending
    ? "同步中"
    : humanizeRuntimeDetailText(liveRunnerOverview?.status || "尚未建立 standalone runner");
  const liveRunnerGateStatusLabel = humanizeRuntimeDetailText(liveRunnerGate?.status || "尚未建立 24h gate");
  const liveRunnerLatestActionLabel = humanizeRuntimeDetailText(liveRunnerLatestDecision?.action || liveRunnerLatestDecision?.signal || "尚無決策");
  const liveRunnerLatestDecisionDetailLabel = liveRunnerLatestDecision
    ? `${formatTime(liveRunnerLatestDecision.created_at || liveRunnerLatestDecision.feature_timestamp)} · confidence ${formatNumber(liveRunnerLatestDecision.model_confidence, 3)} · EQ ${formatNumber(liveRunnerLatestDecision.entry_quality, 3)} · ${humanizeRuntimeDetailText(liveRunnerLatestDecision.reason || "—")}`
    : "等待 runner 寫入 live_runner_decisions。";
  const liveRunnerEvidenceLabel = `${liveRunnerSummary?.total_runs ?? 0} runs · ${liveRunnerSummary?.total_decisions ?? 0} decisions · JSONL ${liveRunnerSummary?.jsonl_backed ? "已對齊" : "未對齊"}`;
  const liveRunnerGateCountsLabel = `24h gate resolved ${liveRunnerGate?.resolved_outcomes ?? 0} · pending ${liveRunnerGate?.pending_outcomes ?? 0} · label replay ${liveRunnerGate?.awaiting_label_replay ?? 0}`;
  const liveRunnerFailClosedLabel = liveRunnerGate?.order_submission_enabled || liveRunnerSummary?.order_submission_enabled
    ? "送單允許（需立即複核）"
    : "Fail-closed · 不送單";
  const liveRunnerJsonlPathLabel = liveRunnerLatestRun?.jsonl?.path || liveRunnerOverview?.jsonl_root || "data/live_trading";
  const shadowEvidenceDaemon = executionOverview?.shadow_evidence_daemon ?? null;
  const shadowEvidenceDaemonSummary = shadowEvidenceDaemon?.summary ?? null;
  const shadowEvidenceDaemonReview = shadowEvidenceDaemon?.operator_review ?? null;
  const shadowEvidenceDaemonGuardrail = shadowEvidenceDaemon?.guardrail ?? null;
  const shadowEvidenceDaemonLatest = shadowEvidenceDaemon?.latest_decision ?? null;
  const shadowEvidenceDaemonStatusLabel = overviewPending
    ? "同步中"
    : humanizeRuntimeDetailText(shadowEvidenceDaemon?.status || "尚未建立 daemon artifact");
  const shadowEvidenceDaemonDetailLabel = humanizeRuntimeDetailText(shadowEvidenceDaemon?.operator_message || "背景 daemon 只蒐集 shadow evidence，不送單。");
  const shadowEvidenceDaemonCountsLabel = `cycles ${shadowEvidenceDaemonSummary?.cycles_completed ?? 0} · decisions ${shadowEvidenceDaemonSummary?.total_decisions ?? 0} · candidates ${shadowEvidenceDaemonSummary?.candidate_decisions ?? 0}`;
  const shadowEvidenceDaemonOutcomeLabel = `pending ${shadowEvidenceDaemonSummary?.pending_outcomes ?? 0} · resolved ${shadowEvidenceDaemonSummary?.resolved_outcomes ?? 0} · label replay ${shadowEvidenceDaemonSummary?.awaiting_label_replay ?? 0}`;
  const shadowEvidenceDaemonLatestLabel = shadowEvidenceDaemonLatest
    ? `${formatTime(shadowEvidenceDaemonLatest.created_at || shadowEvidenceDaemonLatest.feature_timestamp)} · ${humanizeRuntimeDetailText(shadowEvidenceDaemonLatest.action || shadowEvidenceDaemonLatest.signal || "HOLD")} · ${humanizeRuntimeDetailText(shadowEvidenceDaemonLatest.reason || "—")}`
    : "等待第一筆 shadow evidence decision。";
  const shadowEvidenceDaemonReviewLabel = shadowEvidenceDaemonReview?.confirmation_due
    ? "需要使用者確認 evidence"
    : `下次確認 ${formatTime(shadowEvidenceDaemonReview?.next_operator_review_at)}`;
  const shadowEvidenceDaemonTone = shadowEvidenceDaemonGuardrail?.live_order_submitted
    ? "border-red-400/25 bg-red-400/8 text-red-100"
    : shadowEvidenceDaemonReview?.confirmation_due
      ? "border-amber-400/25 bg-amber-400/8 text-amber-100"
      : "border-cyan-400/20 bg-cyan-400/8 text-cyan-100";
  const runsByProfileId = new Map(executionRunRecords.map((run) => [run.profile_id || "", run]));
  const runLedgerPreviews = executionRunRecords
    .map((run) => run.runtime_binding_snapshot?.shared_symbol_ledger_preview ?? null)
    .filter((item): item is ExecutionRunLedgerPreview => Boolean(item));
  const totalUnrealizedPnl = runLedgerPreviews.reduce((sum, item) => sum + (typeof item.unrealized_pnl === "number" ? item.unrealized_pnl : 0), 0);
  const totalCapitalInUse = runLedgerPreviews.reduce((sum, item) => sum + (typeof item.capital_in_use === "number" ? item.capital_in_use : 0), 0);
  const profitableRuns = executionRunRecords.filter((run) => (run.runtime_binding_snapshot?.shared_symbol_ledger_preview?.unrealized_pnl ?? 0) > 0).length;
  const deployableCapital = executionCapitalPlan?.deployable_capital ?? balanceFree;
  const hasBlockedState = !runtimeStatusPending && !executionSurfaceContract?.live_ready;
  const breakerRelease = liveRuntimeTruth?.deployment_blocker_details?.release_condition ?? null;
  const breakerRecentWindowDetails = liveRuntimeTruth?.deployment_blocker_details?.recent_window ?? null;
  const circuitBreakerActive = liveRuntimeTruth?.deployment_blocker === "circuit_breaker_active";
  const breakerRecentWindow = typeof breakerRelease?.recent_window === "number"
    ? breakerRelease.recent_window
    : (typeof breakerRecentWindowDetails?.window_size === "number" ? breakerRecentWindowDetails.window_size : null);
  const breakerWins = typeof breakerRelease?.current_recent_window_wins === "number"
    ? breakerRelease.current_recent_window_wins
    : (typeof breakerRecentWindowDetails?.wins === "number" ? breakerRecentWindowDetails.wins : null);
  const breakerRequiredWins = typeof breakerRelease?.required_recent_window_wins === "number"
    ? breakerRelease.required_recent_window_wins
    : null;
  const breakerWinsGap = typeof breakerRelease?.additional_recent_window_wins_needed === "number"
    ? breakerRelease.additional_recent_window_wins_needed
    : null;
  const breakerStreakLimit = typeof breakerRelease?.streak_must_be_below === "number"
    ? breakerRelease.streak_must_be_below
    : null;
  const breakerCurrentStreak = typeof breakerRelease?.current_streak === "number"
    ? breakerRelease.current_streak
    : null;
  const breakerReleaseSummaryLabel = circuitBreakerActive
    ? `金字塔 24h 熔斷：目前 ${breakerWins ?? "—"}/${breakerRecentWindow ?? 50} 勝，還差 ${breakerWinsGap ?? "—"} 勝；連敗 ${breakerCurrentStreak ?? "—"}/${breakerStreakLimit ?? 50}`
    : "目前沒有熔斷解除條件阻塞。";
  const currentLiveSupportScopeLabel = runtimeStatusPending
    ? "當前分桶"
    : humanizeCurrentLiveSupportScopeLabel(
      liveRuntimeTruth?.current_live_structure_bucket
      || liveRouting?.current_structure_bucket
      || liveRuntimeTruth?.structure_bucket
      || null,
    );
  const breakerSupportCaveatLabel = `${currentLiveSupportScopeLabel}支持樣本 / 候選修補不可取代熔斷解除條件。`;
  const rawPrimaryBlockedReason = liveRuntimeTruth?.deployment_blocker_reason
    || liveRuntimeTruth?.deployment_blocker
    || liveRuntimeTruth?.execution_guardrail_reason
    || liveReadyBlockers[0]
    || executionSurfaceContract?.operator_message
    || null;
  const primaryBlockedReason = runtimeStatusPending ? "正在同步 /api/status" : humanizeExecutionReason(rawPrimaryBlockedReason);
  const blockedReasonSummary = runtimeStatusPending
    ? "正在同步 /api/status"
    : (Array.from(new Set([
      rawPrimaryBlockedReason,
      ...liveReadyBlockers,
    ]
      .map((item) => humanizeExecutionReason(item))
      .filter((item) => item && item !== "尚未提供阻塞點摘要。")))
      .join(" · ") || primaryBlockedReason);
  const automationEnabled = Boolean(runtimeStatus?.automation);
  const manualBuyBlocked = runtimeStatusPending || hasBlockedState;
  const automationEnableBlocked = runtimeStatusPending || (hasBlockedState && !automationEnabled);
  const manualBuyBlockedMessage = runtimeStatusPending
    ? "正在同步 /api/status：買入與啟用自動模式暫停；減碼 / 賣出風險降低路徑 / 查看阻塞原因仍可使用。"
    : manualBuyBlocked
      ? "目前即時阻塞點啟動中：買入指令暫停；減碼 / 賣出風險降低路徑 / 模式切換 / 查看阻塞原因仍可使用。"
      : null;
  const operatorShortcutBlockedMessage = manualBuyBlockedMessage;
  const deploymentStatusLabel = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");
  const deploymentStatusDetail = runtimeStatusPending
    ? "正在向 /api/status 取得目前阻塞點 / 部署閉環摘要。"
    : humanizeRuntimeDetailText(
      executionSurfaceContract?.live_ready
        ? (liveRuntimeTruth?.runtime_closure_summary || executionSurfaceContract?.operator_message || "目前已滿足主要部署條件。")
        : (liveRuntimeTruth?.runtime_closure_summary || liveRuntimeTruth?.deployment_blocker_reason || primaryBlockedReason)
    );
  const dryRunEnabled = Boolean(runtimeStatus?.dry_run);
  const executionSymbol = runtimeStatus?.symbol || "BTCUSDT";
  const executionModeRaw = executionSummary?.mode || (dryRunEnabled ? "dry_run" : "paper");
  const executionModeLabel = runtimeStatusPending ? "同步中" : humanizeExecutionModeLabel(executionModeRaw);
  const executionVenueLabel = runtimeStatusPending ? "同步中" : humanizeExecutionVenueLabel(executionSummary?.venue || "unknown");
  const automationStatusLabel = runtimeStatusPending ? "自動交易同步中" : `自動交易 ${automationEnabled ? "開啟" : "關閉"}`;
  const operatorQuickCommands = [
    { label: "Paper 買入 0.001 BTC", disabled: operatorActionState.tone === "pending" },
    { label: manualBuyBlocked ? "買入暫停" : "買入 0.001 BTC", disabled: operatorActionState.tone === "pending" || manualBuyBlocked },
    { label: "減碼 0.001 BTC", disabled: operatorActionState.tone === "pending" },
    { label: "等待 / 觀望", disabled: operatorActionState.tone === "pending" },
    { label: automationEnableBlocked ? "自動模式暫停" : (automationEnabled ? "切到手動模式" : "切到自動模式"), disabled: operatorActionState.tone === "pending" || automationEnableBlocked },
    { label: "查看阻塞原因", disabled: operatorActionState.tone === "pending" },
    { label: "重新整理", disabled: operatorActionState.tone === "pending" },
  ];
  const liveReadyStatusLabel = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");
  const balanceTotalLabel = runtimeStatusPending
    ? "同步中"
    : (balanceTotal !== null ? `${formatNumber(balanceTotal)} ${balanceCurrency}` : accountSnapshotUnavailableLabel);
  const balanceBreakdownLabel = runtimeStatusPending
    ? "正在向 /api/status 取得帳戶快照。"
    : (balanceFree !== null && allocatedCapital !== null
      ? `可用 ${formatNumber(balanceFree)} · 已分配 ${formatNumber(allocatedCapital)}`
      : accountSnapshotUnavailableReason);
  const sharedPnlLabel = runsPending
    ? `同步中 ${balanceCurrency}`
    : (runLedgerPreviews.length > 0 ? `${formatSignedNumber(totalUnrealizedPnl)} ${balanceCurrency}` : sharedLedgerUnavailableLabel);
  const sharedPnlSummaryLabel = runsPending
    ? "正在向 /api/execution/runs 取得共享盈虧預覽。"
    : (runLedgerPreviews.length > 0 ? `共享帳戶預覽 · ${executionRunRecords.length} 條運行` : "先啟動運行才會顯示共享盈虧預覽");
  const capitalInUseLabel = executionConsoleInitialSyncPending
    ? `同步中 ${balanceCurrency}`
    : (runLedgerPreviews.length > 0
      ? `${formatNumber(totalCapitalInUse)} ${balanceCurrency}`
      : (allocatedCapital !== null ? `${formatNumber(allocatedCapital)} ${balanceCurrency}` : sharedLedgerUnavailableLabel));
  const capitalInUseSummaryLabel = executionConsoleInitialSyncPending
    ? "正在同步共享帳戶預覽 / 預算。"
      : (runLedgerPreviews.length > 0
      ? "依目前共享帳戶預覽匯總"
      : (allocatedCapital !== null ? "暫以帳戶已分配資金表示" : "先啟動運行；若要顯示共享資金占用仍需私有餘額。"));
  const deployableCapitalLabel = overviewPending || runtimeStatusPending
    ? `同步中 ${balanceCurrency}`
    : (deployableCapital !== null ? `${formatNumber(deployableCapital)} ${balanceCurrency}` : accountBalanceUnavailableLabel);
  const allocationRuleLabel = humanizeExecutionOperatorLabel(
    executionCapitalPlan?.allocation_rule || executionOverviewSummary?.allocation_rule,
    "allocation_rule",
  ) || "啟用倉位腿均分";
  const deployableCapitalSummaryLabel = overviewPending || runtimeStatusPending
    ? "正在向 /api/status 與 /api/execution/overview 取得可部署資金。"
    : (deployableCapital !== null
      ? `資金分配 ${allocationRuleLabel}`
      : `${accountBalanceUnavailableReason}${hasBlockedState ? " 阻塞點解除後才會得到真正可部署資金。" : ""}`);
  const configuredSleeveCount = executionStrategySummary?.total_sleeves ?? executionOverviewSummary?.total_profiles ?? executionProfileCards.length;
  const sleeveLabelById = new Map<string, string>();
  executionProfileCards.forEach((card) => {
    const label = String(card.label || card.key || card.profile_id || "").trim();
    if (!label) return;
    if (card.profile_id) sleeveLabelById.set(card.profile_id, label);
    if (card.key) sleeveLabelById.set(card.key, label);
  });
  const missingSleeveLabels = (executionStrategySummary?.missing_sleeves || [])
    .map((value) => sleeveLabelById.get(value) || humanizeRuntimeDetailText(value) || value)
    .filter((value): value is string => Boolean(value));
  const runningRunsLabel = runsPending ? "同步中" : String(executionRunsSummary?.running_runs ?? 0);
  const workerOutcomeProofLoading = workerOutcomesLoading && !workerOutcomes && !workerOutcomesError;
  const workerPollPendingGuardActive = Boolean(workerRehearsalProof?.poll_blocked_by_pending_outcome);
  const workerPollAvailable = Boolean(
    workerRehearsalProof?.can_poll_workers
    ?? (!workerOutcomeProofLoading && !workerPollPendingGuardActive && ((executionRunsSummary?.running_runs ?? 0) > 0))
  );
  const workerPollDisabledReason = workerOutcomeProofLoading
    ? "正在同步 paper/shadow outcome proof；同步完成前先不重複 poll。"
    : workerPollPendingGuardActive
      ? `24h outcome 觀察窗尚未到期；${workerOutcomeEtaLabel}`
      : workerRehearsalProof?.can_poll_workers === false
        ? workerOutcomeNextActionLabel
        : ((executionRunsSummary?.running_runs ?? 0) <= 0 ? "目前沒有 running run 可供 worker poll。" : "");
  const runningRunsSummaryLabel = runsPending
    ? "正在向 /api/execution/runs 取得運行控制 / 事件。"
    : `運行中 ${executionRunsSummary?.running_runs ?? 0} · 獲利中 ${profitableRuns} · 總計 ${executionRunsSummary?.total_runs ?? executionRunRecords.length} · 已配置倉位腿 ${configuredSleeveCount}`;
  const executionStrategySummaryLabel = overviewPending
    ? "正在向 /api/execution/overview 取得策略 / 倉位腿覆蓋。"
    : `已儲存策略 ${executionStrategySummary?.strategy_count ?? 0} · 已覆蓋倉位腿 ${executionStrategySummary?.covered_sleeves ?? 0}/${executionStrategySummary?.total_sleeves ?? 0} · 缺 ${missingSleeveLabels.join(" / ") || "無"}`;
  const executionProfileCardsEmptyState = overviewPending
    ? "正在向 /api/execution/overview 取得 Bot 卡片。"
    : "尚未取得 Bot 卡片；先確認 /api/execution/overview 是否可用。";
  const executionRunsEmptyState = runsPending
    ? "正在向 /api/execution/runs 取得運行控制 / 事件。"
    : "尚未建立可持久化運行；先在上方 Bot 卡啟動，這裡才會出現事件與狀態。";
  const liveReadinessSummary = runtimeStatusPending
    ? "正在向 /api/status 取得部署狀態。"
    : humanizeExecutionReason(
      liveRuntimeTruth?.deployment_blocker_reason
      || liveRuntimeTruth?.deployment_blocker
      || liveRuntimeTruth?.execution_guardrail_reason
      || executionSurfaceContract?.operator_message
      || "尚未提供部署狀態訊息。"
    );
  const runActionTone = runActionState.tone === "success"
    ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-100"
    : runActionState.tone === "warning"
      ? "border-amber-500/20 bg-amber-500/10 text-amber-100"
    : runActionState.tone === "error"
      ? "border-rose-500/20 bg-rose-500/10 text-rose-100"
      : "border-cyan-500/20 bg-cyan-500/10 text-cyan-100";
  const operatorActionTone = operatorActionState.tone === "success"
    ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-100"
    : operatorActionState.tone === "error"
      ? "border-rose-500/20 bg-rose-500/10 text-rose-100"
      : "border-cyan-500/20 bg-cyan-500/10 text-cyan-100";

  const handleOperatorTrade = async (side: "buy" | "paper_buy" | "reduce" | "wait", qty = 0.001) => {
    const paperBuy = side === "paper_buy";
    const label = paperBuy ? "Paper 買入" : (side === "buy" ? "買入" : (side === "wait" ? "等待 / 觀望" : "減碼"));
    if (side === "buy" && manualBuyBlocked) {
      setOperatorActionState({
        tone: "error",
        message: manualBuyBlockedMessage || "目前即時阻塞點啟動中：買入指令暫停；減碼 / 賣出風險降低路徑 / 模式切換 / 查看阻塞原因仍可使用。",
      });
      return;
    }
    const normalizedQty = Number.isFinite(qty) && qty > 0 ? qty : 0.001;
    setOperatorActionState({
      tone: "pending",
      message: side === "wait"
        ? `${label} 指令記錄中… 不送單，只同步 ${executionSymbol} 的執行狀態。`
        : (paperBuy
          ? `${label} 指令送出中… ${executionSymbol} 只送 paper/shadow 到 /api/trade，數量 ${formatNumber(normalizedQty, 6)}；不送 OKX live 買入。`
          : `${label} 指令送出中… ${executionSymbol} 會送到 /api/trade，數量 ${formatNumber(normalizedQty, 6)}，完成後自動刷新 runtime。`),
    });
    try {
      const resp = await fetchApi<any>("/api/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ side, symbol: executionSymbol, qty: normalizedQty }),
      });
      await refreshRuntimeStatus();
      const order = resp?.order ?? null;
      const normalization = resp?.normalization ?? null;
      const normalizedQtyFromContract = typeof normalization?.normalized?.qty === "number" ? normalization.normalized.qty : (typeof order?.qty === "number" ? order.qty : null);
      const normalizedPrice = typeof normalization?.normalized?.price === "number" ? normalization.normalized.price : null;
      const stepSize = normalization?.contract?.step_size;
      const tickSize = normalization?.contract?.tick_size;
      const contractSummary = [
        stepSize != null ? `數量步進 ${formatNumber(Number(stepSize), 6)}` : null,
        tickSize != null ? `價格刻度 ${formatNumber(Number(tickSize), 6)}` : null,
      ].filter(Boolean).join(" · ");
      const orderModeLabel = humanizeExecutionModeLabel(order?.mode || (resp?.dry_run ? "dry_run" : executionModeRaw));
      const orderVenueLabel = humanizeExecutionVenueLabel(resp?.venue || executionSummary?.venue || executionVenueLabel);
      if (side === "wait" || resp?.no_order_submitted) {
        setOperatorActionState({
          tone: "success",
          message: resp?.operator_message || "已切到等待 / 觀望：沒有送出 OKX 委託；請持續看執行狀態頁的阻塞點與解除條件。",
        });
        return;
      }
      if (resp?.shadow_trade) {
        setOperatorActionState({
          tone: "success",
          message: resp?.operator_message || `${label} 已提交 paper/shadow 委託；真實買入仍需 current-live support、場館生命週期與 bounded canary gate 通過。`,
        });
        return;
      }
      setOperatorActionState({
        tone: "success",
        message: `${label} 已提交：模式 ${orderModeLabel} · 場館 ${orderVenueLabel}${normalizedQtyFromContract != null ? ` · 校準後數量 ${formatNumber(normalizedQtyFromContract, 6)}` : ""}${normalizedPrice != null ? ` · 校準後價格 ${formatNumber(normalizedPrice, 2)}` : ""}${contractSummary ? ` · 規則 ${contractSummary}` : ""}`,
      });
    } catch (err: any) {
      await refreshRuntimeStatus();
      setOperatorActionState({
        tone: "error",
        message: `${label} 指令失敗：${err?.message || "未知錯誤"}`,
      });
    }
  };

  const handleAutomationToggle = async (enabled: boolean) => {
    if (enabled && automationEnableBlocked) {
      setOperatorActionState({
        tone: "error",
        message: operatorShortcutBlockedMessage || "目前阻塞點啟動中：自動模式切換暫停；請先查看阻塞原因。",
      });
      return;
    }
    setOperatorActionState({
      tone: "pending",
      message: `${enabled ? "切換至自動" : "切換至手動"}模式中…`,
    });
    try {
      const resp = await fetchApi<{ automation?: boolean; message?: string }>("/api/automation/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      await refreshRuntimeStatus();
      setOperatorActionState({
        tone: "success",
        message: resp.message || `目前已是${resp.automation ? "自動" : "手動"}模式`,
      });
    } catch (err: any) {
      await refreshRuntimeStatus();
      setOperatorActionState({
        tone: "error",
        message: `模式切換失敗：${err?.message || "未知錯誤"}`,
      });
    }
  };

  const handleNaturalLanguageAction = async (rawCommand?: string) => {
    const command = String(rawCommand ?? naturalCommand).trim();
    if (!command) {
      setOperatorActionState({
        tone: "error",
        message: "請直接輸入自然語句，例如：買 0.001 BTC、減碼 0.001、等待 / 觀望、切到自動、查看阻塞原因。",
      });
      return;
    }

    setNaturalCommand("");

    if (/(查看|前往).*(阻塞|診斷|狀態)|execution\s*status|blocker/i.test(command)) {
      setOperatorActionState({
        tone: "success",
        message: "已導向執行狀態頁，請先看阻塞點 / 新鮮度 / 恢復。",
      });
      window.location.href = "/execution/status";
      return;
    }

    if (/(策略|實驗室|lab)/i.test(command) && /(前往|打開|開|去)/i.test(command)) {
      setOperatorActionState({
        tone: "success",
        message: "已導向策略實驗室。",
      });
      window.location.href = "/lab";
      return;
    }

    if (/(刷新|重新整理|同步|reload|refresh)/i.test(command)) {
      setOperatorActionState({
        tone: "pending",
        message: "正在同步 Bot 營運頁面…",
      });
      try {
        await refreshExecutionWorkspace();
        setOperatorActionState({
          tone: "success",
          message: "已重新整理 Bot 營運、運行控制與執行狀態。",
        });
      } catch (err: any) {
        setOperatorActionState({
          tone: "error",
          message: `重新整理失敗：${err?.message || "未知錯誤"}`,
        });
      }
      return;
    }

    if (/(切|開|改).*(自動)|自動模式|automation\s*on/i.test(command)) {
      await handleAutomationToggle(true);
      return;
    }

    if (/(切|關|改).*(手動)|關自動|手動模式|automation\s*off/i.test(command)) {
      await handleAutomationToggle(false);
      return;
    }

    if (/(等待|觀望|先等|wait|hold)/i.test(command)) {
      await handleOperatorTrade("wait");
      return;
    }

    const qtyMatch = command.match(/([0-9]+(?:\.[0-9]+)?)/);
    const qty = qtyMatch ? Number(qtyMatch[1]) : 0.001;

    if (/(減碼|賣|平倉|reduce|sell)/i.test(command)) {
      await handleOperatorTrade("reduce", qty);
      return;
    }

    if (/(paper|shadow|模擬|影子|演練).*(買入|買|加碼|buy)|(買入|買|加碼|buy).*(paper|shadow|模擬|影子|演練)/i.test(command)) {
      await handleOperatorTrade("paper_buy", qty);
      return;
    }

    if (/(買入|買|加碼|buy)/i.test(command)) {
      await handleOperatorTrade("buy", qty);
      return;
    }

    setOperatorActionState({
      tone: "error",
      message: "暫時支援：Paper 買入 / 減碼 / 等待或觀望 / 切到自動 / 切到手動 / 查看阻塞原因 / 前往策略實驗室 / 重新整理。真實買入需先解除阻塞。",
    });
  };

  return (
    <div className="execution-shell app-page-shell text-white">
      <ExecutionHero
        className="app-page-header"
        eyebrow="Bot 營運 / 執行工作台"
        title="先看我的 Bot、資金使用與盈虧預覽"
        subtitle="主頁只放營運關鍵：Bot 狀態、資金、盈虧；診斷與恢復集中到「執行狀態」。"
        statusPills={(
          <>
            <ExecutionPill>{executionModeLabel}</ExecutionPill>
            <ExecutionPill>{executionVenueLabel}</ExecutionPill>
            <ExecutionPill className={getStatusTone(runtimeStatusPending ? "pending" : (automationEnabled ? "ok" : "warning"))}>
              {automationStatusLabel}
            </ExecutionPill>
            <ExecutionPill className={getStatusTone(runtimeStatusPending ? "pending" : (executionSurfaceContract?.live_ready ? "ok" : "blocked"))}>
              {liveReadyStatusLabel}
            </ExecutionPill>
            <ExecutionPill className={getStatusTone(metadataSmokeFreshness?.status)}>
              新鮮度 {metadataSmokeFreshnessLabel}
            </ExecutionPill>
          </>
        )}
        actions={(
          <>
            <button
              type="button"
              onClick={() => refreshExecutionWorkspace()}
              className="app-button-primary"
            >
              重新整理
            </button>
            <a href="/lab" className="app-button-secondary">
              選策略
            </a>
            <a href="/execution/status" className="app-button-secondary">
              執行狀態
            </a>
          </>
        )}
      >
        {executionSurfaceContract?.operator_message && !hasBlockedState && (
          <div className="rounded-2xl border border-white/8 bg-white/5 px-4 py-3 text-sm text-slate-200">
            {executionSurfaceContract.operator_message}
          </div>
        )}
        {(loading || error) && (
          <div className="rounded-2xl border border-white/8 bg-[#0d1324] px-4 py-3 text-sm text-slate-300">
            {loading ? "/api/status 載入中…" : `載入失敗：${error}`}
          </div>
        )}
        {runActionState.tone !== "idle" && runActionState.message && (
          <div className={`rounded-2xl border px-4 py-3 text-sm ${runActionTone}`}>
            {runActionState.message}
          </div>
        )}
        {hasBlockedState && (
          <div className="rounded-[24px] border border-amber-400/30 bg-[linear-gradient(135deg,rgba(245,158,11,0.18),rgba(113,50,245,0.14))] p-4 shadow-[0_18px_40px_rgba(245,158,11,0.12)]">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-200/80">阻塞中</div>
                <div className="mt-2 text-lg font-semibold text-amber-50">先解除阻塞點，再做操作</div>
                <div className="mt-1 text-sm text-amber-100/90">{primaryBlockedReason}</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <a href="/execution/status" className="rounded-xl bg-amber-300 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-amber-200">
                  查看阻塞原因
                </a>
                <button
                  type="button"
                  onClick={() => refreshExecutionWorkspace()}
                  className="app-button-secondary"
                >
                  重新整理
                </button>
              </div>
            </div>
          </div>
        )}
        {rangeChopPlaybookVisible && (
          <div className="rounded-[24px] border border-cyan-400/25 bg-[linear-gradient(135deg,rgba(34,211,238,0.14),rgba(124,58,237,0.14))] p-4 shadow-[0_18px_40px_rgba(34,211,238,0.10)]">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="text-[11px] font-semibold tracking-[0.22em] text-cyan-200/80">高低震盪實戰拆解</div>
                <div className="mt-2 text-lg font-semibold text-cyan-50">震盪不是停工，也不是永遠不能實戰</div>
                <div className="mt-1 text-sm text-cyan-100/90">{rangeChopOperatorMessageLabel}</div>
                <div className="mt-2 text-xs text-cyan-100/75">{rangeChopNextActionLabel}</div>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-full border border-purple-400/30 bg-purple-400/10 px-3 py-1 text-purple-100">影子觀察 / 減風險先行</span>
                <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-emerald-100">
                  {rangeChopPlaybook?.risk_reduction_allowed ? "減碼 / 取消掛單允許" : "等待減風險檢查"}
                </span>
                <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-amber-100">
                  {rangeChopPlaybook?.buy_add_requires_current_live_gate ? "買入 / 加倉仍需即時部署門檻" : "買入門檻未回報"}
                </span>
                <span className="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-slate-200">{rangeChopSupportSummaryLabel}</span>
              </div>
            </div>
            <div className="mt-3 text-xs text-cyan-100/70">買入 / 加倉仍等即時部署門檻；影子觀察只收集執行期證據，不送單。</div>
          </div>
        )}
      </ExecutionHero>

      <ExecutionSectionCard
        title="實戰準備度"
        subtitle="Shadow / Reduce-only：買入 / 加倉仍鎖住；影子觀察、減風險與 venue proof 今天可以前進。"
        aside={<ExecutionPill className={getStatusTone(readinessStatusTone)}>{readinessStageLabel}</ExecutionPill>}
      >
        <div className="grid gap-3 xl:grid-cols-[1.2fr_0.9fr_0.9fr]">
          <div className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.03] p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-white">Gate stack</div>
                <div className="mt-1 text-xs text-slate-400">哪一個 gate 卡住：{readinessBlockingGateLabel}</div>
              </div>
              <ExecutionPill className={getStatusTone(readinessStatusTone)}>
                {executionReadiness?.canary_ready ? "Canary ready" : "買入 / 加倉仍鎖住"}
              </ExecutionPill>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {[
                readinessGateByKey.get("model_gate") || { label: "模型 gate", summary: "同步中" },
                readinessGateByKey.get("current_lane_actionability_gate") || { label: "當前 lane 可行動 gate", summary: "同步中" },
                readinessGateByKey.get("current_live_support_gate") || { label: "即時支持 gate", summary: "同步中" },
                readinessGateByKey.get("circuit_breaker_gate") || { label: "熔斷 gate", summary: "同步中" },
                readinessGateByKey.get("venue_gate") || { label: "場館 gate", summary: "同步中" },
                readinessGateByKey.get("live_canary_policy_gate") || { label: "Live-canary policy gate", summary: "同步中" },
                readinessGateByKey.get("shadow_observation_gate") || { label: "影子觀察 gate", summary: "同步中" },
              ].map((gate) => (
                <div key={gate.label || gate.key} className="rounded-xl border border-white/8 bg-[#0d1324] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-xs font-semibold text-slate-100">{gate.label}</div>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] ${getStatusTone(gate.passed ? "ok" : gate.status === "ready" || gate.status === "shadow_ready" ? "warning" : "blocked")}`}>
                      {gate.status || (gate.passed ? "passed" : "blocked")}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-slate-400">{humanizeRuntimeDetailText(gate.summary || gate.next_action || "同步中")}</div>
                  {Array.isArray(gate.sub_gates) && gate.sub_gates.length > 0 && (
                    <div className="mt-2 space-y-1 rounded-lg border border-cyan-300/10 bg-cyan-300/5 p-2 text-[11px] text-cyan-100/80">
                      <div className="font-semibold text-cyan-50">sub-gates：strict exact / shadow evidence / cost-aware edge</div>
                      {gate.sub_gates.map((subGate) => (
                        <div key={subGate.key || subGate.label || "subgate"} className="flex flex-wrap items-center justify-between gap-2">
                          <span>{subGate.label || subGate.key}</span>
                          <span className="text-cyan-100/65">{subGate.status || (subGate.passed ? "passed" : "blocked")}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {(typeof gate.current === "number" || typeof gate.required === "number" || typeof gate.gap === "number") && (
                    <div className="mt-2 text-[11px] text-slate-500">{gate.current ?? "—"} / {gate.required ?? "—"} · 缺 {gate.gap ?? "—"}</div>
                  )}
                  {gate.release_evidence_lane && (
                    <div className="mt-2 rounded-lg border border-amber-300/15 bg-amber-300/5 p-2 text-[11px] text-amber-100/85">
                      <div>release evidence：{gate.release_evidence_lane.status || "同步中"} · 還差 {gate.release_evidence_lane.wins_needed ?? gate.gap ?? "—"} 勝</div>
                      <div className="mt-1 text-amber-100/65">artifact：{gate.release_evidence_lane.next_validation_artifact || gate.next_validation_artifact || "data/circuit_breaker_audit.json"}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            {milestoneProgression && (
              <div className="rounded-xl border border-cyan-400/20 bg-cyan-400/8 p-3 text-xs text-cyan-100">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="font-semibold">MILESTONE progression / 不卡死路由</div>
                    <div className="mt-1 text-cyan-100/75">{humanizeRuntimeDetailText(milestoneProgression.operator_message || milestoneProgression.auto_adjustment_reason || "live gate 未全過時自動轉入安全實戰 lane。")}</div>
                  </div>
                  <span className="rounded-full border border-cyan-300/30 bg-black/20 px-2 py-0.5 text-[10px] text-cyan-50">
                    {milestoneProgression.active_lane_label || milestoneProgression.active_lane || "safe lane"}
                  </span>
                </div>
                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  <div className="rounded-lg border border-cyan-300/15 bg-black/20 p-2">
                    <div className="font-semibold text-cyan-50">程式現在要進入哪裡</div>
                    <div className="mt-1 text-cyan-100/80">
                      {milestonePreferredEndpoint || milestonePreferredCommand || "等待 preferred entrypoint"}
                      {milestonePreferredSide ? ` · side=${milestonePreferredSide}` : ""}
                      {typeof milestonePreferredQty === "number" ? ` · qty=${milestonePreferredQty}` : ""}
                    </div>
                  </div>
                  <div className="rounded-lg border border-cyan-300/15 bg-black/20 p-2">
                    <div className="font-semibold text-cyan-50">可切換的安全 lane</div>
                    <ul className="mt-1 list-disc space-y-1 pl-4 text-cyan-100/80">
                      {milestoneVisibleLanes.map((lane) => {
                        const laneKey = typeof lane.key === "string" ? lane.key : String(lane.label || "lane");
                        const laneLabel = typeof lane.label === "string" ? lane.label : laneKey;
                        const canEnter = lane.can_enter === true ? "可進入" : "等待 gate";
                        return <li key={laneKey}>{laneLabel}：{canEnter}</li>;
                      })}
                    </ul>
                  </div>
                </div>
              </div>
            )}
            <div className="grid gap-2 md:grid-cols-2">
              <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/8 p-3 text-xs text-emerald-100">
                <div className="font-semibold">現在可以做什麼</div>
                <ul className="mt-2 list-disc space-y-1 pl-4">
                  {(readinessCanDo.length ? readinessCanDo : ["影子觀察 / 減風險演練", "Venue dry-run proof 不送單"]).map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
              <div className="rounded-xl border border-amber-400/20 bg-amber-400/8 p-3 text-xs text-amber-100">
                <div className="font-semibold">現在不能做什麼</div>
                <ul className="mt-2 list-disc space-y-1 pl-4">
                  {(readinessCannotDo.length ? readinessCannotDo : ["買入 / 加倉仍鎖住", "不送單、不把候選標成可部署"]).map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
            </div>
          </div>

          <div className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.03] p-4">
            <div>
              <div className="text-sm font-semibold text-white">Shadow Trade Ledger</div>
              <div className="mt-1 text-xs text-slate-400">每個影子訊號記錄 signal time / model / confidence / regime / 假想 entry / 24h 結果 / pyramid win；不送單。</div>
            </div>
            <div className="rounded-xl border border-white/8 bg-[#0d1324] p-3 text-xs text-slate-300">
              <div className="flex items-center justify-between gap-2">
                <span>candidate model</span>
                <span className="text-white">{firstShadowLedgerEntry?.candidate_model || "等待候選"}</span>
              </div>
              <div className="mt-2 grid gap-2 text-[11px] text-slate-400">
                <div>訊號時間：{formatTime(firstShadowLedgerEntry?.signal_time)}</div>
                <div>confidence：{formatPercent(firstShadowLedgerEntry?.confidence, 1)}</div>
                <div>regime：{humanizeRuntimeDetailText(firstShadowLedgerEntry?.regime || "同步中")}</div>
                <div>假想 entry：{firstShadowLedgerEntry?.hypothetical_entry?.operator_copy || "只記錄，不送單"}</div>
                <div>24h 結果：{firstShadowLedgerEntry?.outcome_24h?.status || "pending"}</div>
                <div>pyramid win：{typeof firstShadowLedgerEntry?.pyramid_win === "boolean" ? (firstShadowLedgerEntry.pyramid_win ? "符合" : "不符合") : "待 24h"}</div>
              </div>
            </div>
            <div className="text-xs text-slate-500">{shadowTradeLedger?.operator_message || "Shadow ledger 是觀察帳本，不是委託帳本。"}</div>
          </div>

          <div className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.03] p-4">
            <div>
              <div className="text-sm font-semibold text-white">Venue dry-run proof</div>
              <div className="mt-1 text-xs text-slate-400">credential present 只顯示布林 / 狀態；order preview、ack simulation、cancel simulation、fill simulation、reconciliation check 都不得輸出 secret。</div>
            </div>
            <div className="space-y-2">
              {venueProofChecks.map((check) => (
                <div key={check.label} className="flex items-center justify-between gap-2 rounded-xl border border-white/8 bg-[#0d1324] px-3 py-2 text-xs">
                  <span className="text-slate-400">{check.label}</span>
                  <span className="text-slate-100">{humanizeRuntimeDetailText(check.value)}</span>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-purple-400/20 bg-purple-400/8 p-3 text-xs text-purple-100">
              <div className="font-semibold">目前距離 canary 還差什麼</div>
              <ul className="mt-2 list-disc space-y-1 pl-4">
                {(canaryDistance.length ? canaryDistance : ["等待即時支持、熔斷與場館 gate 全過"]).map((item) => <li key={item}>{humanizeRuntimeDetailText(item)}</li>)}
              </ul>
            </div>
            <div className="rounded-xl border border-amber-400/20 bg-amber-400/8 p-3 text-xs text-amber-100">
              <div className="flex items-center justify-between gap-2">
                <div className="font-semibold">time-to-evidence / 替代解法評審</div>
                <span className="rounded-full border border-white/10 bg-black/20 px-2 py-0.5 text-[10px]">
                  {alternativeSolutionReview?.status || "watch_only"}
                </span>
              </div>
              <div className="mt-2 text-amber-50">{timeToEvidenceEtaLabel}</div>
              <div className="mt-1 text-amber-100/80">{humanizeRuntimeDetailText(timeToEvidence?.operator_message || timeToEvidence?.summary || "等待支持增量估算。")}</div>
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                <div>
                  <div className="font-semibold">替代解法今天可前進</div>
                  <ul className="mt-1 list-disc space-y-1 pl-4">
                    {(alternativeSolutionAllowed.length ? alternativeSolutionAllowed : ["paper-shadow", "減風險路徑", "venue proof"]).map((item) => <li key={item}>{humanizeRuntimeDetailText(item)}</li>)}
                  </ul>
                </div>
                <div>
                  <div className="font-semibold">仍然不可做</div>
                  <ul className="mt-1 list-disc space-y-1 pl-4">
                    {(alternativeSolutionNotAllowed.length ? alternativeSolutionNotAllowed : ["買入 / 加倉", "把舊語義支持當部署閉環"]).map((item) => <li key={item}>{humanizeRuntimeDetailText(item)}</li>)}
                  </ul>
                </div>
              </div>
            </div>
            <div className="rounded-xl border border-cyan-400/20 bg-cyan-400/8 p-3 text-xs text-cyan-100">
              <div className="font-semibold">今天可以演練什麼</div>
              <ul className="mt-2 list-disc space-y-1 pl-4">
                {(canaryDrills.length ? canaryDrills : ["order preview / ack simulation / cancel simulation / fill simulation / reconciliation check"]).map((item) => <li key={item}>{humanizeRuntimeDetailText(item)}</li>)}
              </ul>
            </div>
            <div className="text-xs text-slate-400">
              如果 gate 全過，第一筆 canary 如何執行：{formatPercent(canaryPlan?.exposure_pct_max, 1)} 上限，{canaryPlan?.pyramid_layer || "20% first layer only"}，add exposure {canaryPlan?.add_exposure_enabled ? "允許" : "不允許"}。
            </div>
          </div>
        </div>
      </ExecutionSectionCard>

      <section className={`rounded-[24px] border p-4 text-xs ${shadowEvidenceDaemonTone}`}>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="text-sm font-semibold text-white">Shadow evidence daemon</div>
            <div className="mt-1 text-cyan-100/85">{shadowEvidenceDaemonStatusLabel} · {shadowEvidenceDaemonDetailLabel}</div>
            <div className="mt-2 text-[11px] text-slate-400">最新 decision：{shadowEvidenceDaemonLatestLabel}</div>
          </div>
          <div className="flex flex-wrap gap-2 text-[11px]">
            <span className="rounded-full border border-white/10 bg-black/20 px-2 py-0.5">{shadowEvidenceDaemonCountsLabel}</span>
            <span className="rounded-full border border-white/10 bg-black/20 px-2 py-0.5">{shadowEvidenceDaemonOutcomeLabel}</span>
            <span className="rounded-full border border-white/10 bg-black/20 px-2 py-0.5">{shadowEvidenceDaemonReviewLabel}</span>
            <span className="rounded-full border border-emerald-400/25 bg-emerald-400/10 px-2 py-0.5 text-emerald-100">
              {shadowEvidenceDaemonGuardrail?.live_order_submitted ? "⚠️ live order detected" : "Fail-closed · 不送單"}
            </span>
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <ExecutionMetricCard
          title="資產總覽"
          value={balanceTotalLabel}
          detail={balanceBreakdownLabel}
        />
        <ExecutionMetricCard
          title="共享盈虧預覽"
          value={sharedPnlLabel}
          detail={sharedPnlSummaryLabel}
          toneClass={totalUnrealizedPnl > 0 ? "text-emerald-300" : totalUnrealizedPnl < 0 ? "text-rose-300" : "text-white"}
        />
        <ExecutionMetricCard
          title="資金使用中"
          value={capitalInUseLabel}
          detail={capitalInUseSummaryLabel}
        />
        <ExecutionMetricCard
          title="可部署資金"
          value={deployableCapitalLabel}
          detail={deployableCapitalSummaryLabel}
        />
        <ExecutionMetricCard
          title="運行中 Bot"
          value={runningRunsLabel}
          detail={runningRunsSummaryLabel}
        />
        <ExecutionMetricCard
          title="部署狀態"
          value={deploymentStatusLabel}
          detail={deploymentStatusDetail}
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.55fr_0.95fr]">
        <div className="space-y-4">
          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">我的 Bot</div>
                <div className="mt-1 text-sm text-slate-400">
                  已配置倉位腿策略與共享帳戶預覽；是否真的運行請看「運行中 Bot」。
                </div>
              </div>
              <div className="text-right text-xs text-slate-400">
                <div>策略來源 {overviewPending ? "同步中" : (executionStrategySummary?.strategy_count ?? 0)}</div>
                <div>資金規則 {overviewPending ? "同步中" : allocationRuleLabel}</div>
              </div>
            </div>
            {(overviewLoading || overviewError) && (
              <div className="mt-3 rounded-2xl border border-white/8 bg-[#0d1324] px-4 py-3 text-sm text-slate-300">
                {overviewLoading ? "/api/execution/overview 載入中…" : `Bot 營運摘要載入失敗：${overviewError}`}
              </div>
            )}
            {executionOverview?.operator_message && (
              <div className="mt-3 text-sm text-slate-300">{humanizeRuntimeDetailText(executionOverview.operator_message)}</div>
            )}
            <div className="mt-2 text-xs text-slate-400">
              {executionStrategySummaryLabel}
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {executionProfileCards.length > 0 ? executionProfileCards.map((card) => {
                const profileId = card.profile_id || card.key || "";
                const linkedRun = runsByProfileId.get(profileId) || card.current_run || null;
                const profileStrategyBinding = card.strategy_binding ?? null;
                const ledgerPreview = linkedRun?.runtime_binding_snapshot?.shared_symbol_ledger_preview ?? null;
                const profileSharedPreviewValue = typeof ledgerPreview?.unrealized_pnl === "number"
                  ? `${formatSignedNumber(ledgerPreview.unrealized_pnl)} ${ledgerPreview?.currency || balanceCurrency}`
                  : (linkedRun ? "尚無共享預覽" : "未啟動運行");
                const profileSharedPreviewDetail = typeof ledgerPreview?.capital_in_use === "number"
                  ? `資金使用中 ${formatNumber(ledgerPreview.capital_in_use)} ${ledgerPreview?.currency || balanceCurrency}`
                  : (linkedRun ? "運行已建立，但尚未鏡像共享資金占用" : "先啟動運行才會建立共享帳戶預覽");
                const profileBudgetValue = typeof card.planned_budget_amount === "number"
                  ? `${formatNumber(card.planned_budget_amount)} ${balanceCurrency}`
                  : accountBalanceUnavailableLabel;
                const profileBudgetDetail = typeof card.planned_budget_amount === "number"
                  ? `勝率 ${formatPercent(profileStrategyBinding?.avg_expected_win_rate, 1)}`
                  : `${accountBalanceUnavailableReason} · 勝率 ${formatPercent(profileStrategyBinding?.avg_expected_win_rate, 1)}`;
                const profileLifecycleLabel = humanizeExecutionOperatorLabel(
                  linkedRun?.state_label || linkedRun?.state || card.lifecycle_status || card.activation_status,
                  "status",
                );
                const profileLatestEventLabel = humanizeExecutionOperatorLabel(
                  linkedRun?.last_event_type || card.control_contract?.latest_event_type,
                  "event",
                );
                const profilePositionStatusLabel = humanizeExecutionOperatorLabel(linkedRun?.state_label || linkedRun?.state, "status");
                const profileNextActionLabel = humanizeExecutionOperatorLabel(card.control_contract?.start_status, "start_status");
                const profileNextActionEventLabel = humanizeExecutionOperatorLabel(
                  linkedRun?.latest_event?.event_type || linkedRun?.last_event_type || "waiting",
                  "event",
                );
                const profilePreviewStatusLabel = humanizeExecutionOperatorLabel(
                  ledgerPreview?.budget_alignment_status || ledgerPreview?.ownership_status,
                  "preview",
                );
                const profileRoutingReasonLabel = humanizeRuntimeDetailText(card.routing_reason || null);
                const profileStartReasonLabel = humanizeRuntimeDetailText(card.control_contract?.start_reason || null);
                const profileShadowContract = card.control_contract?.shadow_only ? card.control_contract.high_conviction_topk ?? null : null;
                const profileShadowSummaryLabel = humanizeRuntimeDetailText(
                  currentSupportSummaryFromRuntimeContract(profileShadowContract)
                    || (card.control_contract?.shadow_only ? "影子觀察已可啟動；只記錄決策，不送單、不加倉。" : null),
                );
                const profileLatestEventMessageLabel = humanizeRuntimeDetailText(
                  linkedRun?.latest_event?.message || linkedRun?.last_event_message || card.control_contract?.latest_event_message || null,
                );
                const profileSummaryLabel = humanizeRuntimeDetailText(card.summary || profileStrategyBinding?.summary || profileRoutingReasonLabel || "尚未提供策略摘要");
                const profileIdLabel = humanizeRuntimeDetailText(profileId || card.key || null) || "—";
                const primarySleeveLabel = String(
                  profileStrategyBinding?.primary_sleeve_label || card.strategy_binding?.primary_sleeve_label || "",
                ).trim();
                const cardLabel = String(card.label || card.key || "未命名倉位腿").trim();
                const shouldShowPrimarySleeveBadge = Boolean(primarySleeveLabel) && primarySleeveLabel !== cardLabel;
                const strategyBindingStatus = String(profileStrategyBinding?.status || card.strategy_binding?.status || "").trim();
                const strategyBindingTitle = String(
                  profileStrategyBinding?.title || card.strategy_binding?.title || profileStrategyBinding?.strategy_name || "",
                ).trim();
                const strategyBundle = profileStrategyBinding?.strategy_bundle || linkedRun?.strategy_binding?.strategy_bundle || null;
                const strategyBundleStatus = String(
                  profileStrategyBinding?.strategy_bundle_status || linkedRun?.strategy_bundle_status || strategyBundle?.deployability_status || "",
                ).trim();
                const strategyBundleHash = String(
                  profileStrategyBinding?.strategy_bundle_hash || linkedRun?.strategy_bundle_hash || strategyBundle?.bundle_hash || "",
                ).trim();
                const workerControl = linkedRun?.worker_control || linkedRun?.action_contract?.worker_control || null;
                const workerStatusLabel = humanizeRuntimeDetailText(workerControl?.status || linkedRun?.worker_status || "未綁定 worker");
                const strategyBindingBadgeLabel = strategyBindingStatus === "missing_saved_strategy"
                  ? "待儲存策略快照"
                  : (strategyBindingTitle ? `策略：${strategyBindingTitle}` : "已綁定策略快照");
                const strategyBindingBadgeTone = strategyBindingStatus === "missing_saved_strategy"
                  ? "border-amber-500/30 bg-amber-500/10 text-amber-100"
                  : "border-emerald-500/25 bg-emerald-500/10 text-emerald-100";
                const isShadowStart = card.control_contract?.start_status === "shadow_start_available";
                const canStart = Boolean(profileId) && ["ready_control_plane", "resume_available", "shadow_start_available"].includes(card.control_contract?.start_status || "");
                const startButtonLabel = isShadowStart ? "啟動影子觀察" : "啟動 / 恢復";
                const startPendingLabel = isShadowStart ? "啟動影子觀察中…" : "建立運行中…";
                const startDoneLabel = card.control_contract?.start_status === "resume_available"
                  ? "已恢復運行。"
                  : (isShadowStart ? "已啟動影子觀察。" : "已建立運行。");
                const canPause = Boolean(linkedRun?.action_contract?.can_pause && linkedRun?.run_id);
                const canStop = Boolean(linkedRun?.action_contract?.can_stop && linkedRun?.run_id);
                return (
                  <div key={card.key || card.label} className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-base font-semibold text-white">{cardLabel}</div>
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                          {shouldShowPrimarySleeveBadge && (
                            <span className="rounded-full border border-[#7132f5]/25 bg-[#7132f5]/12 px-2.5 py-1 text-[#d8cbff]">
                              {primarySleeveLabel}
                            </span>
                          )}
                          {strategyBindingStatus && (
                            <span className={`rounded-full border px-2.5 py-1 ${strategyBindingBadgeTone}`}>
                              {strategyBindingBadgeLabel}
                            </span>
                          )}
                          {strategyBundleStatus && (
                            <span className="rounded-full border border-cyan-500/25 bg-cyan-500/10 px-2.5 py-1 text-cyan-100">
                              Freeze {strategyBundleHash ? strategyBundleHash.slice(0, 12) : strategyBundleStatus}
                            </span>
                          )}
                          {workerControl && (
                            <span className="rounded-full border border-amber-500/25 bg-amber-500/10 px-2.5 py-1 text-amber-100">
                              Worker {workerStatusLabel}
                            </span>
                          )}
                          <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(linkedRun?.state || card.lifecycle_status || card.activation_status)}`}>
                            {profileLifecycleLabel}
                          </span>
                          {ledgerPreview && (
                            <span className="rounded-full border border-cyan-500/25 bg-cyan-500/10 px-2.5 py-1 text-cyan-100">
                              共享預覽
                            </span>
                          )}
                          {card.control_contract?.shadow_only && (
                            <span className="rounded-full border border-purple-500/30 bg-purple-500/12 px-2.5 py-1 text-purple-100">
                              影子觀察 · 不送單
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-right text-[11px] text-slate-500">
                        <div>{profileIdLabel}</div>
                        <div>{profileLatestEventLabel}</div>
                      </div>
                    </div>

                    <div className="mt-3 text-sm text-slate-300">{profileSummaryLabel}</div>

                    <div className="mt-4 grid grid-cols-2 gap-2 xl:grid-cols-3">
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">策略 ROI</div>
                        <div className={`mt-1 text-sm font-semibold ${((profileStrategyBinding?.roi ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300")}`}>
                          {formatPercent(profileStrategyBinding?.roi, 1)}
                        </div>
                        <div className="text-[11px] text-slate-400">PF {formatNumber(profileStrategyBinding?.profit_factor, 2)}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">共享盈虧預覽</div>
                        <div className={`mt-1 text-sm font-semibold ${typeof ledgerPreview?.unrealized_pnl === "number" ? ((ledgerPreview.unrealized_pnl ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300") : "text-white"}`}>
                          {profileSharedPreviewValue}
                        </div>
                        <div className="text-[11px] text-slate-400">{profileSharedPreviewDetail}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">預算 / 勝率</div>
                        <div className="mt-1 text-sm font-semibold text-white">{profileBudgetValue}</div>
                        <div className="text-[11px] text-slate-400">{profileBudgetDetail}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">DQ</div>
                        <div className="mt-1 text-sm font-semibold text-white">{formatNumber(profileStrategyBinding?.avg_decision_quality_score, 3)}</div>
                        <div className="text-[11px] text-slate-400">交易數 {profileStrategyBinding?.total_trades ?? "—"}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">倉位 / 掛單</div>
                        <div className="mt-1 text-sm font-semibold text-white">{card.symbol_scoped_position_count ?? 0} / {card.symbol_scoped_open_order_count ?? 0}</div>
                        <div className="text-[11px] text-slate-400">{profilePositionStatusLabel}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">下一步</div>
                        <div className="mt-1 text-sm font-semibold text-white">{profileNextActionLabel}</div>
                        <div className="text-[11px] text-slate-400">{profileNextActionEventLabel}</div>
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-slate-400">
                      <span>路由 {profileRoutingReasonLabel || "—"}</span>
                      <span>啟動條件 {profileStartReasonLabel || "—"}</span>
                      {profileShadowSummaryLabel && <span>實戰影子 {profileShadowSummaryLabel}</span>}
                      <span>預覽 {profilePreviewStatusLabel}</span>
                      <span>Freeze {strategyBundleStatus ? `${strategyBundleStatus}${strategyBundleHash ? ` · ${strategyBundleHash.slice(0, 12)}` : ""}` : "尚未建立"}</span>
                      <span>Worker {workerStatusLabel}</span>
                      <span>送單 {workerControl?.order_submission_enabled ? "允許" : "Fail-closed"}</span>
                      <span>最新事件 {profileLatestEventMessageLabel || "尚未建立 Bot 事件"}</span>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2 text-sm">
                      <button
                        type="button"
                        disabled={!canStart || runActionState.tone === "pending"}
                        onClick={() => handleRunAction(`/api/execution/runs/${profileId}/start`, startPendingLabel, startDoneLabel)}
                        className="rounded-xl border border-emerald-500/30 bg-emerald-500/12 px-3 py-2 font-medium text-emerald-100 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {startButtonLabel}
                      </button>
                      <button
                        type="button"
                        disabled={!canPause || runActionState.tone === "pending"}
                        onClick={() => linkedRun?.run_id && handleRunAction(`/api/execution/runs/${linkedRun.run_id}/pause`, "暫停運行中…", "已暫停運行。")}
                        className="rounded-xl border border-amber-500/30 bg-amber-500/12 px-3 py-2 font-medium text-amber-100 transition hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        暫停
                      </button>
                      <button
                        type="button"
                        disabled={!canStop || runActionState.tone === "pending"}
                        onClick={() => linkedRun?.run_id && handleRunAction(`/api/execution/runs/${linkedRun.run_id}/stop`, "停止運行中…", "已停止運行。")}
                        className="rounded-xl border border-rose-500/30 bg-rose-500/12 px-3 py-2 font-medium text-rose-100 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        停止
                      </button>
                    </div>
                  </div>
                );
              }) : (
                <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-5 text-sm text-slate-300">
                  {executionProfileCardsEmptyState}
                </div>
              )}
            </div>
          </section>

          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">運行中</div>
                <div className="mt-1 text-sm text-slate-400">
                  {runsPending
                    ? "正在向 /api/execution/runs 取得運行控制 / 事件。"
                    : `進行中 ${executionRunsSummary?.running_runs ?? 0} · 暫停 ${executionRunsSummary?.paused_runs ?? 0} · 已停止 ${executionRunsSummary?.stopped_runs ?? 0} · 總計 ${executionRunsSummary?.total_runs ?? executionRunRecords.length}`}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  Outcome {workerOutcomeStatusLabel} · {workerOutcomeSummaryLabel}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  Proof {workerRehearsalStatusLabel} · {workerOutcomeNextActionLabel}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  ETA {workerOutcomeEtaLabel}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  disabled={!workerPollAvailable || runActionState.tone === "pending"}
                  title={workerPollDisabledReason || undefined}
                  onClick={() => handleRunAction("/api/execution/workers/poll", "同步 paper/shadow worker 中…", "已同步 paper/shadow worker。")}
                  className="rounded-xl border border-cyan-500/30 bg-cyan-500/12 px-3 py-2 text-sm font-medium text-cyan-100 transition hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  同步 worker
                </button>
                <div className="max-w-[22rem] text-xs text-slate-400">{workerPollDisabledReason || "運行控制（測試版）"}</div>
              </div>
            </div>
            {(runsLoading || runsError) && (
              <div className="mt-3 rounded-2xl border border-white/8 bg-[#0d1324] px-4 py-3 text-sm text-slate-300">
                {runsLoading ? "/api/execution/runs 載入中…" : `運行列表載入失敗：${runsError}`}
              </div>
            )}
            <div className="mt-4 rounded-[20px] border border-cyan-500/15 bg-cyan-500/[0.06] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-cyan-100">Standalone Live Runner 證據</div>
                  <div className="mt-1 text-xs text-slate-400">{liveRunnerEvidenceLabel}</div>
                  <div className="mt-1 text-xs text-slate-500">JSONL {liveRunnerJsonlPathLabel}</div>
                </div>
                <div className={`rounded-full border px-2.5 py-1 text-[11px] ${getStatusTone(liveRunnerOverview?.status || "pending")}`}>
                  {liveRunnerStatusLabel}
                </div>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-[12px] xl:grid-cols-4">
                <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-slate-500">最新決策</div>
                  <div className="mt-1 font-semibold text-white">{liveRunnerLatestActionLabel}</div>
                  <div className="text-slate-400">{liveRunnerLatestDecisionDetailLabel}</div>
                </div>
                <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-slate-500">24h Gate</div>
                  <div className="mt-1 font-semibold text-white">{liveRunnerGateStatusLabel}</div>
                  <div className="text-slate-400">{liveRunnerGateCountsLabel}</div>
                </div>
                <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-slate-500">Runner</div>
                  <div className="mt-1 font-semibold text-white">{liveRunnerLatestRun?.run_id || "尚未建立"}</div>
                  <div className="text-slate-400">heartbeat {formatTime(liveRunnerLatestRun?.last_heartbeat_at)}</div>
                </div>
                <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-slate-500">送單狀態</div>
                  <div className={`mt-1 font-semibold ${liveRunnerGate?.order_submission_enabled || liveRunnerSummary?.order_submission_enabled ? "text-rose-300" : "text-emerald-300"}`}>{liveRunnerFailClosedLabel}</div>
                  <div className="text-slate-400">{humanizeRuntimeDetailText(liveRunnerGate?.operator_message || liveRunnerOverview?.operator_message || "paper/shadow evidence only")}</div>
                </div>
              </div>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {executionRunRecords.length > 0 ? executionRunRecords.slice(0, 6).map((run) => {
                const runStrategyBinding = run.strategy_binding ?? null;
                const runStrategyBundle = runStrategyBinding?.strategy_bundle || null;
                const runStrategyBundleStatus = String(run.strategy_bundle_status || runStrategyBinding?.strategy_bundle_status || runStrategyBundle?.deployability_status || "").trim();
                const runStrategyBundleHash = String(run.strategy_bundle_hash || runStrategyBinding?.strategy_bundle_hash || runStrategyBundle?.bundle_hash || "").trim();
                const runWorkerControl = run.worker_control || run.action_contract?.worker_control || null;
                const runWorkerStatusLabel = humanizeRuntimeDetailText(runWorkerControl?.status || run.worker_status || "未綁定 worker");
                const latestMessage = humanizeRuntimeDetailText(run.latest_event?.message || run.last_event_message || "尚未取得運行事件");
                const runRuntimeTopKContract = run.runtime_binding_contract?.shadow_only ? run.runtime_binding_contract.high_conviction_topk ?? null : null;
                const runRuntimeSupportSummaryLabel = humanizeRuntimeDetailText(
                  currentSupportSummaryFromRuntimeContract(runRuntimeTopKContract)
                    || run.runtime_binding_contract?.summary
                    || latestMessage
                    || "尚未取得運行事件",
                );
                const runStrategySnapshotSummaryLabel = humanizeRuntimeDetailText(runStrategyBinding?.summary || null);
                const runProfileLabel = humanizeRuntimeDetailText(run.profile_id || null) || "—";
                const runModeLabel = humanizeExecutionModeLabel(run.mode || "paper");
                const runStateLabel = humanizeExecutionOperatorLabel(run.state_label || run.state, "status");
                const runLatestEventTypeLabel = humanizeExecutionOperatorLabel(run.latest_event?.event_type || run.last_event_type || "waiting", "event");
                const ledgerPreview = run.runtime_binding_snapshot?.shared_symbol_ledger_preview ?? null;
                const runBudgetValue = typeof run.budget_amount === "number"
                  ? `${formatNumber(run.budget_amount)} ${run.capital_currency || balanceCurrency}`
                  : accountBalanceUnavailableLabel;
                const runBudgetDetail = typeof run.budget_amount === "number"
                  ? `比例 ${formatNumber(run.budget_ratio, 3)}`
                  : accountBalanceUnavailableReason;
                const runSharedPreviewValue = typeof ledgerPreview?.unrealized_pnl === "number"
                  ? `${formatSignedNumber(ledgerPreview.unrealized_pnl)} ${ledgerPreview?.currency || balanceCurrency}`
                  : "尚無共享預覽";
                const runSharedPreviewDetail = typeof ledgerPreview?.capital_in_use === "number"
                  ? `資金使用中 ${formatNumber(ledgerPreview.capital_in_use)} ${ledgerPreview?.currency || balanceCurrency}`
                  : "運行已建立，但尚未鏡像共享資金占用";
                return (
                  <div key={run.run_id || `${run.profile_id}-${run.start_time}`} className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-base font-semibold text-white">{run.label || run.profile_id || "未命名運行"}</div>
                        <div className="mt-1 text-[12px] text-slate-400">設定檔 {runProfileLabel} · {runModeLabel}</div>
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                          {runStrategyBundleStatus && (
                            <span className="rounded-full border border-cyan-500/25 bg-cyan-500/10 px-2.5 py-1 text-cyan-100">
                              Freeze {runStrategyBundleHash ? runStrategyBundleHash.slice(0, 12) : runStrategyBundleStatus}
                            </span>
                          )}
                          {runWorkerControl && (
                            <span className="rounded-full border border-amber-500/25 bg-amber-500/10 px-2.5 py-1 text-amber-100">
                              Worker {runWorkerStatusLabel}
                            </span>
                          )}
                          <span className="rounded-full border border-rose-500/25 bg-rose-500/10 px-2.5 py-1 text-rose-100">
                            送單 {runWorkerControl?.order_submission_enabled ? "允許" : "Fail-closed"}
                          </span>
                        </div>
                      </div>
                      <div className={`rounded-full border px-2.5 py-1 text-[11px] ${getStatusTone(run.state || "unknown")}`}>
                        {runStateLabel}
                      </div>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-[12px] xl:grid-cols-4">
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">預算</div>
                        <div className="mt-1 font-semibold text-white">{runBudgetValue}</div>
                        <div className="text-slate-400">{runBudgetDetail}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">共享盈虧預覽</div>
                        <div className={`mt-1 font-semibold ${typeof ledgerPreview?.unrealized_pnl === "number" ? ((ledgerPreview.unrealized_pnl ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300") : "text-white"}`}>{runSharedPreviewValue}</div>
                        <div className="text-slate-400">{runSharedPreviewDetail}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">策略能力</div>
                        <div className={`mt-1 font-semibold ${(runStrategyBinding?.roi ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{formatPercent(runStrategyBinding?.roi, 1)}</div>
                        <div className="text-slate-400">PF {formatNumber(runStrategyBinding?.profit_factor, 2)} · win {formatPercent(runStrategyBinding?.avg_expected_win_rate, 1)}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">最近事件</div>
                        <div className="mt-1 font-semibold text-white">{runLatestEventTypeLabel}</div>
                        <div className="text-slate-400">{formatTime(run.last_event_at)}</div>
                      </div>
                    </div>
                    <div className="mt-3 text-sm text-slate-300">{runRuntimeSupportSummaryLabel}</div>
                    {runStrategySnapshotSummaryLabel && (
                      <div className="mt-1 text-[12px] text-slate-500">策略 snapshot {runStrategySnapshotSummaryLabel}</div>
                    )}
                    <div className="mt-2 text-[12px] text-slate-400">共享預覽 {humanizeRuntimeDetailText(ledgerPreview?.budget_alignment_summary || ledgerPreview?.summary || "尚未提供共享帳戶預覽。")}</div>
                    <div className="mt-1 text-[12px] text-slate-400">
                      Freeze {runStrategyBundleStatus || "尚未建立"}{runStrategyBundleHash ? ` · ${runStrategyBundleHash.slice(0, 12)}` : ""} · Worker {runWorkerStatusLabel} · 送單 {runWorkerControl?.order_submission_enabled ? "允許" : "Fail-closed"}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-sm">
                      <button
                        type="button"
                        disabled={!run.action_contract?.can_resume || !run.profile_id || runActionState.tone === "pending"}
                        onClick={() => run.profile_id && handleRunAction(`/api/execution/runs/${run.profile_id}/start`, "恢復運行中…", "已恢復運行。")}
                        className="rounded-xl border border-emerald-500/30 bg-emerald-500/12 px-3 py-2 font-medium text-emerald-100 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        恢復
                      </button>
                      <button
                        type="button"
                        disabled={!run.action_contract?.can_pause || !run.run_id || runActionState.tone === "pending"}
                        onClick={() => run.run_id && handleRunAction(`/api/execution/runs/${run.run_id}/pause`, "暫停運行中…", "已暫停運行。")}
                        className="rounded-xl border border-amber-500/30 bg-amber-500/12 px-3 py-2 font-medium text-amber-100 transition hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        暫停
                      </button>
                      <button
                        type="button"
                        disabled={!run.action_contract?.can_stop || !run.run_id || runActionState.tone === "pending"}
                        onClick={() => run.run_id && handleRunAction(`/api/execution/runs/${run.run_id}/stop`, "停止運行中…", "已停止運行。")}
                        className="rounded-xl border border-rose-500/30 bg-rose-500/12 px-3 py-2 font-medium text-rose-100 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        停止
                      </button>
                    </div>
                  </div>
                );
              }) : (
                <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-5 text-sm text-slate-300">
                  {executionRunsEmptyState}
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="space-y-4">
          <ExecutionSectionCard
            title="自然語句操作"
            subtitle={runtimeStatusPending ? "正在向 /api/status 取得商品 / 模式 / 場館。" : `${executionSymbol} · ${executionModeLabel} · ${executionVenueLabel} · 舊的「應急手動操作」已整併到這裡`}
            aside={(
              <div className={`rounded-full border px-2.5 py-1 text-[11px] ${getStatusTone(runtimeStatusPending ? "pending" : (automationEnabled ? "ok" : "warning"))}`}>
                {automationStatusLabel}
              </div>
            )}
          >
            <div className="text-sm text-slate-300">自然語句會優先幫你判斷是交易、模式切換還是前往診斷；不需要先找對按鈕。</div>
            {operatorShortcutBlockedMessage && (
              <div className="mt-3 rounded-2xl border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
                {operatorShortcutBlockedMessage}
              </div>
            )}
            <div className="mt-3 flex flex-col gap-3">
              <input
                value={naturalCommand}
                onChange={(event) => setNaturalCommand(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    void handleNaturalLanguageAction();
                  }
                }}
                className="execution-command-input"
                placeholder="例如：買 0.001 BTC / 減碼 0.001 / 等待觀望 / 切到自動 / 查看阻塞原因"
              />
              <div className="flex flex-wrap gap-2">
                {operatorQuickCommands.map((command) => (
                  <button
                    key={command.label}
                    type="button"
                    disabled={command.disabled}
                    onClick={() => void handleNaturalLanguageAction(command.label)}
                    className="app-button-secondary"
                  >
                    {command.label}
                  </button>
                ))}
                <button
                  type="button"
                  disabled={operatorActionState.tone === "pending"}
                  onClick={() => void handleNaturalLanguageAction()}
                  className="app-button-primary"
                >
                  執行語句
                </button>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-300">
              <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(guardrails?.kill_switch ? "blocked" : "ok")}`}>停機開關 {guardrails?.kill_switch ? "啟用" : "關閉"}</span>
              <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(guardrails?.failure_halt ? "warning" : "ok")}`}>失敗暫停 {guardrails?.failure_halt ? "啟用" : "關閉"}</span>
              <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(guardrails?.daily_loss_halt ? "warning" : "ok")}`}>日損暫停 {guardrails?.daily_loss_halt ? "啟用" : "關閉"}</span>
            </div>
            {operatorActionState.tone !== "idle" && operatorActionState.message && (
              <div className={`mt-3 rounded-2xl border px-3 py-2 text-sm ${operatorActionTone}`}>
                {operatorActionState.message}
              </div>
            )}
          </ExecutionSectionCard>

          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">部署狀態</div>
                <div className="mt-1 text-sm text-slate-400">{runtimeStatusPending ? "正在向 /api/status 取得市場狀態 / 閘門 / 分桶。" : `${humanizeStructureBucketLabel(liveRouting?.current_regime || liveRuntimeTruth?.regime_label || "—")} · 閘門 ${humanizeStructureBucketLabel(liveRouting?.current_regime_gate || liveRuntimeTruth?.regime_gate || "—")} · 當前分桶 ${humanizeStructureBucketLabel(liveRouting?.current_structure_bucket || liveRuntimeTruth?.structure_bucket || "—")}`}</div>
              </div>
              <div className={`rounded-full border px-2.5 py-1 text-[11px] ${getStatusTone(runtimeStatusPending ? "pending" : (executionSurfaceContract?.live_ready ? "ok" : "blocked"))}`}>
                {liveReadyStatusLabel}
              </div>
            </div>
            <div className="mt-3 text-sm text-slate-300">{deploymentStatusDetail}</div>
            <div className="mt-2 text-xs text-slate-400">部署閉環 {runtimeClosureStateLabel}</div>
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
              {circuitBreakerActive && (
                <div className="col-span-2 rounded-2xl border border-amber-500/25 bg-amber-500/10 p-3 text-amber-100">
                  <div className="text-[10px] uppercase tracking-wide opacity-80">熔斷解除條件</div>
                  <div className="mt-1 font-semibold text-white">{breakerReleaseSummaryLabel}</div>
                  <div className="text-[11px]">最近 {breakerRecentWindow ?? 50} 筆目前 {breakerWins ?? "—"}/{breakerRecentWindow ?? 50} 勝；解除門檻 {breakerRequiredWins ?? "—"} 勝</div>
                  <div className="text-[11px]">至少還差 {breakerWinsGap ?? "—"} 勝；連敗需低於 {breakerStreakLimit ?? 50}。</div>
                  <div className="mt-1 text-[11px] text-amber-50/80">熔斷是目前即時路徑的 primary hard gate；精準支持與場館生命週期仍是後續 live gate；{breakerSupportCaveatLabel}</div>
                </div>
              )}
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">層數</div>
                <div className="mt-1 font-semibold text-white">{liveRuntimeTruth?.allowed_layers_raw ?? "—"} → {liveRuntimeTruth?.allowed_layers ?? "—"}</div>
                <div className="text-[11px] text-slate-400">{finalAllowedLayersReasonLabel !== "—" ? finalAllowedLayersReasonLabel : rawAllowedLayersReasonLabel}</div>
              </div>
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">支持樣本</div>
                <div className="mt-1 font-semibold text-white">當前分桶 {supportRowsLabel} · 缺口 {supportGapLabel}</div>
                <div className="text-[11px] text-slate-400">支持狀態 {supportProgressStatusLabel}</div>
                <div className="text-[11px] text-slate-400">樣本變化 {supportDeltaLabel}</div>
                <div className="text-[11px] text-slate-400">最近已就緒 {supportReferenceLabel}</div>
                <div className="text-[11px] text-slate-400">支持路徑 {supportRouteVerdictLabel}</div>
                <div className="text-[11px] text-slate-400">治理路徑 {supportGovernanceRouteLabel}</div>
                <div className="text-[11px] text-slate-400">{supportAlignmentCountsLabel}</div>
                <div className="text-[11px] text-slate-400">{supportAlignmentSummaryLabel}</div>
              </div>
            </div>
            {(runtimeStatusPending || liveReadyBlockers.length > 0) && (
              <div className="mt-3 rounded-2xl border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
                {blockedReasonSummary}
              </div>
            )}
            {venueChecks.length > 0 && (
              <div className="mt-3">
                <div className="mb-2 text-[11px] uppercase tracking-wide text-slate-500">場館實單證據缺口</div>
                <VenueReadinessSummary venues={venueChecks} compact />
              </div>
            )}
            <div className="mt-4 space-y-3">
              <div>
                <div className="text-[11px] uppercase tracking-wide text-slate-500">啟用倉位腿</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {liveActiveSleeves.length > 0 ? liveActiveSleeves.map((item) => {
                    const sleeveLabel = humanizeRuntimeDetailText(item.label || item.key || null);
                    const sleeveReason = item.why ? humanizeRuntimeDetailText(item.why) : undefined;
                    return (
                      <span key={item.key || item.label} title={sleeveReason} className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1 text-[11px] text-emerald-100">
                        {sleeveLabel}
                      </span>
                    );
                  }) : <span className="text-sm text-slate-400">目前沒有啟用倉位腿</span>}
                </div>
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-wide text-slate-500">待命倉位腿</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {liveInactiveSleeves.length > 0 ? liveInactiveSleeves.map((item) => {
                    const sleeveLabel = humanizeRuntimeDetailText(item.label || item.key || null);
                    const sleeveReason = item.why ? humanizeRuntimeDetailText(item.why) : undefined;
                    return (
                      <span key={item.key || item.label} title={sleeveReason} className="rounded-full border border-rose-500/25 bg-rose-500/10 px-2.5 py-1 text-[11px] text-rose-100">
                        {sleeveLabel}
                      </span>
                    );
                  }) : <span className="text-sm text-slate-400">目前沒有待命倉位腿</span>}
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">帳戶與成交</div>
                <div className="mt-1 text-sm text-slate-400">擷取時間 {formatTime(accountSummary?.captured_at)}</div>
              </div>
              <div className="text-xs text-slate-400">{accountSummary?.requested_symbol || "—"} → {accountSummary?.normalized_symbol || "—"}</div>
            </div>
            {(accountSummary?.operator_message || accountSummary?.recovery_hint || accountSummary?.degraded) && (
              <div className="mt-3 rounded-2xl border border-white/8 bg-white/5 px-3 py-2 text-sm text-slate-300">
                {humanizeRuntimeDetailText(accountSummary?.operator_message || accountSummary?.recovery_hint || (accountSummary?.degraded ? "account snapshot degraded" : ""))}
              </div>
            )}
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">持倉</div>
                <div className="mt-1 font-semibold text-white">{accountSummary?.position_count ?? positions.length}</div>
                <div className="text-[11px] text-slate-400">{summarizePreviewRecords(positions.slice(0, 2) as ExecutionRunPreviewRecord[])}</div>
              </div>
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">掛單</div>
                <div className="mt-1 font-semibold text-white">{accountSummary?.open_order_count ?? openOrders.length}</div>
                <div className="text-[11px] text-slate-400">{summarizePreviewRecords(openOrders.slice(0, 2) as ExecutionRunPreviewRecord[])}</div>
              </div>
            </div>
            <div className="mt-4 grid gap-2 md:grid-cols-3 text-sm">
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">最近委託</div>
                <div className="mt-1 font-semibold text-white">{humanizeTradeSideLabel(lastOrder?.side || null)} · {humanizeRuntimeDetailText(lastOrder?.status || null) || "—"}</div>
                <div className="text-[11px] text-slate-400">數量 {formatNumber(lastOrder?.qty)} · 價格 {formatNumber(lastOrder?.price)}</div>
              </div>
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">最近拒單</div>
                <div className="mt-1 font-semibold text-white">{lastReject?.code || "無"}</div>
                <div className="text-[11px] text-slate-400">{lastReject?.message || "尚無最近拒單"}</div>
              </div>
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">最近失敗</div>
                <div className="mt-1 font-semibold text-white">{lastFailure?.message || "無"}</div>
                <div className="text-[11px] text-slate-400">{formatTime(lastFailure?.timestamp)}</div>
              </div>
            </div>
          </section>
        </div>
      </section>

      <details className="execution-card">
        <summary className="cursor-pointer list-none text-lg font-semibold text-white">進階營運細節（需要時再展開）</summary>
        <div className="mt-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <div className="text-lg font-semibold text-white">執行狀態</div>
              <div className="mt-1 text-sm leading-6 text-slate-300">
                阻塞原因、元資料新鮮度與對帳 / 恢復已移到獨立頁；這裡只保留營運摘要與入口。
              </div>
            </div>
            <a href="/execution/status" className="app-button-secondary">
              前往執行狀態 →
            </a>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm text-slate-300">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Live 部署狀態</div>
              <div className="mt-2 text-base font-semibold text-white">{runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞")}</div>
              <div className="mt-2">{liveReadinessSummary}</div>
            </div>
            <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm text-slate-300">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">元資料新鮮度</div>
              <div className="mt-2 text-base font-semibold text-white">{metadataSmokeFreshnessLabel}</div>
              <div className="mt-2">{runtimeStatusPending ? "正在向 /api/status 取得元資料檢查。" : `生成於 ${formatTime(metadataSmoke?.generated_at)} · 距今 ${metadataSmokeFreshness?.age_minutes != null ? `${metadataSmokeFreshness.age_minutes.toFixed(1)} 分鐘` : "—"}`}</div>
            </div>
            <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm text-slate-300">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">對帳 / 恢復</div>
              <div className="mt-2 text-base font-semibold text-white">{reconciliationStatusLabel}</div>
              <div className="mt-2">{reconciliationSummaryLabel}</div>
            </div>
          </div>
        </div>
      </details>
    </div>
  );
}
