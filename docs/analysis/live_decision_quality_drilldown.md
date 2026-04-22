# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-22 00:38:38.234736**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / C**
- signal: **HOLD** @ confidence **0.4296**
- layers: **1 → 0**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `decision_quality_below_trade_floor`
- execution_guardrail_reason: `decision_quality_below_trade_floor`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `None` | reason: `None`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_supported` | floor_cross `None`
- runtime closure summary: **q35 discriminative redesign 已啟用並把 entry_quality 拉到 0.5504（raw layers=1），但最終 execution 仍被 decision_quality_below_trade_floor 擋住；目前不可把 patch active 誤讀成可部署。 exact-vs-spillover=同 gate 寬 scope 出現 bull|CAUTION spillover，200 rows / WR 42.5% / 品質 0.047，明顯劣於 exact live lane WR — / 品質 —。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `deployable_patch_candidate` / support_route `exact_bucket_supported` / gap `0` / reference_scope `bull|CAUTION` / source `live_scope_spillover`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: live_scope_spillover），可直接對應到 core_plus_macro_plus_all_4h patch；exact support 已達 deployable 條件，可把它視為正式 runtime / training patch 候選。
- recommended_patch_action: same-scope exact support 已達 minimum rows，可進入 runtime / training patch 驗證；deployment blocker 仍以 latest runtime truth 為準。

## Entry-quality component breakdown

- final entry_quality: **0.5504** / trade_floor **0.55** / gap **0.0004**
- base_quality: **0.5967** × weight **0.75**
- structure_quality: **0.4114** × weight **0.25**
- base components: feat_4h_bias50=0.2283 (w=0.0, contrib=0.0), feat_nose=0.2693 (w=0.45, contrib=0.1212), feat_pulse=0.3567 (w=0.05, contrib=0.0178), feat_ear=0.9153 (w=0.5, contrib=0.4577)
- structure components: feat_4h_bb_pct_b=0.6435 (w=0.34, contrib=0.2188), feat_4h_dist_bb_lower=0.2474 (w=0.33, contrib=0.0816), feat_4h_dist_swing_low=0.3363 (w=0.33, contrib=0.111)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.3025** | structure_group_max_entry_gain: **0.1472**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**0.6144** / layers≈**1** / required_bias50_cap≈**-1.5265**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 73 | 0.4247 | 0.0468 | 0.2788 | 0.6908 | 73 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| broad `regime_gate+entry_quality_label` | 3 | 1.0 | 0.7114 | 0.0118 | 0.0089 | 0 | False |

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
