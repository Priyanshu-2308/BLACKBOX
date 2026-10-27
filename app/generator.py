import random
import json
from typing import Any, Dict, List, Optional, Tuple, Set
from app.primitives import PRIMITIVE_REGISTRY


CONDITIONS = {
    "int": [
        {"name": "is_even", "desc": "x is even", "fn": lambda x: x % 2 == 0},
        {"name": "is_non_negative", "desc": "x >= 0", "fn": lambda x: x >= 0},
        {"name": "digit_sum_even", "desc": "sum of digits of x is even", "fn": lambda x: sum(int(d) for d in str(abs(x))) % 2 == 0},
    ],
    "str": [
        {"name": "even_length", "desc": "length of string is even", "fn": lambda s: len(s) % 2 == 0},
        {"name": "starts_with_vowel", "desc": "starts with vowel", "fn": lambda s: bool(s and s[0].lower() in "aeiou")},
        {"name": "has_space", "desc": "contains whitespace", "fn": lambda s: " " in s},
    ],
    "list": [
        {"name": "even_length", "desc": "list length is even", "fn": lambda lst: len(lst) % 2 == 0},
        {"name": "sum_positive", "desc": "sum of list elements >= 0", "fn": lambda lst: sum(lst) >= 0},
        {"name": "first_elem_even", "desc": "first element is even", "fn": lambda lst: bool(lst and lst[0] % 2 == 0)},
    ]
}


def _get_benchmark_inputs(input_type: str) -> List[Any]:
    """Canonical benchmark inputs for duplicate & degeneracy detection."""
    if input_type == "int":
        return [-15, -7, -2, -1, 0, 1, 2, 3, 4, 7, 10, 15, 24, 42, 63, 100, 128, 255, 300, 999]
    elif input_type == "str":
        return [
            "", "a", "Z", "hello", "WORLD", "CodeDecode", "abc", "xyz", "radar",
            "black box", "Python 3", "AEIOU", "12345", "a b c", "stark", "monolith"
        ]
    elif input_type == "list":
        return [
            [], [0], [1], [-1], [1, 2], [3, 1], [-2, 4], [0, 5, 0],
            [1, 2, 3, 4], [5, 4, 3, 2, 1], [-10, 20, -30], [2, 4, 6, 8],
            [1, 3, 5, 7], [42, 42], [-5, -5, -5]
        ]
    return []


def _apply_primitive(step: Dict[str, Any], val: Any) -> Any:
    name = step["name"]
    params = step["params"]
    entry = PRIMITIVE_REGISTRY[name]
    return entry["fn"](val, params)


def apply_rule(rule_spec: Dict[str, Any], x: Any) -> Any:
    """Execute rule pipeline on input x."""
    tier = rule_spec.get("tier", "easy")
    input_type = rule_spec.get("input_type", "int")

    if tier == "hard" and "condition" in rule_spec:
        cond_name = rule_spec["condition"]["name"]
        cond_def = next((c for c in CONDITIONS[input_type] if c["name"] == cond_name), None)
        cond_res = cond_def["fn"](x) if cond_def else True
        pipeline = rule_spec["branch_true"] if cond_res else rule_spec["branch_false"]
    else:
        pipeline = rule_spec.get("pipeline", [])

    curr = x
    for step in pipeline:
        curr = _apply_primitive(step, curr)
    return curr


def describe_rule(rule_spec: Dict[str, Any]) -> str:
    """Generate human-readable rule text for post-solve reveal."""
    def describe_pipeline(pipe: List[Dict[str, Any]]) -> str:
        parts = []
        for step in pipe:
            name = step["name"]
            params = step["params"]
            desc_tmpl = PRIMITIVE_REGISTRY[name]["desc"]
            parts.append(desc_tmpl.format(**params))
        return " ➔ ".join(parts)

    tier = rule_spec.get("tier", "easy")
    if tier == "hard" and "condition" in rule_spec:
        cond_desc = rule_spec["condition"]["desc"]
        true_desc = describe_pipeline(rule_spec["branch_true"])
        false_desc = describe_pipeline(rule_spec["branch_false"])
        return f"If {cond_desc}:\n  ➔ {true_desc}\nElse:\n  ➔ {false_desc}"
    else:
        return describe_pipeline(rule_spec.get("pipeline", []))


