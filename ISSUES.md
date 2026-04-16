# ISSUES.md — Current State Only

_最後更新：2026-04-16 18:06 UTC_

只保留目前有效問題，不保留舊流水帳。

---

## 目前主線
本輪依 Step 0.5 承接上輪要求，先確認 **Dashboard 仍是 canonical execution route、SignalBanner 仍是 shortcut lane、governance closure 仍不等於 live-ready** 是否真的持續存在於 runtime，而不是只留在舊文件與舊測試記憶裡。這輪不擴第二條 execution route；只做兩件事：
1. 直接用 `/api/status` 驗證 route contract 與 external monitor ticking-state 仍在 runtime 中成立。
2. 把先前沒有被 regression test 鎖住的 contract 細節（canonical surface label、shortcut status/message、upgrade prerequisite、operator message、live blockers）補進測試，避免之後被靜默回退。

### 本輪已完成的 root-cause closure
1. 實際查驗 `http://127.0.0.1:8000/api/status`，確認：
   - `execution_surface_contract.canonical_execution_route = dashboard`
   - `execution_surface_contract.canonical_surface_label = Dashboard / Execution 狀態面板`
   - `execution_surface_contract.shortcut_surface.role = shortcut-only`
   - `execution_surface_contract.shortcut_surface.status = not-upgraded`
   - `execution_surface_contract.readiness_scope = runtime_governance_visibility_only`
   - `execution_surface_contract.live_ready = false`
2. 實際查驗 `/api/status.execution_metadata_smoke.governance.external_monitor.ticking_state`，確認 host scheduler 仍在自然 ticking：
   - `ticking_state.status = observed-ticking`
   - `active_lane = user_crontab`
   - freshness 仍在 policy 內。
3. 補強 regression lock：
   - `tests/test_server_startup.py` 現在直接斷言 `canonical_surface_label / shortcut status / shortcut message / upgrade_prerequisite / readiness_scope / operator_message / live_ready_blockers`。
   - `tests/test_frontend_decision_contract.py` 現在直接鎖住 Dashboard source 仍保留 `canonical surface / shortcut message / upgrade prerequisite / operator_message` 等 execution route contract 顯示。

---

## Step 0.5 承接結果
### 上輪文件要求本輪先處理什麼
- 最高優先問題：`execution_surface_contract 已落地，但下一輪必須先確認 /api/status 與 Dashboard 是否仍穩定顯示 canonical route / shortcut lane / live_ready=false，禁止任何 surface 把這層 closure 誤寫成 live-ready。`
- 上輪指定本輪先做：
  1. 驗證 route contract 仍穩定存在
  2. 若考慮擴 SignalBanner，必須先補同一份 runtime contract
  3. 繼續禁止把 governance closure 誤寫成 live / canary safe
- 本輪明確不做：
  - live exchange credential / order ack / fill lifecycle 驗證
  - execution 以外的模型 / leaderboard / label side quest
  - 把 SignalBanner 升級成完整 execution governance surface

### Step 0 gate 四問
1. **現在最大的 P0/P1 是什麼？**
   - 本輪開始時最大的 P1 是：route contract 雖然還在，但關鍵欄位沒有完整 regression lock，未來可能被 source 或 API 小改動靜默沖淡。
2. **上輪明確要求本輪處理的是什麼？**
   - 先確認 runtime contract 沒退化，再把缺少的 contract 細節補進測試守門。
3. **本輪要推進哪 1~3 件事？**
   - (a) 直接讀 `/api/status` 驗證 execution route contract
   - (b) 直接讀 `/api/status` 驗證 external monitor ticking-state
   - (c) 補強 regression tests，鎖住 route contract 細節
4. **哪些事本輪明確不做？**
   - 第二 execution route 擴張、live-ready 敘事升級、execution 以外議題

---

## 本輪事實摘要
### 已改善
- `/api/status` 仍實際回傳完整 `execution_surface_contract`，不只是測試或文件假設。
- `/api/status.execution_metadata_smoke.governance.external_monitor.ticking_state` 仍是 `observed-ticking`，表示 host scheduler 路徑沒有退回人工判讀。
- route contract 的關鍵細節現在已被 regression tests 明確鎖住，未來若有人刪掉 canonical surface / upgrade prerequisite / live blockers / operator message，測試會直接失敗。

