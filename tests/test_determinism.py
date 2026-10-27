import pytest
from datetime import datetime, timedelta
from app.config import derive_seed, get_daily_info, IST


def test_seed_determinism_for_fixed_secret():
    s1 = derive_seed("benchmark_label_alpha")
    s2 = derive_seed("benchmark_label_alpha")
    assert s1 == s2
    assert isinstance(s1, int)

    s3 = derive_seed("benchmark_label_beta")
    assert s1 != s3


def test_daily_puzzle_differs_by_date():
    _, tier1, _, seed1 = get_daily_info("2026-10-26")
    _, tier2, _, seed2 = get_daily_info("2026-10-27")
    _, tier3, _, seed3 = get_daily_info("2026-10-28")

    assert seed1 != seed2
    assert seed2 != seed3
    assert seed1 != seed3


def test_weekly_difficulty_pattern():
    # 2026-10-26 is Monday -> Easy
    _, t_mon, _, _ = get_daily_info("2026-10-26")
    assert t_mon == "easy"

    # 2026-10-27 is Tuesday -> Easy
    _, t_tue, _, _ = get_daily_info("2026-10-27")
    assert t_tue == "easy"

    # 2026-10-28 is Wednesday -> Medium
    _, t_wed, _, _ = get_daily_info("2026-10-28")
    assert t_wed == "medium"

    # 2026-10-29 is Thursday -> Medium
    _, t_thu, _, _ = get_daily_info("2026-10-29")
    assert t_thu == "medium"

    # 2026-10-30 is Friday -> Medium
    _, t_fri, _, _ = get_daily_info("2026-10-30")
    assert t_fri == "medium"

    # 2026-10-31 is Saturday -> Hard
    _, t_sat, _, _ = get_daily_info("2026-10-31")
    assert t_sat == "hard"

    # 2026-11-01 is Sunday -> Hard
    _, t_sun, _, _ = get_daily_info("2026-11-01")
    assert t_sun == "hard"


def test_countdown_seconds_to_midnight_ist():
    _, _, sec_left, _ = get_daily_info()
    assert 0 <= sec_left <= 86400
