# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-23 21:09:35.642850**
- target: `simulated_pyramid_win`
- live path: **盤整 / 觀察 / C**
- signal: **風控熔斷** @ confidence **0.5000**
- layers: **1 → 0**
- allowed_layers_raw_reason: 進場品質_C_single_layer
- allowed_layers_reason: 決策品質低於交易門檻; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade; 風控熔斷啟用中
- execution_guardrail_reason: 決策品質低於交易門檻; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade; 風控熔斷啟用中
- runtime_blocker: 風控熔斷 | reason: 最近 50 筆勝率: 18.00% < 30%
- deployment_blocker: 風控熔斷啟用中 | reason: 最近 50 筆勝率: 18.00% < 30%
- support blocker summary: **精準樣本 14/50（缺口 36） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版 #1238 0/50僅能當歷史參考，因校準視窗、進場品質不吻合目前支持語義，不可宣稱同一語義已閉環。**
- support next action: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。
- current-bucket root cause: verdict=執行期阻塞優先於分桶根因分析 / patch=None / feature=None / exact_support=10/50 / gap=40 / neighbor=觀察｜基線觀察（市場狀態 / 偏離）｜q15
- 精準樣本修補: **未啟用** | 支持路徑 **精準樣本未達最小門檻** | 跨越門檻 **執行期阻塞優先於跨門檻分析**
- runtime closure summary: **風控熔斷啟用中：最近 50 筆勝率: 18.00% < 30%；解除條件：連續虧損筆數 < 50 且最近 50 筆勝率 >= 30%；目前最近 50 筆只贏 9/50，至少還差 6 勝。 精準路徑與外溢對照：同 gate 寬範圍出現 盤整｜觀察 外溢，107 筆 / 勝率 2.9% / 品質 -0.283，明顯劣於 精準即時路徑 勝率 20.7% / 品質 -0.119。**
- q35 scaling audit: overall=執行期_阻塞點_preempts_q35_scaling / redesign=執行期_阻塞點_preempts_q35_scaling / runtime_gap=None / mode=defer_until_風控熔斷_releases / next_patch=release_風控熔斷_then_rerun_q35_scaling_audit
- q35 runtime truth: redesign_entry_quality=None / redesign_layers_after=None / runtime_layers=None / blocker=None / exact_support=None/None / support_gap=None
- q35 audit action: 先解除 canonical 風控熔斷 或至少接近 解除條件，再重跑 q35 scaling audit；在 breaker 仍有效時，不得把 q35 formula / calibration 當成本輪 live 阻塞點 主敘事。
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=None
- 建議修補方案: **None** — 狀態：None；精準樣本缺口 `None`；適用範圍 None；來源 None
- 建議修補特徵: None
- 建議修補說明: 精準樣本 14/50（缺口 36） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版 #1238 0/50僅能當歷史參考，因校準視窗、進場品質不吻合目前支持語義，不可宣稱同一語義已閉環。
- 下一步: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。

## Entry-quality component breakdown

- final entry_quality: **0.554** / trade_floor **0.55** / gap **0.004**
- 基礎品質: **0.5801** × 權重 **0.75**
- 結構品質: **0.4759** × 權重 **0.25**
- base components: feat_4h_bias50=0.5351 (w=0.4, contrib=0.214), feat_nose=0.1335 (w=0.18, contrib=0.024), feat_pulse=0.7908 (w=0.27, contrib=0.2135), feat_ear=0.8566 (w=0.15, contrib=0.1285)
- structure components: feat_4h_bb_pct_b=1.0 (w=0.34, contrib=0.34), feat_4h_dist_bb_lower=0.3691 (w=0.33, contrib=0.1218), feat_4h_dist_swing_low=0.0426 (w=0.33, contrib=0.0141)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.315** | structure_group_max_entry_gain: **0.131**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 82 | 0.2073 | -0.1188 | 0.2625 | 0.6799 | 14 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 82 | 0.2073 | -0.1188 | 0.2625 | 0.6799 | 14 | False |
| narrow `regime_label+entry_quality_label` | 82 | 0.2073 | -0.1188 | 0.2625 | 0.6799 | 14 | False |
| broad `regime_gate+entry_quality_label` | 114 | 0.2456 | -0.0975 | 0.2757 | 0.6973 | 14 | False |

## Exact live-lane bucket diagnostic

- verdict: **toxic sub bucket identified** | bucket_count: **2**
- reason: 精準即時路徑 的 current bucket `觀察｜基線觀察（市場狀態 / 偏離）｜q35` 本身就是最差子 bucket，應直接升級成 執行期 veto / rejection 規則。
- toxic_bucket: 觀察｜基線觀察（市場狀態 / 偏離）｜q35

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
