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
        "進階診斷（需要時再展開）",
        "Venue lanes",
        "Timeline",
        "<details",
    ]
    for snippet in required_snippets:
        assert snippet in source
