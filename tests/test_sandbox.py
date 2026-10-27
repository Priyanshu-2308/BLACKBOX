import pytest
import time
from app.sandbox import execute_in_sandbox, check_rate_limit


def test_sandbox_executes_safe_code():
    code = """
def f(x):
    return x * 2
"""
    res = execute_in_sandbox(code, [1, 2, 3])
    assert res["status"] == "success"
    assert res["results"][0]["output"] == 2
    assert res["results"][1]["output"] == 4
    assert res["results"][2]["output"] == 6


def test_sandbox_terminates_infinite_loop_timeout():
    code = """
def f(x):
    while True:
        pass
"""
    start = time.time()
    res = execute_in_sandbox(code, [1], timeout_sec=2.0)
    elapsed = time.time() - start
    assert res["status"] == "timeout"
    assert elapsed < 3.5  # bounded near 2.0s


def test_sandbox_blocks_file_access():
    code = """
def f(x):
    with open('arena.db', 'r') as f:
        return f.read()
"""
    res = execute_in_sandbox(code, [1])
    assert res["status"] == "success"
    assert res["results"][0]["status"] == "runtime_error"
    assert "PermissionError" in res["results"][0]["error"] or "File access disabled" in res["results"][0]["error"]


def test_sandbox_blocks_network_access():
    code = """
def f(x):
    import socket
    s = socket.socket()
    return x
"""
    res = execute_in_sandbox(code, [1])
    assert res["status"] == "success"
    assert res["results"][0]["status"] == "runtime_error"
    assert "PermissionError" in res["results"][0]["error"] or "access disabled" in res["results"][0]["error"]


def test_rate_limiter():
    uid = "test_user_rate_limit"
    # First call should succeed
    allowed, wait = check_rate_limit(uid)
    assert allowed is True
    assert wait == 0.0

    # Immediate second call should be blocked
    allowed2, wait2 = check_rate_limit(uid)
    assert allowed2 is False
    assert wait2 > 0.0
