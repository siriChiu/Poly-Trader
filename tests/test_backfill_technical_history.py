import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from scripts.backfill_technical_history import build_volume_series


def test_build_volume_series_preserves_real_values_without_ffill():
    close = np.array([100.0, 101.0, 103.0, 102.0], dtype=float)
    raw_volume = pd.Series([10.0, None, 0.0, 40.0])

    result = build_volume_series(close, raw_volume)

    assert result.tolist() == [10.0, 1.0, 2.0, 40.0]
    assert result[1] != result[0], "missing volume should not be forward-filled"
    assert result[2] != result[3], "zero volume should use per-row proxy, not backward-fill"
