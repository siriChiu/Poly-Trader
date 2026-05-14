# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-14 23:21:13.636814**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / C**
- signal: **HOLD** @ confidence **0.3370**
- layers: **1 → 0**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `under_minimum_exact_live_structure_bucket`
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `under_minimum_exact_live_structure_bucket` | reason: `當前即時結構分桶 `CAUTION|base_caution_regime_or_bias|q35` 的精準支持樣本仍停在 2/50（缺 48），support_route=精準樣本未達最小門檻，不可把舊 範圍 的支持閉環誤讀成部署閉環；決策品質仍為 D / score=0.3326；目前維持不可部署治理。`
- support blocker summary: **精準樣本 2/50（缺口 48） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 建議修補方案 core_plus_macro_plus_all_4h 目前為僅供治理參考，適用範圍 bull|CAUTION、來源 live_scope_spillover；只能作治理參考，不是目前即時可部署修補。**
- support next action: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 保留建議修補方案可見但標示為僅參考；適用範圍與來源對齊、且精準樣本達標前不可放行。
- q15 精準樣本修補: **未啟用** | 支持路徑 `exact_bucket_present_but_below_minimum` | 跨越門檻 `floor_crossed_but_support_not_ready`
- runtime closure summary: **當前即時分桶 CAUTION|base_caution_regime_or_bias|q35 的精準樣本仍未就緒（2/50，路徑=精準樣本未達最小門檻 / 治理=目前即時分桶精準樣本已就緒）；較寬範圍 / 近似樣本 與建議修補方案 目前都只屬僅供治理參考，不可視為部署閉環。 建議修補方案=core_plus_macro_plus_all_4h (非目前即時範圍，僅供治理參考). 阻塞點=當前即時結構分桶 `CAUTION|base_caution_regime_or_bias|q35` 的精準支持樣本仍停在 2/50（缺 48），support_route=精準樣本未達最小門檻，不可把舊 範圍 的支持閉環誤讀成部署閉環；決策品質仍為 D / score=0.3326；目前維持不可部署治理。 精準路徑與外溢對照：同 gate 寬 範圍 出現 牛市|警戒 外溢，525 筆 / 勝率 41.9% / 品質 0.103，明顯劣於 精準即時路徑 勝率 70.8% / 品質 0.352。**
- q35 scaling audit: overall=`bias50_formula_may_be_too_harsh` / redesign=`base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked` / runtime_gap=`-0.0359` / mode=`exact_lane_formula_review` / next_patch=`feat_4h_bias50_formula`
- q35 audit action: discriminative base-stack redesign 只能讓 進場品質 跨過 評分門檻，執行期 gate/樣本支持 仍讓 allowed_layers=0；下一輪必須把它治理成 僅限評分 / 執行仍阻塞，不得把 跨越門檻 當成 部署閉環。
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- 建議修補方案: **core_plus_macro_plus_all_4h** — 狀態：僅供治理參考；精準樣本缺口 `48`；適用範圍 `bull|CAUTION`；來源 `live_scope_spillover`
- 建議修補特徵: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- 建議修補說明: 精準樣本 2/50（缺口 48） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 建議修補方案 core_plus_macro_plus_all_4h 目前為僅供治理參考，適用範圍 bull|CAUTION、來源 live_scope_spillover；只能作治理參考，不是目前即時可部署修補。
- 下一步: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 保留建議修補方案可見但標示為僅參考；適用範圍與來源對齊、且精準樣本達標前不可放行。

## Entry-quality component breakdown

- final entry_quality: **0.5859** / trade_floor **0.55** / gap **0.0359**
- base_quality: **0.613** × weight **0.75**
- structure_quality: **0.5046** × weight **0.25**
- base components: feat_4h_bias50=0.3289 (w=0.4, contrib=0.1316), feat_nose=0.8286 (w=0.18, contrib=0.1491), feat_pulse=0.6829 (w=0.27, contrib=0.1844), feat_ear=0.9862 (w=0.15, contrib=0.1479)
- structure components: feat_4h_bb_pct_b=0.9162 (w=0.34, contrib=0.3115), feat_4h_dist_bb_lower=0.28 (w=0.33, contrib=0.0924), feat_4h_dist_swing_low=0.305 (w=0.33, contrib=0.1007)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.2902** | structure_group_max_entry_gain: **0.1238**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**0.7872** / layers≈**2** / required_bias50_cap≈**0.7555**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 89 | 0.7079 | 0.3518 | 0.1259 | 0.3583 | 2 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 89 | 0.7079 | 0.3518 | 0.1259 | 0.3583 | 2 | False |
| narrow `regime_label+entry_quality_label` | 89 | 0.7079 | 0.3518 | 0.1259 | 0.3583 | 2 | False |
| broad `regime_gate+entry_quality_label` | 109 | 0.6972 | 0.3514 | 0.135 | 0.3665 | 2 | False |

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
