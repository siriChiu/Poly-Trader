import { useEffect, useMemo, useState } from "react";
import CandlestickChart from "../components/CandlestickChart";
import { fetchApi } from "../hooks/useApi";
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

interface StrategyResult {
  roi: number;
  win_rate: number;
  total_trades: number;
  wins: number;
  losses: number;
  max_drawdown: number;
  profit_factor: number;
  total_pnl: number;
  max_consecutive_losses?: number;
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
  regime_breakdown?: RegimeBreakdownEntry[];
  benchmarks?: {
    buy_hold?: BenchmarkEntry;
    blind_pyramid?: BenchmarkEntry;
  };
  equity_curve?: EquityPoint[];
  trades?: StrategyTrade[];
  chart_context?: ChartContext;
  run_at?: string;
}

interface StrategyEntry {
  name: string;
  created_at: string;
  definition: { type: string; params: Record<string, any> };
  metadata?: StrategyMetadata;
  last_results?: StrategyResult;
  run_count: number;
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
}

interface StrategyLeaderboardMeta {
  target_col?: string | null;
  target_label?: string | null;
  sort_semantics?: string | null;
}

interface ModelStatsResponse {
  model_loaded?: boolean;
  sample_count?: number;
  cv_accuracy?: number | null;
  feature_importance?: Record<string, number>;
  ic_values?: Record<string, number>;
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
  },
  layers: [0.2, 0.3, 0.5],
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
  return reasons.slice(0, 3).join(" · ") || `ROI ${formatPct(model.avg_roi, 1, true)} · 勝率 ${formatPct(model.avg_win_rate)}`;
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
  return reasons.slice(0, 3).join(" · ") || `ROI ${formatPct(result.roi, 1, true)} · 勝率 ${formatPct(result.win_rate)}`;
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

const toMillis = (value?: string | null) => {
  if (!value) return null;
  const ms = new Date(value).getTime();
  return Number.isFinite(ms) ? ms : null;
};