def _sample_step(rng: random.Random, input_type: str) -> Dict[str, Any]:
    available = [name for name, meta in PRIMITIVE_REGISTRY.items() if meta["type"] == input_type]
    choice_name = rng.choice(available)
    meta = PRIMITIVE_REGISTRY[choice_name]
    params = meta["param_gen"](rng)
    return {"name": choice_name, "params": params}


def check_degeneracy(rule_spec: Dict[str, Any]) -> bool:
    """
    Returns True if rule is valid and non-degenerate.
    Returns False if rule is constant, identity, crashes, or 90%+ same outputs.
    """
    input_type = rule_spec["input_type"]
    benchmarks = _get_benchmark_inputs(input_type)
    if not benchmarks:
        return False

    outputs = []
    identical_to_input = 0
    for sample in benchmarks:
        try:
            out = apply_rule(rule_spec, sample)
            outputs.append(repr(out))
            if out == sample:
                identical_to_input += 1
        except Exception:
            return False

    # Check identity
    if identical_to_input == len(benchmarks):
        return False

    # Check constant / near constant
    output_counts: Dict[str, int] = {}
    for o in outputs:
        output_counts[o] = output_counts.get(o, 0) + 1

    max_freq = max(output_counts.values()) if output_counts else 0
    if max_freq >= int(len(benchmarks) * 0.9):
        return False

    # Need at least 3 distinct outputs
    if len(output_counts) < 3:
        return False

    return True


def compute_fingerprint(rule_spec: Dict[str, Any]) -> str:
    """Produce deterministic fingerprint string on 8 benchmark inputs."""
    bench = _get_benchmark_inputs(rule_spec["input_type"])[:8]
    outs = []
    for b in bench:
        try:
            outs.append(repr(apply_rule(rule_spec, b)))
        except Exception:
            outs.append("ERR")
    return "|".join(outs)


def generate_question(seed: int, tier: str, existing_fingerprints: Optional[Set[str]] = None) -> Dict[str, Any]:
    """
    Generate a non-degenerate, non-duplicate question.
    Tier:
      - 'easy': 1 primitive
      - 'medium': 2 primitives
      - 'hard': 3 primitives + conditional branch
    """
    rng = random.Random(seed)
    existing_fps = existing_fingerprints if existing_fingerprints is not None else set()

    for attempt in range(100):
        # Pick input type
        input_type = rng.choice(["int", "str", "list"])

        rule_spec: Dict[str, Any] = {
            "tier": tier,
            "input_type": input_type,
            "seed": seed,
        }

        topics = set()
        if tier == "easy":
            step = _sample_step(rng, input_type)
            rule_spec["pipeline"] = [step]
            topics.add(PRIMITIVE_REGISTRY[step["name"]]["topic"])

        elif tier == "medium":
            s1 = _sample_step(rng, input_type)
            s2 = _sample_step(rng, input_type)
            rule_spec["pipeline"] = [s1, s2]
            topics.add(PRIMITIVE_REGISTRY[s1["name"]]["topic"])
            topics.add(PRIMITIVE_REGISTRY[s2["name"]]["topic"])

        else: # hard
            cond_choice = rng.choice(CONDITIONS[input_type])
            rule_spec["condition"] = {"name": cond_choice["name"], "desc": cond_choice["desc"]}
            
            # True branch: 2 primitives
            b_true = [_sample_step(rng, input_type), _sample_step(rng, input_type)]
            # False branch: 1 or 2 primitives
            b_false = [_sample_step(rng, input_type)]
            
            rule_spec["branch_true"] = b_true
            rule_spec["branch_false"] = b_false

            for s in b_true + b_false:
                topics.add(PRIMITIVE_REGISTRY[s["name"]]["topic"])

        rule_spec["topics"] = sorted(list(topics))

        # Check degeneracy
        if not check_degeneracy(rule_spec):
            # Try new random seed step
            rng = random.Random(seed + attempt + 1)
            continue

        # Check duplicate fingerprint
        fp = compute_fingerprint(rule_spec)
        if fp in existing_fps:
            rng = random.Random(seed + attempt + 1)
            continue

        existing_fps.add(fp)
        rule_spec["fingerprint"] = fp
        return rule_spec

    # Fallback to a guaranteed non-degenerate rule if attempts exceed 100
    fallback_step = {"name": "offset_k", "params": {"k": 7}}
    return {
        "tier": tier,
        "input_type": "int",
        "pipeline": [fallback_step],
        "topics": ["math"],
        "seed": seed,
        "fingerprint": "fallback",
    }
