/**
 * CandlestickChart — stacked synchronized price/equity charts for Strategy Lab & Dashboard.
 */
import { useEffect, useRef, useState } from "react";
import { useGlobalProgressTask } from "../hooks/useGlobalProgress";
import {
  createChart,
  CandlestickData,
  HistogramData,
  IChartApi,
  ISeriesApi,
  LineData,
  MouseEventParams,
  SeriesMarker,
  Time,
} from "lightweight-charts";
import { buildApiUrl } from "../hooks/useApi";

interface KlineResponse {
  symbol: string;
  interval: string;
  candles: { time: number; open: number; high: number; low: number; close: number; volume: number }[];
  indicators?: {
    ma20?: (number | null)[];
    ma60?: (number | null)[];
    rsi?: (number | null)[];
    macd?: (number | null)[];
    signal?: (number | null)[];
    histogram?: (number | null)[];
  };
  incremental?: boolean;
  append_after?: number;
}

interface TradeMarkerInput {
  timestamp?: string;
  entry_timestamp?: string;
  action?: string;
  reason?: string;
  pnl?: number;
  entry?: number;
  exit?: number;
  layers?: number;
}

interface EquityPoint {
  timestamp: string;
  equity: number;
  position_pct?: number;
  position_layers?: number;
}

interface ScorePoint {
  timestamp: string;
  score?: number | null;
  entry_quality?: number | null;
  model_confidence?: number | null;
}

interface HoverState {
  timeLabel: string;
  priceText: string;
  ma20Text: string;
  ma60Text: string;
  equityText: string;
  positionText: string;
  scoreText: string;
  entryQualityText: string;
  confidenceText: string;
  source: "price" | "equity";
}

interface Props {
  symbol?: string;
  interval?: string;
  days?: number;
  since?: number | null;
  until?: number | null;
  tradeMarkers?: TradeMarkerInput[];
  equityCurve?: EquityPoint[];
  scoreSeries?: ScorePoint[];
  title?: string;
}

