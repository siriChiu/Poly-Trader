# ISSUES.md — Current State Only

_最後更新：2026-04-16 16:21 UTC_

只保留目前有效問題，不保留舊流水帳。

---

## 目前主線
本輪依 Step 0.5 承接上輪要求，優先把 **process-external metadata governance 從「可手動重跑 script」推進到「可安裝的 host-level install / fallback contract」**，並同時收斂第二 execution route 的歧義：本輪**不擴 `SignalBanner` 成第二條 runtime governance route**，而是正式把 **Dashboard 定義為 canonical execution route**，避免半套 UI 被誤認為已具備完整 guardrail / stale governance 能力。

本輪已完成的閉環：
1. `scripts/execution_metadata_external_monitor_install.py` 新增 **host-level install contract generator**，可輸出 `user_crontab / systemd --user / fallback` 的 machine-readable 安裝與驗證契約。
2. `scripts/execution_metadata_external_monitor.py` 產出的 artifact 現在會內嵌 `install_contract`；`data/execution_metadata_external_monitor.json` 與 `data/execution_metadata_external_monitor_install_contract.json` 都已在本輪重跑刷新。
3. `server/routes/api.py` 現在會把 `external_monitor.install_contract` 併入 `/api/status` governance contract，Dashboard 可直接讀到 install / verify / fallback 資訊。
4. `web/src/pages/Dashboard.tsx` stale governance 面板新增 **preferred host lane / install command / install verify / fallback command / systemd timer** 顯示；operator 不必翻 repo 才能看到部署契約。
5. `web/src/components/SignalBanner.tsx` 明確標示：它目前只提供快捷下單 / automation toggle，**完整 execution status / guardrail context / stale governance 仍以 Dashboard 為 canonical execution route**。
6. regression tests、smoke、external monitor、frontend build 全部重跑通過，證明本輪不是只寫文件。

目前 execution lane 的主缺口已從：
- 「external monitor 只有 script，沒有 host-level install/fallback contract」
- 「SignalBanner 是否算第二 execution route 不清楚」

收斂到：
- **P1：repo 內已有 install contract，但本機 host-level scheduler 尚未真正安裝啟用；目前完成的是『可安裝契約』，不是『已安裝狀態』。**
- **P1：Dashboard canonical route 已定義，但 `SignalBanner` 仍未升級為完整 runtime governance surface；若未來要做第二 route，必須遵守與 Dashboard 相同 contract。**
- **P1：execution readiness 仍只能宣稱 governance / visibility 改善，不得誤寫成 live/canary order-level safe。**

---

## Step 0.5 承接結果
### 上輪文件要求本輪先處理什麼
- 最高優先問題：`process-external execution metadata governance lane 已落地，但仍缺 host-level scheduler / pager installer；下一輪先把安裝/部署契約收斂清楚，避免 external lane 只停在可手動重跑。`
- 上輪指定本輪先做：
  1. 把 external monitor 從 **可重跑 script** 升級成 **host-level scheduler / pager install contract**
  2. 決定 `SignalBanner` 是否升級成第二個 execution operator-facing route；若不升級，就正式文件化 Dashboard 是唯一 canonical route
- 本輪明確不做：
  - 不擴 live/canary readiness 敘事
  - 不碰 execution 以外的模型 / label / leaderboard side quest
  - 不在治理閉環未完成前轉去做 UI 美化

### Step 0 gate 四問
1. **現在最大的 P0/P1 是什麼？**
   - 本輪開始時最大的 P1 是：external monitor 仍缺 host-level install/fallback contract，且 execution route coverage 仍有歧義。
2. **上輪明確要求本輪處理的是什麼？**
   - 先把 external monitor 安裝契約做實，再收斂 `SignalBanner` / Dashboard 的 route 真相。
3. **本輪要推進哪 1~3 件事？**
   - (a) 落地 external monitor install contract generator 與 artifact
   - (b) 把 install contract 掛回 `/api/status` / Dashboard governance surface
   - (c) 正式標示 Dashboard 是 canonical execution route，避免 `SignalBanner` 假完成
