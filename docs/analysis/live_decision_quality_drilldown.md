# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-20 00:47:15.429720**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Consecutive loss streak: 191 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Consecutive loss streak: 191 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_unsupported_block` | floor_cross `None`
- runtime closure summary: **circuit breaker active：Consecutive loss streak: 191 >= 50; Recent 50-sample win rate: 0.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 0/50，至少還差 15 勝。 同時 recent pathology=recent scope slice 100 rows shows distribution_pathology alerts=['constant_target'] win_rate=0.0 avg_pnl=-0.0095 avg_quality=-0.2363 window=2026-04-18 18:00:51.160129->2026-04-19 01:10:17.732530 adverse_streak=100x0 (2026-04-18 18:00:51.160129->2026-04-19 01:10:17.732530) vs sibling prev_win_rate=0.01 Δwin_rate=-0.01 prev_quality=-0.1881 Δquality=-0.0482 prev_pnl=-0.0041 Δpnl=-0.0054 top_shifts=feat_4h_dist_swing_low(3.4671→3.1574), feat_4h_dist_bb_lower(0.7269→0.5536), feat_4h_bb_pct_b(0.2525→0.1914)。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_until_exact_support_ready` / support_route `exact_bucket_unsupported_block` / gap `50` / reference_scope `bull|CAUTION` / source `bull_4h_pocket_ablation.bull_collapse_q35`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: bull_4h_pocket_ablation.bull_collapse_q35），建議 profile=core_plus_macro_plus_all_4h；但 current live exact support 仍是 0/50；目前只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。

## Entry-quality component breakdown

- final entry_quality: **0.4611** / trade_floor **0.55** / gap **-0.0889**
- base_quality: **0.5727** × weight **0.75**
- structure_quality: **0.1261** × weight **0.25**
- base components: feat_4h_bias50=0.5029 (w=0.4, contrib=0.2012), feat_nose=0.632 (w=0.18, contrib=0.1138), feat_pulse=0.4215 (w=0.27, contrib=0.1138), feat_ear=0.96 (w=0.15, contrib=0.144)
- structure components: feat_4h_bb_pct_b=0.1822 (w=0.34, contrib=0.062), feat_4h_dist_bb_lower=0.0711 (w=0.33, contrib=0.0235), feat_4h_dist_swing_low=0.1231 (w=0.33, contrib=0.0406)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0889**
- base_group_max_entry_gain: **0.3204** | structure_group_max_entry_gain: **0.2184**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.2963, max_gain≈0.1491）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.2963), feat_pulse (Δscore≈0.439)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `global` | 200 | 0.005 | -0.2122 | 0.243 | 0.8097 | 0 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| broad `regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |

## Shared shifts

- None
- worst_pathology_scope: **entry_quality_label** rows=200 win_rate=0.005 quality=-0.2122

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
