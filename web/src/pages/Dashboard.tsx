/**
 * Dashboard — 主頁面
 * 左側：五角雷達圖 | 右上：建議卡片 | 五感走勢圖 | 右下：K 線圖（全寬） | 底部：回測摘要
 */
import { useState, useEffect, useCallback } from "react";
import RadarChart from "../components/RadarChart";
import AdviceCard from "../components/AdviceCard";
import CandlestickChart from "../components/CandlestickChart";
import BacktestSummary from "../components/BacktestSummary";
import SenseChart from "../components/SenseChart";
import { useApi, fetchApi } from "../hooks/useApi";

interface SensesResponse {
  senses: Record<string, any>;
  scores: Record<string, number>;
  recommendation: {
    score: number;
    summary: string;
    descriptions: string[];
    action: string;
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

  const { data: sensesData, refresh: refreshSenses } = useApi<SensesResponse>("/api/senses");
  const { data: backtestData } = useApi<BacktestData>("/api/backtest");

  // WebSocket for real-time updates
  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/live`;

    let ws: WebSocket | null = null;
    let timer: number;

    const connect = () => {
      try {
        ws = new WebSocket(url);
        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "senses_update" || msg.type === "connected") {
              const data = msg.data;
              if (data?.scores) setLiveScores(data.scores);
              if (data?.recommendation) setLiveAdvice(data.recommendation);
            }
          } catch {}
        };
        ws.onclose = () => {
          timer = window.setTimeout(connect, 5000);
        };
      } catch {
        timer = window.setTimeout(connect, 5000);
      }
    };

    connect();
    return () => {
      clearTimeout(timer);
      ws?.close();
    };
  }, []);

  // Merge live data with API data
  const scores = liveScores.eye !== 0.5 || liveScores.ear !== 0.5
    ? liveScores
    : sensesData?.scores || liveScores;

  const advice = liveAdvice || sensesData?.recommendation;

  const handleTrade = useCallback(async (side: string) => {
    if (side === "hold") return;
    try {
      await fetchApi("/api/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ side, symbol: "BTCUSDT", qty: 0.001 }),
      });
    } catch (e) {
      console.error("Trade failed:", e);
    }
  }, []);

  return (
    <div className="space-y-6">
      {/* Row 1: Radar + Advice */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Pentagon Radar */}
        <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-6 flex flex-col items-center justify-center">
          <h2 className="text-sm font-semibold text-slate-400 mb-4 self-start">🎯 五感雷達圖</h2>
          <RadarChart scores={scores} size={300} onSenseClick={setSelectedSense} />
        </div>

        {/* Right: Advice Card */}
        <div className="flex flex-col justify-center">
          {advice ? (
            <AdviceCard
              score={advice.score}
              summary={advice.summary}
              descriptions={advice.descriptions}
              action={advice.action}
              onTrade={handleTrade}
            />
          ) : (
            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-6 flex items-center justify-center h-full">
              <div className="text-slate-500 animate-pulse">載入建議...</div>
            </div>
          )}
        </div>
      </div>

      {/* Row 2: Sense History Chart (full width) */}
      <SenseChart selectedSense={selectedSense} days={days} />

      {/* Row 3: K 線圖 (全寬) */}
      <div>
        {/* Timeframe selector */}
        <div className="flex items-center gap-2 mb-3">
          <span className="text-sm text-slate-400">時間週期：</span>
          {[
            { label: "1H", iv: "1h", d: 3 },
            { label: "4H", iv: "4h", d: 14 },
            { label: "1D", iv: "1d", d: 90 },
            { label: "1W", iv: "1w", d: 365 },
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
        <CandlestickChart symbol="BTCUSDT" interval={interval} days={days} />
      </div>

      {/* Row 4: Backtest Summary */}
      {backtestData && (
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
