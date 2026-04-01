/**
 * Dashboard v2.0 — 使用者體驗增強版
 */
import { useState, useEffect, useCallback } from "react";
import RadarChart from "../components/RadarChart";
import AdviceCard from "../components/AdviceCard";
import SenseChart from "../components/SenseChart";
import CandlestickChart from "../components/CandlestickChart";
import BacktestSummary from "../components/BacktestSummary";
import { useApi, fetchApi } from "../hooks/useApi";

interface SensesResponse {
  senses: Record<string, any>;
  scores: Record<string, number>;
  recommendation: {
    score: number;
    summary: string;
    descriptions: string[];
    action: string;
    timestamp?: string;
  };
}

interface BacktestData {
  final_equity: number;
  initial_capital: number;
  total_trades: number;
  win_rate: number;
  profit_loss_ratio: number;
  max_drawdown: number;
  total_return: number;
}

export default function Dashboard() {
  const [interval, setInterval] = useState("1h");
  const [days, setDays] = useState(7);
  const [selectedSense, setSelectedSense] = useState<string | null>(null);
  const [liveScores, setLiveScores] = useState<Record<string, number>>({
    eye: 0.5, ear: 0.5, nose: 0.5, tongue: 0.5, body: 0.5,
  });
  const [liveAdvice, setLiveAdvice] = useState<any>(null);
  const [lastUpdate, setLastUpdate] = useState<string>();
  const [wsConnected, setWsConnected] = useState(false);

  const { data: sensesData, error: apiError, refresh: refreshSenses } = useApi<SensesResponse>("/api/senses", 30000);
  const { data: backtestData } = useApi<BacktestData>("/api/backtest");

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
            <h2 className="text-sm font-semibold text-slate-400">🎯 五感雷達圖</h2>
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

      {/* Row 2: Sense History Chart */}
      <SenseChart selectedSense={selectedSense} days={days} onClear={() => setSelectedSense(null)} />

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
