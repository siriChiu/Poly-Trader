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
}

interface MergedPoint {
  time: number;
  label: string;
  price: number;
  score: number | null;
  buySignal: number | null;
  sellSignal: number | null;
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

const TIMEFRAMES = [
  { label: "1D", days: 1 },
  { label: "7D", days: 7 },
  { label: "30D", days: 30 },
];

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

/** Combine visible feature scores into a recommendation score 0–100 */
function calcScore(point: Partial<MergedPoint>): number | null {
  const vals = FEATURE_ORDER.map((k) => point[FEATURE_CONFIG[k].key]);
  const valid = vals.filter((v): v is number => v !== null && v !== undefined);
  if (valid.length === 0) return null;
  const avg = valid.reduce((a, b) => a + b, 0) / valid.length;
  return Math.round(Math.max(0, Math.min(100, avg * 100)));
}

/** Sell/Short signals: score crosses thresholds (high score = strong sell signal) */
function detectSignals(data: MergedPoint[]) {
  for (let i = 1; i < data.length; i++) {
    const prev = data[i - 1].score;
    const curr = data[i].score;
    if (prev === null || curr === null) continue;
    // Core: high score = sell-win (short profit)
    if (prev < 60 && curr >= 60) data[i].sellSignal = data[i].price;  // SELL signal strengthening
    if (prev > 40 && curr <= 40) data[i].buySignal = data[i].price;   // SELL signal weakening = HOLD/DON'T SHORT
  }
}

// ─── Custom Legend ───

function CustomLegend({
  visibility,
  onToggle,
  onToggleGroup,
}: {
  visibility: Record<string, boolean>;
  onToggle: (key: string) => void;
  onToggleGroup: (group: FeatureGroupKey) => void;
}) {
  const groupedEntries = Object.entries(FEATURE_CONFIG).reduce((acc, [key, cfg]) => {
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
        <span className="flex items-center gap-1 text-xs text-green-400 bg-slate-800/60 px-2 py-1 rounded-md">▲ 買</span>
        <span className="flex items-center gap-1 text-xs text-red-400 bg-slate-800/60 px-2 py-1 rounded-md">▼ 賣</span>
      </div>

      {Object.entries(groupedEntries).map(([groupKey, items]) => (
        <div key={groupKey} className="rounded-lg border border-slate-800/70 bg-slate-900/40 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <div>
              <div className="text-xs font-semibold text-slate-300">{FEATURE_GROUPS[groupKey as FeatureGroupKey].label}</div>
              <div className="text-[11px] text-slate-500">{FEATURE_GROUPS[groupKey as FeatureGroupKey].description}</div>
            </div>
            <button
              onClick={() => onToggleGroup(groupKey as FeatureGroupKey)}
              className="text-[11px] text-blue-400 hover:text-blue-300"
            >
              切換整組
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {items.map(([key, cfg]) => {
              const active = visibility[key] ?? true;
              return (
                <button
                  key={key}
                  onClick={() => onToggle(key)}
                  className={`flex items-center gap-1 text-xs px-2 py-1 rounded-md transition-all ${
                    active ? "bg-slate-700/80 text-white" : "bg-slate-800/40 text-slate-500 line-through"
                  }`}
                  style={active ? { borderColor: cfg.color, borderWidth: 1 } : undefined}
                >
                  <span className="w-3 h-0.5 inline-block" style={{ backgroundColor: active ? cfg.color : "#475569" }} />
                  {cfg.label}
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

// ─── Buy/Sell Custom Dot ───

function SignalDot(props: any) {
  const { cx, cy, payload } = props;
  if (!cx || !cy) return null;

  if (payload.buySignal != null) {
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
  if (payload.sellSignal != null) {
    return (
      <g>
        <polygon
          points={`${cx},${cy + 8} ${cx - 6},${cy - 4} ${cx + 6},${cy - 4}`}
          fill="#ef4444"
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

// ─── Main Component ───

export default function FeatureChart({ selectedFeature, onClear, days: initialDays = 7 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [days, setDays] = useState(initialDays);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [merged, setMerged] = useState<MergedPoint[]>([]);
  const [visibility, setVisibility] = useState<Record<string, boolean>>(
    Object.fromEntries(Object.keys(FEATURE_CONFIG).map((k) => [k, true]))
  );

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
    setError(null);

    async function load() {
      try {
        const interval = days <= 1 ? "15m" : days <= 7 ? "1h" : "4h";
        const limit = days <= 1 ? 96 : days <= 7 ? 168 : 180;

        const [features, klines] = await Promise.all([
          fetchApi<FeatureRow[]>(`/api/features?days=${days}`),
          fetchApi<KlineResponse>(`/api/chart/klines?symbol=BTCUSDT&interval=${interval}&limit=${limit}`),
        ]);

        if (cancelled) return;

        // Build feature lookup by hour key
        const featMap = new Map<string, FeatureRow>();
        for (const f of features) {
          const d = new Date(f.timestamp);
          // Round to the interval boundary
          const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}-${Math.floor(d.getHours() / (interval === "15m" ? 1 : interval === "4h" ? 4 : 1)) * (interval === "15m" ? 1 : interval === "4h" ? 4 : 1)}`;
          featMap.set(key, f);
        }

        const points: MergedPoint[] = klines.candles.map((c) => {
          const d = new Date(c.time * 1000);
          const hourBucket = Math.floor(d.getHours() / (interval === "15m" ? 1 : interval === "4h" ? 4 : 1)) * (interval === "15m" ? 1 : interval === "4h" ? 4 : 1);
          const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}-${hourBucket}`;

          let feat: FeatureRow | undefined = featMap.get(key);
          let minDiff = Infinity;
          if (!feat) {
            for (const f of features) {
              const diff = Math.abs(new Date(String(f.timestamp)).getTime() - c.time * 1000);
              if (diff < minDiff) {
                minDiff = diff;
                feat = f;
              }
            }
            if (minDiff > 2 * 3600 * 1000) feat = undefined;
          }

          const dynamicValues = Object.fromEntries(
            FEATURE_ORDER.map((featureKey) => {
              const raw = feat?.[featureKey];
              return [featureKey, typeof raw === "number" ? raw : raw == null ? null : Number(raw)];
            })
          );

          return {
            time: c.time,
            label: formatTime(c.time),
            price: c.close,
            ...dynamicValues,
            score: null,
            buySignal: null,
            sellSignal: null,
          };
        });

        // Calculate scores and detect signals
        for (const p of points) {
          p.score = calcScore(p);
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

  const toggleVisibility = useCallback((key: string) => {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const toggleGroupVisibility = useCallback((group: FeatureGroupKey) => {
    const keys = Object.entries(FEATURE_CONFIG)
      .filter(([, cfg]) => cfg.category === group)
      .map(([key]) => key);
    setVisibility((prev) => {
      const shouldEnable = keys.some((key) => !prev[key]);
      const next = { ...prev };
      for (const key of keys) next[key] = shouldEnable;
      return next;
    });
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
      <CustomLegend visibility={visibility} onToggle={toggleVisibility} onToggleGroup={toggleGroupVisibility} />

      {/* Loading / Error */}
      {loading && (
        <div className="flex items-center justify-center h-64 text-slate-500 animate-pulse">
          載入歷史數據...
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
                  type="monotone"
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

              {/* Buy signals */}
              <Scatter
                yAxisId="price"
                dataKey="buySignal"
                shape={<SignalDot />}
                isAnimationActive={false}
              />

              {/* Sell signals */}
              <Scatter
                yAxisId="price"
                dataKey="sellSignal"
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
