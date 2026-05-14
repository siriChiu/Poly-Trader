# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-14 14:02:03.138802**
- target: `simulated_pyramid_win`
- live path: **bear / CAUTION / C**
- signal: **HOLD** @ confidence **0.3206**
- layers: **1 → 0**
- allowed_layers_raw_reason: `entry_quality_C_single_layer`
- allowed_layers_reason: `under_minimum_exact_live_structure_bucket`
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `under_minimum_exact_live_structure_bucket` | reason: `current live structure bucket 已有 exact rows，但仍低於 deployment-grade minimum support；在 support 補滿前，runtime 只能維持 guardrail，不可把這條 lane 視為已可部署。`
- support blocker summary: **exact support 20/50 (gap 30) 未達 current-live exact support；broader/proxy rows 僅可作治理參考。 建議 patch `core_plus_macro_plus_all_4h` 目前 status=`reference_only_non_current_live_scope`、reference_scope=`bull|CAUTION`、source=`live_scope_spillover`；只能作治理參考，不是目前即時可部署修補。**
- support next action: 保持 no-deploy；先累積或回放同一 current-live structure bucket 的 exact lane 樣本，不可用 broader/proxy support 放行。 保留 recommended_patch 可見但 reference-only；適用範圍 / 來源對齊且 exact support 達標前不可放行。
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_present_but_below_minimum` | floor_cross `floor_crossed_but_support_not_ready`
- runtime closure summary: **當前即時分桶 CAUTION|structure_quality_caution|q15 的精準樣本仍未就緒（20/50，路徑=精準樣本未達最小門檻 / 治理=exact_live_bucket_present_but_below_minimum）；較寬範圍 / 近似樣本 與建議修補方案 目前都只屬僅供治理參考，不可視為部署閉環。 建議修補方案=core_plus_macro_plus_all_4h (僅供治理參考_non_current_live_範圍). 阻塞點=當前即時結構分桶 已有 exact 筆，但仍低於 部署-grade minimum support；在 support 補滿前，執行期 只能維持 guardrail，不可把這條 lane 視為已可部署。。 精準路徑與外溢對照：同 gate 寬 範圍 出現 牛市|警戒 外溢，576 筆 / 勝率 41.9% / 品質 0.103，明顯劣於 精準即時路徑 勝率 65.0% / 品質 0.350。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **core_plus_macro_plus_all_4h** / status `reference_only_non_current_live_scope` / support_route `exact_bucket_present_but_below_minimum` / gap `30` / reference_scope `bull|CAUTION` / source `live_scope_spillover`
- recommended_patch_features: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- recommended_patch_reason: 參考 patch 來自 bull|CAUTION（source: live_scope_spillover），但 current live scope 是 bear|CAUTION；這代表 patch 描述的是 spillover / broader lane，而不是目前 current-live row 的 deploy patch。 current live exact support 目前仍是 20/50，因此這條 patch 同時不具備 same-scope 與 exact-support 放行條件。 即使 exact support 已達 minimum rows，也只能作治理 / 訓練參考，不可直接放行 runtime。
- recommended_patch_action: 維持 reference-only patch 可見性；目前 current live 是 bear|CAUTION，但 patch 來自 bull|CAUTION spillover。 在 scope 對齊前，只可作治理 / 訓練參考，不可把它升級成 current-live deploy patch。

## Entry-quality component breakdown

- final entry_quality: **0.5596** / trade_floor **0.55** / gap **0.0096**
- base_quality: **0.6366** × weight **0.75**
- structure_quality: **0.3283** × weight **0.25**
- base components: feat_4h_bias50=0.6749 (w=0.4, contrib=0.27), feat_nose=0.5083 (w=0.18, contrib=0.0915), feat_pulse=0.4866 (w=0.27, contrib=0.1314), feat_ear=0.9587 (w=0.15, contrib=0.1438)
- structure components: feat_4h_bb_pct_b=0.658 (w=0.34, contrib=0.2237), feat_4h_dist_bb_lower=0.1809 (w=0.33, contrib=0.0597), feat_4h_dist_swing_low=0.1359 (w=0.33, contrib=0.0449)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.2725** | structure_group_max_entry_gain: **0.168**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_gate+entry_quality_label` | 104 | 0.6827 | 0.3352 | 0.1356 | 0.3741 | 20 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 20 | 0.65 | 0.3499 | 0.1753 | 0.4031 | 20 | False |
| narrow `regime_label+entry_quality_label` | 42 | 0.8333 | 0.4508 | 0.1375 | 0.3268 | 20 | False |
| broad `regime_gate+entry_quality_label` | 104 | 0.6827 | 0.3352 | 0.1356 | 0.3741 | 20 | False |

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
