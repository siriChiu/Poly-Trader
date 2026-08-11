from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class GateCategory(str, Enum):
    EVIDENCE = "evidence"
    RELEASE = "release"
    DEPLOYMENT = "deployment"
    MARKET = "market"
    EXECUTION = "execution"
    CAPABILITY = "capability"


class GateStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"
    UNKNOWN = "unknown"
    INCONSISTENT = "inconsistent"


@dataclass(frozen=True, slots=True)
class GateProvenance:
    source: str
    generation_id: str
    subject_id: str
    as_of: datetime
    content_digest: str | None = None

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")


@dataclass(frozen=True, slots=True)
class GateResult:
    category: GateCategory
    status: GateStatus
    code: str
    owner: str
    enforced_at: str | None
    provenance: GateProvenance
    release_condition: str | None = None
    message: str | None = None

    @property
    def blocks_side_effect(self) -> bool:
        return self.status in {
            GateStatus.BLOCK,
            GateStatus.UNKNOWN,
            GateStatus.INCONSISTENT,
        }
