# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-13 12:20:44.051389**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / C**
- signal: **HOLD** @ confidence **0.2963**
- layers: **1 → 0**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `decision_quality_below_trade_floor`
- execution_guardrail_reason: `decision_quality_below_trade_floor`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `decision_quality_below_trade_floor` | reason: `current live structure bucket `CAUTION|base_caution_regime_or_bias|q15` 已完成 exact support closure（95/50），且 q15 patch 已啟用並把 raw entry 拉到 entry_quality=0.5501（raw layers=1），但 final execution 仍被 decision-quality trade floor 擋住；目前必須維持 patch_active_but_execution_blocked，不可把 q15 patch active 或 support closure 誤讀成 deployment closure。`
- support blocker summary: **exact support 95/50 (gap 0) 已達 deployable support；deployment 仍以 `decision_quality_below_trade_floor` 與 allowed_layers 為準。**
- support next action: 不要把 support closure 誤讀成 deployment closure；繼續檢查 allowed_layers / signal / venue proof。
- q15 exact-supported patch: **active** | support_route `exact_bucket_supported` | floor_cross `legal_component_experiment_after_support_ready`
- runtime closure summary: **q15 patch 已啟用並把 entry_quality 拉到 0.5501（raw layers=1），但最終 execution 仍被 decision_quality_below_trade_floor 擋住；目前不可把 patch active 誤讀成可部署。 exact-vs-spillover=同 regime 寬 scope 出現 chop|CAUTION spillover，96 rows / WR 64.6% / 品質 0.260，明顯劣於 exact live lane WR 75.0% / 品質 0.300。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=True / entry_quality_ge_0_55=True / allowed_layers_gt_0=True / preserves_positive_discrimination_status=`verified_exact_lane_bucket_dominance`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None` / reference_scope `None` / source `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.5501** / trade_floor **0.55** / gap **0.0001**
- base_quality: **0.6763** × weight **0.75**
- structure_quality: **0.1712** × weight **0.25**
- base components: feat_4h_bias50=0.783 (w=0.4, contrib=0.3132), feat_nose=0.602 (w=0.18, contrib=0.1084), feat_pulse=0.3988 (w=0.27, contrib=0.1077), feat_ear=0.9807 (w=0.15, contrib=0.1471)
- structure components: feat_4h_bb_pct_b=0.3429 (w=0.34, contrib=0.1166), feat_4h_dist_bb_lower=0.0827 (w=0.33, contrib=0.0273), feat_4h_dist_swing_low=0.0828 (w=0.33, contrib=0.0273)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0626**
- base_group_max_entry_gain: **0.3053** | structure_group_max_entry_gain: **0.2073**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.2087, max_gain≈0.1277）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.2087), feat_pulse (Δscore≈0.3091), feat_4h_dist_bb_lower (Δscore≈0.7588), feat_4h_dist_swing_low (Δscore≈0.7588)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 100 | 0.65 | 0.262 | 0.0976 | 0.3539 | 97 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 4 | 0.75 | 0.2998 | 0.0929 | 0.4327 | 2 | False |
| narrow `regime_label+entry_quality_label` | 4 | 0.75 | 0.2998 | 0.0929 | 0.4327 | 2 | False |
| broad `regime_gate+entry_quality_label` | 4 | 0.75 | 0.2998 | 0.0929 | 0.4327 | 2 | False |

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
