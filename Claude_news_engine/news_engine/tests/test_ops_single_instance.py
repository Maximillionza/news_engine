"""
Tests for ops/single_instance.py (B4 O8) - real OS file locks in tmp dirs,
a real child process for the crash case, no network.
"""
import socket
import subprocess
import sys
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from ops import single_instance


def test_acquire_release_reacquire(tmp_path):
    lock = single_instance.try_acquire("t", tmp_path)
    assert lock is not None
    lock.release()
    again = single_instance.try_acquire("t", tmp_path)
    assert again is not None
    again.release()


def test_second_acquire_in_same_process_is_refused(tmp_path):
    lock = single_instance.try_acquire("t", tmp_path)
    try:
        assert single_instance.try_acquire("t", tmp_path) is None
    finally:
        lock.release()


def test_lock_is_released_when_the_holder_dies(tmp_path):
    code = (
        "import sys, time; sys.path.insert(0, sys.argv[1]);"
        "from pathlib import Path; from ops import single_instance;"
        "l = single_instance.try_acquire('t', Path(sys.argv[2]));"
        "print('LOCKED' if l else 'FAILED', flush=True); time.sleep(60)"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", code, str(APP_DIR), str(tmp_path)],
        stdout=subprocess.PIPE, text=True,
    )
    try:
        assert child.stdout.readline().strip() == "LOCKED"
        assert single_instance.try_acquire("t", tmp_path) is None
        assert single_instance.running_pid("t", tmp_path) == child.pid
    finally:
        child.kill()
        child.wait()
    lock = single_instance.try_acquire("t", tmp_path)
    assert lock is not None  # no stale lock after a crash
    lock.release()


def test_claim_or_exit_exits_3_when_the_lock_is_held(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(single_instance, "try_acquire", lambda name, lock_dir=tmp_path: None)
    with pytest.raises(SystemExit) as exc:
        single_instance.claim_or_exit("webapp", lock_dir=tmp_path)
    assert exc.value.code == single_instance.ALREADY_RUNNING_EXIT_CODE == 3
    assert "already running" in capsys.readouterr().out


def test_claim_or_exit_exits_3_when_the_port_is_bound_and_frees_the_lock(tmp_path):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    try:
        port = srv.getsockname()[1]
        with pytest.raises(SystemExit) as exc:
            single_instance.claim_or_exit("w", port=port, lock_dir=tmp_path)
        assert exc.value.code == 3
    finally:
        srv.close()
    lock = single_instance.try_acquire("w", tmp_path)
    assert lock is not None
    lock.release()


def test_claim_or_exit_returns_the_lock_when_free(tmp_path):
    lock = single_instance.claim_or_exit("free", lock_dir=tmp_path)
    assert lock is not None
    lock.release()


def test_app_claims_single_instance_before_starting_the_scheduler():
    app_text = (APP_DIR / "webapp" / "app.py").read_text(encoding="utf-8")
    main_block = app_text.split('if __name__ == "__main__":', 1)[1]
    claim = main_block.index('claim_or_exit("webapp", port=5001)')
    assert claim < main_block.index("_ensure_defaults()")
    assert claim < main_block.index("start_scheduler(")
    acc_text = (APP_DIR / "scripts" / "run_accumulator.py").read_text(encoding="utf-8")
    assert acc_text.index('claim_or_exit("accumulator")') < acc_text.index("start_accumulator(tracked)")


def test_restart_loop_stops_on_exit_code_3():
    data = (APP_DIR / "scripts" / "_restart_loop.bat").read_bytes()
    assert b"\n" not in data.replace(b"\r\n", b"")  # CRLF throughout
    text = data.decode("utf-8")
    assert "python %1\r\nset EXITCODE=%ERRORLEVEL%\r\n" in text
    branch = text.index('if "%EXITCODE%"=="3"')
    assert "exit /b 3" in text[branch:text.index("goto loop")]
    assert branch < text.index("goto loop")
