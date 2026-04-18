# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-18 23:45:18.269444**
- target: `simulated_pyramid_win`
- live path: **bull / BLOCK / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `regime_gate_block`
- allowed_layers_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Consecutive loss streak: 238 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Consecutive loss streak: 238 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_missing_exact_lane_proxy_only` | floor_cross `runtime_blocker_preempts_floor_analysis`
- runtime closure summary: **circuit breaker active：Consecutive loss streak: 238 >= 50; Recent 50-sample win rate: 0.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 0/50，至少還差 15 勝。 同時 recent pathology=recent scope slice 100 rows shows distribution_pathology alerts=['constant_target'] win_rate=0.0 avg_pnl=-0.0095 avg_quality=-0.287 window=2026-04-17 19:49:20.724170->2026-04-18 00:29:49.821627 adverse_streak=100x0 (2026-04-17 19:49:20.724170->2026-04-18 00:29:49.821627) vs sibling prev_win_rate=0.0 Δwin_rate=0.0 prev_quality=-0.2825 Δquality=-0.0045 prev_pnl=-0.0104 Δpnl=0.0009 top_shifts=feat_4h_dist_bb_lower(3.88→3.0501), feat_4h_bb_pct_b(1.1183→0.9042), feat_4h_dist_swing_low(5.4023→5.2472)。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro** / status `reference_only_until_exact_support_ready` / support_route `exact_bucket_missing_exact_lane_proxy_only` / gap `50`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: bull|CAUTION spillover 已有正式 patch 建議（core_plus_macro），但 current live exact support 仍是 0/50；目前只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。

## Entry-quality component breakdown

- final entry_quality: **0.3715** / trade_floor **0.55** / gap **-0.1785**
- base_quality: **0.4189** × weight **0.75**
- structure_quality: **0.229** × weight **0.25**
- base components: feat_4h_bias50=0.0156 (w=0.4, contrib=0.0063), feat_nose=0.4869 (w=0.18, contrib=0.0876), feat_pulse=0.6487 (w=0.27, contrib=0.1752), feat_ear=0.9993 (w=0.15, contrib=0.1499)
- structure components: feat_4h_bb_pct_b=0.2674 (w=0.34, contrib=0.0909), feat_4h_dist_bb_lower=0.0964 (w=0.33, contrib=0.0318), feat_4h_dist_swing_low=0.3221 (w=0.33, contrib=0.1063)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.1785**
- base_group_max_entry_gain: **0.4358** | structure_group_max_entry_gain: **0.1927**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.595, max_gain≈0.2953）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.595)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+entry_quality_label` | 199 | 0.0 | -0.2848 | 0.3783 | 0.8446 | 0 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 199 | 0.0 | -0.2848 | 0.3783 | 0.8446 | 0 | True |
| broad `regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |

## Shared shifts

- feat_4h_dist_bb_lower (x2), feat_4h_bb_pct_b (x2), feat_4h_dist_swing_low (x2)
- worst_pathology_scope: **regime_label+entry_quality_label** rows=199 win_rate=0.0 quality=-0.2848

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
