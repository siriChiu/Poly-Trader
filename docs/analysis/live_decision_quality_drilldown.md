# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-24 18:01:36.281423**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **HOLD** @ confidence **0.3523**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `decision_quality_below_trade_floor`
- execution_guardrail_reason: `decision_quality_below_trade_floor`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `decision_quality_below_trade_floor` | reason: `current live structure bucket `CAUTION|base_caution_regime_or_bias|q15` 已完成 exact support closure（123/50），但 top-level live baseline 仍停在 entry_quality=0.4000，低於 trade floor 0.55；目前只能維持明確 no-deploy governance，不可把 support closure 或 component-experiment readiness 誤讀成 deployment closure。`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_supported` | floor_cross `legal_component_experiment_after_support_ready`
- runtime closure summary: **current live bucket CAUTION|base_caution_regime_or_bias|q15 已完成 exact support closure（123/50），但 top-level live baseline 仍停在 entry_quality=0.4000 (D) < trade floor 0.55；目前維持明確 no-deploy governance。 不可把 support closure 誤讀成 deployment closure。 exact-vs-spillover=同 quality 寬 scope 出現 bull|BLOCK spillover，710 rows / WR 44.9% / 品質 0.123，明顯劣於 exact live lane WR 82.6% / 品質 0.467。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None` / reference_scope `None` / source `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.4** / trade_floor **0.55** / gap **-0.15**
- base_quality: **0.4632** × weight **0.75**
- structure_quality: **0.2103** × weight **0.25**
- base components: feat_4h_bias50=0.186 (w=0.4, contrib=0.0744), feat_nose=0.6554 (w=0.18, contrib=0.118), feat_pulse=0.4528 (w=0.27, contrib=0.1222), feat_ear=0.9904 (w=0.15, contrib=0.1486)
- structure components: feat_4h_bb_pct_b=0.3881 (w=0.34, contrib=0.1319), feat_4h_dist_bb_lower=0.1479 (w=0.33, contrib=0.0488), feat_4h_dist_swing_low=0.0896 (w=0.33, contrib=0.0296)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.15**
- base_group_max_entry_gain: **0.4026** | structure_group_max_entry_gain: **0.1974**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.5, max_gain≈0.2442）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.5)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 190 | 0.8263 | 0.4667 | 0.1689 | 0.3076 | 123 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 190 | 0.8263 | 0.4667 | 0.1689 | 0.3076 | 123 | False |
| narrow `regime_label+entry_quality_label` | 190 | 0.8263 | 0.4667 | 0.1689 | 0.3076 | 123 | False |
| broad `regime_gate+entry_quality_label` | 391 | 0.7903 | 0.4343 | 0.1949 | 0.4082 | 123 | False |

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
