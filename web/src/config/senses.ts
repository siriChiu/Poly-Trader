/**
 * Feature metadata for Poly-Trader.
 * Replaces the old body-sense metaphor with grouped crypto-native explanations.
 */

export type FeatureGroupKey = "microstructure" | "technical" | "macro" | "structure4h";

export interface SenseMeta {
  name: string;
  shortLabel: string;
  description: string;
  meaning: string;
  category: FeatureGroupKey;
  color: string;
}

export const FEATURE_GROUPS: Record<FeatureGroupKey, { label: string; description: string }> = {
  microstructure: {
    label: "市場微結構",
    description: "短線價格、量能、均值回歸與局部波動，反映當下進場節奏。",
  },
  technical: {
    label: "技術指標",
    description: "經典技術指標，協助辨識趨勢、波動與相對位置。",
  },
  macro: {
    label: "宏觀風險",
    description: "跨市場風險偏好與美元環境，觀察加密貨幣是否受到外部資金壓力。",
  },
  structure4h: {
    label: "4H 結構",
    description: "4 小時級別的趨勢框架、支撐距離與大方向位置，用來過濾雜訊。",
  },
};

export const ALL_SENSES: Record<string, SenseMeta> = {
  eye: {
    name: "趨勢強度",
    shortLabel: "趨勢",
    description: "24H 報酬 / 72H 波動比率。",
    meaning: "高值代表價格推進效率高，市場正在用較小波動換取較大漲跌幅，通常意味趨勢更明確。",
    category: "microstructure",
    color: "#3b82f6",
  },
  ear: {
    name: "短線動能",
    shortLabel: "動能",
    description: "24H 價格動能變化。",
    meaning: "觀察最近一段時間的推進速度，高值代表買盤/賣盤正在加速，低值代表短線推力減弱。",
    category: "microstructure",
    color: "#8b5cf6",
  },
  nose: {
    name: "RSI 極值",
    shortLabel: "RSI",
    description: "RSI(14) 正規化位置。",
    meaning: "用來衡量短線是否過熱或過冷；在加密貨幣中常作為抄底/追價的節奏濾網。",
    category: "microstructure",
    color: "#f59e0b",
  },
  tongue: {
    name: "均值回歸偏離",
    shortLabel: "回歸",
    description: "價格偏離短期均值的程度。",
    meaning: "高偏離通常代表短線價格拉太快，回測均值機率上升；低偏離代表價格更接近平衡區。",
    category: "microstructure",
    color: "#ec4899",
  },
  body: {
    name: "波動狀態",
    shortLabel: "波動",
    description: "48H 波動率 z-score。",
    meaning: "用來辨識市場是否進入劇烈波動期；在加密市場中，過高波動常意味風險放大與止損更容易被掃。",
    category: "microstructure",
    color: "#14b8a6",
  },
  pulse: {
    name: "量能脈衝",
    shortLabel: "量能",
    description: "12H 成交量突增強度。",
    meaning: "量能放大代表資金正在真正參與，能幫助分辨『有成交支持的突破』和『無量反彈』。",
    category: "microstructure",
    color: "#ef4444",
  },
  aura: {
    name: "均線偏離",
    shortLabel: "均線差",
    description: "144 期均線偏離。",
    meaning: "衡量價格離中期均線有多遠；對加密貨幣來說，偏離過大通常代表情緒過熱或過度恐慌。",
    category: "microstructure",
    color: "#a855f7",
  },
  mind: {
    name: "中期動量",
    shortLabel: "中期動量",
    description: "144 期報酬變化。",
    meaning: "用來觀察一段更長週期的推進方向，幫助你區分只是反彈，還是真正的中期轉強。",
    category: "microstructure",
    color: "#06b6d4",
  },
  vix: {
    name: "VIX 風險溫度",
    shortLabel: "VIX",
    description: "美股波動率指數。",
    meaning: "VIX 升高通常代表全球風險偏好下降，資金更傾向縮減高波動資產部位，對加密幣偏不利。",
    category: "macro",
    color: "#f97316",
  },
  dxy: {
    name: "美元強弱",
    shortLabel: "DXY",
    description: "美元指數。",
    meaning: "美元偏強時，全球流動性通常更緊，加密資產容易承壓；美元回落則常有利風險資產表現。",
    category: "macro",
    color: "#22c55e",
  },
  rsi14: {
    name: "RSI 14",
    shortLabel: "RSI14",
    description: "經典 RSI 動能指標。",
    meaning: "衡量價格最近一段時間的強弱比，適合搭配支撐/壓力判斷是否已進入超買超賣區。",
    category: "technical",
    color: "#eab308",
  },
  macd_hist: {
    name: "MACD 柱狀差",
    shortLabel: "MACD",
    description: "MACD Histogram。",
    meaning: "看趨勢推力是擴張還是收斂，在加密市場常用來分辨反彈是否有延續性。",
    category: "technical",
    color: "#60a5fa",
  },
  atr_pct: {
    name: "ATR 波幅占比",
    shortLabel: "ATR%",
    description: "ATR / 價格。",
    meaning: "代表平均真實波幅相對於價格有多大，可幫助調整止損距離與判斷市場是否過度躁動。",
    category: "technical",
    color: "#f472b6",
  },
  vwap_dev: {
    name: "VWAP 偏離",
    shortLabel: "VWAP",
    description: "價格偏離 VWAP 的幅度。",
    meaning: "接近 VWAP 代表交易更接近當日公平價，偏離太大可能暗示追價成本正在變高。",
    category: "technical",
    color: "#14b8a6",
  },
  bb_pct_b: {
    name: "布林帶位置",
    shortLabel: "BB%B",
    description: "Bollinger Band %B。",
    meaning: "表示目前價格在布林通道中的相對位置，能快速辨識價格貼近上/下緣的程度。",
    category: "technical",
    color: "#c084fc",
  },
  claw: {
    name: "清算壓力",
    shortLabel: "清算",
    description: "多空清算比率。",
    meaning: "觀察高槓桿部位被強平的方向，常用於辨識是否正在出現恐慌踩踏或空頭擠壓。",
    category: "microstructure",
    color: "#ef4444",
  },
  claw_intensity: {
    name: "清算強度",
    shortLabel: "強平強度",
    description: "清算事件強度。",
    meaning: "比單純方向更進一步，衡量被迫平倉的力道是否異常放大。",
    category: "microstructure",
    color: "#fb923c",
  },
  fang_pcr: {
    name: "選擇權 Put/Call",
    shortLabel: "PCR",
    description: "選擇權 Put/Call Ratio。",
    meaning: "偏高常代表避險需求上升，市場更保守；偏低則代表看多情緒較強。",
    category: "macro",
    color: "#6366f1",
  },
  fang_skew: {
    name: "選擇權偏斜",
    shortLabel: "Skew",
    description: "隱含波動率 skew。",
    meaning: "反映市場願意為哪一側保護付更高溢價，對大資金風險情緒很敏感。",
    category: "macro",
    color: "#8b5cf6",
  },
  fin_netflow: {
    name: "ETF 資金流",
    shortLabel: "ETF流",
    description: "ETF netflow。",
    meaning: "代表機構資金是否持續流入或流出，對加密資產的中期趨勢有指標意義。",
    category: "macro",
    color: "#22c55e",
  },
  nq_return_1h: {
    name: "那指 1H 聯動",
    shortLabel: "NQ 1H",
    description: "NASDAQ 100 一小時報酬。",
    meaning: "觀察科技股風險偏好是否同步帶動加密市場，特別適合做跨市場情緒參照。",
    category: "macro",
    color: "#06b6d4",
  },
  "4h_bias50": {
    name: "4H MA50 偏離",
    shortLabel: "4H偏離50",
    description: "4H 價格相對 MA50 的偏離。",
    meaning: "這是你現貨金字塔最重要的框架特徵之一，用來判斷是在健康回調、超跌，還是已經遠離合理區。",
    category: "structure4h",
    color: "#f43f5e",
  },
  "4h_bias20": {
    name: "4H MA20 偏離",
    shortLabel: "4H偏離20",
    description: "4H 價格相對 MA20 的偏離。",
    meaning: "更偏短期的 4H 框架位置，有助於觀察回檔深度是否只是短線波動。",
    category: "structure4h",
    color: "#fb923c",
  },
  "4h_bias200": {
    name: "4H MA200 偏離",
    shortLabel: "4H偏離200",
    description: "4H 價格相對 MA200 的偏離。",
    meaning: "用來辨識更長級別的多空背景，但在現貨策略中通常只拿來當風險濾網。",
    category: "structure4h",
    color: "#a3e635",
  },
  "4h_rsi14": {
    name: "4H RSI",
    shortLabel: "4H RSI",
    description: "4H RSI(14)。",
    meaning: "在較高時間框架判斷趨勢是否進入過熱/過冷區，避免 1 分鐘雜訊誤導進場。",
    category: "structure4h",
    color: "#facc15",
  },
  "4h_macd_hist": {
    name: "4H MACD 柱狀差",
    shortLabel: "4H MACD",
    description: "4H MACD Histogram。",
    meaning: "判斷 4H 級別推力是增強還是衰退，對區分反彈和真正轉勢很有用。",
    category: "structure4h",
    color: "#60a5fa",
  },
  "4h_bb_pct_b": {
    name: "4H 布林帶位置",
    shortLabel: "4H BB%B",
    description: "4H Bollinger %B。",
    meaning: "幫你判斷 4H 價格在波動通道中的相對位置，適合搭配支撐距離使用。",
    category: "structure4h",
    color: "#c084fc",
  },
  "4h_dist_bb_lower": {
    name: "4H 下軌距離",
    shortLabel: "4H下軌",
    description: "距離 4H 布林下軌的百分比。",
    meaning: "越接近下軌，通常越靠近短線壓力釋放後的反彈區，但仍需配合趨勢方向。",
    category: "structure4h",
    color: "#34d399",
  },
  "4h_dist_sl": {
    name: "4H 支撐距離",
    shortLabel: "4H支撐",
    description: "距離最近 4H swing low 的百分比。",
    meaning: "直接告訴使用者離結構支撐還有多遠，對金字塔分批進場尤其重要。",
    category: "structure4h",
    color: "#fb7185",
  },
  "4h_ma_order": {
    name: "4H 均線排列",
    shortLabel: "4H排列",
    description: "4H MA 對齊狀態。",
    meaning: "用來判斷 4H 框架到底是多頭、空頭還是盤整，屬於 regime filter 的核心訊號。",
    category: "structure4h",
    color: "#94a3b8",
  },
  "4h_vol_ratio": {
    name: "4H 相對量能",
    shortLabel: "4H量能",
    description: "4H 成交量 / 20 期平均量。",
    meaning: "高值代表更高時間框架也在放量，有助於分辨支撐反彈是否真的有大級別資金參與。",
    category: "structure4h",
    color: "#fbbf24",
  },
};

/** Helper: map feature name (with or without feat_ prefix) → metadata */
export function getSenseConfig(key: string) {
  if (key in ALL_SENSES) return { key, ...ALL_SENSES[key] };
  const stripped = key.replace("feat_", "");
  if (stripped in ALL_SENSES) return { key: stripped, ...ALL_SENSES[stripped] };
  return {
    key,
    name: key.replace("feat_", "").replace("4h_", "4H ").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
    shortLabel: key.replace("feat_", "").replace("4h_", "4H "),
    description: "",
    meaning: "",
    category: "technical" as FeatureGroupKey,
    color: "#64748b",
  };
}
