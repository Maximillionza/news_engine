"""
Suite-wide network guard (B2, 2026-10-21).

The shock-alert classifier tries Ollama first, and Ollama is live on the
owner's box (and may even be auto-started from OLLAMA_EXECUTABLE), so any
test that only patches the Claude call would otherwise reach the real
local model. A .env Telegram token could likewise send a real message.
This autouse fixture makes the unmocked defaults inert:

- Telegram bot token / chat id blanked -> send_alert() skips the push.
- Ollama pointed at port 9 (discard; nothing listens) and at an
  executable path that doesn't exist -> no auto-start.
- ANTHROPIC_API_KEY unset -> no real Claude call can authenticate.
- ACT: the release-time actuals poller thread is switched off and the official
  publisher keys (BLS/BEA/Census/EIA/FRED) read as empty, so no test starts the
  thread or can authenticate against a publisher.

Tests that patch these themselves still win inside their own
`with patch(...)`. requests.post is deliberately not patched globally,
because other suites rely on mocking it their own way.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from data_layer.official_actuals.keys import Keys


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("alerting.notify_telegram.TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr("alerting.notify_telegram.TELEGRAM_CHAT_ID", "")
    monkeypatch.setattr("alerting.llm_classify.OLLAMA_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setattr("alerting.llm_classify.OLLAMA_EXECUTABLE", str(tmp_path / "no-ollama.exe"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # B8: the scheduler's hourly FRED backfill must not reach FRED when a .env key is present.
    monkeypatch.setattr("webapp.actuals_backfill.FRED_API_KEY", "")
    monkeypatch.setattr("webapp.actuals_backfill._last_run_utc", None)
    # B4: no test may write the real ops/ops_state.db.
    monkeypatch.setattr("ops.state.DB_PATH", tmp_path / "ops_state.db")
    # B4: no test may touch the real ops/*.lock or ops/*.pid either.
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()
    monkeypatch.setattr("ops.single_instance.LOCK_DIR", lock_dir)
    # ACT: no test starts the actuals poller thread, and none can read the owner's publisher keys.
    monkeypatch.setattr("webapp.release_poller.POLLER_ENABLED", False)
    monkeypatch.setattr("data_layer.official_actuals.keys.load_keys",
                        lambda env_file=None: Keys(bls="", bea="", census="", eia="", fred=""))
