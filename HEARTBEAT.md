# HEARTBEAT.md — Poly-Trader Productization Charter

> 核心參考：`ISSUES.md`、`ROADMAP.md`、`issues.json`、`ARCHITECTURE.md`、`README.md`

---

## 0. 心跳唯一目的
**心跳唯一目的：把 Poly-Trader 往可運營、可驗證、可產品化的 P0/P1 主線推進。**

若本輪沒有帶來以下任一項，視為不合格：
- code / runtime / UI patch
- 可重跑驗證證據
- `ISSUES.md / ROADMAP.md / issues.json` 的 current-state overwrite sync
- commit + push 到 git remote（若失敗，必須明記 blocker）

---

## 本輪產品化事實摘要 (Heartbeat #1054)
- 數據收集管線恢復正常：+1 raw, +1 features, +0 labels (Raw=32331, Features=23749, Labels=65285)
- 完成 regime labels 補齊：所有 23749 筆 features 具備 regime labels
- 模型訓練完成：Global model Train=67.3%, CV=54.6% ± 3.27%
- 全面驗證通過：6/6 測試全部通過（檔案結構、語法、模組導入、特徵引擎、前端 TypeScript、數據品質）
- 自動化文件同步：ISSUES.md、ROADMAP.md、ORID_DECISIONS.md 已 overwrite sync 為 current state
- 生成 heartbeat summary：data/heartbeat_1054_summary.json
- 更新 issues.json：包含 P0 與 P1 問題的機器可讀追蹤

## 六帽摘要
- 白帽 (事實)：數據增長+1/+1/+0，CV=54.6%，最近 100 筆 win_rate=91.00%，熔斷器未激活（streak=0，recent_win_rate=91.00% > 30% 門檻）
- 紅帽 (感覺)：系統顯示出極強近期信號強度（TW-IC 27/30 通過）且長期穩定性良好，Global IC 16/30 顯示基礎訊號存在
- 黑帽 (批判)：主要阻塞點仍為 current live bucket exact support 不足（42/50），需要補滿 minimum 50 rows 才能解除部署阻塞
- 黃帽 (利益)：TW-IC 顯示近期信號極強（27/30 通過），N=100 動態窗口 8/8 通過， regime-aware IC 在 chop regime 達 5/8 通過
- 綠帽 (創意)：考慮 regime-gated feature weighting 來利用近期信號強度；探索縮短特徵窗口以捕捉 N=100 的極強信號
- 藍帽 (控制)：優先解決 P0 current live bucket exact support 問題；保持文件 current-state 同步；下一輪聚焦在 exact support 積累至 50 rows

## ORID 決策
- O (客觀)：當前狀態顯示 `deployment_blocker=under_minimum_exact_live_structure_bucket`，current live bucket BLOCK|bull_high_bias200_overheat_block|q35 exact support=42/50，gap=8
- R (反應)：系統處於待部署狀態，近期信號極強但受 exact support 限制無法轉換為交易機會
- I (解釋)：部署阻塞機制設計用來確保只有當 exact live structure bucket 達成 minimum 支持門檻時才允許交易，當前觸發原因是 exact support 仍未達標
- D (決定)：優先監控並等待 exact support 自然積累（達成 50/50）；同時確認近期信號強度是否穩定，準備好在解除後立即驗證交易恢復

## Patch 清單
1. 自動 overwrite sync ISSUES.md、ROADMAP.md、ORID_DECISIONS.md (由 hb_parallel_runner.py v5 完成)
2. 生成 data/heartbeat_1054_summary.json
3. 更新 issues.json 當前狀態
4. 無代碼修改（本輪聚焦在診斷與文件同步）

## 驗證證據
- 測試結果：6/6 全通過 (見 terminal 輸出 \"總計: 6/6 通過\")
- 數據品質測試：所有特徵標準差 > 0，唯一值充足
- 前端 TypeScript 編譯：通過
- 模組導入測試：所有 8 個核心模組成功載入
- 檔案結構檢查：所有 21 個必要文件存在

## 文件覆蓋更新確認
- ISSUES.md：已 overwrite 為 current state (最後更新：2026-04-27 03:30:02 CST)
- ROADMAP.md：已 overwrite 為 current state
- ORID_DECISIONS.md：已 overwrite 為 current state
- HEARTBEAT.md：本文件已更新為 current state
- issues.json：已更新為機器可讀當前狀態

## 下一輪 gate
1. **主要目標**：監控 current live bucket exact support 積累至 minimum 50 rows (目前 42/50)
   - 驗證方式：透過 hb_predict_probe.py 檢查 deployment_blocker 變為 false
   - 失敗升級：若連續 3 次心跳 exact support 無增長，升級為 P0 blocker 需要主動介入方案（如檢查數據收集管線是否正常向該 bucket 貢獻 rows）
2. **次要目標**：驗證近期信號強度 (TW-IC) 是否可轉換為實際交易勝率提升
   - 驗證方式：比較 exact support 達標前後的 simulated_pyramid_win 趨勢
   - 失敗升級：若 exact support 達標後勝率未顯著改善，啟動 regime-gated feature weighting 調研
3. **文件目標**：保持 current-state 文件同步自動化（無需人工干預）
   - 驗證方式：檢查 ISSUES.md 時間戳是否晚於心跳執行時間
   - 失敗升級：若自動同步失敗 2 次，檢查 hb_parallel_runner.py v5 的 auto_propose_fixes 文件寫入權限