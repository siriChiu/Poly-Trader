# PRD — v4.1 實戰化產品需求規格

## 產品定位

Poly-Trader 是一套以「**低頻高信心、可驗證、可拒單**」為核心的加密貨幣 **BTC spot-long 金字塔交易作戰 APP**。

它不是黑箱自動下單器，而是把價格、技術指標、4H 結構、宏觀情緒、模型信心、recent drift、venue readiness 與 execution guardrails 整合成可互動的實戰決策平台，讓使用者能回答：

```text
現在這一筆，值得用真錢開第一層嗎？
如果值得，最多能開幾層？
如果不值得，是哪一個 gate 阻擋？
```

**投資方式固定使用 spot-long 金字塔**：20% → 30% → 50% 分批加碼 + 風險控制。不要槓桿、不要高頻、不要為了增加交易數而放寬門檻。

---

## 實戰化核心原則

1. **No Trade 是一種正確決策**
   APP 的價值不是一直交易，而是能避開低期望值、低支持度、高不確定性的交易。

2. **OOS / Walk-forward 優先於 in-sample 漂亮結果**
   Strategy Lab 的 winner 只有通過 walk-forward OOS、top-k、drawdown、minimum trades、current-live support 後，才能成為 deployment candidate。

3. **ROI / 回撤 / 高信心 precision 優先於 CV accuracy**
   CV 只作診斷；實戰排序應優先看離線 ROI、勝率、盈虧比、最大回撤、最差分折、深套時間與高信心 top-k precision。

4. **Fail-closed，不硬交易**
   若即時支持、熔斷、conformal uncertainty、場館證據或 execution guardrail 任一關鍵條件不通過，只允許模擬觀察 / 影子驗證 / 僅觀察 / 減倉。操作員畫面必須顯示繁中 humanized gate reason；support route / governance route / runtime summary 不得直接露出 raw control-plane token。

5. **研究可追溯、部署可解釋**
   每個 deployable candidate 必須能回溯到 feature profile、regime、top-k slice、walk-forward folds、風控門檻與拒單原因。

---

## 成功定義

### P0 實戰 KPI

- **OOS ROI > Buy-and-hold / Rule baseline**：只接受 walk-forward OOS 上勝出的策略。
- **Top-k high-conviction precision**：top 1% / 2% / 5% / 10% 高信心 slice 的 win rate、ROI、max drawdown 必須單獨可見。
- **最大回撤受控**：預設 deployment gate 要求 max drawdown ≤ 8%；任何單筆/策略風險不得繞過 execution guardrail。
- **Minimum support**：每個候選至少需達 minimum trades / same-bucket support；目前建議下限 `trades >= 50`。
- **Profit Factor ≥ 1.5**：低於門檻只可留在 research / paper。
- **Worst fold 不可崩壞**：不得只靠單一 fold 或單一 regime 撐起 ROI。

### P1 操作 KPI

- Dashboard 10 秒內回答：是否可交易、阻塞原因、允許層數、venue/source 是否健康。
- Execution Console 保持停機開關、reduce-only、pause strategy、reconcile position、order preview，且支持路徑 / 治理路徑 / runtime summary 必須 humanized，不外洩 raw route token。
- 所有 saved strategy 都出現在 Strategy Lab leaderboard，並可回填編輯。
- current-state docs (`ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`) 與 `issues.json / live artifacts` 保持 overwrite sync。

---

## Trade Decision Stack

實戰下單前必須通過五層 gate：

```text
1. Primary Signal Gate
   目前模型 / 策略是否出現 candidate long？

2. Meta-label Gate
   這個 candidate 是否值得 take？p_take 是否高於門檻？

3. Regime Gate
   目前市場 regime 是否允許 spot-long / 加倉？

4. Uncertainty Gate
   conformal / interval / downside risk 是否明確？不確定時拒單。

5. Execution & Risk Gate
   circuit breaker、allowed_layers、current-live support、venue proof、order lifecycle 是否可用？
```

最終輸出不是單純 BUY / HOLD，而是：

```text
Decision: TAKE / SKIP / HOLD_ONLY / REDUCE_ONLY
Allowed layers: 0 / 1 / 2 / 3
Primary confidence: xx%
Meta p_take: xx%
Regime: bull / bear / chop / high-vol
Uncertainty: low / medium / high
Reason: 具體 gate 與阻塞原因
```

