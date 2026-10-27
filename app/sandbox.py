import sys
import json
import time
import subprocess
import tempfile
import os
from typing import Any, Dict, List, Tuple

# Rate limiting: user_id -> last_timestamp
_SUBMISSION_TIMESTAMPS: Dict[str, float] = {}
RATE_LIMIT_SECONDS = 2.0


def check_rate_limit(user_id: str) -> Tuple[bool, float]:
    """
    Returns (is_allowed, wait_seconds).
    Enforces at least 2 seconds between submissions per user.
    """
    now = time.time()
    last = _SUBMISSION_TIMESTAMPS.get(user_id, 0.0)
    elapsed = now - last
    if elapsed < RATE_LIMIT_SECONDS:
        return False, round(RATE_LIMIT_SECONDS - elapsed, 2)
    _SUBMISSION_TIMESTAMPS[user_id] = now
    return True, 0.0


# Python sandbox harness that executes in subprocess
SANDBOX_HARNESS = """
import sys
import json

# =====================================================================
# RESTRICT ENVIRONMENT & BLOCK DANGEROUS ACCESS
# =====================================================================

# Block network
import socket
def _blocked_socket(*args, **kwargs):
    raise PermissionError("Network access disabled in sandbox")
socket.socket = _blocked_socket

# Block file access
import builtins
import io
def _blocked_open(*args, **kwargs):
    raise PermissionError("File access disabled in sandbox")
builtins.open = _blocked_open
io.open = _blocked_open

# Disable dangerous os / subprocess functions
import os
for attr in ['system', 'popen', 'spawnl', 'spawnle', 'spawnlp', 'spawnlpe',
             'spawnv', 'spawnve', 'spawnvp', 'spawnvpe', 'execv', 'execve',
             'fork', 'kill', 'remove', 'unlink', 'rmdir', 'rename']:
    if hasattr(os, attr):
        setattr(os, attr, None)

# Clean sys.modules
for mod in ['subprocess', 'urllib', 'http', 'ftplib', 'smtplib', 'telnetlib', 'asyncio']:
    sys.modules[mod] = None

# Safe import hook
_orig_import = __import__
def _safe_import(name, *args, **kwargs):
    if name in ('math', 'itertools', 'collections', 're', 'functools', 'string'):
        return _orig_import(name, *args, **kwargs)
    raise PermissionError(f"Module '{name}' access disabled in sandbox")

# Restricted builtins dictionary for user code execution
safe_builtins = {
    'abs': abs,
    'all': all,
    'any': any,
    'bin': bin,
    'bool': bool,
    'chr': chr,
    'dict': dict,
    'divmod': divmod,
    'enumerate': enumerate,
    'filter': filter,
    'float': float,
    'format': format,
    'frozenset': frozenset,
    'hash': hash,
    'hex': hex,
    'int': int,
    'isinstance': isinstance,
    'issubclass': issubclass,
    'iter': iter,
    'len': len,
    'list': list,
    'map': map,
    'max': max,
    'min': min,
    'next': next,
    'oct': oct,
    'ord': ord,
    'pow': pow,
    'range': range,
    'reversed': reversed,
    'round': round,
    'set': set,
    'slice': slice,
    'sorted': sorted,
    'str': str,
    'sum': sum,
    'tuple': tuple,
    'type': type,
    'zip': zip,
    'open': _blocked_open,
    '__import__': _safe_import,
    'print': lambda *args, **kwargs: None,  # Silent print
    'Exception': Exception,
    'ValueError': ValueError,
    'TypeError': TypeError,
    'IndexError': IndexError,
    'KeyError': KeyError,
    'PermissionError': PermissionError,
}

# Pre-import safe libraries
import math
import itertools
import collections
import re
import functools

exec_globals = {
    '__builtins__': safe_builtins,
    'math': math,
    'itertools': itertools,
    'collections': collections,
    're': re,
    'functools': functools,
}

# Read user code and test inputs from stdin
try:
    data = json.loads(sys.stdin.read())
    code = data["code"]
    test_inputs = data["inputs"]
except Exception as e:
    print(json.dumps({"status": "fatal", "error": "Invalid harness payload"}))
    sys.exit(0)

# Execute user code
try:
    exec(code, exec_globals)
except Exception as e:
    print(json.dumps({"status": "compile_error", "error": f"{type(e).__name__}: {str(e)}"}))
    sys.exit(0)

# Locate candidate function: f or solve or last callable
target_fn = exec_globals.get("f") or exec_globals.get("solve")
if not target_fn or not callable(target_fn):
    # Find any function defined
    for k, v in list(exec_globals.items()):
        if callable(v) and k not in ['math', 'itertools', 'collections', 're', 'functools', '__builtins__']:
            target_fn = v
            break

if not target_fn or not callable(target_fn):
    print(json.dumps({"status": "compile_error", "error": "No callable function 'f(x)' or 'solve(x)' defined."}))
    sys.exit(0)

# Evaluate each input
results = []
for inp in test_inputs:
    try:
        # Clone input to avoid mutation issues
        res = target_fn(inp)
        results.append({"status": "ok", "output": res})
    except Exception as e:
        results.append({"status": "runtime_error", "error": f"{type(e).__name__}: {str(e)}"})
        break

print(json.dumps({"status": "success", "results": results}))
"""


def execute_in_sandbox(user_code: str, test_inputs: List[Any], timeout_sec: float = 2.0) -> Dict[str, Any]:
    """
    Execute user Python code in an isolated subprocess with 2-second timeout.
    Returns:
      {"status": "success" | "compile_error" | "timeout" | "runtime_error" | "fatal", ...}
    """
    payload = json.dumps({"code": user_code, "inputs": test_inputs})

    try:
        proc = subprocess.run(
            [sys.executable, "-c", SANDBOX_HARNESS],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "error": "Execution timed out (2.0s limit exceeded). Check for infinite loops or expensive recursions."
        }
    except Exception as e:
        return {
            "status": "fatal",
            "error": "Internal execution fault."
        }

    if proc.returncode != 0 and not proc.stdout.strip():
        # Crash in child process
        err_line = proc.stderr.splitlines()[-1] if proc.stderr else "Subprocess terminated unexpectedly."
        return {
            "status": "runtime_error",
            "error": f"Process error: {err_line}"
        }

    try:
        data = json.loads(proc.stdout)
        return data
    except json.JSONDecodeError:
        return {
            "status": "fatal",
            "error": "Failed to parse sandbox output."
        }
