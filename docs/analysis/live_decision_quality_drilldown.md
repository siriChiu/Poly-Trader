# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-19 03:51:42.255204**
- target: `simulated_pyramid_win`
- live path: **bull / BLOCK / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `regime_gate_block`
- allowed_layers_reason: `decision_quality_below_trade_floor; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_live_structure_bucket_blocks_trade; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Consecutive loss streak: 245 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Consecutive loss streak: 245 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_present_but_below_minimum` | floor_cross `runtime_blocker_preempts_floor_analysis`
- runtime closure summary: **circuit breaker active：Consecutive loss streak: 245 >= 50; Recent 50-sample win rate: 0.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 0/50，至少還差 15 勝。 同時 recent pathology=recent scope slice 100 rows shows distribution_pathology alerts=['constant_target'] win_rate=0.0 avg_pnl=-0.0094 avg_quality=-0.2875 window=2026-04-17 19:55:33.030808->2026-04-18 04:40:45.098280 adverse_streak=100x0 (2026-04-17 19:55:33.030808->2026-04-18 04:40:45.098280) vs sibling prev_win_rate=0.0 Δwin_rate=0.0 prev_quality=-0.2835 Δquality=-0.004 prev_pnl=-0.0105 Δpnl=0.0011 top_shifts=feat_4h_dist_bb_lower(3.8141→2.9483), feat_4h_bb_pct_b(1.0986→0.8784), feat_4h_dist_swing_low(5.3764→5.2166)。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro** / status `reference_only_until_exact_support_ready` / support_route `exact_bucket_present_but_below_minimum` / gap `49` / reference_scope `bull|CAUTION` / source `bull_4h_pocket_ablation.bull_collapse_q35`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: bull_4h_pocket_ablation.bull_collapse_q35），建議 profile=core_plus_macro；但 current live exact support 仍是 1/50；目前只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持部署 blocker；exact bucket 已出現但仍低於 minimum support，proxy 只可作治理參考。

## Entry-quality component breakdown

- final entry_quality: **0.4043** / trade_floor **0.55** / gap **-0.1457**
- base_quality: **0.4618** × weight **0.75**
- structure_quality: **0.2319** × weight **0.25**
- base components: feat_4h_bias50=0.0659 (w=0.4, contrib=0.0263), feat_nose=0.5046 (w=0.18, contrib=0.0908), feat_pulse=0.7274 (w=0.27, contrib=0.1964), feat_ear=0.9882 (w=0.15, contrib=0.1482)
- structure components: feat_4h_bb_pct_b=0.2862 (w=0.34, contrib=0.0973), feat_4h_dist_bb_lower=0.1035 (w=0.33, contrib=0.0342), feat_4h_dist_swing_low=0.3044 (w=0.33, contrib=0.1004)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.1457**
- base_group_max_entry_gain: **0.4036** | structure_group_max_entry_gain: **0.1921**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.4857, max_gain≈0.2802）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.4857)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 199 | 0.0 | -0.2855 | 0.3799 | 0.8499 | 1 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 199 | 0.0 | -0.2855 | 0.3799 | 0.8499 | 1 | True |
| narrow `regime_label+entry_quality_label` | 199 | 0.0 | -0.2855 | 0.3799 | 0.8499 | 1 | True |
| broad `regime_gate+entry_quality_label` | 199 | 0.0 | -0.2855 | 0.3799 | 0.8499 | 1 | True |

## Shared shifts

- feat_4h_dist_bb_lower (x4), feat_4h_bb_pct_b (x4), feat_4h_dist_swing_low (x4)
- worst_pathology_scope: **regime_label+regime_gate+entry_quality_label** rows=199 win_rate=0.0 quality=-0.2855

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
