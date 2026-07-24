"""Phase 13 (IMPLEMENTATION_PLAN.md, 2026-07-23) deliverable 4, raised by the user during
Phase 12: is the single shared `ModelProvider` instance a real bottleneck under concurrent
load?

`POST /chat/sync` and `POST /objectives` skip the (strictly sequential, one-worker-by-design)
async queue entirely and call the orchestrator directly inside the HTTP handler - that is the
one place today where two requests could genuinely reach the shared provider at the same
time. A deliberately slow fake provider (no real network/API delay, so this stays fast and
free to run) makes any serialization directly observable via wall-clock time: N requests each
taking `_DELAY_SECONDS` complete in roughly `_DELAY_SECONDS` total if they truly overlap, or
roughly `N * _DELAY_SECONDS` if something serializes them.

Follows Tests/integration/test_api_gateway_dashboard.py's pattern (sys.path insert, real
TestClient, real COOOrchestrator underneath) and its precedent of temporarily swapping a
collaborator on the live `gateway_main._coo` singleton (that file swaps `_head`; this swaps
the model gateway's provider via the already-public `ModelGateway.replace_provider()`).
"""

from __future__ import annotations

import concurrent.futures
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api_gateway"))

from fastapi.testclient import TestClient

import main as gateway_main

HEADERS = {"X-API-Key": "dev-only-api-key"}

_DELAY_SECONDS = 0.3
_N_CONCURRENT = 5


class _SlowProvider:
    """Deterministic, artificially slow - not connected to any real model. The delay is what
    makes concurrency (or its absence) observable in a fast, free, deterministic test."""

    def __init__(self, delay_seconds: float) -> None:
        self._delay = delay_seconds

    def generate(self, prompt: str, *, allowed_tools=None) -> str:
        time.sleep(self._delay)
        return "[slow stub output]"


def _client() -> TestClient:
    return TestClient(gateway_main.app)


def test_concurrent_chat_sync_requests_reveal_whether_the_shared_provider_serializes() -> None:
    gateway = gateway_main._coo._model_gateway
    original_provider = gateway._provider
    gateway.replace_provider(_SlowProvider(_DELAY_SECONDS))

    try:
        client = _client()

        def _send(i: int):
            return client.post(
                "/chat/sync", headers=HEADERS, json={"message": f"concurrent probe {i}"}
            )

        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=_N_CONCURRENT) as executor:
            futures = [executor.submit(_send, i) for i in range(_N_CONCURRENT)]
            responses = [f.result() for f in futures]
        elapsed = time.perf_counter() - start

        fully_serial_estimate = _N_CONCURRENT * _DELAY_SECONDS
        print(
            f"\n[Phase 13 bottleneck probe] {_N_CONCURRENT} concurrent /chat/sync requests, "
            f"{_DELAY_SECONDS}s each: elapsed={elapsed:.3f}s "
            f"(fully-serial estimate={fully_serial_estimate:.3f}s, "
            f"fully-parallel estimate={_DELAY_SECONDS:.3f}s)"
        )

        # Sanity, not a claim about which way the timing falls - every request must still
        # complete correctly regardless of whether they overlapped or serialized.
        assert all(r.status_code == 200 for r in responses)

        # Documented, not asserted as pass/fail either way: which regime this falls into is
        # exactly the open question, not a known invariant to enforce. See this module's
        # docstring and IMPLEMENTATION_PLAN.md Phase 13 for the recommendation drawn from
        # this measurement.
        if elapsed < fully_serial_estimate * 0.7:
            print("[Phase 13 bottleneck probe] Result: requests overlapped - not fully serialized.")
        else:
            print("[Phase 13 bottleneck probe] Result: requests ran effectively serialized.")
    finally:
        gateway.replace_provider(original_provider)
