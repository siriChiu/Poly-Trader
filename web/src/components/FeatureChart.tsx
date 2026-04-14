/**
 * FeatureChart — 價格 × 多特徵歷史走勢圖（Recharts）
 *
 * Props:
 *   selectedFeature?  當設置時，自動高亮該特徵線
 *   days?           資料天數（預設 7）
 */
import React, { useEffect, useState, useMemo, useRef, useCallback } from "react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
  Scatter,
  Legend,
  AreaChart,
} from "recharts";
import { fetchApi } from "../hooks/useApi";
import { useGlobalProgressTask } from "../hooks/useGlobalProgress";
import { ALL_SENSES, FEATURE_GROUPS, getSenseConfig, type FeatureGroupKey } from "../config/senses";

// ─── Types ───

interface Props {
  selectedFeature?: string | null;
  onClear?: () => void;
  days?: number;
}

interface FeatureRow {
  timestamp: string;
  [key: string]: string | number | null | undefined;
}

interface KlineCandle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface KlineResponse {
  candles: KlineCandle[];
  incremental?: boolean;
  append_after?: number;
}

interface FeatureCoverageMeta {
  db_key: string;
  non_null: number;
  coverage_pct: number;
  distinct: number;
  min?: number | null;
  max?: number | null;
  chart_usable: boolean;
  score_usable?: boolean;
  maturity_tier?: "core" | "research" | "blocked";
  maturity_label?: string;
  reasons: string[];
  quality_flag?: string;
  quality_label?: string;
  expected_min_coverage?: number;
  expected_min_distinct?: number;
  history_class?: string;
  backfill_status?: string;
  backfill_blocker?: string | null;
  recommended_action?: string | null;
  raw_snapshot_events?: number;
  raw_snapshot_latest_ts?: string | null;
  raw_snapshot_oldest_ts?: string | null;
  raw_snapshot_span_hours?: number | null;
  raw_snapshot_latest_age_min?: number | null;
  raw_snapshot_latest_status?: string | null;
  raw_snapshot_latest_message?: string | null;
  forward_archive_started?: boolean;
  forward_archive_ready?: boolean;
  forward_archive_stale?: boolean;
  forward_archive_status?: string;
  forward_archive_ready_min_events?: number;
  forward_archive_stale_after_min?: number;
  forward_archive_progress_pct?: number;
  archive_window_started?: boolean;
  archive_window_start_ts?: string | null;
  archive_window_rows?: number;
  archive_window_non_null?: number;
  archive_window_coverage_pct?: number | null;
}

function formatCoverageReason(meta?: FeatureCoverageMeta | null): string {
  if (!meta) return "";
  const qualityText = meta.quality_label && meta.quality_label !== "ok"
    ? meta.quality_label
    : (meta.reasons?.join(", ") || "chart hidden");
  const archiveText = meta.raw_snapshot_events
    ? ` · archive ${meta.raw_snapshot_events}/${meta.forward_archive_ready_min_events ?? 10} ${meta.forward_archive_status ?? "building"}`
    : "";
  const freshnessText = meta.raw_snapshot_events && meta.raw_snapshot_latest_age_min !== undefined && meta.raw_snapshot_latest_age_min !== null
    ? ` · last ${meta.raw_snapshot_latest_age_min.toFixed(1)}m · span ${meta.raw_snapshot_span_hours ?? 0}h`
    : "";
  const archiveWindowText = meta.archive_window_started
    ? ` · archive-window ${meta.archive_window_coverage_pct?.toFixed(1) ?? "0.0"}% (${meta.archive_window_non_null ?? 0}/${meta.archive_window_rows ?? 0})`
    : "";
  const statusText = meta.raw_snapshot_latest_status && meta.raw_snapshot_latest_status !== "ok"
    ? ` · latest ${meta.raw_snapshot_latest_status}${meta.raw_snapshot_latest_message ? ` (${meta.raw_snapshot_latest_message})` : ""}`
    : "";
  const blockerText = meta.backfill_blocker ? ` · blocker: ${meta.backfill_blocker}` : "";
  return `${qualityText} · coverage ${meta.coverage_pct.toFixed(1)}% · distinct ${meta.distinct}${archiveText}${freshnessText}${archiveWindowText}${statusText}${blockerText}`;
}

