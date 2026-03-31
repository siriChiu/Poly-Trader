/**
 * AdviceCard v2.0 — 完整建議展示
 */
import { useState, useEffect } from "react";

interface Props {
  score: number;
  summary: string;
  descriptions: string[];
  action: string;
  timestamp?: string;
  onTrade?: (side: string) => void;
}

const ACTION_CONFIG: Record<string, { text: string; color: string; bg: string; icon: string }> = {
  strong_buy: { text: "🟢 強烈建議買入", color: "text-green-400", bg: "from-green-900/40 to-slate-900", icon: "🔥" },
  buy: { text: "🟢 建議買入", color: "text-green-400", bg: "from-green-900/30 to-slate-900", icon: "🟢" },
  hold: { text: "⚪ 建議觀望", color: "text-slate-300", bg: "from-slate-800/50 to-slate-900", icon: "⚪" },
  reduce: { text: "🟠 建議減倉", color: "text-orange-400", bg: "from-orange-900/30 to-slate-900", icon: "🔻" },
  sell: { text: "🔴 建議觀望/做空", color: "text-red-400", bg: "from-red-900/30 to-slate-900", icon: "🔴" },
};

function getScoreLevel(score: number): string {
  if (score >= 80) return "text-green-400";
  if (score >= 60) return "text-yellow-400";
  if (score >= 40) return "text-slate-300";
  if (score >= 20) return "text-orange-400";
  return "text-red-400";
}

export default function AdviceCard({ score, summary, descriptions, action, timestamp, onTrade }: Props) {
  const [confirmTrade, setConfirmTrade] = useState<string | null>(null);
  const [tradeStatus, setTradeStatus] = useState<string | null>(null);
  const [prevScore, setPrevScore] = useState(score);
  const [scoreDelta, setScoreDelta] = useState(0);

  // 追蹤分數變化
  useEffect(() => {
    setScoreDelta(score - prevScore);
    setPrevScore(score);
  }, [score]);

  const handleTrade = (side: string) => {
    if (confirmTrade === side) {
      setTradeStatus(side === "buy" ? "✅ 買入訂單已提交（Dry Run）" : "✅ 賣出訂單已提交（Dry Run）");
      onTrade?.(side);
      setConfirmTrade(null);
      setTimeout(() => setTradeStatus(null), 5000);
    } else {
      setConfirmTrade(side);
      setTimeout(() => setConfirmTrade(null), 5000);
    }
  };

  const config = ACTION_CONFIG[action] || ACTION_CONFIG.hold;

  // 拆分 summary（取前 80 字為短摘要）
  const shortSummary = summary.length > 120 ? summary.slice(0, 120) + "..." : summary;

  return (
    <div className={`bg-gradient-to-br ${config.bg} rounded-xl border border-slate-700/50 p-4 space-y-3`}>
      {/* Header: Score + Action */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Big Score */}
          <div className={`text-5xl font-mono font-bold transition-all duration-500 ${getScoreLevel(score)}`}>
            {score}
          </div>
          {/* Score delta indicator */}
          {scoreDelta !== 0 && (
            <div className={`text-sm font-bold ${scoreDelta > 0 ? "text-green-400" : "text-red-400"}`}>
              {scoreDelta > 0 ? "↑" : "↓"} {Math.abs(scoreDelta)}
            </div>
          )}
        </div>

        <div className="text-right">
          <div className={`text-base font-bold ${config.color}`}>
            {config.icon} {config.text}
          </div>
          {timestamp && (
            <div className="text-xs text-slate-500 mt-0.5">{timestamp}</div>
          )}
        </div>
      </div>

      {/* Summary (full text) */}
      <div className="text-sm text-slate-200 leading-relaxed">
        {shortSummary}
      </div>

      {/* Sense Descriptions (compact grid) */}
      {descriptions && descriptions.length > 0 && (
        <div className="bg-slate-800/30 rounded-lg p-2.5 space-y-0.5">
          {descriptions.map((desc, i) => (
            <div key={i} className="text-xs text-slate-400">{desc}</div>
          ))}
        </div>
      )}

      {/* Trade Status */}
      {tradeStatus && (
        <div className="bg-green-900/30 border border-green-700/30 rounded-lg px-3 py-2 text-green-400 text-xs text-center">
          {tradeStatus}
        </div>
      )}

      {/* Buy / Hold / Sell Buttons */}
      <div className="flex gap-2">
        {/* Buy */}
        <button
          onClick={() => handleTrade("buy")}
          className={`flex-1 py-2.5 rounded-lg font-bold text-sm transition-all ${
            confirmTrade === "buy"
              ? "bg-green-500 text-white animate-pulse"
              : "bg-green-600/40 text-green-400 hover:bg-green-600/60 border border-green-600/30"
          }`}
        >
          {confirmTrade === "buy" ? "✓ 確認買入" : "🟢 買入"}
        </button>

        {/* Hold */}
        <button
          onClick={() => setConfirmTrade(null)}
          className="flex-1 py-2.5 rounded-lg font-bold text-sm bg-slate-700/60 text-slate-400 hover:bg-slate-700 border border-slate-600/30 transition-all"
        >
          ⚪ 觀望
        </button>

        {/* Sell */}
        <button
          onClick={() => handleTrade("sell")}
          className={`flex-1 py-2.5 rounded-lg font-bold text-sm transition-all ${
            confirmTrade === "sell"
              ? "bg-red-500 text-white animate-pulse"
              : "bg-red-600/40 text-red-400 hover:bg-red-600/60 border border-red-600/30"
          }`}
        >
          {confirmTrade === "sell" ? "✓ 確認賣出" : "🔴 賣出"}
        </button>
      </div>
    </div>
  );
}
