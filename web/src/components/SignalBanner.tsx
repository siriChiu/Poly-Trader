/**
 * SignalBanner — Trading signal + manual buy/sell + automation toggle
 */
import { useState } from "react";

interface Props {
  confidence: number;
  signal: string;
  timestamp?: string;
}

export default function SignalBanner({ confidence, signal, timestamp }: Props) {
  const [confirmBuy, setConfirmBuy] = useState(false);
  const [confirmSell, setConfirmSell] = useState(false);
  const [automation, setAutomation] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const isBuy = signal === "BUY";
  const confidencePct = Math.round(confidence * 100);

  const handleTrade = async (side: string) => {
    try {
      const resp = await fetch("/api/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ side: side.toLowerCase(), symbol: "BTCUSDT" }),
      });
      const data = await resp.json();
      setStatusMsg(
        data.error
          ? `❌ ${data.error}`
          : `✅ ${side} 訂單已提交: ${data.order_id || "dry_run"}`
      );
    } catch (e: any) {
      setStatusMsg(`❌ ${e.message}`);
    }
    setConfirmBuy(false);
    setConfirmSell(false);
    setTimeout(() => setStatusMsg(null), 5000);
  };

  const toggleAutomation = async () => {
    const newState = !automation;
    setAutomation(newState);
    try {
      await fetch("/api/automation/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: newState }),
      });
      setStatusMsg(newState ? "🤖 自動模式已開啟" : "🖱️ 手動模式已開啟");
    } catch (e: any) {
      setStatusMsg(`❌ ${e.message}`);
    }
    setTimeout(() => setStatusMsg(null), 3000);
  };

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
      {/* Signal display */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-xs text-slate-400 mb-1">交易信號</div>
          <div
            className={`text-2xl font-bold ${
              isBuy ? "text-green-400" : "text-slate-400"
            }`}
          >
            {signal}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-slate-400 mb-1">信心分數</div>
          <div className="text-xl font-mono text-white">{confidencePct}%</div>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="w-full bg-slate-700 rounded-full h-2 mb-4">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${
            isBuy ? "bg-green-500" : "bg-slate-500"
          }`}
          style={{ width: `${confidencePct}%` }}
        />
      </div>

      {/* Trade buttons */}
      <div className="flex gap-2 mb-3">
        {/* Buy button */}
        {!confirmBuy ? (
          <button
            onClick={() => setConfirmBuy(true)}
            disabled={automation}
            className="flex-1 py-2 px-4 bg-green-600 hover:bg-green-500 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg text-white font-medium transition"
          >
            🟢 買進
          </button>
        ) : (
          <div className="flex-1 flex gap-1">
            <button
              onClick={() => handleTrade("BUY")}
              className="flex-1 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-white text-sm font-medium"
            >
              ✓ 確認買進
            </button>
            <button
              onClick={() => setConfirmBuy(false)}
              className="px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-300 text-sm"
            >
              ✕
            </button>
          </div>
        )}

        {/* Sell button */}
        {!confirmSell ? (
          <button
            onClick={() => setConfirmSell(true)}
            disabled={automation}
            className="flex-1 py-2 px-4 bg-red-600 hover:bg-red-500 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg text-white font-medium transition"
          >
            🔴 賣出
          </button>
        ) : (
          <div className="flex-1 flex gap-1">
            <button
              onClick={() => handleTrade("SELL")}
              className="flex-1 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-white text-sm font-medium"
            >
              ✓ 確認賣出
            </button>
            <button
              onClick={() => setConfirmSell(false)}
              className="px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-300 text-sm"
            >
              ✕
            </button>
          </div>
        )}
      </div>

      {/* Automation toggle */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-400">自動交易</span>
        <button
          onClick={toggleAutomation}
          className={`relative w-12 h-6 rounded-full transition-colors ${
            automation ? "bg-green-600" : "bg-slate-600"
          }`}
        >
          <span
            className={`absolute top-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
              automation ? "translate-x-6" : "translate-x-0.5"
            }`}
          />
        </button>
      </div>

      {/* Status message */}
      {statusMsg && (
        <div className="mt-3 text-sm text-center text-slate-300 bg-slate-900/50 rounded-lg py-2">
          {statusMsg}
        </div>
      )}

      {/* Timestamp */}
      {timestamp && (
        <div className="mt-2 text-xs text-slate-500 text-center">
          更新: {new Date(timestamp).toLocaleString("zh-TW")}
        </div>
      )}
    </div>
  );
}
