import math
import itertools
from typing import Any, Callable, Dict, List, Tuple


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def _next_prime(n: int) -> int:
    p = max(2, n)
    while not _is_prime(p):
        p += 1
    return p


# =====================================================================
# INTEGER PRIMITIVES
# =====================================================================

def prim_mod_k(x: int, params: Dict[str, Any]) -> int:
    k = params.get("k", 5)
    return x % k if k != 0 else x

def prim_digit_sum(x: int, params: Dict[str, Any]) -> int:
    s = sum(int(d) for d in str(abs(x)))
    return -s if x < 0 and params.get("keep_sign", False) else s

def prim_digit_reverse(x: int, params: Dict[str, Any]) -> int:
    sign = -1 if x < 0 else 1
    rev = int(str(abs(x))[::-1])
    return sign * rev

def prim_bit_and_k(x: int, params: Dict[str, Any]) -> int:
    mask = params.get("mask", 15)
    return x & mask

def prim_bit_or_k(x: int, params: Dict[str, Any]) -> int:
    mask = params.get("mask", 7)
    return x | mask

def prim_bit_xor_k(x: int, params: Dict[str, Any]) -> int:
    mask = params.get("mask", 42)
    return x ^ mask

def prim_bit_shift_left(x: int, params: Dict[str, Any]) -> int:
    shift = params.get("shift", 1)
    # Clamp to prevent exponential blowup
    return (x << shift) % 65536

def prim_bit_shift_right(x: int, params: Dict[str, Any]) -> int:
    shift = params.get("shift", 1)
    return x >> shift

def prim_bit_popcount(x: int, params: Dict[str, Any]) -> int:
    return bin(abs(x)).count("1")

def prim_gcd_k(x: int, params: Dict[str, Any]) -> int:
    k = params.get("k", 12)
    return math.gcd(abs(x), k)

def prim_lcm_k(x: int, params: Dict[str, Any]) -> int:
    k = params.get("k", 6)
    val = abs(x) if abs(x) > 0 else 1
    return (val * k) // math.gcd(val, k)

def prim_collatz(x: int, params: Dict[str, Any]) -> int:
    if x % 2 == 0:
        return x // 2
    return 3 * x + 1

def prim_parity_mult(x: int, params: Dict[str, Any]) -> int:
    even_mult = params.get("even_mult", 2)
    odd_add = params.get("odd_add", 3)
    if x % 2 == 0:
        return x * even_mult
    return x + odd_add

def prim_offset_k(x: int, params: Dict[str, Any]) -> int:
    k = params.get("k", 7)
    return x + k

def prim_mult_k(x: int, params: Dict[str, Any]) -> int:
    k = params.get("k", 3)
    return x * k

def prim_prime_distance(x: int, params: Dict[str, Any]) -> int:
    val = abs(x)
    return _next_prime(val) - val

def prim_alt_digit_sum(x: int, params: Dict[str, Any]) -> int:
    digits = [int(d) for d in str(abs(x))]
    total = 0
    for idx, d in enumerate(digits):
        total += d if idx % 2 == 0 else -d
    return total

def prim_int_sqrt(x: int, params: Dict[str, Any]) -> int:
    return math.isqrt(abs(x))


# =====================================================================
# STRING PRIMITIVES
# =====================================================================

def prim_caesar_shift(s: str, params: Dict[str, Any]) -> str:
    k = params.get("k", 3) % 26
    res = []
    for ch in s:
        if "a" <= ch <= "z":
            res.append(chr((ord(ch) - ord("a") + k) % 26 + ord("a")))
        elif "A" <= ch <= "Z":
            res.append(chr((ord(ch) - ord("A") + k) % 26 + ord("A")))
        else:
            res.append(ch)
    return "".join(res)

def prim_reverse_str(s: str, params: Dict[str, Any]) -> str:
    return s[::-1]

def prim_reverse_words(s: str, params: Dict[str, Any]) -> str:
    parts = s.split(" ")
    return " ".join(parts[::-1])