function summarizeCoverageChip(meta?: FeatureCoverageMeta | null): string {
  if (!meta) return "coverage不足";
  if (meta.quality_flag === "source_auth_blocked") {
    return "來源授權缺失";
  }
  if (meta.quality_flag === "source_fetch_error") {
    return "來源抓取失敗";
  }
  if (meta.quality_flag === "source_history_gap" && meta.history_class) {
    if (meta.raw_snapshot_events) {
      const archiveWindow = meta.archive_window_started
        ? ` · 最近窗${meta.archive_window_coverage_pct?.toFixed(0) ?? "0"}%`
        : "";
      return `來源歷史不足 · ${meta.coverage_pct.toFixed(0)}%${archiveWindow}`;
    }
    return `來源歷史不足 · ${meta.coverage_pct.toFixed(0)}%`;
  }
  if (meta.quality_flag === "source_fallback_zero") {
    return "來源 fallback 污染";
  }
  return `${meta.coverage_pct.toFixed(0)}% / d${meta.distinct}`;
}

function maturityBadge(meta?: FeatureCoverageMeta | null) {
  const tier = meta?.maturity_tier ?? "blocked";
  if (tier === "core") {
    return { label: "核心", className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" };
  }
  if (tier === "research") {
    return { label: "研究", className: "border-sky-500/30 bg-sky-500/10 text-sky-300" };
  }
  return { label: "阻塞", className: "border-amber-500/30 bg-amber-500/10 text-amber-300" };
}

interface MergedPoint {
  time: number;
  label: string;
  price: number;
  score: number | null;
  entrySignal: number | null;
  reduceSignal: number | null;
  [key: string]: string | number | null | undefined;
}

// ─── Constants ───

const FEATURE_ORDER = Object.keys(ALL_SENSES).filter((key) => {
  const meta = getSenseConfig(key);
  return ["microstructure", "technical", "macro", "structure4h"].includes(meta.category);
});

const FEATURE_CONFIG: Record<string, { label: string; color: string; key: keyof MergedPoint; category: FeatureGroupKey }> =
  Object.fromEntries(
    FEATURE_ORDER.map((key) => {
      const meta = getSenseConfig(key);
      return [key, { label: meta.name, color: meta.color, key: key as keyof MergedPoint, category: meta.category }];
    })
  );

const GROUP_AVERAGE_CONFIG: Record<FeatureGroupKey, { key: keyof MergedPoint; label: string; color: string }> = {
  microstructure: { key: "avg_microstructure", label: "市場微結構平均", color: "#38bdf8" },
  technical: { key: "avg_technical", label: "技術指標平均", color: "#facc15" },
  macro: { key: "avg_macro", label: "宏觀風險平均", color: "#34d399" },
  structure4h: { key: "avg_structure4h", label: "4H 結構平均", color: "#fb7185" },
};

function lineTypeForFeature(key: string): "monotone" | "stepAfter" {
  return key === "4h_ma_order" ? "stepAfter" : "monotone";
}

const TIMEFRAMES = [
  { label: "1D", days: 1 },
  { label: "7D", days: 7 },
  { label: "30D", days: 30 },
];

const FEATURE_CHART_KLINE_CACHE_KEY_PREFIX = "polytrader.featurechart.klines.v1";
const FEATURE_CHART_KLINE_MEMORY_CACHE = new Map<string, KlineResponse>();

// ─── Helpers ───

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  const month = (d.getMonth() + 1).toString().padStart(2, "0");
  const day = d.getDate().toString().padStart(2, "0");
  const hour = d.getHours().toString().padStart(2, "0");
  return `${month}/${day} ${hour}:00`;
}

function formatPrice(v: number): string {
  if (v >= 1000) return `$${(v / 1000).toFixed(1)}k`;
  return `$${v.toFixed(0)}`;
}

