/**
 * SignalBanner — Trading signal + manual buy/sell + automation toggle
 */
import { useEffect, useState } from "react";
import {
  humanizeCurrentLiveBlockerLabel,
  humanizeExecutionReason,
  humanizeRuntimeClosureStateLabel,
  humanizeRuntimeDetailText,
} from "../utils/runtimeCopy";

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
  current_live_structure_bucket?: string | null;
  current_live_structure_bucket_rows?: number | null;
  minimum_support_rows?: number | null;
  current_live_structure_bucket_gap_to_minimum?: number | null;
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
  const runtimeAllowedLayersRawReasonLabel = humanizeExecutionReason(runtimeDecision?.allowed_layers_raw_reason || null);
  const runtimeAllowedLayersReasonLabel = humanizeRuntimeDetailText(runtimeDecision?.allowed_layers_reason || null);
  const runtimeClosureStateLabel = humanizeRuntimeClosureStateLabel(
    runtimeDecision?.runtime_closure_state,
    runtimeDecision?.runtime_closure_summary,
  );
  const runtimeClosureSummaryLabel = humanizeRuntimeDetailText(
    runtimeDecision?.runtime_closure_summary || "尚未取得部署閉環摘要。",
  );
  const runtimeDeploymentBlocker = runtimeDecision?.deployment_blocker || null;
  const runtimeDeploymentBlockerLabel = humanizeCurrentLiveBlockerLabel(runtimeDeploymentBlocker);
  const runtimeShortcutPending = !runtimeDecision;
  const runtimeShortcutBlocked = runtimeShortcutPending
    || Boolean(runtimeDeploymentBlocker)
    || ((runtimeDecision?.allowed_layers ?? 0) <= 0);
  const runtimeShortcutBlockerLabel = runtimeShortcutPending
    ? "正在同步即時執行狀態"
    : runtimeDeploymentBlocker
      ? runtimeDeploymentBlockerLabel
      : "目前有效層數為 0";
  const currentSupportRows = runtimeDecision?.current_live_structure_bucket_rows ?? null;
  const currentSupportMinimum = runtimeDecision?.minimum_support_rows ?? null;
  const currentSupportGap = runtimeDecision?.current_live_structure_bucket_gap_to_minimum ?? null;
  const currentSupportLabel = currentSupportRows != null
    ? `當前樣本 ${currentSupportRows}/${currentSupportMinimum ?? "—"}${currentSupportGap != null ? ` · 缺口 ${currentSupportGap}` : ""}`
    : null;

  const showShortcutBlockedMessage = () => {
    setStatusMsg(`⛔ 快捷下單已暫停：${runtimeShortcutBlockerLabel}。請先到執行狀態頁確認完整阻塞點。`);
    setTimeout(() => setStatusMsg(null), 5000);
  };

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
    if (runtimeShortcutBlocked) {
      showShortcutBlockedMessage();
      setConfirmBuy(false);
      setConfirmSell(false);
      return;
    }

    try {
      const resp = await fetch("/api/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ side: side.toLowerCase(), symbol: "BTCUSDT" }),
      });
      const data = await resp.json();
      const orderId = data.order_id || data.order?.order_id || null;
      setStatusMsg(
        data.error
          ? `❌ ${humanizeRuntimeDetailText(data.error)}`
          : orderId
            ? `✅ ${side} 訂單已提交：${orderId}`
            : "✅ 模擬委託已記錄；請回執行狀態頁確認保護欄與委託回放。"
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
        <div className={`mb-4 rounded-lg border px-3 py-2 text-xs leading-5 ${runtimeShortcutBlocked ? "border-amber-500/30 bg-amber-500/10 text-amber-100" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"}`}>
          <div className="font-semibold">即時執行快照</div>
          <div className="mt-1">
            訊號 {runtimeDecision.signal || "—"} · 層數 {runtimeDecision.allowed_layers_raw ?? "—"} → {runtimeDecision.allowed_layers ?? "—"} · 原始原因 {runtimeAllowedLayersRawReasonLabel} · 最終原因 {runtimeAllowedLayersReasonLabel}
          </div>
          {currentSupportLabel && (
            <div className="mt-1">{currentSupportLabel}</div>
          )}
          <div className="mt-1">
            部署閉環 {runtimeClosureStateLabel} · {runtimeClosureSummaryLabel}
          </div>
          {circuitBreakerActive && (
            <div className="mt-1">
              熔斷保護：最近 {breakerWindow ?? 50} 筆解除視窗 {breakerWins ?? "—"}/{breakerWindow ?? "—"}，勝率 {breakerRecentWinRate != null ? `${(breakerRecentWinRate * 100).toFixed(1)}%` : "—"}，解除門檻 {breakerFloor != null ? `${(breakerFloor * 100).toFixed(1)}%` : "—"}，至少還差 {breakerWinsGap ?? "—"} 勝。不要把支持樣本 / 元件修補方案當成熔斷解除替代品。
            </div>
          )}
          <div className="mt-1">
            {circuitBreakerActive
              ? "目前即時交易路徑仍被熔斷保護擋下；快捷面板只同步解除條件，不可把這裡誤讀成可部署狀態。"
              : runtimeDecision.q15_exact_supported_component_patch_applied
                ? ((runtimeDecision.allowed_layers ?? 0) > 0
                    ? "目前精準樣本已就緒且修補方案已套用；即使訊號仍是 HOLD，也只代表執行期已開出 1 層可部署容量，不等於自動買入。"
                    : "目前支援修補方案已經作用在當前即時資料列，但執行期仍被阻塞點 / 保護欄壓回 0 層；這代表修補方案已套用，但執行仍被阻擋。")
                : runtimeShortcutBlocked
                  ? `快捷下單已暫停：${runtimeShortcutBlockerLabel}；請改看執行狀態頁確認完整即時真相。`
                  : "目前未偵測到阻塞點；仍以執行狀態頁的完整治理與委託回放為準。"}
          </div>
        </div>
      )}

      {/* Trade buttons */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => runtimeShortcutBlocked ? showShortcutBlockedMessage() : setConfirmBuy(true)}
          disabled={runtimeShortcutBlocked}
          className={`flex-1 px-3 py-2 rounded-lg font-medium transition-colors ${
            runtimeShortcutBlocked
              ? "cursor-not-allowed border border-amber-500/30 bg-amber-950/30 text-amber-100/60"
              : "bg-green-600 hover:bg-green-500 text-white"
          }`}
        >
          {runtimeShortcutBlocked ? "買入暫停" : "買入"}
        </button>
        <button
          onClick={() => runtimeShortcutBlocked ? showShortcutBlockedMessage() : setConfirmSell(true)}
          disabled={runtimeShortcutBlocked}
          className={`flex-1 px-3 py-2 rounded-lg font-medium transition-colors ${
            runtimeShortcutBlocked
              ? "cursor-not-allowed border border-amber-500/30 bg-amber-950/30 text-amber-100/60"
              : "bg-red-600 hover:bg-red-500 text-white"
          }`}
        >
          {runtimeShortcutBlocked ? "賣出暫停" : "賣出"}
        </button>
      </div>

      {runtimeShortcutBlocked && (
        <div className="mb-3 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs leading-5 text-amber-100">
          快捷下單暫停：{runtimeShortcutBlockerLabel}。此面板只能查看狀態；請到執行狀態頁確認完整阻塞點、樣本支持與委託回放。
        </div>
      )}

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
        <div>快捷面板目前只提供受阻塞點保護的下單入口 / 自動交易切換；完整阻塞點、保護欄脈絡、治理狀態與恢復脈絡請到執行狀態頁查看。</div>
        <div className="mt-1">若支援修補方案已啟用但訊號仍是 HOLD，這裡應理解為「部署容量已開但訊號仍維持 HOLD」，不是修補方案失效，也不是自動買入就緒。</div>
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
