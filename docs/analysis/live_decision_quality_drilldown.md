# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-21 16:01:23.482752**
- target: `simulated_pyramid_win`
- live path: **盤整 / 觀察 / D**
- signal: **觀望** @ confidence **0.6562**
- layers: **0 → 0**
- allowed_layers_raw_reason: 進場品質低於交易門檻
- allowed_layers_reason: 精準樣本未達最小門檻
- execution_guardrail_reason: 精準樣本未達最小門檻
- runtime_blocker: None | reason: None
- deployment_blocker: 精準樣本未達最小門檻 | reason: 當前即時結構分桶 `觀察｜基線觀察（市場狀態 / 偏離）｜q15` 的精準支持樣本仍停在 1/50（缺 49），支持路徑=精準樣本未達最小門檻，不可把舊範圍的支持閉環誤讀成部署閉環；決策品質仍為 C / 品質分數 0.3685；目前維持不可部署治理。
- support blocker summary: **精準樣本 1/50（缺口 49） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版 #1250 173/50僅能當歷史參考，因校準視窗不吻合目前支持語義，不可宣稱同一語義已閉環。**
- support next action: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。
- current-bucket root cause: verdict=current_exact_support_under_minimum / patch=support_accumulation_or_semantic_rebaseline / feature=None / exact_support=1/50 / gap=49 / neighbor=觀察｜基線觀察（市場狀態 / 偏離）｜q65
- 精準樣本修補: **未啟用** | 支持路徑 **精準樣本未達最小門檻** | 跨越門檻 **數學上可跨門檻，但精準樣本未達標前不可啟用**
- runtime closure summary: **當前即時分桶 觀察｜基線觀察（市場狀態 / 偏離）｜q15 的精準樣本仍未就緒（1/50，路徑=精準樣本未達最小門檻 / 治理=目前即時分桶精準樣本未達最小門檻）；較寬範圍 / 近似樣本 目前都只屬僅供治理參考，不可視為部署閉環。 阻塞點=當前即時結構分桶 `觀察｜基線觀察（市場狀態 / 偏離）｜q15` 的精準支持樣本仍停在 1/50（缺 49），支持路徑=精準樣本未達最小門檻，不可把舊範圍的支持閉環誤讀成部署閉環；決策品質仍為 C / 品質分數 0.3685；目前維持不可部署治理。 精準路徑與外溢對照：同 gate 寬範圍出現 盤整｜觀察 外溢，199 筆 / 勝率 48.8% / 品質 0.192，明顯劣於 精準即時路徑 勝率 100.0% / 品質 0.506。**
- q35 scaling audit: overall=None / redesign=None / runtime_gap=None / mode=None / next_patch=None
- q35 runtime truth: redesign_entry_quality=None / redesign_layers_after=None / runtime_layers=None / blocker=None / exact_support=None/None / support_gap=None
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=None
- 建議修補方案: **None** — 狀態：None；精準樣本缺口 `None`；適用範圍 None；來源 None
- 建議修補特徵: None
- 建議修補說明: 精準樣本 1/50（缺口 49） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版 #1250 173/50僅能當歷史參考，因校準視窗不吻合目前支持語義，不可宣稱同一語義已閉環。
- 下一步: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。

## Entry-quality component breakdown

- final entry_quality: **0.5239** / trade_floor **0.55** / gap **-0.0261**
- 基礎品質: **0.6203** × 權重 **0.75**
- 結構品質: **0.2344** × 權重 **0.25**
- base components: feat_4h_bias50=0.7182 (w=0.4, contrib=0.2873), feat_nose=0.4731 (w=0.18, contrib=0.0852), feat_pulse=0.3908 (w=0.27, contrib=0.1055), feat_ear=0.9492 (w=0.15, contrib=0.1424)
- structure components: feat_4h_bb_pct_b=0.4099 (w=0.34, contrib=0.1394), feat_4h_dist_bb_lower=0.1239 (w=0.33, contrib=0.0409), feat_4h_dist_swing_low=0.164 (w=0.33, contrib=0.0541)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0261**
- base_group_max_entry_gain: **0.2847** | structure_group_max_entry_gain: **0.1915**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.087, max_gain≈0.0845）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.087), feat_pulse (Δscore≈0.1289), feat_nose (Δscore≈0.1933), feat_4h_bb_pct_b (Δscore≈0.3071)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_gate` | 200 | 0.74 | 0.3381 | 0.0843 | 0.3215 | 141 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 1 | 1.0 | 0.5059 | 0.002 | 0.0137 | 1 | False |
| narrow `regime_label+entry_quality_label` | 1 | 1.0 | 0.5059 | 0.002 | 0.0137 | 1 | False |
| broad `regime_gate+entry_quality_label` | 1 | 1.0 | 0.5059 | 0.002 | 0.0137 | 1 | False |

## Exact live-lane bucket diagnostic

- verdict: **no exact lane sub bucket split** | bucket_count: **1**
- reason: 精準即時路徑 沒有可比較的非 current bucket 子 bucket。
- toxic_bucket: None

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- 若 `runtime_blocker.type=circuit_breaker`，代表目前即時列在決策品質合約評估前已被熔斷；q35/q15 診斷只能作背景研究，不可當成即時部署路由。
- 若 `deployment_blocker.type=bull_q35_no_deploy_governance`，代表目前 bull q35 路徑雖有精準樣本，但只有非判別式高風險重配能跨過門檻；不得描述成單純樣本不足或一般門檻缺口。
- 若 `q15_exact_supported_component_patch_applied=true` 且 `signal=HOLD`，應描述為容量已開但訊號仍觀望；不是修補缺失，也不是自動買入就緒。
- 精準即時路徑與選用範圍刻意分離：若精準路徑樣本太少或缺少目前結構分桶支持，執行期不可盲目信任它。
- 較寬同 gate 範圍只可作結構分桶備援，不是目前即時牛市路徑的主要語義代表。
- 若共享位移仍由 `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b` 主導，下一步應持續聚焦 4H 結構塌陷，而不是泛化校準調參。
