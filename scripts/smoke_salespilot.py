#!/usr/bin/env python
"""Wrapper racine → backend.scripts.smoke_salespilot."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
sys.argv[0] = str(BACKEND / "scripts" / "smoke_salespilot.py")
runpy.run_path(str(BACKEND / "scripts" / "smoke_salespilot.py"), run_name="__main__")
