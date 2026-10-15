# tests/test_metric_components.py
from webapp.metric_components import METRICS, get_components


def test_every_registered_metric_resolves_and_has_components_with_sources():
    for metric in METRICS:
        data = get_components(metric)
        assert data["metric"] == metric and data["components"]
        for component in data["components"]:
            assert component["name"] and component["source"]


def test_unknown_metric_is_none():
    assert get_components("not_a_metric") is None


def test_nowcast_lists_the_ten_cleveland_inputs_including_oil_and_gasoline():
    names = [c["name"] for c in get_components("cleveland_nowcast")["components"]]
    assert len(names) == 10
    assert "Brent crude (daily)" in names and "Retail gasoline (weekly)" in names


def test_combined_states_the_fixed_weights_and_review_date():
    data = get_components("combined")
    text = " ".join([data["summary"], data.get("note") or ""] + [c["detail"] for c in data["components"]])
    assert "70%" in text and "30%" in text and "2027-01-15" in text


def test_component_sources_are_plain_language_not_file_paths():
    for metric in METRICS:
        for component in get_components(metric)["components"]:
            source = component["source"]
            assert ".py" not in source and "spec" not in source.lower()


def test_get_components_returns_a_copy_so_callers_cannot_change_the_registry():
    first = get_components("combined")
    first["components"][0]["name"] = "mutated"
    first["title"] = "mutated"
    assert get_components("combined")["components"][0]["name"] != "mutated"
    assert get_components("combined")["title"] != "mutated"