const toUnix = (value?: string | null) => {
  if (!value) return null;
  const normalized = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value.replace(" ", "T")}Z`;
  const ms = new Date(normalized).getTime();
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : null;
};

const uniqueByTime = <T extends { time: Time }>(rows: T[]) => {
  const seen = new Map<string, T>();
  for (const row of rows) {
    seen.set(String(row.time), row);
  }
  return Array.from(seen.values()).sort((a, b) => Number(a.time) - Number(b.time));
};

const formatPrice = (value?: number | null, digits = 2) => (
  typeof value === "number" && Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: digits }) : "—"
);

const formatPct = (value?: number | null) => (
  typeof value === "number" && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "—"
);

const CHART_PROGRESS_TOTAL = 6;
const toChartProgress = (completed: number) => Math.max(0, Math.min(100, Math.round((completed / CHART_PROGRESS_TOTAL) * 100)));

const estimateFetchLimit = (interval: string, days: number, since?: number | null, until?: number | null) => {
  const intervalMsMap: Record<string, number> = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
  };
  const intervalMs = intervalMsMap[interval] || 3_600_000;
  if (since && until && until > since) {
    return Math.max(80, Math.min(1000, Math.ceil((until - since) / intervalMs) + 20));
  }
  return Math.max(80, Math.min(1000, Math.ceil((days * 24 * 3_600_000) / intervalMs) + 20));
};

const alignToCandleTime = (ts: number | null, candleTimes: number[]) => {
  if (!ts || candleTimes.length === 0) return null;
  let aligned: number | null = null;
  for (const candleTime of candleTimes) {
    if (candleTime <= ts) aligned = candleTime;
    else break;
  }
  return aligned;
};

const findClosestPoint = <T,>(lookup: Map<number, T>, orderedTimes: number[], targetTime: number) => {
  if (orderedTimes.length === 0) return null;
  if (lookup.has(targetTime)) {
    return { time: targetTime, value: lookup.get(targetTime)! };
  }
  let prev: number | null = null;
  let next: number | null = null;
  for (const time of orderedTimes) {
    if (time < targetTime) prev = time;
    else {
      next = time;
      break;
    }
  }
  const candidate = (() => {
    if (prev == null) return next;
    if (next == null) return prev;
    return Math.abs(targetTime - prev) <= Math.abs(next - targetTime) ? prev : next;
  })();
  if (candidate == null) return null;
  const value = lookup.get(candidate);
  return value == null ? null : { time: candidate, value };
};

const buildFallbackPositionSeries = (trades: TradeMarkerInput[], candleTimes: number[]) => {
  if (!trades.length || !candleTimes.length) return [] as LineData<Time>[];
  const levelByTime = new Map<number, number>();
  for (const trade of trades) {
    const start = alignToCandleTime(toUnix(trade.entry_timestamp), candleTimes);
    const end = alignToCandleTime(toUnix(trade.timestamp), candleTimes);
    if (!start) continue;
    const layers = Math.max(1, Math.min(3, trade.layers ?? 1));
    const level = (layers / 3) * 100;
    for (const candleTime of candleTimes) {
      if (candleTime < start) continue;
      if (end && candleTime > end) break;
      levelByTime.set(candleTime, Math.max(levelByTime.get(candleTime) ?? 0, level));
    }
  }
  return uniqueByTime(Array.from(levelByTime.entries()).map(([time, value]) => ({ time: time as Time, value })));
};

const CHART_CACHE_KEY_PREFIX = "polytrader.chartcache.v3";
const CHART_MEMORY_CACHE = new Map<string, KlineResponse>();
const CHART_INCREMENTAL_REFRESH_GAP_MS = 30_000;

const getIndicatorValue = (payload: KlineResponse, key: "ma20" | "ma60" | "rsi" | "macd" | "signal" | "histogram", time: number) => {
  const candles = payload.candles || [];
  const index = candles.findIndex((row) => row.time === time);
  if (index < 0) return null;
  return payload.indicators?.[key]?.[index] ?? null;
};

const mergeKlinePayload = (base: KlineResponse, incoming: KlineResponse): KlineResponse => {
  const candleMap = new Map<number, KlineResponse["candles"][number]>();
  const indicatorMaps = {
    ma20: new Map<number, number | null>(),
    ma60: new Map<number, number | null>(),
    rsi: new Map<number, number | null>(),
    macd: new Map<number, number | null>(),
    signal: new Map<number, number | null>(),
    histogram: new Map<number, number | null>(),
  };
  const applyPayload = (payload: KlineResponse) => {
    for (const candle of payload.candles || []) {
      candleMap.set(candle.time, candle);
      indicatorMaps.ma20.set(candle.time, getIndicatorValue(payload, "ma20", candle.time));
      indicatorMaps.ma60.set(candle.time, getIndicatorValue(payload, "ma60", candle.time));
      indicatorMaps.rsi.set(candle.time, getIndicatorValue(payload, "rsi", candle.time));
      indicatorMaps.macd.set(candle.time, getIndicatorValue(payload, "macd", candle.time));
      indicatorMaps.signal.set(candle.time, getIndicatorValue(payload, "signal", candle.time));
      indicatorMaps.histogram.set(candle.time, getIndicatorValue(payload, "histogram", candle.time));
    }
  };
  applyPayload(base);
  applyPayload(incoming);
  const candles = Array.from(candleMap.values()).sort((a, b) => a.time - b.time);
  const candleTimes = candles.map((candle) => candle.time);
  return {
    symbol: incoming.symbol || base.symbol,
    interval: incoming.interval || base.interval,
    candles,
    indicators: {
      ma20: candleTimes.map((time) => indicatorMaps.ma20.get(time) ?? null),
      ma60: candleTimes.map((time) => indicatorMaps.ma60.get(time) ?? null),
      rsi: candleTimes.map((time) => indicatorMaps.rsi.get(time) ?? null),
      macd: candleTimes.map((time) => indicatorMaps.macd.get(time) ?? null),
      signal: candleTimes.map((time) => indicatorMaps.signal.get(time) ?? null),
      histogram: candleTimes.map((time) => indicatorMaps.histogram.get(time) ?? null),
    },
    incremental: false,
  };
};

const shouldIncrementallyRefresh = (payload: KlineResponse, interval: string, until?: number | null) => {
  const lastCandle = payload.candles?.[payload.candles.length - 1];
  if (!lastCandle) return false;
  const intervalMsMap: Record<string, number> = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
  };
  const intervalMs = intervalMsMap[interval] || 3_600_000;
  const lastCandleMs = lastCandle.time * 1000;
  if (until && until > 0) {
    return lastCandleMs + intervalMs <= until;
  }
  return Date.now() - lastCandleMs > Math.max(intervalMs, CHART_INCREMENTAL_REFRESH_GAP_MS);
};

const loadCachedChartPayload = (cacheKey: string): KlineResponse | null => {
  if (CHART_MEMORY_CACHE.has(cacheKey)) {
    return CHART_MEMORY_CACHE.get(cacheKey) ?? null;
  }
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(`${CHART_CACHE_KEY_PREFIX}:${cacheKey}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as KlineResponse;
    CHART_MEMORY_CACHE.set(cacheKey, parsed);
    return parsed;
  } catch {
    return null;
  }
};

const saveCachedChartPayload = (cacheKey: string, payload: KlineResponse) => {
  CHART_MEMORY_CACHE.set(cacheKey, payload);
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(`${CHART_CACHE_KEY_PREFIX}:${cacheKey}`, JSON.stringify(payload));
  } catch {
    // ignore quota issues
  }
};