4. **哪些事本輪明確不做？**
   - live/canary readiness 升級、execution 以外主題、把 `SignalBanner` 包裝成已完整接線的第二 route

---

## 本輪事實摘要
### 已改善
- `scripts/execution_metadata_external_monitor_install.py`
  - 新增 **host-level install contract generator**。
  - 產出 `data/execution_metadata_external_monitor_install_contract.json`，包含：
    - `preferred_host_lane=user_crontab`
    - `user_crontab.schedule/install_command/verify_command`
    - `systemd_user.service_file/timer_file/install_steps/verify_command`
    - `fallback.command/verify_command`
- `scripts/execution_metadata_external_monitor.py`
  - 現在會把 `install_contract` 內嵌到 external monitor artifact。
- `server/routes/api.py`
  - `/api/status` governance 的 `external_monitor` 現在帶 `install_contract`。
- `web/src/pages/Dashboard.tsx`
  - stale governance 面板新增：
    - `preferred host lane`
    - `install command`
    - `install verify`
    - `fallback contract`
    - `fallback command`
    - `systemd user timer`
- `web/src/components/SignalBanner.tsx`
  - 正式聲明它不是完整 execution governance route；Dashboard 才是 canonical route。
- `tests/test_server_startup.py`
  - 新增 external monitor install contract 載入與 governance contract regression checks。
- `tests/test_frontend_decision_contract.py`
  - 新增 Dashboard install contract surface 與 SignalBanner canonical-route 提示的 regression checks。

### 驗證證據
- `source venv/bin/activate && python scripts/execution_metadata_smoke.py --symbol BTCUSDT`
  - **成功**
  - `data/execution_metadata_smoke.json` 更新為 `2026-04-16T16:20:47.252496Z`
  - `ok_count=2/2`、`all_ok=true`
- `source venv/bin/activate && python scripts/execution_metadata_external_monitor_install.py --symbol BTCUSDT`
  - **成功**
  - `data/execution_metadata_external_monitor_install_contract.json` 已生成，`preferred_host_lane=user_crontab`
- `source venv/bin/activate && python scripts/execution_metadata_external_monitor.py --symbol BTCUSDT`
  - **成功**
  - `data/execution_metadata_external_monitor.json` 更新為 `2026-04-16T16:20:15.594483Z`
  - `status=healthy`、`freshness_status=fresh`、`governance_status=healthy`
  - artifact 已帶 `install_contract`
