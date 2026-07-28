import importlib.util
from datetime import datetime, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync_pm_status.py"
SPEC = importlib.util.spec_from_file_location("sync_pm_status_test_module", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
sync_pm_status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_pm_status)


def test_pm_status_surfaces_local_lifecycle_rehearsal_without_runtime_promotion():
    rendered = sync_pm_status.build_pm_status_markdown(
        now=datetime(2026, 7, 19, 8, 0, tzinfo=timezone.utc)
    )

    assert "local_rehearsal=passed_local_state_machine_runtime_unverified" in rendered
    assert "local_scope=local_contract_rehearsal_not_exchange_proof" in rendered
    assert "local_runtime_backed=false" in rendered
    assert "local_live_adapter_called=false" in rendered
    assert "venue_dry_run_status=blocked_missing_runtime_backed_proof" in rendered
    assert "order_submission_enabled=false" in rendered
