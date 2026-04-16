# ISSUES.md — Current State Only

_最後更新：2026-04-16 16:42 UTC_

只保留目前有效問題，不保留舊流水帳。

---

## 目前主線
本輪依 Step 0.5 承接上輪要求，先把 **process-external execution metadata governance 從 install-ready 推進到 installed + verified**。本輪已完成：

1. 依 `preferred_host_lane=user_crontab` 真正安裝 host-level scheduler，`crontab -l | grep 'poly-trader-execution-metadata-external-monitor'` 已可驗證 cron lane 存在。
2. `scripts/execution_metadata_external_monitor_install.py` 新增 **install status 偵測**，會把 `installed / active_lane / checked_at / per-lane verify stdout/stderr` 寫入 contract artifact。
3. `data/execution_metadata_external_monitor_install_contract.json` 與 `data/execution_metadata_external_monitor.json` 已重跑刷新，現在都會帶 `install_status.status=installed`、`active_lane=user_crontab`。
4. `web/src/pages/Dashboard.tsx` stale governance 面板新增 **install status / active lane / install checked at / crontab verify stdout**，不再只顯示「可安裝契約」，而是直接顯示「是否已安裝」。
5. regression tests 與 frontend build 全部重跑通過，證明這輪不是只改文件或只手動裝 cron。

本輪結束後，execution lane 的主缺口已從：
- 「只有 install contract，沒有真正 host-level 安裝」
- 「Dashboard 看得到 install command，但看不到 installed/verified 狀態」

收斂到：
- **P1：目前已安裝的是 `user_crontab` lane，但尚未跨多個 5 分鐘週期驗證它持續自動刷新 artifact。**
- **P1：`SignalBanner` 仍維持快捷 lane；完整 execution governance surface 仍只有 Dashboard。**
- **P1：execution readiness 仍只能宣稱 runtime governance / visibility closure，不得誤寫成 live/canary order-level safe。**

---

## Step 0.5 承接結果
### 上輪文件要求本輪先處理什麼
- 最高優先問題：`host-level install contract 已完成，但 external monitor 尚未真正安裝到主機 scheduler；下一輪先用 install contract 落地並 verify。`
- 上輪指定本輪先做：
  1. 依 `preferred_host_lane` 真正安裝 external monitor scheduler
  2. 用 `install verify` 證明 host-level lane 已存在
  3. 在未升級完整 runtime contract 前，維持 `SignalBanner = 快捷 lane`、`Dashboard = canonical execution route`
- 本輪明確不做：
  - 不擴 live/canary readiness 敘事
  - 不碰 execution 以外的模型 / label / leaderboard side quest
  - 不把 `SignalBanner` 包裝成完整第二 route

### Step 0 gate 四問
1. **現在最大的 P0/P1 是什麼？**
   - 本輪開始時最大的 P1 是：host-level scheduler 尚未真正安裝，導致 external governance 仍停在 install-ready。
2. **上輪明確要求本輪處理的是什麼？**
   - 用 install contract 真的把 scheduler 裝上去，並留下 verify 證據。
3. **本輪要推進哪 1~3 件事？**
   - (a) 安裝 `user_crontab` lane
   - (b) 把 install status 變成 machine-readable artifact
   - (c) 讓 Dashboard 直接顯示 installed / active lane / verify evidence
4. **哪些事本輪明確不做？**
   - live trading readiness 升級、第二 execution route 擴張、execution 以外主題

---

## 本輪事實摘要
### 已改善
- `crontab -l` 在本輪開始前為 `no crontab for kazuha`；本輪安裝後已存在：
  - `*/5 * * * * cd /home/kazuha/Poly-Trader && source venv/bin/activate && python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT --interval-seconds 300 >> /home/kazuha/Poly-Trader/data/execution_metadata_external_monitor.log 2>&1 # poly-trader-execution-metadata-external-monitor`
- `scripts/execution_metadata_external_monitor_install.py`
  - 新增 `install_status={status, installed, active_lane, checked_at, lanes.*}`
  - 直接檢查 `crontab` / `systemctl --user` verify command，將 stdout/stderr 一起落盤
- `data/execution_metadata_external_monitor_install_contract.json`
  - 現在顯示 `install_status.status=installed`
  - `install_status.active_lane=user_crontab`
  - `install_status.lanes.user_crontab.installed=true`
- `data/execution_metadata_external_monitor.json`
  - 已內嵌上述 install status，Dashboard/API 可直接讀取
- `web/src/pages/Dashboard.tsx`
  - stale governance 面板新增：
    - `install status`
    - `active lane`
    - `install checked at`
    - `crontab verify stdout`
