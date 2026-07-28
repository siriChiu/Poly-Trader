from pathlib import Path


WEB_SRC = Path(__file__).resolve().parents[1] / "web" / "src"


def _read(relative: str) -> str:
    return (WEB_SRC / relative).read_text(encoding="utf-8")


def test_primary_navigation_is_reduced_to_three_user_goals():
    source = _read("App.tsx")
    assert "{ to: '/', label: '總覽'" in source
    assert "{ to: '/lab', label: '策略'" in source
    assert "{ to: '/execution', label: '營運'" in source
    assert '<summary className="app-nav-link cursor-pointer list-none">進階</summary>' in source
    assert '<Route path="/" element={<CommandCenter />} />' in source
    assert '<Route path="/diagnostics" element={<Dashboard />} />' in source


def test_command_center_has_one_action_and_three_stage_journey():
    source = _read("pages/CommandCenter.tsx")
    required = [
        "今日只看一件事",
        "建議下一步",
        "從研究到實戰，只保留三步",
        "回測候選",
        "Paper / Shadow",
        "Bounded Canary",
        '/api/execution/runs/selective/start',
        '/api/execution/workers/poll',
        "每一步都有產出，不再只顯示「等待放行」。",
    ]
    for snippet in required:
        assert snippet in source


def test_execution_console_exposes_partial_promotion_evidence_without_fake_progress():
    source = _read("pages/ExecutionConsole.tsx")
    required = [
        "模型升級證據（非發布進度）",
        "Promotion 自動化尚未形成可執行閉環",
        "promotion_status",
        "progress_is_release_metric",
        "Exact fitted model 已留下單次 Paper/Shadow 證據",
        "這些階段只描述證據是否存在，不代表發布完成百分比，也不能授權 Live",
        "策略 Bundle",
        "Exact Model",
        "Paper / Shadow",
        "24h Outcome",
        "Live Candidate",
        "Live 解鎖條件",
    ]
    for snippet in required:
        assert snippet in source


def test_strategy_lab_can_activate_the_exact_saved_strategy_in_paper_shadow():
    source = _read("pages/StrategyLab.tsx")
    required = [
        "const handleStartPaperShadow = async () =>",
        "/paper-shadow",
        "把回測策略投入演練",
        "啟動目前策略的 Paper/Shadow",
        "bundle parity 未通過",
        "exact fitted model",
        "全程不送實單",
        "進階：調整策略模組",
        "查看完整模型、決策品質與 Canary 指標",
        "查看 Raw / Features / Labels 明細",
    ]
    for snippet in required:
        assert snippet in source
