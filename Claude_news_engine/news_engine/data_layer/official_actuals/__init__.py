"""
Official-publisher actuals (ACT, 2026-10-28).

One small adapter per publisher (BLS, BEA, Census, EIA, Fed, TreasuryDirect,
plus FRED for weekly claims), all calling HTTP through one injectable
`Fetcher` (http.py) so tests run on recorded fixtures and never reach the
network. Adapters are pure parses: they RAISE `SourceError` subclasses on any
failure (the poller must tell "publisher down" from "not yet published") and
never invent a value. No error message ever carries a URL, query or key.
"""
