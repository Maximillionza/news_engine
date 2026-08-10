"""
Tests for scripts/run_all.py's supervise() — no real subprocesses spawned;
process objects are mocked with controllable .poll()/.terminate()/.wait().
"""
import sys
import os
import subprocess as sp
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scripts.run_all as run_all


def _fake_process(poll_results):
    """A Mock standing in for subprocess.Popen — poll() returns each value
    in poll_results in sequence (None means still running)."""
    proc = Mock()
    proc.poll.side_effect = poll_results
    return proc


def test_supervise_stops_all_when_one_process_exits():
    print("=== run_all: supervise() stops every process when one exits on its own (crash) ===")
    # dashboard keeps running; accumulator exits with code 1 on its 2nd poll.
    # Both need a 3rd poll value for the finally block's own re-check.
    dashboard = _fake_process([None, None, None])
    accumulator = _fake_process([None, 1, 1])
    processes = [("dashboard", dashboard), ("accumulator", accumulator)]

    run_all.supervise(processes, poll_interval_seconds=0, sleep_fn=lambda _s: None)

    dashboard.terminate.assert_called_once()
    accumulator.terminate.assert_not_called()
    dashboard.wait.assert_called_once()
    accumulator.wait.assert_called_once()
    print("PASS\n")


def test_supervise_stops_all_on_keyboard_interrupt():
    print("=== run_all: supervise() stops every still-running process cleanly on Ctrl+C ===")
    dashboard = _fake_process([None] * 5)
    accumulator = _fake_process([None] * 5)
    processes = [("dashboard", dashboard), ("accumulator", accumulator)]

    def fake_sleep(_seconds):
        raise KeyboardInterrupt()

    run_all.supervise(processes, poll_interval_seconds=0, sleep_fn=fake_sleep)

    dashboard.terminate.assert_called_once()
    accumulator.terminate.assert_called_once()
    dashboard.wait.assert_called_once()
    accumulator.wait.assert_called_once()
    print("PASS\n")


def test_supervise_kills_a_process_that_wont_stop():
    print("=== run_all: supervise() force-kills a process that doesn't terminate within the timeout ===")
    dashboard = _fake_process([None] * 5)
    dashboard.wait.side_effect = sp.TimeoutExpired(cmd="dashboard", timeout=10)
    processes = [("dashboard", dashboard)]

    def fake_sleep(_seconds):
        raise KeyboardInterrupt()

    run_all.supervise(processes, poll_interval_seconds=0, sleep_fn=fake_sleep)

    dashboard.terminate.assert_called_once()
    dashboard.kill.assert_called_once()
    print("PASS\n")


def test_main_passes_correctly_shaped_name_process_pairs_to_supervise():
    print("=== run_all: main() passes (name, proc) tuples to supervise(), not bare proc objects ===")
    # Regression test: an earlier version's list comprehension dropped the
    # name and passed supervise() a bare list of Popen objects, which
    # crashed on the very first `for name, proc in processes` unpack — a
    # bug the mocked supervise() tests above couldn't catch, since they
    # hand-built the correct (name, proc) shape directly. This test
    # exercises main()'s own wiring instead.
    fake_dashboard = Mock()
    fake_accumulator = Mock()
    with patch.object(run_all, "start_service", side_effect=[fake_dashboard, fake_accumulator]), \
         patch.object(run_all, "supervise") as mock_supervise:
        run_all.main()

        mock_supervise.assert_called_once()
        (processes,), _kwargs = mock_supervise.call_args
        assert processes == [("dashboard", fake_dashboard), ("accumulator", fake_accumulator)], (
            f"expected (name, proc) tuples matching SERVICES, got {processes!r}"
        )
    print("PASS\n")


if __name__ == "__main__":
    test_supervise_stops_all_when_one_process_exits()
    test_supervise_stops_all_on_keyboard_interrupt()
    test_supervise_kills_a_process_that_wont_stop()
    test_main_passes_correctly_shaped_name_process_pairs_to_supervise()
    print("All run_all tests passed.")