function loadCachedFeatureChartKlines(cacheKey: string): KlineResponse | null {
  if (FEATURE_CHART_KLINE_MEMORY_CACHE.has(cacheKey)) {
    return FEATURE_CHART_KLINE_MEMORY_CACHE.get(cacheKey) ?? null;
  }
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(`${FEATURE_CHART_KLINE_CACHE_KEY_PREFIX}:${cacheKey}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as KlineResponse;
    FEATURE_CHART_KLINE_MEMORY_CACHE.set(cacheKey, parsed);
    return parsed;
  } catch {
    return null;
  }
}

function saveCachedFeatureChartKlines(cacheKey: string, payload: KlineResponse) {
  FEATURE_CHART_KLINE_MEMORY_CACHE.set(cacheKey, payload);
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(`${FEATURE_CHART_KLINE_CACHE_KEY_PREFIX}:${cacheKey}`, JSON.stringify(payload));
  } catch {
    // ignore quota issues
  }
}

function mergeFeatureChartKlines(base: KlineResponse, incoming: KlineResponse): KlineResponse {
  const candleMap = new Map<number, KlineCandle>();
  for (const candle of base.candles || []) candleMap.set(candle.time, candle);
  for (const candle of incoming.candles || []) candleMap.set(candle.time, candle);
  return {
    candles: Array.from(candleMap.values()).sort((a, b) => a.time - b.time),
    incremental: false,
  };
}

/** Combine only core-score features into a recommendation score 0–100. */
function calcScore(point: Partial<MergedPoint>, scoreKeys: string[]): number | null {
  const vals = scoreKeys.map((k) => point[FEATURE_CONFIG[k].key]);
  const valid = vals.filter((v): v is number => v !== null && v !== undefined);
  if (valid.length === 0) return null;
  const avg = valid.reduce((a, b) => a + b, 0) / valid.length;
  return Math.round(Math.max(0, Math.min(100, avg * 100)));
}

/** Spot-long semantics: rising composite score -> entry zone, falling score -> reduce zone. */
function detectSignals(data: MergedPoint[]) {
  for (let i = 1; i < data.length; i++) {
    const prev = data[i - 1].score;
    const curr = data[i].score;
    if (prev === null || curr === null) continue;
    if (prev < 60 && curr >= 60) data[i].entrySignal = data[i].price;
    if (prev > 40 && curr <= 40) data[i].reduceSignal = data[i].price;
  }
}

// ─── Custom Legend ───

function CustomLegend({
  visibility,
  averageVisibility,
  coverage,
  onToggle,
  onToggleGroup,
  onToggleAverage,
}: {
  visibility: Record<string, boolean>;
  averageVisibility: Record<FeatureGroupKey, boolean>;
  coverage: Record<string, FeatureCoverageMeta>;
  onToggle: (key: string) => void;
  onToggleGroup: (group: FeatureGroupKey) => void;
  onToggleAverage: (group: FeatureGroupKey) => void;
}) {
  const groupedEntries = Object.entries(FEATURE_CONFIG).reduce((acc, [key, cfg]) => {
    const meta = coverage[key];
    if (meta && !meta.chart_usable) return acc;
    (acc[cfg.category] ||= []).push([key, cfg] as [string, typeof cfg]);
    return acc;
  }, {} as Record<FeatureGroupKey, Array<[string, (typeof FEATURE_CONFIG)[string]]>>);

  return (
    <div className="space-y-3 px-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="flex items-center gap-1 text-xs text-slate-300 bg-slate-800/60 px-2 py-1 rounded-md">
          <span className="w-3 h-0.5 bg-slate-300 inline-block" />
          價格
        </span>
        <span className="flex items-center gap-1 text-xs text-green-400 bg-slate-800/60 px-2 py-1 rounded-md">▲ 進場</span>
        <span className="flex items-center gap-1 text-xs text-orange-400 bg-slate-800/60 px-2 py-1 rounded-md">▼ 減碼</span>
      </div>

      {Object.entries(groupedEntries).map(([groupKey, items]) => (
        <div key={groupKey} className="rounded-lg border border-slate-800/70 bg-slate-900/40 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <div>
              <div className="text-xs font-semibold text-slate-300">{FEATURE_GROUPS[groupKey as FeatureGroupKey].label}</div>
              <div className="text-[11px] text-slate-500">{FEATURE_GROUPS[groupKey as FeatureGroupKey].description}</div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => onToggleAverage(groupKey as FeatureGroupKey)}
                className={`text-[11px] ${averageVisibility[groupKey as FeatureGroupKey] ? 'text-emerald-300' : 'text-emerald-500'} hover:text-emerald-300`}
              >
                {averageVisibility[groupKey as FeatureGroupKey] ? '隱藏平均線' : '只看平均線'}
              </button>
              <button
                onClick={() => onToggleGroup(groupKey as FeatureGroupKey)}
                className="text-[11px] text-blue-400 hover:text-blue-300"
              >
                切換整組
              </button>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {items.map(([key, cfg]) => {
              const active = visibility[key] ?? true;
              const meta = coverage[key];
              const disabled = meta ? !meta.chart_usable : false;
              const reason = formatCoverageReason(meta);
              const badge = maturityBadge(meta);
              return (
                <button
                  key={key}
                  onClick={() => !disabled && onToggle(key)}
                  disabled={disabled}
                  title={disabled ? `已隱藏：${reason}` : undefined}
                  className={`flex items-center gap-1 text-xs px-2 py-1 rounded-md transition-all ${
                    disabled
                      ? "bg-slate-900/40 text-slate-600 border border-slate-800/60 cursor-not-allowed"
                      : active
                        ? "bg-slate-700/80 text-white"
                        : "bg-slate-800/40 text-slate-500 line-through"
                  }`}
                  style={!disabled && active ? { borderColor: cfg.color, borderWidth: 1 } : undefined}
                >
                  <span className="w-3 h-0.5 inline-block" style={{ backgroundColor: !disabled && active ? cfg.color : "#475569" }} />
                  {cfg.label}
                  <span className={`rounded-full border px-1.5 py-0.5 text-[10px] ${badge.className}`}>
                    {badge.label}
                  </span>
                  {disabled && (
                    <span className="text-[10px] text-slate-500">
                      {summarizeCoverageChip(meta)}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Custom Tooltip ───

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null;
  const d: MergedPoint = payload[0]?.payload;
  if (!d) return null;

  return (
    <div className="bg-slate-800/95 border border-slate-600 rounded-lg px-3 py-2 text-xs shadow-xl backdrop-blur-sm">
      <div className="text-slate-300 mb-1 font-mono">{d.label}</div>
      <div className="text-white font-bold mb-1">
        價格：${d.price?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
        {Object.entries(FEATURE_CONFIG).map(([key, cfg]) => {
          const val = d[key as keyof MergedPoint] as number | null;
          return (
            <div key={key} style={{ color: cfg.color }}>
              {cfg.label}：{val !== null ? (val * 100).toFixed(0) : "—"}
            </div>
          );
        })}
      </div>
      {d.score !== null && (
        <div className="mt-1 pt-1 border-t border-slate-600 text-slate-200">
          綜合分數：<span className="font-bold">{d.score}</span>
        </div>
      )}
    </div>
  );
}

// ─── Entry/Reduce Custom Dot ───

function SignalDot(props: any) {
  const { cx, cy, payload } = props;
  if (!cx || !cy) return null;

  if (payload.entrySignal != null) {
    return (
      <g>
        <polygon
          points={`${cx},${cy - 8} ${cx - 6},${cy + 4} ${cx + 6},${cy + 4}`}
          fill="#22c55e"
          stroke="#0f172a"
          strokeWidth={1}
        />
      </g>
    );
  }
  if (payload.reduceSignal != null) {
    return (
      <g>
        <polygon
          points={`${cx},${cy + 8} ${cx - 6},${cy - 4} ${cx + 6},${cy - 4}`}
          fill="#f97316"
          stroke="#0f172a"
          strokeWidth={1}
        />
      </g>
    );
  }
  return null;
}

// ─── Score color helper ───

function scoreColor(score: number): string {
  if (score >= 70) return "#22c55e";
  if (score >= 50) return "#eab308";
  if (score >= 30) return "#f97316";
  return "#ef4444";
}

function calcGroupAverage(point: Partial<MergedPoint>, group: FeatureGroupKey): number | null {
  const keys = Object.entries(FEATURE_CONFIG)
    .filter(([, cfg]) => cfg.category === group)
    .map(([key]) => key);
  const vals = keys.map((k) => point[FEATURE_CONFIG[k].key]);
  const valid = vals.filter((v): v is number => v !== null && v !== undefined);
  if (!valid.length) return null;
  return valid.reduce((a, b) => a + b, 0) / valid.length;
}

// ─── Main Component ───

export default function FeatureChart({ selectedFeature, onClear, days: initialDays = 7 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [days, setDays] = useState(initialDays);
  const [loading, setLoading] = useState(true);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingDetail, setLoadingDetail] = useState("準備同步特徵、coverage 與 BTC/USDT 價格資料");
  const [error, setError] = useState<string | null>(null);
  const [merged, setMerged] = useState<MergedPoint[]>([]);
  const [visibility, setVisibility] = useState<Record<string, boolean>>(
    Object.fromEntries(Object.keys(FEATURE_CONFIG).map((k) => [k, true]))
  );
  const [averageVisibility, setAverageVisibility] = useState<Record<FeatureGroupKey, boolean>>({
    microstructure: false,
    technical: false,
    macro: false,
    structure4h: false,
  });
  const [featureCoverage, setFeatureCoverage] = useState<Record<string, FeatureCoverageMeta>>({});

  useGlobalProgressTask(loading, {
    label: "載入歷史特徵資料中",
    detail: loadingDetail,
    progress: loadingProgress,
    tone: "violet",
    priority: 45,
    kind: "manual",
  });

  const hiddenCoverageItems = useMemo(
    () => Object.entries(featureCoverage).filter(([, meta]) => !meta.chart_usable),
    [featureCoverage]
  );
  const scoreFeatureKeys = useMemo(
    () => FEATURE_ORDER.filter((key) => {
      const meta = featureCoverage[key];
      return meta ? meta.score_usable !== false : true;
    }),
    [featureCoverage]
  );
  const maturitySummary = useMemo(() => {
    const summary = { core: 0, research: 0, blocked: 0 };
    for (const meta of Object.values(featureCoverage)) {
      const tier = meta.maturity_tier ?? "blocked";
      if (tier === "core" || tier === "research" || tier === "blocked") {
        summary[tier] += 1;
      }
    }
    return summary;
  }, [featureCoverage]);

  const [_autoHighlight, setAutoHighlight] = useState(false);

  const normalizeSelectedFeature = useCallback((feature?: string | null) => {
    if (!feature) return null;
    if (feature in FEATURE_CONFIG) return feature;
    const stripped = feature.replace("feat_", "");
    return stripped in FEATURE_CONFIG ? stripped : null;
  }, []);

  // Auto-scroll into view when selectedFeature changes
  useEffect(() => {
    const normalized = normalizeSelectedFeature(selectedFeature);
    if (normalized && containerRef.current) {
      containerRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
      setVisibility(Object.fromEntries(Object.keys(FEATURE_CONFIG).map((k) => [k, k === normalized])));
      setAutoHighlight(true);
    }
  }, [selectedFeature, normalizeSelectedFeature]);

  // Fetch & merge data
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadingProgress(0);
    setLoadingDetail("準備同步特徵、coverage 與 BTC/USDT 價格資料");
    setError(null);

    async function load() {
      try {
        const interval = days <= 1 ? "15m" : days <= 7 ? "1h" : "4h";
        const limit = days <= 1 ? 96 : days <= 7 ? 168 : 180;
        const totalSteps = 6;
        let completedSteps = 0;
        const advance = (detail: string) => {
          completedSteps += 1;
          setLoadingProgress(Math.round((completedSteps / totalSteps) * 100));
          setLoadingDetail(detail);
        };

        const klineCacheKey = `BTCUSDT:${interval}:${limit}`;
        const cachedKlines = loadCachedFeatureChartKlines(klineCacheKey);
        const [features, coverageResp, initialKlines] = await Promise.all([
          fetchApi<FeatureRow[]>(`/api/features?days=${days}`),
          fetchApi<{ features: Record<string, FeatureCoverageMeta> }>(`/api/features/coverage?days=${Math.max(days, 30)}`),
          cachedKlines
            ? Promise.resolve(cachedKlines)
            : fetchApi<KlineResponse>(`/api/chart/klines?symbol=BTCUSDT&interval=${interval}&limit=${limit}`),
        ]);
        let klines = initialKlines;
        if (!cachedKlines) {
          saveCachedFeatureChartKlines(klineCacheKey, klines);
        }
        advance(`已取得 ${features.length} 筆特徵資料、${klines.candles.length} 根價格 K 線${cachedKlines ? "（本地快取）" : ""}`);

        if (cachedKlines && klines.candles.length > 0) {
          const lastCached = klines.candles[klines.candles.length - 1];
          setLoadingDetail("特徵與 coverage 已就緒，正在補抓 FeatureChart 缺少的最新 K 線");
          const delta = await fetchApi<KlineResponse>(
            `/api/chart/klines?symbol=BTCUSDT&interval=${interval}&limit=${limit}&append_after=${lastCached.time * 1000}`
          );
          if (delta.candles?.length) {
            klines = mergeFeatureChartKlines(klines, delta);
            saveCachedFeatureChartKlines(klineCacheKey, klines);
            advance(`FeatureChart 已從本地快取還原，並補上 ${delta.candles.length} 根新 K 線`);
          }
        }

        if (cancelled) return;

        const coverage = coverageResp?.features ?? {};
        setFeatureCoverage(coverage);

        const sortedFeatures = [...features]
          .map((row) => ({ ...row, _ts: new Date(String(row.timestamp)).getTime() }))
          .sort((a, b) => (a._ts as number) - (b._ts as number));
        let featureIndex = 0;

        const points: MergedPoint[] = klines.candles.map((c) => {
          const candleTs = c.time * 1000;
          while (
            featureIndex + 1 < sortedFeatures.length &&
            (sortedFeatures[featureIndex + 1]._ts as number) <= candleTs
          ) {
            featureIndex += 1;
          }

          let feat: FeatureRow | undefined = sortedFeatures[featureIndex];
          if (!feat || Math.abs(((feat as any)._ts as number) - candleTs) > 48 * 3600 * 1000) {
            feat = undefined;
          }

          const dynamicValues = Object.fromEntries(
            FEATURE_ORDER.map((featureKey) => {
              const coverageMeta = coverage[featureKey];
              if (coverageMeta && !coverageMeta.chart_usable) {
                return [featureKey, null];
              }
              const raw = feat?.[featureKey];
              return [featureKey, typeof raw === "number" ? raw : raw == null ? null : Number(raw)];
            })
          );

          const averageValues = Object.fromEntries(
            (Object.keys(GROUP_AVERAGE_CONFIG) as FeatureGroupKey[]).map((groupKey) => [
              GROUP_AVERAGE_CONFIG[groupKey].key,
              calcGroupAverage(dynamicValues as Partial<MergedPoint>, groupKey),
            ])
          );

          return {
            time: c.time,
            label: formatTime(c.time),
            price: c.close,
            ...dynamicValues,
            ...averageValues,
            score: null,
            entrySignal: null,
            reduceSignal: null,
          };
        });

        const scoreKeys = FEATURE_ORDER.filter((featureKey) => {
          const coverageMeta = coverage[featureKey];
          return coverageMeta ? coverageMeta.score_usable !== false : true;
        });

        // Calculate scores and detect signals using core decision signals only.
        for (const p of points) {
          p.score = calcScore(p, scoreKeys);
        }
        detectSignals(points);

        if (!cancelled) {
          setMerged(points);
          setLoading(false);
        }
      } catch (e: any) {
        if (!cancelled) {
          setError(e.message || "載入失敗");
          setLoading(false);
        }
      }
    }

    load();
  }, [days]);

  useEffect(() => {
    const disabledKeys = Object.entries(featureCoverage)
      .filter(([, meta]) => !meta.chart_usable)
      .map(([key]) => key);
    if (!disabledKeys.length) return;
    setVisibility((prev) => {
      const next = { ...prev };
      for (const key of disabledKeys) next[key] = false;
      return next;
    });
  }, [featureCoverage]);

  const toggleVisibility = useCallback((key: string) => {
    if (featureCoverage[key] && !featureCoverage[key].chart_usable) return;
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  }, [featureCoverage]);

  const toggleGroupVisibility = useCallback((group: FeatureGroupKey) => {
    const keys = Object.entries(FEATURE_CONFIG)
      .filter(([, cfg]) => cfg.category === group)
      .map(([key]) => key)
      .filter((key) => !featureCoverage[key] || featureCoverage[key].chart_usable);
    setVisibility((prev) => {
      const shouldEnable = keys.some((key) => !prev[key]);
      const next = { ...prev };
      for (const key of keys) next[key] = shouldEnable;
      return next;
    });
  }, [featureCoverage]);

  const toggleAverageVisibility = useCallback((group: FeatureGroupKey) => {
    setAverageVisibility((prev) => ({ ...prev, [group]: !prev[group] }));
  }, []);

  // Price domain
  const priceDomain = useMemo(() => {
    if (!merged.length) return [0, 100000] as [number, number];
    const prices = merged.map((d) => d.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const pad = (max - min) * 0.05;
    return [Math.floor(min - pad), Math.ceil(max + pad)] as [number, number];
  }, [merged]);

  return (
    <div
      ref={containerRef}
      className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4 space-y-3"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h2 className="text-sm font-semibold text-slate-400">
          📈 價格 × 多特徵走勢
          {normalizeSelectedFeature(selectedFeature) && (
            <span className="ml-2 text-xs px-2 py-0.5 rounded-full"
              style={{
                backgroundColor: FEATURE_CONFIG[normalizeSelectedFeature(selectedFeature)!]?.color + "22",
                color: FEATURE_CONFIG[normalizeSelectedFeature(selectedFeature)!]?.color,
              }}
            >
              聚焦：{FEATURE_CONFIG[normalizeSelectedFeature(selectedFeature)!]?.label}
            </span>
          )}
        </h2>

        <div className="flex items-center gap-2">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.days}
              onClick={() => setDays(tf.days)}
              className={`px-3 py-1 text-xs rounded-lg transition ${
                days === tf.days
                  ? "bg-blue-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700"
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Legend Toggles */}
      <div className="rounded-lg border border-sky-500/20 bg-sky-500/5 px-3 py-2 text-[11px] text-slate-300 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-sky-200">成熟度分層</span>
          <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-emerald-300">核心 {maturitySummary.core}</span>
          <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-2 py-0.5 text-sky-300">研究 {maturitySummary.research}</span>
          <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-amber-300">阻塞 {maturitySummary.blocked}</span>
        </div>
        <div className="text-slate-400 leading-5">
          綜合分數現在只使用 <span className="text-emerald-300">核心 decision signals</span>（{scoreFeatureKeys.length} 個），研究型 sparse-source 特徵只做 overlay 觀察，不再把 forward-archive / auth-blocked / snapshot-only 訊號混進主分數。
        </div>
      </div>
      <CustomLegend
        visibility={visibility}
        averageVisibility={averageVisibility}
        coverage={featureCoverage}
        onToggle={toggleVisibility}
        onToggleGroup={toggleGroupVisibility}
        onToggleAverage={toggleAverageVisibility}
      />
      {hiddenCoverageItems.length > 0 && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-[11px] text-slate-300 space-y-1">
          <div className="text-amber-300 font-medium">
            已自動隱藏 {hiddenCoverageItems.length} 個 coverage / 資料品質不足特徵，避免圖上出現失真雜訊線。
          </div>
          <div className="text-slate-400">
            {hiddenCoverageItems
              .slice(0, 5)
              .map(([key, meta]) => {
                const label = FEATURE_CONFIG[key]?.label ?? key;
                const reason = meta.quality_label && meta.quality_label !== "ok"
                  ? meta.quality_label
                  : `coverage ${meta.coverage_pct.toFixed(1)}%`;
                const policy = meta.history_class ? ` / ${meta.history_class}` : "";
                const archive = meta.raw_snapshot_events
                  ? ` / archive ${meta.raw_snapshot_events}/${meta.forward_archive_ready_min_events ?? 10} ${meta.forward_archive_status ?? "building"}${meta.raw_snapshot_latest_age_min != null ? ` / last ${meta.raw_snapshot_latest_age_min.toFixed(1)}m` : ""}`
                  : "";
                const latestStatus = meta.raw_snapshot_latest_status && meta.raw_snapshot_latest_status !== "ok"
                  ? ` / status ${meta.raw_snapshot_latest_status}${meta.raw_snapshot_latest_message ? `: ${meta.raw_snapshot_latest_message}` : ""}`
                  : "";
                return `${label}(${reason}${policy}${archive}${latestStatus})`;
              })
              .join(" · ")}
            {hiddenCoverageItems.length > 5 ? " …" : ""}
          </div>
        </div>
      )}

      {/* Loading / Error */}
      {loading && (
        <div className="px-4 py-10">
          <div className="rounded-xl border border-slate-700/60 bg-slate-950/60 px-4 py-3 text-sm text-slate-200">
            <div className="font-medium">載入歷史特徵資料中…</div>
            <div className="mt-1 text-xs text-slate-400">{loadingDetail}</div>
          </div>
        </div>
      )}
      {error && (
        <div className="flex items-center justify-center h-64 text-red-400 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Main Chart */}
      {!loading && !error && merged.length > 0 && (
        <div className="space-y-3">
          {/* Price + Features */}
          <ResponsiveContainer width="100%" height={340}>
            <ComposedChart data={merged} margin={{ top: 5, right: 50, left: 20, bottom: 5 }}>
              <defs>
                <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#94a3b8" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#94a3b8" stopOpacity={0} />
                </linearGradient>
              </defs>

              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />

              {/* Time X-axis */}
              <XAxis
                dataKey="label"
                tick={{ fill: "#64748b", fontSize: 10 }}
                axisLine={{ stroke: "#334155" }}
                tickLine={{ stroke: "#334155" }}
                interval="preserveStartEnd"
              />

              {/* Price Y-axis (left) */}
              <YAxis
                yAxisId="price"
                domain={priceDomain}
                tickFormatter={formatPrice}
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={{ stroke: "#334155" }}
                tickLine={{ stroke: "#334155" }}
                width={55}
              />

              {/* Feature Y-axis (right, 0–1) */}
              <YAxis
                yAxisId="sense"
                orientation="right"
                domain={[0, 1]}
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}`}
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={{ stroke: "#334155" }}
                tickLine={{ stroke: "#334155" }}
                width={40}
              />

              <Tooltip content={<CustomTooltip />} />

              {/* Price line */}
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="price"
                stroke="#e2e8f0"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#e2e8f0" }}
                animationDuration={800}
                name="價格"
              />

              {/* Feature lines */}
              {Object.entries(FEATURE_CONFIG).map(([key, cfg]) => (
                <Line
                  key={key}
                  yAxisId="sense"
                  type={lineTypeForFeature(key)}
                  dataKey={cfg.key}
                  stroke={cfg.color}
                  strokeWidth={normalizeSelectedFeature(selectedFeature) === key ? 3 : 1.5}
                  dot={false}
                  activeDot={{ r: normalizeSelectedFeature(selectedFeature) === key ? 5 : 3, fill: cfg.color }}
                  hide={!visibility[key]}
                  animationDuration={600}
                  connectNulls={false}
                  name={cfg.label}
                />
              ))}

              {(Object.keys(GROUP_AVERAGE_CONFIG) as FeatureGroupKey[]).map((groupKey) => {
                const avgCfg = GROUP_AVERAGE_CONFIG[groupKey];
                return (
                  <Line
                    key={String(avgCfg.key)}
                    yAxisId="sense"
                    type="monotone"
                    dataKey={avgCfg.key}
                    stroke={avgCfg.color}
                    strokeWidth={averageVisibility[groupKey] ? 3 : 0}
                    strokeDasharray="6 4"
                    dot={false}
                    hide={!averageVisibility[groupKey]}
                    animationDuration={400}
                    connectNulls={true}
                    name={avgCfg.label}
                  />
                );
              })}

              {/* Entry signals */}
              <Scatter
                yAxisId="price"
                dataKey="entrySignal"
                shape={<SignalDot />}
                isAnimationActive={false}
              />

              {/* Reduce signals */}
              <Scatter
                yAxisId="price"
                dataKey="reduceSignal"
                shape={<SignalDot />}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>

          {/* Score Area Chart */}
          <div>
            <div className="text-xs text-slate-500 mb-1 px-1">
              綜合推薦分數（0–100）
            </div>
            <ResponsiveContainer width="100%" height={100}>
              <AreaChart data={merged} margin={{ top: 5, right: 50, left: 20, bottom: 5 }}>
                <defs>
                  <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.6} />
                    <stop offset="50%" stopColor="#eab308" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#ef4444" stopOpacity={0.2} />
                  </linearGradient>
                </defs>

                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />

                <XAxis
                  dataKey="label"
                  tick={{ fill: "#64748b", fontSize: 9 }}
                  axisLine={{ stroke: "#334155" }}
                  tickLine={{ stroke: "#334155" }}
                  interval="preserveStartEnd"
                />

                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  axisLine={{ stroke: "#334155" }}
                  tickLine={{ stroke: "#334155" }}
                  width={35}
                />

                {/* Zone references */}
                <ReferenceArea y1={0} y2={30} fill="#ef4444" fillOpacity={0.05} />
                <ReferenceArea y1={30} y2={50} fill="#f97316" fillOpacity={0.05} />
                <ReferenceArea y1={50} y2={70} fill="#eab308" fillOpacity={0.05} />
                <ReferenceArea y1={70} y2={100} fill="#22c55e" fillOpacity={0.05} />

                <ReferenceLine y={30} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.3} />
                <ReferenceLine y={50} stroke="#eab308" strokeDasharray="3 3" strokeOpacity={0.3} />
                <ReferenceLine y={70} stroke="#22c55e" strokeDasharray="3 3" strokeOpacity={0.3} />

                <Tooltip
                  content={({ active, payload }: any) => {
                    if (!active || !payload?.[0]) return null;
                    const d: MergedPoint = payload[0].payload;
                    return (
                      <div className="bg-slate-800/95 border border-slate-600 rounded-lg px-3 py-1.5 text-xs shadow-xl">
                        <div className="text-slate-300">{d.label}</div>
                        <div style={{ color: d.score != null ? scoreColor(d.score) : "#94a3b8" }}>
                          分數：<span className="font-bold">{d.score ?? "—"}</span>
                        </div>
                      </div>
                    );
                  }}
                />

                <Area
                  type="monotone"
                  dataKey="score"
                  stroke="#3b82f6"
                  strokeWidth={1.5}
                  fill="url(#scoreGrad)"
                  animationDuration={800}
                  connectNulls={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && merged.length === 0 && (
        <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
          暫無歷史數據。系統需要累積足夠的特徵數據後才會顯示走勢圖。
        </div>
      )}
    </div>
  );
}
