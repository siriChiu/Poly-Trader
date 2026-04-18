# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-18 15:02:26.615581**
- target: `simulated_pyramid_win`
- live path: **bull / None / None**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **None → 0**
- allowed_layers_raw_reason: `circuit_breaker_preempts_runtime_sizing`
- allowed_layers_reason: `circuit_breaker_blocks_trade`
- execution_guardrail_reason: `circuit_breaker_blocks_trade`
- runtime_blocker: `circuit_breaker` | reason: `Consecutive loss streak: 74 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Consecutive loss streak: 74 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `None` | floor_cross `None`
- runtime closure summary: **circuit breaker active：Consecutive loss streak: 74 >= 50; Recent 50-sample win rate: 0.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 0/50，至少還差 15 勝。 同時 recent pathology=recent drift primary window 1000 rows; shows distribution_pathology; dominant_regime=bull (92%); alerts=['label_imbalance', 'regime_concentration', 'regime_shift']。**
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`

## Entry-quality component breakdown

- final entry_quality: **None** / trade_floor **None** / gap **None**
- base_quality: **None** × weight **None**
- structure_quality: **None** × weight **None**
- base components: None
- structure components: None

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **None**
- base_group_max_entry_gain: **None** | structure_group_max_entry_gain: **None**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**None** / required_bias50_cap≈**None**
- unavailable_reason: `Consecutive loss streak: 74 >= 50; Recent 50-sample win rate: 0.00% < 30%`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `unknown` | 0 | None | None | None | None | 0 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| broad `regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |

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
