# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-13 23:02:08.190973**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- execution_guardrail_reason: `decision_quality_below_trade_floor; circuit_breaker_active`
- runtime_blocker: `circuit_breaker` | reason: `Recent 50-sample win rate: 28.00% < 30%`
- deployment_blocker: `circuit_breaker_active` | reason: `Recent 50-sample win rate: 28.00% < 30%`
- support blocker summary: **exact support 190/50 (gap 0) 已達 deployable support；deployment 仍以 `circuit_breaker_active` 與 allowed_layers 為準。**
- support next action: 不要把 support closure 誤讀成 deployment closure；繼續檢查 allowed_layers / signal / venue proof。
- q15 exact-supported patch: **inactive** | support_route `exact_bucket_supported` | floor_cross `None`
- runtime closure summary: **風控熔斷啟用中：最近 50 筆勝率: 28.00% < 30%；解除條件：連續虧損筆數 < 50 且最近 50 筆勝率 >= 30%；目前最近 50 筆只贏 14/50，至少還差 1 勝。 精準路徑與外溢對照：同品質寬範圍 出現 牛市|阻塞 外溢，442 筆 / 勝率 20.2% / 品質 -0.058，明顯劣於 精準即時路徑 勝率 58.7% / 品質 0.220。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- recommended_patch: **None** / status `None` / support_route `None` / gap `None` / reference_scope `None` / source `None`
- recommended_patch_features: None
- recommended_patch_reason: None
- recommended_patch_action: None

## Entry-quality component breakdown

- final entry_quality: **0.5275** / trade_floor **0.55** / gap **-0.0225**
- base_quality: **0.679** × weight **0.75**
- structure_quality: **0.0731** × weight **0.25**
- base components: feat_4h_bias50=0.8137 (w=0.4, contrib=0.3255), feat_nose=0.3604 (w=0.18, contrib=0.0649), feat_pulse=0.5165 (w=0.27, contrib=0.1395), feat_ear=0.9946 (w=0.15, contrib=0.1492)
- structure components: feat_4h_bb_pct_b=0.1687 (w=0.34, contrib=0.0573), feat_4h_dist_bb_lower=0.0476 (w=0.33, contrib=0.0157), feat_4h_dist_swing_low=0.0 (w=0.33, contrib=0.0)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0225**
- base_group_max_entry_gain: **0.2407** | structure_group_max_entry_gain: **0.2318**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.075, max_gain≈0.0559）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.075), feat_pulse (Δscore≈0.1111), feat_nose (Δscore≈0.1667), feat_4h_bb_pct_b (Δscore≈0.2647)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 419 | 0.5871 | 0.2197 | 0.1416 | 0.4637 | 190 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 419 | 0.5871 | 0.2197 | 0.1416 | 0.4637 | 190 | False |
| narrow `regime_label+entry_quality_label` | 419 | 0.5871 | 0.2197 | 0.1416 | 0.4637 | 190 | False |
| broad `regime_gate+entry_quality_label` | 472 | 0.572 | 0.2096 | 0.1462 | 0.4692 | 190 | False |

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
