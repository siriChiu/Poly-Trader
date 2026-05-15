# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-15 03:31:03.502906**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **HOLD** @ confidence **0.3220**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `unsupported_exact_live_structure_bucket`
- execution_guardrail_reason: `unsupported_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `unsupported_exact_live_structure_bucket` | reason: `當前即時結構分桶 `CAUTION|base_caution_regime_or_bias|q35` 的精準支持樣本仍停在 0/50（缺 50），support_route=exact_bucket_missing_exact_lane_proxy_only，不可把舊 範圍 的支持閉環誤讀成部署閉環；決策品質仍為 D / score=0.0839；目前維持不可部署治理。`
- support blocker summary: **精準樣本 0/50（缺口 50） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。**
- support next action: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。
- q15 精準樣本修補: **未啟用** | 支持路徑 `exact_bucket_missing_exact_lane_proxy_only` | 跨越門檻 `math_cross_possible_but_illegal_without_exact_support`
- runtime closure summary: **當前即時分桶 CAUTION|base_caution_regime_or_bias|q35 的精準樣本仍未就緒（0/50，路徑=exact_bucket_missing_exact_lane_proxy_only / 治理=exact_live_lane_proxy_available）；較寬範圍 / 近似樣本 目前都只屬僅供治理參考，不可視為部署閉環。 阻塞點=當前即時結構分桶 `CAUTION|base_caution_regime_or_bias|q35` 的精準支持樣本仍停在 0/50（缺 50），support_route=exact_bucket_missing_exact_lane_proxy_only，不可把舊 範圍 的支持閉環誤讀成部署閉環；決策品質仍為 D / score=0.0839；目前維持不可部署治理。 精準路徑與外溢對照：同 gate 寬 範圍 出現 盤整|警戒 外溢，31 筆 / 勝率 66.7% / 品質 0.256，明顯劣於 精準即時路徑 勝率 40.4% / 品質 0.080。**
- q35 scaling audit: overall=`bias50_formula_may_be_too_harsh` / redesign=`base_stack_redesign_discriminative_reweight_crosses_floor_but_execution_blocked` / runtime_gap=`0.005` / mode=`exact_lane_formula_review` / next_patch=`feat_4h_bias50_formula`
- q35 runtime truth: redesign_entry_quality=`0.5535` / redesign_layers_after=`0` / runtime_layers=`0` / blocker=`unsupported_exact_live_structure_bucket` / exact_support=`0/50` / support_gap=`50`
- q35 audit action: discriminative base-stack redesign 只能讓 進場品質 跨過 評分門檻，執行期 gate/樣本支持 仍讓 allowed_layers=0；下一輪必須把它治理成 僅限評分 / 執行仍阻塞，不得把 跨越門檻 當成 部署閉環。
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- 建議修補方案: **None** — 狀態：None；精準樣本缺口 `None`；適用範圍 `None`；來源 `None`
- 建議修補特徵: None
- 建議修補說明: 精準樣本 0/50（缺口 50） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。
- 下一步: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。

## Entry-quality component breakdown

- final entry_quality: **0.545** / trade_floor **0.55** / gap **-0.005**
- base_quality: **0.576** × weight **0.75**
- structure_quality: **0.4523** × weight **0.25**
- base components: feat_4h_bias50=0.3358 (w=0.4, contrib=0.1343), feat_nose=0.5598 (w=0.18, contrib=0.1008), feat_pulse=0.7227 (w=0.27, contrib=0.1951), feat_ear=0.9714 (w=0.15, contrib=0.1457)
- structure components: feat_4h_bb_pct_b=0.8075 (w=0.34, contrib=0.2745), feat_4h_dist_bb_lower=0.2381 (w=0.33, contrib=0.0786), feat_4h_dist_swing_low=0.3007 (w=0.33, contrib=0.0992)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.005**
- base_group_max_entry_gain: **0.3181** | structure_group_max_entry_gain: **0.137**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.0167, max_gain≈0.1993）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.0167), feat_pulse (Δscore≈0.0247), feat_nose (Δscore≈0.037), feat_4h_bb_pct_b (Δscore≈0.0588)
- bias50 fully relaxed: entry≈**0.7443** / layers≈**2** / required_bias50_cap≈**0.6375**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 57 | 0.4035 | 0.0802 | 0.265 | 0.6475 | 0 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 57 | 0.4035 | 0.0802 | 0.265 | 0.6475 | 0 | False |
| narrow `regime_label+entry_quality_label` | 57 | 0.4035 | 0.0802 | 0.265 | 0.6475 | 0 | False |
| broad `regime_gate+entry_quality_label` | 59 | 0.4237 | 0.0997 | 0.2615 | 0.6375 | 0 | False |

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
