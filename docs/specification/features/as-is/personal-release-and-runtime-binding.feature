@as_is @release @binding
Feature: Owner personal release 與 runtime bundle binding
  為了讓owner接受研究風險但不繞過交易安全
  作為release系統
  我需要把策略核准紀錄與runtime identity驗證分開

  # Sources: model/personal_release.py, model/runtime_closure.py,
  # execution/strategy_bundle.py, tests/test_personal_release_policy.py,
  # tests/test_strategy_bundle_exact_model.py

  Background:
    Given personal release policy可由config啟用
    And owner selector包含model、feature profile、regime與top-k

  Scenario: selector相符且沒有hard risk時owner可核准個人使用
    Given candidate leaderboard row符合owner selector
    And owner enabled personal release
    And circuit breaker未active
    When evaluate_personal_release執行
    Then strategy_release_status是 `RELEASED_FOR_PERSONAL_USE`
    And strategy_release_ready是true
    And deployment_candidate_tier是 `owner_approved_personal_use`

  Scenario: 統計support不足不自動撤銷owner release
    Given owner release已成立
    And exact support小於statistical minimum
    When personal release被評估
    Then strategy_release_status保持 `RELEASED_FOR_PERSONAL_USE`
    And evidence tier與warning反映support不足
    And release record不被artifact overlay改成rejected

  Scenario: circuit breaker保留release record但禁止新增曝險
    Given owner release已成立
    And circuit breaker active
    When runtime personal release policy套用
    Then strategy_release_status仍可保持owner released
    But allowed_layers變成0
    And deployment blocker反映hard technical/risk failure

  Scenario: hard risk failure不能被owner acceptance覆寫
    Given kill switch、circuit breaker或等價hard risk failure存在
    When personal release被評估
    Then owner acceptance不會授權risk-on order
    And technical blocker保持blocking

  Scenario: owner release不是execution permit
    Given strategy_release_ready是true
    When non-dry order抵達ExecutionService
    Then order仍需live config triple、canary policy與execution permit

  @known_gap
  Scenario: runtime overlay未重新驗證完整selector
    Given owner selector是 logistic/current_full/specific regime/top-k
    And runtime payload來自另一個regime或top-k identity
    When apply_runtime_release_policy直接套用
    Then 現行函式主要依賴owner enabled與runtime context
    And 未在該入口重新執行完整selector match
    And release欄位可能出現在不匹配runtime payload上

  @known_gap
  Scenario: personal release binding只檢查boolean與部分identity
    Given runtime_binding包含 `verified=true`
    And model與feature_profile符合
    But artifact SHA或schema未證明相同
    When `_binding_matches` 執行
    Then 現行函式仍可回傳match
    And 它不檢查regime、top-k、target、training manifest或artifact checksum

  Scenario: strategy bundle exact binding驗證更多artifact欄位
    Given immutable saved strategy與exact fitted model可用
    When build_strategy_bundle執行
    Then bundle包含strategy definition identity
    And 包含model artifact path/hash/feature schema等metadata
    And exact model缺失時不得使用placeholder冒充

  @known_inconsistency
  Scenario: release binding與strategy bundle proof是兩套機制
    Given personal release payload顯示binding verified
    But immutable strategy bundle缺少或hash不符
    When execution readiness被不同projection計算
    Then 一個projection可能顯示released
    And 另一個projection顯示not live deployable
    And 目前沒有single BundleRegistry仲裁

  Scenario: exact fitted model缺失時paper-shadow啟動失敗
    Given saved strategy要求exact model artifact
    And 沒有可重現fitted artifact
    When exact-model paper-shadow endpoint啟動
    Then 請求fail closed
    And 不以dummy predictor或未綁定retrain替代

  @known_gap
  Scenario: runtime可在某些路徑自動retrain產生artifact
    Given runner找不到預期model artifact
    When ensure_model_artifact fallback被允許
    Then 它可能以當前DB重新訓練
    And 產生的新artifact不等於owner原核准的fitted model
    And 該artifact不得被promotion為exact binding
