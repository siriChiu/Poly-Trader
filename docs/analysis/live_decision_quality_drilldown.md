# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-23 20:37:12.329530**
- target: `simulated_pyramid_win`
- live path: **bull / BLOCK / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `regime_gate_block`
- allowed_layers_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Recent 50-sample win rate: 26.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Recent 50-sample win rate: 26.00% < 30%`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_missing_proxy_reference_only` | floor_cross `runtime_blocker_preempts_floor_analysis`
- runtime closure summary: **circuit breaker active：Recent 50-sample win rate: 26.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 13/50，至少還差 2 勝。 exact-vs-spillover=同 regime 寬 scope 出現 bull|ALLOW spillover，447 rows / WR 36.0% / 品質 -0.005，明顯劣於 exact live lane WR — / 品質 —。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_non_current_live_scope` / support_route `exact_bucket_missing_proxy_reference_only` / gap `50` / reference_scope `bull|CAUTION` / source `bull_4h_pocket_ablation.bull_collapse_q35`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: bull_4h_pocket_ablation.bull_collapse_q35），但 current live scope 是 bull|BLOCK；這代表 patch 描述的是 spillover / broader lane，而不是目前 current-live row 的 deploy patch。 current live exact support 目前仍是 0/50，因此這條 patch 同時不具備 same-scope 與 exact-support 放行條件。 即使 exact support 已達 minimum rows，也只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 reference-only patch 可見性；目前 current live 是 bull|BLOCK，但 patch 來自 bull|CAUTION spillover。 在 scope 對齊前，只可作治理 / 訓練參考，不可把它升級成 current-live deploy patch。

## Entry-quality component breakdown

- final entry_quality: **0.3487** / trade_floor **0.55** / gap **-0.2013**
- base_quality: **0.353** × weight **0.75**
- structure_quality: **0.3356** × weight **0.25**
- base components: feat_4h_bias50=0.0527 (w=0.4, contrib=0.0211), feat_nose=0.5774 (w=0.18, contrib=0.1039), feat_pulse=0.2965 (w=0.27, contrib=0.0801), feat_ear=0.9865 (w=0.15, contrib=0.148)
- structure components: feat_4h_bb_pct_b=0.4387 (w=0.34, contrib=0.1492), feat_4h_dist_bb_lower=0.1768 (w=0.33, contrib=0.0584), feat_4h_dist_swing_low=0.3883 (w=0.33, contrib=0.1281)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.2013**
- base_group_max_entry_gain: **0.4853** | structure_group_max_entry_gain: **0.1661**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.671, max_gain≈0.2842）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.671)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+entry_quality_label` | 387 | 0.5685 | 0.2106 | 0.2576 | 0.5911 | 0 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 387 | 0.5685 | 0.2106 | 0.2576 | 0.5911 | 0 | False |
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