### 驗證證據
- `source venv/bin/activate && python -m pytest tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
  - **20 passed**
- `source venv/bin/activate && python -m py_compile tests/test_server_startup.py tests/test_frontend_decision_contract.py`
  - **成功**
- `http://127.0.0.1:8000/api/status` 實際回傳：
  - `execution_surface_contract.canonical_execution_route = dashboard`
  - `execution_surface_contract.canonical_surface_label = Dashboard / Execution 狀態面板`
  - `execution_surface_contract.shortcut_surface.status = not-upgraded`
  - `execution_surface_contract.shortcut_surface.upgrade_prerequisite` 存在
  - `execution_surface_contract.operator_message` 存在
  - `execution_surface_contract.live_ready_blockers = [credential, order ack, fill lifecycle]`
  - `execution_metadata_smoke.governance.external_monitor.ticking_state.status = observed-ticking`

### 卡住不動
- SignalBanner 仍未消費 `/api/status` 的 `ticking_state / stale governance / guardrail context / install_contract`；它仍只是 shortcut lane。這仍是刻意保留的邊界，不是本輪要解的缺口。
- readiness 邊界依舊停在 governance / visibility closure；仍沒有 live credential、order ack、fill lifecycle 的 order-level 驗證。
- 本輪沒有做 Dashboard 實際瀏覽器截圖驗證；目前靠 runtime API + source/test lock 守住 contract。

### 本輪未量測（明確不報）
- Raw / Features / Labels row counts
- canonical IC / CV / ROI / drift
- leaderboard / Strategy Lab 指標

本輪聚焦 execution route governance contract，不對未重跑的模型面數字做假更新。

---

## 策略決策紀錄（Step 2）
| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 只做一次 `/api/status` smoke check，不補測試 | 立刻知道 runtime 還活著 | 下輪仍可能被靜默回退 | 治標 | 只想臨時確認狀態 | ❌ 不建議 |
| 直接升級 SignalBanner 成第二 execution route | 表面上 coverage 變多 | 會跳過既有邊界，重新引入 route 假完成 | 治標（治本需先補同一份 runtime contract） | 已完整消費 `/api/status` contract 時 | ❌ 不建議 |
| 先做 runtime 驗證，再補關鍵 contract regression lock | 同時處理「現在有沒有退化」與「之後會不會靜默退化」 | 只強化 governance，不會直接帶來 live readiness | 治本 | Dashboard 仍是 canonical route | ✅ 本輪採用 |

### 效益前提驗證
- 前提 1：`/api/status` 仍是所有 execution surface 的共同入口 → **成立**
- 前提 2：SignalBanner 現階段仍不該升級成完整 execution route → **成立**
- 前提 3：補測試可以實際降低 contract drift 風險 → **成立**
- 前提 4：本輪 closure 是否等於 live/canary ready → **不成立**

---

## 六帽會議摘要
- **白帽**：runtime API 回傳完整 execution route contract；external monitor ticking-state 也是 `observed-ticking`；20 個 targeted tests 通過。
- **紅帽**：最令人不安的是 contract 雖然存在，但若沒被測試守住，很容易又被 UI/API 細改靜默沖淡。
- **黑帽**：如果下一輪有人只看 `live_ready=false` 還不足夠，卻把 `canonical surface / shortcut status / upgrade prerequisite / operator message` 刪掉，route split 仍會退回人工腦補。
- **黃帽**：本輪 patch 雖小，但它把 runtime contract 的細節正式變成守門條件，比只寫文件更穩。
- **綠帽**：最佳 patch 是補 server + frontend regression tests，把 route contract 關鍵欄位直接鎖住。
- **藍帽**：本輪只守住 route split / readiness boundary；不擴第二 route，不碰 live order readiness。

---

## ORID 決策
- **O（Objective）**
  - `/api/status` 仍回傳 `execution_surface_contract`。
  - `external_monitor.ticking_state.status = observed-ticking`。
  - 先前測試未完整涵蓋 `canonical_surface_label / shortcut status / message / upgrade prerequisite / operator message / blockers`。
  - 本輪補強測試後，`pytest` 20 passed。
