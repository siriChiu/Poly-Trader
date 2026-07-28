import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchApi, useApi } from "../hooks/useApi";

type Gate = {
  key?: string | null;
  label?: string | null;
  passed?: boolean | null;
  status?: string | null;
  summary?: string | null;
  next_action?: string | null;
  paper_shadow_available?: boolean | null;
};

type RuntimeStatus = {
  execution?: {
    mode?: string | null;
    venue?: string | null;
    live_runtime_truth?: {
      signal?: string | null;
      regime_label?: string | null;
      deployment_blocker?: string | null;
      deployment_blocker_reason?: string | null;
      runtime_closure_summary?: string | null;
      support_progress?: {
        current_rows?: number | null;
        minimum_support_rows?: number | null;
        gap_to_minimum?: number | null;
      } | null;
    } | null;
  } | null;
};

type ExecutionOverview = {
  execution_readiness?: {
    status?: string | null;
    stage_label?: string | null;
    live_ready?: boolean | null;
    canary_ready?: boolean | null;
    order_submission_enabled?: boolean | null;
    risk_on_order_enabled?: boolean | null;
    blocking_gate_label?: string | null;
    operator_message?: string | null;
    what_can_do_now?: string[] | null;
    next_release_condition?: string | null;
    live_runner_24h_shadow_gate?: {
      resolved_outcomes?: number | null;
      pending_outcomes?: number | null;
      next_reconcile_at?: string | null;
      pending_hours_remaining_min?: number | null;
    } | null;
    gates?: Gate[] | null;
    milestone_progression?: {
      active_lane_label?: string | null;
      operator_message?: string | null;
    } | null;
  } | null;
  summary?: {
    active_profiles?: number | null;
    running_runs?: number | null;
  } | null;
  profile_cards?: Array<{
    profile_id?: string | null;
    current_run?: { state?: string | null; strategy_name?: string | null } | null;
  }> | null;
  paper_shadow_outcome_reconciliation?: {
    artifact?: {
      resolved_outcomes?: number | null;
      pending_outcomes?: number | null;
      rehearsal_status?: string | null;
    } | null;
  } | null;
  user_action_state?: {
    state?: string | null;
    next_action?: string | null;
    deadline?: {
      status?: string | null;
      estimated_hours?: number | null;
      estimated_days?: number | null;
      summary?: string | null;
    } | null;
    alternative_lane?: {
      required?: boolean | null;
      label?: string | null;
      auto_adjustment_applied?: boolean | null;
    } | null;
    operator_fix?: { required?: boolean | null; label?: string | null } | null;
  } | null;
};

const gateLabel = (gate: Gate | undefined, fallback: string) => gate?.label || fallback;