def prim_reverse_each_word(s: str, params: Dict[str, Any]) -> str:
    parts = s.split(" ")
    return " ".join(p[::-1] for p in parts)

def prim_vowel_upper(s: str, params: Dict[str, Any]) -> str:
    vowels = set("aeiouAEIOU")
    return "".join(ch.upper() if ch in vowels else ch.lower() for ch in s)

def prim_vowel_remove(s: str, params: Dict[str, Any]) -> str:
    vowels = set("aeiouAEIOU")
    res = "".join(ch for ch in s if ch not in vowels)
    return res if res else s

def prim_vowel_replace(s: str, params: Dict[str, Any]) -> str:
    rep = params.get("char", "*")
    vowels = set("aeiouAEIOU")
    return "".join(rep if ch in vowels else ch for ch in s)

def prim_pairwise_swap(s: str, params: Dict[str, Any]) -> str:
    chars = list(s)
    for i in range(0, len(chars) - 1, 2):
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
    return "".join(chars)

def prim_repeat_chars(s: str, params: Dict[str, Any]) -> str:
    k = params.get("k", 2)
    # Guard against huge outputs
    if len(s) * k > 200:
        k = 1
    return "".join(ch * k for ch in s)

def prim_alternate_case(s: str, params: Dict[str, Any]) -> str:
    res = []
    for i, ch in enumerate(s):
        res.append(ch.upper() if i % 2 == 0 else ch.lower())
    return "".join(res)

def prim_rot_str(s: str, params: Dict[str, Any]) -> str:
    if not s:
        return s
    k = params.get("k", 1) % len(s)
    return s[k:] + s[:k]

def prim_remove_consecutive_dupes(s: str, params: Dict[str, Any]) -> str:
    if not s:
        return s
    res = [s[0]]
    for ch in s[1:]:
        if ch != res[-1]:
            res.append(ch)
    return "".join(res)

def prim_mirror_str(s: str, params: Dict[str, Any]) -> str:
    if len(s) > 50:
        return s
    return s + s[::-1]

def prim_count_vowels_tag(s: str, params: Dict[str, Any]) -> str:
    vowels = set("aeiouAEIOU")
    count = sum(1 for ch in s if ch in vowels)
    return f"{s}_{count}"

def prim_interleave_halves(s: str, params: Dict[str, Any]) -> str:
    if len(s) <= 1:
        return s
    mid = (len(s) + 1) // 2
    h1 = s[:mid]
    h2 = s[mid:]
    res = []
    for i in range(max(len(h1), len(h2))):
        if i < len(h1):
            res.append(h1[i])
        if i < len(h2):
            res.append(h2[i])
    return "".join(res)


# =====================================================================
# LIST PRIMITIVES (List[int] -> List[int])
# =====================================================================

def prim_prefix_sums(lst: List[int], params: Dict[str, Any]) -> List[int]:
    return list(itertools.accumulate(lst))

def prim_adjacent_diffs(lst: List[int], params: Dict[str, Any]) -> List[int]:
    if len(lst) <= 1:
        return [0] if lst else []
    return [lst[i] - lst[i - 1] for i in range(1, len(lst))]

def prim_sort_asc(lst: List[int], params: Dict[str, Any]) -> List[int]:
    return sorted(lst)

def prim_sort_desc(lst: List[int], params: Dict[str, Any]) -> List[int]:
    return sorted(lst, reverse=True)

def prim_reverse_list(lst: List[int], params: Dict[str, Any]) -> List[int]:
    return lst[::-1]

def prim_filter_evens(lst: List[int], params: Dict[str, Any]) -> List[int]:
    res = [x for x in lst if x % 2 == 0]
    return res if res else [0]

def prim_filter_odds(lst: List[int], params: Dict[str, Any]) -> List[int]:
    res = [x for x in lst if x % 2 != 0]
    return res if res else [1]