- **R（Reflective）**
  - 風險不在於 contract 消失，而在於「看起來還在、其實細節已退化」的靜默漂移。
- **I（Interpretive）**
  - 根因是 route contract 細節尚未被完整鎖進 regression guard，導致上輪 closure 仍部分依賴人類記憶。
- **D（Decisional）**
  - `Owner:` Hermes
  - `Action:` 用 runtime API 驗證 route contract 與 ticking-state，並補強 server/frontend regression tests 鎖住 execution route contract 細節
  - `Artifact:` `tests/test_server_startup.py`、`tests/test_frontend_decision_contract.py`
  - `Verify:` `pytest` 20 passed、`py_compile` 成功、`/api/status` 直接回傳 canonical surface / shortcut status / operator message / blockers / observed-ticking
  - `If fail:` 若 contract 細節再次從 API/UI 消失，升級為 execution governance blocker，禁止再宣稱 route governance explicit

---

## Open Issues
### P1. SignalBanner 仍未升級為完整 execution governance surface
**現況**
- SignalBanner 仍明確屬於 shortcut-only，且會導回 Dashboard。

**缺口**
- 尚未消費 `/api/status` 的 `ticking_state / stale governance / guardrail context / install_contract / execution_surface_contract`。

**風險**
- 若在未補 contract 前直接擴第二 route，會重新引入 route 假完成。

**下一步**
- 維持 `Dashboard = canonical route`；只有在 SignalBanner 消費同一份 runtime contract 後才可升級。

### P1. readiness 邊界仍需嚴格守住
**現況**
- 本輪確認的是 execution governance / visibility contract 仍健康，且 host scheduler ticking 正常。

**缺口**
- 尚未驗證 live exchange credential、order ack、fill lifecycle、canary 安全性。

**風險**
- 若把 `observed-ticking + live_ready=false` 解讀成實盤可用，就會重新回到假 readiness。

**下一步**
- 所有 surface 繼續使用 governance / visibility 語言；只有 order-level 驗證完成後才可升級 readiness 敘事。

---

## 本輪已處理
- 實際驗證 `/api/status.execution_surface_contract` 仍存在且欄位完整
- 實際驗證 `external_monitor.ticking_state = observed-ticking`
- 補強 `tests/test_server_startup.py` 鎖定 execution route contract 細節
- 補強 `tests/test_frontend_decision_contract.py` 鎖定 Dashboard route contract 顯示細節
- 完成 targeted pytest / py_compile 驗證

---

## Current Priority
1. **P1：維持 Dashboard 為唯一 canonical execution route；不要讓 SignalBanner 語義偷跑**
2. **P1：持續守住 governance closure ≠ live/canary ready 的邊界**
3. **P1：若未來要擴第二 route，必須先讓它完整消費 `/api/status` 同一份 contract**

---

## Carry-forward（供下一輪 Step 0.5 直接讀入）
- 最高優先問題：`execution route contract 與 observed-ticking 目前 runtime 正常，但下一輪先檢查 /api/status、Dashboard、SignalBanner 是否仍同時維持 canonical route / shortcut-only / live_ready=false / observed-ticking，禁止任何 surface 把 governance closure 誤寫成 live-ready。`
- 本輪已完成：`直接驗證 /api/status contract、直接驗證 external monitor ticking_state=observed-ticking、補強 server/frontend regression tests 鎖住 canonical surface / shortcut status-message / upgrade prerequisite / operator message / blockers。`
- 下一輪必須先處理：`(1) 再次驗證 runtime contract 與 ticking-state 沒退化；(2) 若考慮擴 SignalBanner，先補同一份 /api/status contract；(3) 繼續禁止把 governance closure 誤寫成 live / canary safe。`
- 成功門檻：`/api/status` 與 Dashboard 持續直接顯示 canonical route / canonical surface / shortcut lane / readiness scope / live blockers，且 external monitor 仍有明確 ticking-state；沒有任何 surface 把 `live_ready=false` 邊界沖淡。
- 若失敗：`升級為 execution governance blocker，文件必須明示目前 route split 或 readiness / ticking 邊界已退回人工判讀；禁止宣稱 runtime route governance explicit。`