export default function StrategyLab() {
  const [strategies, setStrategies] = useState<StrategyEntry[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyEntry | null>(null);
  const [strategyMeta, setStrategyMeta] = useState<StrategyLeaderboardMeta>({});
  const [modelLeaderboard, setModelLeaderboard] = useState<ModelLeaderboardEntry[]>([]);
  const [targetComparison, setTargetComparison] = useState<TargetComparisonEntry[]>([]);
  const [modelMeta, setModelMeta] = useState<ModelLeaderboardMeta>({});
  const [modelStats, setModelStats] = useState<ModelStatsResponse | null>(null);
  const [running, setRunning] = useState(false);
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
  const [stopLoss, setStopLoss] = useState(-5);
  const [tpBias, setTpBias] = useState(4.0);
  const [tpRoi, setTpRoi] = useState(8);
  const [chartStart, setChartStart] = useState<string>("");
  const [chartEnd, setChartEnd] = useState<string>("");

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
  const recommendedModels = useMemo(() => modelLeaderboard.filter((m) => !m.is_overfit), [modelLeaderboard]);
  const eliminatedModels = useMemo(() => modelLeaderboard.filter((m) => m.is_overfit), [modelLeaderboard]);
  const topRecommendedModel = recommendedModels[0] ?? modelLeaderboard[0] ?? null;
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
    setLayer1(Math.round((layers[0] ?? DEFAULT_PARAMS.layers[0]) * 100));
    setLayer2(Math.round((layers[1] ?? DEFAULT_PARAMS.layers[1]) * 100));
    setLayer3(Math.round((layers[2] ?? DEFAULT_PARAMS.layers[2]) * 100));
    setStopLoss(Math.round((params.stop_loss ?? DEFAULT_PARAMS.stop_loss) * 100));
    setTpBias(params.take_profit_bias ?? DEFAULT_PARAMS.take_profit_bias);
    setTpRoi(Math.round((params.take_profit_roi ?? DEFAULT_PARAMS.take_profit_roi) * 100));
  };

  const selectStrategyByName = async (strategyName: string) => {
    try {
      const detail = await fetchApi(`/api/strategies/${encodeURIComponent(strategyName)}`) as StrategyEntry;
      setSelectedStrategy(detail);
      setRunResult(null);
      applyStrategyToForm(detail);
    } catch (err: any) {
      setError(err.message || "讀取策略失敗");
    }
  };

  const loadLeaderboard = async () => {
    try {
      const res = await fetchApi("/api/strategies/leaderboard") as any;
      const list = res?.strategies ?? res?.data?.strategies ?? (Array.isArray(res) ? res : []);
      setStrategies(list || []);
      setStrategyMeta({
        target_col: res?.target_col ?? res?.data?.target_col ?? "simulated_pyramid_win",
        target_label: res?.target_label ?? res?.data?.target_label ?? "Canonical Decision Quality",
        sort_semantics: res?.sort_semantics ?? res?.data?.sort_semantics ?? null,
      });
      if (!selectedStrategy && list?.length) {
        selectStrategyByName(list[0].name);
      }
    } catch (err: any) {
      console.error("Leaderboard error:", err);
    }
  };

  const loadModelLeaderboard = async (forceRefresh = false) => {
    try {
      const data = await fetchApi(`/api/models/leaderboard${forceRefresh ? "?refresh=true" : ""}`) as any;
      setModelLeaderboard(Array.isArray(data?.leaderboard) ? data.leaderboard : []);
      setTargetComparison(Array.isArray(data?.target_comparison) ? data.target_comparison : []);
      setModelMeta({
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
      });
    } catch (err) {
      console.error("Model leaderboard error:", err);
      setModelMeta({ error: "模型排行榜載入失敗" });
    }
  };

  const loadModelStats = async () => {
    try {
      const data = await fetchApi("/api/model/stats") as ModelStatsResponse;
      setModelStats(data);
    } catch (err) {
      console.error("Model stats error:", err);
    }
  };

  useEffect(() => {
    loadLeaderboard();
    loadModelLeaderboard();
    loadModelStats();
  }, []);

  useEffect(() => {
    if (!modelMeta.refreshing && !modelMeta.stale) return;
    const timer = window.setInterval(() => {
      loadModelLeaderboard(false);
      loadModelStats();
    }, 2500);
    return () => window.clearInterval(timer);
  }, [modelMeta.refreshing, modelMeta.stale]);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
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
          },
          layers: [layer1 / 100, layer2 / 100, layer3 / 100],
          stop_loss: stopLoss / 100,
          take_profit_bias: tpBias,
          take_profit_roi: tpRoi / 100,
        },
      };
      const data = await fetchApi("/api/strategies/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }) as any;
      if (data?.error) {
        setError(data.error);
      } else {
        const result = data?.results ?? data?.result ?? data?.run_result ?? null;
        const enrichedResult = result
          ? {
              ...result,
              equity_curve: Array.isArray(data?.equity_curve) ? data.equity_curve : result.equity_curve,
              trades: Array.isArray(data?.trades) ? data.trades : result.trades,
              chart_context: data?.chart_context ?? result?.chart_context,
            }
          : null;
        setRunResult(enrichedResult);
        await loadLeaderboard();
        await loadModelStats();
        await selectStrategyByName(name);
      }
    } catch (err: any) {
      setError(err.message || "Execution failed");
    }
    setRunning(false);
  };

  const presets = [
    { label: "🔥 金字塔+SL/TP", params: { bias50Max: 1.0, noseMax: 0.4, layer2Bias: -1.5, layer3Bias: -3.5, stopLoss: -5, tpBias: 4, tpRoi: 8, l1: 20, l2: 30, l3: 50 } },
    { label: "🌀 Fib 23/38/39", params: { bias50Max: -1.0, noseMax: 0.35, layer2Bias: -2.8, layer3Bias: -5.0, stopLoss: -5, tpBias: 4.5, tpRoi: 8, l1: 23, l2: 38, l3: 39 } },
  ];

  const applyPreset = (preset: any) => {
    setBias50Max(preset.params.bias50Max);
    setNoseMax(preset.params.noseMax);
    setLayer2Bias(preset.params.layer2Bias);
    setLayer3Bias(preset.params.layer3Bias);
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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-200">🧪 策略實驗室</h2>
        <span className="text-xs text-slate-500">排行榜點一下，左側設定就會自動切換</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[360px,minmax(0,1fr)] 2xl:grid-cols-[380px,minmax(0,1fr)] gap-4 items-start">
        <div className="space-y-4 self-start min-w-0">
          <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4">
            <h3 className="text-sm font-semibold text-slate-300">⚙️ 參數設定</h3>
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
              <button onClick={handleRun} disabled={running} className={`w-full py-2 rounded-lg font-semibold text-sm ${running ? "bg-slate-700 text-slate-400" : "bg-blue-600 text-white hover:bg-blue-500"}`}>
                {running ? "⏳ 回測中..." : "▶ 執行回測"}
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-slate-700/50 bg-slate-950/40 p-3 space-y-2">
            <div className="text-xs uppercase tracking-wide text-slate-500">策略介紹</div>
            <div className="text-sm font-semibold text-slate-200">{activeMeta.title}</div>
            <div className="text-xs leading-5 text-slate-400">{activeMeta.description}</div>
            <div className="pt-2 border-t border-slate-800/80">
              <div className="text-[11px] text-slate-500">交易模型</div>
              <div className="text-sm text-emerald-300">{activeMeta.model_name || "rule_based"}</div>
              <div className="text-xs leading-5 text-slate-400 mt-1">{activeMeta.model_summary}</div>
            </div>
          </div>
        </div>

        <div className="space-y-4 min-w-0">
          {error && <div className="bg-red-900/20 border border-red-700/50 rounded-xl p-4 text-red-400 text-sm">{error}</div>}

          <div className="grid grid-cols-1 2xl:grid-cols-3 gap-4">
            <div className="2xl:col-span-2 space-y-3">
              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-3 flex flex-wrap items-end gap-3">
                <div>
                  <div className="text-[11px] text-slate-500">圖表開始</div>
                  <input type="datetime-local" value={chartStart} onChange={(e) => setChartStart(e.target.value)} className="mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200" />
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">圖表結束</div>
                  <input type="datetime-local" value={chartEnd} onChange={(e) => setChartEnd(e.target.value)} className="mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200" />
                </div>
                <div className="min-w-[220px] rounded-lg border border-slate-700/50 bg-slate-950/40 px-3 py-2 text-[11px] text-slate-400">
                  <div>回測完成：{activeResult?.run_at ? new Date(activeResult.run_at).toLocaleString("zh-TW") : "—"}</div>
                  <div>目前顯示：價格 + 策略曲線 + 買賣 markers</div>
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
                title={`${activeMeta.title || name} 回測圖`}
              />
            </div>
            <div className="space-y-3">
              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 grid grid-cols-2 gap-3">
                {[
                  { label: "ROI", value: formatPct(activeResult?.roi, 1, true), color: isFiniteNumber(activeResult?.roi) && (activeResult?.roi ?? 0) >= 0 ? "text-green-400" : "text-red-400" },
                  { label: "勝率", value: formatPct(activeResult?.win_rate), color: "text-emerald-300" },
                  { label: "交易次數", value: `${activeResult?.total_trades ?? "—"}`, color: "text-slate-200" },
                  { label: "PF", value: formatDecimal(activeResult?.profit_factor), color: "text-violet-300" },
                  { label: "最大回撤", value: formatPct(activeResult?.max_drawdown), color: "text-red-400" },
                  { label: "總損益", value: formatMoney(activeResult?.total_pnl), color: isFiniteNumber(activeResult?.total_pnl) && (activeResult?.total_pnl ?? 0) >= 0 ? "text-green-400" : "text-red-400" },
                  { label: "平均進場品質", value: formatDecimal(activeResult?.avg_entry_quality, 2), color: "text-cyan-300" },
                  { label: "平均允許層數", value: formatDecimal(activeResult?.avg_allowed_layers, 1), color: "text-fuchsia-300" },
                ].map((card) => (
                  <div key={card.label} className="bg-slate-800/50 rounded-lg p-3">
                    <div className="text-[11px] text-slate-500">{card.label}</div>
                    <div className={`text-lg font-bold ${card.color}`}>{card.value}</div>
                  </div>
                ))}
              </div>

              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold text-slate-300">🧭 決策檔位</div>
                  <div className="text-xs text-slate-500">主 gate：{activeResult?.dominant_regime_gate || "—"}</div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  {[
                    { gate: "ALLOW", color: "text-emerald-300" },
                    { gate: "CAUTION", color: "text-yellow-300" },
                    { gate: "BLOCK", color: "text-red-300" },
                  ].map(({ gate, color }) => (
                    <div key={gate} className="rounded bg-slate-800/40 p-2">
                      <div className="text-slate-500">{gate}</div>
                      <div className={`text-lg font-semibold ${color}`}>{activeResult?.regime_gate_summary?.[gate] ?? 0}</div>
                    </div>
                  ))}
                </div>
                <div className="text-[11px] leading-5 text-slate-500">這個區塊用來看目前策略回測中，多數交易是在 ALLOW、CAUTION 還是 BLOCK 背景下觸發，並搭配平均進場品質與允許層數一起判讀。</div>
              </div>

              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <div className="text-sm font-semibold text-slate-300">🧠 訓練成績</div>
                <div className="text-xs text-slate-400 leading-5">
                  這裡直接顯示你在 log 裡看到的全局與分 regime 訓練/驗證成績。
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded bg-slate-800/50 p-2"><div className="text-slate-500">Global Train</div><div className="text-emerald-300 font-semibold">{formatPct(modelMeta.global_metrics?.train_accuracy)}</div></div>
                  <div className="rounded bg-slate-800/50 p-2"><div className="text-slate-500">Global CV</div><div className="text-sky-300 font-semibold">{formatPct(modelMeta.global_metrics?.cv_accuracy)}</div></div>
                  <div className="rounded bg-slate-800/50 p-2"><div className="text-slate-500">CV 波動</div><div className="text-slate-200 font-semibold">{formatPct(modelMeta.global_metrics?.cv_std)}</div></div>
                  <div className="rounded bg-slate-800/50 p-2"><div className="text-slate-500">樣本數</div><div className="text-slate-200 font-semibold">{modelMeta.global_metrics?.n_samples ?? "—"}</div></div>
                </div>
                <div className="space-y-2 text-xs">
                  {Object.entries(modelMeta.regime_metrics || {}).map(([regime, stats]) => (
                    <div key={regime} className="rounded bg-slate-800/40 p-2 flex items-center justify-between gap-2">
                      <span className="text-slate-300 font-medium">{regimeLabelMap[regime] ?? regime}</span>
                      <span className="text-slate-400">CV {formatPct(stats.cv_accuracy)}</span>
                      <span className="text-slate-400">Train {formatPct(stats.train_accuracy)}</span>
                      <span className="text-slate-400">n={stats.n_samples ?? "—"}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-slate-300">⚔️ 技術指標競爭力</div>
                    <div className="text-xs text-slate-500">拆成短線節奏與 4H 結構雙榜，避免全部擠成一塊難判讀。</div>
                  </div>
                  <div className="text-[11px] text-slate-500">樣本 {modelStats?.sample_count ?? "—"}</div>
                </div>
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                  {[
                    { title: "短線節奏 Top", tone: "text-cyan-300", rows: shortTermCompetitiveIndicators },
                    { title: "4H 結構 Top", tone: "text-fuchsia-300", rows: structureCompetitiveIndicators },
                  ].map((section) => (
                    <div key={section.title} className="rounded-xl border border-slate-700/40 bg-slate-950/30 p-3 space-y-2">
                      <div className={`text-sm font-semibold ${section.tone}`}>{section.title}</div>
                      {section.rows.length > 0 ? section.rows.map((row, idx) => (
                        <div key={row.key} className="rounded-lg border border-slate-700/30 bg-slate-800/30 px-3 py-2">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="text-[10px] text-slate-500">#{idx + 1}</div>
                              <div className="text-sm font-medium text-slate-100">{row.label}</div>
                            </div>
                            <div className="text-right text-[11px]">
                              <div className="text-emerald-300">IC {row.ic !== null ? row.ic.toFixed(3) : "—"}</div>
                              <div className="text-sky-300">Imp {row.importance !== null ? row.importance.toFixed(3) : "—"}</div>
                            </div>
                          </div>
                          <div className="mt-1 line-clamp-2 text-[11px] leading-5 text-slate-400">{row.description}</div>
                        </div>
                      )) : (
                        <div className="rounded-lg border border-slate-700/40 bg-slate-800/20 p-3 text-xs text-slate-400">尚未載入該分組的 IC / importance。</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 2xl:grid-cols-3 gap-4">
            <div className="2xl:col-span-2 bg-slate-900/60 rounded-xl border border-slate-700/50 p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-300">🏆 策略排行榜</h3>
                <button onClick={loadLeaderboard} className="text-xs text-blue-400 hover:text-blue-300">🔄 刷新</button>
              </div>
              <div className="mb-3 rounded border border-cyan-700/30 bg-cyan-950/10 p-3 text-xs space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-cyan-200 font-medium">Canonical 策略排序語義</span>
                  <span className="text-[10px] text-cyan-300">{strategyMeta.target_label || strategyMeta.target_col || "simulated_pyramid_win"}</span>
                </div>
                <div className="text-slate-400 leading-5">策略排行榜不再只看 ROI。現在會優先比較實際 trade entry timestamps 對齊出的 decision-quality、預期勝率與 drawdown / underwater 懲罰，再用 ROI 當次排序。</div>
                {strategyMeta.sort_semantics && <div className="text-[11px] text-slate-500">排序：{strategyMeta.sort_semantics}</div>}
                {strategies[0]?.last_results && (
                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <div className="rounded bg-slate-900/40 px-2 py-2">
                      <div className="text-[10px] text-slate-500">目前第一名</div>
                      <div className="text-sm font-semibold text-slate-100">{strategies[0].name}</div>
                      <div className={`text-sm font-semibold ${decisionQualityTone(strategies[0].last_results?.avg_decision_quality_score)}`}>
                        DQ {formatDecimal(strategies[0].last_results?.avg_decision_quality_score, 3)}
                      </div>
                    </div>
                    <div className="rounded bg-slate-900/40 px-2 py-2">
                      <div className="text-[10px] text-slate-500">canonical ranking reason</div>
                      <div className="text-slate-200">{describeStrategyRankingReason(strategies[0].last_results)}</div>
                    </div>
                  </div>
                )}
              </div>
              <div className="overflow-auto">
                <table className="w-full text-xs min-w-[980px]">
                  <thead className="text-slate-500 border-b border-slate-800">
                    <tr>
                      <th className="text-left py-2 px-2">#</th>
                      <th className="text-left py-2 px-2">策略</th>
                      <th className="text-right py-2 px-2">DQ</th>
                      <th className="text-right py-2 px-2">預期勝率</th>
                      <th className="text-right py-2 px-2">DD / UW</th>
                      <th className="text-right py-2 px-2">層數 / 品質</th>
                      <th className="text-right py-2 px-2">ROI / PF</th>
                      <th className="text-right py-2 px-2">穩定度</th>
                    </tr>
                  </thead>
                  <tbody>
                    {strategies.map((strategy, idx) => {
                      const r = strategy.last_results;
                      const selected = strategy.name === selectedStrategy?.name;
                      return (
                        <tr key={strategy.name} onClick={() => selectStrategyByName(strategy.name)} className={`cursor-pointer border-b border-slate-800/50 ${selected ? "bg-sky-950/30" : "hover:bg-slate-800/30"}`}>
                          <td className="py-2 px-2 text-slate-500">{idx + 1}</td>
                          <td className="py-2 px-2 text-slate-200 font-medium align-top">
                            <div>{strategy.name} <span className="ml-1 text-[10px] text-slate-500">(x{strategy.run_count})</span></div>
                            <div className="mt-1 text-[11px] text-slate-500">{strategy.metadata?.model_name || strategy.definition?.type}</div>
                            <div className="mt-1 text-[11px] text-slate-500">{describeStrategyRankingReason(r)}</div>
                          </td>
                          <td className={`py-2 px-2 text-right font-semibold ${decisionQualityTone(r?.avg_decision_quality_score)}`}>
                            {formatDecimal(r?.avg_decision_quality_score, 3)}
                            <div className="mt-1 text-[10px] text-slate-500">{r?.decision_quality_label || "—"}</div>
                          </td>
                          <td className="py-2 px-2 text-right text-emerald-300">
                            {formatPct(r?.avg_expected_win_rate)}
                            <div className="mt-1 text-[10px] text-slate-500">n={r?.decision_quality_sample_size ?? 0}</div>
                          </td>
                          <td className="py-2 px-2 text-right text-amber-300">
                            {formatPct(r?.avg_expected_drawdown_penalty)}
                            <div className="mt-1 text-[10px] text-slate-500">UW {formatPct(r?.avg_expected_time_underwater)}</div>
                          </td>
                          <td className="py-2 px-2 text-right text-fuchsia-300">
                            {formatDecimal(r?.avg_allowed_layers, 1)}
                            <div className="mt-1 text-[10px] text-slate-500">Q {formatDecimal(r?.avg_entry_quality, 2)} · {r?.dominant_regime_gate || "—"}</div>
                          </td>
                          <td className="py-2 px-2 text-right">
                            <div className={`${isFiniteNumber(r?.roi) && (r?.roi ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>{formatPct(r?.roi, 1, true)}</div>
                            <div className="mt-1 text-[10px] text-slate-500">PF {formatDecimal(r?.profit_factor)} · {r?.total_trades ?? "—"} trades</div>
                          </td>
                          <td className="py-2 px-2 text-right align-top">
                            <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] ${strategyRiskTone[strategy.overfit_risk ?? "unknown"]}`}>{strategyRiskLabel[strategy.overfit_risk ?? "unknown"]}</span>
                            <div className="mt-1 text-[10px] text-slate-500">{sufficiencyLabel[strategy.trade_sufficiency ?? "unknown"]}</div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-3">
              <h3 className="text-sm font-semibold text-slate-300">🤖 模型排行榜</h3>
              <div className="text-[11px] text-slate-500">{modelMeta.refreshing ? "背景重算中，先顯示快取結果…" : modelMeta.updated_at ? `上次更新 ${new Date(modelMeta.updated_at).toLocaleString("zh-TW")}` : "尚未建立快取"}</div>
              <div className="rounded border border-cyan-700/30 bg-cyan-950/10 p-3 text-xs space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-cyan-200 font-medium">Canonical 排序語義</span>
                  <span className="text-[10px] text-cyan-300">{modelMeta.target_label || modelMeta.target_col || "simulated_pyramid_win"}</span>
                </div>
                <div className="text-slate-400 leading-5">前端現在直接顯示 decision-quality、預期勝率、回撤懲罰與深套時間，不再只用 ROI / gap 猜模型為何排前面。</div>
                {topRecommendedModel && (
                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <div className="rounded bg-slate-900/40 px-2 py-2">
                      <div className="text-[10px] text-slate-500">目前第一名</div>
                      <div className="text-sm font-semibold text-slate-100">{topRecommendedModel.model_name}</div>
                      <div className={`text-sm font-semibold ${decisionQualityTone(topRecommendedModel.avg_decision_quality_score)}`}>
                        DQ {formatDecimal(topRecommendedModel.avg_decision_quality_score, 3)}
                      </div>
                    </div>
                    <div className="rounded bg-slate-900/40 px-2 py-2">
                      <div className="text-[10px] text-slate-500">決策語義</div>
                      <div className="text-slate-200">勝率 {formatPct(topRecommendedModel.avg_expected_win_rate)}</div>
                      <div className="text-slate-400">DD {formatPct(topRecommendedModel.avg_expected_drawdown_penalty)} / UW {formatPct(topRecommendedModel.avg_expected_time_underwater)}</div>
                    </div>
                  </div>
                )}
              </div>
              <div className="space-y-2">
                {recommendedModels.slice(0, 5).map((model) => (
                  <div key={model.model_name} className="rounded border border-slate-700/40 bg-slate-800/30 p-3 text-xs space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-slate-200 font-medium">{model.model_name}</span>
                      <span className={`font-semibold ${decisionQualityTone(model.avg_decision_quality_score)}`}>
                        DQ {formatDecimal(model.avg_decision_quality_score, 3)}
                      </span>
                    </div>
                    <div className="text-slate-500">{describeRankingReason(model)}</div>
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div className="rounded bg-slate-900/40 px-2 py-1.5">
                        <div className="text-slate-500">預期勝率 / 品質</div>
                        <div className="text-emerald-300">{formatPct(model.avg_expected_win_rate)} / {formatDecimal(model.avg_expected_pyramid_quality, 3)}</div>
                      </div>
                      <div className="rounded bg-slate-900/40 px-2 py-1.5">
                        <div className="text-slate-500">回撤 / 深套</div>
                        <div className="text-amber-300">{formatPct(model.avg_expected_drawdown_penalty)} / {formatPct(model.avg_expected_time_underwater)}</div>
                      </div>
                      <div className="rounded bg-slate-900/40 px-2 py-1.5">
                        <div className="text-slate-500">允許層數 / 進場品質</div>
                        <div className="text-fuchsia-300">{formatDecimal(model.avg_allowed_layers, 1)} / {formatDecimal(model.avg_entry_quality, 2)}</div>
                      </div>
                      <div className="rounded bg-slate-900/40 px-2 py-1.5">
                        <div className="text-slate-500">ROI / Gap</div>
                        <div className="text-slate-200">{formatPct(model.avg_roi, 1, true)} / {(model.train_test_gap * 100).toFixed(1)}pp</div>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-500">
                      <span>PF {formatDecimal(model.profit_factor)} · 交易 {formatDecimal(model.avg_trades, 0)}</span>
                      <span>回撤懲罰評語：{formatPenaltyHint(model.avg_expected_drawdown_penalty)}</span>
                    </div>
                  </div>
                ))}
              </div>
              {(modelMeta.skipped_models || []).length > 0 && (
                <div className="rounded border border-amber-700/30 bg-amber-900/10 p-3 text-xs text-amber-200">
                  <div className="font-semibold mb-2">未納入排行的模型</div>
                  <div className="space-y-1">
                    {(modelMeta.skipped_models || []).map((row) => (
                      <div key={row.model_name}>{row.model_name}：{row.reason === "missing_dependency" ? "缺依賴" : "資料不足"}{row.detail ? ` (${row.detail})` : ""}</div>
                    ))}
                  </div>
                </div>
              )}
              {eliminatedModels.length > 0 && <div className="text-[11px] text-red-300">已淘汰過擬合模型 {eliminatedModels.length} 個</div>}
            </div>
          </div>

          <div className="grid grid-cols-1 2xl:grid-cols-3 gap-4">
            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
              <h3 className="text-sm font-semibold text-slate-300 mb-3">📈 基準對比</h3>
              <div className="grid grid-cols-1 gap-3 text-xs">
                {benchmarkCards.map((card) => (
                  <div key={card.label} className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/40">
                    <div className="text-slate-400">{card.label}</div>
                    <div className={`mt-2 text-2xl font-bold ${isFiniteNumber(card.roi) && (card.roi ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>{formatPct(card.roi, 1, true)}</div>
                    <div className="mt-2 space-y-1 text-[11px] text-slate-500">
                      <div>勝率：{formatPct(card.win_rate, 1)}</div>
                      <div>交易：{card.total_trades ?? "—"}</div>
                      <div>PF：{formatDecimal(card.profit_factor)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
              <h3 className="text-sm font-semibold text-slate-300 mb-3">🧭 Regime 回測</h3>
              <div className="space-y-2 text-xs">
                {(activeResult?.regime_breakdown || []).map((row) => (
                  <div key={row.regime} className="rounded border border-slate-700/40 bg-slate-800/20 p-3">
                    <div className="flex justify-between"><span className="text-slate-200">{regimeLabelMap[row.regime] ?? row.regime}</span><span className="text-slate-400">{row.trades} trades</span></div>
                    <div className="mt-1 text-slate-500">勝率 {formatPct(row.win_rate)} · ROI {formatPct(row.roi, 1, true)} · PF {formatDecimal(row.profit_factor)}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
              <h3 className="text-sm font-semibold text-slate-300 mb-3">🧾 最近交易</h3>
              <div className="space-y-2 max-h-[340px] overflow-auto text-xs">
                {(activeResult?.trades || []).slice(-20).reverse().map((trade, idx) => (
                  <div key={`${trade.timestamp || trade.entry_timestamp}-${idx}`} className="rounded border border-slate-700/40 bg-slate-800/20 p-3">
                    <div className="flex justify-between gap-3">
                      <span className="text-slate-200">{trade.entry_timestamp || trade.timestamp ? new Date((trade.entry_timestamp || trade.timestamp) as string).toLocaleString("zh-TW") : "—"}</span>
                      <span className={`${isFiniteNumber(trade.pnl) && (trade.pnl ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>{isFiniteNumber(trade.pnl) ? `${trade.pnl! >= 0 ? "+" : ""}${trade.pnl!.toFixed(2)}` : "—"}</span>
                    </div>
                    <div className="mt-1 text-slate-500">進場 {isFiniteNumber(trade.entry) ? trade.entry!.toFixed(2) : "—"} → 出場 {isFiniteNumber(trade.exit) ? trade.exit!.toFixed(2) : "—"}</div>
                    <div className="mt-1 text-slate-500">原因 {trade.reason || "—"} · 層數 {trade.layers ?? "—"} · Regime {regimeLabelMap[trade.entry_regime || "unknown"] ?? trade.entry_regime}</div>
                    <div className="mt-1 text-slate-500">Gate {trade.regime_gate || "—"} · 品質 {isFiniteNumber(trade.entry_quality) ? trade.entry_quality.toFixed(2) : "—"} · 允許層數 {trade.allowed_layers ?? "—"}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {targetComparison.length > 0 && (
            <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 text-xs text-slate-400 space-y-2">
              <div className="font-semibold text-slate-300">🎯 Target 比較</div>
              {targetComparison.map((entry) => (
                <div key={entry.target_col} className="flex flex-wrap gap-3">
                  <span className="text-emerald-300">{entry.label}</span>
                  <span>樣本 {entry.samples}</span>
                  <span>正例 {formatPct(entry.positive_ratio, 1)}</span>
                  <span>最佳 {entry.best_model?.model_name || "—"}</span>
                  <span>{entry.usage_note}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
