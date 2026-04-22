from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "web" / "src"


def _read(relative_path: str) -> str:
    return (WEB_SRC / relative_path).read_text(encoding="utf-8")


def test_execution_surfaces_use_shared_execution_shell_components():
    console_source = _read("pages/ExecutionConsole.tsx")
    status_source = _read("pages/ExecutionStatus.tsx")
    shared_source = _read("components/execution/ExecutionSurface.tsx")
    css_source = _read("index.css")

    assert "export function ExecutionHero" in shared_source
    assert "export function ExecutionSectionCard" in shared_source
    assert "export function ExecutionMetricCard" in shared_source

    for source in [console_source, status_source]:
        assert "ExecutionHero" in source
        assert "ExecutionSectionCard" in source
        assert "ExecutionMetricCard" in source

    for token in [
        ".execution-shell",
        ".execution-hero",
        ".execution-card",
        ".execution-pill",
        ".execution-command-input",
    ]:
        assert token in css_source


def test_execution_console_exposes_natural_language_operator_input_and_progressive_disclosure():
    source = _read("pages/ExecutionConsole.tsx")
    required_snippets = [
        "自然語句操作",
        "例如：買 0.001 BTC / 減碼 0.001 / 切到自動 / 查看阻塞原因",
        "handleNaturalLanguageAction",
        "自然語句會優先幫你判斷是交易、模式切換還是前往診斷",
        "進階營運細節（需要時再展開）",
        "<details",
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_execution_status_keeps_diagnostics_collapsed_by_default_and_reuses_shared_shell():
    source = _read("pages/ExecutionStatus.tsx")
    required_snippets = [
        "ExecutionHero",
        "ExecutionSectionCard",
        "ExecutionMetricCard",
        "進階診斷（Surface contract / timeline；需要時再展開）",
        "Venue lanes",
        "Timeline",
        "<details",
    ]
    for snippet in required_snippets:
        assert snippet in source


def test_dashboard_and_strategy_lab_share_execution_workspace_summary_component():
    shared_source = _read("components/execution/ExecutionWorkspaceSummary.tsx")
    dashboard_source = _read("pages/Dashboard.tsx")
    strategy_lab_source = _read("pages/StrategyLab.tsx")

    assert "export function ExecutionWorkspaceSummary" in shared_source
    assert "export function ExecutionWorkspaceMetric" in shared_source

    for source in [dashboard_source, strategy_lab_source]:
        assert "ExecutionWorkspaceSummary" in source
        assert "ExecutionWorkspaceMetric" in source

    for snippet in [
        "Execution 摘要",
        "Live 部署同步",
        "前往 Bot 營運 →",
        "前往執行狀態 →",
    ]:
        assert snippet in (dashboard_source + strategy_lab_source)


def test_execution_console_bot_cards_surface_strategy_binding_state_without_duplicate_sleeve_labels():
    source = _read("pages/ExecutionConsole.tsx")
    required_snippets = [
        'const primarySleeveLabel = String(',
        'const cardLabel = String(card.label || card.key || "unknown sleeve").trim();',
        'const shouldShowPrimarySleeveBadge = Boolean(primarySleeveLabel) && primarySleeveLabel !== cardLabel;',
        'const strategyBindingStatus = String(profileStrategyBinding?.status || card.strategy_binding?.status || "").trim();',
        'const strategyBindingBadgeLabel = strategyBindingStatus === "missing_saved_strategy"',
        '"待儲存策略快照"',
        '`策略：${strategyBindingTitle}`',
        '{shouldShowPrimarySleeveBadge && (',
        '{strategyBindingStatus && (',
    ]
    for snippet in required_snippets:
        assert snippet in source

    assert 'profileStrategyBinding?.primary_sleeve_label || card.strategy_binding?.title || "未分類"' not in source
