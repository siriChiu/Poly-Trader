import { useState, useEffect } from "react";
import { fetchApi } from "../hooks/useApi";

interface StrategyResult {
  roi: number;
  win_rate: number;
  total_trades: number;
  wins: number;
  losses: number;
  max_drawdown: number;
  profit_factor: number;
  total_pnl: number;
  run_at?: string;
}

interface StrategyEntry {
  name: string;
  created_at: string;
  definition: { type: string; params: Record<string, any> };
  last_results?: StrategyResult;
  run_count: number;
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

export default function StrategyLab() {
  const [strategies, setStrategies] = useState<StrategyEntry[]>([]);
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
      const data = res as { strategies: StrategyEntry[] };
      setStrategies(data?.strategies || []);
    } catch (err: any) {
      console.error("Leaderboard error:", err);
    }
  };

  useEffect(() => { loadLeaderboard(); }, []);

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
      } else if (data?.results) {
        setRunResult(data.results);
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
              </div>
              <div>
                <label className="text-xs text-slate-500">Nose (RSI) 上限</label>
                <input type="number" step="0.05" value={noseMax} onChange={e => setNoseMax(parseFloat(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-slate-500">Layer 2 Bias (%)</label>
                <input type="number" step="0.5" value={layer2Bias} onChange={e => setLayer2Bias(parseFloat(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
              </div>
              <div>
                <label className="text-xs text-slate-500">Layer 3 Bias (%)</label>
                <input type="number" step="0.5" value={layer3Bias} onChange={e => setLayer3Bias(parseFloat(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
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
              </div>
              <div>
                <label className="text-xs text-slate-500">L2</label>
                <input type="number" value={layer2} onChange={e => setLayer2(parseInt(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
              </div>
              <div>
                <label className="text-xs text-slate-500">L3</label>
                <input type="number" value={layer3} onChange={e => setLayer3(parseInt(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
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
              </div>
              <div>
                <label className="text-xs text-slate-500">TP Bias (%)</label>
                <input type="number" step="0.5" value={tpBias} onChange={e => setTpBias(parseFloat(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
              </div>
              <div>
                <label className="text-xs text-slate-500">TP ROI (%)</label>
                <input type="number" step="1" value={tpRoi} onChange={e => setTpRoi(parseInt(e.target.value))}
                  className="w-full mt-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200" />
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
                  { label: "ROI", value: `${runResult.roi > 0 ? '+' : ''}${(runResult.roi * 100).toFixed(1)}%`, color: runResult.roi > 0 ? 'text-green-400' : 'text-red-400' },
                  { label: "勝率", value: `${(runResult.win_rate * 100).toFixed(1)}%`, color: runResult.win_rate > 0.5 ? 'text-green-400' : 'text-yellow-400' },
                  { label: "交易次數", value: `${runResult.total_trades}`, color: 'text-slate-200' },
                  { label: "Profit Factor", value: runResult.profit_factor.toFixed(2), color: runResult.profit_factor > 1 ? 'text-green-400' : 'text-red-400' },
                  { label: "最大回撤", value: `${(runResult.max_drawdown * 100).toFixed(1)}%`, color: 'text-red-400' },
                  { label: "總損益", value: `USDT ${runResult.total_pnl > 0 ? '+' : ''}${runResult.total_pnl.toFixed(0)}`, color: runResult.total_pnl > 0 ? 'text-green-400' : 'text-red-400' },
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
                  {runResult ? `${runResult.roi > 0 ? '+' : ''}${(runResult.roi * 100).toFixed(1)}%` : '—'}
                </div>
              </div>
            </div>
          </div>

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
                        <td className={`py-2 px-2 text-right font-bold ${r && r.roi > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {r ? `${r.roi > 0 ? '+' : ''}${(r.roi * 100).toFixed(1)}%` : '—'}
                        </td>
                        <td className="py-2 px-2 text-right text-slate-300">
                          {r ? `${(r.win_rate * 100).toFixed(0)}%` : '—'}
                        </td>
                        <td className="py-2 px-2 text-right text-slate-400">{r?.total_trades ?? '—'}</td>
                        <td className={`py-2 px-2 text-right ${r && r.profit_factor > 1 ? 'text-green-400' : 'text-red-400'}`}>
                          {r?.profit_factor?.toFixed(2) ?? '—'}
                        </td>
                        <td className="py-2 px-2 text-right text-red-400">
                          {r ? `${(r.max_drawdown * 100).toFixed(1)}%` : '—'}
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
        </div>
      </div>
    </div>
  );
}
