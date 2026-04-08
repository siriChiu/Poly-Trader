/**
 * AdviceCard v3 — 安全防禦版
 */
import { useState, useEffect } from "react";

interface Props {
  score?: number;
  summary?: string;
  descriptions?: string[];
  action?: string;
  timestamp?: string;
  onTrade?: (side: string) => void;
}

// Core strategy: SPOT LONG + pyramid entries.
// High score = stronger long-entry quality.
const ACTION_CONFIG: Record<string, { text: string; color: string; bg: string; icon: string }> = {
  strong_buy: { text: "🟢 強烈建議買入 — 可考慮金字塔進場", color: "text-green-400", bg: "from-green-900/40 to-slate-900", icon: "🟢" },
  buy: { text: "🟡 偏多格局 — 等待確認後買入", color: "text-yellow-400", bg: "from-yellow-900/30 to-slate-900", icon: "🟡" },
  hold: { text: "⚪ 建議觀望 — 方向不明", color: "text-slate-300", bg: "from-slate-800/50 to-slate-900", icon: "⚪" },
  hold_long: { text: "🔴 弱勢格局 — 暫停新增部位", color: "text-red-400", bg: "from-red-900/30 to-slate-900", icon: "🔴" },
  reduce: { text: "🟠 偏弱格局 — 保守減碼", color: "text-orange-400", bg: "from-orange-900/30 to-slate-900", icon: "🔻" },
};

function getScoreLevel(score: number): string {
  if (score >= 80) return "text-green-400";
  if (score >= 60) return "text-yellow-400";
  if (score >= 40) return "text-slate-300";
  if (score >= 20) return "text-orange-400";
  return "text-red-400";
}

export default function AdviceCard({ score = 50, summary = "分析中...", descriptions = [], action = "hold", timestamp, onTrade }: Props) {
  const [confirmTrade, setConfirmTrade] = useState<string | null>(null);
  const [tradeStatus, setTradeStatus] = useState<string | null>(null);
  const [prevScore, setPrevScore] = useState(score);
  const [delta, setDelta] = useState(0);

  useEffect(() => { setDelta(score - prevScore); setPrevScore(score); }, [score]);

  const handleTrade = (side: string) => {
    if (confirmTrade === side) {
      const label = side === "buy" ? "買入" : side === "reduce" ? "減碼" : "觀望";
      setTradeStatus(`✅ ${label}指令已提交 (Dry Run)`);
      onTrade?.(side);
      setConfirmTrade(null);
      setTimeout(() => setTradeStatus(null), 5000);
    } else {
      setConfirmTrade(side);
      setTimeout(() => setConfirmTrade(null), 5000);
    }
  };

  const config = ACTION_CONFIG[action] || ACTION_CONFIG.hold;

  return (
    <div className={`bg-gradient-to-br ${config.bg} rounded-xl border border-slate-700/50 p-4 space-y-3`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`text-5xl font-mono font-bold transition-all duration-500 ${getScoreLevel(score)}`}>{score}</div>
          {delta !== 0 && <div className={`text-sm font-bold ${delta > 0 ? "text-green-400" : "text-red-400"}`}>{delta > 0 ? "↑" : "↓"} {Math.abs(delta)}</div>}
        </div>
        <div className="text-right">
          <div className={`text-base font-bold ${config.color}`}>{config.icon} {config.text}</div>
          {timestamp && <div className="text-xs text-slate-500 mt-0.5">{timestamp}</div>}
        </div>
      </div>

      <div className="text-sm text-slate-200 leading-relaxed">{summary}</div>

      {descriptions && descriptions.length > 0 && (
        <div className="bg-slate-800/30 rounded-lg p-2.5 space-y-0.5">
          {descriptions.map((d, i) => <div key={i} className="text-xs text-slate-400">{d}</div>)}
        </div>
      )}

      {tradeStatus && <div className="bg-green-900/30 border border-green-700/30 rounded-lg px-3 py-2 text-green-400 text-xs text-center">{tradeStatus}</div>}

      <div className="flex gap-2">
        <button onClick={() => handleTrade("buy")} className={`flex-1 py-2.5 rounded-lg font-bold text-sm transition-all ${confirmTrade === "buy" ? "bg-green-500 text-white animate-pulse" : "bg-green-600/40 text-green-400 hover:bg-green-600/60 border border-green-600/30"}`}>
          {confirmTrade === "buy" ? "✓ 確認買入" : "🟢 買入"}
        </button>
        <button onClick={() => setConfirmTrade(null)} className="flex-1 py-2.5 rounded-lg font-bold text-sm bg-slate-700/60 text-slate-400 hover:bg-slate-700 border border-slate-600/30 transition-all">⚪ 觀望</button>
        <button onClick={() => handleTrade("reduce")} className={`flex-1 py-2.5 rounded-lg font-bold text-sm transition-all ${confirmTrade === "reduce" ? "bg-orange-500 text-white animate-pulse" : "bg-orange-600/40 text-orange-400 hover:bg-orange-600/60 border border-orange-600/30"}`}>
          {confirmTrade === "reduce" ? "✓ 確認減碼" : "🟠 減碼"}
        </button>
      </div>
    </div>
  );
}
