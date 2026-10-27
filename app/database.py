import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from app.config import DB_PATH, derive_seed, get_daily_info, get_ist_now
from app.generator import generate_question, apply_rule, describe_rule
from app.judge import judge_submission
from app.sandbox import check_rate_limit


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables and pre-populate library and today's daily puzzle."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id TEXT PRIMARY KEY,
        tier TEXT NOT NULL,
        input_type TEXT NOT NULL,
        topics TEXT NOT NULL,
        seed INTEGER NOT NULL,
        rule_spec_json TEXT NOT NULL,
        is_daily INTEGER NOT NULL DEFAULT 0,
        daily_date TEXT,
        fingerprint TEXT,
        created_at TEXT NOT NULL,
        total_attempts INTEGER DEFAULT 0,
        total_solves INTEGER DEFAULT 0
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        question_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'unsolved',
        queries_used INTEGER DEFAULT 0,
        queries_history TEXT DEFAULT '[]',
        attempts_count INTEGER DEFAULT 0,
        started_at TEXT,
        solved_at TEXT,
        duration_seconds REAL DEFAULT 0.0,
        UNIQUE(user_id, question_id)
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_q_is_daily ON questions(is_daily, daily_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_up_user ON user_progress(user_id, question_id);")

    conn.commit()

    # Pre-generate library questions if empty (100 easy, 100 medium, 100 hard)
    cur.execute("SELECT COUNT(*) as cnt FROM questions WHERE is_daily = 0")
    count = cur.fetchone()["cnt"]
    if count < 300:
        _populate_initial_library(conn, target_per_tier=100)

    # Ensure today's daily puzzle exists
    today_str, tier, _, seed = get_daily_info()
    cur.execute("SELECT id FROM questions WHERE is_daily = 1 AND daily_date = ?", (today_str,))
    if not cur.fetchone():
        _create_daily_puzzle_record(conn, today_str, tier, seed)

    # Ensure default user exists
    cur.execute("SELECT id FROM users WHERE username = 'contender'")
    if not cur.fetchone():
        now_iso = datetime.now().isoformat()
        cur.execute("INSERT INTO users (id, username, created_at) VALUES ('u_contender', 'contender', ?)", (now_iso,))
        conn.commit()

    conn.close()


def _populate_initial_library(conn: sqlite3.Connection, target_per_tier: int = 100):
    cur = conn.cursor()
    cur.execute("SELECT fingerprint FROM questions WHERE fingerprint IS NOT NULL")
    fps: Set[str] = {row["fingerprint"] for row in cur.fetchall()}

    tiers = [("easy", target_per_tier), ("medium", target_per_tier), ("hard", target_per_tier)]
    q_num = 1
    now_iso = datetime.now().isoformat()

    for tier, target in tiers:
        cur.execute("SELECT COUNT(*) as cnt FROM questions WHERE is_daily = 0 AND tier = ?", (tier,))
        existing = cur.fetchone()["cnt"]
        needed = target - existing

        for i in range(needed):
            q_id = f"Q-{tier[0].upper()}{str(q_num).zfill(3)}"
            q_num += 1
            seed = derive_seed(f"lib_{tier}_{i}_{q_id}")
            rule_spec = generate_question(seed, tier, fps)

            cur.execute("""
            INSERT OR REPLACE INTO questions (
                id, tier, input_type, topics, seed, rule_spec_json, is_daily, daily_date, fingerprint, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
            """, (
                q_id,
                tier,
                rule_spec["input_type"],
                json.dumps(rule_spec["topics"]),
                seed,
                json.dumps(rule_spec),
                rule_spec.get("fingerprint", ""),
                now_iso
            ))
        conn.commit()


def _create_daily_puzzle_record(conn: sqlite3.Connection, date_str: str, tier: str, seed: int):
    cur = conn.cursor()
    rule_spec = generate_question(seed, tier)
    q_id = f"POTD-{date_str}"
    now_iso = datetime.now().isoformat()

    cur.execute("""
    INSERT OR REPLACE INTO questions (
        id, tier, input_type, topics, seed, rule_spec_json, is_daily, daily_date, fingerprint, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
    """, (
        q_id,
        tier,
        rule_spec["input_type"],
        json.dumps(rule_spec["topics"]),
        seed,
        json.dumps(rule_spec),
        date_str,
        rule_spec.get("fingerprint", ""),
        now_iso
    ))
    conn.commit()


def get_or_create_daily_puzzle(target_date: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve or create POTD for the given date in Asia/Kolkata."""
    date_str, tier, seconds_remaining, seed = get_daily_info(target_date)
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, tier, input_type, topics, is_daily, daily_date FROM questions WHERE is_daily = 1 AND daily_date = ?", (date_str,))
    row = cur.fetchone()
    if not row:
        _create_daily_puzzle_record(conn, date_str, tier, seed)
        cur.execute("SELECT id, tier, input_type, topics, is_daily, daily_date FROM questions WHERE is_daily = 1 AND daily_date = ?", (date_str,))
        row = cur.fetchone()

    res = dict(row)
    res["topics"] = json.loads(res["topics"])
    res["seconds_until_reset"] = seconds_remaining
    conn.close()
    return res


def get_library_questions(
    user_id: str,
    tier: Optional[str] = None,
    topic: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get library questions with user progress.
    SECRECY: Never select rule_spec_json.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
    SELECT q.id, q.tier, q.input_type, q.topics, q.total_attempts, q.total_solves,
           COALESCE(up.status, 'unsolved') as user_status,
           COALESCE(up.queries_used, 0) as queries_used
    FROM questions q
    LEFT JOIN user_progress up ON q.id = up.question_id AND up.user_id = ?
    WHERE q.is_daily = 0
    """
    params: List[Any] = [user_id]

    if tier and tier.upper() != "ALL":
        query += " AND q.tier = ?"
        params.append(tier.lower())

    if topic and topic.upper() != "ALL":
        query += " AND q.topics LIKE ?"
        params.append(f'%"{topic}"%')

    if status and status.upper() != "ALL":
        query += " AND COALESCE(up.status, 'unsolved') = ?"
        params.append(status.lower())

    # Count total matching
    count_query = f"SELECT COUNT(*) as total FROM ({query})"
    cur.execute(count_query, params)
    total_count = cur.fetchone()["total"]

    query += " ORDER BY q.id ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cur.execute(query, params)
    rows = cur.fetchall()

    questions = []
    for r in rows:
        d = dict(r)
        d["topics"] = json.loads(d["topics"])
        attempts = d["total_attempts"]
        solves = d["total_solves"]
        d["solve_rate"] = round((solves / attempts * 100) if attempts > 0 else 0.0, 1)
        questions.append(d)

    conn.close()
    return {"total": total_count, "questions": questions}


def get_question_meta(question_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve public question metadata and user's query progress."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT q.id, q.tier, q.input_type, q.topics, q.is_daily, q.daily_date,
           COALESCE(up.status, 'unsolved') as user_status,
           COALESCE(up.queries_used, 0) as queries_used,
           COALESCE(up.queries_history, '[]') as queries_history,
           COALESCE(up.attempts_count, 0) as attempts_count,
           up.started_at, up.solved_at, up.duration_seconds
    FROM questions q
    LEFT JOIN user_progress up ON q.id = up.question_id AND up.user_id = ?
    WHERE q.id = ?
    """, (user_id, question_id))

    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    res = dict(row)
    res["topics"] = json.loads(res["topics"])
    res["queries_history"] = json.loads(res["queries_history"])
    res["max_queries"] = 30
    res["remaining_queries"] = max(0, 30 - res["queries_used"])

    if res["is_daily"]:
        _, _, sec_left, _ = get_daily_info(res["daily_date"])
        res["seconds_until_reset"] = sec_left

    conn.close()
    return res


def query_oracle(question_id: str, user_id: str, input_value: Any) -> Dict[str, Any]:
    """
    Query the black box function f(input_value).
    - Limit: 30 queries per question per user.
    - Validate input type.
    - Secrecy: No internal rule parameters in errors.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT rule_spec_json, input_type FROM questions WHERE id = ?", (question_id,))
    q_row = cur.fetchone()
    if not q_row:
        conn.close()
        raise ValueError("Chamber does not exist.")

    input_type = q_row["input_type"]
    rule_spec = json.loads(q_row["rule_spec_json"])

    # Validate input type
    if input_type == "int":
        if not isinstance(input_value, int) or isinstance(input_value, bool):
            conn.close()
            raise ValueError("Input must be an integer (e.g. 42 or -7).")
        if abs(input_value) > 1_000_000_000:
            conn.close()
            raise ValueError("Integer input value out of permissible bounds.")

    elif input_type == "str":
        if not isinstance(input_value, str):
            conn.close()
            raise ValueError("Input must be a string (e.g. 'hello').")
        if len(input_value) > 200:
            conn.close()
            raise ValueError("String input length exceeds 200 characters.")

    elif input_type == "list":
        if not isinstance(input_value, list):
            conn.close()
            raise ValueError("Input must be a list of integers (e.g. [1, 2, 3]).")
        if len(input_value) > 50:
            conn.close()
            raise ValueError("List length exceeds 50 elements.")
        for item in input_value:
            if not isinstance(item, int) or isinstance(item, bool):
                conn.close()
                raise ValueError("All list elements must be integers.")

    # Check progress & query limit
    cur.execute("SELECT status, queries_used, queries_history, started_at FROM user_progress WHERE user_id = ? AND question_id = ?", (user_id, question_id))
    prog = cur.fetchone()
    now_iso = datetime.now().isoformat()

    if not prog:
        queries_used = 0
        history = []
        status = "attempted"
        started_at = now_iso
        cur.execute("""
        INSERT INTO user_progress (user_id, question_id, status, queries_used, queries_history, started_at)
        VALUES (?, ?, ?, 0, '[]', ?)
        """, (user_id, question_id, status, started_at))
    else:
        queries_used = prog["queries_used"]
        history = json.loads(prog["queries_history"])
        status = prog["status"] if prog["status"] in ("solved", "given_up") else "attempted"
        started_at = prog["started_at"] or now_iso

    if queries_used >= 30:
        conn.close()
        raise ValueError("Probe capacity exhausted (30 / 30 probes used). Submit solution or surrender.")

    # Execute f(x)
    try:
        output_val = apply_rule(rule_spec, input_value)
    except Exception:
        conn.close()
        raise ValueError("Evaluation rejected on input vector.")

    queries_used += 1
    history.append({
        "num": queries_used,
        "input": input_value,
        "output": output_val
    })

    cur.execute("""
    UPDATE user_progress
    SET queries_used = ?, queries_history = ?, status = ?, started_at = ?
    WHERE user_id = ? AND question_id = ?
    """, (queries_used, json.dumps(history), status, started_at, user_id, question_id))

    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "output": output_val,
        "queries_used": queries_used,
        "remaining": 30 - queries_used,
        "history": history
    }


def submit_code_solution(question_id: str, user_id: str, code: str) -> Dict[str, Any]:
    """
    Submit Python code to judge against 200 hidden test cases.
    - Subprocess sandbox execution.
    - Rate-limited.
    - Single failing input report on failure.
    """
    is_allowed, wait_sec = check_rate_limit(user_id)
    if not is_allowed:
        return {
            "passed": False,
            "status": "rate_limited",
            "error": f"Rate limit active. Please wait {wait_sec}s before next transmission."
        }

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT rule_spec_json FROM questions WHERE id = ?", (question_id,))
    q_row = cur.fetchone()
    if not q_row:
        conn.close()
        return {"passed": False, "status": "error", "error": "Chamber does not exist."}

    rule_spec = json.loads(q_row["rule_spec_json"])

    # Update question attempts
    cur.execute("UPDATE questions SET total_attempts = total_attempts + 1 WHERE id = ?", (question_id,))

    # Update user progress attempts
    now_iso = datetime.now().isoformat()
    cur.execute("SELECT started_at, attempts_count, status FROM user_progress WHERE user_id = ? AND question_id = ?", (user_id, question_id))
    prog = cur.fetchone()
    if not prog:
        started_at = now_iso
        attempts = 1
        cur.execute("""
        INSERT INTO user_progress (user_id, question_id, status, attempts_count, started_at)
        VALUES (?, ?, 'attempted', 1, ?)
        """, (user_id, question_id, started_at))
    else:
        started_at = prog["started_at"] or now_iso
        attempts = prog["attempts_count"] + 1
        cur.execute("""
        UPDATE user_progress SET attempts_count = ? WHERE user_id = ? AND question_id = ?
        """, (attempts, user_id, question_id))
    conn.commit()

    # Judge
    judge_res = judge_submission(rule_spec, code)

    if judge_res.get("passed"):
        # Solved!
        cur.execute("UPDATE questions SET total_solves = total_solves + 1 WHERE id = ?", (question_id,))
        start_dt = datetime.fromisoformat(started_at) if started_at else datetime.now()
        duration = max(1.0, round((datetime.now() - start_dt).total_seconds(), 2))

        cur.execute("""
        UPDATE user_progress
        SET status = 'solved', solved_at = ?, duration_seconds = ?
        WHERE user_id = ? AND question_id = ?
        """, (now_iso, duration, user_id, question_id))
        conn.commit()

        judge_res["duration_seconds"] = duration

    conn.close()
    return judge_res


def give_up_question(question_id: str, user_id: str) -> Dict[str, Any]:
    """Surrender puzzle to unlock rule revelation."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO user_progress (user_id, question_id, status)
    VALUES (?, ?, 'given_up')
    ON CONFLICT(user_id, question_id) DO UPDATE SET status = 'given_up'
    WHERE status != 'solved'
    """, (user_id, question_id))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Chamber declassified."}


def reveal_rule(question_id: str, user_id: str) -> Dict[str, Any]:
    """
    Reveal rule formula ONLY if user has solved or given up.
    SECRECY: Strictly locked otherwise.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT status FROM user_progress WHERE user_id = ? AND question_id = ?", (user_id, question_id))
    prog = cur.fetchone()
    if not prog or prog["status"] not in ("solved", "given_up"):
        conn.close()
        raise PermissionError("Access Denied: Rule remains encrypted until solved or surrendered.")

    cur.execute("SELECT rule_spec_json FROM questions WHERE id = ?", (question_id,))
    q_row = cur.fetchone()
    conn.close()

    if not q_row:
        raise ValueError("Chamber does not exist.")

    rule_spec = json.loads(q_row["rule_spec_json"])
    formula_text = describe_rule(rule_spec)
    return {
        "status": "declassified",
        "question_id": question_id,
        "rule_formula": formula_text
    }


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Compute user streak, total solved, breakdown by tier, and solved dates.
    Streak: Consecutive days where daily puzzle was solved in IST.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT up.question_id, up.status, up.solved_at, q.tier, q.is_daily, q.daily_date
    FROM user_progress up
    JOIN questions q ON up.question_id = q.id
    WHERE up.user_id = ? AND up.status = 'solved'
    ORDER BY up.solved_at DESC
    """, (user_id,))
    solved_rows = cur.fetchall()

    tier_counts = {"easy": 0, "medium": 0, "hard": 0}
    daily_solved_dates: Set[str] = set()

    for r in solved_rows:
        t = r["tier"]
        tier_counts[t] = tier_counts.get(t, 0) + 1
        if r["is_daily"] and r["daily_date"]:
            daily_solved_dates.add(r["daily_date"])

    # Calculate streak from current IST date backwards
    ist_today = get_ist_now().date()
    streak = 0
    check_date = ist_today

    # If today not solved yet, check if yesterday was solved to keep active streak
    today_str = check_date.strftime("%Y-%m-%d")
    yesterday_str = (check_date - timedelta(days=1)).strftime("%Y-%m-%d")

    if today_str in daily_solved_dates:
        curr = check_date
    elif yesterday_str in daily_solved_dates:
        curr = check_date - timedelta(days=1)
    else:
        curr = None

    if curr:
        while curr.strftime("%Y-%m-%d") in daily_solved_dates:
            streak += 1
            curr = curr - timedelta(days=1)

    conn.close()
    return {
        "user_id": user_id,
        "streak": streak,
        "total_solved": len(solved_rows),
        "tier_counts": tier_counts,
        "daily_solved_dates": sorted(list(daily_solved_dates), reverse=True)
    }


