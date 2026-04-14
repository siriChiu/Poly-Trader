/**
 * Dashboard v2.0 — 使用者體驗增強版
 */
import { useState, useEffect, useCallback } from "react";
import RadarChart from "../components/RadarChart";
import AdviceCard from "../components/AdviceCard";
import FeatureChart from "../components/FeatureChart";
import CandlestickChart from "../components/CandlestickChart";
import BacktestSummary from "../components/BacktestSummary";
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

interface BacktestData {
  final_equity: number;
  initial_capital: number;
  total_trades: number;
  win_rate: number;
  profit_loss_ratio: number;
  max_drawdown: number;
  total_return: number;
  avg_entry_quality?: number | null;
  avg_allowed_layers?: number | null;
  dominant_regime_gate?: string | null;
  avg_expected_win_rate?: number | null;
  avg_expected_pyramid_quality?: number | null;
  avg_expected_drawdown_penalty?: number | null;
  avg_expected_time_underwater?: number | null;
  avg_decision_quality_score?: number | null;
  decision_quality_label?: string | null;
  decision_quality_sample_size?: number | null;
  decision_contract?: {
    target_col?: string | null;
    target_label?: string | null;
    sort_semantics?: string | null;
    decision_quality_horizon_minutes?: number | null;
  } | null;
  error?: string;
}

export default function Dashboard() {
  const [interval, setInterval] = useState("1h");
  const [days, setDays] = useState(7);
  const [selectedSense, setSelectedSense] = useState<string | null>(null);
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

  const { data: sensesData, error: apiError, refresh: refreshSenses } = useApi<SensesResponse>("/api/senses", 30000);
  const { data: featureCoverageData } = useApi<FeatureCoverageResponse>("/api/features/coverage?days=30", 60000);
  const { data: backtestData } = useApi<BacktestData>("/api/backtest");
  const { data: confidenceData } = useApi<ConfidenceData>("/api/predict/confidence", 60000);
  const { data: modelStats } = useApi<ModelStats>("/api/model/stats", 60000);

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

  // 合併 live data 與 API data
  const scores = liveScores.eye !== 0.5 || liveScores.ear !== 0.5
    ? liveScores
    : sensesData?.scores || liveScores;

  const advice = liveAdvice || sensesData?.recommendation;
  const maturitySummary = featureCoverageData?.maturity_counts ?? null;

  const handleTrade = useCallback(async (side: string) => {
    if (side === "hold") return;
    try {
      const resp = await fetchApi("/api/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ side, symbol: "BTCUSDT", qty: 0.001 }),
      });
      // 顯示成功提示
      const data = resp as any;
      const label = side === "buy" ? "買入" : side === "reduce" ? "減碼" : side.toUpperCase();
      alert(data?.success || data?.order
        ? `${label} 指令已提交（Dry Run）`
        : `${label} 已發送`);
    } catch (e: any) {
      alert(`下單失敗: ${e.message}`);
    }
  }, []);

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

      {/* Row 1: Radar + Advice */}
      <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-4 items-stretch">
        {/* Left: Radar */}
        <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-5 flex h-full flex-col items-center">
          <div className="flex items-center justify-between w-full mb-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-300">🎯 多特徵雷達圖</h2>
              <div className="text-xs text-slate-500 mt-1">已改用市場語義短標籤，避免舊感官命名與文字重疊。</div>
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

      {/* Row 2: Sense History Chart */}
      <FeatureChart selectedFeature={selectedSense} days={days} onClear={() => setSelectedSense(null)} />

      {/* Row 3: K 線圖 */}
      <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <span className="text-sm font-semibold text-slate-300">📊 K 線圖 + 技術指標</span>
          <div className="flex items-center gap-1">
            {[
              { label: "1H", iv: "1h", d: 3 },
              { label: "4H", iv: "4h", d: 14 },
              { label: "1D", iv: "1d", d: 90 },
            ].map((opt) => (
              <button
                key={opt.iv}
                onClick={() => { setInterval(opt.iv); setDays(opt.d); }}
                className={`px-3 py-1 text-xs rounded-lg transition ${
                  interval === opt.iv
                    ? "bg-blue-600 text-white"
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <CandlestickChart symbol="BTCUSDT" interval={interval} days={days} />
        {/* 指標圖例 */}
        <div className="flex flex-wrap gap-3 mt-2 text-xs text-slate-500">
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-yellow-500 inline-block"></span> MA20</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-pink-500 inline-block"></span> MA60</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-purple-500 inline-block"></span> RSI</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-blue-500 inline-block"></span> MACD</span>
        </div>
      </div>

      {/* Row 4: Backtest */}
      {backtestData && backtestData.total_trades !== undefined && !backtestData.error && (
        <BacktestSummary
          finalEquity={backtestData.final_equity}
          initialCapital={backtestData.initial_capital}
          totalTrades={backtestData.total_trades}
          winRate={backtestData.win_rate}
          profitLossRatio={backtestData.profit_loss_ratio}
          maxDrawdown={backtestData.max_drawdown}
          totalReturn={backtestData.total_return}
          avgEntryQuality={backtestData.avg_entry_quality}
          avgAllowedLayers={backtestData.avg_allowed_layers}
          dominantRegimeGate={backtestData.dominant_regime_gate}
          avgDecisionQualityScore={backtestData.avg_decision_quality_score}
          decisionQualityLabel={backtestData.decision_quality_label}
          avgExpectedWinRate={backtestData.avg_expected_win_rate}
          avgExpectedPyramidQuality={backtestData.avg_expected_pyramid_quality}
          avgExpectedDrawdownPenalty={backtestData.avg_expected_drawdown_penalty}
          avgExpectedTimeUnderwater={backtestData.avg_expected_time_underwater}
          decisionQualitySampleSize={backtestData.decision_quality_sample_size}
          decisionContract={backtestData.decision_contract}
        />
      )}
    </div>
  );
}
