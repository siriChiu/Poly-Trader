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
  onTrade?: (side: string) => Promise<void> | void;
  executionActionState?: "syncing" | "blocked" | "ready";
  executionBlockerLabel?: string;
  executionBlockerReason?: string;
  maturitySummary?: {
    core: number;
    research: number;
    blocked: number;
  };
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

export default function AdviceCard({
  score = 50,
  summary = "分析中...",
  descriptions = [],
  action = "hold",
  timestamp,
  onTrade,
  executionActionState = "syncing",
  executionBlockerLabel,
  executionBlockerReason,
  maturitySummary,
}: Props) {
  const [confirmTrade, setConfirmTrade] = useState<string | null>(null);
  const [tradeStatus, setTradeStatus] = useState<string | null>(null);
  const [isSubmittingTrade, setIsSubmittingTrade] = useState(false);
  const [prevScore, setPrevScore] = useState(score);
  const [delta, setDelta] = useState(0);

  useEffect(() => { setDelta(score - prevScore); setPrevScore(score); }, [score]);

  const tradeActionsDisabled = executionActionState !== "ready" || isSubmittingTrade;
  const executionActionSummary = executionActionState === "syncing"
    ? "正在同步 /api/status；Dashboard 建議卡暫不提供快捷下單，避免 current live blocker truth 尚未到位前出現誤導 CTA。"
    : (executionBlockerReason || "目前 current live blocker 尚未解除；Dashboard 建議卡只保留分析摘要，快捷交易請改到執行狀態 / Bot 營運頁。");

  const handleTrade = async (side: string) => {
    if (tradeActionsDisabled) return;
    if (confirmTrade === side) {
      const label = side === "buy" ? "買入" : side === "reduce" ? "減碼" : "觀望";
      setTradeStatus(`⏳ ${label} 指令已交由 Bot 營運處理，請以下方 execution feedback 為準。`);
      setIsSubmittingTrade(true);
      try {
        await onTrade?.(side);
      } finally {
        setIsSubmittingTrade(false);
        setConfirmTrade(null);
        setTimeout(() => setTradeStatus(null), 5000);
      }
    } else {
      setConfirmTrade(side);
      setTimeout(() => setConfirmTrade(null), 5000);
    }
  };

  const signalConfig = ACTION_CONFIG[action] || ACTION_CONFIG.hold;
  const displayConfig = executionActionState === "ready"
    ? signalConfig
    : executionActionState === "syncing"
      ? {
          text: "⏳ 先同步 runtime blocker",
          color: "text-sky-300",
          bg: "from-sky-950/30 to-slate-900",
          icon: "⏳",
        }
      : {
          text: `🚫 先解除 blocker · ${executionBlockerLabel || "blocked"}`,
          color: "text-amber-300",
          bg: "from-amber-950/30 to-slate-900",
          icon: "🚫",
        };

  return (
    <div className={`app-surface-card bg-gradient-to-br ${displayConfig.bg} space-y-3 h-full`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`text-5xl font-mono font-bold transition-all duration-500 ${getScoreLevel(score)}`}>{score}</div>
          {delta !== 0 && <div className={`text-sm font-bold ${delta > 0 ? "text-green-400" : "text-red-400"}`}>{delta > 0 ? "↑" : "↓"} {Math.abs(delta)}</div>}
        </div>
        <div className="text-right">
          <div className={`text-base font-bold ${displayConfig.color}`}>{displayConfig.icon} {displayConfig.text}</div>
          {timestamp && <div className="text-xs text-slate-500 mt-0.5">{timestamp}</div>}
        </div>
      </div>

      <div className="text-sm text-slate-200 leading-relaxed">{summary}</div>

      {maturitySummary && (
        <div className="bg-slate-900/40 border border-slate-700/50 rounded-lg px-3 py-2 space-y-2">
          <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold">
            <span className="text-slate-400">成熟度摘要</span>
            <span className="rounded-full border border-emerald-700/40 bg-emerald-950/40 px-2 py-0.5 text-emerald-300">
              核心 {maturitySummary.core}
            </span>
            <span className="rounded-full border border-sky-700/40 bg-sky-950/40 px-2 py-0.5 text-sky-300">
              研究 {maturitySummary.research}
            </span>
            <span className="rounded-full border border-amber-700/40 bg-amber-950/30 px-2 py-0.5 text-amber-300">
              阻塞 {maturitySummary.blocked}
            </span>
          </div>
          <div className="text-[11px] leading-relaxed text-slate-400">
            主建議卡請優先解讀核心訊號；研究與阻塞特徵保留在 Dashboard / FeatureChart 供觀察與排障，避免把成熟度不足的資料當成主判斷。
          </div>
        </div>
      )}

      {descriptions && descriptions.length > 0 && (
        <div className="bg-slate-800/30 rounded-lg p-2.5 space-y-0.5">
          {descriptions.map((d, i) => <div key={i} className="text-xs text-slate-400">{d}</div>)}
        </div>
      )}

      {tradeStatus && <div className="bg-green-900/30 border border-green-700/30 rounded-lg px-3 py-2 text-green-400 text-xs text-center">{tradeStatus}</div>}

      {tradeActionsDisabled ? (
        <>
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs leading-relaxed text-amber-100">
            <div className="font-semibold">
              {executionActionState === "syncing"
                ? "⏳ current live blocker 同步中"
                : `🚫 current live blocker · ${executionBlockerLabel || "blocked"}`}
            </div>
            <div className="mt-1">{executionActionSummary}</div>
            <div className="mt-2 text-[11px] text-amber-200/80">
              訊號分析仍為：{signalConfig.text}
            </div>
          </div>
          <div className="flex gap-2">
            <a href="/execution/status" className="app-button-secondary flex-1 text-center text-sm font-semibold">
              查看阻塞原因
            </a>
            <a href="/execution" className="app-button-secondary flex-1 text-center text-sm font-semibold">
              前往 Bot 營運
            </a>
          </div>
        </>
      ) : (
        <div className="flex gap-2">
          <button onClick={() => void handleTrade("buy")} disabled={isSubmittingTrade} className={`app-button-primary flex-1 text-sm font-bold ${confirmTrade === "buy" ? "animate-pulse bg-green-500 border-green-400" : "bg-green-600/40 text-green-100 hover:bg-green-600/60 border-green-600/30 shadow-none"}`}>
            {confirmTrade === "buy" ? "✓ 確認買入" : "🟢 買入"}
          </button>
          <button onClick={() => setConfirmTrade(null)} disabled={isSubmittingTrade} className="app-button-secondary flex-1 text-sm font-bold">⚪ 觀望</button>
          <button onClick={() => void handleTrade("reduce")} disabled={isSubmittingTrade} className={`app-button-primary flex-1 text-sm font-bold ${confirmTrade === "reduce" ? "animate-pulse bg-orange-500 border-orange-400" : "bg-orange-600/40 text-orange-100 hover:bg-orange-600/60 border-orange-600/30 shadow-none"}`}>
            {confirmTrade === "reduce" ? "✓ 確認減碼" : "🟠 減碼"}
          </button>
        </div>
      )}
    </div>
  );
}
