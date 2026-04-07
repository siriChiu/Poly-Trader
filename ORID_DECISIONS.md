# ORID 循環 — ORID D 決策行動

> 生成時間：每次心跳自動寫入
> 最後更新：心跳 #242

---

## 心跳 #242 ORID（2026-04-05）

### O 客觀事實
- **IC (full_ic.py v4, 正確 JOIN)**: Global 4/15 PASS, TW-IC 9/15 PASS
  - ✅ 通過: Eye(+0.137), Ear(-0.053), Nose(-0.028), Tongue(+0.530), Body(+0.510), Pulse(-0.302), Aura(-0.178), Mind(-0.199), VIX(-0.125), DXY(-0.270), RSI14(-0.065), ATR%(+0.443), VWAP(+0.140), BB%B(-0.058)
  - ❌ 失敗: MACD-Hist(-0.035), feat_claw/fin/fang/web/scales/nest: NO_DATA
- **Model**: Train=63.9%, CV=51.4%, gap=12.5pp (n=8917)
- **sell_win**: 49.9% (< 50% → EMERGENCY)
- **losing streak**: 156 (持續)
- **Raw data**: 110 分鐘未更新 → collector 已死
- **新特徵**: 6 個 P0/P1 特徵全部 NO_DATA (Claw, Fang, Fin, Web, Scales, Nest)

### R 感受直覺
- 全域 IC 0/10 的詛咒是 **JOIN bug** 造成的幻覺 — 修復後 4/15 通過
- sell_win < 50% 持續 156 輪，意味著「當前的交易邏輯在當前市場 regime 下根本沒 edge」
- TW-IC 很強 (9/15 PASS) 但僅限近期 200 樣本 — 是 **regime-dependent** 的信號，不是通用模型
- 新特徵 0% 有數據 → collector 完全沒調用這些模組

### I 意義洞察
1. **P0 根因**: 全域 IC 崩潰的根本原因是 `scripts/full_ic.py` 用 positional matching（不是 timestamp JOIN），導致 feature 和 label 配對錯誤
2. **sell_win < 50%**: `threshold_pct=0.05%` 在當前 choppy 市場中把 156 筆微小回報都標為 sell_win=0
3. **TW-IC 9/15 PASS**: 近期信號強，但模型 CV 仍停在 51.4% — CV gap 才是問題
4. **數據停滯**: collector 死了 110 分鐘，heartbeat 跑完但沒收集新數據

### D 決策行動

| 優先級 | 動作 | 負責人 | 狀態 |
|--------|------|--------|------|
| 🔴 P0 | 重啟 main.py collector (確認 apscheduler 正在運行) | AI Agent | 待執行 |
| 🔴 P0 | 修改 labeling.py: threshold 從 0.05% 提升到 0.20% | AI Agent | 待執行 |
| 🔴 P0 | 驗證所有 6 個新特徵的 collector 呼叫 | AI Agent | 待執行 |
| 🟡 P1 | 加入 data collection 監控 (每 5 分檢查 Δ_raw) | ✅ 已寫入 runner | 完成 |
| 🟡 P1 | 加入 IC null_count / ic_status 到 ic_signs.json | ✅ 已寫入 | 完成 |
| 🟡 P1 | 加入 auto_propose_fixes 自動修復提案 | ✅ 已寫入 | 完成 |
| 🟡 P1 | 加入 backtest 到平行 runner | ✅ 已寫入 | 完成 |
| 🟢 P2 | 加入 hb_metrics.csv 趨勢追蹤 | ✅ 已寫入 | 完成 |
| 🟢 P2 | SensoryETF 自動更新 | 待執行 | 待執行 |
| 🟢 P2 | issues.json 結構化 tracker | ✅ 已寫入 | 完成 |

---

## 本輪心跳完成的修復

| 修復 | 文件 | 說明 |
|------|------|------|
| P0#1 | hb_parallel_runner.py | Data freshness 監控 (age, Δ_raw, alerts) |
| P0#2 | model/train.py + full_ic.py | null_count + ic_status (NO_DATA / LOW / PASS / FAIL) |
| P0#3 | full_ic.py v4 | 正確 INNER JOIN on timestamp+symbol (非 positional) |
| P0#3 | model/train.py | TW-IC 修正: non_null_before 在 fillna 之前計算 |
| P1#4 | hb_parallel_runner.py | 回測任務加入並行執行 |
| P1#5 | hb_parallel_runner.py | API endpoint 自動檢查 |
| P1#6 | scripts/issues.py | 結構化 IssueTracker (JSON, auto-markdown) |
| P1#7 | scripts/auto_propose_fixes.py | 基於規則的自動修復提案 |
| P2#8 | model/train.py | ic_signs.json 包含 ic_status |
| P2#9 | hb_parallel_runner.py | hb_metrics.csv 趨勢追蹤 |
