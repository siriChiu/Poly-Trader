/**
 * TradingView-style Candlestick Chart
 * Uses lightweight-charts by TradingView for professional-grade charting
 */
import { useEffect, useRef, useState } from "react";
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  Time,
  CandlestickSeriesPartialOptions,
  HistogramSeriesPartialOptions,
} from "lightweight-charts";

interface KlineData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Props {
  symbol?: string;
  interval?: string;
  days?: number;
  height?: number;
}

const CANDLE_OPTIONS: CandlestickSeriesPartialOptions = {
  upColor: "#26a69a",
  downColor: "#ef5350",
  borderVisible: false,
  wickUpColor: "#26a69a",
  wickDownColor: "#ef5350",
};

const VOLUME_OPTIONS: HistogramSeriesPartialOptions = {
  color: "#26a69a80",
  priceFormat: { type: "volume" },
  priceScaleId: "",
};

export default function CandlestickChart({
  symbol = "BTCUSDT",
  interval = "1h",
  days = 7,
  height = 500,
}: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastPrice, setLastPrice] = useState<number | null>(null);

  // Fetch kline data from Binance directly (or via backend proxy)
  useEffect(() => {
    const fetchKlines = async () => {
      try {
        setLoading(true);
        setError(null);

        const end = Date.now();
        const start = end - days * 24 * 60 * 60 * 1000;
        const url = `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&startTime=${start}&endTime=${end}&limit=1000`;

        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`Binance API error: ${resp.status}`);
        const data = await resp.json();

        const candleData: CandlestickData<Time>[] = [];
        const volumeData: HistogramData<Time>[] = [];

        for (const kline of data) {
          const time = (kline[0] / 1000) as Time;
          const open = parseFloat(kline[1]);
          const high = parseFloat(kline[2]);
          const low = parseFloat(kline[3]);
          const close = parseFloat(kline[4]);
          const volume = parseFloat(kline[5]);

          candleData.push({ time, open, high, low, close });
          volumeData.push({
            time,
            value: volume,
            color: close >= open ? "#26a69a40" : "#ef535040",
          });
        }

        if (candleRef.current && candleData.length > 0) {
          candleRef.current.setData(candleData);
          setLastPrice(candleData[candleData.length - 1].close);
        }
        if (volumeRef.current && volumeData.length > 0) {
          volumeRef.current.setData(volumeData);
        }

        if (chartRef.current && candleData.length > 0) {
          chartRef.current.timeScale().fitContent();
        }

        setLoading(false);
      } catch (err: any) {
        setError(err.message || "Failed to fetch kline data");
        setLoading(false);
      }
    };

    fetchKlines();
  }, [symbol, interval, days]);

  // Create chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: "#0f172a" },
        textColor: "#94a3b8",
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      crosshair: {
        mode: 1, // Magnet
        vertLine: { color: "#475569", width: 1, style: 2 },
        horzLine: { color: "#475569", width: 1, style: 2 },
      },
      rightPriceScale: {
        borderColor: "#334155",
        scaleMargins: { top: 0.1, bottom: 0.25 },
      },
      timeScale: {
        borderColor: "#334155",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // Candlestick series
    const candleSeries = chart.addCandlestickSeries(CANDLE_OPTIONS);

    // Volume series (separate price scale at bottom)
    const volumeSeries = chart.addHistogramSeries({
      ...VOLUME_OPTIONS,
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    chartRef.current = chart;
    candleRef.current = candleSeries;
    volumeRef.current = volumeSeries;

    // Resize observer
    const resizeObserver = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      chart.applyOptions({ width });
    });
    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [height]);

  const priceChange = lastPrice
    ? ((lastPrice - (candleRef.current?.dataByIndex(0, 0) as any)?.close || 0) /
        lastPrice) *
      100
    : 0;

  return (
    <div className="relative">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900/50 border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-white">
            {symbol.replace("USDT", "/USDT")}
          </span>
          {lastPrice && (
            <span className="text-xl font-mono text-white">
              ${lastPrice.toLocaleString()}
            </span>
          )}
        </div>
        <div className="flex gap-1">
          {["1h", "4h", "1d"].map((intv) => (
            <button
              key={intv}
              className={`px-2 py-1 text-xs rounded ${
                interval === intv
                  ? "bg-blue-600 text-white"
                  : "bg-slate-700 text-slate-400 hover:bg-slate-600"
              }`}
              onClick={() => {
                /* interval change triggers re-fetch via parent */
              }}
            >
              {intv.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div ref={chartContainerRef} className="w-full" />

      {/* Loading / Error overlay */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80">
          <div className="text-slate-400 animate-pulse">載入 K 線數據...</div>
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
