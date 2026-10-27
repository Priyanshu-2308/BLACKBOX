import pytest
import random
from app.generator import check_degeneracy, generate_question
from app.primitives import PRIMITIVE_REGISTRY


def test_degeneracy_rejects_constant_rule():
    # Construct an artificial constant rule (e.g. bitwise AND with 0)
    rule_spec = {
        "tier": "easy",
        "input_type": "int",
        "pipeline": [{"name": "bit_and_k", "params": {"mask": 0}}],
        "seed": 123
    }
    assert check_degeneracy(rule_spec) is False


def test_degeneracy_rejects_identity_rule():
    # Construct an artificial identity rule (e.g. modulo 0 fallback or shift by 0)
    rule_spec = {
        "tier": "easy",
        "input_type": "int",
        "pipeline": [{"name": "offset_k", "params": {"k": 0}}],
        "seed": 123
    }
    assert check_degeneracy(rule_spec) is False


def test_generator_produces_non_degenerate_rules():
    fps = set()
    for tier in ["easy", "medium", "hard"]:
        for i in range(5):
            rule = generate_question(seed=1000 + i, tier=tier, existing_fingerprints=fps)
            assert check_degeneracy(rule) is True
            assert len(rule["topics"]) >= 1


def test_all_primitives_safe_on_edge_cases():
    rng = random.Random(42)
    int_edges = [0, -1, 1, -100, 100, 99999]
    str_edges = ["", "a", "A", "   ", "hello world", "aeiou", "123!@#"]
    list_edges = [[], [0], [1], [-1], [1, 2, 3], [-5, 5], [10] * 5]

    for name, meta in PRIMITIVE_REGISTRY.items():
        fn = meta["fn"]
        ptype = meta["type"]
        params = meta["param_gen"](rng)

        if ptype == "int":
            for x in int_edges:
                out = fn(x, params)
                assert isinstance(out, (int, float))
        elif ptype == "str":
            for s in str_edges:
                out = fn(s, params)
                assert isinstance(out, str)
        elif ptype == "list":
            for lst in list_edges:
                out = fn(lst, params)
                assert isinstance(out, list)
