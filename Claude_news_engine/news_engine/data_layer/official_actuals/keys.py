"""
API keys for the official-actuals adapters (ACT Task 1).

Read here rather than in config/settings.py so another batch's edits there
cannot conflict. With `env_file` the values come from `dotenv_values(path)`
and are NOT exported into os.environ (scripts run from a worktree without a
.env point at the live one); otherwise `config.settings` is imported first,
which runs `load_dotenv()`, and os.environ is read. A missing key is "".
Never print or log a value from here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from dotenv import dotenv_values

KEY_NAMES = {
    "bls": "BLS_API_KEY",
    "bea": "BEA_API_KEY",
    "census": "CENSUS_API_KEY",
    "eia": "EIA_API_KEY",
    "fred": "FRED_API_KEY",
}


@dataclass(frozen=True)
class Keys:
    bls: str
    bea: str
    census: str
    eia: str
    fred: str

    def __repr__(self) -> str:  # never show a key value, even in a traceback
        present = ", ".join(f"{name}={'set' if getattr(self, name) else 'missing'}" for name in KEY_NAMES)
        return f"Keys({present})"

    def values(self) -> list[str]:
        """Every non-empty key value (used to scrub recorded bodies)."""
        return [v for v in (getattr(self, name) for name in KEY_NAMES) if v]


def load_keys(env_file: Optional[Path] = None) -> Keys:
    """Keys from `env_file` (not exported) or from the process environment after config.settings."""
    source: Mapping[str, Optional[str]]
    if env_file is not None:
        path = Path(env_file)
        if not path.is_file():
            raise FileNotFoundError("env file not found")
        source = dotenv_values(path)
    else:
        import config.settings  # noqa: F401 — runs load_dotenv() for the app's own .env
        source = os.environ
    return Keys(**{name: (source.get(var) or "").strip() for name, var in KEY_NAMES.items()})
