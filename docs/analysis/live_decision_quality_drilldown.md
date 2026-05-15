# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-15 15:02:20.860934**
- target: `simulated_pyramid_win`
- live path: **熊市 / 阻塞 / C**
- signal: **HOLD** @ confidence **0.3426**
- layers: **0 → 0**
- allowed_layers_raw_reason: 市場閘門阻塞
- allowed_layers_reason: 精準樣本未達最小門檻
- execution_guardrail_reason: 精準樣本未達最小門檻
- runtime_blocker: None | reason: None
- deployment_blocker: 精準樣本未達最小門檻 | reason: 當前即時結構分桶 `阻塞｜結構品質阻塞｜q00` 的精準支持樣本仍停在 32/50（缺 18），支持路徑=精準樣本未達最小門檻，不可把舊範圍的支持閉環誤讀成部署閉環；決策品質仍為 B / 品質分數 0.5630；目前維持不可部署治理。
- support blocker summary: **精準樣本 32/50（缺口 18） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 建議修補方案 core_plus_macro_plus_all_4h 目前為僅供治理參考，適用範圍 牛市｜觀察、來源 牛市 4H 口袋消融 / 牛市崩落 q35；只能作治理參考，不是目前即時可部署修補。**
- support next action: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 保留建議修補方案可見但標示為僅參考；適用範圍與來源對齊、且精準樣本達標前不可放行。
- 精準樣本修補: **未啟用** | 支持路徑 **精準樣本未達最小門檻** | 跨越門檻 **已跨越門檻但精準樣本未就緒**
- runtime closure summary: **當前即時分桶 阻塞｜結構品質阻塞｜q00 的精準樣本仍未就緒（32/50，路徑=精準樣本未達最小門檻 / 治理=目前即時分桶精準樣本未達最小門檻）；較寬範圍 / 近似樣本 與建議修補方案 目前都只屬僅供治理參考，不可視為部署閉環。 建議修補方案=core_plus_macro_plus_all_4h (非目前即時範圍，僅供治理參考). 阻塞點=當前即時結構分桶 `阻塞｜結構品質阻塞｜q00` 的精準支持樣本仍停在 32/50（缺 18），支持路徑=精準樣本未達最小門檻，不可把舊範圍的支持閉環誤讀成部署閉環；決策品質仍為 B / 品質分數 0.5630；目前維持不可部署治理。 精準路徑與外溢對照：同 gate 寬範圍出現 牛市｜阻塞 外溢，180 筆 / 勝率 20.2% / 品質 -0.058，明顯劣於 精準即時路徑 勝率 100.0% / 品質 0.604。**
- q35 scaling audit: overall=None / redesign=None / runtime_gap=None / mode=None / next_patch=None
- q35 runtime truth: redesign_entry_quality=None / redesign_layers_after=None / runtime_layers=None / blocker=None / exact_support=None/None / support_gap=None
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=None
- 建議修補方案: **core_plus_macro_plus_all_4h** — 狀態：非目前即時範圍，僅供治理參考；精準樣本缺口 `18`；適用範圍 牛市｜觀察；來源 牛市 4H 口袋消融 / 牛市崩落 q35
- 建議修補特徵: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- 建議修補說明: 精準樣本 32/50（缺口 18） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 建議修補方案 core_plus_macro_plus_all_4h 目前為僅供治理參考，適用範圍 牛市｜觀察、來源 牛市 4H 口袋消融 / 牛市崩落 q35；只能作治理參考，不是目前即時可部署修補。
- 下一步: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 保留建議修補方案可見但標示為僅參考；適用範圍與來源對齊、且精準樣本達標前不可放行。

## Entry-quality component breakdown

- final entry_quality: **0.6147** / trade_floor **0.55** / gap **0.0647**
- 基礎品質: **0.8139** × 權重 **0.75**
- 結構品質: **0.0171** × 權重 **0.25**
- base components: feat_4h_bias50=0.8237 (w=0.4, contrib=0.3295), feat_nose=0.8202 (w=0.18, contrib=0.1476), feat_pulse=0.7446 (w=0.27, contrib=0.201), feat_ear=0.9048 (w=0.15, contrib=0.1357)
- structure components: feat_4h_bb_pct_b=0.0 (w=0.34, contrib=0.0), feat_4h_dist_bb_lower=0.0 (w=0.33, contrib=0.0), feat_4h_dist_swing_low=0.0517 (w=0.33, contrib=0.0171)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0**
- base_group_max_entry_gain: **0.1396** | structure_group_max_entry_gain: **0.2457**
- best_single_component: **None**（group=None, Δscore≈None, max_gain≈None）
- single-component floor crossers: None
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 32 | 1.0 | 0.6042 | 0.0871 | 0.2059 | 32 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 32 | 1.0 | 0.6042 | 0.0871 | 0.2059 | 32 | False |
| narrow `regime_label+entry_quality_label` | 73 | 0.9041 | 0.5574 | 0.1153 | 0.2931 | 32 | False |
| broad `regime_gate+entry_quality_label` | 32 | 1.0 | 0.6042 | 0.0871 | 0.2059 | 32 | False |

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
