#!/usr/bin/env python3
"""Compact `/api/execution/overview` JSON from stdin for heartbeat verification."""
from __future__ import annotations

import sys

from hb_compact_runtime_probe import main


if __name__ == "__main__":
    raise SystemExit(main(["execution", *sys.argv[1:]]))