def prim_map_mult_k(lst: List[int], params: Dict[str, Any]) -> List[int]:
    k = params.get("k", 2)
    return [x * k for x in lst]

def prim_map_add_k(lst: List[int], params: Dict[str, Any]) -> List[int]:
    k = params.get("k", 3)
    return [x + k for x in lst]

def prim_alternating_sign(lst: List[int], params: Dict[str, Any]) -> List[int]:
    return [x if i % 2 == 0 else -x for i, x in enumerate(lst)]

def prim_rotate_list(lst: List[int], params: Dict[str, Any]) -> List[int]:
    if not lst:
        return lst
    k = params.get("k", 1) % len(lst)
    return lst[k:] + lst[:k]

def prim_running_max(lst: List[int], params: Dict[str, Any]) -> List[int]:
    if not lst:
        return lst
    res = []
    curr = lst[0]
    for x in lst:
        curr = max(curr, x)
        res.append(curr)
    return res

def prim_moving_window_sum(lst: List[int], params: Dict[str, Any]) -> List[int]:
    if len(lst) <= 1:
        return lst[:]
    return [lst[i] + lst[i + 1] for i in range(len(lst) - 1)]


# =====================================================================
# PRIMITIVE REGISTRY & SPECIFICATION
# =====================================================================

PRIMITIVE_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Integers (Math & Bits)
    "mod_k": {
        "fn": prim_mod_k,
        "type": "int",
        "topic": "math",
        "desc": "Modulo {k}",
        "param_gen": lambda rng: {"k": rng.choice([2, 3, 4, 5, 7, 8, 9, 10, 11, 13])},
    },
    "digit_sum": {
        "fn": prim_digit_sum,
        "type": "int",
        "topic": "math",
        "desc": "Sum of digits",
        "param_gen": lambda rng: {"keep_sign": rng.choice([True, False])},
    },
    "digit_reverse": {
        "fn": prim_digit_reverse,
        "type": "int",
        "topic": "math",
        "desc": "Reverse digits",
        "param_gen": lambda rng: {},
    },
    "bit_and_k": {
        "fn": prim_bit_and_k,
        "type": "int",
        "topic": "bits",
        "desc": "Bitwise AND with {mask}",
        "param_gen": lambda rng: {"mask": rng.choice([3, 7, 15, 31, 63, 127])},
    },
    "bit_or_k": {
        "fn": prim_bit_or_k,
        "type": "int",
        "topic": "bits",
        "desc": "Bitwise OR with {mask}",
        "param_gen": lambda rng: {"mask": rng.choice([1, 3, 5, 7, 9, 15])},
    },
    "bit_xor_k": {
        "fn": prim_bit_xor_k,
        "type": "int",
        "topic": "bits",
        "desc": "Bitwise XOR with {mask}",
        "param_gen": lambda rng: {"mask": rng.choice([3, 5, 7, 10, 15, 23, 42, 63])},
    },
    "bit_shift_left": {
        "fn": prim_bit_shift_left,
        "type": "int",
        "topic": "bits",
        "desc": "Bitwise left shift by {shift} (mod 65536)",
        "param_gen": lambda rng: {"shift": rng.choice([1, 2, 3, 4])},
    },
    "bit_shift_right": {
        "fn": prim_bit_shift_right,
        "type": "int",
        "topic": "bits",
        "desc": "Bitwise right shift by {shift}",
        "param_gen": lambda rng: {"shift": rng.choice([1, 2, 3])},
    },
    "bit_popcount": {
        "fn": prim_bit_popcount,
        "type": "int",
        "topic": "bits",
        "desc": "Count set bits (popcount)",
        "param_gen": lambda rng: {},
    },
    "gcd_k": {
        "fn": prim_gcd_k,
        "type": "int",
        "topic": "math",
        "desc": "GCD with {k}",
        "param_gen": lambda rng: {"k": rng.choice([6, 8, 12, 15, 18, 20, 24, 30])},
    },
    "lcm_k": {
        "fn": prim_lcm_k,
        "type": "int",
        "topic": "math",
        "desc": "LCM with {k}",
        "param_gen": lambda rng: {"k": rng.choice([2, 3, 4, 5, 6])},
    },
    "collatz": {
        "fn": prim_collatz,
        "type": "int",
        "topic": "math",
        "desc": "Collatz step (n/2 if even else 3n+1)",
        "param_gen": lambda rng: {},
    },
    "parity_mult": {
        "fn": prim_parity_mult,
        "type": "int",
        "topic": "math",
        "desc": "Multiply by {even_mult} if even, add {odd_add} if odd",
        "param_gen": lambda rng: {"even_mult": rng.choice([2, 3, 4]), "odd_add": rng.choice([1, 3, 5])},
    },
    "offset_k": {
        "fn": prim_offset_k,
        "type": "int",
        "topic": "math",
        "desc": "Add offset {k}",
        "param_gen": lambda rng: {"k": rng.choice([-15, -7, -3, 3, 5, 7, 11, 13, 21])},
    },
    "mult_k": {
        "fn": prim_mult_k,
        "type": "int",
        "topic": "math",
        "desc": "Multiply by {k}",
        "param_gen": lambda rng: {"k": rng.choice([2, 3, 4, 5, -2, -3])},
    },
    "prime_distance": {
        "fn": prim_prime_distance,
        "type": "int",
        "topic": "math",
        "desc": "Distance to next prime",
        "param_gen": lambda rng: {},
    },
    "alt_digit_sum": {
        "fn": prim_alt_digit_sum,
        "type": "int",
        "topic": "math",
        "desc": "Alternating sum of digits",
        "param_gen": lambda rng: {},
    },
    "int_sqrt": {
        "fn": prim_int_sqrt,
        "type": "int",
        "topic": "math",
        "desc": "Integer square root",
        "param_gen": lambda rng: {},
    },

    # Strings
    "caesar_shift": {
        "fn": prim_caesar_shift,
        "type": "str",
        "topic": "strings",
        "desc": "Caesar shift by {k}",
        "param_gen": lambda rng: {"k": rng.choice([1, 2, 3, 4, 5, 7, 13, 17, 21])},
    },
    "reverse_str": {
        "fn": prim_reverse_str,
        "type": "str",
        "topic": "strings",
        "desc": "Reverse string",
        "param_gen": lambda rng: {},
    },
    "reverse_words": {
        "fn": prim_reverse_words,
        "type": "str",
        "topic": "strings",
        "desc": "Reverse words order",
        "param_gen": lambda rng: {},
    },
    "reverse_each_word": {
        "fn": prim_reverse_each_word,
        "type": "str",
        "topic": "strings",
        "desc": "Reverse each word",
        "param_gen": lambda rng: {},
    },
    "vowel_upper": {
        "fn": prim_vowel_upper,
        "type": "str",
        "topic": "strings",
        "desc": "Uppercase vowels, lowercase consonants",
        "param_gen": lambda rng: {},
    },
    "vowel_remove": {
        "fn": prim_vowel_remove,
        "type": "str",
        "topic": "strings",
        "desc": "Remove vowels",
        "param_gen": lambda rng: {},
    },
    "vowel_replace": {
        "fn": prim_vowel_replace,
        "type": "str",
        "topic": "strings",
        "desc": "Replace vowels with '{char}'",
        "param_gen": lambda rng: {"char": rng.choice(["*", "_", "#", "X", "0"])},
    },
    "pairwise_swap": {
        "fn": prim_pairwise_swap,
        "type": "str",
        "topic": "strings",
        "desc": "Swap adjacent characters",
        "param_gen": lambda rng: {},
    },
    "repeat_chars": {
        "fn": prim_repeat_chars,
        "type": "str",
        "topic": "strings",
        "desc": "Repeat each character {k} times",
        "param_gen": lambda rng: {"k": rng.choice([2, 3])},
    },
    "alternate_case": {
        "fn": prim_alternate_case,
        "type": "str",
        "topic": "strings",
        "desc": "Alternate letter case",
        "param_gen": lambda rng: {},
    },
    "rot_str": {
        "fn": prim_rot_str,
        "type": "str",
        "topic": "strings",
        "desc": "Rotate string left by {k}",
        "param_gen": lambda rng: {"k": rng.choice([1, 2, 3, 4])},
    },
    "remove_consecutive_dupes": {
        "fn": prim_remove_consecutive_dupes,
        "type": "str",
        "topic": "strings",
        "desc": "Collapse consecutive duplicates",
        "param_gen": lambda rng: {},
    },
    "mirror_str": {
        "fn": prim_mirror_str,
        "type": "str",
        "topic": "strings",
        "desc": "Mirror string (s + reverse(s))",
        "param_gen": lambda rng: {},
    },
    "count_vowels_tag": {
        "fn": prim_count_vowels_tag,
        "type": "str",
        "topic": "strings",
        "desc": "Append vowel count tag",
        "param_gen": lambda rng: {},
    },
    "interleave_halves": {
        "fn": prim_interleave_halves,
        "type": "str",
        "topic": "strings",
        "desc": "Interleave string halves",
        "param_gen": lambda rng: {},
    },

    # Lists
    "prefix_sums": {
        "fn": prim_prefix_sums,
        "type": "list",
        "topic": "lists",
        "desc": "Prefix sums",
        "param_gen": lambda rng: {},
    },
    "adjacent_diffs": {
        "fn": prim_adjacent_diffs,
        "type": "list",
        "topic": "lists",
        "desc": "Adjacent element differences",
        "param_gen": lambda rng: {},
    },
    "sort_asc": {
        "fn": prim_sort_asc,
        "type": "list",
        "topic": "lists",
        "desc": "Sort ascending",
        "param_gen": lambda rng: {},
    },
    "sort_desc": {
        "fn": prim_sort_desc,
        "type": "list",
        "topic": "lists",
        "desc": "Sort descending",
        "param_gen": lambda rng: {},
    },
    "reverse_list": {
        "fn": prim_reverse_list,
        "type": "list",
        "topic": "lists",
        "desc": "Reverse list",
        "param_gen": lambda rng: {},
    },
    "filter_evens": {
        "fn": prim_filter_evens,
        "type": "list",
        "topic": "lists",
        "desc": "Filter even numbers",
        "param_gen": lambda rng: {},
    },
    "filter_odds": {
        "fn": prim_filter_odds,
        "type": "list",
        "topic": "lists",
        "desc": "Filter odd numbers",
        "param_gen": lambda rng: {},
    },
    "map_mult_k": {
        "fn": prim_map_mult_k,
        "type": "list",
        "topic": "lists",
        "desc": "Multiply each element by {k}",
        "param_gen": lambda rng: {"k": rng.choice([2, 3, -1, -2])},
    },
    "map_add_k": {
        "fn": prim_map_add_k,
        "type": "list",
        "topic": "lists",
        "desc": "Add {k} to each element",
        "param_gen": lambda rng: {"k": rng.choice([1, 2, 3, 5, -1, -3])},
    },
    "alternating_sign": {
        "fn": prim_alternating_sign,
        "type": "list",
        "topic": "lists",
        "desc": "Alternate sign of elements",
        "param_gen": lambda rng: {},
    },
    "rotate_list": {
        "fn": prim_rotate_list,
        "type": "list",
        "topic": "lists",
        "desc": "Rotate list by {k}",
        "param_gen": lambda rng: {"k": rng.choice([1, 2, 3])},
    },
    "running_max": {
        "fn": prim_running_max,
        "type": "list",
        "topic": "lists",
        "desc": "Running maximum",
        "param_gen": lambda rng: {},
    },
    "moving_window_sum": {
        "fn": prim_moving_window_sum,
        "type": "list",
        "topic": "lists",
        "desc": "Moving window pair sums",
        "param_gen": lambda rng: {},
    },
}
