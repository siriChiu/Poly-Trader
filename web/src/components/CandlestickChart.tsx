/**
 * CandlestickChart — TradingView-style K 線圖 + MA + RSI + MACD
 */
import { useEffect, useRef, useState, useCallback } from "react";
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  LineData,
  Time,
} from "lightweight-charts";

interface KlineResponse {
  symbol: string;
  interval: string;
  candles: { time: number; open: number; high: number; low: number; close: number; volume: number }[];
  indicators?: {
    ma20?: (number | null)[];
    ma60?: (number | null)[];
    rsi?: (number | null)[];
    macd?: { macd: (number | null)[]; signal: (number | null)[]; histogram: (number | null)[] };
  };
}

interface Props {
  symbol?: string;
  interval?: string;
  days?: number;
}

export default function CandlestickChart({ symbol = "BTCUSDT", interval = "1h", days = 7 }: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastPrice, setLastPrice] = useState<number | null>(null);

  // Create chart function — called only when container has valid dimensions
  const initChart = useCallback(() => {
    const container = chartContainerRef.current;
    if (!container) return false;

    const rect = container.getBoundingClientRect();
    const width = Math.floor(rect.width);
    const height = Math.floor(rect.height);

    if (width <= 0 || height <= 0) return false;

    const chart = createChart(container, {
      width,
      height,
      layout: {
        background: { color: "#0f172a" },
        textColor: "#94a3b8",
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: "#475569", width: 1, style: 2 },
        horzLine: { color: "#475569", width: 1, style: 2 },
      },
      rightPriceScale: { borderColor: "#334155", scaleMargins: { top: 0.1, bottom: 0.25 } },
      timeScale: { borderColor: "#334155", timeVisible: true, secondsVisible: false },
    });

    // Main candlestick
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#26a69a", downColor: "#ef5350",
      borderVisible: false, wickUpColor: "#26a69a", wickDownColor: "#ef5350",
    });

    // Volume (bottom 25%)
    const volumeSeries = chart.addHistogramSeries({
      color: "#26a69a40", priceFormat: { type: "volume" }, priceScaleId: "",
    });
    chart.priceScale("").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

    // MA20 line
    const ma20Series = chart.addLineSeries({
      color: "#f59e0b", lineWidth: 2, priceScaleId: "right",
      title: "MA20",
    });

    // MA60 line
    const ma60Series = chart.addLineSeries({
      color: "#ec4899", lineWidth: 2, priceScaleId: "right",
      title: "MA60",
    });

    // RSI pane (separate price scale at bottom)
    const rsiSeries = chart.addLineSeries({
      color: "#8b5cf6", lineWidth: 2,
      priceScaleId: "rsi",
      title: "RSI(14)",
    });
    chart.priceScale("rsi").applyOptions({
      scaleMargins: { top: 0.75, bottom: 0.05 },
      borderVisible: false,
    });

    // MACD pane
    const macdLineSeries = chart.addLineSeries({
      color: "#3b82f6", lineWidth: 1,
      priceScaleId: "macd", title: "MACD",
    });
    const macdSignalSeries = chart.addLineSeries({
      color: "#ef4444", lineWidth: 1,
      priceScaleId: "macd", title: "Signal",
    });
    const macdHistSeries = chart.addHistogramSeries({
      priceScaleId: "macd", title: "Histogram",
    });
    chart.priceScale("macd").applyOptions({
      scaleMargins: { top: 0.60, bottom: 0.20 },
      borderVisible: false,
    });

    chartRef.current = chart;

    // Expose series refs on chart for data population
    (chart as any)._candleSeries = candleSeries;
    (chart as any)._volumeSeries = volumeSeries;
    (chart as any)._ma20Series = ma20Series;
    (chart as any)._ma60Series = ma60Series;
    (chart as any)._rsiSeries = rsiSeries;
    (chart as any)._macdLineSeries = macdLineSeries;
    (chart as any)._macdSignalSeries = macdSignalSeries;
    (chart as any)._macdHistSeries = macdHistSeries;

    return true;
  }, []);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const container = chartContainerRef.current;

    // Setup ResizeObserver to create chart when dimensions are valid
    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;

      const w = Math.floor(entry.contentRect.width);
      const h = Math.floor(entry.contentRect.height);

      if (w > 0 && h > 0 && !chartRef.current) {
        // Create chart on first valid dimensions
        const ok = initChart();
        if (ok) {
          // Now that chart exists, fetch data
          fetchAndSetData();
        }
      } else if (chartRef.current) {
        // Just resize existing chart
        chartRef.current.applyOptions({ width: w, height: h });
      }
    });

    resizeObserver.observe(container);
    resizeObserverRef.current = resizeObserver;

    let cancelled = false;

    const fetchAndSetData = async () => {
      try {
        setLoading(true);
        const BASE = "";
        const limit = Math.min(days * 24, 1000);
        const resp = await fetch(`${BASE}/api/chart/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`);
        if (!resp.ok) throw new Error(`${resp.status}`);
        const data: KlineResponse = await resp.json();

        // Guard against empty or missing candles
        if (!data.candles || data.candles.length === 0) {
          if (!cancelled) setLoading(false);
          return;
        }

        // Guard against missing indicators
        const indicators = data.indicators || {};

        // Helper: safe mapping from indicator array to chart data
        const safeMap = (arr: (number | null)[] | undefined, _key: string): LineData<Time>[] => {
          if (!arr || arr.length === 0) return [];
          return data.candles
            .map((c, i) => ({
              time: c.time as Time,
              value: i < arr.length ? arr[i] : null,
            }))
            .filter((d): d is LineData<Time> => d.value !== null && d.value !== undefined);
        };

        // Set candle data
        const candleData: CandlestickData<Time>[] = data.candles.map(c => ({
          time: c.time as Time, open: c.open, high: c.high, low: c.low, close: c.close,
        }));
        const candleSeries = (chartRef.current as any)?._candleSeries as ISeriesApi<"Candlestick"> | undefined;
        if (candleSeries) candleSeries.setData(candleData);
        if (candleData.length > 0 && !cancelled) setLastPrice(candleData[candleData.length - 1].close);

        // Set volume
        const volumeSeries = (chartRef.current as any)?._volumeSeries as ISeriesApi<"Histogram"> | undefined;
        if (volumeSeries) {
          const volumeData: HistogramData<Time>[] = data.candles.map(c => ({
            time: c.time as Time, value: c.volume,
            color: c.close >= c.open ? "#26a69a40" : "#ef535040",
          }));
          volumeSeries.setData(volumeData);
        }

        // Set MA20
        const ma20Series = (chartRef.current as any)?._ma20Series as ISeriesApi<"Line"> | undefined;
        if (ma20Series) ma20Series.setData(safeMap(indicators.ma20, "ma20"));

        // Set MA60
        const ma60Series = (chartRef.current as any)?._ma60Series as ISeriesApi<"Line"> | undefined;
        if (ma60Series) ma60Series.setData(safeMap(indicators.ma60, "ma60"));

        // Set RSI
        const rsiSeries = (chartRef.current as any)?._rsiSeries as ISeriesApi<"Line"> | undefined;
        if (rsiSeries) rsiSeries.setData(safeMap(indicators.rsi, "rsi"));

        // Set MACD
        const macdLineSeries = (chartRef.current as any)?._macdLineSeries as ISeriesApi<"Line"> | undefined;
        const macdSignalSeries = (chartRef.current as any)?._macdSignalSeries as ISeriesApi<"Line"> | undefined;
        const macdHistSeries = (chartRef.current as any)?._macdHistSeries as ISeriesApi<"Histogram"> | undefined;

        const macdData = indicators.macd;

        if (macdLineSeries) macdLineSeries.setData(safeMap(macdData?.macd, "macd"));
        if (macdSignalSeries) macdSignalSeries.setData(safeMap(macdData?.signal, "signal"));

        if (macdHistSeries) {
          const histArr = macdData?.histogram;
          if (!histArr || histArr.length === 0) {
            // Empty histogram — no data to show
            macdHistSeries.setData([]);
          } else {
            const histData: HistogramData<Time>[] = data.candles.map((c, i) => {
              const val = i < histArr.length ? (histArr[i] ?? 0) : 0;
              return {
                time: c.time as Time,
                value: val,
                color: val >= 0 ? "#26a69a80" : "#ef535080",
              };
            });
            macdHistSeries.setData(histData);
          }
        }

        if (!cancelled) {
          chartRef.current?.timeScale().fitContent();
          setLoading(false);
        }
      } catch (e: any) {
        if (!cancelled) {
          setError(e.message || "Failed to load chart data");
          setLoading(false);
        }
      }
    };

    // Expose fetchAndSetData for ResizeObserver to call
    (resizeObserver as any)._fetchData = fetchAndSetData;

    return () => {
      cancelled = true;
      resizeObserver.disconnect();
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [symbol, interval, days, initChart]);

  return (
    <div className="relative rounded-xl overflow-hidden border border-slate-700/50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900/80 border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-white">{symbol.replace("USDT", "/USDT")}</span>
          {lastPrice && (
            <span className="text-lg font-mono text-white">${lastPrice.toLocaleString()}</span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-yellow-500 inline-block"></span> MA20</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-pink-500 inline-block"></span> MA60</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-purple-500 inline-block"></span> RSI</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-blue-500 inline-block"></span> MACD</span>
        </div>
      </div>

      {/* Chart — explicit style to ensure dimensions */}
      <div ref={chartContainerRef} style={{ width: "100%", height: "500px" }} />

      {/* Loading / Error */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80">
          <div className="text-slate-400 animate-pulse">載入 K 線與技術指標...</div>
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
