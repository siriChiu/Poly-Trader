# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-19 11:02:07.606268**
- target: `simulated_pyramid_win`
- live path: **熊市 / 觀察 / C**
- signal: **風控熔斷** @ confidence **0.5000**
- layers: **1 → 0**
- allowed_layers_raw_reason: 進場品質_C_single_layer
- allowed_layers_reason: 決策品質低於交易門檻; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade; unsupported_live_structure_bucket_blocks_trade; 風控熔斷啟用中
- execution_guardrail_reason: 決策品質低於交易門檻; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade; unsupported_live_structure_bucket_blocks_trade; 風控熔斷啟用中
- runtime_blocker: 風控熔斷 | reason: 最近 50 筆勝率: 20.00% < 30%
- deployment_blocker: 風控熔斷啟用中 | reason: 最近 50 筆勝率: 20.00% < 30%
- support blocker summary: **精準樣本 1/50（缺口 49） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版 #1250 173/50僅能當歷史參考，因校準視窗、進場品質、市場狀態不吻合目前支持語義，不可宣稱同一語義已閉環。**
- support next action: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。
- current-bucket root cause: verdict=執行期阻塞優先於分桶根因分析 / patch=None / feature=None / exact_support=0/50 / gap=50 / neighbor=觀察｜結構品質觀察｜q15
- 精準樣本修補: **未啟用** | 支持路徑 **精準樣本未達最小門檻** | 跨越門檻 **執行期阻塞優先於跨門檻分析**
- runtime closure summary: **風控熔斷啟用中：最近 50 筆勝率: 20.00% < 30%；解除條件：連續虧損筆數 < 50 且最近 50 筆勝率 >= 30%；目前最近 50 筆只贏 10/50，至少還差 5 勝。 同時近期病態=近期範圍切片 100 筆 顯示 分佈病態 警示=['標籤失衡'] win_rate=0.17 avg_pnl=-0.0055 avg_品質=-0.1095 window=2026-05-16 17:00:00->2026-05-18 12:00:00 adverse_連續虧損筆數=31x0 (2026-05-16 23:02:20.327320->2026-05-17 12:01:57.351618) vs sibling prev_win_rate=0.3 Δwin_rate=-0.13 prev_品質=-0.0396 Δ品質=-0.0699 prev_pnl=-0.0056 Δpnl=0.0001 top_shifts=feat_4h_dist_bb_lower(0.36→0.929), feat_4h_bb_pct_b(0.1406→0.3683), feat_4h_dist_swing_low(-0.2325→-0.0473)。 精準路徑與外溢對照：同 gate 寬範圍出現 盤整｜觀察 外溢，20 筆 / 勝率 0.0% / 品質 -0.423，明顯劣於 精準即時路徑 勝率 17.4% / 品質 -0.114。**
- q35 scaling audit: overall=None / redesign=None / runtime_gap=None / mode=None / next_patch=None
- q35 runtime truth: redesign_entry_quality=None / redesign_layers_after=None / runtime_layers=None / blocker=None / exact_support=None/None / support_gap=None
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=None
- 建議修補方案: **None** — 狀態：None；精準樣本缺口 `None`；適用範圍 None；來源 None
- 建議修補特徵: None
- 建議修補說明: 精準樣本 1/50（缺口 49） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版 #1250 173/50僅能當歷史參考，因校準視窗、進場品質、市場狀態不吻合目前支持語義，不可宣稱同一語義已閉環。
- 下一步: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。

## Entry-quality component breakdown

- final entry_quality: **0.6791** / trade_floor **0.55** / gap **0.1291**
- 基礎品質: **0.8144** × 權重 **0.75**
- 結構品質: **0.273** × 權重 **0.25**
- base components: feat_4h_bias50=1.0 (w=0.4, contrib=0.4), feat_nose=0.461 (w=0.18, contrib=0.083), feat_pulse=0.6849 (w=0.27, contrib=0.1849), feat_ear=0.9769 (w=0.15, contrib=0.1465)
- structure components: feat_4h_bb_pct_b=0.5177 (w=0.34, contrib=0.176), feat_4h_dist_bb_lower=0.166 (w=0.33, contrib=0.0548), feat_4h_dist_swing_low=0.1278 (w=0.33, contrib=0.0422)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.1392** | structure_group_max_entry_gain: **0.1818**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+entry_quality_label` | 150 | 0.2133 | -0.0862 | 0.2287 | 0.6707 | 1 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 92 | 0.1739 | -0.1138 | 0.2578 | 0.7 | 1 | True |
| narrow `regime_label+entry_quality_label` | 150 | 0.2133 | -0.0862 | 0.2287 | 0.6707 | 1 | True |
| broad `regime_gate+entry_quality_label` | 92 | 0.1739 | -0.1138 | 0.2578 | 0.7 | 1 | True |

## Exact live-lane bucket diagnostic

- verdict: **toxic sub bucket identified** | bucket_count: **3**
- reason: 精準即時路徑 的 current bucket `觀察｜基線觀察（市場狀態 / 偏離）｜q15` 本身就是最差子 bucket，應直接升級成 執行期 veto / rejection 規則。
- toxic_bucket: 觀察｜基線觀察（市場狀態 / 偏離）｜q15

## Shared shifts

- feat_4h_dist_bb_lower (x2), feat_4h_bb_pct_b (x2), feat_4h_dist_swing_low (x2)
- worst_pathology_scope: **regime_label+entry_quality_label** rows=150 win_rate=0.2133 quality=-0.0862

## Interpretation

- 若 `runtime_blocker.type=circuit_breaker`，代表目前即時列在決策品質合約評估前已被熔斷；q35/q15 診斷只能作背景研究，不可當成即時部署路由。
- 若 `deployment_blocker.type=bull_q35_no_deploy_governance`，代表目前 bull q35 路徑雖有精準樣本，但只有非判別式高風險重配能跨過門檻；不得描述成單純樣本不足或一般門檻缺口。
- 若 `q15_exact_supported_component_patch_applied=true` 且 `signal=HOLD`，應描述為容量已開但訊號仍觀望；不是修補缺失，也不是自動買入就緒。
- 精準即時路徑與選用範圍刻意分離：若精準路徑樣本太少或缺少目前結構分桶支持，執行期不可盲目信任它。
- 較寬同 gate 範圍只可作結構分桶備援，不是目前即時牛市路徑的主要語義代表。
- 若共享位移仍由 `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b` 主導，下一步應持續聚焦 4H 結構塌陷，而不是泛化校準調參。
