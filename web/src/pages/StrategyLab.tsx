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
import { fetchApi } from "../hooks/useApi";
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

interface StrategyMetadata {
  title?: string;
  description?: string;
  strategy_type?: string;
  model_name?: string;
  model_summary?: string;
}

interface DecisionContractMeta {
  target_col?: string | null;
  target_label?: string | null;
  sort_semantics?: string | null;
  decision_quality_horizon_minutes?: number | null;
}

interface StrategyResult {
  roi: number;
  win_rate: number;
  total_trades: number;
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
  id: number;
  created_at: string;
  target_col?: string | null;
  model_count?: number | null;
}

interface ModelLeaderboardMeta {
  refreshing?: boolean;
  cached?: boolean;
  stale?: boolean;
  updated_at?: string | null;
  cache_age_sec?: number | null;
  warning?: string | null;
  error?: string | null;
  target_col?: string | null;
  target_label?: string | null;
  global_metrics?: LeaderboardGlobalMetrics | null;
  regime_metrics?: Record<string, RegimeMetricsEntry> | null;
  skipped_models?: SkippedModel[];
  score_dimensions?: ScoreDimensionMeta[];
  storage?: { canonical_store?: string; cache_store?: string } | null;
  snapshot_history?: LeaderboardHistoryRow[];
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

interface BackgroundStage {
  mode: "initial" | "select_strategy" | "run_strategy" | "model_refresh";
  label: string;
  detail: string;
  progress: number;
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
    bias50_max: 1.0,
    nose_max: 0.4,
    pulse_min: 0.0,
    layer2_bias_max: -1.5,
    layer3_bias_max: -3.5,
    confidence_min: 0.55,
    entry_quality_min: 0.55,
    top_k_percent: 0,
    allowed_regimes: ["bull", "chop", "bear", "unknown"],
  },
  layers: [0.2, 0.3, 0.5],
  capital_management: {
    mode: "classic_pyramid",
    base_entry_fraction: 0.10,
    reserve_trigger_drawdown: 0.10,
  },
  stop_loss: -0.05,
  take_profit_bias: 4.0,
  take_profit_roi: 0.08,
};

const MODEL_OPTIONS = ["rule_baseline", "logistic_regression", "xgboost", "lightgbm", "catboost", "random_forest", "mlp", "svm"] as const;

const isFiniteNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
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
const describeRankingReason = (model: ModelLeaderboardEntry) => {
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

const toStageProgress = (completed: number, total: number) => {
  if (total <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((completed / total) * 100)));
};