- `source venv/bin/activate && python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - **19 passed**
- `cd web && npm run build`
  - **成功**

### 卡住不動
- host-level scheduler / pager **尚未真正安裝到主機環境**；本輪完成的是 install/fallback contract，不是已啟用狀態。
- `SignalBanner` 仍不是完整 execution governance surface；目前只解了「不要再把它誤認成完整 route」，還沒有把它升級成 `/api/status + guardrails + stale governance` 消費者。
- readiness 邊界仍需持續守住：本輪只把 install contract 與 route 真相收斂清楚，不是 live/canary order-level readiness。

### 本輪未量測（明確不報）
- Raw / Features / Labels row counts
- canonical IC / CV / ROI / target drift
- leaderboard / Strategy Lab 模型主指標

本輪聚焦 execution governance，不對未重跑的模型數字做假更新。

---

## 策略決策紀錄（Step 2）
| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 繼續只保留 external monitor script | 改動最小 | host-level 安裝路徑仍模糊，operator 無法直接採用 | 治標 | 只想證明 script 能跑 | ❌ 不建議 |
| 新增 install contract generator + artifact，讓 `/api/status` / Dashboard 直接顯示 install / verify / fallback | 把部署責任邊界 machine-readable 化；適合下一輪直接安裝 | 還沒真的寫入 crontab/systemd | **治本第一步** | 已有穩定 external monitor script 與 artifact contract | ✅ 本輪採用 |
| 直接在本輪硬裝 host-level cron/systemd | 最接近「真的啟用」 | 在 cron job 環境直接改 host config 風險較高，且未先留下明確 contract 容易變黑盒 | 治本第二步 | install contract 已先收斂 | ⏳ 下一輪採用 |
| 直接把 `SignalBanner` 升級成第二 execution route | 可擴 route coverage | 會分散主題；本輪最大 blocker 仍是 install contract 缺失與 route 歧義 | 治標 | host-level contract 已穩定後 | ❌ 本輪不採用 |
| 正式把 Dashboard 定義為 canonical execution route，SignalBanner 維持快捷 lane | 立即消除 route 歧義，避免假完成 | 第二 route 仍待未來升級 | **治本的語義收斂** | `SignalBanner` 尚未具備完整 runtime context | ✅ 本輪採用 |

### 效益前提驗證
- 前提 1：external monitor script 已穩定可重跑，適合作為 install contract 的核心 command → **成立**
- 前提 2：Dashboard 已有 stale governance 面板可承接 install/fallback 資訊 → **成立**
- 前提 3：先把 Dashboard / SignalBanner 的角色邊界說清楚，再談第二 route 升級，比硬塞更多 UI 更容易驗證 → **成立**
- 前提 4：本輪是否已足以宣稱 host-level scheduler 已完成安裝 → **不成立**

---

## 六帽會議摘要
- **白帽**：新增 install contract generator、external monitor artifact 內嵌 contract、`/api/status` / Dashboard 顯示 install/fallback、SignalBanner 顯示 canonical route 提示；smoke / external monitor / pytest / build 全部成功。
- **紅帽**：若只說「未來可以裝 cron/systemd」但不留下可執行 install command，仍是假進度；因此本輪強制把安裝路徑與 verify command 落成 artifact。
- **黑帽**：若下一輪不真的安裝 host-level scheduler，external lane 仍停留在 repo 內治理，不是主機層持續治理。
- **黃帽**：現在 operator 已能從 Dashboard 直接讀到 preferred lane、cron install/verify、systemd timer 路徑與 fallback command，後續實裝不再需要重新找文檔。
- **綠帽**：本輪可落地 patch 是 install contract generator + API/Dashboard surface + SignalBanner canonical-route 提示。
- **藍帽**：本輪範圍收斂到 install contract 與 route 收斂，不擴到 live readiness 或第二 route 全量接線。

---

## ORID 決策
- **O（Objective）**
  - 上輪已完成 external monitor script，但缺 host-level install/fallback contract。
  - `SignalBanner` 仍只有 `/api/trade` / automation toggle，無 `/api/status` refresh、無 guardrail context、無 stale governance。
  - 本輪新增 install contract generator，並把 contract 帶入 artifact / API / Dashboard。
- **R（Reflective）**
  - 最大風險不再是「完全沒有 host-level 路徑」，而是「已有 install contract，但尚未真正安裝」，以及「若不明講 Dashboard 才是 canonical route，團隊仍可能誤判 `SignalBanner` 已經完整」。
- **I（Interpretive）**
  - 根因是上一輪 external monitor 只解了 process-external execution lane，沒有把部署與 route 邊界也變成可執行契約。
- **D（Decisional）**
  - `Owner:` Hermes
  - `Action:` 落地 external monitor install contract generator，把 contract 併入 `/api/status` / Dashboard，並正式宣告 Dashboard 是 canonical execution route。
  - `Artifact:` `scripts/execution_metadata_external_monitor_install.py`、`data/execution_metadata_external_monitor_install_contract.json`、`data/execution_metadata_external_monitor.json`、`server/routes/api.py`、`web/src/pages/Dashboard.tsx`、`web/src/components/SignalBanner.tsx`
  - `Verify:` `execution_metadata_smoke.py`、`execution_metadata_external_monitor_install.py`、`execution_metadata_external_monitor.py`、`pytest`、`npm run build`
  - `If fail:` 若 install contract 無法穩定生成或 Dashboard 仍看不到 install/fallback 資訊，升級為 blocker，禁止再宣稱 external governance 已完整。

---

## Open Issues

### P1. host-level scheduler 尚未真正安裝
**現況**
- repo 內已有 `scripts/execution_metadata_external_monitor_install.py` 與 `data/execution_metadata_external_monitor_install_contract.json`。
- `external_monitor.install_contract` 已能透過 `/api/status` 與 Dashboard 看到。

**缺口**
- 本機 crontab / systemd timer 尚未真正啟用；目前仍屬於 install-ready，而非 installed。

**風險**
- 若把 install-ready 誤寫成 installed，就會形成新的治理假進度。

**下一步**
- 依 contract 選定主路徑（優先 `user_crontab`），在主機上真正安裝並用 verify command 驗證。

### P1. SignalBanner 尚未升級成完整第二 execution route
**現況**
- 本輪已正式標示：Dashboard 是 canonical execution route；SignalBanner 只屬快捷 lane。

**缺口**
- SignalBanner 仍未消費 `/api/status` refresh、guardrail context、metadata governance、install/fallback contract。

**風險**
- 若未來又把它當成完整 execution surface，會重新引入 route 假完成。

**下一步**
- 只有在 host-level scheduler 真正裝好後，才評估是否值得把 SignalBanner 升級成第二 route；否則維持快捷 lane 定位。

### P1. execution readiness 邊界仍要持續守住
**現況**
- 本輪修的是 metadata governance install contract + route 真相。

**缺口**
- 尚未驗證真實 exchange credential、order ack、fill lifecycle、canary/live safety。

**風險**
- 若把本輪結果誤寫成 live/canary safe，會形成 readiness 假進度。

**下一步**
- 文件持續使用「runtime governance / visibility closure」語義；只有 order-level 驗證完成後才可升級 readiness 語言。

---

## 本輪已處理
- external monitor host-level install contract generator 落地
- install contract artifact 落地並重跑
- external monitor artifact 內嵌 install contract
- `/api/status` governance 新增 `external_monitor.install_contract`
- Dashboard stale governance 面板顯示 install / verify / fallback / systemd timer
- SignalBanner 正式標示 Dashboard 為 canonical execution route
- regression tests 19 passed
- web build 成功
- metadata smoke 腳本成功（2/2）
- external monitor 腳本成功（healthy artifact）

---

## Current Priority
1. **P1：依 install contract 真正完成 host-level scheduler 安裝與 verify**
2. **P1：維持 Dashboard 為 canonical execution route；未升級前不要把 SignalBanner 誤當完整 execution surface**
3. **P1：持續守住 readiness 文案邊界，不把 install-ready 誤寫成 live-ready**

---

## Carry-forward（供下一輪 Step 0.5 直接讀入）
- 最高優先問題：`host-level install contract 已完成，但 external monitor 尚未真正安裝到主機 scheduler；下一輪先用 install contract 落地並 verify。`
- 本輪已完成：`scripts/execution_metadata_external_monitor_install.py、data/execution_metadata_external_monitor_install_contract.json、external_monitor.install_contract API/Dashboard surface、SignalBanner canonical-route 提示、pytest 19 passed、web build 成功、execution_metadata_smoke.py 2/2 成功、execution_metadata_external_monitor.py healthy。`
- 下一輪必須先處理：`(1) 依 preferred host lane 安裝並驗證 external monitor scheduler；(2) 若不升級 SignalBanner，就維持它是快捷 lane，不可再把它描述成完整 execution route。`
- 成功門檻：`Dashboard 顯示的 install contract 已被真正採用，verify command 可證明 host-level scheduler 存在；execution route coverage 不再模糊。`
- 若失敗：`升級為 blocker，文件必須明確標示 external governance 仍停在 install-ready、尚未 installed；禁止宣稱 execution readiness 已完成。`
