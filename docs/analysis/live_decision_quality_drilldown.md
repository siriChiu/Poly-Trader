# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-15 18:02:01.442804**
- target: `simulated_pyramid_win`
- live path: **熊市 / 阻塞 / D**
- signal: **HOLD** @ confidence **0.3784**
- layers: **0 → 0**
- allowed_layers_raw_reason: 市場閘門阻塞
- allowed_layers_reason: 精準樣本未達最小門檻
- execution_guardrail_reason: 精準樣本未達最小門檻
- runtime_blocker: None | reason: None
- deployment_blocker: 精準樣本未達最小門檻 | reason: 當前即時結構分桶 `阻塞｜結構品質阻塞｜q00` 的精準支持樣本仍停在 2/50（缺 48），支持路徑=精準樣本未達最小門檻，不可把舊範圍的支持閉環誤讀成部署閉環；決策品質仍為 D / 品質分數 0.3296；目前維持不可部署治理。
- support blocker summary: **精準樣本 2/50（缺口 48） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 建議修補方案 core_plus_macro_plus_all_4h 目前為僅供治理參考，適用範圍 牛市｜觀察、來源 live_範圍_外溢；只能作治理參考，不是目前即時可部署修補。**
- support next action: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 保留建議修補方案可見但標示為僅參考；適用範圍與來源對齊、且精準樣本達標前不可放行。
- 精準樣本修補: **未啟用** | 支持路徑 **精準樣本未達最小門檻** | 跨越門檻 **數學上可跨門檻，但精準樣本未達標前不可啟用**
- runtime closure summary: **當前即時分桶 阻塞｜結構品質阻塞｜q00 的精準樣本仍未就緒（2/50，路徑=精準樣本未達最小門檻 / 治理=目前即時分桶精準樣本未達最小門檻）；較寬範圍 / 近似樣本 與建議修補方案 目前都只屬僅供治理參考，不可視為部署閉環。 建議修補方案=core_plus_macro_plus_all_4h (非目前即時範圍，僅供治理參考). 阻塞點=當前即時結構分桶 `阻塞｜結構品質阻塞｜q00` 的精準支持樣本仍停在 2/50（缺 48），支持路徑=精準樣本未達最小門檻，不可把舊範圍的支持閉環誤讀成部署閉環；決策品質仍為 D / 品質分數 0.3296；目前維持不可部署治理。 精準路徑與外溢對照：同品質寬範圍出現 牛市｜觀察 外溢，434 筆 / 勝率 22.2% / 品質 -0.067，明顯劣於 精準即時路徑 勝率 100.0% / 品質 0.670。**
- q35 scaling audit: overall=None / redesign=None / runtime_gap=None / mode=None / next_patch=None
- q35 runtime truth: redesign_entry_quality=None / redesign_layers_after=None / runtime_layers=None / blocker=None / exact_support=None/None / support_gap=None
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=None
- 建議修補方案: **core_plus_macro_plus_all_4h** — 狀態：非目前即時範圍，僅供治理參考；精準樣本缺口 `48`；適用範圍 牛市｜觀察；來源 live_範圍_外溢
- 建議修補特徵: feat_4h_dist_swing_low, feat_4h_dist_bb_lower, feat_4h_bb_pct_b
- 建議修補說明: 精準樣本 2/50（缺口 48） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 建議修補方案 core_plus_macro_plus_all_4h 目前為僅供治理參考，適用範圍 牛市｜觀察、來源 live_範圍_外溢；只能作治理參考，不是目前即時可部署修補。
- 下一步: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 保留建議修補方案可見但標示為僅參考；適用範圍與來源對齊、且精準樣本達標前不可放行。

## Entry-quality component breakdown

- final entry_quality: **0.5343** / trade_floor **0.55** / gap **-0.0157**
- 基礎品質: **0.6847** × 權重 **0.75**
- 結構品質: **0.083** × 權重 **0.25**
- base components: feat_4h_bias50=0.7336 (w=0.4, contrib=0.2934), feat_nose=0.6589 (w=0.18, contrib=0.1186), feat_pulse=0.4897 (w=0.27, contrib=0.1322), feat_ear=0.9365 (w=0.15, contrib=0.1405)
- structure components: feat_4h_bb_pct_b=0.117 (w=0.34, contrib=0.0398), feat_4h_dist_bb_lower=0.0373 (w=0.33, contrib=0.0123), feat_4h_dist_swing_low=0.0938 (w=0.33, contrib=0.0309)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0157**
- base_group_max_entry_gain: **0.2363** | structure_group_max_entry_gain: **0.2293**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.0523, max_gain≈0.0799）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.0523), feat_pulse (Δscore≈0.0775), feat_nose (Δscore≈0.1163), feat_4h_bb_pct_b (Δscore≈0.1847)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+entry_quality_label` | 36 | 0.6944 | 0.3669 | 0.1826 | 0.3813 | 2 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 2 | 1.0 | 0.6698 | 0.1074 | 0.2144 | 2 | False |
| narrow `regime_label+entry_quality_label` | 36 | 0.6944 | 0.3669 | 0.1826 | 0.3813 | 2 | False |
| broad `regime_gate+entry_quality_label` | 50 | 0.28 | -0.0164 | 0.2588 | 0.6048 | 2 | False |

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
