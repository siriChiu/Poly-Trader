/**
 * ConfidenceIndicator — 信心分層指示器
 * 顯示模型信心、信號、是否建議交易
 */
import React from "react";

interface Props {
  confidence: number;        // 0~1
  signal: string;            // BUY / SELL / HOLD
  confidenceLevel: string;   // HIGH / MEDIUM / LOW
  shouldTrade: boolean;
  timestamp?: string;
}

export default function ConfidenceIndicator({
  confidence, signal, confidenceLevel, shouldTrade, timestamp
}: Props) {
  const pct = Math.round(confidence * 100);
  
  const levelConfig: Record<string, { color: string; bg: string; label: string; emoji: string }> = {
    HIGH:   { color: "text-green-400",   bg: "bg-green-900/30 border-green-700/50",   label: "高信心",  emoji: "🎯" },
    MEDIUM: { color: "text-yellow-400",  bg: "bg-yellow-900/30 border-yellow-700/50",  label: "中信心",  emoji: "🤔" },
    LOW:    { color: "text-red-400",     bg: "bg-red-900/30 border-red-700/50",        label: "低信心",  emoji: "⚠️" },
  };
  
  const signalConfig: Record<string, { color: string; label: string }> = {
    BUY:  { color: "text-green-400",  label: "買入" },
    SELL: { color: "text-red-400",    label: "賣出" },
    HOLD: { color: "text-slate-400",  label: "觀望" },
  };

  const lv = levelConfig[confidenceLevel] || levelConfig.LOW;
  const sig = signalConfig[signal] || signalConfig.HOLD;

  return (
    <div className={`rounded-xl border p-5 ${lv.bg}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-slate-400">{lv.emoji} 信心分層</span>
        {shouldTrade && (
          <span className="px-2 py-0.5 text-xs font-bold rounded bg-green-600 text-white animate-pulse">
            建議交易
          </span>
        )}
      </div>
      
      {/* 大字信心 */}
      <div className="flex items-baseline gap-3 mb-2">
        <span className={`text-5xl font-mono font-bold ${lv.color}`}>{pct}%</span>
        <span className={`text-lg font-bold ${sig.color}`}>{sig.label}</span>
      </div>
      
      {/* 信心等級 */}
      <div className="flex items-center gap-2 text-sm">
        <span className={lv.color}>{lv.label}</span>
        <span className="text-slate-600">|</span>
        <span className="text-slate-500">
          {confidenceLevel === "HIGH" ? ">0.65 或 <0.35" : confidenceLevel === "MEDIUM" ? "0.45~0.65" : "0.45~0.55"}
        </span>
      </div>
      
      {/* 信心條 */}
      <div className="mt-3 h-2 bg-slate-800 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all ${
            pct > 65 ? "bg-green-500" : pct > 55 ? "bg-yellow-500" : "bg-red-500"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      
      {timestamp && (
        <div className="mt-2 text-xs text-slate-600">
          更新: {new Date(timestamp).toLocaleTimeString("zh-TW")}
        </div>
      )}
    </div>
  );
}
