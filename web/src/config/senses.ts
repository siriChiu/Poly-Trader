/**
 * 完整特徵配置 — 20+ 特徵對應 Poly-Trader 的所有 IC-validated features
 * 包含：8 Core Senses + 2 Macro + 5 Technical + 6 P0/P1 Sensory + 4H 指標
 */

export const ALL_SENSES: Record<string, { emoji: string; name: string; description: string; color: string }> = {
  // 8 Core Senses
  eye:        { emoji: "👁️",  name: "Eye",        description: "24H return / 72H vol ratio (trend strength)",          color: "#3b82f6" },
  ear:        { emoji: "👂",  name: "Ear",        description: "24H momentum (price change)",                          color: "#8b5cf6" },
  nose:       { emoji: "👃",  name: "Nose",       description: "RSI(14) normalized (momemtum)",                       color: "#f59e0b" },
  tongue:     { emoji: "👅",  name: "Tongue",     description: "20-period mean-reversion deviation",                  color: "#ec4899" },
  body:       { emoji: "💪",  name: "Body",        description: "48H volatility z-score (vol regime detector)",        color: "#14b8a6" },
  pulse:      { emoji: "💓",  name: "Pulse",       description: "12H volume spike (short-term activity burst)",        color: "#ef4444" },
  aura:       { emoji: "🌈",  name: "Aura",        description: "144-period MA deviation (position extremeness proxy)", color: "#a855f7" },
  mind:       { emoji: "🧠",  name: "Mind",        description: "144-period return (medium-term momentum)",            color: "#06b6d4" },

  // 2 Macro
  vix:        { emoji: "📉",  name: "VIX",         description: "VIX value (fear gauge)",                             color: "#f97316" },
  dxy:        { emoji: "💵",  name: "DXY",         description: "Dollar Index (macro strength)",                     color: "#22c55e" },

  // 5 Technical Indicators
  rsi14:      { emoji: "📊",  name: "RSI 14",      description: "RSI period 14 (momentum oscillator)",               color: "#eab308" },
  macd_hist:  { emoji: "📈",  name: "MACD H",      description: "MACD Histogram (trend momentum)",                   color: "#3b82f6" },
  atr_pct:    { emoji: "📏",  name: "ATR %",       description: "Average True Range % of price (volatility)",         color: "#ec4899" },
  vwap_dev:   { emoji: "⚖️",  name: "VWAP Dev",   description: "VWAP deviation (fair value proxy)",                 color: "#14b8a6" },
  bb_pct_b:   { emoji: "🔵",  name: "BB %B",       description: "Bollinger Band %B (volatility channel)",            color: "#a855f7" },

  // P0/P1 Sensory + NQ
  claw:           { emoji: "🦞",  name: "Claw",     description: "Liquidation ratio (long liq = good for short)",    color: "#ef4444" },
  claw_intensity: { emoji: "🔥",  name: "Claw Int", description: "Liquidation intensity (severity)",                 color: "#f97316" },
  fang_pcr:       { emoji: "🦷",  name: "Fang PCR",  description: "Options Put/Call ratio (fear gauge)",             color: "#6366f1" },
  fang_skew:      { emoji: "⚡",  name: "Fang Skew", description: "Options IV skew (risk sentiment)",                color: "#8b5cf6" },
  fin_netflow:    { emoji: "🏦",  name: "Fin Flow", description: "ETF netflow (institutional sentiment)",           color: "#22c55e" },
  nq_return_1h:   { emoji: "📉",  name: "NQ 1H",     description: "NASDAQ 100 1H return (macro correlation)",      color: "#06b6d4" },

  // 4H Timeframe Indicators
  "4h_bias50":       { emoji: "📐", name: "4H Bias50",  description: "4H Price vs MA50 deviation (%)",                color: "#f43f5e" },
  "4h_bias20":       { emoji: "📐", name: "4H Bias20",  description: "4H Price vs MA20 deviation (%)",                color: "#fb923c" },
  "4h_bias200":      { emoji: "📐", name: "4H Bias200", description: "4H Price vs MA200 deviation (%) (regime)",      color: "#a3e635" },
  "4h_rsi14":        { emoji: "📈", name: "4H RSI 14",  description: "4H RSI period 14 (momentum)",                  color: "#facc15" },
  "4h_macd_hist":    { emoji: "📊", name: "4H MACD H",  description: "4H MACD Histogram (trend momentum)",            color: "#60a5fa" },
  "4h_bb_pct_b":     { emoji: "🔵", name: "4H BB %B",   description: "4H Bollinger Band %B",                          color: "#c084fc" },
  "4h_dist_bb_lower":{ emoji: "🛡️", name: "4H BB Low",  description: "4H Distance to BB lower band (support)",        color: "#34d399" },
  "4h_dist_sl":      { emoji: "📍", name: "4H Swing",   description: "4H Distance to nearest swing low (support level)", color: "#fb7185" },
  "4h_ma_order":     { emoji: "🔄", name: "4H MA ord",  description: "4H MA alignment (+1=bull / -1=bear)",           color: "#94a3b8" },
  "4h_vol_ratio":    { emoji: "📊", name: "4H Vol R",   description: "4H Volume vs 20-period average",                color: "#fbbf24" },
};

/** Helper: map feature name (with or without prefix) → config */
export function getSenseConfig(key: string) {
  // Try direct match first
  if (key in ALL_SENSES) return { key, ...ALL_SENSES[key] };
  // Strip prefixes
  const stripped = key.replace("feat_", "").replace("4h_", "4h_");
  if (stripped in ALL_SENSES) return { key: stripped, ...ALL_SENSES[stripped] };
  // Fallback
  return {
    key,
    emoji: "❓",
    name: key.replace("feat_", "").replace("4h_", "4H ").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
    description: "",
    color: "#64748b",
  };
}
