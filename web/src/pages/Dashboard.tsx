/**
 * Dashboard v2.0 — 使用者體驗增強版
 */
import { useState, useEffect, useCallback } from "react";
import RadarChart from "../components/RadarChart";
import AdviceCard from "../components/AdviceCard";
import FeatureChart from "../components/FeatureChart";
import CandlestickChart from "../components/CandlestickChart";
import { buildWsUrl, useApi, fetchApi } from "../hooks/useApi";
import ConfidenceIndicator from "../components/ConfidenceIndicator";
import { ALL_SENSES, getSenseConfig } from "../config/senses";

interface SensesResponse {
  senses: Record<string, any>;
  scores: Record<string, number>;
  raw?: Record<string, number>;
  recommendation: {
    score: number;
    summary: string;
    descriptions: string[];
    action: string;
    timestamp?: string;
  };
}

interface FeatureCoverageResponse {
  maturity_counts?: {
    core: number;
    research: number;
    blocked: number;
  };
}

interface ModelStats {
  model_loaded: boolean;
  sample_count: number;
  label_distribution: Record<string, number>;
  cv_accuracy: number | null;
  feature_importance: Record<string, number>;
  ic_values: Record<string, number>;
  model_params: Record<string, any>;
}

interface RuntimeStatusResponse {
  automation: boolean;
  dry_run: boolean;
  symbol: string;
  timestamp: string;
  execution_metadata_smoke?: {
    available?: boolean;
    artifact_path?: string;
    generated_at?: string;
    symbol?: string;
    all_ok?: boolean;
    ok_count?: number;
    venues_checked?: number;
    error?: string;
    freshness?: {
      status?: "fresh" | "stale" | "unavailable" | string;
      label?: string;
      reason?: string;
      age_minutes?: number | null;
      stale_after_minutes?: number | null;
    } | null;
    governance?: {
      status?: string;
      operator_action?: string;
      operator_message?: string;
      refresh_command?: string;
      escalation_message?: string | null;
      auto_refresh?: {
        attempted_at?: string | null;
        completed_at?: string | null;
        status?: string;
        reason?: string;
        next_retry_at?: string | null;
        error?: string | null;
        cooldown_seconds?: number | null;
      } | null;
      background_monitor?: {
        status?: string;
        reason?: string;
        checked_at?: string | null;
        freshness_status?: string | null;
        governance_status?: string | null;
        error?: string | null;
        interval_seconds?: number | null;
      } | null;
      external_monitor?: {
        available?: boolean;
        artifact_path?: string;
        source?: string;
        status?: string;
        reason?: string;
        checked_at?: string | null;
        freshness_status?: string | null;
        governance_status?: string | null;
        error?: string | null;
        interval_seconds?: number | null;
        command?: string | null;
        install_contract?: {
          preferred_host_lane?: string;
          generator_command?: string;
          manual_run_command?: string;
          fallback?: {
            reason?: string;
            command?: string;
            verify_command?: string;
          } | null;
          user_crontab?: {
            schedule?: string;
            entry?: string;
            install_command?: string;
            verify_command?: string;
          } | null;
          systemd_user?: {
            service_file?: string;
            timer_file?: string;
            verify_command?: string;
          } | null;
        } | null;
        freshness?: {
          status?: "fresh" | "stale" | "unavailable" | string;
          label?: string;
          reason?: string;
          age_minutes?: number | null;
          stale_after_minutes?: number | null;
        } | null;
      } | null;
    } | null;
    venues?: Array<{
      venue?: string;
      ok?: boolean;
      enabled_in_config?: boolean;
      credentials_configured?: boolean;
      error?: string | null;
      contract?: {
        symbol?: string;
        min_qty?: number | null;
        min_cost?: number | null;
        step_size?: string | number | null;
        tick_size?: string | number | null;
      } | null;
    }>;
  } | null;
  execution?: {
    mode?: string;
    venue?: string;
    live_enabled?: boolean;
    kill_switch?: boolean;
    health?: {
      connected?: boolean;
      credentials_configured?: boolean;
      [key: string]: unknown;
    } | null;
    guardrails?: {
      kill_switch?: boolean;
      max_daily_loss_pct?: number;
      daily_loss_ratio?: number | null;
      daily_loss_halt?: boolean;
      max_consecutive_failures?: number;
      consecutive_failures?: number;
      failure_halt?: boolean;
      last_failure?: { message?: string; timestamp?: string } | null;
      last_reject?: {
        code?: string;
        message?: string;
        timestamp?: string;
        context?: {
          field?: string;
          raw_value?: number | null;
          adjusted_value?: number | null;
          delta?: number | null;
          step_size?: string | number | null;
          precision?: string | number | null;
          rules?: Record<string, unknown> | null;
        } | null;
      } | null;
      last_order?: {
        venue?: string;
        symbol?: string;
        side?: string;
        qty?: number;
        price?: number | null;
        status?: string;
        timestamp?: number;
        normalization?: {
          requested?: { qty?: number | null; price?: number | null; symbol?: string; side?: string; type?: string } | null;
          normalized?: {
            qty?: number | null;
            price?: number | null;
            symbol?: string;
            side?: string;
            type?: string;
            qty_changed?: boolean;
            price_changed?: boolean;
          } | null;
          contract?: {
            step_size?: string | number | null;
            tick_size?: string | number | null;
            min_qty?: number | null;
            min_cost?: number | null;
          } | null;
        } | null;
      } | null;
    } | null;
  } | null;
  account?: {
    venue?: string;
    mode?: string;
    dry_run?: boolean;
    balance?: {
      free?: number;
      total?: number;
      currency?: string;
      [key: string]: unknown;
    } | null;
    positions?: Array<Record<string, unknown>>;
    open_orders?: Array<Record<string, unknown>>;
    health?: {
      connected?: boolean;
      credentials_configured?: boolean;
      [key: string]: unknown;
    } | null;
  } | null;
  raw_continuity?: {
    status?: "clean" | "repaired" | "error" | string;
    checked_at?: string;
    error?: string;
    continuity_repair?: {
      inserted_total?: number;
      coarse_inserted?: number;
      fine_inserted?: number;
      bridge_inserted?: number;
      used_bridge?: boolean;
      used_fine_grain?: boolean;
    };
  } | null;
  feature_continuity?: {
    status?: "clean" | "repaired" | "error" | string;
    checked_at?: string;
    error?: string;
    continuity_repair?: {
      inserted_total?: number;
      remaining_missing?: number;
    };
  } | null;
}

