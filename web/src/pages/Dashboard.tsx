/**
 * Dashboard v2.0 — 使用者體驗增強版
 */
import { useState, useEffect, useCallback } from "react";
import RadarChart from "../components/RadarChart";
import AdviceCard from "../components/AdviceCard";
import FeatureChart from "../components/FeatureChart";
import CandlestickChart from "../components/CandlestickChart";
import BacktestSummary from "../components/BacktestSummary";
import { useApi, fetchApi } from "../hooks/useApi";
import ConfidenceIndicator from "../components/ConfidenceIndicator";
import { ALL_SENSES, getSenseConfig } from "../config/senses";

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

interface ModelStats {
  model_loaded: boolean;
  sample_count: number;
  label_distribution: Record<string, number>;
  cv_accuracy: number | null;
  feature_importance: Record<string, number>;
  ic_values: Record<string, number>;
  model_params: Record<string, any>;
}

interface ConfidenceData {
  error?: string;
  confidence: number;
  signal: string;
  confidence_level: string;
  should_trade: boolean;
  timestamp: string;
}

interface BacktestData {
  final_equity: number;
  initial_capital: number;
  total_trades: number;
  win_rate: number;
  profit_loss_ratio: number;
  max_drawdown: number;
  total_return: number;
  error?: string;
}