def get_daily_leaderboard(date_str: str) -> List[Dict[str, Any]]:
    """Leaderboard for a daily puzzle: fewest queries, then fastest duration."""
    q_id = f"POTD-{date_str}"
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT u.username, up.queries_used, up.duration_seconds, up.solved_at
    FROM user_progress up
    JOIN users u ON up.user_id = u.id
    WHERE up.question_id = ? AND up.status = 'solved'
    ORDER BY up.queries_used ASC, up.duration_seconds ASC
    LIMIT 50
    """, (q_id,))

    rows = cur.fetchall()
    leaderboard = []
    for idx, r in enumerate(rows):
        leaderboard.append({
            "rank": idx + 1,
            "username": r["username"],
            "queries": r["queries_used"],
            "duration": round(r["duration_seconds"], 1),
            "solved_at": r["solved_at"]
        })

    conn.close()
    return leaderboard


def get_random_unsolved_id(user_id: str) -> Optional[str]:
    """Find a random unsolved library question for the user."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT q.id FROM questions q
    LEFT JOIN user_progress up ON q.id = up.question_id AND up.user_id = ?
    WHERE q.is_daily = 0 AND (up.status IS NULL OR up.status = 'unsolved')
    ORDER BY RANDOM()
    LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["id"] if row else None


def generate_new_batch(tier: str, count: int = 10) -> int:
    """Add more library questions with fresh random seeds."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT fingerprint FROM questions WHERE fingerprint IS NOT NULL")
    fps: Set[str] = {row["fingerprint"] for row in cur.fetchall()}

    cur.execute("SELECT COUNT(*) as cnt FROM questions WHERE is_daily = 0")
    total_existing = cur.fetchone()["cnt"]

    now_iso = datetime.now().isoformat()
    added = 0
    for i in range(count):
        idx = total_existing + i + 1
        q_id = f"Q-{tier[0].upper()}{str(idx).zfill(3)}"
        seed = derive_seed(f"batch_{tier}_{time.time()}_{idx}")
        rule_spec = generate_question(seed, tier, fps)

        cur.execute("""
        INSERT OR REPLACE INTO questions (
            id, tier, input_type, topics, seed, rule_spec_json, is_daily, daily_date, fingerprint, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
        """, (
            q_id,
            tier,
            rule_spec["input_type"],
            json.dumps(rule_spec["topics"]),
            seed,
            json.dumps(rule_spec),
            rule_spec.get("fingerprint", ""),
            now_iso
        ))
        added += 1

    conn.commit()
    conn.close()
    return added