interface ConfidenceData {
  error?: string;
  confidence: number;
  signal: string;
  confidence_level: string;
  should_trade: boolean;
  regime_gate?: string | null;
  entry_quality?: number | null;
  entry_quality_label?: string | null;
  allowed_layers?: number | null;
  decision_quality_horizon_minutes?: number | null;
  decision_quality_calibration_scope?: string | null;
  decision_quality_sample_size?: number | null;
  expected_win_rate?: number | null;
  expected_pyramid_quality?: number | null;
  expected_drawdown_penalty?: number | null;
  expected_time_underwater?: number | null;
  decision_quality_score?: number | null;
  decision_quality_label?: string | null;
  decision_profile_version?: string | null;
  timestamp: string;
}

interface DashboardScorePoint {
  timestamp: string;
  score?: number | null;
}

interface TradeFeedbackState {
  tone: "success" | "error" | "pending";
  title: string;
  detail: string;
  timestamp: string;
}

interface FeatureHistoryRow {
  timestamp: string;
  [key: string]: string | number | null | undefined;
}

const DASHBOARD_SCORE_WEIGHTS: Record<string, number> = {
  pulse: 0.18,
  eye: 0.12,
  nose: 0.12,
  tongue: 0.08,
  body: 0.06,
  bb_pct_b: 0.10,
  nw_slope: 0.08,
  adx: 0.05,
  vix: 0.04,
  dxy: 0.04,
  "4h_bias50": 0.07,
  "4h_dist_swing_low": 0.04,
  "4h_rsi14": 0.02,
};

function computeDashboardCompositeScore(row: Record<string, string | number | null | undefined>): number | null {
  let weightedSum = 0;
  let weightTotal = 0;
  for (const [key, weight] of Object.entries(DASHBOARD_SCORE_WEIGHTS)) {
    const value = row[key];
    if (typeof value !== "number" || !Number.isFinite(value)) continue;
    weightedSum += value * weight;
    weightTotal += weight;
  }
  if (weightTotal <= 0) return null;
  return Math.max(0, Math.min(1, weightedSum / weightTotal));
}

function formatGuardrailValue(value: unknown, digits = 6): string {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "—";
    return value.toFixed(digits).replace(/\.?0+$/, "");
  }
  if (typeof value === "string" && value.trim()) return value;
  return "—";
}

function formatGuardrailRules(rules: Record<string, unknown> | null | undefined): string[] {
  if (!rules) return [];
  return Object.entries(rules)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => `${key}: ${formatGuardrailValue(value)}`);
}

function getSmokeFreshnessTone(status: string | undefined | null): string {
  if (status === "fresh") return "border-emerald-700/40 bg-emerald-950/20 text-emerald-200";
  if (status === "stale") return "border-amber-700/40 bg-amber-950/20 text-amber-200";
  return "border-slate-700/40 bg-slate-950/20 text-slate-300";
}

function getSmokeFreshnessLabel(status: string | undefined | null): string {
  if (status === "fresh") return "FRESH";
  if (status === "stale") return "STALE";
  return "UNAVAILABLE";
}

function getSmokeGovernanceTone(status: string | undefined | null): string {
  if (status === "healthy") return "border-emerald-700/40 bg-emerald-950/20 text-emerald-200";
  if (status === "refresh_required") return "border-amber-700/40 bg-amber-950/20 text-amber-200";
  return "border-red-700/40 bg-red-950/20 text-red-200";
}

