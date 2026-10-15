# tests/test_stats_rules.py
import pytest

from webapp.stats_rules import decimals_of, judge, miss_size, parse_number, side, tolerance


@pytest.mark.parametrize("text,expected", [
    ("0.6%", 0.6), ("-0.6%", -0.6), ("89K", 89.0), ("-23K", -23.0), ("3.9", 3.9), (" 1.2% ", 1.2),
])
def test_parse_number_reads_published_formats(text, expected):
    assert parse_number(text) == expected


@pytest.mark.parametrize("text", [None, "", "N/A", "1.2|0.9", "abc", "--"])
def test_parse_number_returns_none_for_unreadable_text(text):
    assert parse_number(text) is None


def test_tolerance_is_one_rounding_step_of_the_forecast():
    assert tolerance("0.3%") == pytest.approx(0.1)
    assert tolerance("3.85") == pytest.approx(0.01)
    assert tolerance("89K") == pytest.approx(1.0)
    assert tolerance("N/A") is None
    assert decimals_of("0.3%") == 1 and decimals_of("89K") == 0


def test_side_uses_the_tolerance_band_with_float_noise_protection():
    assert side(3.9, 3.8, 0.1) == 1          # exactly one step above: hotter
    assert side(3.8, 3.8, 0.1) == 0
    assert side(3.75, 3.8, 0.1) == 0         # less than a step: in line
    assert side(3.7, 3.8, 0.1) == -1
    assert side(0.4, 0.3, 0.1) == 1          # 0.4-0.3 is 0.10000000000000003 in floats
    assert side(0.2, 0.3, 0.1) == -1


def test_the_owners_worked_example_is_right_and_the_in_line_miss_is_wrong():
    f, tol = 3.8, 0.1
    assert judge(side(4.0, f, tol), side(3.9, f, tol)) == "right"   # hotter / hotter
    assert judge(side(4.0, f, tol), side(3.8, f, tol)) == "wrong"   # hotter vs in line
    assert judge(side(3.8, f, tol), side(3.8, f, tol)) == "right"   # in line / in line


def test_judge_is_none_when_either_side_is_missing():
    assert judge(None, 1) is None and judge(1, None) is None


def test_miss_size():
    assert miss_size(4.0, 3.9) == pytest.approx(0.1)
    assert miss_size(None, 3.9) is None
