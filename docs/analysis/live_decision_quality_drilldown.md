# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-19 23:26:26.081956**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Consecutive loss streak: 186 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Consecutive loss streak: 186 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_unsupported_block` | floor_cross `None`
- runtime closure summary: **circuit breaker active：Consecutive loss streak: 186 >= 50; Recent 50-sample win rate: 0.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 0/50，至少還差 15 勝。 同時 recent pathology=recent scope slice 100 rows shows distribution_pathology alerts=['constant_target'] win_rate=0.0 avg_pnl=-0.0094 avg_quality=-0.2343 window=2026-04-18 17:54:06.647344->2026-04-19 00:18:39.001837 adverse_streak=100x0 (2026-04-18 17:54:06.647344->2026-04-19 00:18:39.001837) vs sibling prev_win_rate=0.01 Δwin_rate=-0.01 prev_quality=-0.1938 Δquality=-0.0405 prev_pnl=-0.0044 Δpnl=-0.005 top_shifts=feat_4h_dist_swing_low(3.5193→3.1703), feat_4h_dist_bb_lower(0.768→0.5423), feat_4h_bb_pct_b(0.2651→0.1875)。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_until_exact_support_ready` / support_route `exact_bucket_unsupported_block` / gap `50` / reference_scope `bull|CAUTION` / source `live_scope_spillover`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: live_scope_spillover），建議 profile=core_plus_macro_plus_all_4h；但 current live exact support 仍是 0/50；目前只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。

## Entry-quality component breakdown

- final entry_quality: **0.5465** / trade_floor **0.55** / gap **-0.0035**
- base_quality: **0.7198** × weight **0.75**
- structure_quality: **0.0267** × weight **0.25**
- base components: feat_4h_bias50=0.5855 (w=0.4, contrib=0.2342), feat_nose=0.879 (w=0.18, contrib=0.1582), feat_pulse=0.7068 (w=0.27, contrib=0.1908), feat_ear=0.9102 (w=0.15, contrib=0.1365)
- structure components: feat_4h_bb_pct_b=0.0 (w=0.34, contrib=0.0), feat_4h_dist_bb_lower=0.0 (w=0.33, contrib=0.0), feat_4h_dist_swing_low=0.081 (w=0.33, contrib=0.0267)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0035**
- base_group_max_entry_gain: **0.2102** | structure_group_max_entry_gain: **0.2433**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.0117, max_gain≈0.1244）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.0117), feat_pulse (Δscore≈0.0173), feat_nose (Δscore≈0.0259), feat_ear (Δscore≈0.0311)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `global` | 200 | 0.005 | -0.2141 | 0.2445 | 0.8147 | 0 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| broad `regime_gate+entry_quality_label` | 1 | 0.0 | -0.4283 | 0.3984 | 0.9957 | 0 | False |

## Shared shifts

- None
- worst_pathology_scope: **entry_quality_label** rows=200 win_rate=0.005 quality=-0.2141

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