export default function Dashboard() {
  const [interval, setInterval] = useState("4h");
  const [days, setDays] = useState(14);
  const [selectedSense, setSelectedSense] = useState<string | null>(null);
  const [showFeatureHistory, setShowFeatureHistory] = useState(false);
  const [dashboardScoreSeries, setDashboardScoreSeries] = useState<DashboardScorePoint[]>([]);
  // Build initial scores from ALL known features (8 core + 2 macro + 5 TI + 6 P0/P1 + 10 4H)
  const defaultScores: Record<string, number> = {};
  const allFeatures = [...Object.keys(ALL_SENSES)];
  for (const key of allFeatures) {
    defaultScores[key] = 0.5;
  }

  const [liveScores, setLiveScores] = useState<Record<string, number>>(defaultScores);
  const [liveAdvice, setLiveAdvice] = useState<any>(null);
  const [lastUpdate, setLastUpdate] = useState<string>();
  const [wsConnected, setWsConnected] = useState(false);
  const [tradeFeedback, setTradeFeedback] = useState<TradeFeedbackState | null>(null);

  const { data: sensesData, error: apiError, refresh: refreshSenses } = useApi<SensesResponse>("/api/senses", 30000);
  const { data: featureCoverageData } = useApi<FeatureCoverageResponse>("/api/features/coverage?days=30", 60000);
  const { data: confidenceData } = useApi<ConfidenceData>("/api/predict/confidence", 60000);
  const { data: modelStats } = useApi<ModelStats>("/api/model/stats", 60000);
  const { data: runtimeStatus, refresh: refreshRuntimeStatus } = useApi<RuntimeStatusResponse>("/api/status", 60000);

  // WebSocket
  useEffect(() => {
    const url = buildWsUrl("/ws/live");
    let ws: WebSocket | null = null;
    let timer: number;

    const connect = () => {
      try {
        ws = new WebSocket(url);
        ws.onopen = () => setWsConnected(true);
        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "senses_update" || msg.type === "connected") {
              const data = msg.data;
              if (data?.scores) setLiveScores(data.scores);
              if (data?.recommendation) setLiveAdvice(data.recommendation);
              if (data?.timestamp) setLastUpdate(new Date(data.timestamp).toLocaleTimeString("zh-TW"));
            }
          } catch {}
        };
        ws.onclose = () => {
          setWsConnected(false);
          timer = window.setTimeout(connect, 5000);
        };
        ws.onerror = () => setWsConnected(false);
      } catch {
        setWsConnected(false);
        timer = window.setTimeout(connect, 5000);
      }
    };
    connect();
    return () => { clearTimeout(timer); ws?.close(); };
  }, []);

  // 更新最後更新時間
  useEffect(() => {
    if (sensesData?.recommendation?.timestamp) {
      setLastUpdate(new Date(sensesData.recommendation.timestamp).toLocaleTimeString("zh-TW"));
    }
  }, [sensesData]);

  useEffect(() => {
    let cancelled = false;
    const loadScoreSeries = async () => {
      try {
        const rows = await fetchApi(`/api/features?days=${days}`) as FeatureHistoryRow[];
        const nextSeries = (rows || []).map((row) => ({
          timestamp: row.timestamp,
          score: computeDashboardCompositeScore(row),
        }));
        if (!cancelled) {
          setDashboardScoreSeries(nextSeries);
        }
      } catch (error) {
        if (!cancelled) {
          setDashboardScoreSeries([]);
        }
      }
    };
    loadScoreSeries();
    return () => {
      cancelled = true;
    };
  }, [days]);

  // 合併 live data 與 API data
  const scores = liveScores.eye !== 0.5 || liveScores.ear !== 0.5
    ? liveScores
    : sensesData?.scores || liveScores;

  const advice = liveAdvice || sensesData?.recommendation;
  const maturitySummary = featureCoverageData?.maturity_counts ?? null;
  const executionSummary = runtimeStatus?.execution ?? null;
  const accountSummary = runtimeStatus?.account ?? null;
  const metadataSmoke = runtimeStatus?.execution_metadata_smoke ?? null;
  const metadataSmokeFreshness = metadataSmoke?.freshness ?? null;
  const metadataSmokeGovernance = metadataSmoke?.governance ?? null;
  const metadataSmokeAutoRefresh = metadataSmokeGovernance?.auto_refresh ?? null;
  const metadataSmokeBackgroundMonitor = metadataSmokeGovernance?.background_monitor ?? null;
  const metadataSmokeExternalMonitor = metadataSmokeGovernance?.external_monitor ?? null;
  const externalMonitorInstallContract = metadataSmokeExternalMonitor?.install_contract ?? null;
  const metadataSmokeFreshnessTone = getSmokeFreshnessTone(metadataSmokeFreshness?.status);
  const metadataSmokeFreshnessLabel = getSmokeFreshnessLabel(metadataSmokeFreshness?.status);
  const metadataSmokeGovernanceTone = getSmokeGovernanceTone(metadataSmokeGovernance?.status);
  const rawContinuity = runtimeStatus?.raw_continuity ?? null;
  const featureContinuity = runtimeStatus?.feature_continuity ?? null;
  const executionModeLabel = executionSummary?.mode || accountSummary?.mode || "unknown";
  const executionVenueLabel = executionSummary?.venue || accountSummary?.venue || "—";
  const executionHealth = executionSummary?.health ?? accountSummary?.health ?? null;
  const balanceFree = typeof accountSummary?.balance?.free === "number" ? accountSummary.balance.free : null;
  const balanceTotal = typeof accountSummary?.balance?.total === "number" ? accountSummary.balance.total : null;
  const balanceCurrency = typeof accountSummary?.balance?.currency === "string" ? accountSummary.balance.currency : "USDT";
  const openOrderCount = Array.isArray(accountSummary?.open_orders) ? accountSummary.open_orders.length : 0;
  const positionCount = Array.isArray(accountSummary?.positions) ? accountSummary.positions.length : 0;
  const guardrails = executionSummary?.guardrails ?? null;
  const lastReject = guardrails?.last_reject ?? null;
  const lastRejectContext = lastReject?.context ?? null;
  const lastRejectRuleLines = formatGuardrailRules(lastRejectContext?.rules);
  const lastFailure = guardrails?.last_failure ?? null;
  const lastOrder = guardrails?.last_order ?? null;
  const tradeFeedbackTone = tradeFeedback?.tone === "success"
    ? "border-emerald-700/40 bg-emerald-950/20 text-emerald-200"
    : tradeFeedback?.tone === "error"
      ? "border-red-700/40 bg-red-950/20 text-red-200"
      : "border-sky-700/40 bg-sky-950/20 text-sky-200";
  const executionTone = executionSummary?.kill_switch || guardrails?.daily_loss_halt || guardrails?.failure_halt
    ? "border-red-700/40 bg-red-950/30 text-red-200"
    : executionModeLabel === "live"
      ? "border-emerald-700/40 bg-emerald-950/30 text-emerald-200"
      : executionModeLabel === "live_canary"
        ? "border-amber-700/40 bg-amber-950/30 text-amber-200"
        : "border-slate-700/40 bg-slate-950/30 text-slate-300";
  const continuityTone = rawContinuity?.status === "clean"
    ? "border-emerald-700/40 bg-emerald-950/30 text-emerald-200"
    : rawContinuity?.status === "repaired"
      ? "border-amber-700/40 bg-amber-950/30 text-amber-200"
      : rawContinuity?.status === "error"
        ? "border-red-700/40 bg-red-950/30 text-red-200"
        : "border-slate-700/40 bg-slate-950/30 text-slate-300";
  const continuityLabel = rawContinuity?.status === "clean"
    ? "raw 連續性正常"
    : rawContinuity?.status === "repaired"
      ? "啟動時已自動回填資料斷點"
      : rawContinuity?.status === "error"
        ? "啟動檢查失敗"
        : "尚未收到啟動檢查結果";

  const handleTrade = useCallback(async (side: string) => {
    if (side === "hold") return;
    const label = side === "buy" ? "買入" : side === "reduce" ? "減碼" : side.toUpperCase();
    setTradeFeedback({
      tone: "pending",
      title: `${label} 指令送出中`,
      detail: "正在提交 /api/trade，完成後會主動刷新 execution status。",
      timestamp: new Date().toLocaleString("zh-TW"),
    });
    try {
      const resp = await fetchApi("/api/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ side, symbol: "BTCUSDT", qty: 0.001 }),
      });
      await refreshRuntimeStatus();
      const data = resp as any;
      const mode = data?.order?.mode || (data?.dry_run ? "dry_run" : "live");
      const qty = typeof data?.order?.qty === "number" ? data.order.qty : null;
      const venue = data?.venue || "unknown";
      const normalizedQty = typeof data?.normalization?.normalized?.qty === "number" ? data.normalization.normalized.qty : qty;
      const normalizedPrice = typeof data?.normalization?.normalized?.price === "number" ? data.normalization.normalized.price : null;
      const stepSize = data?.normalization?.contract?.step_size;
      const tickSize = data?.normalization?.contract?.tick_size;
      const contractSummary = [
        stepSize != null ? `step ${formatGuardrailValue(stepSize)}` : null,
        tickSize != null ? `tick ${formatGuardrailValue(tickSize)}` : null,
      ].filter(Boolean).join(" · ");
      setTradeFeedback({
        tone: "success",
        title: `${label} 指令已提交`,
        detail: `模式 ${mode} · 場館 ${venue}${normalizedQty != null ? ` · normalized qty ${formatGuardrailValue(normalizedQty)}` : ""}${normalizedPrice != null ? ` · normalized price ${formatGuardrailValue(normalizedPrice)}` : ""}${contractSummary ? ` · contract ${contractSummary}` : ""}。已主動刷新 /api/status。`,
        timestamp: new Date().toLocaleString("zh-TW"),
      });
    } catch (e: any) {
      await refreshRuntimeStatus();
      const detail = typeof e?.message === "string" ? e.message : "未知錯誤";
      setTradeFeedback({
        tone: "error",
        title: `${label} 指令被拒絕或失敗`,
        detail: `${detail}。已主動刷新 /api/status，請檢查下方 Guardrail context 面板。`,
        timestamp: new Date().toLocaleString("zh-TW"),
      });
    }
  }, [refreshRuntimeStatus]);

  // 判斷資料新鮮度
  const isDataStale = !lastUpdate && !wsConnected && !sensesData;

  return (
    <div className="space-y-4">
      {/* Top bar */}
      <div className="flex flex-wrap items-center justify-between bg-slate-900/60 rounded-xl border border-slate-700/50 px-4 py-2 text-xs gap-2">
        <div className="flex items-center gap-3">
          <span className="font-bold text-slate-300">🐰 Poly-Trader</span>
          {/* 狀態指示器 */}
          <span className={`flex items-center gap-1 ${wsConnected ? "text-green-400" : "text-orange-400"}`}>
            <span className={`w-2 h-2 rounded-full ${wsConnected ? "bg-green-400" : "bg-orange-400"}`} />
            {wsConnected ? "即時連線" : "離線"}
          </span>
          {lastUpdate && (
            <span className="text-slate-500">更新: {lastUpdate}</span>
          )}
          {/* 模型準確率 — show top IC features dynamically */}
          {modelStats?.ic_values && Object.keys(modelStats.ic_values).length > 0 && (
            <span className="flex items-center gap-1 text-slate-400">
              📊 樣本:{modelStats.sample_count}
              {(() => {
                const topIcs = Object.entries(modelStats.ic_values)
                  .filter(([k, v]) => typeof v === "number")
                  .sort((a, b) => Math.abs(b[1] as number) - Math.abs(a[1] as number))
                  .slice(0, 3);
                return topIcs.map(([name, val]) => (
                  <span key={name} className="text-xs opacity-70">
                    | {name.replace("4h_", "4H ")} IC: {(val as number) > 0 ? '+' : ''}{(val as number).toFixed(3)}
                  </span>
                ));
              })()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-slate-500">
          {apiError && <span className="text-red-400">API 連線異常</span>}
        </div>
      </div>

      <div className={`rounded-xl border px-4 py-3 text-xs ${executionTone}`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="font-semibold">💼 Execution 狀態面板</div>
          <div className="text-[11px] opacity-80">
            {executionModeLabel.toUpperCase()} · {executionVenueLabel}
            {executionSummary?.kill_switch ? " · KILL SWITCH" : ""}
          </div>
        </div>
        <div className="mt-2 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-white/10 bg-slate-950/20 p-3">
            <div className="text-[11px] opacity-70">模式 / 場館</div>
            <div className="mt-1 font-semibold">{executionModeLabel} · {executionVenueLabel}</div>
            <div className="mt-1 text-[11px] opacity-80">
              live enabled: {executionSummary?.live_enabled ? "yes" : "no"}
            </div>
            <div className="mt-1 text-[11px] opacity-80">
              {accountSummary?.dry_run ? "目前為 paper / dry-run" : "可能進入真實委託路徑"}
            </div>
          </div>
          <div className="rounded-lg border border-white/10 bg-slate-950/20 p-3">
            <div className="text-[11px] opacity-70">餘額</div>
            <div className="mt-1 font-semibold">
              {balanceFree !== null ? `${balanceFree.toFixed(2)} ${balanceCurrency}` : "—"}
            </div>
            <div className="mt-1 text-[11px] opacity-80">
              total {balanceTotal !== null ? balanceTotal.toFixed(2) : "—"}
            </div>
            <div className="mt-1 text-[11px] opacity-80">倉位 {positionCount} · 掛單 {openOrderCount}</div>
          </div>
          <div className="rounded-lg border border-white/10 bg-slate-950/20 p-3">
            <div className="text-[11px] opacity-70">連線 / 憑證 / Halt</div>
            <div className="mt-1 font-semibold">
              {executionHealth?.connected ? "已連線" : "未連線"}
            </div>
            <div className="mt-1 text-[11px] opacity-80">
              憑證 {executionHealth?.credentials_configured ? "已配置" : "未配置"}
            </div>
            <div className="mt-1 text-[11px] opacity-80">
              daily halt {guardrails?.daily_loss_halt ? "ON" : "off"} · failure halt {guardrails?.failure_halt ? "ON" : "off"}
            </div>
          </div>
          <div className="rounded-lg border border-white/10 bg-slate-950/20 p-3">
            <div className="text-[11px] opacity-70">Guardrails</div>
            <div className="mt-1 font-semibold">
              日損 {guardrails?.daily_loss_ratio != null ? `${(guardrails.daily_loss_ratio * 100).toFixed(2)}%` : "—"}
            </div>
            <div className="mt-1 text-[11px] opacity-80">
              上限 {guardrails?.max_daily_loss_pct != null ? `${(guardrails.max_daily_loss_pct * 100).toFixed(1)}%` : "—"}
            </div>
            <div className="mt-1 text-[11px] opacity-80">
              連續失敗 {guardrails?.consecutive_failures ?? 0}/{guardrails?.max_consecutive_failures ?? 0}
            </div>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-3">
          <div className="rounded-lg border border-white/10 bg-slate-950/20 p-3">
            <div className="text-[11px] opacity-70">最近拒單</div>
            <div className="mt-1 font-semibold">{lastReject?.code || "—"}</div>
            <div className="mt-1 text-[11px] opacity-80">{lastReject?.message || "尚無拒單紀錄"}</div>
            <div className="mt-2 text-[11px] opacity-70">
              {lastReject?.timestamp ? new Date(lastReject.timestamp).toLocaleString("zh-TW") : "尚未收到 reject timestamp"}
            </div>
          </div>
          <div className="rounded-lg border border-white/10 bg-slate-950/20 p-3">
            <div className="text-[11px] opacity-70">最近失敗</div>
            <div className="mt-1 font-semibold">{lastFailure?.timestamp ? new Date(lastFailure.timestamp).toLocaleString("zh-TW") : "—"}</div>
            <div className="mt-1 text-[11px] opacity-80">{lastFailure?.message || "尚無執行失敗"}</div>
          </div>
          <div className="rounded-lg border border-white/10 bg-slate-950/20 p-3">
            <div className="text-[11px] opacity-70">最近委託</div>
            <div className="mt-1 font-semibold">{lastOrder?.symbol || "—"}</div>
            <div className="mt-1 text-[11px] opacity-80">{lastOrder ? `${lastOrder.side} · qty ${lastOrder.qty} · ${lastOrder.status}` : "尚無委託"}</div>
            {lastOrder?.normalization && (
              <div className="mt-2 text-[11px] opacity-80 leading-5">
                normalized qty {formatGuardrailValue(lastOrder.normalization.normalized?.qty)}
                {lastOrder.normalization.normalized?.price != null ? ` · price ${formatGuardrailValue(lastOrder.normalization.normalized?.price)}` : ""}
                {lastOrder.normalization.contract?.step_size != null ? ` · step ${formatGuardrailValue(lastOrder.normalization.contract?.step_size)}` : ""}
                {lastOrder.normalization.contract?.tick_size != null ? ` · tick ${formatGuardrailValue(lastOrder.normalization.contract?.tick_size)}` : ""}
              </div>
            )}
            <div className="mt-2 text-[11px] opacity-70">
              {lastOrder?.timestamp ? new Date(lastOrder.timestamp).toLocaleString("zh-TW") : "尚未收到 order timestamp"}
            </div>
          </div>
        </div>
        {tradeFeedback && (
          <div className={`mt-3 rounded-lg border p-3 text-xs ${tradeFeedbackTone}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-semibold">手動交易即時回饋</div>
              <div className="text-[11px] opacity-80">{tradeFeedback.timestamp}</div>
            </div>
            <div className="mt-1 font-semibold">{tradeFeedback.title}</div>
            <div className="mt-1 leading-5 opacity-90">{tradeFeedback.detail}</div>
          </div>
        )}
        <div className="mt-3 rounded-lg border border-white/10 bg-slate-950/20 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="font-semibold">Metadata smoke 摘要</div>
            <div className="text-[11px] opacity-70">
              {metadataSmoke?.generated_at ? new Date(metadataSmoke.generated_at).toLocaleString("zh-TW") : "尚未產生 smoke artifact"}
            </div>
          </div>
          {metadataSmoke ? (
            <>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] opacity-85">
                <span>
                  {metadataSmoke.all_ok ? "public metadata contract 驗證通過" : "public metadata contract 尚未全通過"}
                  {metadataSmoke.ok_count != null && metadataSmoke.venues_checked != null ? ` · ${metadataSmoke.ok_count}/${metadataSmoke.venues_checked}` : ""}
                  {metadataSmoke.symbol ? ` · ${metadataSmoke.symbol}` : ""}
                </span>
                <span className={`rounded-full border px-2 py-0.5 font-semibold tracking-wide ${metadataSmokeFreshnessTone}`}>
                  smoke freshness {metadataSmokeFreshnessLabel}
                </span>
              </div>
              <div className="mt-2 text-[11px] opacity-75">
                {metadataSmokeFreshness?.age_minutes != null
                  ? `artifact age ${metadataSmokeFreshness.age_minutes.toFixed(1)}m · stale after ${formatGuardrailValue(metadataSmokeFreshness.stale_after_minutes, 1)}m`
                  : "artifact age unavailable · stale/unavailable policy 已啟用"}
              </div>
              <div className={`mt-3 rounded-lg border p-3 text-[11px] leading-5 ${metadataSmokeGovernanceTone}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-semibold">stale governance</div>
                  <div className="opacity-80">{metadataSmokeGovernance?.status || "unknown"}</div>
                </div>
                <div className="mt-2 opacity-90">{metadataSmokeGovernance?.operator_message || "尚未收到治理訊息"}</div>
                {metadataSmokeAutoRefresh?.status && (
                  <div className="mt-2 opacity-85">
                    auto refresh {metadataSmokeAutoRefresh.status}
                    {metadataSmokeAutoRefresh.completed_at ? ` · completed ${new Date(metadataSmokeAutoRefresh.completed_at).toLocaleString("zh-TW")}` : ""}
                    {metadataSmokeAutoRefresh.next_retry_at ? ` · next retry ${new Date(metadataSmokeAutoRefresh.next_retry_at).toLocaleString("zh-TW")}` : ""}
                  </div>
                )}
                {metadataSmokeBackgroundMonitor?.status && (
                  <div className="mt-2 opacity-85">
                    background monitor {metadataSmokeBackgroundMonitor.status}
                    {metadataSmokeBackgroundMonitor.checked_at ? ` · checked ${new Date(metadataSmokeBackgroundMonitor.checked_at).toLocaleString("zh-TW")}` : ""}
                    {metadataSmokeBackgroundMonitor.freshness_status ? ` · freshness ${metadataSmokeBackgroundMonitor.freshness_status}` : ""}
                    {metadataSmokeBackgroundMonitor.interval_seconds != null ? ` · every ${metadataSmokeBackgroundMonitor.interval_seconds}s` : ""}
                  </div>
                )}
                {metadataSmokeExternalMonitor?.status && (
                  <div className="mt-2 opacity-85">
                    external monitor {metadataSmokeExternalMonitor.status}
                    {metadataSmokeExternalMonitor.checked_at ? ` · checked ${new Date(metadataSmokeExternalMonitor.checked_at).toLocaleString("zh-TW")}` : ""}
                    {metadataSmokeExternalMonitor.freshness?.status ? ` · freshness ${metadataSmokeExternalMonitor.freshness.status}` : ""}
                    {metadataSmokeExternalMonitor.interval_seconds != null ? ` · every ${metadataSmokeExternalMonitor.interval_seconds}s` : ""}
                  </div>
                )}
                {metadataSmokeGovernance?.refresh_command && (
                  <div className="mt-2 font-mono opacity-85 break-all">refresh command: {metadataSmokeGovernance.refresh_command}</div>
                )}
                {metadataSmokeGovernance?.escalation_message && (
                  <div className="mt-2 opacity-90">escalation: {metadataSmokeGovernance.escalation_message}</div>
                )}
                {metadataSmokeAutoRefresh?.error && (
                  <div className="mt-2 text-red-200">auto refresh error: {metadataSmokeAutoRefresh.error}</div>
                )}
                {metadataSmokeExternalMonitor?.command && (
                  <div className="mt-2 font-mono opacity-85 break-all">external monitor command: {metadataSmokeExternalMonitor.command}</div>
                )}
                {externalMonitorInstallContract?.preferred_host_lane && (
                  <div className="mt-2 opacity-85">
                    preferred host lane: {externalMonitorInstallContract.preferred_host_lane}
                    {externalMonitorInstallContract.user_crontab?.schedule ? ` · schedule ${externalMonitorInstallContract.user_crontab.schedule}` : ""}
                  </div>
                )}
                {externalMonitorInstallContract?.user_crontab?.install_command && (
                  <div className="mt-2 font-mono opacity-85 break-all">install command: {externalMonitorInstallContract.user_crontab.install_command}</div>
                )}
                {externalMonitorInstallContract?.user_crontab?.verify_command && (
                  <div className="mt-2 font-mono opacity-85 break-all">install verify: {externalMonitorInstallContract.user_crontab.verify_command}</div>
                )}
                {externalMonitorInstallContract?.fallback?.reason && (
                  <div className="mt-2 opacity-90">fallback contract: {externalMonitorInstallContract.fallback.reason}</div>
                )}
                {externalMonitorInstallContract?.fallback?.command && (
                  <div className="mt-2 font-mono opacity-85 break-all">fallback command: {externalMonitorInstallContract.fallback.command}</div>
                )}
                {externalMonitorInstallContract?.systemd_user?.timer_file && (
                  <div className="mt-2 opacity-80">systemd user timer: {externalMonitorInstallContract.systemd_user.timer_file}</div>
                )}
                {metadataSmokeExternalMonitor?.error && (
                  <div className="mt-2 text-red-200">external monitor error: {metadataSmokeExternalMonitor.error}</div>
                )}
              </div>
              <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
                {(metadataSmoke.venues || []).map((item) => (
                  <div key={item.venue || "unknown"} className="rounded-lg border border-white/10 bg-slate-950/30 p-3 text-[11px] leading-5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="font-semibold">{item.venue || "unknown"}</div>
                      <div className={item.ok ? "text-emerald-300" : "text-red-300"}>{item.ok ? "OK" : "FAIL"}</div>
                    </div>
                    <div className="mt-1 opacity-85">
                      step {formatGuardrailValue(item.contract?.step_size)} · tick {formatGuardrailValue(item.contract?.tick_size)}
                    </div>
                    <div className="mt-1 opacity-85">
                      min qty {formatGuardrailValue(item.contract?.min_qty)} · min cost {formatGuardrailValue(item.contract?.min_cost)}
                    </div>
                    <div className="mt-1 opacity-70">
                      config {item.enabled_in_config ? "enabled" : "disabled"} · creds {item.credentials_configured ? "configured" : "public-only"}
                    </div>
                    {item.error && <div className="mt-1 text-red-200">{item.error}</div>}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="mt-2 text-[11px] opacity-80">/api/status 尚未提供 metadata smoke 摘要。</div>
          )}
        </div>
        <div className="mt-3 rounded-lg border border-white/10 bg-slate-950/20 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="font-semibold">Guardrail context 面板</div>
            <div className="text-[11px] opacity-70">raw → adjusted → delta → rules</div>
          </div>
          {lastRejectContext ? (
            <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
              <div className="rounded-lg border border-white/10 bg-slate-950/30 p-3">
                <div className="text-[11px] opacity-70">欄位 / 合約</div>
                <div className="mt-1 font-semibold">{lastRejectContext.field || "—"}</div>
                <div className="mt-2 text-[11px] opacity-85">原始值 {formatGuardrailValue(lastRejectContext.raw_value)}</div>
                <div className="mt-1 text-[11px] opacity-85">合法值 {formatGuardrailValue(lastRejectContext.adjusted_value)}</div>
                <div className="mt-1 text-[11px] opacity-85">差額 {formatGuardrailValue(lastRejectContext.delta)}</div>
                <div className="mt-1 text-[11px] opacity-85">step / tick {formatGuardrailValue(lastRejectContext.step_size)}</div>
                <div className="mt-1 text-[11px] opacity-85">precision {formatGuardrailValue(lastRejectContext.precision, 0)}</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-slate-950/30 p-3">
                <div className="text-[11px] opacity-70">規則來源</div>
                {lastRejectRuleLines.length > 0 ? (
                  <div className="mt-2 space-y-1 text-[11px] opacity-90">
                    {lastRejectRuleLines.map((line) => (
                      <div key={line}>• {line}</div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-2 text-[11px] opacity-80">尚無可讀 rules；請檢查 API payload。</div>
                )}
              </div>
            </div>
          ) : (
            <div className="mt-2 text-[11px] opacity-80">目前沒有最近 reject context；一旦 pre-trade guardrail 擋單，這裡會直接顯示可調整的 qty / price 規則。</div>
          )}
        </div>
      </div>

      <div className={`rounded-xl border px-4 py-3 text-xs ${continuityTone}`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="font-semibold">🩹 啟動檢查 / continuity</div>
          <div className="text-[11px] opacity-80">
            {rawContinuity?.checked_at ? `檢查時間 ${new Date(rawContinuity.checked_at).toLocaleString("zh-TW")}` : "等待啟動檢查結果"}
          </div>
        </div>
        <div className="mt-1 leading-5">{continuityLabel}</div>
        {rawContinuity?.continuity_repair && (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] opacity-90">
            <span>總補回 {rawContinuity.continuity_repair.inserted_total ?? 0}</span>
            <span>4h {rawContinuity.continuity_repair.coarse_inserted ?? 0}</span>
            <span>1h {rawContinuity.continuity_repair.fine_inserted ?? 0}</span>
            <span>bridge {rawContinuity.continuity_repair.bridge_inserted ?? 0}</span>
            {rawContinuity.continuity_repair.used_bridge && <span className="text-amber-300">⚠️ 依賴 bridge fallback</span>}
          </div>
        )}
        {featureContinuity?.continuity_repair && (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] opacity-90">
            <span>feature 狀態 {featureContinuity.status ?? "unknown"}</span>
            <span>補回 {featureContinuity.continuity_repair.inserted_total ?? 0}</span>
            <span>remaining missing {featureContinuity.continuity_repair.remaining_missing ?? 0}</span>
          </div>
        )}
        {rawContinuity?.error && (
          <div className="mt-2 text-[11px] text-red-200">錯誤：{rawContinuity.error}</div>
        )}
        {featureContinuity?.error && (
          <div className="mt-2 text-[11px] text-red-200">Feature 錯誤：{featureContinuity.error}</div>
        )}
      </div>

      {/* Row 1: Radar + Advice */}
      <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-4 items-stretch">
        {/* Left: Radar */}
        <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-5 flex h-full flex-col items-center">
          <div className="flex items-center justify-between w-full mb-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-300">🎯 多特徵雷達圖</h2>
              <div className="text-xs text-slate-500 mt-1">已改用市場語義短標籤，避免舊人格化命名與文字重疊。</div>
              {maturitySummary && (
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] font-semibold">
                  <span className="rounded-full border border-emerald-700/40 bg-emerald-950/40 px-2 py-0.5 text-emerald-300">
                    核心 {maturitySummary.core}
                  </span>
                  <span className="rounded-full border border-sky-700/40 bg-sky-950/40 px-2 py-0.5 text-sky-300">
                    研究 {maturitySummary.research}
                  </span>
                  <span className="rounded-full border border-amber-700/40 bg-amber-950/30 px-2 py-0.5 text-amber-300">
                    阻塞 {maturitySummary.blocked}
                  </span>
                  <span className="text-slate-500">
                    雷達保留研究/阻塞 overlay 供觀察；主決策請搭配下方建議卡與 FeatureChart 成熟度資訊。
                  </span>
                </div>
              )}
            </div>
            <span className="text-xs text-slate-500 cursor-pointer hover:text-slate-300"
              onClick={() => setSelectedSense(null)}>
              點擊特徵看走勢
            </span>
          </div>
          {isDataStale ? (
            <div className="py-12 text-center text-slate-500">
              <div className="animate-pulse mb-2">🔄 等待資料...</div>
              <div className="text-xs text-slate-600">確認後端有啟動</div>
              <button onClick={refreshSenses} className="mt-3 px-3 py-1 text-xs bg-blue-600 rounded hover:bg-blue-500">
                手動刷新
              </button>
            </div>
          ) : (
            <RadarChart scores={scores} size={380} onSenseClick={setSelectedSense} />
          )}
        </div>

        {/* Right: Advice Card */}
        <div className="h-full">
          {advice ? (
            <div className="h-full">
              <AdviceCard
                score={advice.score}
                summary={advice.summary}
                descriptions={advice.descriptions}
                action={advice.action}
                timestamp={advice.timestamp || lastUpdate}
                onTrade={handleTrade}
                maturitySummary={maturitySummary || undefined}
              />
            </div>
          ) : apiError ? (
            <div className="bg-red-900/20 border border-red-700/50 rounded-xl p-8 text-center h-full min-h-[420px] flex flex-col items-center justify-center">
              <div className="text-red-400 text-lg mb-2">⚠️ 無法連線</div>
              <p className="text-slate-400 text-sm">{apiError}</p>
              <button onClick={refreshSenses} className="mt-4 px-4 py-2 text-sm bg-red-600 rounded hover:bg-red-500">
                重試
              </button>
            </div>
          ) : (
            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-8 flex h-full min-h-[420px] items-center justify-center">
              <div className="text-slate-500 animate-pulse text-center">
                <div className="text-2xl mb-2">🤔</div>
                <div>分析中...</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Row 1.5: Confidence Indicator */}
      {confidenceData && !confidenceData.error && (
        <ConfidenceIndicator
          confidence={confidenceData.confidence}
          signal={confidenceData.signal}
          confidenceLevel={confidenceData.confidence_level}
          shouldTrade={confidenceData.should_trade}
          regimeGate={confidenceData.regime_gate}
          entryQuality={confidenceData.entry_quality}
          entryQualityLabel={confidenceData.entry_quality_label}
          allowedLayers={confidenceData.allowed_layers}
          decisionQualityScore={confidenceData.decision_quality_score}
          decisionQualityLabel={confidenceData.decision_quality_label}
          expectedWinRate={confidenceData.expected_win_rate}
          expectedPyramidQuality={confidenceData.expected_pyramid_quality}
          expectedDrawdownPenalty={confidenceData.expected_drawdown_penalty}
          expectedTimeUnderwater={confidenceData.expected_time_underwater}
          decisionQualitySampleSize={confidenceData.decision_quality_sample_size}
          decisionQualityHorizonMinutes={confidenceData.decision_quality_horizon_minutes}
          decisionProfileVersion={confidenceData.decision_profile_version}
          timestamp={confidenceData.timestamp}
        />
      )}

      {/* ─── 4H Structure Panel ─── */}
      {sensesData?.raw && Object.keys(sensesData.raw).length > 0 && (() => {
        const raw = sensesData.raw as Record<string, number>;
        const bias50 = raw['4h_bias50'] ?? null;
        const bias20 = raw['4h_bias20'] ?? null;
        const rsi14 = raw['4h_rsi14'] ?? null;
        const macd = raw['4h_macd_hist'] ?? null;
        const swingDist = raw['4h_dist_sl'] ?? null;
        const maOrder = raw['4h_ma_order'] ?? 0;

        // 牛市/熊市判斷
        const regime = bias50 !== null ? (bias50 >= 0 ? 'bull' : 'bear') : 'unknown';
        const regimeLabel = regime === 'bull' ? '🟢 牛市格局' : '🔴 熊市格局';
        const regimeColor = regime === 'bull' ? 'text-green-400' : 'text-red-400';

        // 判斷: 靠近支撐? 靠近壓力?
        let zone = '觀望';
        let zoneColor = 'text-slate-400';
        if (bias50 !== null) {
          if (bias50 <= -5) { zone = '極端超賣'; zoneColor = 'text-green-400'; }
          else if (bias50 <= -3) { zone = '超賣區'; zoneColor = 'text-green-400'; }
          else if (bias50 <= -1) { zone = '回調區'; zoneColor = 'text-yellow-400'; }
          else if (bias50 >= 5) { zone = '極端超買'; zoneColor = 'text-red-400'; }
          else if (bias50 >= 3) { zone = '超買區'; zoneColor = 'text-red-400'; }
          else if (bias50 >= 0) { zone = '正常偏強'; zoneColor = 'text-slate-300'; }
          else { zone = '正常偏弱'; zoneColor = 'text-slate-300'; }
        }

        // Context-only structural note. Canonical trade action must come from the
        // live decision-quality contract (regime_gate + entry_quality + allowed_layers).
        let contextAction = '';
        if (regime === 'bull' && bias50! <= -3) contextAction = '背景偏多，價格接近支撐。';
        else if (regime === 'bull' && bias50! <= -1) contextAction = '背景偏多，正在回調區。';
        else if (regime === 'bull' && bias50! >= 5) contextAction = '背景偏熱，已進入超買帶。';
        else if (regime === 'bull') contextAction = '背景偏多，但仍需等 live gate / quality 確認。';
        else contextAction = '背景偏保守，先觀察 4H 結構是否改善。';

        const canonicalGate = confidenceData?.regime_gate || '—';
        const canonicalEntryQuality = typeof confidenceData?.entry_quality === 'number'
          ? confidenceData.entry_quality.toFixed(2)
          : '—';
        const canonicalEntryLabel = confidenceData?.entry_quality_label || '—';
        const canonicalLayers = typeof confidenceData?.allowed_layers === 'number'
          ? `${confidenceData.allowed_layers.toFixed(0)} / 3`
          : '—';
        const canonicalDecisionText = confidenceData
          ? `主決策：4H Gate ${canonicalGate} · Entry ${canonicalEntryQuality} (${canonicalEntryLabel}) · Layers ${canonicalLayers}`
          : '主決策：等待 live decision-quality contract 載入';

        return (
        <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-5">
          <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
            <div>
              <h2 className="text-sm font-semibold text-slate-300">📐 4H 結構線儀表板</h2>
              <div className="mt-1 text-[11px] text-slate-500">主決策以 live decision-quality contract 為準；以下 4H 指標僅作背景解讀。</div>
            </div>
            <span className={`text-xs font-bold ${regimeColor} px-2 py-0.5 rounded bg-slate-800`}>{regimeLabel}</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
            <div className="bg-slate-800/50 rounded-lg p-3">
              <div className="text-xs text-slate-500 mb-1">偏離 MA50</div>
              <div className={`text-xl font-bold ${bias50! <= -3 ? 'text-green-400' : bias50! >= 3 ? 'text-red-400' : 'text-slate-200'}`}>
                {bias50 !== null ? `${bias50 > 0 ? '+' : ''}${bias50.toFixed(2)}%` : '—'}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3">
              <div className="text-xs text-slate-500 mb-1">距離支撐線</div>
              <div className={`text-xl font-bold ${swingDist! < 3 && swingDist! >= 0 ? 'text-green-400' : 'text-slate-200'}`}>
                {swingDist !== null ? `${swingDist > 0 ? '+' : ''}${swingDist.toFixed(2)}%` : '—'}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3">
              <div className="text-xs text-slate-500 mb-1">4H RSI</div>
              <div className={`text-xl font-bold ${rsi14! < 30 ? 'text-green-400' : rsi14! > 70 ? 'text-red-400' : 'text-slate-200'}`}>
                {rsi14 !== null ? rsi14.toFixed(1) : '—'}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3">
              <div className="text-xs text-slate-500 mb-1">位置</div>
              <div className={`text-xl font-bold ${zoneColor}`}>{zone}</div>
            </div>
          </div>

          {/* Secondary metrics */}
          <div className="grid grid-cols-3 gap-3 text-xs text-slate-400 mb-3">
            <div>偏離 MA20: <span className="text-slate-200">{bias20 !== null ? `${bias20 > 0 ? '+' : ''}${bias20.toFixed(2)}%` : '—'}</span></div>
            <div>MACD-H: <span className={macd! > 0 ? 'text-green-400' : 'text-red-400'}>{macd !== null ? macd.toFixed(1) : '—'}</span></div>
            <div>MA排列: <span className={maOrder > 0 ? 'text-green-400' : maOrder < 0 ? 'text-red-400' : 'text-slate-400'}>
              {maOrder > 0.5 ? '📈 多頭' : maOrder < -0.5 ? '📉 空頭' : '📊 盤整'}
            </span></div>
          </div>

          {/* Canonical decision contract first; raw 4H metrics are context only. */}
          <div className="space-y-2">
            <div className="bg-cyan-950/20 rounded-lg px-4 py-3 text-sm text-cyan-100 border border-cyan-700/30">
              <div className="font-semibold">{canonicalDecisionText}</div>
              <div className="mt-1 text-xs text-cyan-200/80">
                若 4H raw 結構與 canonical gate 不一致，應以 decision-quality contract 為主，而不是手寫 bias 規則。
              </div>
            </div>
            <div className="bg-slate-800/30 rounded-lg px-4 py-2 text-sm text-slate-300 border border-slate-700/30">
              <div className="font-medium text-slate-200">結構背景</div>
              <div className="mt-1">{contextAction}</div>
            </div>
          </div>
        </div>
        );
      })()}

      {/* Row 2: TradingView-style BTC/USDT + composite score */}
      <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-slate-300">📈 BTC/USDT × 綜合分數走勢</div>
            <div className="mt-1 text-xs text-slate-500">主圖只保留價格與綜合分數，讓使用者用 TradingView 風格直接對照市場與策略強弱。</div>
          </div>
          <div className="flex items-center gap-2">
            {[
              { label: "4H", iv: "4h", d: 14 },
              { label: "1D", iv: "1d", d: 90 },
            ].map((opt) => (
              <button
                key={opt.iv}
                onClick={() => { setInterval(opt.iv); setDays(opt.d); }}
                className={`px-3 py-1 text-xs rounded-lg transition ${interval === opt.iv ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}
              >
                {opt.label}
              </button>
            ))}
            <button
              onClick={() => setShowFeatureHistory((prev) => !prev)}
              className={`px-3 py-1 text-xs rounded-lg transition ${showFeatureHistory ? "bg-cyan-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}
            >
              {showFeatureHistory ? "隱藏多特徵" : "顯示多特徵"}
            </button>
          </div>
        </div>
        <CandlestickChart
          symbol="BTCUSDT"
          interval={interval}
          days={days}
          scoreSeries={dashboardScoreSeries}
          title="BTC/USDT（綜合分數指標）"
        />
      </div>

      {showFeatureHistory && (
        <FeatureChart selectedFeature={selectedSense} days={days} onClear={() => setSelectedSense(null)} />
      )}
    </div>
  );
}
