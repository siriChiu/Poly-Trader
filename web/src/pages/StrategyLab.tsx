import { useState, useEffect, useMemo } from "react";
import { fetchApi } from "../hooks/useApi";

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
  regime_breakdown?: RegimeBreakdownEntry[];
  benchmarks?: {
    buy_hold?: BenchmarkEntry;
    blind_pyramid?: BenchmarkEntry;
  };
  run_at?: string;
}

interface StrategyEntry {
  name: string;
  created_at: string;
  definition: { type: string; params: Record<string, any> };
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
  is_overfit?: boolean;
  overfit_reason?: string | null;
  folds: Array<{
    fold: number;
    roi: number;
    win_rate: number;
    trades: number;
    max_dd: number;
    profit_factor: number;
  }>;
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
}

const DEFAULT_PARAMS = {
  entry: {
    bias50_max: 1.0,
    nose_max: 0.40,
    pulse_min: 0.0,
    layer2_bias_max: -1.5,
    layer3_bias_max: -3.5,
  },
  layers: [0.20, 0.30, 0.50],
  stop_loss: -0.05,
  take_profit_bias: 4.0,
  take_profit_roi: 0.08,
};

const isFiniteNumber = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);

const formatPct = (value: number | null | undefined, digits = 1, signed = false) => {
  if (!isFiniteNumber(value)) return "—";
  const prefix = signed && value > 0 ? "+" : "";
  return `${prefix}${(value * 100).toFixed(digits)}%`;
};

const formatDecimal = (value: number | null | undefined, digits = 2) => {
  if (!isFiniteNumber(value)) return "—";
  return value.toFixed(digits);
};

const formatMoney = (value: number | null | undefined) => {
  if (!isFiniteNumber(value)) return "—";
  return `USDT ${value > 0 ? "+" : ""}${value.toFixed(0)}`;
};

const regimeLabelMap: Record<string, string> = {
  bull: "牛市",
  bear: "熊市",
  chop: "盤整",
  unknown: "未知",
};

const strategyRiskTone: Record<string, string> = {
  low: "text-emerald-300 bg-emerald-900/20 border-emerald-700/30",
  medium: "text-yellow-300 bg-yellow-900/20 border-yellow-700/30",
  high: "text-red-300 bg-red-900/20 border-red-700/30",
  unknown: "text-slate-300 bg-slate-800/50 border-slate-700/40",
};

const strategyRiskLabel: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
  unknown: "—",
};

const sufficiencyLabel: Record<string, string> = {
  high: "充足",
  medium: "普通",
  low: "不足",
  unknown: "—",
};

const OVERFIT_GAP_THRESHOLD = 0.12;