---

## 核心架構

### 1. 4H 結構線（低雜訊定位）

用 4H K 線畫出 MA50、MA200、布林通道、Swing 支撐/壓力線。每分鐘計算 1m 價格到這些線的距離百分比，作為交易定位特徵。

| 特徵 | 意義 |
|------|------|
| `feat_4h_bias50` | 距離 MA50 (%) |
| `feat_4h_bias200` | 距離 MA200 (%) — 牛熊判定 |
| `feat_4h_rsi14` | 4H RSI |
| `feat_4h_macd_hist` | 4H MACD Histogram |
| `feat_4h_dist_swing_low` | 距離最近 Swing Low (%) |
| `feat_4h_ma_order` | MA 排列方向 (+1 多 / -1 空) |

### 2. 金字塔交易框架（固定）

- **Layer 1 (20%)**：只允許 high-conviction candidate 開第一層。
- **Layer 2 (30%)**：需 top-k 信心更高、4H 未過熱、drawdown 未惡化。
- **Layer 3 (50%)**：只在極高信心 + 風控支持 + support route deployable 時允許。
- **止損 / 風控**：策略層止損不得繞過 Execution Console / `/api/trade` fail-closed contract。
- **止盈 / 降風險**：reduce / sell / derisk 在 blocker 狀態下仍保持可用。

### 3. Strategy Lab

Strategy Lab 是互動式實驗平台，必須支援：

- 調整進場條件、4H gating、金字塔層數條件、止損/止盈。
- Backtest、Walk-forward、Paper replay、Live shadow、Canary live 分階段模式。
- 顯示 ROI、勝率、盈虧比、最大回撤、最差分折、交易數、深套時間與手續費 / 滑價敏感度。
- 支援 top-k gate 回測：top 1% / 2% / 5% / 10%。
- 點 leaderboard 回填策略參數；所有 user-saved strategy 都必須上榜且可編輯。

### 4. Model Leaderboard / Deployment Profile

比較不同模型與 feature profile 時，排序要以實戰指標為主：

```text
score =
  OOS_ROI * 0.30
+ win_rate * 0.20
+ profit_factor * 0.15
+ top_k_precision * 0.15
- max_drawdown_penalty * 0.15
- instability_penalty * 0.05
```

CV accuracy 只作診斷欄位，不可單獨作為 deployment ranking。

候選 profile 必須標示：

- `research_only`
- `paper_only`
- `shadow_only`
- `canary_candidate`
- `deployable`
- `risk_locked`

### 5. High-Conviction Top-k ROI Gate（P0）

建立 `P0_high_conviction_topk_roi_gate`：

- 產出 `data/high_conviction_topk_oos_matrix.json`。
- 交叉評估 `model × feature_profile × regime × top_k`。
- 每列包含：離線 ROI、勝率、盈虧比、最大回撤、最差分折、交易數、支持路徑與部署判定。
- 未達 `min_trades / win_rate / drawdown / profit_factor / worst_fold / support_route` 門檻時 fail-closed；UI 必須以操作員繁中 copy 顯示失敗原因，不直接露出 raw gate token。
- 排序不得只看最高 ROI：必須先分離 `model_gate_failures`（例如最大回撤、最差分折、最低交易數）與 `live_gate_failures`（即時分桶支持 / 部署阻塞），並優先顯示 `nearest_deployable_rows`。
- 若離線驗證 / 模型風控 gate 已通過但只剩即時分桶 / 支持阻塞，標為 `runtime_blocked_oos_pass`，只能進模擬觀察 / 影子驗證 / 僅觀察，不可直接 live automation。
- `/api/models/leaderboard.high_conviction_topk` 與 Strategy Lab 高信心 OOS Top-K 部署門檻面板必須顯示 `risk_qualified_count / runtime_blocked_candidate_count / nearest_deployable_rows / gate_failures`，避免 operator 被高 ROI 但高回撤或負最差分折的列誤導。
- 最新 matrix truth：`rows=24` / `risk_qualified_rows=6` / `runtime_blocked_candidate_rows=6` / `deployable_rows=0`；最接近部署候選為 `logistic_regression top_2pct`（離線 ROI `0.9324`、勝率 `0.8621`、最大回撤 `0.022`、最差分折 `0.2068`），但因支持路徑尚不可部署 / 部署阻塞點仍啟動而維持 fail-closed。
- 目前 scan 上 CatBoost 約 `ROI=19.78% / win_rate=62.16% / max_drawdown=6.55% / trades=37` 只能作研究線索，因 trades 太少且尚未通過 high-conviction top-k gate，不可直接部署。

