# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-17 02:01:33.543175**
- target: `simulated_pyramid_win`
- live path: **熊市 / 阻塞 / B**
- signal: **CIRCUIT_BREAKER** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: 市場閘門阻塞
- allowed_layers_reason: 決策品質低於交易門檻; 風控熔斷啟用中
- execution_guardrail_reason: 決策品質低於交易門檻; 風控熔斷啟用中
- runtime_blocker: circuit_breaker | reason: 連續虧損筆數： 101 >= 50; 最近 50 筆勝率: 0.00% < 30%
- deployment_blocker: 風控熔斷啟用中 | reason: 連續虧損筆數： 101 >= 50; 最近 50 筆勝率: 0.00% < 30%
- support blocker summary: **精準樣本 0/50（缺口 50） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。**
- support next action: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。
- 精準樣本修補: **未啟用** | 支持路徑 **精準樣本尚未建立** | 跨越門檻 **執行期阻塞優先於跨門檻分析**
- runtime closure summary: **風控熔斷啟用中：連續虧損筆數： 101 >= 50; 最近 50 筆勝率: 0.00% < 30%；解除條件：連續虧損筆數 < 50 且最近 50 筆勝率 >= 30%；目前最近 50 筆只贏 0/50，至少還差 15 勝。 精準路徑與外溢對照：同 regime 寬範圍出現 熊市｜阻塞 外溢，87 筆 / 勝率 25.0% / 品質 -0.049，明顯劣於 精準即時路徑 勝率 — / 品質 —。**
- q35 scaling audit: overall=None / redesign=None / runtime_gap=None / mode=None / next_patch=None
- q35 runtime truth: redesign_entry_quality=None / redesign_layers_after=None / runtime_layers=None / blocker=None / exact_support=None/None / support_gap=None
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=None
- 建議修補方案: **None** — 狀態：None；精準樣本缺口 `None`；適用範圍 None；來源 None
- 建議修補特徵: None
- 建議修補說明: 精準樣本 0/50（缺口 50） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。
- 下一步: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。

## Entry-quality component breakdown

- final entry_quality: **0.7176** / trade_floor **0.55** / gap **0.1676**
- 基礎品質: **0.9194** × 權重 **0.75**
- 結構品質: **0.1122** × 權重 **0.25**
- base components: feat_4h_bias50=1.0 (w=0.4, contrib=0.4), feat_nose=0.9257 (w=0.18, contrib=0.1666), feat_pulse=0.7664 (w=0.27, contrib=0.2069), feat_ear=0.9721 (w=0.15, contrib=0.1458)
- structure components: feat_4h_bb_pct_b=0.2535 (w=0.34, contrib=0.0862), feat_4h_dist_bb_lower=0.0788 (w=0.33, contrib=0.026), feat_4h_dist_swing_low=0.0 (w=0.33, contrib=0.0)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.0604** | structure_group_max_entry_gain: **0.222**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label` | 87 | 0.5172 | 0.2079 | 0.211 | 0.5455 | 48 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| broad `regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |

## Exact live-lane bucket diagnostic

- verdict: **no exact lane 筆** | bucket_count: **0**
- reason: 精準即時路徑 沒有 筆，無法做子 bucket 診斷。
- toxic_bucket: None

## Shared shifts

- None
- worst_pathology_scope: **None** rows=None win_rate=None quality=None

## Interpretation

- 若 `runtime_blocker.type=circuit_breaker`，代表目前即時列在決策品質合約評估前已被熔斷；q35/q15 診斷只能作背景研究，不可當成即時部署路由。
- 若 `deployment_blocker.type=bull_q35_no_deploy_governance`，代表目前 bull q35 路徑雖有精準樣本，但只有非判別式高風險重配能跨過門檻；不得描述成單純樣本不足或一般門檻缺口。
- 若 `q15_exact_supported_component_patch_applied=true` 且 `signal=HOLD`，應描述為容量已開但訊號仍觀望；不是修補缺失，也不是自動買入就緒。
- 精準即時路徑與選用範圍刻意分離：若精準路徑樣本太少或缺少目前結構分桶支持，執行期不可盲目信任它。
- 較寬同 gate 範圍只可作結構分桶備援，不是目前即時牛市路徑的主要語義代表。
- 若共享位移仍由 `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b` 主導，下一步應持續聚焦 4H 結構塌陷，而不是泛化校準調參。
