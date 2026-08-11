# ADR-0005：允許模型自動重建、訓練與成長

- Status: **ACCEPTED**
- Decision date: 2026-08-11
- Decided by: Owner（Kazuha）
- Decision source: 本次BDD owner Q&A，Q5回答「可重建資料，重新訓練模型（更優的話）、更新報告與狀態，希望模型會自己成長」
- Scope: Heartbeat與automatic model-improvement pipeline
- Related: ADR-0001 Live Canary；ADR-0002 release lifecycle；ADR-0004 DecisionSnapshot

## 白話背景

只做檢查與警告，模型不會進步。Owner希望系統可以持續吸收新資料、訓練挑戰者、比較新舊模型，並把真正更好的模型放進下一輪觀察。

風險是：如果「自動成長」等同「自動改程式、改規則、直接替換實盤模型」，一次資料污染、look-ahead、錯誤label或偶然過度擬合就可能直接影響資金。因此，模型可以自主學習與競爭，但live authorization仍必須分離。

## Decision

> **Heartbeat可以安排資料重建、模型重新訓練、公平比較、候選登錄、Paper/Shadow觀察、報告更新與DecisionSnapshot刷新。只有可重現地優於現任champion的模型，才能成為新candidate/champion。**

自動成長不包含：

- 自動修改source code；
- 自動改feature/label語義或交易規則；
- 自動降低hard safety；
- 自動讓新模型繼承舊Owner release；
- 自動把新identity放進Live Canary。

## 自動成長流程

1. **更新資料**：抓取新market facts，建立immutable dataset snapshot。
2. **資料驗證**：檢查缺口、重複、時間順序、symbol、4H point-in-time、feature/label版本與look-ahead。
3. **訓練挑戰者**：用版本化recipe與固定random seeds訓練多個candidate。
4. **公平比較**：champion與challenger使用同一as-of dataset、walk-forward splits、fees、slippage與評分規則。
5. **判斷是否更好**：以OOS ROI、最大回撤、profit factor、交易數、穩定性與成本後結果為主，不以CV accuracy單獨決定。
6. **登錄結果**：所有成功/失敗run都寫入immutable experiment record。
7. **更新候選**：只有通過versioned comparator與hard non-regression checks的challenger成為新candidate/champion-for-shadow。
8. **Paper/Shadow觀察**：新candidate用自己的exact identity累積outcomes。
9. **發布狀態**：更新leaderboard、generated reports與下一張DecisionSnapshot。
10. **Live保持分離**：新candidate必須經適用的Owner release與exact bundle binding，才能進Live Canary。

## 「更好」的最低契約

Comparator必須版本化並記錄：

- dataset snapshot ID與as-of；
- feature schema、label、target與horizon；
- train/validation/test或walk-forward split IDs；
- fees、slippage、latency assumptions；
- ROI、max drawdown、profit factor、win rate、trade count；
- regime與時間切片穩定性；
- champion與challenger相同條件的差異；
- comparator policy version與決策reason codes。

預設原則：**成本後ROI更高且回撤沒有超過核准容忍範圍**，再由多維分數判斷。Accuracy只能作診斷。

Exact support依ADR-0003只作信心警告，不單獨阻止candidate競爭；但資料污染、look-ahead、identity mismatch與不可重現是hard failure。

## 自動promotion邊界

允許自動：

- experiment完成；
- challenger註冊；
- leaderboard排名；
- champion-for-research或champion-for-shadow切換；
- Paper/Shadow worker使用新candidate；
- generated reports與DecisionSnapshot更新。

不允許自動：

- 修改或撤銷Owner personal release；
- 把新bundle視為已核准；
- 切換live execution bundle；
- 提高Live Canary資金cap或層數；
- 啟用Full Auto Live。

這些需要相符identity的release與後續Owner決策。

## Heartbeat責任

Heartbeat是scheduler/orchestrator，不在自己的fast loop重做全部domain policy：

- fast lane檢查freshness、job lease與是否需要安排工作；
- 資料重建、training、evaluation、shadow與publication各由獨立idempotent job執行；
- heavy job有lease、timeout、resource cap、retry policy與single-flight；
- GET/API request不得觸發訓練或資料回填；
- job失敗時現任champion與active snapshot不被部分覆寫。

## 失敗與回復

- 資料驗證失敗：停止training，保留champion，發布資料問題。
- Training失敗：記錄run failure，不改champion。
- Challenger沒有更好：保留champion並更新比較報告。
- Publication失敗：不切active candidate/snapshot pointer。
- 新shadow candidate後續惡化：停止其promotion，但不改寫historical run。
- 所有切換可由immutable registry pointer回到上一個已知良好identity。

## 文件與畫面

- Leaderboard顯示champion/challenger、比較generation與資料as-of。
- Generated current-state reports可自動覆寫更新，但必須標DecisionSnapshot ID。
- Evergreen PRD、policy、ADR與source code不可由Heartbeat自動改寫。
- UI清楚區分research champion、shadow champion、owner-released bundle與live bundle。

## Pending dependencies

- Q6決定完整runtime bundle identity。
- Q7決定Paper/Shadow evidence與candidate identity的嚴格程度。
- Q8決定Live Canary的精確金額與風險上限。

## Executable specification

- `docs/specification/features/to-be/autonomous-model-improvement.feature`
- As-is heartbeat characterization：`docs/specification/features/as-is/heartbeat-and-artifact-freshness.feature`
- As-is evidence characterization：`docs/specification/features/as-is/strategy-evidence-and-lab.feature`
