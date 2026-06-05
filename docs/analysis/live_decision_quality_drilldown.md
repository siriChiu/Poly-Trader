# Live Decision-Quality Drilldown

- generated_at: **2026-06-05T03:46:22.921229Z**
- feature_timestamp: **2026-06-05 03:00:00**
- live_probe_generated_at: **2026-06-05T03:46:21.654036Z**
- target: `simulated_pyramid_win`
- live path: **熊市 / 阻塞 / C**
- signal: **觀望** @ confidence **0.5949**
- layers: **0 → 0**
- allowed_layers_raw_reason: 市場閘門阻塞
- allowed_layers_reason: 決策品質低於交易門檻; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade
- execution_guardrail_reason: 決策品質低於交易門檻; exact_live_lane_toxic_sub_bucket_current_bucket_blocks_trade
- runtime_blocker: None | reason: None
- deployment_blocker: exact_live_lane_toxic_sub_bucket_current_bucket | reason: 精準即時路徑 current bucket `阻塞｜bias200_below_min｜q00` 已被標記為 toxic sub-bucket (筆=131, win_rate=0.3053, 品質=-0.082)
- support blocker summary: **精準樣本 131/50（缺口 0） 已達可部署樣本門檻；是否放行仍以即時部署阻塞與執行層數為準。**
- support next action: 不要把樣本達標誤讀成部署已放行；繼續檢查執行層數、訊號與場館證據。
- current-bucket root cause: verdict=同路徑鄰近分桶更穩健 / patch=structure_component_scoring / feature=feat_4h_bb_pct_b / exact_support=131/50 / gap=0 / neighbor=阻塞｜bear_bias200_hard_block｜q00
- 精準樣本修補: **未啟用** | 支持路徑 **精準樣本已就緒** | 跨越門檻 **floor_already_crossed_and_support_ready**
- runtime closure summary: **當前即時分桶 阻塞｜bias200_below_min｜q00 已具精準樣本，但執行期仍被 exact_live_lane_toxic_sub_bucket_current_bucket 擋住；精準即時路徑 current bucket `阻塞｜bias200_below_min｜q00` 已被標記為 toxic sub-bucket (筆=131, win_rate=0.3053, 品質=-0.082)。目前保持僅觀察，不可把支持樣本閉環誤讀成部署閉環。 精準路徑與外溢對照：同品質寬範圍出現 盤整｜觀察 外溢，6 筆 / 勝率 0.0% / 品質 -0.433，明顯劣於 精準即時路徑 勝率 44.3% / 品質 0.039。**
- q35 scaling audit: overall=None / redesign=None / runtime_gap=None / mode=None / next_patch=None
- q35 runtime truth: redesign_entry_quality=None / redesign_layers_after=None / runtime_layers=None / blocker=None / exact_support=None/None / support_gap=None
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=None
- 建議修補方案: **None** — 狀態：None；精準樣本缺口 `None`；適用範圍 None；來源 None
- 建議修補特徵: None
- 建議修補說明: 精準樣本 131/50（缺口 0） 已達可部署樣本門檻；是否放行仍以即時部署阻塞與執行層數為準。
- 下一步: 不要把樣本達標誤讀成部署已放行；繼續檢查執行層數、訊號與場館證據。

## Entry-quality component breakdown

- final entry_quality: **0.5788** / trade_floor **0.55** / gap **0.0288**
- 基礎品質: **0.752** × 權重 **0.75**
- 結構品質: **0.0593** × 權重 **0.25**
- base components: feat_4h_bias50=1.0 (w=0.4, contrib=0.4), feat_nose=0.6667 (w=0.18, contrib=0.12), feat_pulse=0.3595 (w=0.27, contrib=0.0971), feat_ear=0.8994 (w=0.15, contrib=0.1349)
- structure components: feat_4h_bb_pct_b=0.0 (w=0.34, contrib=0.0), feat_4h_dist_bb_lower=0.0 (w=0.33, contrib=0.0), feat_4h_dist_swing_low=0.1796 (w=0.33, contrib=0.0593)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.186** | structure_group_max_entry_gain: **0.2352**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 183 | 0.4426 | 0.0388 | 0.2831 | 0.5108 | 131 | True |
| exact `regime_label+regime_gate+entry_quality_label` | 183 | 0.4426 | 0.0388 | 0.2831 | 0.5108 | 131 | True |
| narrow `regime_label+entry_quality_label` | 183 | 0.4426 | 0.0388 | 0.2831 | 0.5108 | 131 | True |
| broad `regime_gate+entry_quality_label` | 183 | 0.4426 | 0.0388 | 0.2831 | 0.5108 | 131 | True |

## Exact live-lane bucket diagnostic

- verdict: **toxic sub bucket identified** | bucket_count: **3**
- reason: 精準即時路徑 的 current bucket `阻塞｜bias200_below_min｜q00` 本身就是最差子 bucket，應直接升級成 執行期 veto / rejection 規則。
- toxic_bucket: 阻塞｜bias200_below_min｜q00

## Shared shifts

- feat_4h_dist_swing_low (x4), feat_4h_dist_bb_lower (x4), feat_4h_bb_pct_b (x4)
- worst_pathology_scope: **entry_quality_label** rows=189 win_rate=0.4286 quality=0.0239

## Interpretation

- 若 `runtime_blocker.type=circuit_breaker`，代表目前即時列在決策品質合約評估前已被熔斷；q35/q15 診斷只能作背景研究，不可當成即時部署路由。
- 若 `deployment_blocker.type=bull_q35_no_deploy_governance`，代表目前 bull q35 路徑雖有精準樣本，但只有非判別式高風險重配能跨過門檻；不得描述成單純樣本不足或一般門檻缺口。
- 若 `q15_exact_supported_component_patch_applied=true` 且 `signal=HOLD`，應描述為容量已開但訊號仍觀望；不是修補缺失，也不是自動買入就緒。
- 精準即時路徑與選用範圍刻意分離：若精準路徑樣本太少或缺少目前結構分桶支持，執行期不可盲目信任它。
- 較寬同 gate 範圍只可作結構分桶備援，不是目前即時牛市路徑的主要語義代表。
- 若共享位移仍由 `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b` 主導，下一步應持續聚焦 4H 結構塌陷，而不是泛化校準調參。
