# ORID 循環 — ORID D 決策行動

> 生成時間：每次心跳自動寫入
> 最後更新：戰略評審（2026-04-10）

---

## 心跳 #648 ORID（2026-04-10 23:36 UTC）

### O 客觀事實
- `python scripts/hb_parallel_runner.py --fast --hb 648` 成功推進 **Raw 20377→20378 / Features 11806→11807 / Labels 40766→40772**，canonical freshness 仍為 `expected_horizon_lag`。
- Canonical diagnostics 維持健康：Global **13/30 PASS**、TW-IC **16/30 PASS**；Regime IC **Bear 7/8 / Bull 6/8 / Chop 5/8 / Neutral 21 rows**（`simulated_pyramid_win`, n=11,029）。
- Source blocker 沒有改善：仍有 **8 blocked sparse features**；`fin_netflow` 仍是 `auth_missing`，Claw / Claw intensity / Fin 仍需要 CoinGlass auth / archive-level 修復。
- 成熟度語義在首頁仍有缺口：Heartbeat #647 雖已讓 FeatureChart 顯示 core / research / blocked，但 Dashboard 雷達與 AdviceCard 還沒同步，首頁主決策區仍可能讓使用者誤把 research / blocked overlay 當成同權主訊號。

### R 感受直覺
- 現在最危險的不是數據鏈路，而是首頁決策卡若沒有把成熟度語義講清楚，會讓「blocked 只是 UI 顯示問題」的錯覺重新回來。
- 若成熟度 contract 只留在 FeatureChart，使用者在最常看的 Dashboard 首屏仍會被混合語義誤導，等同把前幾輪做好的 source blocker 治理又稀釋掉。

### I 意義洞察
1. **#CORE_VS_RESEARCH_SIGNAL_MIXING 的真缺口已縮到首頁主決策區**：後端 policy 與 FeatureChart 已分層，但 Dashboard / AdviceCard 未同步時，使用者決策入口仍可能混淆。
2. **這輪最有價值的 patch 不是再改 IC/模型，而是把既有成熟度 contract 推到真正高曝光的 UI 入口**，避免 sparse-source blocker 被重新包裝成「可直接拿來判斷」。
3. **source blockers 仍是 source-level 問題，不該被 UI patch 假裝解掉**；因此本輪只修語義，不虛報 coverage 有進展。

### D 決策行動
- **Owner:** AI Agent / web dashboard path
- **Action:** 把 `/api/features/coverage` 的 maturity summary 接到 `Dashboard.tsx` 與 `AdviceCard.tsx`，在首頁直接標示 `核心 / 研究 / 阻塞` 計數與使用說明。
- **Artifact:** `web/src/pages/Dashboard.tsx`、`web/src/components/AdviceCard.tsx`、`ISSUES.md`、`ROADMAP.md`、`ARCHITECTURE.md`
- **Verify:** `python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_feature_history_policy.py -q`、`cd web && npm run build`、`python scripts/hb_parallel_runner.py --fast --hb 648`
- **If fail:** 若 Dashboard/AdviceCard 無法穩定消化 coverage payload，下一輪先在 API 回傳專用 maturity summary contract，再重試首頁同步，禁止回退成只在 FeatureChart 顯示成熟度

---

## 戰略評審 ORID（2026-04-10）

### O 客觀事實
- canonical target 已統一到 `simulated_pyramid_win`，raw / features / labels 主鏈路目前健康，Heartbeat #634 顯示 240m / 1440m freshness 皆為 `expected_horizon_lag`。
- 訓練結果已明顯優於早期階段：global **Train 70.25% / CV 72.23% ± 13.64pp**；regime CV 為 **Bear 58.97% / Bull 78.30% / Chop 71.05%**。
- live predictor probe 已確認 canonical 4H features / lag values 非空，但目前 runtime `used_model=circuit_breaker`，表示風控 gate 正主動阻擋交易。
- 仍有 **8 個 sparse-source blockers**；其中 Claw / Claw intensity / Fin 明確卡在 `COINGLASS_API_KEY` / source auth blocker，不屬於前端顯示問題。
- Strategy Lab / leaderboard / chart 已進入可用研究台階段，但 leaderboard 排序、feature 分級、decision semantics 尚未完全對齊「高勝率、低回撤」目標。

### R 感受直覺
- 現在最不安的不是 pipeline 會不會壞，而是「哪些訊號真的可以信、哪些只能研究看」還沒有被制度化。
- 產品已經跨過 demo 階段，若繼續只堆 feature / 模型而不先收斂決策語義，會慢慢變成看起來很強、但很難安心使用的系統。
- 若再讓低成熟度 sparse-source 與核心 4H/technical signals 同權，勝率與回撤會被噪音污染，而不是被真正 alpha 改善。

### I 意義洞察
1. **下一階段的主要瓶頸不再是 target 錯位，而是 decision-quality 尚未顯式建模**：binary win/loss 仍不足以代表高勝率、低回撤、低深套的真偏好。
2. **最有效的勝率/回撤改善不在於再換模型，而在於把決策拆成兩層**：先用 4H 結構判斷能不能做，再用短線訊號決定做得漂不漂亮。
3. **金字塔本身就該是風控器，不只是資金配置器**：若 layer sizing 沒有跟 signal quality 綁定，低品質訊號仍會把回撤放大。
4. **目前真正需要的是核心信號 / 研究信號分級**：4H + 高 coverage technical 應構成主決策；sparse-source 應先作 overlay / veto / 研究，而不是直接同權進主模型。

### D 決策行動
- **Owner:** AI Agent / repo 主線
- **Action:** 把下一階段主軸收斂為三件事：
  1. 兩階段決策（4H regime gate → short-term entry-quality）
  2. decision-quality target（win + pnl_quality + drawdown_penalty + time_underwater）
  3. confidence-based layer sizing + 核心/研究信號分級
- **Artifact:** 更新 `strategy-decision-guide.md`、`ISSUES.md`、`ROADMAP.md`、`ARCHITECTURE.md`
- **Verify:** 文件中必須明確出現上述三條主線，且 roadmap / issues / architecture 對同一方向敘事一致
- **If fail:** 若無法在文件層一致收斂，後續 patch 只能視為局部修補，不得宣稱已決定系統下一階段方向

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
| 🟢 P2 | FeatureETF 自動更新 | 待執行 | 待執行 |
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