export default function StrategyLab() {
  const [strategies, setStrategies] = useState<StrategyEntry[]>([]);
  const [modelLeaderboard, setModelLeaderboard] = useState<ModelLeaderboardEntry[]>([]);
  const [targetComparison, setTargetComparison] = useState<TargetComparisonEntry[]>([]);
  const [modelMeta, setModelMeta] = useState<ModelLeaderboardMeta>({});
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<StrategyResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Strategy params
  const [name, setName] = useState("My Strategy");
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

  const loadLeaderboard = async () => {
    try {
      const res = await fetchApi("/api/strategies/leaderboard");
      const data = res as any;
      // Handle multiple possible response formats: { strategies: [...] }, { data: { strategies: [...] } }, or direct array
      const list = data?.strategies ?? data?.data?.strategies ?? (Array.isArray(data) ? data : []);
      setStrategies(list || []);
    } catch (err: any) {
      console.error("Leaderboard error:", err);
    }
  };

  const loadModelLeaderboard = async (forceRefresh = false) => {
    try {
      const res = await fetchApi(`/api/models/leaderboard${forceRefresh ? "?refresh=true" : ""}`);
      const data = res as any;
      const list = data?.leaderboard ?? [];
      const comparison = data?.target_comparison ?? [];
      setModelLeaderboard(Array.isArray(list) ? list : []);
      setTargetComparison(Array.isArray(comparison) ? comparison : []);
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
      });
    } catch (err) {
      console.error("Model leaderboard error:", err);
      setModelLeaderboard([]);
      setTargetComparison([]);
      setModelMeta({ error: "模型排行榜載入失敗" });
    }
  };

  useEffect(() => {
    loadLeaderboard();
    loadModelLeaderboard();
  }, []);

  useEffect(() => {
    if (!modelMeta.refreshing) return;
    const timer = window.setTimeout(() => {
      loadModelLeaderboard(false);
    }, 2500);
    return () => window.clearTimeout(timer);
  }, [modelMeta.refreshing]);

  const recommendedModels = useMemo(
    () => modelLeaderboard.filter((m) => !m.is_overfit && m.train_test_gap <= OVERFIT_GAP_THRESHOLD),
    [modelLeaderboard]
  );

  const eliminatedModels = useMemo(
    () => modelLeaderboard.filter((m) => m.is_overfit || m.train_test_gap > OVERFIT_GAP_THRESHOLD),
    [modelLeaderboard]
  );

  const bestStrategyWinRate = useMemo(
    () => [...strategies]
      .filter((s) => isFiniteNumber(s.last_results?.win_rate))
      .sort((a, b) => (b.last_results?.win_rate ?? -1) - (a.last_results?.win_rate ?? -1))[0],
    [strategies]
  );

  const bestStrategyRoi = useMemo(
    () => [...strategies]
      .filter((s) => isFiniteNumber(s.last_results?.roi))
      .sort((a, b) => (b.last_results?.roi ?? -999) - (a.last_results?.roi ?? -999))[0],
    [strategies]
  );

  const bestModelWinRate = useMemo(
    () => [...recommendedModels]
      .filter((m) => isFiniteNumber(m.avg_win_rate))
      .sort((a, b) => b.avg_win_rate - a.avg_win_rate)[0],
    [recommendedModels]
  );

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setRunResult(null);
    try {
      const body = {
        name,
        type: "rule_based",
        params: {
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
      const res = await fetchApi("/api/strategies/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = res as any;
      if (data?.error) {
        setError(data.error);
      } else {
        // Handle multiple possible response field names: results, result, run_result
        const result = data?.results ?? data?.result ?? data?.run_result ?? null;
        setRunResult(result);

        // Optimistically add the strategy to the leaderboard
        const newEntry: StrategyEntry = {
          name,
          created_at: new Date().toISOString(),
          definition: { type: "rule_based", params: body.params },
          last_results: result,
          run_count: 1,
        };
        setStrategies(prev => {
          const existing = prev.find(s => s.name === name);
          if (existing) {
            return prev.map(s => s.name === name ? {
              ...s,
              definition: { type: "rule_based", params: body.params },
              last_results: result,
              run_count: existing.run_count + 1,
            } : s);
          }
          return [newEntry, ...prev];
        });

        await loadLeaderboard();
      }
    } catch (err: any) {
      setError(err.message || "Execution failed");
    }
    setRunning(false);
  };

  const presets = [
    {
      label: "🔥 金字塔+SL/TP",
      params: { bias50Max: 1.0, noseMax: 0.40, layer2Bias: -1.5, layer3Bias: -3.5, stopLoss: -5, tpBias: 4.0, tpRoi: 8, l1: 20, l2: 30, l3: 50 },
    },
    { label: "🛡️ 保守型", params: { bias50Max: -2.0, noseMax: 0.30, layer2Bias: -4.0, layer3Bias: -6.0, stopLoss: -3, tpBias: 5.0, tpRoi: 10, l1: 20, l2: 20, l3: 20 } },
    { label: "🚀 激進型", params: { bias50Max: 2.0, noseMax: 0.50, layer2Bias: -1.0, layer3Bias: -2.0, stopLoss: -8, tpBias: 3.0, tpRoi: 5, l1: 30, l2: 30, l3: 40 } },
    { label: "🌀 Fib 23/38/39", params: { bias50Max: -1.0, noseMax: 0.35, layer2Bias: -2.8, layer3Bias: -5.0, stopLoss: -5, tpBias: 4.5, tpRoi: 8, l1: 23, l2: 38, l3: 39 } },
  ];

  const applyPreset = (p: any) => {
    const p2 = p.params;
    setBias50Max(p2.bias50Max); setNoseMax(p2.noseMax);
    setLayer2Bias(p2.layer2Bias); setLayer3Bias(p2.layer3Bias);
    setStopLoss(p2.stopLoss); setTpBias(p2.tpBias); setTpRoi(p2.tpRoi);
    setLayer1(p2.l1); setLayer2(p2.l2); setLayer3(p2.l3);
  };

  const benchmarkCards = [
    runResult?.benchmarks?.buy_hold,
    runResult?.benchmarks?.blind_pyramid,
    runResult ? { label: "你的策略", roi: runResult.roi, win_rate: runResult.win_rate, total_pnl: runResult.total_pnl, profit_factor: runResult.profit_factor } : null,
  ].filter(Boolean) as BenchmarkEntry[];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-200">🧪 策略實驗室</h2>
        <span className="text-xs text-slate-500">參數即時回測</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* ─── LEFT: Params ─── */}
        <div className="lg:col-span-1 bg-slate-900/60 rounded-xl border border-slate-700/50 p-4 space-y-3">
          <h3 className="text-sm font-semibold text-slate-300">⚙️ 參數設定</h3>

          <div>
            <label className="text-xs text-slate-500">策略名稱</label>
            <input
              type="text" value={name} onChange={e => setName(e.target.value)}
              className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200"
            />
          </div>

          {/* Presets */}
          <div className="flex gap-2">
            {presets.map((p) => (
              <button key={p.label}
                onClick={() => applyPreset(p)}
                className="flex-1 px-2 py-1 text-xs bg-slate-800 text-slate-300 rounded border border-slate-600 hover:bg-slate-700"
              >{p.label}</button>
            ))}
          </div>

          {/* Entry */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-blue-400">進場條件</h4>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-slate-500">Bias50 上限 (%)</label>
                <input type="number" step="0.5" value={bias50Max} onChange={e => setBias50Max(parseFloat(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                <input type="range" min={-8} max={4} step={0.5} value={bias50Max} onChange={e => setBias50Max(parseFloat(e.target.value))}
                  className="w-full mt-2 accent-blue-500" />
              </div>
              <div>
                <label className="text-xs text-slate-500">Nose (RSI) 上限</label>
                <input type="number" step="0.05" value={noseMax} onChange={e => setNoseMax(parseFloat(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                <input type="range" min={0.1} max={0.9} step={0.05} value={noseMax} onChange={e => setNoseMax(parseFloat(e.target.value))}
                  className="w-full mt-2 accent-blue-500" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-slate-500">Layer 2 Bias (%)</label>
                <input type="number" step="0.5" value={layer2Bias} onChange={e => setLayer2Bias(parseFloat(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                <input type="range" min={-10} max={0} step={0.5} value={layer2Bias} onChange={e => setLayer2Bias(parseFloat(e.target.value))}
                  className="w-full mt-2 accent-blue-500" />
              </div>
              <div>
                <label className="text-xs text-slate-500">Layer 3 Bias (%)</label>
                <input type="number" step="0.5" value={layer3Bias} onChange={e => setLayer3Bias(parseFloat(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                <input type="range" min={-14} max={-1} step={0.5} value={layer3Bias} onChange={e => setLayer3Bias(parseFloat(e.target.value))}
                  className="w-full mt-2 accent-blue-500" />
              </div>
            </div>
          </div>

          {/* Layers */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-yellow-400">金字塔比例 (%)</h4>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-xs text-slate-500">L1</label>
                <input type="number" value={layer1} onChange={e => setLayer1(parseInt(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                <input type="range" min={0} max={100} step={1} value={layer1} onChange={e => setLayer1(parseInt(e.target.value))}
                  className="w-full mt-2 accent-yellow-500" />
              </div>
              <div>
                <label className="text-xs text-slate-500">L2</label>
                <input type="number" value={layer2} onChange={e => setLayer2(parseInt(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                <input type="range" min={0} max={100} step={1} value={layer2} onChange={e => setLayer2(parseInt(e.target.value))}
                  className="w-full mt-2 accent-yellow-500" />
              </div>
              <div>
                <label className="text-xs text-slate-500">L3</label>
                <input type="number" value={layer3} onChange={e => setLayer3(parseInt(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                <input type="range" min={0} max={100} step={1} value={layer3} onChange={e => setLayer3(parseInt(e.target.value))}
                  className="w-full mt-2 accent-yellow-500" />
              </div>
            </div>
          </div>

          {/* Exit */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-red-400">出場條件</h4>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-xs text-slate-500">止損 (%)</label>
                <input type="number" step="1" value={stopLoss} onChange={e => setStopLoss(parseInt(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                <input type="range" min={-15} max={-1} step={1} value={stopLoss} onChange={e => setStopLoss(parseInt(e.target.value))}
                  className="w-full mt-2 accent-red-500" />
              </div>
              <div>
                <label className="text-xs text-slate-500">TP Bias (%)</label>
                <input type="number" step="0.5" value={tpBias} onChange={e => setTpBias(parseFloat(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                <input type="range" min={1} max={10} step={0.5} value={tpBias} onChange={e => setTpBias(parseFloat(e.target.value))}
                  className="w-full mt-2 accent-red-500" />
              </div>
              <div>
                <label className="text-xs text-slate-500">TP ROI (%)</label>
                <input type="number" step="1" value={tpRoi} onChange={e => setTpRoi(parseInt(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
                <input type="range" min={1} max={20} step={1} value={tpRoi} onChange={e => setTpRoi(parseInt(e.target.value))}
                  className="w-full mt-2 accent-red-500" />
              </div>
            </div>
          </div>

          <button
            onClick={handleRun} disabled={running}
            className={`w-full py-2 rounded-lg font-semibold text-sm transition ${
              running
                ? "bg-slate-700 text-slate-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-500"
            }`}
          >
            {running ? "⏳ 回測中..." : "▶ 執行回測"}
          </button>
        </div>

        {/* ─── RIGHT: Results + Leaderboard ─── */}
        <div className="lg:col-span-2 space-y-4">
          {error && (
            <div className="bg-red-900/20 border border-red-700/50 rounded-xl p-4 text-red-400 text-sm">{error}</div>
          )}

          {/* Run Result */}
          {runResult && (
            <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4">
              <h3 className="text-sm font-semibold text-slate-300 mb-3">📊 回測結果</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: "ROI", value: formatPct(runResult.roi, 1, true), color: runResult.roi > 0 ? 'text-green-400' : 'text-red-400' },
                  { label: "勝率", value: formatPct(runResult.win_rate), color: runResult.win_rate > 0.5 ? 'text-green-400' : 'text-yellow-400' },
                  { label: "交易次數", value: `${runResult.total_trades}`, color: 'text-slate-200' },
                  { label: "Profit Factor", value: formatDecimal(runResult.profit_factor), color: runResult.profit_factor > 1 ? 'text-green-400' : 'text-red-400' },
                  { label: "最大回撤", value: formatPct(runResult.max_drawdown), color: 'text-red-400' },
                  { label: "總損益", value: formatMoney(runResult.total_pnl), color: runResult.total_pnl > 0 ? 'text-green-400' : 'text-red-400' },
                ].map((m) => (
                  <div key={m.label} className="bg-slate-800/50 rounded-lg p-3">
                    <div className="text-xs text-slate-500">{m.label}</div>
                    <div className={`text-lg font-bold ${m.color}`}>{m.value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
              <div className="text-xs text-slate-500">目前最高策略勝率</div>
              <div className="mt-2 text-2xl font-bold text-emerald-300">
                {bestStrategyWinRate ? formatPct(bestStrategyWinRate.last_results?.win_rate, 1) : '—'}
              </div>
              <div className="mt-1 text-xs text-slate-400">
                {bestStrategyWinRate ? `${bestStrategyWinRate.name} · ${formatPct(bestStrategyWinRate.last_results?.roi, 1, true)} ROI` : '先執行並儲存至少一個策略'}
              </div>
            </div>
            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
              <div className="text-xs text-slate-500">目前最佳策略 ROI</div>
              <div className="mt-2 text-2xl font-bold text-blue-300">
                {bestStrategyRoi ? formatPct(bestStrategyRoi.last_results?.roi, 1, true) : '—'}
              </div>
              <div className="mt-1 text-xs text-slate-400">
                {bestStrategyRoi ? `${bestStrategyRoi.name} · ${formatPct(bestStrategyRoi.last_results?.win_rate, 1)} 勝率` : '尚無策略排行資料'}
              </div>
            </div>
            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
              <div className="text-xs text-slate-500">保留模型最高勝率</div>
              <div className="mt-2 text-2xl font-bold text-violet-300">
                {bestModelWinRate ? formatPct(bestModelWinRate.avg_win_rate, 1) : '—'}
              </div>
              <div className="mt-1 text-xs text-slate-400">
                {bestModelWinRate ? `${bestModelWinRate.model_name} · Gap ${formatDecimal(bestModelWinRate.train_test_gap * 100, 1)}pp` : '避免展示已淘汰過擬合模型'}
              </div>
            </div>
          </div>

          {/* Benchmark comparison */}
          <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-slate-300">📈 基準對比</h3>
              <span className="text-xs text-slate-500">改為和當前回測同一批資料動態計算，不再顯示過時固定數值</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              {benchmarkCards.map((card) => {
                const roi = card.roi;
                return (
                  <div key={card.label} className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/40">
                    <div className="text-slate-400">{card.label}</div>
                    <div className={`mt-2 text-2xl font-bold ${isFiniteNumber(roi) ? (roi >= 0 ? 'text-green-400' : 'text-red-400') : 'text-slate-500'}`}>
                      {formatPct(roi, 1, true)}
                    </div>
                    <div className="mt-2 space-y-1 text-[11px] text-slate-500">
                      <div>勝率：{formatPct(card.win_rate, 1)}</div>
                      <div>交易：{isFiniteNumber(card.total_trades) ? card.total_trades : '—'}</div>
                      <div>PF：{formatDecimal(card.profit_factor)}</div>
                    </div>
                  </div>
                );
              })}
              {!runResult && (
                <div className="md:col-span-3 rounded-lg border border-dashed border-slate-700/60 p-4 text-center text-slate-500">
                  執行一次回測後，這裡會顯示與同批資料同步計算的買入持有 / 盲金字塔 / 你的策略對比。
                </div>
              )}
            </div>
          </div>

          {runResult?.regime_breakdown && runResult.regime_breakdown.length > 0 && (
            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-300">🧭 市場分類回測</h3>
                <span className="text-xs text-slate-500">依進場時 regime 切分 Bull / Bear / Chop</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-700/50">
                      <th className="text-left py-2 px-2">Regime</th>
                      <th className="text-right py-2 px-2">交易</th>
                      <th className="text-right py-2 px-2">勝率</th>
                      <th className="text-right py-2 px-2">ROI</th>
                      <th className="text-right py-2 px-2">PF</th>
                      <th className="text-right py-2 px-2">損益</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runResult.regime_breakdown.map((row) => (
                      <tr key={row.regime} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                        <td className="py-2 px-2 text-slate-200 font-medium">{regimeLabelMap[row.regime] ?? row.regime}</td>
                        <td className="py-2 px-2 text-right text-slate-400">{row.trades}</td>
                        <td className="py-2 px-2 text-right text-slate-300">{formatPct(row.win_rate)}</td>
                        <td className={`py-2 px-2 text-right font-bold ${isFiniteNumber(row.roi) && row.roi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatPct(row.roi, 1, true)}
                        </td>
                        <td className={`py-2 px-2 text-right ${isFiniteNumber(row.profit_factor) && row.profit_factor >= 1 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatDecimal(row.profit_factor)}
                        </td>
                        <td className={`py-2 px-2 text-right ${isFiniteNumber(row.total_pnl) && row.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatMoney(row.total_pnl)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Leaderboard */}
          <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-slate-300">🏆 策略排行榜</h3>
              <button onClick={loadLeaderboard} className="text-xs text-blue-400 hover:text-blue-300">🔄 刷新</button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-slate-700/50">
                    <th className="text-left py-2 px-2">#</th>
                    <th className="text-left py-2 px-2">策略</th>
                    <th className="text-right py-2 px-2">ROI</th>
                    <th className="text-right py-2 px-2">勝率</th>
                    <th className="text-right py-2 px-2">交易</th>
                    <th className="text-right py-2 px-2">PF</th>
                    <th className="text-right py-2 px-2">最大回撤</th>
                    <th className="text-right py-2 px-2">連敗</th>
                    <th className="text-right py-2 px-2">穩定度</th>
                    <th className="text-right py-2 px-2">過擬合風險</th>
                    <th className="text-right py-2 px-2">樣本充足性</th>
                  </tr>
                </thead>
                <tbody>
                  {strategies.map((s, i) => {
                    const r = s.last_results;
                    return (
                      <tr key={s.name} className="border-b border-slate-800/50 hover:bg-slate-800/30 align-top">
                        <td className="py-2 px-2 text-slate-500">{i + 1}</td>
                        <td className="py-2 px-2 text-slate-200 font-medium">
                          {s.name}
                          <span className="ml-1 text-xs text-slate-500">(x{s.run_count})</span>
                          {s.risk_reasons && s.risk_reasons.length > 0 && (
                            <div className="mt-1 text-[10px] leading-4 text-slate-500">{s.risk_reasons.join(' · ')}</div>
                          )}
                        </td>
                        <td className={`py-2 px-2 text-right font-bold ${r && isFiniteNumber(r.roi) && r.roi > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {r ? formatPct(r.roi, 1, true) : '—'}
                        </td>
                        <td className="py-2 px-2 text-right text-slate-300">
                          {r ? formatPct(r.win_rate, 0) : '—'}
                        </td>
                        <td className="py-2 px-2 text-right text-slate-400">{r?.total_trades ?? '—'}</td>
                        <td className={`py-2 px-2 text-right ${r && isFiniteNumber(r.profit_factor) && r.profit_factor > 1 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatDecimal(r?.profit_factor)}
                        </td>
                        <td className="py-2 px-2 text-right text-red-400">
                          {r ? formatPct(r.max_drawdown) : '—'}
                        </td>
                        <td className="py-2 px-2 text-right text-slate-300">{r?.max_consecutive_losses ?? '—'}</td>
                        <td className="py-2 px-2 text-right">
                          <div className="text-slate-200">{isFiniteNumber(s.stability_score) ? `${s.stability_score}` : '—'}</div>
                          <div className="text-[10px] text-slate-500">{s.stability_label ?? '—'}</div>
                        </td>
                        <td className="py-2 px-2 text-right">
                          <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] ${strategyRiskTone[s.overfit_risk ?? 'unknown']}`}>
                            {strategyRiskLabel[s.overfit_risk ?? 'unknown']}
                          </span>
                        </td>
                        <td className="py-2 px-2 text-right text-slate-300">{sufficiencyLabel[s.trade_sufficiency ?? 'unknown']}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {strategies.length === 0 && (
                <div className="text-center text-slate-500 py-8 text-sm">
                  尚無已儲存的策略。設定參數後點擊「執行回測」來開始。
                </div>
              )}
            </div>
            <p className="text-xs text-slate-600 mt-2">
              ⚠️ 歷史回測 ≠ 未來表現。所有結果均基於 2025-04 到 2026-04 的 1m 資料。
            </p>
          </div>

          <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-300">🤖 模型排行榜</h3>
                <div className="mt-1 text-[11px] text-slate-500">
                  {modelMeta.refreshing ? '背景重算中，先顯示快取結果…' : modelMeta.updated_at ? `上次更新 ${new Date(modelMeta.updated_at).toLocaleString('zh-TW')}` : '尚未建立快取，首次載入會先背景計算'}
                </div>
                {modelMeta.target_label && (
                  <div className="mt-1 text-[11px] text-emerald-300">主評估 target：{modelMeta.target_label}</div>
                )}
              </div>
              <button onClick={() => loadModelLeaderboard(true)} className="text-xs text-blue-400 hover:text-blue-300">{modelMeta.refreshing ? '⏳ 背景更新中' : '🔄 刷新'}</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
              <div className="rounded-lg border border-emerald-700/30 bg-emerald-900/10 p-3 text-xs text-slate-300">
                <div className="font-semibold text-emerald-300 mb-1">實務優先 Hybrid #1</div>
                <div>XGBoost / CatBoost → 規則式金字塔執行</div>
                <div className="text-slate-500 mt-1">先用樹模型做訊號排序，再由支撐 / 分批 / SLTP 規則執行，最常見也最容易落地。</div>
              </div>
              <div className="rounded-lg border border-violet-700/30 bg-violet-900/10 p-3 text-xs text-slate-300">
                <div className="font-semibold text-violet-300 mb-1">研究路線 Hybrid #2</div>
                <div>XGBoost / CatBoost → PPO</div>
                <div className="text-slate-500 mt-1">先保留為下一階段：用樹模型當 state / reward 輔助，再讓 PPO 學會加減碼節奏。</div>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 mb-3 text-xs">
              <span className="px-2 py-1 rounded bg-emerald-900/20 text-emerald-300 border border-emerald-700/30">保留模型 {recommendedModels.length}</span>
              <span className="px-2 py-1 rounded bg-red-900/20 text-red-300 border border-red-700/30">淘汰過擬合 {eliminatedModels.length}</span>
              <span className="text-slate-500">Gap &gt; {(OVERFIT_GAP_THRESHOLD * 100).toFixed(0)}pp 或 Train &gt; 90% 直接淘汰</span>
              {modelMeta.cached && <span className="px-2 py-1 rounded bg-slate-800/60 text-slate-300 border border-slate-700/40">快取回應</span>}
              {modelMeta.stale && <span className="px-2 py-1 rounded bg-yellow-900/20 text-yellow-300 border border-yellow-700/30">舊資料，背景更新中</span>}
            </div>
            {targetComparison.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4 text-xs">
                {targetComparison.map((entry) => (
                  <div key={entry.target_col} className="rounded-lg border border-slate-700/50 bg-slate-950/40 p-3 text-slate-300">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2 font-semibold text-slate-200">
                          <span>{entry.label}</span>
                          <span className={`rounded-full border px-2 py-0.5 text-[10px] ${entry.is_canonical ? 'border-emerald-600/40 bg-emerald-900/20 text-emerald-300' : 'border-amber-600/40 bg-amber-900/20 text-amber-300'}`}>
                            {entry.is_canonical ? 'canonical' : 'legacy compare'}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-500">樣本 {entry.samples} · 正例 {formatPct(entry.positive_ratio, 1)}</div>
                        {entry.usage_note && (
                          <div className={`mt-1 text-[11px] ${entry.is_canonical ? 'text-emerald-300/90' : 'text-amber-300/90'}`}>{entry.usage_note}</div>
                        )}
                      </div>
                      <span className="rounded-full border border-slate-700/50 px-2 py-0.5 text-[10px] text-slate-400">{entry.models_evaluated} models</span>
                    </div>
                    <div className="mt-2 text-[11px] text-slate-400">
                      {entry.best_model ? (
                        <>
                          最佳非過擬合：<span className="text-emerald-300">{entry.best_model.model_name}</span>
                          <span className="ml-1">ROI {formatPct(entry.best_model.avg_roi, 1, true)} · 勝率 {formatPct(entry.best_model.avg_win_rate, 1)} · Gap {formatDecimal(entry.best_model.train_test_gap * 100, 1)}pp</span>
                        </>
                      ) : (
                        '尚無可用比較結果'
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-slate-700/50">
                    <th className="text-left py-2 px-2">#</th>
                    <th className="text-left py-2 px-2">模型</th>
                    <th className="text-right py-2 px-2">ROI</th>
                    <th className="text-right py-2 px-2">勝率</th>
                    <th className="text-right py-2 px-2">PF</th>
                    <th className="text-right py-2 px-2">Train</th>
                    <th className="text-right py-2 px-2">Test</th>
                    <th className="text-right py-2 px-2">Gap</th>
                    <th className="text-right py-2 px-2">Fold</th>
                  </tr>
                </thead>
                <tbody>
                  {recommendedModels.map((m, i) => (
                    <tr key={m.model_name} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                      <td className="py-2 px-2 text-slate-500">{i + 1}</td>
                      <td className="py-2 px-2 text-slate-200 font-medium">{m.model_name}</td>
                      <td className={`py-2 px-2 text-right font-bold ${m.avg_roi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {m.avg_roi >= 0 ? '+' : ''}{(m.avg_roi * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 px-2 text-right text-slate-300">{(m.avg_win_rate * 100).toFixed(1)}%</td>
                      <td className={`py-2 px-2 text-right ${m.profit_factor >= 1 ? 'text-green-400' : 'text-red-400'}`}>{m.profit_factor.toFixed(2)}</td>
                      <td className="py-2 px-2 text-right text-slate-400">{(m.train_acc * 100).toFixed(1)}%</td>
                      <td className="py-2 px-2 text-right text-slate-300">{(m.test_acc * 100).toFixed(1)}%</td>
                      <td className={`py-2 px-2 text-right ${m.train_test_gap <= 0.1 ? 'text-green-400' : 'text-yellow-400'}`}>{(m.train_test_gap * 100).toFixed(1)}pp</td>
                      <td className="py-2 px-2 text-right text-slate-500">{m.folds?.length ?? 0}</td>
                    </tr>
                  ))}
                  {eliminatedModels.length > 0 && (
                    <tr>
                      <td colSpan={9} className="py-3 text-[11px] uppercase tracking-wide text-red-300">淘汰過擬合模型</td>
                    </tr>
                  )}
                  {eliminatedModels.map((m, i) => (
                    <tr key={`elim-${m.model_name}`} className="border-b border-slate-800/50 opacity-60 hover:bg-slate-800/20">
                      <td className="py-2 px-2 text-slate-500">{recommendedModels.length + i + 1}</td>
                      <td className="py-2 px-2 text-slate-300 font-medium">{m.model_name} <span className="text-red-400">(淘汰)</span><div className="text-[10px] text-slate-500">{m.overfit_reason === 'train_accuracy_cap' ? 'Train 準確率過高' : 'Train/Test gap 過大'}</div></td>
                      <td className={`py-2 px-2 text-right font-bold ${m.avg_roi >= 0 ? 'text-green-400' : 'text-red-400'}`}>{m.avg_roi >= 0 ? '+' : ''}{(m.avg_roi * 100).toFixed(1)}%</td>
                      <td className="py-2 px-2 text-right text-slate-300">{(m.avg_win_rate * 100).toFixed(1)}%</td>
                      <td className={`py-2 px-2 text-right ${m.profit_factor >= 1 ? 'text-green-400' : 'text-red-400'}`}>{m.profit_factor.toFixed(2)}</td>
                      <td className="py-2 px-2 text-right text-slate-400">{(m.train_acc * 100).toFixed(1)}%</td>
                      <td className="py-2 px-2 text-right text-slate-300">{(m.test_acc * 100).toFixed(1)}%</td>
                      <td className="py-2 px-2 text-right text-red-400">{(m.train_test_gap * 100).toFixed(1)}pp</td>
                      <td className="py-2 px-2 text-right text-slate-500">{m.folds?.length ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {modelLeaderboard.length === 0 && (
                <div className="text-center text-slate-500 py-8 text-sm">
                  {modelMeta.refreshing
                    ? '模型排行榜正在背景計算，頁面會自動重整。'
                    : '尚無可用模型排行榜資料。請先確認 `/api/models/leaderboard` 可正常產生資料。'}
                </div>
              )}
            </div>
            <p className="text-xs text-slate-600 mt-2">
              使用 Walk-Forward 驗證，比較 ROI、勝率與過擬合差距（Train-Test gap）。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
