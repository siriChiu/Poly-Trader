# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-24 09:30:06.572983**
- target: `simulated_pyramid_win`
- live path: **盤整 / 觀察 / C**
- signal: **ABSTAIN** @ confidence **0.5000**
- layers: **1 → 0**
- allowed_layers_raw_reason: 進場品質_C_single_layer
- allowed_layers_reason: 精準樣本尚未建立
- execution_guardrail_reason: 精準樣本尚未建立
- runtime_blocker: None | reason: None
- deployment_blocker: 精準樣本尚未建立 | reason: 當前即時結構分桶 `觀察｜基線觀察（市場狀態 / 偏離）｜q35` 的精準支持樣本仍停在 0/50（缺 50），支持路徑=精準樣本尚未建立，不可把舊範圍的支持閉環誤讀成部署閉環；決策品質仍為 D / 品質分數 -0.1322；目前維持不可部署治理。
- support blocker summary: **精準樣本 0/50（缺口 50） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版 #1238 0/50僅能當歷史參考，因校準視窗、進場品質不吻合目前支持語義，不可宣稱同一語義已閉環。**
- support next action: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。
- current-bucket root cause: verdict=current_row_already_above_q35_boundary / patch=support_accumulation / feature=feat_4h_bb_pct_b / exact_support=0/50 / gap=50 / neighbor=觀察｜基線觀察（市場狀態 / 偏離）｜q15
- 精準樣本修補: **未啟用** | 支持路徑 **精準樣本尚未建立** | 跨越門檻 **已跨越門檻但精準樣本未就緒**
- runtime closure summary: **當前即時分桶 觀察｜基線觀察（市場狀態 / 偏離）｜q35 的精準樣本仍未就緒（0/50，路徑=精準樣本尚未建立 / 治理=精準即時代理路徑僅供治理參考）；較寬範圍 / 近似樣本 目前都只屬僅供治理參考，不可視為部署閉環。 阻塞點=當前即時結構分桶 `觀察｜基線觀察（市場狀態 / 偏離）｜q35` 的精準支持樣本仍停在 0/50（缺 50），支持路徑=精準樣本尚未建立，不可把舊範圍的支持閉環誤讀成部署閉環；決策品質仍為 D / 品質分數 -0.1322；目前維持不可部署治理。 精準路徑與外溢對照：同 gate 寬範圍出現 盤整｜觀察 外溢，94 筆 / 勝率 0.0% / 品質 -0.325，明顯劣於 精準即時路徑 勝率 13.3% / 品質 -0.216。**
- q35 scaling audit: overall=bias50_formula_may_be_too_harsh / redesign=base_stack_redesign_discriminative_reweight_crosses_floor_but_執行_blocked / runtime_gap=-0.0176 / mode=exact_lane_formula_review / next_patch=feat_4h_bias50_formula
- q35 runtime truth: redesign_entry_quality=0.5506 / redesign_layers_after=0 / runtime_layers=0 / blocker=精準樣本尚未建立 / exact_support=0/50 / support_gap=50
- q35 audit action: discriminative base-stack redesign 只能讓 進場品質 跨過 評分門檻，執行期 gate/樣本支持 仍讓 allowed_layers=0；下一輪必須把它治理成 僅限評分 / 執行仍阻塞，不得把 跨越門檻 當成 部署閉環。
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=None
- 建議修補方案: **None** — 狀態：None；精準樣本缺口 `None`；適用範圍 None；來源 None
- 建議修補特徵: None
- 建議修補說明: 精準樣本 0/50（缺口 50） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版 #1238 0/50僅能當歷史參考，因校準視窗、進場品質不吻合目前支持語義，不可宣稱同一語義已閉環。
- 下一步: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。

## Entry-quality component breakdown

- final entry_quality: **0.5676** / trade_floor **0.55** / gap **0.0176**
- 基礎品質: **0.5987** × 權重 **0.75**
- 結構品質: **0.4742** × 權重 **0.25**
- base components: feat_4h_bias50=0.5275 (w=0.4, contrib=0.211), feat_nose=0.352 (w=0.18, contrib=0.0634), feat_pulse=0.6508 (w=0.27, contrib=0.1757), feat_ear=0.9909 (w=0.15, contrib=0.1486)
- structure components: feat_4h_bb_pct_b=0.8136 (w=0.34, contrib=0.2766), feat_4h_dist_bb_lower=0.2491 (w=0.33, contrib=0.0822), feat_4h_dist_swing_low=0.3496 (w=0.33, contrib=0.1154)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.301** | structure_group_max_entry_gain: **0.1314**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**0.7093** / layers≈**2** / required_bias50_cap≈**-0.2375**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_gate+entry_quality_label` | 77 | 0.2208 | -0.1441 | 0.3173 | 0.7371 | 0 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 45 | 0.1333 | -0.2158 | 0.3228 | 0.7339 | 0 | True |
| narrow `regime_label+entry_quality_label` | 45 | 0.1333 | -0.2158 | 0.3228 | 0.7339 | 0 | True |
| broad `regime_gate+entry_quality_label` | 77 | 0.2208 | -0.1441 | 0.3173 | 0.7371 | 0 | False |

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