export default function CandlestickChart({
  symbol = "BTCUSDT",
  interval = "1h",
  days = 7,
  since = null,
  until = null,
  tradeMarkers = [],
  equityCurve = [],
  scoreSeries = [],
  title,
}: Props) {
  const priceContainerRef = useRef<HTMLDivElement>(null);
  const equityContainerRef = useRef<HTMLDivElement>(null);

  const priceChartRef = useRef<IChartApi | null>(null);
  const equityChartRef = useRef<IChartApi | null>(null);

  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const ma20SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const ma60SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const scoreSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const confidenceSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const equitySeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const positionSeriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  const candleLookupRef = useRef<Map<number, CandlestickData<Time>>>(new Map());
  const candleTimesRef = useRef<number[]>([]);
  const ma20LookupRef = useRef<Map<number, number>>(new Map());
  const ma60LookupRef = useRef<Map<number, number>>(new Map());
  const equityLookupRef = useRef<Map<number, number>>(new Map());
  const equityTimesRef = useRef<number[]>([]);
  const positionLookupRef = useRef<Map<number, number>>(new Map());
  const scoreLookupRef = useRef<Map<number, number>>(new Map());
  const entryQualityLookupRef = useRef<Map<number, number>>(new Map());
  const confidenceLookupRef = useRef<Map<number, number>>(new Map());
  const syncingRangeRef = useRef(false);
  const syncingCrosshairRef = useRef(false);
  const viewportKeyRef = useRef<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [progressDetail, setProgressDetail] = useState<string>("準備讀取 BTC/USDT 價格資料");
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [lastCandleTime, setLastCandleTime] = useState<number | null>(null);
  const [windowLabel, setWindowLabel] = useState<string>("—");
  const [hover, setHover] = useState<HoverState | null>(null);

  useGlobalProgressTask(loading, {
    label: hasLoadedOnce ? "圖表更新中" : "載入回測圖表中",
    detail: progressDetail,
    progress,
    tone: hasLoadedOnce ? "cyan" : "blue",
    priority: hasLoadedOnce ? 35 : 55,
    kind: "manual",
  });

  useEffect(() => {
    const priceContainer = priceContainerRef.current;
    const equityContainer = equityContainerRef.current;
    if (!priceContainer || !equityContainer) return;

    const priceChart = createChart(priceContainer, {
      width: priceContainer.clientWidth || 900,
      height: 360,
      layout: {
        background: { color: "#0f172a" },
        textColor: "#94a3b8",
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "#334155", scaleMargins: { top: 0.08, bottom: 0.24 } },
      leftPriceScale: {
        visible: true,
        borderColor: "#334155",
        scaleMargins: { top: 0.08, bottom: 0.62 },
      },
      timeScale: { borderColor: "#334155", timeVisible: true, secondsVisible: false },
    });

    const equityChart = createChart(equityContainer, {
      width: equityContainer.clientWidth || 900,
      height: 180,
      layout: {
        background: { color: "#0f172a" },
        textColor: "#94a3b8",
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "#334155", scaleMargins: { top: 0.15, bottom: 0.12 } },
      leftPriceScale: {
        visible: true,
        borderColor: "#334155",
        scaleMargins: { top: 0.12, bottom: 0.55 },
      },
      timeScale: { borderColor: "#334155", timeVisible: true, secondsVisible: false },
    });

    const candleSeries = priceChart.addCandlestickSeries({
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
    });
    const volumeSeries = priceChart.addHistogramSeries({
      color: "#26a69a40",
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    priceChart.priceScale("").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    const ma20Series = priceChart.addLineSeries({ color: "#f59e0b", lineWidth: 2, title: "MA20" });
    const ma60Series = priceChart.addLineSeries({ color: "#ec4899", lineWidth: 2, title: "MA60" });
    const scoreSeriesHandle = priceChart.addLineSeries({
      color: "#22c55e",
      lineWidth: 2,
      title: "進場分數",
      priceScaleId: "left",
      priceFormat: { type: "price", precision: 1, minMove: 0.1 },
      lineStyle: 0,
    });
    const confidenceSeriesHandle = priceChart.addLineSeries({
      color: "#38bdf8",
      lineWidth: 2,
      title: "模型信心",
      priceScaleId: "left",
      priceFormat: { type: "price", precision: 1, minMove: 0.1 },
      lineStyle: 2,
    });
    const equitySeries = equityChart.addLineSeries({
      color: "#38bdf8",
      lineWidth: 2,
      title: "策略權益指數",
      priceFormat: { type: "price", precision: 1, minMove: 0.1 },
    });
    const positionSeries = equityChart.addAreaSeries({
      priceScaleId: "left",
      lineColor: "#a855f7",
      topColor: "rgba(168, 85, 247, 0.35)",
      bottomColor: "rgba(168, 85, 247, 0.04)",
      lineWidth: 2,
      title: "倉位水位",
      priceFormat: { type: "price", precision: 0, minMove: 1 },
    });

    priceChartRef.current = priceChart;
    equityChartRef.current = equityChart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    ma20SeriesRef.current = ma20Series;
    ma60SeriesRef.current = ma60Series;
    scoreSeriesRef.current = scoreSeriesHandle;
    confidenceSeriesRef.current = confidenceSeriesHandle;
    equitySeriesRef.current = equitySeries;
    positionSeriesRef.current = positionSeries;

    const syncVisibleRange = (source: IChartApi, target: IChartApi) => {
      source.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (!range || syncingRangeRef.current) return;
        syncingRangeRef.current = true;
        target.timeScale().setVisibleLogicalRange(range);
        syncingRangeRef.current = false;
      });
    };
    syncVisibleRange(priceChart, equityChart);
    syncVisibleRange(equityChart, priceChart);

    const updateHoverFromTime = (timeValue: number, source: "price" | "equity") => {
      const candlePoint = findClosestPoint(candleLookupRef.current, candleTimesRef.current, timeValue);
      const equityPoint = findClosestPoint(equityLookupRef.current, equityTimesRef.current, timeValue);
      const positionPoint = findClosestPoint(positionLookupRef.current, equityTimesRef.current, timeValue);
      const hoverTime = candlePoint?.time ?? equityPoint?.time ?? positionPoint?.time ?? timeValue;
      const candle = candlePoint?.value ?? null;
      const ma20 = candlePoint ? ma20LookupRef.current.get(candlePoint.time) : undefined;
      const ma60 = candlePoint ? ma60LookupRef.current.get(candlePoint.time) : undefined;
      const score = candlePoint ? scoreLookupRef.current.get(candlePoint.time) : undefined;
      const entryQuality = candlePoint ? entryQualityLookupRef.current.get(candlePoint.time) : undefined;
      const confidence = candlePoint ? confidenceLookupRef.current.get(candlePoint.time) : undefined;
      setHover({
        timeLabel: new Date(hoverTime * 1000).toLocaleString("zh-TW"),
        priceText: candle ? `O ${formatPrice(candle.open)} · H ${formatPrice(candle.high)} · L ${formatPrice(candle.low)} · C ${formatPrice(candle.close)}` : "—",
        ma20Text: formatPrice(ma20),
        ma60Text: formatPrice(ma60),
        equityText: equityPoint != null ? `${equityPoint.value.toFixed(1)}` : "—",
        positionText: positionPoint != null ? `${positionPoint.value.toFixed(0)}%` : "—",
        scoreText: formatPct(score),
        entryQualityText: formatPct(entryQuality),
        confidenceText: formatPct(confidence),
        source,
      });
    };

    const syncCrosshairToOther = (
      source: "price" | "equity",
      param: MouseEventParams<Time>
    ) => {
      if (syncingCrosshairRef.current) return;
      const timeValue = param.time ? Number(param.time) : null;
      if (!timeValue) {
        syncingCrosshairRef.current = true;
        if (source === "price") equityChart.clearCrosshairPosition();
        else priceChart.clearCrosshairPosition();
        syncingCrosshairRef.current = false;
        return;
      }

      updateHoverFromTime(timeValue, source);

      syncingCrosshairRef.current = true;
      if (source === "price") {
        const equityPoint = findClosestPoint(equityLookupRef.current, equityTimesRef.current, timeValue);
        if (equityPoint && equitySeriesRef.current) {
          equityChart.setCrosshairPosition(equityPoint.value, equityPoint.time as Time, equitySeriesRef.current);
        } else {
          equityChart.clearCrosshairPosition();
        }
      } else {
        const candlePoint = findClosestPoint(candleLookupRef.current, candleTimesRef.current, timeValue);
        if (candlePoint && candleSeriesRef.current) {
          priceChart.setCrosshairPosition(candlePoint.value.close, candlePoint.time as Time, candleSeriesRef.current);
        } else {
          priceChart.clearCrosshairPosition();
        }
      }
      syncingCrosshairRef.current = false;
    };

    const onPriceMove = (param: MouseEventParams<Time>) => syncCrosshairToOther("price", param);
    const onEquityMove = (param: MouseEventParams<Time>) => syncCrosshairToOther("equity", param);

    priceChart.subscribeCrosshairMove(onPriceMove);
    equityChart.subscribeCrosshairMove(onEquityMove);

    const resizeObserver = new ResizeObserver(() => {
      if (priceContainerRef.current && priceChartRef.current) {
        priceChartRef.current.applyOptions({ width: Math.floor(priceContainerRef.current.clientWidth), height: 360 });
      }
      if (equityContainerRef.current && equityChartRef.current) {
        equityChartRef.current.applyOptions({ width: Math.floor(equityContainerRef.current.clientWidth), height: 180 });
      }
    });
    resizeObserver.observe(priceContainer);
    resizeObserver.observe(equityContainer);

    return () => {
      resizeObserver.disconnect();
      priceChart.unsubscribeCrosshairMove(onPriceMove);
      equityChart.unsubscribeCrosshairMove(onEquityMove);
      priceChart.remove();
      equityChart.remove();
      priceChartRef.current = null;
      equityChartRef.current = null;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const applyChartData = async (data: KlineResponse, options?: { updateViewport?: boolean; readyDetail?: string }) => {
      setProgress(toChartProgress(1));
      setProgressDetail(`已取得 ${data.candles?.length ?? 0} 根 K 線，正在整理價格序列`);
      if (!data.candles?.length) {
        if (!cancelled) {
          candleSeriesRef.current?.setData([]);
          volumeSeriesRef.current?.setData([]);
          ma20SeriesRef.current?.setData([]);
          ma60SeriesRef.current?.setData([]);
          equitySeriesRef.current?.setData([]);
          positionSeriesRef.current?.setData([]);
          candleSeriesRef.current?.setMarkers([]);
          equitySeriesRef.current?.setMarkers([]);
          setLoading(false);
          setHasLoadedOnce(true);
        }
        return;
      }

      const candleData = uniqueByTime(data.candles.map((c) => ({
        time: c.time as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })) as CandlestickData<Time>[]);
      const candleTimes = candleData.map((row) => Number(row.time));
      const candleLookup = new Map<number, CandlestickData<Time>>();
      candleData.forEach((row) => candleLookup.set(Number(row.time), row));
      candleLookupRef.current = candleLookup;
      candleTimesRef.current = candleTimes;
      candleSeriesRef.current?.setData(candleData);
      setProgress(toChartProgress(2));
      setProgressDetail("價格 K 線已對齊，正在整理 MA 與分數指標");

      volumeSeriesRef.current?.setData(
        uniqueByTime(data.candles.map((c) => ({
          time: c.time as Time,
          value: c.volume,
          color: c.close >= c.open ? "#26a69a40" : "#ef535040",
        })) as HistogramData<Time>[])
      );

      const safeLine = (arr?: (number | null)[]) =>
        uniqueByTime(
          (arr || [])
            .map((value, idx) => ({ time: data.candles[idx]?.time as Time, value }))
            .filter((row): row is LineData<Time> => typeof row.value === "number")
        );

      const ma20Data = safeLine(data.indicators?.ma20);
      const ma60Data = safeLine(data.indicators?.ma60);
      ma20SeriesRef.current?.setData(ma20Data);
      ma60SeriesRef.current?.setData(ma60Data);
      ma20LookupRef.current = new Map(ma20Data.map((row) => [Number(row.time), row.value]));
      ma60LookupRef.current = new Map(ma60Data.map((row) => [Number(row.time), row.value]));

      const toScoreLine = (selector: (point: ScorePoint) => number | null | undefined) => uniqueByTime(
        scoreSeries
          .map((point) => {
            const ts = alignToCandleTime(toUnix(point.timestamp), candleTimes);
            const value = selector(point);
            if (!ts || typeof value !== "number" || !Number.isFinite(value)) return null;
            return { time: ts as Time, value: value * 100 };
          })
          .filter((row): row is LineData<Time> => !!row)
      );
      const scoreData = toScoreLine((point) => point.score);
      const confidenceData = toScoreLine((point) => point.model_confidence);
      const entryQualityData = toScoreLine((point) => point.entry_quality);
      scoreSeriesRef.current?.setData(scoreData.length > 0 ? scoreData : entryQualityData);
      confidenceSeriesRef.current?.setData(confidenceData);
      scoreLookupRef.current = new Map((scoreData.length > 0 ? scoreData : entryQualityData).map((row) => [Number(row.time), row.value]));
      entryQualityLookupRef.current = new Map(entryQualityData.map((row) => [Number(row.time), row.value]));
      confidenceLookupRef.current = new Map(confidenceData.map((row) => [Number(row.time), row.value]));
      setProgress(toChartProgress(3));
      setProgressDetail("模型 / 進場分數已整理完成，正在對齊權益曲線");

      const baseEquity = equityCurve[0]?.equity ?? 0;
      const equityData = baseEquity > 0 && equityCurve.length > 1
        ? uniqueByTime(
            equityCurve
              .map((point) => {
                const ts = alignToCandleTime(toUnix(point.timestamp), candleTimes);
                if (!ts) return null;
                return { time: ts as Time, value: 100 * (point.equity / baseEquity) };
              })
              .filter((row): row is LineData<Time> => !!row)
          )
        : [];
      const rawPositionData = uniqueByTime(
        equityCurve
          .map((point) => {
            const ts = alignToCandleTime(toUnix(point.timestamp), candleTimes);
            const value = typeof point.position_pct === "number" && Number.isFinite(point.position_pct)
              ? point.position_pct * 100
              : null;
            if (!ts || value == null) return null;
            return { time: ts as Time, value };
          })
          .filter((row): row is LineData<Time> => !!row)
      );
      const positionData = rawPositionData.length > 0 ? rawPositionData : buildFallbackPositionSeries(tradeMarkers, candleTimes);
      equitySeriesRef.current?.setData(equityData);
      positionSeriesRef.current?.setData(positionData);
      equityLookupRef.current = new Map(equityData.map((row) => [Number(row.time), row.value]));
      equityTimesRef.current = Array.from(new Set([...equityData.map((row) => Number(row.time)), ...positionData.map((row) => Number(row.time))])).sort((a, b) => a - b);
      positionLookupRef.current = new Map(positionData.map((row) => [Number(row.time), row.value]));
      setProgress(toChartProgress(4));
      setProgressDetail("權益曲線與倉位水位已對齊，正在把買賣 markers 掛到圖上");

      const markers: SeriesMarker<Time>[] = [];
      const equityMarkers: SeriesMarker<Time>[] = [];
      for (const trade of tradeMarkers) {
        const buyTs = alignToCandleTime(toUnix(trade.entry_timestamp), candleTimes);
        if (buyTs) {
          const buyMarker = {
            time: buyTs as Time,
            position: "belowBar" as const,
            color: "#38bdf8",
            shape: "arrowUp" as const,
            text: trade.layers ? `buy L${trade.layers}` : "buy",
          };
          markers.push(buyMarker);
          equityMarkers.push({ ...buyMarker, text: trade.layers ? `進 L${trade.layers}` : "進" });
        }
        const sellTs = alignToCandleTime(toUnix(trade.timestamp), candleTimes);
        if (sellTs) {
          const positive = (trade.pnl ?? 0) >= 0;
          const sellMarker = {
            time: sellTs as Time,
            position: "aboveBar" as const,
            color: positive ? "#22c55e" : "#ef4444",
            shape: "arrowDown" as const,
            text: `${trade.reason ?? "exit"}${typeof trade.pnl === "number" ? ` ${trade.pnl.toFixed(0)}` : ""}`,
          };
          markers.push(sellMarker);
          equityMarkers.push({ ...sellMarker, text: positive ? "出 ✓" : "出 ✕" });
        }
      }
      const lastCandleTime = candleTimes[candleTimes.length - 1] ?? null;
      const normalizedMarkers = markers
        .filter((marker) => marker.time != null && (lastCandleTime == null || Number(marker.time) <= lastCandleTime))
        .map((marker) => Number(marker.time) === lastCandleTime ? { ...marker, text: marker.text?.slice(0, 12) ?? "" } : marker)
        .sort((a, b) => Number(a.time) - Number(b.time));
      const normalizedEquityMarkers = equityMarkers
        .filter((marker) => marker.time != null && (lastCandleTime == null || Number(marker.time) <= lastCandleTime))
        .map((marker) => Number(marker.time) === lastCandleTime ? { ...marker, text: marker.text?.slice(0, 8) ?? "" } : marker)
        .sort((a, b) => Number(a.time) - Number(b.time));
      candleSeriesRef.current?.setMarkers(normalizedMarkers);
      equitySeriesRef.current?.setMarkers(normalizedEquityMarkers);
      setProgress(toChartProgress(5));
      setProgressDetail(`買賣點已對齊完成，共 ${normalizedMarkers.length} 個 markers，正在更新視窗`);

      const viewportKey = `${symbol}:${interval}:${since ?? ""}:${until ?? ""}`;
      if ((options?.updateViewport ?? true) && (!hasLoadedOnce || viewportKeyRef.current !== viewportKey)) {
        priceChartRef.current?.timeScale().fitContent();
        equityChartRef.current?.timeScale().fitContent();
        viewportKeyRef.current = viewportKey;
      }

      if (!cancelled) {
        const firstTs = Number(candleData[0]?.time ?? 0);
        const lastTs = Number(candleData[candleData.length - 1]?.time ?? 0);
        const lastClose = candleData[candleData.length - 1]?.close ?? null;
        setLastPrice(lastClose);
        setLastCandleTime(lastTs || null);
        setWindowLabel(
          firstTs && lastTs
            ? `${new Date(firstTs * 1000).toLocaleString("zh-TW")} → ${new Date(lastTs * 1000).toLocaleString("zh-TW")}`
            : "—"
        );
        if (lastTs) {
          const lastEquity = findClosestPoint(equityLookupRef.current, equityTimesRef.current, lastTs)?.value;
          const lastPosition = findClosestPoint(positionLookupRef.current, equityTimesRef.current, lastTs)?.value;
          setHover({
            timeLabel: new Date(lastTs * 1000).toLocaleString("zh-TW"),
            priceText: lastClose != null ? `C ${formatPrice(lastClose)}` : "—",
            ma20Text: formatPrice(ma20LookupRef.current.get(lastTs)),
            ma60Text: formatPrice(ma60LookupRef.current.get(lastTs)),
            equityText: lastEquity != null ? `${lastEquity.toFixed(1)}` : "—",
            positionText: lastPosition != null ? `${lastPosition.toFixed(0)}%` : "—",
            scoreText: formatPct(scoreLookupRef.current.get(lastTs)),
            entryQualityText: formatPct(entryQualityLookupRef.current.get(lastTs)),
            confidenceText: formatPct(confidenceLookupRef.current.get(lastTs)),
            source: "price",
          });
        }
        setProgress(toChartProgress(6));
        setProgressDetail(options?.readyDetail || "BTC/USDT 價格圖、買賣點、分數指標與權益曲線已同步完成");
        setLoading(false);
        setHasLoadedOnce(true);
      }
    };

    const fetchAndSetData = async () => {
      try {
        setLoading(true);
        setError(null);
        setProgress(toChartProgress(0));
        setProgressDetail("正在向後端請求 BTC/USDT K 線資料");
        const limit = estimateFetchLimit(interval, days, since, until);
        const params = new URLSearchParams({ symbol, interval, limit: `${limit}` });
        if (since) params.set("since", `${since}`);
        if (until) params.set("until", `${until}`);
        const cacheKey = `${symbol}:${interval}:${since ?? ""}:${until ?? ""}:${limit}`;
        const cachedPayload = loadCachedChartPayload(cacheKey);

        if (cachedPayload) {
          await applyChartData(cachedPayload, {
            updateViewport: !hasLoadedOnce,
            readyDetail: "已從本地快取還原價格圖與權益曲線。",
          });
          if (!shouldIncrementallyRefresh(cachedPayload, interval, until)) {
            return;
          }
          setLoading(true);
          setProgress(toChartProgress(0));
          setProgressDetail("已載入本地快取，正在補抓最新 K 線差異");
          const lastCachedCandle = cachedPayload.candles[cachedPayload.candles.length - 1];
          if (!lastCachedCandle) {
            setLoading(false);
            return;
          }
          const incrementalParams = new URLSearchParams({ symbol, interval, limit: `${limit}`, append_after: `${lastCachedCandle.time * 1000}` });
          if (since) incrementalParams.set("since", `${since}`);
          if (until) incrementalParams.set("until", `${until}`);
          const incrementalResp = await fetch(buildApiUrl(`/api/chart/klines?${incrementalParams.toString()}`));
          if (!incrementalResp.ok) throw new Error(`${incrementalResp.status}`);
          const incrementalPayload: KlineResponse = await incrementalResp.json();
          if (!incrementalPayload.candles?.length) {
            setProgress(toChartProgress(6));
            setProgressDetail("本地快取已是最新，無需重新完整刷新。");
            setLoading(false);
            return;
          }
          const mergedPayload = mergeKlinePayload(cachedPayload, incrementalPayload);
          saveCachedChartPayload(cacheKey, mergedPayload);
          await applyChartData(mergedPayload, {
            updateViewport: false,
            readyDetail: `已從本地快取還原，並補上 ${incrementalPayload.candles.length} 根新 K 線。`,
          });
          return;
        }

        const resp = await fetch(buildApiUrl(`/api/chart/klines?${params.toString()}`));
        if (!resp.ok) throw new Error(`${resp.status}`);
        const payload: KlineResponse = await resp.json();
        saveCachedChartPayload(cacheKey, payload);
        await applyChartData(payload, { updateViewport: true });
      } catch (e: any) {
        if (!cancelled) {
          setError(e.message || "Failed to load chart data");
          setLoading(false);
        }
      }
    };

    if (priceChartRef.current && equityChartRef.current) {
      fetchAndSetData();
    }

    return () => {
      cancelled = true;
    };
  }, [symbol, interval, days, since, until, tradeMarkers, equityCurve, scoreSeries]);

  return (
    <div className="relative rounded-xl overflow-hidden border border-slate-700/50 bg-slate-950/70">
      <div className="flex flex-wrap items-start justify-between gap-3 px-4 py-3 bg-slate-900/80 border-b border-slate-700/50">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <span className="text-sm font-bold text-white">{title || symbol.replace("USDT", "/USDT")}</span>
            {lastPrice && <span className="text-lg font-mono text-white">${lastPrice.toLocaleString()}</span>}
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
            <span>資料窗：{windowLabel}</span>
            <span>·</span>
            <span>最後更新：{lastCandleTime ? new Date(lastCandleTime * 1000).toLocaleString("zh-TW") : "—"}</span>
          </div>
        </div>
        <div className="grid gap-2 text-[11px] sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-slate-700/50 bg-slate-950/50 px-3 py-2 text-slate-300">
            <div className="text-slate-500">價格圖</div>
            <div>BTC/USDT 價格 + MA20 / MA60 + 買賣 markers</div>
          </div>
          <div className="rounded-lg border border-emerald-700/30 bg-emerald-950/10 px-3 py-2 text-emerald-100">
            <div className="text-emerald-300">分數圖層</div>
            <div>上圖疊加進場分數，Hybrid 另顯示模型信心</div>
          </div>
          <div className="rounded-lg border border-cyan-700/30 bg-cyan-950/10 px-3 py-2 text-cyan-100">
            <div className="text-cyan-300">權益圖</div>
            <div>顯示策略權益、倉位水位與下圖買賣 markers</div>
          </div>
          <div className="rounded-lg border border-slate-700/50 bg-slate-950/50 px-3 py-2 text-slate-300 sm:col-span-2 xl:col-span-1">
            <div className="text-slate-500">同步檢視</div>
            <div>上下十字線與 hover 資訊同步</div>
          </div>
        </div>
      </div>

      <div className="border-b border-slate-800/80 bg-slate-950/40 px-4 py-3">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6 text-xs">
          <div className="rounded-lg border border-slate-700/40 bg-slate-900/40 px-3 py-2">
            <div className="text-slate-500">游標時間</div>
            <div className="font-medium text-slate-100">{hover?.timeLabel || "—"}</div>
          </div>
          <div className="rounded-lg border border-slate-700/40 bg-slate-900/40 px-3 py-2 xl:col-span-2">
            <div className="text-slate-500">價格 / K 線</div>
            <div className="font-medium text-slate-100">{hover?.priceText || "—"}</div>
          </div>
          <div className="rounded-lg border border-slate-700/40 bg-slate-900/40 px-3 py-2">
            <div className="text-slate-500">MA20 / MA60</div>
            <div className="font-medium text-slate-100">{hover ? `${hover.ma20Text} / ${hover.ma60Text}` : "—"}</div>
          </div>
          <div className="rounded-lg border border-emerald-700/30 bg-emerald-950/10 px-3 py-2">
            <div className="text-emerald-300">分數 / 品質</div>
            <div className="font-medium text-emerald-100">{hover ? `${hover.scoreText} / ${hover.entryQualityText}` : "—"}</div>
            <div className="mt-1 text-[10px] text-emerald-300/80">模型信心 {hover?.confidenceText || "—"}</div>
          </div>
          <div className="rounded-lg border border-cyan-700/30 bg-cyan-950/10 px-3 py-2">
            <div className="text-cyan-300">策略權益 / 倉位</div>
            <div className="font-medium text-cyan-100">{hover?.equityText || "—"}</div>
            <div className="mt-1 text-[10px] text-fuchsia-300/80">倉位水位 {hover?.positionText || "—"}</div>
          </div>
        </div>
      </div>

      <div className="px-4 pt-4 pb-2">
        <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
          <span>上圖：BTC/USDT 價格、買賣點、模型/進場分數</span>
          <span>{interval}</span>
        </div>
        <div ref={priceContainerRef} className="w-full h-[360px] min-h-[360px]" />
      </div>

      <div className="px-4 pb-4 pt-2 border-t border-slate-800/60">
        <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
          <span>下圖：策略權益 / 倉位水位 / 買賣點</span>
          <span className="text-cyan-300">hover 與上圖同步</span>
        </div>
        <div ref={equityContainerRef} className="w-full h-[180px] min-h-[180px]" />
      </div>

      {loading && !hasLoadedOnce && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 px-6">
          <div className="w-full max-w-md rounded-xl border border-slate-700/60 bg-slate-950/90 px-4 py-3 text-center text-sm text-slate-200">
            <div className="font-medium">載入回測圖表中…</div>
            <div className="mt-1 text-xs text-slate-400">{progressDetail}</div>
          </div>
        </div>
      )}
      {loading && hasLoadedOnce && (
        <div className="pointer-events-none absolute right-4 top-20 max-w-[calc(100%-2rem)] rounded-lg border border-cyan-700/30 bg-slate-950/85 px-3 py-2 text-xs text-cyan-100">
          圖表更新中… {progressDetail}
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80">
          <div className="text-red-400">⚠️ {error}</div>
        </div>
      )}
    </div>
  );
}
