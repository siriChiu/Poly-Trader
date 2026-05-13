# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-13 20:01:21.063749**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Recent 50-sample win rate: 28.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Recent 50-sample win rate: 28.00% < 30%`
- support blocker summary: **exact support 37/50 (gap 13) 未達 current-live exact support；broader/proxy rows 僅可作治理參考。 建議 patch `core_plus_macro_plus_all_4h` 目前 status=`reference_only_non_current_live_scope`、reference_scope=`bull|CAUTION`、source=`bull_4h_pocket_ablation.bull_collapse_q35`；只能作治理參考，不是目前即時可部署修補。**
- support next action: 保持 no-deploy；先累積或回放同一 current-live structure bucket 的 exact lane 樣本，不可用 broader/proxy support 放行。 保留 recommended_patch 可見但 reference-only；適用範圍 / 來源對齊且 exact support 達標前不可放行。
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_present_but_below_minimum` | floor_cross `None`
- runtime closure summary: **circuit breaker active：Recent 50-sample win rate: 28.00% < 30%; release condition = streak < 50 且 recent 50 win rate >= 30%；目前 recent 50 只贏 14/50，至少還差 1 勝。 exact-vs-spillover=同 quality 寬 scope 出現 bull|BLOCK spillover，445 rows / WR 20.2% / 品質 -0.058，明顯劣於 exact live lane WR 58.2% / 品質 0.214。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_non_current_live_scope` / support_route `exact_bucket_present_but_below_minimum` / gap `13` / reference_scope `bull|CAUTION` / source `bull_4h_pocket_ablation.bull_collapse_q35`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: bull_4h_pocket_ablation.bull_collapse_q35），但 current live scope 是 chop|CAUTION；這代表 patch 描述的是 spillover / broader lane，而不是目前 current-live row 的 deploy patch。 current live exact support 目前仍是 37/50，因此這條 patch 同時不具備 same-scope 與 exact-support 放行條件。 即使 exact support 已達 minimum rows，也只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 reference-only patch 可見性；目前 current live 是 chop|CAUTION，但 patch 來自 bull|CAUTION spillover。 在 scope 對齊前，只可作治理 / 訓練參考，不可把它升級成 current-live deploy patch。

## Entry-quality component breakdown

- final entry_quality: **0.5149** / trade_floor **0.55** / gap **-0.0351**
- base_quality: **0.6457** × weight **0.75**
- structure_quality: **0.1224** × weight **0.25**
- base components: feat_4h_bias50=0.7531 (w=0.4, contrib=0.3012), feat_nose=0.5392 (w=0.18, contrib=0.0971), feat_pulse=0.3941 (w=0.27, contrib=0.1064), feat_ear=0.9399 (w=0.15, contrib=0.141)
- structure components: feat_4h_bb_pct_b=0.2827 (w=0.34, contrib=0.0961), feat_4h_dist_bb_lower=0.0796 (w=0.33, contrib=0.0263), feat_4h_dist_swing_low=0.0 (w=0.33, contrib=0.0)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0351**
- base_group_max_entry_gain: **0.2658** | structure_group_max_entry_gain: **0.2194**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.117, max_gain≈0.0741）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.117), feat_pulse (Δscore≈0.1733), feat_nose (Δscore≈0.26), feat_4h_bb_pct_b (Δscore≈0.4129)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 452 | 0.5819 | 0.2143 | 0.1418 | 0.4625 | 37 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 452 | 0.5819 | 0.2143 | 0.1418 | 0.4625 | 37 | False |
| narrow `regime_label+entry_quality_label` | 452 | 0.5819 | 0.2143 | 0.1418 | 0.4625 | 37 | False |
| broad `regime_gate+entry_quality_label` | 505 | 0.5683 | 0.2055 | 0.146 | 0.4678 | 37 | False |

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
