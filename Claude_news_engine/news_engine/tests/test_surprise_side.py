"""FIX task 2: data_layer/surprise_side.py is the single, import-free in-line definition."""
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))

from data_layer import surprise_side
from webapp import stats_rules


def test_module_imports_without_webapp() -> None:
    code = "import sys; import data_layer.surprise_side; sys.exit(1 if any(m == 'webapp' or m.startswith('webapp.') for m in sys.modules) else 0)"
    result = subprocess.run([sys.executable, "-c", code], cwd=APP, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_stats_rules_reexports_the_same_objects() -> None:
    for name in ("parse_number", "decimals_of", "tolerance", "side"):
        assert getattr(stats_rules, name) is getattr(surprise_side, name), name


def test_one_rounding_step_is_the_tolerance() -> None:
    assert surprise_side.tolerance("0.3%") == 0.1
    assert surprise_side.tolerance("89K") == 1.0
    assert surprise_side.tolerance("n/a") is None
    # 4.1 vs 4.2 is one full tick away: a miss, not in line.
    assert surprise_side.side(4.1, 4.2, 0.1) == -1
    assert surprise_side.side(4.2, 4.2, 0.1) == 0