const STAGE_TOTALS = {
  initial: 4,
  select_strategy: 3,
  run_strategy: 5,
} as const;

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
  const [strategyType, setStrategyType] = useState<"rule_based" | "hybrid">("rule_based");
  const [selectedModelName, setSelectedModelName] = useState<string>("xgboost");
  const [bias50Max, setBias50Max] = useState(DEFAULT_PARAMS.entry.bias50_max);
  const [noseMax, setNoseMax] = useState(DEFAULT_PARAMS.entry.nose_max);
  const [layer2Bias, setLayer2Bias] = useState(DEFAULT_PARAMS.entry.layer2_bias_max);
  const [layer3Bias, setLayer3Bias] = useState(DEFAULT_PARAMS.entry.layer3_bias_max);
  const [layer1, setLayer1] = useState(20);
  const [layer2, setLayer2] = useState(30);
  const [layer3, setLayer3] = useState(50);
  const [confidenceMin, setConfidenceMin] = useState(55);
  const [entryQualityMin, setEntryQualityMin] = useState(55);
  const [topKPercent, setTopKPercent] = useState(0);
  const [allowedRegimesMode, setAllowedRegimesMode] = useState<"all" | "bull_chop" | "bull_only" | "bear_only">("all");
  const [capitalMode, setCapitalMode] = useState<"classic_pyramid" | "reserve_90">("classic_pyramid");
  const [baseEntryFractionPct, setBaseEntryFractionPct] = useState(10);
  const [reserveTriggerDrawdownPct, setReserveTriggerDrawdownPct] = useState(10);
  const [stopLoss, setStopLoss] = useState(-5);
  const [tpBias, setTpBias] = useState(4.0);
  const [tpRoi, setTpRoi] = useState(8);
  const [chartStart, setChartStart] = useState<string>("");
  const [chartEnd, setChartEnd] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"workspace" | "leaderboard">("workspace");
  const [capitalModeFilter, setCapitalModeFilter] = useState<"all" | "classic_pyramid" | "reserve_90">("all");

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
  const availableTradingModels = useMemo(() => {
    const merged = [...modelLeaderboard.map((row) => row.model_name), ...MODEL_OPTIONS];
    return merged.filter((name, idx) => merged.indexOf(name) === idx);
  }, [modelLeaderboard]);
  const sortedModelLeaderboard = useMemo(() => {
    const rows = [...modelLeaderboard];
    rows.sort((a, b) => {
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
  const strategyCapitalMode = useCallback((entry: StrategyEntry) => {
    const fromResults = entry.last_results?.capital_mode;
    if (fromResults === "classic_pyramid" || fromResults === "reserve_90") return fromResults;
    const fromParams = entry.definition?.params?.capital_management?.mode;
    return fromParams === "reserve_90" ? "reserve_90" : "classic_pyramid";
  }, []);

  const filteredStrategies = useMemo(() => {
    if (capitalModeFilter === "all") return strategies;
    return strategies.filter((entry) => strategyCapitalMode(entry) === capitalModeFilter);
  }, [capitalModeFilter, strategies, strategyCapitalMode]);

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

  const loadLeaderboard = async () => {
    try {
      const res = await fetchApi("/api/strategies/leaderboard") as any;
      const list = res?.strategies ?? res?.data?.strategies ?? (Array.isArray(res) ? res : []);
      const nextStrategies = list || [];
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
        error: data?.error ?? null,
        target_col: data?.target_col ?? null,
        target_label: data?.target_label ?? null,
        global_metrics: data?.global_metrics ?? null,
        regime_metrics: data?.regime_metrics ?? null,
        skipped_models: Array.isArray(data?.skipped_models) ? data.skipped_models : [],
        score_dimensions: Array.isArray(data?.score_dimensions) ? data.score_dimensions : [],
        storage: data?.storage ?? null,
        snapshot_history: Array.isArray(data?.snapshot_history) ? data.snapshot_history : [],
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
          detail: "模型排行榜已同步，正在載入模型統計與技術競爭力。",
          progress: toStageProgress(2, STAGE_TOTALS.initial),
        });
        await loadModelStats();
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
    if (!modelMeta.refreshing && !modelMeta.stale) {
      clearBackgroundStage("model_refresh");
      return;
    }
    updateBackgroundStage({
      mode: "model_refresh",
      label: modelMeta.refreshing ? "模型排行榜背景重算中" : "模型排行榜快取刷新中",
      detail: modelMeta.cache_age_sec != null
        ? `目前快取年齡 ${modelMeta.cache_age_sec} 秒，系統持續輪詢最新結果。`
        : "正在輪詢最新 leaderboard 與模型統計。",
      progress: toModelFreshnessProgress(modelMeta.cache_age_sec) ?? 0,
    });
    const timer = window.setInterval(() => {
      loadModelLeaderboard(false);
      loadModelStats();
    }, 2500);
    return () => window.clearInterval(timer);
  }, [modelMeta.refreshing, modelMeta.stale, modelMeta.cache_age_sec]);

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
      const body = {
        name,
        type: strategyType,
        params: {
          model_name: selectedModelName,
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
      for (let attempt = 0; attempt < 600; attempt += 1) {
        const job = await fetchApi(`/api/strategies/jobs/${jobId}`) as any;
        updateBackgroundStage({
          mode: "run_strategy",
          label: `正在執行回測：${name}`,
          detail: job?.detail || "背景回測執行中。",
          progress: typeof job?.progress === "number" ? job.progress : toStageProgress(1, STAGE_TOTALS.run_strategy),
        });
        if (job?.status === "completed") {
          data = job?.result;
          break;
        }
        if (job?.status === "failed") {
          throw new Error(job?.error || job?.detail || "回測失敗");
        }
        await new Promise((resolve) => window.setTimeout(resolve, 400));
      }

      if (!data) {
        throw new Error("回測逾時，請稍後再試");
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

  const presets = [
    {
      label: "🔥 金字塔+SL/TP",
      mode: "rule_based",
      modelName: "rule_baseline",
      note: "通用規則模式，保留完整 regime 與分層加碼。",
      params: { bias50Max: 1.0, noseMax: 0.4, layer2Bias: -1.5, layer3Bias: -3.5, confidenceMin: 55, qualityMin: 55, topKPercent: 0, allowedRegimesMode: "all", capitalMode: "classic_pyramid", baseEntryFractionPct: 10, reserveTriggerDrawdownPct: 10, stopLoss: -5, tpBias: 4, tpRoi: 8, l1: 20, l2: 30, l3: 50 },
    },
    {
      label: "🌀 Fib 23/38/39",
      mode: "rule_based",
      modelName: "rule_baseline",
      note: "偏向回調承接的規則模式，適合較慢節奏測試。",
      params: { bias50Max: -1.0, noseMax: 0.35, layer2Bias: -2.8, layer3Bias: -5.0, confidenceMin: 55, qualityMin: 68, topKPercent: 0, allowedRegimesMode: "bull_chop", capitalMode: "classic_pyramid", baseEntryFractionPct: 10, reserveTriggerDrawdownPct: 10, stopLoss: -5, tpBias: 4.5, tpRoi: 8, l1: 23, l2: 38, l3: 39 },
    },
    {
      label: "🎯 高勝率低頻",
      mode: "hybrid",
      modelName: "random_forest",
      note: "依目前 walk-forward top-k 結果，主打 random_forest + bear only + top 5% 高把握訊號。",
      params: { bias50Max: 1.0, noseMax: 0.4, layer2Bias: -1.5, layer3Bias: -3.5, confidenceMin: 75, qualityMin: 68, topKPercent: 5, allowedRegimesMode: "bear_only", capitalMode: "classic_pyramid", baseEntryFractionPct: 10, reserveTriggerDrawdownPct: 10, stopLoss: -5, tpBias: 4, tpRoi: 8, l1: 20, l2: 30, l3: 50 },
    },
    {
      label: "🛡️ 10/90 後守",
      mode: "rule_based",
      modelName: "rule_baseline",
      note: "先用 10% 試單，只有當浮虧擴大到 10% 時才啟動剩餘 90% 後守金。更偏向資金可靠性與解套生存率。",
      params: { bias50Max: 0.5, noseMax: 0.35, layer2Bias: -2.5, layer3Bias: -4.5, confidenceMin: 55, qualityMin: 60, topKPercent: 0, allowedRegimesMode: "all", capitalMode: "reserve_90", baseEntryFractionPct: 10, reserveTriggerDrawdownPct: 10, stopLoss: -7, tpBias: 4, tpRoi: 8, l1: 20, l2: 30, l3: 50 },
    },
  ];

  const applyPreset = (preset: any) => {
    setStrategyType((preset.mode as "rule_based" | "hybrid") ?? "rule_based");
    setSelectedModelName(preset.modelName ?? "rule_baseline");
    setBias50Max(preset.params.bias50Max);
    setNoseMax(preset.params.noseMax);
    setLayer2Bias(preset.params.layer2Bias);
    setLayer3Bias(preset.params.layer3Bias);
    setConfidenceMin(preset.params.confidenceMin ?? 55);
    setEntryQualityMin(preset.params.qualityMin ?? 55);
    setTopKPercent(preset.params.topKPercent ?? 0);
    setAllowedRegimesMode(preset.params.allowedRegimesMode ?? "all");
    setCapitalMode(preset.params.capitalMode ?? "classic_pyramid");
    setBaseEntryFractionPct(preset.params.baseEntryFractionPct ?? 10);
    setReserveTriggerDrawdownPct(preset.params.reserveTriggerDrawdownPct ?? 10);
    setStopLoss(preset.params.stopLoss);
    setTpBias(preset.params.tpBias);
    setTpRoi(preset.params.tpRoi);
    setLayer1(preset.params.l1);
    setLayer2(preset.params.l2);
    setLayer3(preset.params.l3);
  };

  useEffect(() => {
    const start = activeResult?.chart_context?.start ? new Date(activeResult.chart_context.start).toISOString().slice(0, 16) : "";
    const end = activeResult?.chart_context?.end ? new Date(activeResult.chart_context.end).toISOString().slice(0, 16) : "";
    setChartStart(start);
    setChartEnd(end);
  }, [activeResult?.chart_context?.start, activeResult?.chart_context?.end]);

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
  const activeSortSemantics = activeResult?.sort_semantics || selectedStrategy?.decision_contract?.sort_semantics || strategyMeta.sort_semantics || "ROI -> lower max_drawdown -> avg_decision_quality_score -> profit_factor (win_rate reference only)";
  const activeHorizonMinutes = activeResult?.decision_quality_horizon_minutes || selectedStrategy?.decision_contract?.decision_quality_horizon_minutes || activeDecisionContract?.decision_quality_horizon_minutes || 1440;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-200">🧪 策略實驗室</h2>
          <span className="text-xs text-slate-500">排行榜點一下，左側設定就會自動切換</span>
        </div>
        <div className="inline-flex rounded-lg border border-slate-700/60 bg-slate-900/70 p-1 text-sm">
          <button
            type="button"
            onClick={() => setActiveTab("workspace")}
            className={`rounded-md px-3 py-1.5 ${activeTab === "workspace" ? "bg-cyan-500/20 text-cyan-200" : "text-slate-400 hover:text-slate-200"}`}
          >
            工作區
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("leaderboard")}
            className={`rounded-md px-3 py-1.5 ${activeTab === "leaderboard" ? "bg-cyan-500/20 text-cyan-200" : "text-slate-400 hover:text-slate-200"}`}
          >
            排行榜
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[360px,minmax(0,1fr)] 2xl:grid-cols-[380px,minmax(0,1fr)] gap-4 items-start">
        <div className="space-y-4 self-start min-w-0">
          <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-300">⚙️ 策略編輯器</h3>
                <div className="mt-1 text-[11px] leading-5 text-slate-500">保留必要參數：進場條件、風控、資金模式。其他分析移到右側摘要，不再把版面切得太碎。</div>
              </div>
              <div className="rounded-lg border border-slate-700/50 bg-slate-950/40 px-3 py-2 text-right">
                <div className="text-[10px] text-slate-500">目前策略</div>
                <div className="text-sm font-semibold text-slate-100">{activeMeta.title}</div>
                <div className="text-[11px] text-emerald-300">{activeMeta.model_name || "rule_based"}</div>
              </div>
            </div>
            <div className="mt-3 space-y-3">
              <div>
                <label className="text-xs text-slate-500">策略名稱</label>
                <input value={name} onChange={(e) => setName(e.target.value)} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-slate-500">交易模式</label>
                  <select value={strategyType} onChange={(e) => setStrategyType(e.target.value as any)} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200">
                    <option value="rule_based">Rule-based</option>
                    <option value="hybrid">Hybrid</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-500">交易模型</label>
                  <select value={selectedModelName} onChange={(e) => setSelectedModelName(e.target.value)} disabled={strategyType !== "hybrid"} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200 disabled:text-slate-500">
                    {availableTradingModels.map((modelName) => <option key={modelName} value={modelName}>{modelName}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex gap-2">
                {presets.map((preset) => (
                  <button key={preset.label} onClick={() => applyPreset(preset)} className="flex-1 px-2 py-1 text-xs bg-slate-800 text-slate-300 rounded border border-slate-600 hover:bg-slate-700">{preset.label}</button>
                ))}
              </div>
              <div className="rounded-lg border border-cyan-700/30 bg-cyan-950/10 px-3 py-2 text-[11px] leading-5 text-cyan-100 space-y-1">
                <div className="font-medium">目前高可靠度模式建議</div>
                <div>主排序已改成 ROI + 最大回撤優先；勝率只保留為參考輔助，不再主導排行榜。</div>
                <div>🛡️ 10/90 後守 會先用 10% 試單，只有當浮虧擴大到設定門檻時才啟用剩餘 90% 後守資金。</div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-slate-500">Bias50 上限 (%)</label>
                  <input type="number" step="0.5" value={bias50Max} onChange={(e) => setBias50Max(parseFloat(e.target.value))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Nose 上限</label>
                  <input type="number" step="0.05" value={noseMax} onChange={(e) => setNoseMax(parseFloat(e.target.value))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Layer2 Bias (%)</label>
                  <input type="number" step="0.5" value={layer2Bias} onChange={(e) => setLayer2Bias(parseFloat(e.target.value))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Layer3 Bias (%)</label>
                  <input type="number" step="0.5" value={layer3Bias} onChange={(e) => setLayer3Bias(parseFloat(e.target.value))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                </div>
                <div>
                  <label className="text-xs text-slate-500">信心門檻 (%)</label>
                  <input type="number" step="1" min="0" max="100" value={confidenceMin} onChange={(e) => setConfidenceMin(parseInt(e.target.value || "0", 10))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                </div>
                <div>
                  <label className="text-xs text-slate-500">進場品質門檻 (%)</label>
                  <input type="number" step="1" min="0" max="100" value={entryQualityMin} onChange={(e) => setEntryQualityMin(parseInt(e.target.value || "0", 10))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Top-K (%)</label>
                  <input type="number" step="1" min="0" max="100" value={topKPercent} onChange={(e) => setTopKPercent(parseInt(e.target.value || "0", 10))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                </div>
                <div>
                  <label className="text-xs text-slate-500">允許 regime</label>
                  <select value={allowedRegimesMode} onChange={(e) => setAllowedRegimesMode(e.target.value as any)} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200">
                    <option value="all">全部 regime（all）</option>
                    <option value="bull_chop">只做 bull + chop</option>
                    <option value="bull_only">只做 bull</option>
                    <option value="bear_only">只做 bear</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-500">資金模式</label>
                  <select value={capitalMode} onChange={(e) => setCapitalMode(e.target.value as "classic_pyramid" | "reserve_90")} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200">
                    <option value="classic_pyramid">經典金字塔</option>
                    <option value="reserve_90">10/90 後守</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-500">試單倉位 (%)</label>
                  <input type="number" step="1" min="1" max="100" value={baseEntryFractionPct} onChange={(e) => setBaseEntryFractionPct(parseInt(e.target.value || "0", 10))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                </div>
                <div>
                  <label className="text-xs text-slate-500">後守啟動回撤 (%)</label>
                  <input type="number" step="1" min="1" max="95" value={reserveTriggerDrawdownPct} onChange={(e) => setReserveTriggerDrawdownPct(parseInt(e.target.value || "0", 10))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div><label className="text-xs text-slate-500">L1</label><input type="number" value={layer1} onChange={(e) => setLayer1(parseInt(e.target.value))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" /></div>
                <div><label className="text-xs text-slate-500">L2</label><input type="number" value={layer2} onChange={(e) => setLayer2(parseInt(e.target.value))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" /></div>
                <div><label className="text-xs text-slate-500">L3</label><input type="number" value={layer3} onChange={(e) => setLayer3(parseInt(e.target.value))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" /></div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div><label className="text-xs text-slate-500">止損 (%)</label><input type="number" value={stopLoss} onChange={(e) => setStopLoss(parseInt(e.target.value))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" /></div>
                <div><label className="text-xs text-slate-500">TP Bias (%)</label><input type="number" step="0.5" value={tpBias} onChange={(e) => setTpBias(parseFloat(e.target.value))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" /></div>
                <div><label className="text-xs text-slate-500">TP ROI (%)</label><input type="number" value={tpRoi} onChange={(e) => setTpRoi(parseInt(e.target.value))} className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" /></div>
              </div>
              <button onClick={handleRun} disabled={workspaceBusy} className={`w-full py-2 rounded-lg font-semibold text-sm ${workspaceBusy ? "bg-slate-700 text-slate-400" : "bg-blue-600 text-white hover:bg-blue-500"}`}>
                {running ? "⏳ 回測中..." : loadingStrategy ? "⏳ 載入策略中..." : initialLoading ? "⏳ 初始化中..." : "▶ 執行回測"}
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-slate-700/50 bg-slate-950/40 p-3 text-xs leading-5 text-slate-400">
            <div className="font-semibold text-slate-200">策略說明</div>
            <div className="mt-1">{activeMeta.description}</div>
            <div className="mt-2 border-t border-slate-800/80 pt-2 text-[11px] text-slate-500">{activeMeta.model_summary}</div>
          </div>
        </div>

        <div className="space-y-4 min-w-0">
          {error && <div className="bg-red-900/20 border border-red-700/50 rounded-xl p-4 text-red-400 text-sm">{error}</div>}

          <div className={activeTab === "workspace" ? "space-y-4" : "hidden"}>
            <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-4">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div className="flex flex-wrap items-end gap-3">
                  <div>
                    <div className="text-[11px] text-slate-500">圖表開始</div>
                    <input type="datetime-local" value={chartStart} onChange={(e) => setChartStart(e.target.value)} className="mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200" />
                  </div>
                  <div>
                    <div className="text-[11px] text-slate-500">圖表結束</div>
                    <input type="datetime-local" value={chartEnd} onChange={(e) => setChartEnd(e.target.value)} className="mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200" />
                  </div>
                </div>
                <div className="grid min-w-[280px] gap-2 text-[11px] text-slate-400 sm:grid-cols-2">
                  <div className="rounded-lg border border-slate-700/50 bg-slate-950/40 px-3 py-2">
                    <div>回測完成：{activeResult?.run_at ? new Date(activeResult.run_at).toLocaleString("zh-TW") : "—"}</div>
                    <div>交易筆數：{activeResult?.total_trades ?? "—"}</div>
                  </div>
                  <div className="rounded-lg border border-cyan-700/30 bg-cyan-950/10 px-3 py-2 text-cyan-100">
                    <div className="font-medium">圖表判讀方式</div>
                    <div>上圖看 BTC/USDT 價格、買賣點與模型/進場分數；下圖看策略權益、倉位與買賣點，hover / tips 應同步。</div>
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

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-slate-300">🧭 綜合能力</div>
                    <div className="text-[11px] text-slate-500">用 Leaderboard 2.0 的五維能力看策略。</div>
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
                    <div className="text-[11px] text-slate-500">保留表格 + 象限圖，刪掉重複說明與過多小卡。</div>
                  </div>
                  <button onClick={loadLeaderboard} className="text-xs text-blue-400 hover:text-blue-300">🔄 刷新</button>
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
                          { key: "max_drawdown", label: "Max DD" },
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
                              <div>{strategy.name}</div>
                              <div className="mt-1 text-[10px] text-slate-500">{strategy.metadata?.model_name || strategy.definition?.type} · 變化 {typeof strategy.rank_delta === "number" ? (strategy.rank_delta > 0 ? `↑${strategy.rank_delta}` : strategy.rank_delta < 0 ? `↓${Math.abs(strategy.rank_delta)}` : "—") : "—"}</div>
                            </td>
                            <td className="py-2 px-2 text-right text-emerald-300 font-semibold">{formatDecimal(r?.overall_score, 3)}</td>
                            <td className="py-2 px-2 text-right text-cyan-300">{formatDecimal(r?.reliability_score, 3)}</td>
                            <td className="py-2 px-2 text-right text-violet-300">{formatDecimal(r?.return_power_score, 3)}</td>
                            <td className="py-2 px-2 text-right text-amber-300">{formatDecimal(r?.risk_control_score, 3)}</td>
                            <td className="py-2 px-2 text-right text-fuchsia-300">{formatDecimal(r?.capital_efficiency_score, 3)}</td>
                            <td className={`py-2 px-2 text-right ${isFiniteNumber(r?.roi) && (r?.roi ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>{formatPct(r?.roi, 1, true)}</td>
                            <td className="py-2 px-2 text-right text-red-300">{formatPct(r?.max_drawdown)}</td>
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
                <div className="overflow-auto rounded-lg border border-slate-700/40">
                  <table className="w-full min-w-[760px] text-xs">
                    <thead className="bg-slate-950/30 text-slate-500 border-b border-slate-800">
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
                          <th key={col.key} className="px-2 py-2 text-right first:text-left">
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
                      {sortedModelLeaderboard.map((model, idx) => (
                        <tr key={model.model_name} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                          <td className="px-2 py-2 text-left text-slate-200 font-medium">
                            <div>#{idx + 1} {model.model_name}</div>
                            <div className="mt-1 text-[10px] text-slate-500">{typeof model.rank_delta === "number" ? (model.rank_delta > 0 ? `↑${model.rank_delta}` : model.rank_delta < 0 ? `↓${Math.abs(model.rank_delta)}` : "—") : "—"}</div>
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
                    {(strategyMeta.snapshot_history || []).slice(0, 3).map((row) => (
                      <div key={`strategy-${row.id}`} className="rounded border border-slate-700/30 bg-slate-800/20 p-2">策略 #{row.id} · {new Date(row.created_at).toLocaleString("zh-TW")}</div>
                    ))}
                    {(modelMeta.snapshot_history || []).slice(0, 3).map((row) => (
                      <div key={`model-${row.id}`} className="rounded border border-slate-700/30 bg-slate-800/20 p-2">模型 #{row.id} · {new Date(row.created_at).toLocaleString("zh-TW")}</div>
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
