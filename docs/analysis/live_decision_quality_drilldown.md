# Live Decision-Quality Drilldown

- feature_timestamp: **2026-04-23 03:15:06.138534**
- target: `simulated_pyramid_win`
- live path: **bull / BLOCK / D**
- signal: **HOLD** @ confidence **0.4730**
- layers: **0 → 0**
- allowed_layers_raw_reason: `regime_gate_block`
- allowed_layers_reason: `decision_quality_below_trade_floor`
- execution_guardrail_reason: `decision_quality_below_trade_floor`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `decision_quality_below_trade_floor` | reason: `current live structure bucket `BLOCK|bull_q15_bias50_overextended_block|q15` 已完成 exact support closure（206/50），但 top-level live baseline 仍停在 entry_quality=0.4285，低於 trade floor 0.55；目前只能維持明確 no-deploy governance，不可把 support closure 或 component-experiment readiness 誤讀成 deployment closure。`
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_supported` | floor_cross `legal_component_experiment_after_support_ready`
- runtime closure summary: **current live bucket BLOCK|bull_q15_bias50_overextended_block|q15 已完成 exact support closure（206/50），但 top-level live baseline 仍停在 entry_quality=0.4285 (D) < trade floor 0.55；目前維持明確 no-deploy governance。 不可把 support closure 誤讀成 deployment closure。 exact-vs-spillover=同 quality 寬 scope 出現 bull|CAUTION spillover，378 rows / WR 77.8% / 品質 0.423，明顯劣於 exact live lane WR 5.5% / 品質 -0.163。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_non_current_live_scope` / support_route `exact_bucket_supported` / gap `0` / reference_scope `bull|CAUTION` / source `live_scope_spillover`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: live_scope_spillover），但 current live scope 是 bull|BLOCK；這代表 patch 描述的是 spillover / broader lane，而不是目前 current-live row 的 deploy patch。 即使 exact support 已達 minimum rows，也只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 reference-only patch 可見性；目前 current live 是 bull|BLOCK，但 patch 來自 bull|CAUTION spillover。 在 scope 對齊前，只可作治理 / 訓練參考，不可把它升級成 current-live deploy patch。

## Entry-quality component breakdown

- final entry_quality: **0.4285** / trade_floor **0.55** / gap **-0.1215**
- base_quality: **0.476** × weight **0.75**
- structure_quality: **0.286** × weight **0.25**
- base components: feat_4h_bias50=0.0 (w=0.4, contrib=0.0), feat_nose=0.768 (w=0.18, contrib=0.1382), feat_pulse=0.6975 (w=0.27, contrib=0.1883), feat_ear=0.996 (w=0.15, contrib=0.1494)
- structure components: feat_4h_bb_pct_b=0.3449 (w=0.34, contrib=0.1173), feat_4h_dist_bb_lower=0.1405 (w=0.33, contrib=0.0464), feat_4h_dist_swing_low=0.3708 (w=0.33, contrib=0.1224)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.1215**
- base_group_max_entry_gain: **0.3931** | structure_group_max_entry_gain: **0.1785**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.405, max_gain≈0.3）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.405)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+entry_quality_label` | 408 | 0.3897 | 0.1083 | 0.2282 | 0.6475 | 206 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 219 | 0.0548 | -0.1629 | 0.2351 | 0.7717 | 206 | True |
| narrow `regime_label+entry_quality_label` | 408 | 0.3897 | 0.1083 | 0.2282 | 0.6475 | 206 | False |
| broad `regime_gate+entry_quality_label` | 219 | 0.0548 | -0.1629 | 0.2351 | 0.7717 | 206 | True |

## Shared shifts

- feat_4h_dist_bb_lower (x2), feat_4h_bb_pct_b (x2), feat_4h_dist_swing_low (x2)
- worst_pathology_scope: **regime_label+regime_gate+entry_quality_label** rows=219 win_rate=0.0548 quality=-0.1629

## Interpretation

- if `runtime_blocker.type=circuit_breaker`, the current live row is blocked before the decision-quality contract is evaluated; treat q35/q15 diagnostics as background research, not deployable live routing.
- if `deployment_blocker.type=bull_q35_no_deploy_governance`, the current bull q35 lane is exact-supported but still not deployable because only non-discriminative unsafe reweight can cross the floor; do not describe it as simple support shortage or generic floor gap.
- if `q15_exact_supported_component_patch_applied=true` while `signal=HOLD`, describe the state as 'capacity opened but signal still HOLD' — not as patch missing, and not as automatic BUY readiness.
- exact live lane and chosen scope are separated on purpose: if exact lane is tiny or lacks current structure-bucket support, runtime must not trust it blindly.
- broader same-gate scope is still useful only as a structure-bucket fallback, not as the primary semantic representative of the live bull path.
- if the shared shift set remains dominated by `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`, the next fix should stay on 4H structure collapse rather than generic calibration tuning.
