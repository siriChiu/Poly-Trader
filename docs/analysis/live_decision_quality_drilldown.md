# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-13 19:01:52.164394**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / C**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **1 → 0**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade; circuit_breaker_active`
- execution_guardrail_reason: `exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Recent 50-sample win rate: 28.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Recent 50-sample win rate: 28.00% < 30%`
- support blocker summary: **exact support 18/50 (gap 32) 未達 current-live exact support；broader/proxy rows 僅可作治理參考。 建議 patch `core_plus_macro_plus_all_4h` 目前 status=`reference_only_non_current_live_scope`、reference_scope=`bull|CAUTION`、source=`live_scope_spillover`；只能作治理參考，不是目前即時可部署修補。**
- support next action: 保持 no-deploy；先累積或回放同一 current-live structure bucket 的 exact lane 樣本，不可用 broader/proxy support 放行。 保留 recommended_patch 可見但 reference-only；適用範圍 / 來源對齊且 exact support 達標前不可放行。
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_present_but_below_minimum` | floor_cross `None`
- runtime closure summary: **circuit breaker active：Recent 50-sample win rate: 28.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 14/50，至少還差 1 勝。 exact-vs-spillover=同 gate 寬 scope 出現 bull|CAUTION spillover，526 rows / WR 41.9% / 品質 0.103，明顯劣於 exact live lane WR 81.0% / 品質 0.499。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_non_current_live_scope` / support_route `exact_bucket_present_but_below_minimum` / gap `32` / reference_scope `bull|CAUTION` / source `live_scope_spillover`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: live_scope_spillover），但 current live scope 是 chop|CAUTION；這代表 patch 描述的是 spillover / broader lane，而不是目前 current-live row 的 deploy patch。 current live exact support 目前仍是 18/50，因此這條 patch 同時不具備 same-scope 與 exact-support 放行條件。 即使 exact support 已達 minimum rows，也只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 reference-only patch 可見性；目前 current live 是 chop|CAUTION，但 patch 來自 bull|CAUTION spillover。 在 scope 對齊前，只可作治理 / 訓練參考，不可把它升級成 current-live deploy patch。

## Entry-quality component breakdown

- final entry_quality: **0.5607** / trade_floor **0.55** / gap **0.0107**
- base_quality: **0.7254** × weight **0.75**
- structure_quality: **0.0666** × weight **0.25**
- base components: feat_4h_bias50=0.7822 (w=0.4, contrib=0.3129), feat_nose=0.5284 (w=0.18, contrib=0.0951), feat_pulse=0.6535 (w=0.27, contrib=0.1764), feat_ear=0.9399 (w=0.15, contrib=0.141)
- structure components: feat_4h_bb_pct_b=0.1533 (w=0.34, contrib=0.0521), feat_4h_dist_bb_lower=0.0439 (w=0.33, contrib=0.0145), feat_4h_dist_swing_low=0.0 (w=0.33, contrib=0.0)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.206** | structure_group_max_entry_gain: **0.2334**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 42 | 0.8095 | 0.499 | 0.0692 | 0.2554 | 18 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 42 | 0.8095 | 0.499 | 0.0692 | 0.2554 | 18 | False |
| narrow `regime_label+entry_quality_label` | 42 | 0.8095 | 0.499 | 0.0692 | 0.2554 | 18 | False |
| broad `regime_gate+entry_quality_label` | 62 | 0.7581 | 0.4509 | 0.1034 | 0.3031 | 18 | False |

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
