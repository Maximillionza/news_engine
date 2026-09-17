from data_layer.event_title_mapping import EVENT_TITLE_TO_METHODOLOGY, resolve_methodology_label
from data_layer.event_symbol_relevance import EVENT_TYPES


def test_every_mapped_methodology_label_is_a_real_event_type():
    for methodology_label in EVENT_TITLE_TO_METHODOLOGY.values():
        assert methodology_label in EVENT_TYPES


def test_mapping_has_exactly_14_entries():
    assert len(EVENT_TITLE_TO_METHODOLOGY) == 14


def test_resolve_methodology_label_for_all_14_real_titles():
    expected = {
        "FOMC Meeting Minutes": "FOMC Rate Decision",
        "FOMC Statement": "FOMC Rate Decision",
        "Federal Funds Rate": "FOMC Rate Decision",
        "Prelim GDP q/q": "GDP q/q",
        "Advance GDP q/q": "GDP q/q",
        "GDP q/q": "GDP q/q",
        "Retail Sales m/m": "Retail Sales m/m",
        "Core Retail Sales m/m": "Retail Sales m/m",
        "CPI m/m": "CPI m/m",
        "PPI m/m": "PPI m/m",
        "Non-Farm Employment Change": "Non-Farm Employment Change",
        "Core PCE Price Index m/m": "Core PCE Price Index m/m",
        "ISM Manufacturing PMI": "ISM Manufacturing PMI",
        "ISM Services PMI": "ISM Services PMI",
    }
    for calendar_title, methodology_label in expected.items():
        assert resolve_methodology_label(calendar_title) == methodology_label


def test_resolve_methodology_label_returns_none_for_unmapped_title():
    assert resolve_methodology_label("Unemployment Claims") is None
    assert resolve_methodology_label("") is None
