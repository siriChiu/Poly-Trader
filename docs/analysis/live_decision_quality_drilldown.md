# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-20 10:27:48.585965**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Recent 50-sample win rate: 26.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Recent 50-sample win rate: 26.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_unsupported_block` | floor_cross `None`
- runtime closure summary: **circuit breaker active：Recent 50-sample win rate: 26.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 13/50，至少還差 2 勝。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_until_exact_support_ready` / support_route `exact_bucket_unsupported_block` / gap `50` / reference_scope `bull|CAUTION` / source `bull_4h_pocket_ablation.bull_collapse_q35`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: bull_4h_pocket_ablation.bull_collapse_q35），建議 profile=core_plus_macro_plus_all_4h；但 current live exact support 仍是 0/50；目前只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。

## Entry-quality component breakdown

- final entry_quality: **0.4576** / trade_floor **0.55** / gap **-0.0924**
- base_quality: **0.4821** × weight **0.75**
- structure_quality: **0.3842** × weight **0.25**
- base components: feat_4h_bias50=0.2538 (w=0.4, contrib=0.1015), feat_nose=0.3217 (w=0.18, contrib=0.0579), feat_pulse=0.668 (w=0.27, contrib=0.1804), feat_ear=0.9488 (w=0.15, contrib=0.1423)
- structure components: feat_4h_bb_pct_b=0.6372 (w=0.34, contrib=0.2166), feat_4h_dist_bb_lower=0.2476 (w=0.33, contrib=0.0817), feat_4h_dist_swing_low=0.2602 (w=0.33, contrib=0.0859)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0924**
- base_group_max_entry_gain: **0.3885** | structure_group_max_entry_gain: **0.1539**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.308, max_gain≈0.2239）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.308)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 45 | 0.3333 | -0.0123 | 0.3647 | 0.6817 | 0 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 45 | 0.3333 | -0.0123 | 0.3647 | 0.6817 | 0 | False |
| narrow `regime_label+entry_quality_label` | 45 | 0.3333 | -0.0123 | 0.3647 | 0.6817 | 0 | False |
| broad `regime_gate+entry_quality_label` | 45 | 0.3333 | -0.0123 | 0.3647 | 0.6817 | 0 | False |

## Shared shifts

- None
- worst_pathology_scope: **entry_quality_label** rows=200 win_rate=0.075 quality=-0.1716

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