export default function Dashboard() {
  const [interval, setInterval] = useState("1h");
  const [days, setDays] = useState(7);
  const [selectedSense, setSelectedSense] = useState<string | null>(null);
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

  const { data: sensesData, error: apiError, refresh: refreshSenses } = useApi<SensesResponse>("/api/senses", 30000);
  const { data: backtestData } = useApi<BacktestData>("/api/backtest");
  const { data: confidenceData } = useApi<ConfidenceData>("/api/predict/confidence", 60000);
  const { data: modelStats } = useApi<ModelStats>("/api/model/stats", 60000);

  // WebSocket
  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/live`;
    let ws: WebSocket | null = null;
    let timer: number;

    const connect = () => {
      try {
        ws = new WebSocket(url);
        ws.onopen = () => setWsConnected(true);
        ws.onmessage = (event) => {
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
        ws.onclose = () => {
          setWsConnected(false);
          timer = window.setTimeout(connect, 5000);
        };
        ws.onerror = () => setWsConnected(false);
      } catch {
        setWsConnected(false);
        timer = window.setTimeout(connect, 5000);
      }
    };
    connect();
    return () => { clearTimeout(timer); ws?.close(); };
  }, []);

  // 更新最後更新時間
  useEffect(() => {
    if (sensesData?.recommendation?.timestamp) {
      setLastUpdate(new Date(sensesData.recommendation.timestamp).toLocaleTimeString("zh-TW"));
    }
  }, [sensesData]);

  // 合併 live data 與 API data
  const scores = liveScores.eye !== 0.5 || liveScores.ear !== 0.5
    ? liveScores
    : sensesData?.scores || liveScores;

  const advice = liveAdvice || sensesData?.recommendation;

  const handleTrade = useCallback(async (side: string) => {
    if (side === "hold") return;
    try {
      const resp = await fetchApi("/api/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ side, symbol: "BTCUSDT", qty: 0.001 }),
      });
      // 顯示成功提示
      const data = resp as any;
      alert(data?.success || data?.order
        ? `${side.toUpperCase()} 訂單已提交（Dry Run）`
        : `${side.toUpperCase()} 已發送`);
    } catch (e: any) {
      alert(`下單失敗: ${e.message}`);
    }
  }, []);

  // 判斷資料新鮮度
  const isDataStale = !lastUpdate && !wsConnected && !sensesData;

  return (
    <div className="space-y-4">
      {/* Top bar */}
      <div className="flex flex-wrap items-center justify-between bg-slate-900/60 rounded-xl border border-slate-700/50 px-4 py-2 text-xs gap-2">
        <div className="flex items-center gap-3">
          <span className="font-bold text-slate-300">🐰 Poly-Trader</span>
          {/* 狀態指示器 */}
          <span className={`flex items-center gap-1 ${wsConnected ? "text-green-400" : "text-orange-400"}`}>
            <span className={`w-2 h-2 rounded-full ${wsConnected ? "bg-green-400" : "bg-orange-400"}`} />
            {wsConnected ? "即時連線" : "離線"}
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

      {/* Row 1: Radar + Advice */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Left: Pentagon Radar */}
        <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-5 flex flex-col items-center">
          <div className="flex items-center justify-between w-full mb-3">
            <h2 className="text-sm font-semibold text-slate-400">🎯 多感官雷達圖</h2>
            <span className="text-xs text-slate-500 cursor-pointer hover:text-slate-300"
              onClick={() => setSelectedSense(null)}>
              點擊感官看走勢
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
            <RadarChart scores={scores} size={280} onSenseClick={setSelectedSense} />
          )}
        </div>

        {/* Right: Advice Card */}
        <div>
          {advice ? (
            <AdviceCard
              score={advice.score}
              summary={advice.summary}
              descriptions={advice.descriptions}
              action={advice.action}
              timestamp={advice.timestamp || lastUpdate}
              onTrade={handleTrade}
            />
          ) : apiError ? (
            <div className="bg-red-900/20 border border-red-700/50 rounded-xl p-8 text-center">
              <div className="text-red-400 text-lg mb-2">⚠️ 無法連線</div>
              <p className="text-slate-400 text-sm">{apiError}</p>
              <button onClick={refreshSenses} className="mt-4 px-4 py-2 text-sm bg-red-600 rounded hover:bg-red-500">
                重試
              </button>
            </div>
          ) : (
            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-8 flex items-center justify-center h-48">
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

        // Pyramiding suggestion
        let action = '';
        if (regime === 'bull' && bias50! <= -3) action = '🔥 接近支撐! 可考慮金字塔加碼 (Layer 3)';
        else if (regime === 'bull' && bias50! <= -1) action = '⚡ 小幅回調，可考慮金字塔進場 (Layer 2)';
        else if (regime === 'bull' && bias50! >= 5) action = '⚠️ 超買! 考慮止盈';
        else if (regime === 'bull') action = '✅ 牛市格局，尋找買入時機';
        else action = '觀望中 — 等待回測 MA50';

        return (
        <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-300">📐 4H 結構線儀表板</h2>
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

          {/* Actionable suggestion */}
          <div className="bg-slate-800/30 rounded-lg px-4 py-2 text-sm text-slate-300 border border-slate-700/30">
            {action}
          </div>
        </div>
        );
      })()}

      {/* Row 2: Sense History Chart */}
      <FeatureChart selectedFeature={selectedSense} days={days} onClear={() => setSelectedSense(null)} />

      {/* Row 3: K 線圖 */}
      <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <span className="text-sm font-semibold text-slate-300">📊 K 線圖 + 技術指標</span>
          <div className="flex items-center gap-1">
            {[
              { label: "1H", iv: "1h", d: 3 },
              { label: "4H", iv: "4h", d: 14 },
              { label: "1D", iv: "1d", d: 90 },
            ].map((opt) => (
              <button
                key={opt.iv}
                onClick={() => { setInterval(opt.iv); setDays(opt.d); }}
                className={`px-3 py-1 text-xs rounded-lg transition ${
                  interval === opt.iv
                    ? "bg-blue-600 text-white"
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <CandlestickChart symbol="BTCUSDT" interval={interval} days={days} />
        {/* 指標圖例 */}
        <div className="flex flex-wrap gap-3 mt-2 text-xs text-slate-500">
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-yellow-500 inline-block"></span> MA20</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-pink-500 inline-block"></span> MA60</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-purple-500 inline-block"></span> RSI</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-blue-500 inline-block"></span> MACD</span>
        </div>
      </div>

      {/* Row 4: Backtest */}
      {backtestData && backtestData.total_trades !== undefined && !backtestData.error && (
        <BacktestSummary
          finalEquity={backtestData.final_equity}
          initialCapital={backtestData.initial_capital}
          totalTrades={backtestData.total_trades}
          winRate={backtestData.win_rate}
          profitLossRatio={backtestData.profit_loss_ratio}
          maxDrawdown={backtestData.max_drawdown}
          totalReturn={backtestData.total_return}
        />
      )}
    </div>
  );
}