- regression tests / build：全部成功

### 驗證證據
- `crontab -l || true`
  - **安裝前**：`no crontab for kazuha`
- `source venv/bin/activate && python scripts/execution_metadata_smoke.py --symbol BTCUSDT`
  - **成功**，`all_ok=true`、`ok_count=2/2`
- `source venv/bin/activate && python scripts/execution_metadata_external_monitor_install.py --symbol BTCUSDT`
  - **成功**，artifact 顯示 `install_status.status=installed`、`active_lane=user_crontab`
- `source venv/bin/activate && python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT`
  - **成功**，artifact 顯示 `status=healthy`、`freshness_status=fresh`
- `crontab -l | grep 'poly-trader-execution-metadata-external-monitor'`
  - **成功**，host-level scheduler 已存在
- `source venv/bin/activate && python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - **19 passed**
- `cd web && npm run build`
  - **成功**

### 卡住不動
- 目前只證明 **scheduler 已安裝**；尚未跨多個 5 分鐘週期驗證它會持續自動刷新 artifact。
- `SignalBanner` 仍不是完整 execution governance surface；目前只保留快捷 lane 定位。
- live/canary order-level readiness 仍未驗證；本輪不碰 exchange credential / order ack / fill lifecycle。

### 本輪未量測（明確不報）
- Raw / Features / Labels row counts
- canonical IC / CV / ROI / target drift
- leaderboard / Strategy Lab 模型主指標

本輪聚焦 execution governance，不對未重跑的模型數字做假更新。

---

## 策略決策紀錄（Step 2）
| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 只保留 install contract，不真正安裝 cron | 改動最小 | external lane 仍停在 install-ready，下一輪還是同一個 blocker | 治標 | 只想保留文件契約 | ❌ 不建議 |
| 直接安裝 `user_crontab` 並用 `crontab -l` 驗證 | 立即完成 host-level lane 落地，符合 preferred lane | 還需補 UI / artifact 的 installed 狀態可視性 | 治本第一步 | crontab 可用、command 已穩定 | ✅ 本輪採用 |
| 直接改走 `systemd --user` | 也能形成 host-level scheduler | 目前 timer 尚不存在，且 preferred lane 已是 user crontab | 治本替代路徑 | crontab 不可用時 | ⏳ 本輪不採用 |
| 只手動裝 cron，不補 artifact / Dashboard installed state | scheduler 有了 | UI/API 仍只看得到 install-ready，不利後續治理 | 治標 | 只追求主機側落地 | ❌ 不建議 |
| 補 install status machine-readable contract + Dashboard 顯示 | operator 可直接知道是否 installed / 哪個 lane 在跑 | 需要 patch + regression | 治本收尾 | 已有 install contract 與 Dashboard governance 面板 | ✅ 本輪採用 |

### 效益前提驗證
- 前提 1：`crontab` 在本機可用 → **成立**
- 前提 2：external monitor script 已可穩定重跑 → **成立**
- 前提 3：Dashboard 已有 stale governance 面板可承接 install status → **成立**
- 前提 4：本輪是否已可宣稱 live/canary order-level ready → **不成立**

---

## 六帽會議摘要
- **白帽**：cron 已安裝；install contract 與 external monitor artifact 已刷新為 `installed/user_crontab`；Dashboard 與 tests 已同步。
- **紅帽**：如果只把 cron 裝上去但不把 installed 狀態顯示出來，下一輪仍可能誤判成 install-ready。
- **黑帽**：scheduler 存在不等於它一定會持續工作；若下一輪不檢查實際 tick 更新，仍可能留下假健康。
- **黃帽**：現在 operator 不必 SSH 後手查 crontab；Dashboard 已能直接看到 install status 與 verify output。
- **綠帽**：本輪可落地 patch 是 install status 偵測 + Dashboard installed state surface。
- **藍帽**：範圍收斂在 host-level 安裝與 installed-state 可視性，不擴張到第二 route 或 live readiness。

---

## ORID 決策
- **O（Objective）**
  - 上輪缺口是 install contract 已有，但 host-level scheduler 尚未真正安裝。
  - 本輪開始前 `crontab -l` 回覆 `no crontab for kazuha`。
  - 本輪已安裝 `user_crontab` lane，並讓 contract artifact / Dashboard 同步顯示 installed state。
- **R（Reflective）**
  - 最大風險已從「沒安裝」轉成「安裝後是否穩定持續執行」與「不要把 governance closure 誤寫成 live-ready」。
- **I（Interpretive）**
  - 根因是前一輪只把 install path 文件化，沒有把『實際安裝狀態』也納入 machine-readable contract 與 UI，因此 operator 難以一眼確認 external lane 是否真的落地。
- **D（Decisional）**
  - `Owner:` Hermes
  - `Action:` 安裝 `user_crontab` scheduler，並讓 install contract / Dashboard 直接顯示 installed + active lane + verify output。
  - `Artifact:` `scripts/execution_metadata_external_monitor_install.py`、`data/execution_metadata_external_monitor_install_contract.json`、`data/execution_metadata_external_monitor.json`、`web/src/pages/Dashboard.tsx`
  - `Verify:` `crontab -l | grep 'poly-trader-execution-metadata-external-monitor'`、`execution_metadata_external_monitor_install.py`、`execution_metadata_external_monitor.py`、`pytest`、`npm run build`
  - `If fail:` 若 cron 無法安裝或 verify 失敗，立即回退為 install-ready，保留 fallback command，並升級為 blocker。

---

## Open Issues

### P1. 需要驗證 scheduler 是否跨週期持續刷新 artifact
**現況**
- `user_crontab` lane 已安裝並可被 `crontab -l` 驗證。
- external monitor artifact 仍是本輪手動即時重跑生成。

**缺口**
- 尚未觀察至少一個自然 cron 週期，確認 `data/execution_metadata_external_monitor.json` / log 會被 scheduler 持續更新。

**風險**
- 若 cron entry 存在但實際執行失敗，Dashboard 仍可能暫時顯示已安裝卻沒有新 tick。

**下一步**
- 下一輪先檢查 artifact `generated_at/checked_at` 與 log 是否在無手動介入下前進。

### P1. SignalBanner 仍是快捷 lane，不是完整 execution governance surface
**現況**
- Dashboard 已是 canonical execution route。
- SignalBanner 仍只提供快捷下單 / 自動交易切換。

**缺口**
- SignalBanner 尚未消費 `/api/status` refresh、guardrail context、metadata governance、install status。

**風險**
- 若未來再次把它描述成完整 execution route，會重新引入 route 假完成。

**下一步**
- 在 host-level scheduler 穩定後，再評估是否值得升級第二 route；否則維持快捷 lane 定位。

### P1. readiness 邊界仍需嚴格守住
**現況**
- 本輪完成的是 runtime governance / visibility closure 的進一步落地。

**缺口**
- 尚未驗證真實 exchange credential、order ack、fill lifecycle、canary/live 安全性。

**風險**
- 若把「scheduler 已安裝」誤寫成 live/canary safe，會造成新的 readiness 假進度。

**下一步**
- 文件與 UI 繼續使用 governance / visibility 語言；只有 order-level 驗證完成後才可升級 readiness 敘事。

---

## 本輪已處理
- 安裝 `user_crontab` external monitor scheduler
- `crontab -l` verify 通過
- install contract 新增 installed-state machine-readable 偵測
- external monitor artifact 內嵌 installed-state 資訊
- Dashboard 顯示 install status / active lane / checked at / crontab verify stdout
- regression tests 19 passed
- web build 成功
- metadata smoke 腳本成功（2/2）
- external monitor 腳本成功（healthy artifact）

---

## Current Priority
1. **P1：驗證 host-level scheduler 是否在自然週期下持續刷新 external monitor artifact / log**
2. **P1：維持 Dashboard 為 canonical execution route；未升級前不要把 SignalBanner 誤當完整 execution surface**
3. **P1：持續守住 readiness 文案邊界，不把 governance installed 誤寫成 live-ready**

---

## Carry-forward（供下一輪 Step 0.5 直接讀入）
- 最高優先問題：`host-level scheduler 已安裝，但仍需驗證它在無手動介入下會持續刷新 external monitor artifact / log。`
- 本輪已完成：`user_crontab scheduler installed + verified、install_status machine-readable contract、Dashboard installed-state surface、pytest 19 passed、web build 成功、execution_metadata_smoke.py 成功、execution_metadata_external_monitor.py healthy。`
- 下一輪必須先處理：`(1) 檢查 external monitor artifact generated_at/checked_at 與 log 是否在自然 cron 週期下前進；(2) 若 SignalBanner 尚未升級完整 runtime contract，維持它是快捷 lane。`
- 成功門檻：`在不手動重跑 external monitor 的情況下，Dashboard / artifact / log 能證明 cron lane 正常產生新 tick；execution route coverage 仍不模糊。`
- 若失敗：`升級為 blocker，文件必須明確標示 scheduler 僅為 installed-not-observed 或 installed-but-not-ticking，禁止宣稱 external governance fully healthy。`
