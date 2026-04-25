# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-25 03:36:18.720559**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `circuit_breaker_active`
- execution_guardrail_reason: `circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Consecutive loss streak: 63 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Consecutive loss streak: 63 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_supported` | floor_cross `runtime_blocker_preempts_floor_analysis`
- runtime closure summary: **circuit breaker active：Consecutive loss streak: 63 >= 50; Recent 50-sample win rate: 0.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 0/50，至少還差 15 勝。 exact-vs-spillover=同 quality 寬 scope 出現 bull|BLOCK spillover，757 rows / WR 20.9% / 品質 -0.044，明顯劣於 exact live lane WR 97.9% / 品質 0.616。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None` / reference_scope `None` / source `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.417** / trade_floor **0.55** / gap **-0.133**
- base_quality: **0.4792** × weight **0.75**
- structure_quality: **0.2305** × weight **0.25**
- base components: feat_4h_bias50=0.2237 (w=0.4, contrib=0.0895), feat_nose=0.29 (w=0.18, contrib=0.0522), feat_pulse=0.7044 (w=0.27, contrib=0.1902), feat_ear=0.9823 (w=0.15, contrib=0.1473)
- structure components: feat_4h_bb_pct_b=0.4354 (w=0.34, contrib=0.1481), feat_4h_dist_bb_lower=0.1659 (w=0.33, contrib=0.0547), feat_4h_dist_swing_low=0.084 (w=0.33, contrib=0.0277)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.133**
- base_group_max_entry_gain: **0.3907** | structure_group_max_entry_gain: **0.1924**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.4433, max_gain≈0.2329）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.4433)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 143 | 0.979 | 0.6158 | 0.1042 | 0.1881 | 87 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 143 | 0.979 | 0.6158 | 0.1042 | 0.1881 | 87 | False |
| narrow `regime_label+entry_quality_label` | 143 | 0.979 | 0.6158 | 0.1042 | 0.1881 | 87 | False |
| broad `regime_gate+entry_quality_label` | 335 | 0.8537 | 0.5008 | 0.1637 | 0.3579 | 87 | False |

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