---

## 研究 / 實務方法映射

| 方法 | APP 落地方式 | 優先級 |
|---|---|---|
| Walk-forward / Purged CV | 所有 leaderboard 與 deployment candidate 的基礎驗證 | P0 |
| Triple-barrier / path-dependent label | 建立更貼近 TP/SL/金字塔路徑的 label | P0 |
| Meta-labeling | Primary signal 找候選，meta-model 決定 take/skip | P0 |
| Precision@Top-K | 只交易高信心 slice，不追求全市場高頻 | P0 |
| Conformal uncertainty | 不確定時 no-trade / allowed_layers=0 | P1 |
| Regime-aware deployment | 不同 bull/bear/chop/high-vol 使用不同 threshold/layer | P1 |
| Transformer / TS foundation model | 作為 feature generator，不直接下單 | P2 |
| RL / portfolio optimization | 未來多幣種或 sizing sandbox；目前不作主線 | P3 |

---

## 實戰上線階段

### Phase 0 — Research / No-Go

目前若 `CIRCUIT_BREAKER`、`allowed_layers=0`、`support_route_deployable=false` 或 venue proof 不足，只允許研究 / 回測 / 模擬觀察 / 影子驗證。

### Phase 1 — Walk-forward OOS Top-k

完成 high-conviction matrix，找出真正 OOS 有效的 model + feature_profile + regime + top_k。

### Phase 2 — Paper Trading

至少跑 60–90 天或足夠 live candidate signals，驗證 signal、blocker、no-trade、paper execution 與 backtest 是否一致。

### Phase 3 — Canary Live

只允許極小資金、spot-only、max layer=1、no leverage，且 kill switch / reduce-only 永遠可用。

### Phase 4 — 分層開放金字塔

Canary 穩定後才逐步開放 layer 1 → layer 1+2 → layer 1+2+3。

---

## 已完成的 v4.0 / v4.1 基礎

- [x] 4H 距離特徵回填與 Dashboard raw values。
- [x] ECDF 正規化，避免感官分數壓縮。
- [x] Strategy Lab 參數調整、回測、leaderboard 基礎。
- [x] `backtesting/strategy_lab.py` 規則引擎。
- [x] `backtesting/model_leaderboard.py` walk-forward / leaderboard 基礎。
- [x] Execution Console / `/api/trade` fail-closed：阻塞時暫停買入 / 加倉 / 啟用自動模式，保留減碼 / 賣出風險降低路徑。
- [x] current-state docs overwrite sync：`ISSUES.md / ROADMAP.md / ORID_DECISIONS.md` 對齊 `issues.json / live artifacts`。
- [x] Repo hygiene：heartbeat generated artifacts 不進 git，root legacy scripts 已歸檔。

---

## 下一步（v4.1 實戰化 P0）

- [x] 建立 `P0_high_conviction_topk_roi_gate` 的 matrix scaffold 與 `/api/models/leaderboard` / Strategy Lab surfacing。
- [x] 產出 walk-forward OOS top-k matrix，並加上風控 / current-live blocker 分層 metadata。
- [x] 把 risk-first / nearest-deployable scoring 接入 Strategy Lab leaderboard，避免最高 ROI 但高回撤或負 worst-fold 的列誤導 operator。
- [ ] 建立 meta-labeling take/skip gate 的資料 schema。
- [ ] 建立 triple-barrier / pyramid path label 草案。
- [ ] 將 conformal uncertainty blocker 接到 allowed_layers / no-trade reason。
- [ ] 將 deployment profile 分為研究觀察 / 模擬觀察 / 影子驗證 / 小流量 / 可部署 / 風險鎖定。
