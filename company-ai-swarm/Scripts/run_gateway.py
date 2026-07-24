"""Runs the API gateway (and the dashboard it serves at /ui).

Mirrors pyproject.toml's pytest pythonpath (services, sdk) plus the gateway app dir, plus the
repo root itself - `python -m pytest` adds the root automatically (needed for
evolution_service/pipeline.py's `from sdk.agent_builder...` dotted import), this script has to
do it explicitly - then starts uvicorn in-process.

Usage:
    .venv/Scripts/python.exe Scripts/run_gateway.py
Then open http://127.0.0.1:8000/ui/
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT / "sdk"))
sys.path.insert(0, str(ROOT / "apps" / "api_gateway"))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
