# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-15 09:12:42.307933**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **HOLD** @ confidence **0.3417**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `under_minimum_exact_live_structure_bucket`
- execution_guardrail_reason: `under_minimum_exact_live_structure_bucket`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `under_minimum_exact_live_structure_bucket` | reason: `當前即時結構分桶 `CAUTION|base_caution_regime_or_bias|q15` 的精準支持樣本仍停在 4/50（缺 46），支持路徑=精準樣本未達最小門檻，不可把舊範圍的支持閉環誤讀成部署閉環；決策品質仍為 D / 品質分數 -0.0192；目前維持不可部署治理。`
- support blocker summary: **精準樣本 4/50（缺口 46） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版 #1244 173/50僅能當歷史參考，因校準視窗不吻合目前支持語義，不可宣稱同一語義已閉環。**
- support next action: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。
- q15 精準樣本修補: **未啟用** | 支持路徑 `exact_bucket_present_but_below_minimum` | 跨越門檻 `math_cross_possible_but_illegal_without_exact_support`
- runtime closure summary: **當前即時分桶 CAUTION|base_caution_regime_or_bias|q15 的精準樣本仍未就緒（4/50，路徑=精準樣本未達最小門檻 / 治理=目前即時分桶精準樣本未達最小門檻）；較寬範圍 / 近似樣本 目前都只屬僅供治理參考，不可視為部署閉環。 阻塞點=當前即時結構分桶 `CAUTION|base_caution_regime_or_bias|q15` 的精準支持樣本仍停在 4/50（缺 46），支持路徑=精準樣本未達最小門檻，不可把舊範圍的支持閉環誤讀成部署閉環；決策品質仍為 D / 品質分數 -0.0192；目前維持不可部署治理。 精準路徑與外溢對照：同 gate 寬範圍出現 盤整|警戒 外溢，44 筆 / 勝率 76.2% / 品質 0.330，明顯劣於 精準即時路徑 勝率 50.0% / 品質 0.172。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 runtime truth: redesign_entry_quality=`None` / redesign_layers_after=`None` / runtime_layers=`None` / blocker=`None` / exact_support=`None/None` / support_gap=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- 建議修補方案: **None** — 狀態：None；精準樣本缺口 `None`；適用範圍 `None`；來源 `None`
- 建議修補特徵: None
- 建議修補說明: 精準樣本 4/50（缺口 46） 未達目前即時精準樣本門檻；較寬範圍或近似樣本只可作治理參考。 語義重訂後仍未達門檻；舊版 #1244 173/50僅能當歷史參考，因校準視窗不吻合目前支持語義，不可宣稱同一語義已閉環。
- 下一步: 保持禁止部署；先累積或回放同一目前即時結構分桶的精準路徑樣本，不可用較寬範圍或近似樣本放行。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。

## Entry-quality component breakdown

- final entry_quality: **0.5262** / trade_floor **0.55** / gap **-0.0238**
- base_quality: **0.6188** × weight **0.75**
- structure_quality: **0.2485** × weight **0.25**
- base components: feat_4h_bias50=0.4936 (w=0.4, contrib=0.1974), feat_nose=0.7463 (w=0.18, contrib=0.1343), feat_pulse=0.5298 (w=0.27, contrib=0.143), feat_ear=0.9601 (w=0.15, contrib=0.144)
- structure components: feat_4h_bb_pct_b=0.4012 (w=0.34, contrib=0.1364), feat_4h_dist_bb_lower=0.1181 (w=0.33, contrib=0.039), feat_4h_dist_swing_low=0.2216 (w=0.33, contrib=0.0731)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0238**
- base_group_max_entry_gain: **0.2858** | structure_group_max_entry_gain: **0.1879**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.0793, max_gain≈0.1519）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.0793), feat_pulse (Δscore≈0.1175), feat_nose (Δscore≈0.1763), feat_4h_bb_pct_b (Δscore≈0.28)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 44 | 0.5 | 0.1716 | 0.256 | 0.6063 | 4 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 44 | 0.5 | 0.1716 | 0.256 | 0.6063 | 4 | False |
| narrow `regime_label+entry_quality_label` | 44 | 0.5 | 0.1716 | 0.256 | 0.6063 | 4 | False |
| broad `regime_gate+entry_quality_label` | 52 | 0.5769 | 0.2482 | 0.2367 | 0.5779 | 4 | False |

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
