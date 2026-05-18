#!/usr/bin/env python3
"""Compact `/api/status` JSON from stdin for heartbeat runtime verification."""
from __future__ import annotations

import sys

from hb_compact_runtime_probe import main


if __name__ == "__main__":
    raise SystemExit(main(["status", *sys.argv[1:]]))
