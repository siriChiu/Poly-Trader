from __future__ import annotations

from datetime import datetime, timezone

import pytest

from domain.gates import GateCategory, GateProvenance, GateResult, GateStatus


def test_unknown_execution_gate_blocks_side_effect() -> None:
    result = GateResult(
        category=GateCategory.EXECUTION,
        status=GateStatus.UNKNOWN,
        code="execution_state_unavailable",
        owner="execution_authorizer",
        enforced_at="ExecutionAuthorizer.authorize",
        provenance=GateProvenance(
            source="execution_state",
            generation_id="generation-1",
            subject_id="bundle-1",
            as_of=datetime(2026, 8, 11, tzinfo=timezone.utc),
        ),
        release_condition="publish a complete fresh execution state",
    )

    assert result.blocks_side_effect is True


def test_evidence_warning_does_not_block_side_effect() -> None:
    result = GateResult(
        category=GateCategory.EVIDENCE,
        status=GateStatus.WARN,
        code="exact_support_below_target",
        owner="evidence_service",
        enforced_at=None,
        provenance=GateProvenance(
            source="candidate_evidence",
            generation_id="generation-1",
            subject_id="bundle-1",
            as_of=datetime(2026, 8, 11, tzinfo=timezone.utc),
        ),
        release_condition="collect more exact-bundle evidence",
    )

    assert result.blocks_side_effect is False


def test_inconsistent_execution_gate_blocks_side_effect() -> None:
    result = GateResult(
        category=GateCategory.EXECUTION,
        status=GateStatus.INCONSISTENT,
        code="snapshot_bundle_mismatch",
        owner="execution_authorizer",
        enforced_at="ExecutionAuthorizer.authorize",
        provenance=GateProvenance(
            source="decision_snapshot",
            generation_id="generation-2",
            subject_id="bundle-2",
            as_of=datetime(2026, 8, 11, tzinfo=timezone.utc),
        ),
        release_condition="publish one internally consistent snapshot",
    )

    assert result.blocks_side_effect is True


def test_provenance_rejects_naive_as_of_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        GateProvenance(
            source="execution_state",
            generation_id="generation-1",
            subject_id="bundle-1",
            as_of=datetime(2026, 8, 11),
        )
