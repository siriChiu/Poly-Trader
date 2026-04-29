# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-29 03:01:44.926070**
- target: `simulated_pyramid_win`
- live path: **bear / CAUTION / C**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **1 → 0**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Consecutive loss streak: 108 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Consecutive loss streak: 108 >= 50; Recent 50-sample win rate: 0.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_missing_proxy_reference_only` | floor_cross `runtime_blocker_preempts_floor_analysis`
- runtime closure summary: **circuit breaker active：Consecutive loss streak: 108 >= 50; Recent 50-sample win rate: 0.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 0/50，至少還差 15 勝。 同時 recent pathology=recent scope slice 100 rows shows distribution_pathology alerts=['label_imbalance'] win_rate=0.18 avg_pnl=-0.0056 avg_quality=-0.1032 window=2026-04-25 21:45:12.464914->2026-04-28 03:45:03.734300 adverse_streak=82x0 (2026-04-27 05:15:51.099763->2026-04-28 03:45:03.734300) vs sibling prev_win_rate=0.75 Δwin_rate=-0.57 prev_quality=0.3316 Δquality=-0.4348 prev_pnl=0.0046 Δpnl=-0.0102 top_shifts=feat_4h_dist_swing_low(0.7299→0.3598), feat_4h_dist_bb_lower(1.2772→1.0172), feat_4h_bb_pct_b(0.4252→0.3363)。 exact-vs-spillover=同 quality 寬 scope 出現 chop|CAUTION spillover，4 rows / WR 0.0% / 品質 -0.148，明顯劣於 exact live lane WR — / 品質 —。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None` / reference_scope `None` / source `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.5781** / trade_floor **0.55** / gap **0.0281**
- base_quality: **0.69** × weight **0.75**
- structure_quality: **0.2424** × weight **0.25**
- base components: feat_4h_bias50=0.6988 (w=0.4, contrib=0.2795), feat_nose=0.3022 (w=0.18, contrib=0.0544), feat_pulse=0.7664 (w=0.27, contrib=0.2069), feat_ear=0.9945 (w=0.15, contrib=0.1492)
- structure components: feat_4h_bb_pct_b=0.5356 (w=0.34, contrib=0.1821), feat_4h_dist_bb_lower=0.1827 (w=0.33, contrib=0.0603), feat_4h_dist_swing_low=0.0 (w=0.33, contrib=0.0)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.2325** | structure_group_max_entry_gain: **0.1894**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_gate` | 225 | 0.4756 | 0.1249 | 0.1557 | 0.5464 | 28 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| broad `regime_gate+entry_quality_label` | 4 | 0.0 | -0.1484 | 0.201 | 0.7507 | 0 | False |

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
