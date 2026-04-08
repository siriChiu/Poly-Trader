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

interface StrategyResult {
  roi: number;
  win_rate: number;
  total_trades: number;
  wins: number;
  losses: number;
  max_drawdown: number;
  profit_factor: number;
  total_pnl: number;
  regime_breakdown?: RegimeBreakdownEntry[];
  run_at?: string;
}

interface StrategyEntry {
  name: string;
  created_at: string;
  definition: { type: string; params: Record<string, any> };
  last_results?: StrategyResult;
  run_count: number;
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
  folds: Array<{
    fold: number;
    roi: number;
    win_rate: number;
    trades: number;
    max_dd: number;
    profit_factor: number;
  }>;
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

const OVERFIT_GAP_THRESHOLD = 0.12;

export default function StrategyLab() {
  const [strategies, setStrategies] = useState<StrategyEntry[]>([]);
  const [modelLeaderboard, setModelLeaderboard] = useState<ModelLeaderboardEntry[]>([]);
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

  const loadModelLeaderboard = async () => {
    try {
      const res = await fetchApi("/api/models/leaderboard");
      const data = res as any;
      const list = data?.leaderboard ?? [];
      setModelLeaderboard(Array.isArray(list) ? list : []);
    } catch (err) {
      console.error("Model leaderboard error:", err);
      setModelLeaderboard([]);
    }
  };

  useEffect(() => {
    loadLeaderboard();
    loadModelLeaderboard();
  }, []);

  const recommendedModels = useMemo(
    () => modelLeaderboard.filter((m) => m.train_test_gap <= OVERFIT_GAP_THRESHOLD),
    [modelLeaderboard]
  );

  const eliminatedModels = useMemo(
    () => modelLeaderboard.filter((m) => m.train_test_gap > OVERFIT_GAP_THRESHOLD),
    [modelLeaderboard]
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

          {/* Benchmark comparison */}
          <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">📈 基準對比</h3>
            <div className="grid grid-cols-3 gap-3 text-center text-xs">
              <div className="bg-slate-800/30 rounded p-2">
                <div className="text-slate-500">買入持有</div>
                <div className="text-lg font-bold text-red-400">-18.9%</div>
              </div>
              <div className="bg-slate-800/30 rounded p-2">
                <div className="text-slate-500">盲金字塔</div>
                <div className="text-lg font-bold text-yellow-400">-29.4%</div>
              </div>
              <div className="bg-slate-800/30 rounded p-2">
                <div className="text-slate-500">你的策略</div>
                <div className={`text-lg font-bold ${runResult ? (runResult.roi > 0 ? 'text-green-400' : 'text-red-400') : 'text-slate-500'}`}>
                  {runResult ? formatPct(runResult.roi, 1, true) : '—'}
                </div>
              </div>
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
                  </tr>
                </thead>
                <tbody>
                  {strategies.map((s, i) => {
                    const r = s.last_results;
                    return (
                      <tr key={s.name} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                        <td className="py-2 px-2 text-slate-500">{i + 1}</td>
                        <td className="py-2 px-2 text-slate-200 font-medium">
                          {s.name}
                          <span className="ml-1 text-xs text-slate-500">(x{s.run_count})</span>
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
              <h3 className="text-sm font-semibold text-slate-300">🤖 模型排行榜</h3>
              <button onClick={loadModelLeaderboard} className="text-xs text-blue-400 hover:text-blue-300">🔄 刷新</button>
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
              <span className="text-slate-500">Gap &gt; {(OVERFIT_GAP_THRESHOLD * 100).toFixed(0)}pp 視為過擬合</span>
            </div>
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
                      <td className="py-2 px-2 text-slate-300 font-medium">{m.model_name} <span className="text-red-400">(淘汰)</span></td>
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
                  尚無可用模型排行榜資料。請先確認 `/api/models/leaderboard` 可正常產生資料。
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