function StepCard({ index, title, state, detail, active }: { index: number; title: string; state: string; detail: string; active?: boolean }) {
  return (
    <div className={`rounded-2xl border p-4 ${active ? "border-violet-400/40 bg-violet-500/10" : "border-white/8 bg-slate-950/25"}`}>
      <div className="flex items-center gap-3">
        <span className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${active ? "bg-violet-400 text-slate-950" : "bg-slate-800 text-slate-300"}`}>{index}</span>
        <div>
          <div className="text-sm font-semibold text-white">{title}</div>
          <div className={`text-xs ${active ? "text-violet-200" : "text-slate-400"}`}>{state}</div>
        </div>
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-400">{detail}</p>
    </div>
  );
}

export default function CommandCenter() {
  const { data: status, loading: statusLoading, error: statusError, refresh: refreshStatus } = useApi<RuntimeStatus>("/api/status", 30000);
  const { data: overview, loading: overviewLoading, error: overviewError, refresh: refreshOverview } = useApi<ExecutionOverview>("/api/execution/overview", 30000);
  const [starting, setStarting] = useState(false);
  const [actionResult, setActionResult] = useState<{ ok: boolean; message: string } | null>(null);

  const readiness = overview?.execution_readiness;
  const actionState = overview?.user_action_state;
  const runnerEvidence = readiness?.live_runner_24h_shadow_gate;
  const truth = status?.execution?.live_runtime_truth;
  const gates = Array.isArray(readiness?.gates) ? readiness.gates : [];
  const modelGate = gates.find((gate) => gate.key === "model_gate");
  const shadowGate = gates.find((gate) => gate.key === "shadow_evidence_subgate" || gate.key === "paper_shadow_outcome_reconciliation");
  const support = truth?.support_progress;
  const loading = statusLoading || overviewLoading;
  const error = statusError || overviewError;
  const selectiveRun = overview?.profile_cards?.find((card) => card.profile_id === "selective")?.current_run;
  const outcome = overview?.paper_shadow_outcome_reconciliation?.artifact;
  const resolvedOutcomes = runnerEvidence?.resolved_outcomes ?? outcome?.resolved_outcomes ?? 0;
  const pendingOutcomes = runnerEvidence?.pending_outcomes ?? outcome?.pending_outcomes ?? 0;
  const liveReady = Boolean(readiness?.live_ready);
  const shadowUsable = Boolean(
    shadowGate?.passed
    || shadowGate?.paper_shadow_available
    || readiness?.milestone_progression?.active_lane_label?.toLowerCase().includes("shadow")
    || !liveReady,
  );

  const headline = useMemo(() => {
    if (loading) return { label: "同步系統狀態", tone: "text-slate-200", detail: "正在確認目前能安全執行的最佳動作。" };
    if (error) return { label: "狀態同步失敗", tone: "text-amber-200", detail: "可重新整理；系統不會在狀態未知時送出新風險委託。" };
    if (liveReady) return { label: "已達 bounded canary", tone: "text-emerald-300", detail: "所有硬門檻已通過；仍只允許有數量上限的最小 canary。" };
    if (shadowUsable) return { label: "先跑 Paper / Shadow", tone: "text-violet-200", detail: "不用乾等 live 放行。現在就能凍結策略、產生決策並累積可驗證 outcome。" };
    return { label: "維持觀望 / 降風險", tone: "text-amber-200", detail: "目前沒有安全 risk-on lane；系統保持 no-order 並指出下一個解阻條件。" };
  }, [error, liveReady, loading, shadowUsable]);

  const startBestShadow = async () => {
    setStarting(true);
    setActionResult(null);
    try {
      const started = await fetchApi("/api/execution/runs/selective/start", { method: "POST" }) as any;
      const polled = await fetchApi("/api/execution/workers/poll", { method: "POST" }) as any;
      const processed = Number(polled?.summary?.processed_runs ?? 0);
      setActionResult({
        ok: true,
        message: started?.action_result === "noop_already_running"
          ? `影子 run 已在運行；本輪完成 ${processed} 次 worker tick。`
          : `影子 run 已啟動，並完成 ${processed} 次 worker tick；沒有送出實單。`,
      });
      await Promise.all([refreshStatus(), refreshOverview()]);
    } catch (err: any) {
      setActionResult({ ok: false, message: err?.message || "影子演練啟動失敗" });
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <section className="app-surface-hero overflow-hidden">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl">
            <div className="app-page-kicker">今日只看一件事</div>
            <h1 className={`mt-3 text-3xl font-semibold tracking-tight ${headline.tone}`}>{headline.label}</h1>
            <p className="mt-2 text-sm leading-6 text-slate-300">{headline.detail}</p>
            {!loading && !error && (
              <div className="mt-4 flex flex-wrap gap-2 text-xs">
                <span className="app-chip">訊號 {truth?.signal || "—"}</span>
                <span className="app-chip">市場 {truth?.regime_label || "—"}</span>
                <span className="app-chip">模式 {status?.execution?.mode || "paper"}</span>
                <span className="app-chip">場館 {status?.execution?.venue || "—"}</span>
              </div>
            )}
          </div>

          <div className="w-full rounded-2xl border border-violet-400/25 bg-violet-500/10 p-4 lg:max-w-md">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-200/70">建議下一步</div>
            <div className="mt-2 text-lg font-semibold text-white">
              {selectiveRun?.state === "running" ? "繼續累積影子證據" : "啟動最佳候選影子演練"}
            </div>
            <p className="mt-1 text-xs leading-5 text-violet-100/75">
              {actionState?.next_action || "凍結高信念候選並執行安全 worker；不送單。"}
            </p>
            {actionState?.alternative_lane?.required && (
              <div className="mt-3 rounded-xl border border-amber-300/20 bg-amber-300/8 px-3 py-2 text-[11px] leading-5 text-amber-100">
                Live 證據沒有可靠 ETA，系統已自動改走可產生 outcome 的替代路線，不再原地等待。
              </div>
            )}
            {runnerEvidence?.next_reconcile_at && (
              <div className="mt-2 text-[11px] text-violet-100/60">
                下次可對帳：{new Date(runnerEvidence.next_reconcile_at).toLocaleString("zh-TW")}
              </div>
            )}
            <button
              type="button"
              onClick={startBestShadow}
              disabled={starting || loading || Boolean(error)}
              className="app-button-primary mt-4 w-full disabled:cursor-not-allowed disabled:opacity-50"
            >
              {starting ? "正在執行…" : selectiveRun?.state === "running" ? "執行下一次安全 worker tick" : "立即開始 Paper / Shadow"}
            </button>
            {actionResult && (
              <div className={`mt-3 rounded-xl border px-3 py-2 text-xs leading-5 ${actionResult.ok ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-100" : "border-amber-400/30 bg-amber-400/10 text-amber-100"}`}>
                {actionResult.message}
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="app-surface-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-white">從研究到實戰，只保留三步</h2>
            <p className="mt-1 text-xs text-slate-400">每一步都有產出，不再只顯示「等待放行」。</p>
          </div>
          <div className="text-xs text-slate-400">
            已解決 {resolvedOutcomes} · 觀察中 {pendingOutcomes}
          </div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <StepCard
            index={1}
            title="回測候選"
            state={modelGate?.passed ? "已通過離線門檻" : "需要改善 / 選擇候選"}
            detail={gateLabel(modelGate, "用 ROI、回撤、PF 與 OOS 證據選候選，不用訓練準確率冒充可交易性。")}
            active={!modelGate?.passed}
          />
          <StepCard
            index={2}
            title="Paper / Shadow"
            state={selectiveRun?.state === "running" ? `運行中 · ${selectiveRun.strategy_name || "最佳候選"}` : shadowUsable ? "現在可執行" : "等待安全 lane"}
            detail="凍結策略與模型、執行 worker、記錄 24h outcome；此步驟永遠不送實單。"
            active={!liveReady && shadowUsable}
          />
          <StepCard
            index={3}
            title="Bounded Canary"
            state={liveReady ? "已可最小額驗證" : "硬門檻未全過"}
            detail="只有模型、即時證據、場館生命週期與數量上限全部通過，才會開啟最小額 canary。"
            active={liveReady}
          />
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.15fr,0.85fr]">
        <div className="app-surface-card">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-white">目前唯一阻塞點</h2>
            <span className={`app-chip ${liveReady ? "text-emerald-200" : "text-amber-200"}`}>{liveReady ? "已解除" : "Live 暫停"}</span>
          </div>
          <div className="mt-4 text-lg font-semibold text-slate-100">
            {liveReady
              ? "所有必要門檻已通過"
              : support?.current_rows != null && support?.minimum_support_rows != null
                ? `目前即時證據 ${support.current_rows}/${support.minimum_support_rows}`
                : readiness?.blocking_gate_label || "正在確認阻塞點"}
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            {liveReady
              ? "只允許有明確數量上限的最小 canary。"
              : "Live 買入暫停，但回測、Paper/Shadow、worker 與 outcome 收集都能繼續。"}
          </p>
          {support && (
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="app-surface-muted"><div className="text-slate-500">目前</div><div className="mt-1 text-lg font-semibold text-white">{support.current_rows ?? "—"}</div></div>
              <div className="app-surface-muted"><div className="text-slate-500">最低</div><div className="mt-1 text-lg font-semibold text-white">{support.minimum_support_rows ?? "—"}</div></div>
              <div className="app-surface-muted"><div className="text-slate-500">差距</div><div className="mt-1 text-lg font-semibold text-amber-200">{support.gap_to_minimum ?? "—"}</div></div>
            </div>
          )}
          {actionState?.operator_fix?.required && (
            <div className="mt-3 rounded-xl border border-cyan-400/20 bg-cyan-400/8 px-3 py-2 text-xs leading-5 text-cyan-100">
              主動解阻：{actionState.operator_fix.label || "執行替代路線與重新評估，不只累積等待時間。"}
            </div>
          )}
        </div>

        <div className="app-surface-card">
          <h2 className="text-base font-semibold text-white">工作入口</h2>
          <div className="mt-4 grid gap-2">
            <Link to="/lab" className="app-target-card text-left">
              <div className="font-semibold text-white">策略實驗室</div>
              <div className="mt-1 text-xs text-slate-400">選模型、回測、比較，直接送入 Paper/Shadow。</div>
            </Link>
            <Link to="/execution" className="app-target-card text-left">
              <div className="font-semibold text-white">Bot 營運</div>
              <div className="mt-1 text-xs text-slate-400">查看 run、worker、outcome 與停止控制。</div>
            </Link>
            <Link to="/diagnostics" className="app-target-card text-left">
              <div className="font-semibold text-white">進階診斷</div>
              <div className="mt-1 text-xs text-slate-400">只在需要時查看完整感測、gate 與場館細節。</div>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
