import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field

from app import database
from app.config import get_ist_now


router = APIRouter(prefix="/api")


# --- Pydantic Request Models ---

class QueryRequest(BaseModel):
    question_id: str
    input_value: Any


class SubmitRequest(BaseModel):
    question_id: str
    code: str


class SwitchUserRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)


class BatchRequest(BaseModel):
    tier: str = Field("medium", pattern="^(easy|medium|hard)$")
    count: int = Field(10, ge=1, le=50)


def get_current_user(x_username: Optional[str] = Header(None)) -> str:
    """Helper to resolve username from header or default."""
    username = (x_username or "contender").strip()
    if not username:
        username = "contender"
    # Normalize ID
    clean_id = f"u_{''.join(c for c in username if c.isalnum() or c in '_-')}"
    if not clean_id or clean_id == "u_":
        clean_id = "u_contender"

    # Ensure user exists in db
    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE id = ?", (clean_id,))
    if not cur.fetchone():
        now_iso = get_ist_now().isoformat()
        cur.execute("INSERT OR IGNORE INTO users (id, username, created_at) VALUES (?, ?, ?)", (clean_id, username, now_iso))
        conn.commit()
    conn.close()
    return clean_id


# --- API Routes ---

@router.get("/today")
def get_today_puzzle(x_username: Optional[str] = Header(None)):
    """Fetch today's POTD status and telemetry for current user."""
    user_id = get_current_user(x_username)
    puzzle = database.get_or_create_daily_puzzle()
    q_meta = database.get_question_meta(puzzle["id"], user_id)
    return {
        **puzzle,
        **(q_meta or {})
    }


@router.get("/archive")
def get_past_dailies(x_username: Optional[str] = Header(None)):
    """List past daily puzzles."""
    user_id = get_current_user(x_username)
    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT q.id, q.tier, q.input_type, q.topics, q.daily_date,
           COALESCE(up.status, 'unsolved') as user_status,
           COALESCE(up.queries_used, 0) as queries_used
    FROM questions q
    LEFT JOIN user_progress up ON q.id = up.question_id AND up.user_id = ?
    WHERE q.is_daily = 1
    ORDER BY q.daily_date DESC
    """, (user_id,))
    rows = cur.fetchall()
    res = []
    for r in rows:
        d = dict(r)
        d["topics"] = json.loads(d["topics"])
        res.append(d)
    conn.close()
    return {"archive": res}


@router.get("/library")
def get_library(
    tier: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_username: Optional[str] = Header(None)
):
    """Retrieve practice library questions with filters."""
    user_id = get_current_user(x_username)
    return database.get_library_questions(user_id, tier, topic, status, limit, offset)


@router.get("/question/{question_id}")
def get_question(question_id: str, x_username: Optional[str] = Header(None)):
    """Get metadata and query progress for a question."""
    user_id = get_current_user(x_username)
    meta = database.get_question_meta(question_id, user_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Chamber does not exist.")
    return meta


@router.post("/query")
def query_chamber(req: QueryRequest, x_username: Optional[str] = Header(None)):
    """Query black box f(x). Max 30 queries enforced."""
    user_id = get_current_user(x_username)
    try:
        res = database.query_oracle(req.question_id, user_id, req.input_value)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Evaluation fault.")


@router.post("/submit")
def submit_solution(req: SubmitRequest, x_username: Optional[str] = Header(None)):
    """Submit Python implementation to judge against 200 hidden test inputs."""
    user_id = get_current_user(x_username)
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="Code submission cannot be empty.")
    res = database.submit_code_solution(req.question_id, user_id, req.code)
    return res


@router.post("/giveup/{question_id}")
def giveup_chamber(question_id: str, x_username: Optional[str] = Header(None)):
    """Surrender puzzle to unlock rule revelation."""
    user_id = get_current_user(x_username)
    return database.give_up_question(question_id, user_id)


@router.get("/reveal/{question_id}")
def reveal_chamber_rule(question_id: str, x_username: Optional[str] = Header(None)):
    """Reveal rule formula. SECRECY: Strictly locked unless solved or given up."""
    user_id = get_current_user(x_username)
    try:
        return database.reveal_rule(question_id, user_id)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/user/profile")
def get_profile(x_username: Optional[str] = Header(None)):
    """User stats, streak, solved counts."""
    user_id = get_current_user(x_username)
    return database.get_user_profile(user_id)


@router.post("/user/switch")
def switch_user(req: SwitchUserRequest):
    """Switch active username."""
    clean_username = req.username.strip()
    clean_id = f"u_{''.join(c for c in clean_username if c.isalnum() or c in '_-')}"
    conn = database.get_db_connection()
    cur = conn.cursor()
    now_iso = get_ist_now().isoformat()
    cur.execute("INSERT OR IGNORE INTO users (id, username, created_at) VALUES (?, ?, ?)", (clean_id, clean_username, now_iso))
    conn.commit()
    conn.close()
    return {"status": "ok", "user_id": clean_id, "username": clean_username}


@router.get("/leaderboard/daily")
def get_leaderboard(date: Optional[str] = Query(None)):
    """Daily leaderboard for date (default: today)."""
    target_date = date or get_ist_now().strftime("%Y-%m-%d")
    return {
        "date": target_date,
        "leaderboard": database.get_daily_leaderboard(target_date)
    }


@router.get("/random-unsolved")
def get_random_unsolved(x_username: Optional[str] = Header(None)):
    """Return ID of random unsolved library question."""
    user_id = get_current_user(x_username)
    q_id = database.get_random_unsolved_id(user_id)
    if not q_id:
        return {"id": None, "message": "All chambers conquered!"}
    return {"id": q_id}


@router.post("/library/batch")
def add_library_batch(req: BatchRequest):
    """Generate fresh batch of library questions with new seeds."""
    added = database.generate_new_batch(req.tier, req.count)
    return {"status": "ok", "added": added, "tier": req.tier}
