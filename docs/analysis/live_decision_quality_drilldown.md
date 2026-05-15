# Live Decision-Quality Drilldown

- feature_timestamp: **2026-05-15 10:24:25.300832**
- target: `simulated_pyramid_win`
- live path: **chop / CAUTION / D**
- signal: **HOLD** @ confidence **0.3386**
- layers: **0 → 0**
- allowed_layers_raw_reason: `entry_quality_below_trade_floor`
- allowed_layers_reason: `decision_quality_below_trade_floor`
- execution_guardrail_reason: `decision_quality_below_trade_floor`
- runtime_blocker: `None` | reason: `None`
- deployment_blocker: `decision_quality_below_trade_floor` | reason: `當前即時結構分桶 `CAUTION|base_caution_regime_or_bias|q15` 已完成精準樣本閉環（173/50），但頂層即時基準仍停在進場品質=0.5138，低於交易門檻 0.55；目前只能維持明確不可部署治理，不可把支持樣本閉環或元件實驗就緒誤讀成部署閉環。`
- support blocker summary: **精準樣本 173/50（缺口 0） 已達可部署樣本門檻；是否放行仍以即時部署阻塞與執行層數為準。 語義重訂後仍未達門檻；舊版 #1188 95/50僅能當歷史參考，因校準視窗不吻合目前支持語義，不可宣稱同一語義已閉環。**
- support next action: 不要把樣本達標誤讀成部署已放行；繼續檢查執行層數、訊號與場館證據。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。
- q15 精準樣本修補: **未啟用** | 支持路徑 `exact_bucket_supported` | 跨越門檻 `legal_component_experiment_after_support_ready`
- runtime closure summary: **當前即時分桶 CAUTION|base_caution_regime_or_bias|q15 已完成精準樣本閉環（173/50），但頂層即時基準仍停在進場品質=0.5138 (D) < 交易門檻 0.55；目前維持明確不可部署治理。 不可把支持樣本閉環誤讀成部署閉環。 精準路徑與外溢對照：同品質寬範圍出現 牛市|阻塞 外溢，380 筆 / 勝率 20.2% / 品質 -0.058，明顯劣於 精準即時路徑 勝率 59.1% / 品質 0.224。**
- q35 scaling audit: overall=`None` / redesign=`None` / runtime_gap=`None` / mode=`None` / next_patch=`None`
- q35 runtime truth: redesign_entry_quality=`None` / redesign_layers_after=`None` / runtime_layers=`None` / blocker=`None` / exact_support=`None/None` / support_gap=`None`
- q35 audit action: None
- q15 patch machine-read: support_ready=None / entry_quality_ge_0_55=None / allowed_layers_gt_0=None / preserves_positive_discrimination_status=`None`
- 建議修補方案: **None** — 狀態：None；精準樣本缺口 `None`；適用範圍 `None`；來源 `None`
- 建議修補特徵: None
- 建議修補說明: 精準樣本 173/50（缺口 0） 已達可部署樣本門檻；是否放行仍以即時部署阻塞與執行層數為準。 語義重訂後仍未達門檻；舊版 #1188 95/50僅能當歷史參考，因校準視窗不吻合目前支持語義，不可宣稱同一語義已閉環。
- 下一步: 不要把樣本達標誤讀成部署已放行；繼續檢查執行層數、訊號與場館證據。 先以目前支持語義累積或回放精準樣本；舊版參考不可作為放行依據。

## Entry-quality component breakdown

- final entry_quality: **0.5138** / trade_floor **0.55** / gap **-0.0362**
- base_quality: **0.6025** × weight **0.75**
- structure_quality: **0.2479** × weight **0.25**
- base components: feat_4h_bias50=0.4943 (w=0.4, contrib=0.1977), feat_nose=0.584 (w=0.18, contrib=0.1051), feat_pulse=0.5891 (w=0.27, contrib=0.1591), feat_ear=0.9371 (w=0.15, contrib=0.1406)
- structure components: feat_4h_bb_pct_b=0.4 (w=0.34, contrib=0.136), feat_4h_dist_bb_lower=0.1177 (w=0.33, contrib=0.0389), feat_4h_dist_swing_low=0.2212 (w=0.33, contrib=0.073)

## Gap attribution（哪個 component 真正在卡 floor）

- remaining_gap_to_floor: **0.0362**
- base_group_max_entry_gain: **0.2982** | structure_group_max_entry_gain: **0.1881**
- best_single_component: **feat_4h_bias50**（group=base, Δscore≈0.1207, max_gain≈0.1517）
- single-component floor crossers: feat_4h_bias50 (Δscore≈0.1207), feat_pulse (Δscore≈0.1788), feat_nose (Δscore≈0.2681), feat_4h_bb_pct_b (Δscore≈0.4259)
- bias50 fully relaxed: entry≈**None** / layers≈**0** / required_bias50_cap≈**None**
- unavailable_reason: `None`

## Scope comparison

| scope | rows | win_rate | quality | dd | tuw | live bucket rows | pathology |
|---|---:|---:|---:|---:|---:|---:|---|
| chosen `regime_label+regime_gate+entry_quality_label` | 450 | 0.5911 | 0.224 | 0.1491 | 0.4724 | 173 | False |
| exact `regime_label+regime_gate+entry_quality_label` | 450 | 0.5911 | 0.224 | 0.1491 | 0.4724 | 173 | False |
| narrow `regime_label+entry_quality_label` | 450 | 0.5911 | 0.224 | 0.1491 | 0.4724 | 173 | False |
| broad `regime_gate+entry_quality_label` | 512 | 0.584 | 0.2222 | 0.1521 | 0.4753 | 173 | False |

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
