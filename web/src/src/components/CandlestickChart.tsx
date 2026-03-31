/**
 * TradingView-style Candlestick Chart with MA/RSI/MACD
 * Uses lightweight-charts by TradingView
 */
import { useEffect, useRef, useState } from "react";
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  LineData,
  Time,
  CandlestickSeriesPartialOptions,
  LineSeriesPartialOptions,
} from "lightweight-charts";

interface Props {
  symbol?: string;
  interval?: string;
  days?: number;
}

const CANDLE_OPTS: CandlestickSeriesPartialOptions = {
  upColor: "#26a69a",
  downColor: "#ef5350",
  borderVisible: false,
  wickUpColor: "#26a69a",
  wickDownColor: "#ef5350",
};

export default function CandlestickChart({
  symbol = "BTCUSDT",
  interval = "1h",
  days = 7,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const ma20Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma60Ref = useRef<ISeriesApi<"Line"> | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [indicators, setIndicators] = useState<{ rsi: (number | null)[]; macd: any } | null>(null);

  // Fetch kline data
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
        const closes: number[] = [];

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
          closes.push(close);
        }

        if (candleRef.current && candleData.length > 0) {
          candleRef.current.setData(candleData);
          setLastPrice(candleData[candleData.length - 1].close);
        }
        if (volumeRef.current && volumeData.length > 0) {
          volumeRef.current.setData(volumeData);
        }

        // MA20
        if (ma20Ref.current && closes.length >= 20) {
          const ma20: LineData<Time>[] = [];
          for (let i = 19; i < candleData.length; i++) {
            const avg = closes.slice(i - 19, i + 1).reduce((a, b) => a + b, 0) / 20;
            ma20.push({ time: candleData[i].time, value: avg });
          }
          ma20Ref.current.setData(ma20);
        }

        // MA60
        if (ma60Ref.current && closes.length >= 60) {
          const ma60: LineData<Time>[] = [];
          for (let i = 59; i < candleData.length; i++) {
            const avg = closes.slice(i - 59, i + 1).reduce((a, b) => a + b, 0) / 60;
            ma60.push({ time: candleData[i].time, value: avg });
          }
          ma60Ref.current.setData(ma60);
        }

        // RSI & MACD for display
        const rsi = calcRSI(closes, 14);
        const macd = calcMACD(closes);
        setIndicators({ rsi, macd });

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
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 500,
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
        mode: 1,
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

    // Candlestick
    candleRef.current = chart.addCandlestickSeries(CANDLE_OPTS);

    // Volume
    volumeRef.current = chart.addHistogramSeries({
      color: "#26a69a80",
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    chart.priceScale("").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    // MA lines
    ma20Ref.current = chart.addLineSeries({
      color: "#f59e0b",
      lineWidth: 2,
      title: "MA20",
    });
    ma60Ref.current = chart.addLineSeries({
      color: "#8b5cf6",
      lineWidth: 2,
      title: "MA60",
    });

    chartRef.current = chart;

    // Resize
    const ro = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      chart.applyOptions({ width });
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, []);

  return (
    <div className="relative bg-slate-900/50 rounded-xl border border-slate-700/50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          <span className="text-base font-bold text-white">
            {symbol.replace("USDT", "/USDT")}
          </span>
          {lastPrice && (
            <span className="text-lg font-mono text-white">
              ${lastPrice.toLocaleString()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-yellow-500 inline-block" /> MA20
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-purple-500 inline-block" /> MA60
          </span>
        </div>
      </div>

      {/* Chart */}
      <div ref={containerRef} className="w-full" />

      {/* RSI / MACD indicators bar */}
      {indicators && (
        <div className="flex items-center gap-6 px-4 py-2 border-t border-slate-700/50 text-xs">
          <div>
            <span className="text-slate-500">RSI(14): </span>
            <span className={`font-mono font-bold ${
              (indicators.rsi[indicators.rsi.length - 1] ?? 50) > 70 ? "text-red-400" :
              (indicators.rsi[indicators.rsi.length - 1] ?? 50) < 30 ? "text-green-400" : "text-slate-300"
            }`}>
              {(indicators.rsi[indicators.rsi.length - 1] ?? 50).toFixed(1)}
            </span>
          </div>
          <div>
            <span className="text-slate-500">MACD: </span>
            <span className={`font-mono font-bold ${
              (indicators.macd?.histogram?.[indicators.macd.histogram.length - 1] ?? 0) > 0 ? "text-green-400" : "text-red-400"
            }`}>
              {(indicators.macd?.macd?.[indicators.macd.macd.length - 1] ?? 0).toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-slate-500">Signal: </span>
            <span className="font-mono text-slate-300">
              {(indicators.macd?.signal?.[indicators.macd.signal.length - 1] ?? 0).toFixed(2)}
            </span>
          </div>
        </div>
      )}

      {/* Loading / Error */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 z-10">
          <div className="text-slate-400 animate-pulse">載入 K 線數據...</div>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 z-10">
          <div className="text-red-400">⚠️ {error}</div>
        </div>
      )}
    </div>
  );
}

// ─── RSI / MACD helpers ───

function calcRSI(data: number[], period: number = 14): (number | null)[] {
  const result: (number | null)[] = new Array(period).fill(null);
  if (data.length <= period) return result;

  const gains: number[] = [];
  const losses: number[] = [];
  for (let i = 1; i < data.length; i++) {
    const diff = data[i] - data[i - 1];
    gains.push(Math.max(diff, 0));
    losses.push(Math.max(-diff, 0));
  }

  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;

  result.push(avgLoss === 0 ? 100 : +(100 - 100 / (1 + avgGain / avgLoss)).toFixed(2));

  for (let i = period; i < gains.length; i++) {
    avgGain = (avgGain * (period - 1) + gains[i]) / period;
    avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
    result.push(avgLoss === 0 ? 100 : +(100 - 100 / (1 + avgGain / avgLoss)).toFixed(2));
  }
  return result;
}

function calcMACD(data: number[], fast = 12, slow = 26, signal = 9) {
  function ema(values: number[], period: number): number[] {
    const k = 2 / (period + 1);
    const result = [values[0]];
    for (let i = 1; i < values.length; i++) {
      result.push(result[i - 1] * (1 - k) + values[i] * k);
    }
    return result;
  }

  if (data.length < slow) return { macd: [], signal: [], histogram: [] };

  const emaFast = ema(data, fast);
  const emaSlow = ema(data, slow);
  const macdLine = emaFast.map((f, i) => +(f - emaSlow[i]).toFixed(4));

  const signalLineRaw = ema(macdLine.slice(slow - 1), signal);
  const signalLine: (number | null)[] = new Array(slow - 1).fill(null).concat(signalLineRaw.map(v => +v.toFixed(4)));
  const histogram = macdLine.map((m, i) => signalLine[i] !== null ? +(m - signalLine[i]!).toFixed(4) : null);

  return { macd: macdLine, signal: signalLine, histogram };
}
