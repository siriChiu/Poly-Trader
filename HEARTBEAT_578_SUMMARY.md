# Poly-Trader 心跳 #578 — 2026-04-07 16:00 UTC

## 📊 Data Pipeline
- **Raw**: 9,885 (+5🟢 vs #577 9,880)
- **Features**: 9,844 (+5🟢 vs #577 9,839)
- **Labels**: 18,052 (➡️持平)
- **sell_win**: 40.37% (➡️持平，regime子集49.24% n=8770)

## 🎯 Global IC Analysis (22 features expanded)
- **Global IC**: 5/22 passing (➡️持平)
  - PASS: VIX +0.0714, RSI14 +0.0542, MACDHist +0.0505, BB%B +0.0575, Nose +0.0500
- **TW-IC (tau=200)**: 13/22 passing (🟢維持歷史新高持平)
  - PASS: Nose+0.0587, Pulse-0.0871, AURA+0.0799, Mind+0.0750, VIX+0.0876, RSI14+0.0746, MACD+0.0554, ATR%-0.1280, VWAP+0.1293, BB%B+0.0826, 4h_bias50+0.0715, 4h_rsi14+0.0622, 4h_dist_swing_low+0.0620
  - FAIL: Eye, Ear, Tongue, Body, DXY + 4H features (bias20, macd_hist, bb_pct_b, ma_order)

## 📐 Dynamic Window Analysis
- **N=100**: 7/8🟢 (eye+0.089, nose+0.177, tongue-0.115, body+0.129, pulse-0.081, aura+0.277, mind+0.230)
- **N=200**: 7/8🟢 (eye+0.050, nose+0.114, tongue-0.082, body+0.062, pulse-0.131, aura+0.162, mind+0.167)
- **N=400**: 3/8 (Pulse, Aura, Mind)
- **N=600**: 0/8 🔴 (持續死區)
- **N=1000**: 4/8 (Eye, Pulse, Aura, Mind)

## 🏛️ Regime-Aware IC
- **Bear**: 4/8 (Ear+0.0785, Nose+0.0727, Body+0.0682, Aura+0.0544)
- **Bull**: 0/8🔴 (200+輪持續！)
- **Chop**: 0/8🔴 (200+輪持續！)
- sell_win by Regime: Bear=48.55%, Bull=50.90%, Chop=48.29%

## 🧠 Model Training
- **Global**: Train=63.92%, CV=51.39%±3.66%, gap=12.53pp (➡️持平)
- **Features**: 73, **Samples**: 9,106 (Positive ratio: 30.45%)
- **Regime models**: bear/bull/chop 各98 features saved
- **train.py**: ✅ 完整成功（3 regimes saved）

## 📈 Live Market Data
- **BTC**: $68,656 (⬇️ -$11 vs #577 $68,667)
- **FNG**: 11 (持續極度恐懼)
- **FR**: 0.00003731 (⬇️ -1.3% vs #577 0.00003778)
- **LSR**: 1.2523 (⬆️ +11bps vs #577 1.2512)
- **OI**: 91,084 (⬆️ +2 vs #577 91,082)

## ✅ Tests & Execution
- **Tests**: 6/6 PASS (檔案結構、語法9978文件、模組8/8引入、感官引擎、TypeScript、數據品質)
- **平行心跳**: 5/5 PASS (32.2s) — full_ic, regime_ic, dynamic_window, train, tests 全部通過

## 🔍 關鍵觀察
1. **數據持續增長**：Raw +5, Features +5（管線正常運行）
2. **模型指標全面持平**：CV 51.39%, gap 12.53pp, TW-IC 13/22（系統穩定）
3. **FR 微降至 0.00003731**（-1.3%）：資金費率維持正區間但邊際下降
4. **LSR 微升至 1.2523**（+11bps）：多頭長倉比例微增
5. **BTC 微降至 $68,656**（-$11）：價格小幅回調
6. **Bull/Chop 0/8 持續 200+輪**：結構性問題仍未解決

## 📝 Actions
- 繼續監控數據管線增長情況
- Bull/Chop 0/8 持續200+輪，需新數據源突破
- 系統整體穩定，無緊急問題
