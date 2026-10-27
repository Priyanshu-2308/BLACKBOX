import pytest
from app.judge import judge_submission, generate_hidden_inputs
from app.generator import apply_rule


def test_judge_200_hidden_inputs_generated():
    inputs_int = generate_hidden_inputs("int", seed=42, count=200)
    assert len(inputs_int) == 200
    assert 0 in inputs_int
    assert -1 in inputs_int
    assert 255 in inputs_int

    inputs_str = generate_hidden_inputs("str", seed=42, count=200)
    assert len(inputs_str) == 200
    assert "" in inputs_str
    assert "a" in inputs_str

    inputs_list = generate_hidden_inputs("list", seed=42, count=200)
    assert len(inputs_list) == 200
    assert [] in inputs_list
    assert [0] in inputs_list


def test_judge_passes_correct_implementation():
    rule_spec = {
        "tier": "easy",
        "input_type": "int",
        "pipeline": [{"name": "mult_k", "params": {"k": 3}}],
        "seed": 999
    }
    user_code = """
def f(x):
    return x * 3
"""
    res = judge_submission(rule_spec, user_code)
    assert res["passed"] is True
    assert res["status"] == "solved"
    assert res["tests_passed"] == 200


def test_judge_reports_only_one_failing_input():
    rule_spec = {
        "tier": "easy",
        "input_type": "int",
        "pipeline": [{"name": "mult_k", "params": {"k": 2}}],
        "seed": 777
    }
    # Deliberately fails on negative numbers or values != 1
    user_code = """
def f(x):
    if x == 0:
        return 0
    return 999999
"""
    res = judge_submission(rule_spec, user_code)
    assert res["passed"] is False
    assert res["status"] == "failed"
    assert "failing_input" in res
    assert "expected_output" in res
    # Ensure no rule internals leaked
    assert "rule_spec" not in res
    assert "pipeline" not in res
    assert "params" not in res
