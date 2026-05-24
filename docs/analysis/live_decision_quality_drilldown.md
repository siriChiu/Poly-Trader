# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-24 22:08:41.325569**
- target: `simulated_pyramid_win`
- live path: **盤整 / 觀察 / C**
- signal: **ABSTAIN** @ confidence **0.5000**
- layers: **1 → 0**
- allowed_layers_raw_reason: 進場品質_C_single_layer
- allowed_layers_reason: 精準樣本未達最小門檻
- execution_guardrail_reason: 精準樣本未達最小門檻
- runtime_blocker: None | reason: None
- deployment_blocker: 精準樣本未達最小門檻 | reason: 當前即時結構分桶 `觀察｜基線觀察（市場狀態 / 偏離）｜q15` 的精準支持樣本仍停在 24/50（缺 26），支持路徑=精準樣本未達最小門檻，不可把舊範圍的支持閉環誤讀成部署閉環；決策品質仍為 D / 品質分數 -0.2555；目前維持不可部署治理。
- support blocker summary: **精準樣本 24/50（缺口 26） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版 #1436 59/50僅能當歷史參考，因市場狀態不吻合目前支持語義，不可宣稱同一語義已閉環。**
- support next action: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。
- current-bucket root cause: verdict=current_exact_support_under_minimum / patch=support_accumulation_or_semantic_rebaseline / feature=None / exact_support=24/50 / gap=26 / neighbor=觀察｜基線觀察（市場狀態 / 偏離）｜q35
- 精準樣本修補: **未啟用** | 支持路徑 **精準樣本未達最小門檻** | 跨越門檻 **已跨越門檻但精準樣本未就緒**
- runtime closure summary: **當前即時分桶 觀察｜基線觀察（市場狀態 / 偏離）｜q15 的精準樣本仍未就緒（24/50，路徑=精準樣本未達最小門檻 / 治理=目前即時分桶精準樣本未達最小門檻）；較寬範圍 / 近似樣本 目前都只屬僅供治理參考，不可視為部署閉環。 阻塞點=當前即時結構分桶 `觀察｜基線觀察（市場狀態 / 偏離）｜q15` 的精準支持樣本仍停在 24/50（缺 26），支持路徑=精準樣本未達最小門檻，不可把舊範圍的支持閉環誤讀成部署閉環；決策品質仍為 D / 品質分數 -0.2555；目前維持不可部署治理。 精準路徑與外溢對照：同 gate 寬範圍出現 盤整｜觀察 外溢，67 筆 / 勝率 0.0% / 品質 -0.381，明顯劣於 精準即時路徑 勝率 0.0% / 品質 -0.322。**
- q35 scaling audit: overall=None / redesign=None / runtime_gap=None / mode=None / next_patch=None
- q35 runtime truth: redesign_entry_quality=None / redesign_layers_after=None / runtime_layers=None / blocker=None / exact_support=None/None / support_gap=None
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=None
- 建議修補方案: **None** — 狀態：None；精準樣本缺口 `None`；適用範圍 None；來源 None
- 建議修補特徵: None
- 建議修補說明: 精準樣本 24/50（缺口 26） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版 #1436 59/50僅能當歷史參考，因市場狀態不吻合目前支持語義，不可宣稱同一語義已閉環。
- 下一步: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。

## Entry-quality component breakdown

- final entry_quality: **0.5696** / trade_floor **0.55** / gap **0.0196**
- 基礎品質: **0.6447** × 權重 **0.75**
- 結構品質: **0.3443** × 權重 **0.25**
- base components: feat_4h_bias50=0.5602 (w=0.4, contrib=0.2241), feat_nose=0.4408 (w=0.18, contrib=0.0793), feat_pulse=0.7228 (w=0.27, contrib=0.1951), feat_ear=0.9745 (w=0.15, contrib=0.1462)
- structure components: feat_4h_bb_pct_b=0.5394 (w=0.34, contrib=0.1834), feat_4h_dist_bb_lower=0.1648 (w=0.33, contrib=0.0544), feat_4h_dist_swing_low=0.3226 (w=0.33, contrib=0.1065)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.2664** | structure_group_max_entry_gain: **0.164**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 59 | 0.0 | -0.3529 | 0.3762 | 0.8862 | 51 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 28 | 0.0 | -0.3221 | 0.356 | 0.8305 | 24 | False |
| narrow `regime_label+entry_quality_label` | 28 | 0.0 | -0.3221 | 0.356 | 0.8305 | 24 | False |
| broad `regime_gate+entry_quality_label` | 57 | 0.1228 | -0.2186 | 0.3488 | 0.8354 | 31 | True |

## Exact live-lane bucket diagnostic

- verdict: **toxic sub bucket identified** | bucket_count: **2**
- reason: 精準即時路徑 的 current bucket `觀察｜基線觀察（市場狀態 / 偏離）｜q15` 本身就是最差子 bucket，應直接升級成 執行期 veto / rejection 規則。
- toxic_bucket: 觀察｜基線觀察（市場狀態 / 偏離）｜q15

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
