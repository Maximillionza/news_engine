"""Guard: every shipped static JS file must be strict UTF-8.

A stray Latin-1 byte (e.g. a raw 0xB7 middle dot) is served as
charset=utf-8 and renders as U+FFFD in the browser; node --test never
imports DOM-only modules, so nothing else catches it.
"""
from pathlib import Path

JS_ROOT = Path(__file__).resolve().parent.parent / "webapp" / "static" / "js"


def test_all_static_js_is_strict_utf8() -> None:
    files = sorted(JS_ROOT.rglob("*.js"))
    assert files, "no static JS found"
    bad = []
    for f in files:
        try:
            f.read_bytes().decode("utf-8")
        except UnicodeDecodeError as exc:
            bad.append(f"{f.relative_to(JS_ROOT)}: {exc}")
    assert not bad, bad
