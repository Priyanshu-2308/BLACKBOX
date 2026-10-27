import random
import copy
from typing import Any, Dict, List, Tuple
from app.generator import apply_rule
from app.sandbox import execute_in_sandbox


def generate_hidden_inputs(input_type: str, seed: int, count: int = 200) -> List[Any]:
    """
    Generate 200 hidden inputs including critical edge cases:
    - 0, negatives, large values, rule boundaries
    - empty string / empty list, single char / element
    """
    rng = random.Random(seed ^ 0xDEADBEEF)
    inputs: List[Any] = []

    if input_type == "int":
        # Edge cases
        edges = [
            0, 1, -1, 2, -2, 3, -3, 4, -4, 5, 6, 7, 8, 9, 10, -10,
            15, 16, 31, 32, 63, 64, 127, 128, 255, 256, 512, 1000, -1000,
            1234, -4321, 9999, -9999, 65535, 65536
        ]
        inputs.extend(edges)
        while len(inputs) < count:
            val = rng.choice([
                rng.randint(-10000, 10000),
                rng.randint(-50, 50),
                rng.randint(0, 1000),
                rng.randint(-5000, 0),
            ])
            inputs.append(val)

    elif input_type == "str":
        edges = [
            "", "a", "A", "z", "Z", "0", "!", "hello", "HELLO", "World",
            "a b c", "  spaces  ", "radar", "racecar", "aeiou", "AEIOU",
            "bcdfg", "BCDFG", "a1b2c3", "ababab", "aaaa", "a" * 25,
            "BlackBox", "Arena", "CodeDecode", "python", "monolith"
        ]
        inputs.extend(edges)
        words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet"]
        while len(inputs) < count:
            mode = rng.randint(1, 4)
            if mode == 1:
                # Random lowercase string
                length = rng.randint(1, 15)
                s = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(length))
            elif mode == 2:
                # Mixed case with vowels
                length = rng.randint(1, 20)
                s = "".join(rng.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(length))
            elif mode == 3:
                # Phrase with spaces
                w_count = rng.randint(2, 4)
                s = " ".join(rng.choice(words) for _ in range(w_count))
            else:
                # Repeated characters
                ch = rng.choice("xyzABC")
                s = ch * rng.randint(2, 12)
            inputs.append(s)

    elif input_type == "list":
        edges = [
            [], [0], [1], [-1], [2], [-2], [0, 0], [1, 2], [2, 1], [-5, 5],
            [1, 2, 3], [3, 2, 1], [0, 1, 0], [-10, 20, -30], [5, 5, 5, 5],
            [1, 2, 3, 4, 5], [10, 9, 8, 7, 6], [2, 4, 6, 8], [1, 3, 5, 7],
            [0, -1, 2, -3, 4, -5], [42] * 8, [100, -100]
        ]
        inputs.extend(edges)
        while len(inputs) < count:
            length = rng.randint(1, 12)
            lst = [rng.randint(-50, 50) for _ in range(length)]
            inputs.append(lst)

    return inputs[:count]


def judge_submission(rule_spec: Dict[str, Any], user_code: str) -> Dict[str, Any]:
    """
    Run user code against 200 hidden inputs.
    On failure, report ONLY ONE failing input and its expected output.
    NEVER leak rule primitives, parameters, or test set.
    """
    input_type = rule_spec["input_type"]
    seed = rule_spec["seed"]
    hidden_inputs = generate_hidden_inputs(input_type, seed, 200)

    # Compute expected outputs
    expected_outputs = []
    for inp in hidden_inputs:
        # Deepcopy input to ensure pure reference
        inp_copy = copy.deepcopy(inp)
        try:
            exp = apply_rule(rule_spec, inp_copy)
            expected_outputs.append(exp)
        except Exception:
            # Server rule execution guard
            expected_outputs.append(None)

    # Run in sandbox
    run_res = execute_in_sandbox(user_code, hidden_inputs, timeout_sec=2.0)

    if run_res.get("status") == "timeout":
        return {
            "passed": False,
            "status": "timeout",
            "error": run_res.get("error", "Execution timed out (2.0s limit exceeded)."),
        }

    if run_res.get("status") in ("compile_error", "fatal"):
        return {
            "passed": False,
            "status": "error",
            "error": run_res.get("error", "Code syntax or import error."),
        }

    results = run_res.get("results", [])
    if not results:
        return {
            "passed": False,
            "status": "error",
            "error": "No execution results returned from sandbox.",
        }

    # Compare outputs against expected
    for idx, (inp, exp) in enumerate(zip(hidden_inputs, expected_outputs)):
        if idx >= len(results):
            # User loop aborted early
            return {
                "passed": False,
                "status": "failed",
                "test_index": idx + 1,
                "failing_input": inp,
                "expected_output": exp,
                "user_error": "Execution terminated before completing all test cases.",
            }

        item = results[idx]
        if item.get("status") != "ok":
            return {
                "passed": False,
                "status": "failed",
                "test_index": idx + 1,
                "failing_input": inp,
                "expected_output": exp,
                "user_error": item.get("error", "Runtime error on this input."),
            }

        user_out = item.get("output")
        if user_out != exp:
            return {
                "passed": False,
                "status": "failed",
                "test_index": idx + 1,
                "failing_input": inp,
                "expected_output": exp,
                "user_output": user_out,
            }

    return {
        "passed": True,
        "status": "solved",
        "tests_passed": 200,
        "total_tests": 200,
    }
