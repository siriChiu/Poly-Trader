# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-23 20:09:22.255203**
- target: `simulated_pyramid_win`
- live path: **熊市 / 阻塞 / D**
- signal: **風控熔斷** @ confidence **0.5000**
- layers: **0 → 0**
- allowed_layers_raw_reason: 市場閘門阻塞
- allowed_layers_reason: 決策品質低於交易門檻; 精準樣本尚未建立，阻止交易; 風控熔斷啟用中
- execution_guardrail_reason: 決策品質低於交易門檻; 精準樣本尚未建立，阻止交易; 風控熔斷啟用中
- runtime_blocker: 風控熔斷 | reason: 最近 50 筆勝率: 12.00% < 30%
- deployment_blocker: 風控熔斷啟用中 | reason: 最近 50 筆勝率: 12.00% < 30%
- support blocker summary: **精準樣本 0/50（缺口 50） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版已就緒紀錄僅能當歷史參考，但語義證據仍未證明吻合目前支持語義，不可宣稱同一語義已閉環。**
- support next action: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。
- current-bucket root cause: verdict=執行期阻塞優先於分桶根因分析 / patch=None / feature=None / exact_support=0/50 / gap=50 / neighbor=阻塞｜結構品質阻塞｜q00
- 精準樣本修補: **未啟用** | 支持路徑 **exact_bucket_missing_exact_lane_proxy_only** | 跨越門檻 **執行期阻塞優先於跨門檻分析**
- runtime closure summary: **風控熔斷啟用中：最近 50 筆勝率: 12.00% < 30%；解除條件：連續虧損筆數 < 50 且最近 50 筆勝率 >= 30%；目前最近 50 筆只贏 6/50，至少還差 9 勝。 同時近期病態=近期範圍切片 100 筆 顯示 分佈病態 警示=['標籤失衡'] win_rate=0.06 avg_pnl=-0.0119 avg_品質=-0.2894 window=2026-05-21 23:12:48.600518->2026-05-22 21:09:18.467099 adverse_連續虧損筆數=86x0 (2026-05-21 23:12:48.600518->2026-05-22 18:01:39.630516) vs sibling prev_win_rate=0.24 Δwin_rate=-0.18 prev_品質=-0.0564 Δ品質=-0.233 prev_pnl=-0.0048 Δpnl=-0.0071 top_shifts=feat_4h_dist_swing_low(2.0249→0.9554), feat_4h_dist_bb_lower(1.2863→0.9049), feat_4h_bb_pct_b(0.5261→0.3731)。 精準路徑與外溢對照：同品質寬範圍出現 熊市｜觀察 外溢，76 筆 / 勝率 0.0% / 品質 -0.334，明顯劣於 精準即時路徑 勝率 — / 品質 —。**
- q35 scaling audit: overall=None / redesign=None / runtime_gap=None / mode=None / next_patch=None
- q35 runtime truth: redesign_entry_quality=None / redesign_layers_after=None / runtime_layers=None / blocker=None / exact_support=None/None / support_gap=None
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=None
- 建議修補方案: **None** — 狀態：None；精準樣本缺口 `None`；適用範圍 None；來源 None
- 建議修補特徵: None
- 建議修補說明: 精準樣本 0/50（缺口 50） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版已就緒紀錄僅能當歷史參考，但語義證據仍未證明吻合目前支持語義，不可宣稱同一語義已閉環。
- 下一步: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。

## Entry-quality component breakdown

- final entry_quality: **0.5221** / trade_floor **0.55** / gap **-0.0279**
- 基礎品質: **0.5934** × 權重 **0.75**
- 結構品質: **0.3084** × 權重 **0.25**
- base components: feat_4h_bias50=0.8115 (w=0.4, contrib=0.3246), feat_nose=0.1621 (w=0.18, contrib=0.0292), feat_pulse=0.3768 (w=0.27, contrib=0.1017), feat_ear=0.9191 (w=0.15, contrib=0.1379)
- structure components: feat_4h_bb_pct_b=0.6965 (w=0.34, contrib=0.2368), feat_4h_dist_bb_lower=0.2169 (w=0.33, contrib=0.0716), feat_4h_dist_swing_low=0.0 (w=0.33, contrib=0.0)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0279**
- base_group_max_entry_gain: **0.305** | structure_group_max_entry_gain: **0.1729**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.093, max_gain≈0.0566）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.093), feat_pulse (Δscore≈0.1378), feat_nose (Δscore≈0.2067), feat_4h_dist_bb_lower (Δscore≈0.3382)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `global` | 200 | 0.15 | -0.1729 | 0.3015 | 0.7592 | 0 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 0 | None | None | None | None | 0 | False |
| narrow `regime_label+entry_quality_label` | 6 | 0.0 | -0.334 | 0.4023 | 0.9403 | 0 | False |
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
