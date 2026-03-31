/**
 * AdviceCard — 建議卡片（大分數 + 自然語言 + 買賣按鈕）
 */
import { useState } from "react";

interface Props {
  score: number;
  summary: string;
  descriptions: string[];
  action: string;
  onTrade?: (side: string) => void;
}

export default function AdviceCard({ score, summary, descriptions, action, onTrade }: Props) {
  const [confirmSide, setConfirmSide] = useState<string | null>(null);

  const scoreColor =
    score > 80 ? "text-green-400" :
    score > 60 ? "text-yellow-400" :
    score > 40 ? "text-slate-300" :
    score > 20 ? "text-orange-400" : "text-red-400";

  const bgColor =
    score > 80 ? "from-green-900/30 to-slate-900" :
    score > 60 ? "from-yellow-900/20 to-slate-900" :
    score > 40 ? "from-slate-800/50 to-slate-900" :
    score > 20 ? "from-orange-900/20 to-slate-900" : "from-red-900/20 to-slate-900";

  const handleTrade = (side: string) => {
    if (confirmSide === side) {
      onTrade?.(side);
      setConfirmSide(null);
    } else {
      setConfirmSide(side);
      setTimeout(() => setConfirmSide(null), 3000);
    }
  };

  return (
    <div className={`bg-gradient-to-br ${bgColor} rounded-xl border border-slate-700/50 p-5`}>
      {/* 大分數 */}
      <div className="text-center mb-4">
        <div className={`text-6xl font-mono font-bold ${scoreColor} transition-all duration-500`}>
          {score}
        </div>
        <div className="text-sm text-slate-400 mt-1">綜合建議分數</div>
      </div>

      {/* 綜合建議 */}
      <div className="text-center text-lg font-medium text-slate-200 mb-4">
        {summary}
      </div>

      {/* 五感描述 */}
      <div className="space-y-1 mb-4">
        {descriptions.map((desc, i) => (
          <div key={i} className="text-sm text-slate-400 text-center">
            {desc}
          </div>
        ))}
      </div>

      {/* 買賣按鈕 */}
      <div className="flex gap-3">
        <button
          onClick={() => handleTrade("buy")}
          className={`flex-1 py-3 rounded-lg font-bold text-lg transition-all ${
            confirmSide === "buy"
              ? "bg-green-500 text-white scale-105"
              : "bg-green-600/30 text-green-400 hover:bg-green-600/50 border border-green-600/30"
          }`}
        >
          {confirmSide === "buy" ? "✓ 確認買入" : "🟢 買入"}
        </button>
        <button
          onClick={() => handleTrade("hold")}
          className="flex-1 py-3 rounded-lg font-bold text-lg bg-slate-700/50 text-slate-400 hover:bg-slate-700 border border-slate-600/30 transition-all"
        >
          ⚪ 觀望
        </button>
        <button
          onClick={() => handleTrade("sell")}
          className={`flex-1 py-3 rounded-lg font-bold text-lg transition-all ${
            confirmSide === "sell"
              ? "bg-red-500 text-white scale-105"
              : "bg-red-600/30 text-red-400 hover:bg-red-600/50 border border-red-600/30"
          }`}
        >
          {confirmSide === "sell" ? "✓ 確認賣出" : "🔴 賣出"}
        </button>
      </div>
    </div>
  );
}
