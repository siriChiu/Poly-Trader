# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-24 21:04:05.212904**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **HOLD** @ confidence **0.3085**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `decision_quality_below_trade_floor`
- execution_guardrail_reason: `decision_quality_below_trade_floor`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `decision_quality_below_trade_floor` | reason: `current live structure bucket `CAUTION|base_caution_regime_or_bias|q15` 已完成 exact support closure（122/50），但 top-level live baseline 仍停在 entry_quality=0.3632，低於 trade floor 0.55；目前只能維持明確 no-deploy governance，不可把 support closure 或 component-experiment readiness 誤讀成 deployment closure。`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_supported` | floor_cross `legal_component_experiment_after_support_ready`
- runtime closure summary: **current live bucket CAUTION|base_caution_regime_or_bias|q15 已完成 exact support closure（122/50），但 top-level live baseline 仍停在 entry_quality=0.3632 (D) < trade floor 0.55；目前維持明確 no-deploy governance。 不可把 support closure 誤讀成 deployment closure。 exact-vs-spillover=同 quality 寬 scope 出現 bull|BLOCK spillover，720 rows / WR 33.3% / 品質 0.064，明顯劣於 exact live lane WR 87.2% / 品質 0.502。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None` / reference_scope `None` / source `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.3632** / trade_floor **0.55** / gap **-0.1868**
- base_quality: **0.4067** × weight **0.75**
- structure_quality: **0.2327** × weight **0.25**
- base components: feat_4h_bias50=0.1879 (w=0.4, contrib=0.0752), feat_nose=0.5106 (w=0.18, contrib=0.0919), feat_pulse=0.3508 (w=0.27, contrib=0.0947), feat_ear=0.9662 (w=0.15, contrib=0.1449)
- structure components: feat_4h_bb_pct_b=0.4316 (w=0.34, contrib=0.1467), feat_4h_dist_bb_lower=0.164 (w=0.33, contrib=0.0541), feat_4h_dist_swing_low=0.0964 (w=0.33, contrib=0.0318)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.1868**
- base_group_max_entry_gain: **0.445** | structure_group_max_entry_gain: **0.1918**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.6227, max_gain≈0.2436）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.6227)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 180 | 0.8722 | 0.5019 | 0.1599 | 0.283 | 122 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 180 | 0.8722 | 0.5019 | 0.1599 | 0.283 | 122 | False |
| narrow `regime_label+entry_quality_label` | 180 | 0.8722 | 0.5019 | 0.1599 | 0.283 | 122 | False |
| broad `regime_gate+entry_quality_label` | 374 | 0.8262 | 0.4618 | 0.189 | 0.3911 | 122 | False |

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
