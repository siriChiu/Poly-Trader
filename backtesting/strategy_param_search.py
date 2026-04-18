"""Strategy Lab parameter-search helpers for nested parameter grids."""

from __future__ import annotations

import copy
import itertools
from typing import Any, Dict, Iterable, List


def _set_nested(mapping: Dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = [part for part in str(dotted_path).split('.') if part]
    if not parts:
        return
    cursor = mapping
    for key in parts[:-1]:
        current = cursor.get(key)
        if not isinstance(current, dict):
            current = {}
            cursor[key] = current
        cursor = current
    cursor[parts[-1]] = value


def expand_search_space(base_params: Dict[str, Any], search_space: Dict[str, Iterable[Any]]) -> List[Dict[str, Any]]:
    """Expand a nested discrete search space.

    Returns rows like:
      {"variant": "entry.confidence_min=0.55 | entry.bias50_max=0.0", "params": {...}}
    """
    items = [(path, list(values)) for path, values in (search_space or {}).items()]
    if not items:
        return [{"variant": "base", "params": copy.deepcopy(base_params)}]

    variants: List[Dict[str, Any]] = []
    for combo in itertools.product(*[values for _, values in items]):
        params = copy.deepcopy(base_params)
        labels = []
        for (path, _), value in zip(items, combo):
            _set_nested(params, path, value)
            labels.append(f"{path}={value}")
        variants.append({"variant": " | ".join(labels), "params": params})
    return variants



def rank_param_search_results(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        list(rows or []),
        key=lambda r: (
            float(r.get("roi") if r.get("roi") is not None else -999.0),
            -(float(r.get("max_drawdown") if r.get("max_drawdown") is not None else 999.0)),
            float(r.get("profit_factor") if r.get("profit_factor") is not None else -999.0),
            float(r.get("avg_exit_local_top_score") if r.get("avg_exit_local_top_score") is not None else -999.0),
        ),
        reverse=True,
    )
