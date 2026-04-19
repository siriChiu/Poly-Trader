# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-19 14:14:04.455344**
- target: `simulated_pyramid_win`
- live path: **bull / CAUTION / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `decision_quality_below_trade_floor; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Recent 50-sample win rate: 2.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Recent 50-sample win rate: 2.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_present_but_below_minimum` | floor_cross `None`
- runtime closure summary: **circuit breaker active：Recent 50-sample win rate: 2.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 1/50，至少還差 14 勝。 同時 recent pathology=recent scope slice 199 rows shows distribution_pathology alerts=['label_imbalance'] win_rate=0.005 avg_pnl=-0.0102 avg_quality=-0.2857 window=2026-04-17 17:34:10.942755->2026-04-18 15:02:26.615581 adverse_streak=195x0 (2026-04-17 17:34:10.942755->2026-04-18 13:43:25.809469)。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro** / status `reference_only_until_exact_support_ready` / support_route `exact_bucket_present_but_below_minimum` / gap `49` / reference_scope `bull|CAUTION` / source `bull_4h_pocket_ablation.bull_collapse_q35`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: bull_4h_pocket_ablation.bull_collapse_q35），建議 profile=core_plus_macro；但 current live exact support 仍是 1/50；目前只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。

## Entry-quality component breakdown

- final entry_quality: **0.3901** / trade_floor **0.55** / gap **-0.1599**
- base_quality: **0.4015** × weight **0.75**
- structure_quality: **0.356** × weight **0.25**
- base components: feat_4h_bias50=0.0605 (w=0.4, contrib=0.0242), feat_nose=0.323 (w=0.18, contrib=0.0581), feat_pulse=0.6464 (w=0.27, contrib=0.1745), feat_ear=0.9642 (w=0.15, contrib=0.1446)
- structure components: feat_4h_bb_pct_b=0.5372 (w=0.34, contrib=0.1827), feat_4h_dist_bb_lower=0.1975 (w=0.33, contrib=0.0652), feat_4h_dist_swing_low=0.3278 (w=0.33, contrib=0.1082)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.1599**
- base_group_max_entry_gain: **0.4489** | structure_group_max_entry_gain: **0.161**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.533, max_gain≈0.2819）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.533)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+entry_quality_label` | 199 | 0.005 | -0.2857 | 0.3777 | 0.8551 | 1 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 1 | 0.0 | -0.4283 | 0.3984 | 0.9957 | 1 | False |
| narrow `regime_label+entry_quality_label` | 199 | 0.005 | -0.2857 | 0.3777 | 0.8551 | 1 | True |
| broad `regime_gate+entry_quality_label` | 1 | 0.0 | -0.4283 | 0.3984 | 0.9957 | 1 | False |

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
