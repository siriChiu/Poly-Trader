/**
 * Dashboard — TradingView-style layout
 * Top: Candlestick chart (full width)
 * Bottom left: 5 Sense cards
 * Bottom right: Signal banner + manual trade
 */
import { useState } from "react";
import CandlestickChart from "../components/CandlestickChart";
import SenseCard from "../components/SenseCard";
import SignalBanner from "../components/SignalBanner";
import { useApi } from "../hooks/useApi";
import { useWebSocket } from "../hooks/useWebSocket";

interface StatusData {
  mode: string;
  automation: boolean;
  raw_count: number;
  feature_count: number;
  model_loaded: boolean;
}

interface SenseData {
  timestamp: string;
  close_price: number;
  eye_dist: number | null;
  ear_prob: number | null;
  funding_rate: number | null;
  fng_index: number | null;
  body_roc: number | null;
}

interface FeatureData {
  timestamp: string;
  feat_eye_dist: number | null;
  feat_ear_zscore: number | null;
  feat_nose_sigmoid: number | null;
  feat_tongue_pct: number | null;
  feat_body_roc: number | null;
}

interface SignalData {
  confidence: number;
  signal: string;
  timestamp: string;
}

export default function Dashboard() {
  const [interval, setInterval] = useState("1h");
  const [days, setDays] = useState(7);

  const { data: status } = useApi<StatusData>("/api/status");
  const { data: senses } = useApi<SenseData>("/api/senses/latest");
  const { data: features } = useApi<FeatureData[]>("/api/features?days=1");

  // WebSocket for real-time updates
  const wsData = useWebSocket("/ws/live");

  const signal: SignalData | null = wsData?.signal || null;
  const liveSenses: SenseData | null = wsData?.senses || senses || null;

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold text-blue-400">
            🐰 Poly-Trader
          </h1>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-400">BTC/USDT</span>
            {liveSenses?.close_price && (
              <span className="text-white font-mono text-base">
                ${liveSenses.close_price.toLocaleString()}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 text-sm">
          {/* Timeframe selector */}
          <div className="flex gap-1">
            {[
              { label: "1H", iv: "1h", d: 3 },
              { label: "4H", iv: "4h", d: 14 },
              { label: "1D", iv: "1d", d: 90 },
              { label: "1W", iv: "1w", d: 365 },
            ].map((opt) => (
              <button
                key={opt.iv}
                onClick={() => {
                  setInterval(opt.iv);
                  setDays(opt.d);
                }}
                className={`px-2 py-1 text-xs rounded transition ${
                  interval === opt.iv
                    ? "bg-blue-600 text-white"
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {/* Status indicators */}
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                status?.model_loaded ? "bg-green-400" : "bg-red-400"
              }`}
            />
            <span className="text-slate-400">
              {status?.raw_count || 0} 數據
            </span>
            <span
              className={`px-2 py-0.5 rounded text-xs ${
                status?.automation
                  ? "bg-green-900 text-green-300"
                  : "bg-yellow-900 text-yellow-300"
              }`}
            >
              {status?.automation ? "🤖 自動" : "🖱️ 手動"}
            </span>
          </div>
        </div>
      </div>

      {/* Main content: chart + panels */}
      <div className="flex flex-col lg:flex-row h-[calc(100vh-44px)]">
        {/* Left: Candlestick chart (70% width) */}
        <div className="lg:w-[70%] w-full border-r border-slate-800">
          <CandlestickChart
            symbol="BTCUSDT"
            interval={interval}
            days={days}
            height={undefined}
          />
        </div>

        {/* Right: Sense cards + Signal (30% width) */}
        <div className="lg:w-[30%] w-full flex flex-col overflow-y-auto">
          {/* 5 Sense Cards */}
          <div className="p-3 border-b border-slate-800">
            <h2 className="text-sm font-semibold text-slate-400 mb-2">
              五感即時狀態
            </h2>
            <div className="grid grid-cols-1 gap-2">
              <SenseCard
                name="👁️ Eye"
                label="技術面"
                value={liveSenses?.eye_dist}
                format="pct"
                description="價格與阻力/支撐距離"
              />
              <SenseCard
                name="👂 Ear"
                label="市場共識"
                value={liveSenses?.ear_prob}
                format="pct"
                description="預測市場概率"
              />
              <SenseCard
                name="👃 Nose"
                label="衍生品"
                value={
                  liveSenses?.funding_rate
                    ? liveSenses.funding_rate * 10000
                    : null
                }
                format="fixed4"
                description="資金費率 (×10⁴)"
              />
              <SenseCard
                name="👅 Tongue"
                label="情緒"
                value={liveSenses?.fng_index}
                format="int"
                description="恐懼貪婪指數 (0~100)"
              />
              <SenseCard
                name="💪 Body"
                label="鏈上資金"
                value={liveSenses?.body_roc}
                format="pct"
                description="穩定幣市值 ROC"
              />
            </div>
          </div>

          {/* Signal Banner */}
          <div className="p-3 flex-1">
            <SignalBanner
              confidence={signal?.confidence || 0}
              signal={signal?.signal || "HOLD"}
              timestamp={signal?.timestamp}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
