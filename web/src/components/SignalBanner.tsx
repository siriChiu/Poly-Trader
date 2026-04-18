/**
 * SignalBanner — Trading signal + manual buy/sell + automation toggle
 */
import { useEffect, useState } from "react";

interface Props {
  confidence: number;
  signal: string;
  timestamp?: string;
}

interface RuntimeDecisionSnapshot {
  signal?: string;
  confidence?: number;
  allowed_layers?: number | null;
  allowed_layers_raw?: number | null;
  allowed_layers_raw_reason?: string | null;
  allowed_layers_reason?: string | null;
  deployment_blocker?: string | null;
  deployment_blocker_details?: {
    recent_window?: {
      window_size?: number | null;
      wins?: number | null;
      win_rate?: number | null;
      floor?: number | null;
    } | null;
    release_condition?: {
      recent_window?: number | null;
      current_recent_window_wins?: number | null;
      current_recent_window_win_rate?: number | null;
      required_recent_window_wins?: number | null;
      additional_recent_window_wins_needed?: number | null;
      recent_win_rate_must_be_at_least?: number | null;
    } | null;
  } | null;
  runtime_closure_state?: string | null;
  runtime_closure_summary?: string | null;
  q15_exact_supported_component_patch_applied?: boolean | null;
}

export default function SignalBanner({ confidence, signal, timestamp }: Props) {
  const [confirmBuy, setConfirmBuy] = useState(false);
  const [confirmSell, setConfirmSell] = useState(false);
  const [automation, setAutomation] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [runtimeDecision, setRuntimeDecision] = useState<RuntimeDecisionSnapshot | null>(null);

  const isBuy = signal === "BUY";
  const confidencePct = Math.round(confidence * 100);
  const deploymentBlockerDetails = runtimeDecision?.deployment_blocker_details ?? null;
  const breakerRecentWindow = deploymentBlockerDetails?.recent_window ?? null;
  const breakerRelease = deploymentBlockerDetails?.release_condition ?? null;
  const circuitBreakerActive = runtimeDecision?.deployment_blocker === "circuit_breaker_active";
  const breakerWindow = typeof breakerRelease?.recent_window === "number"
    ? breakerRelease.recent_window
    : (typeof breakerRecentWindow?.window_size === "number" ? breakerRecentWindow.window_size : null);
  const breakerWins = typeof breakerRelease?.current_recent_window_wins === "number"
    ? breakerRelease.current_recent_window_wins
    : (typeof breakerRecentWindow?.wins === "number" ? breakerRecentWindow.wins : null);
  const breakerWinsGap = typeof breakerRelease?.additional_recent_window_wins_needed === "number"
    ? breakerRelease.additional_recent_window_wins_needed
    : null;
  const breakerRecentWinRate = typeof breakerRelease?.current_recent_window_win_rate === "number"
    ? breakerRelease.current_recent_window_win_rate
    : (typeof breakerRecentWindow?.win_rate === "number" ? breakerRecentWindow.win_rate : null);
  const breakerFloor = typeof breakerRelease?.recent_win_rate_must_be_at_least === "number"
    ? breakerRelease.recent_win_rate_must_be_at_least
    : (typeof breakerRecentWindow?.floor === "number" ? breakerRecentWindow.floor : null);

  useEffect(() => {
    let cancelled = false;
    const loadRuntimeDecision = async () => {
      try {
        const resp = await fetch("/api/predict/confidence");
        const data = await resp.json();
        if (!cancelled) {
          setRuntimeDecision(data || null);
        }
      } catch {
        if (!cancelled) {
          setRuntimeDecision(null);
        }
      }
    };
    loadRuntimeDecision();
    const timer = window.setInterval(loadRuntimeDecision, 60000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

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
          className={`h-2 rounded-full transition-all ${
            isBuy ? "bg-green-400" : "bg-slate-500"
          }`}
          style={{ width: `${confidencePct}%` }}
        />
      </div>

      {runtimeDecision && (
        <div className={`mb-4 rounded-lg border px-3 py-2 text-xs leading-5 ${circuitBreakerActive ? "border-amber-500/30 bg-amber-500/10 text-amber-100" : runtimeDecision.q15_exact_supported_component_patch_applied ? ((runtimeDecision.allowed_layers ?? 0) > 0 ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-100" : "border-amber-500/30 bg-amber-500/10 text-amber-100") : "border-slate-700/40 bg-slate-900/40 text-slate-300"}`}>
          <div className="font-semibold">q15 runtime 快照</div>
          <div className="mt-1">
            signal {runtimeDecision.signal || "—"} · layers {runtimeDecision.allowed_layers_raw ?? "—"} → {runtimeDecision.allowed_layers ?? "—"} · raw reason {runtimeDecision.allowed_layers_raw_reason || "—"} · final reason {runtimeDecision.allowed_layers_reason || "—"}
          </div>
          <div className="mt-1">
            runtime closure {runtimeDecision.runtime_closure_state || "—"} · {runtimeDecision.runtime_closure_summary || "尚未取得 runtime closure summary。"}
          </div>
          {circuitBreakerActive && (
            <div className="mt-1">
              circuit breaker：recent 50 release window {breakerWins ?? "—"}/{breakerWindow ?? "—"}，win rate {breakerRecentWinRate != null ? `${(breakerRecentWinRate * 100).toFixed(1)}%` : "—"}，floor {breakerFloor != null ? `${(breakerFloor * 100).toFixed(1)}%` : "—"}，至少還差 {breakerWinsGap ?? "—"} 勝。不要把 support / component patch 當成 breaker release 替代品。
            </div>
          )}
          <div className="mt-1">
            {circuitBreakerActive
              ? "目前 canonical live path 仍被 circuit breaker 擋下；SignalBanner 只同步 release math，不可把這裡的快捷面板誤讀成 deployment readiness。"
              : runtimeDecision.q15_exact_supported_component_patch_applied
                ? ((runtimeDecision.allowed_layers ?? 0) > 0
                    ? "目前是 support-ready + patch active；即使 signal 仍是 HOLD，也代表 runtime 已開出 1 層 deployment capacity，不等於自動 BUY。"
                    : "目前 q15 patch 已經吃到 current live row，但 execution 仍被 blocker / guardrail 壓回 0 層；這裡要讀成 patch active but execution still blocked。")
                : "目前尚未觀察到 q15 patch active；若要確認完整 runtime truth，請改看執行狀態頁。"}
          </div>
        </div>
      )}

      {/* Trade buttons */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setConfirmBuy(true)}
          className="flex-1 px-3 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white font-medium transition-colors"
        >
          買入
        </button>
        <button
          onClick={() => setConfirmSell(true)}
          className="flex-1 px-3 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-medium transition-colors"
        >
          賣出
        </button>
      </div>

      {/* Confirmation dialogs */}
      {confirmBuy && (
        <div className="mb-3 p-3 bg-green-900/20 border border-green-700/30 rounded-lg">
          <div className="text-sm text-green-300 mb-2">確認買入？</div>
          <div className="flex gap-2">
            <button onClick={() => handleTrade("BUY")} className="px-3 py-1 rounded bg-green-600 text-white text-sm">確認</button>
            <button onClick={() => setConfirmBuy(false)} className="px-3 py-1 rounded bg-slate-600 text-white text-sm">取消</button>
          </div>
        </div>
      )}

      {confirmSell && (
        <div className="mb-3 p-3 bg-red-900/20 border border-red-700/30 rounded-lg">
          <div className="text-sm text-red-300 mb-2">確認賣出？</div>
          <div className="flex gap-2">
            <button onClick={() => handleTrade("SELL")} className="px-3 py-1 rounded bg-red-600 text-white text-sm">確認</button>
            <button onClick={() => setConfirmSell(false)} className="px-3 py-1 rounded bg-slate-600 text-white text-sm">取消</button>
          </div>
        </div>
      )}

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

      <div className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs leading-5 text-amber-100">
        <div>SignalBanner 目前只提供快捷下單 / 自動交易切換；完整 blocker、Guardrail context、stale governance 與 recovery 請到執行狀態頁查看。</div>
        <div className="mt-1">若 q15 patch active 但 signal 仍是 HOLD，這裡應理解為「capacity opened but signal still HOLD」，不是 patch 失效，也不是自動 BUY readiness。</div>
        <a href="/execution/status" className="mt-1 inline-flex text-[11px] font-semibold text-amber-200 underline underline-offset-2 hover:text-amber-100">
          前往執行狀態頁 →
        </a>
      </div>

      {/* Timestamp */}
      {timestamp && (
        <div className="mt-2 text-xs text-slate-500 text-center">
          更新: {new Date(timestamp).toLocaleString("zh-TW")}
        </div>
      )}
    </div>
  );
}
