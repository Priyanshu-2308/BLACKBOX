import os
import secrets
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
DB_PATH = BASE_DIR / "arena.db"

# IST Timezone (UTC + 5:30)
IST = timezone(timedelta(hours=5, minutes=30))


def init_server_secret() -> str:
    """
    Generate or load the random SERVER_SECRET from .env file.
    SECRECY: The secret is stored locally and gitignored.
    All seeds are derived via HMAC(SERVER_SECRET, label).
    """
    secret = None
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("SERVER_SECRET="):
                    secret = line.split("=", 1)[1].strip()
                    break

    if not secret:
        # Generate 256-bit cryptographically secure random secret
        secret = secrets.token_hex(32)
        with open(ENV_PATH, "a+", encoding="utf-8") as f:
            f.write(f"\nSERVER_SECRET={secret}\n")

    return secret


SERVER_SECRET = init_server_secret()


def derive_seed(label: str) -> int:
    """
    Derive an integer pseudo-random seed using HMAC-SHA256 with SERVER_SECRET.
    Guarantees:
    - Determinism for identical label + secret.
    - Zero predictability from date or id without knowing SERVER_SECRET.
    """
    mac = hmac.new(SERVER_SECRET.encode("utf-8"), label.encode("utf-8"), hashlib.sha256)
    digest = mac.digest()
    # Convert first 4 bytes of digest to 32-bit unsigned integer (fits SQLite INTEGER)
    return int.from_bytes(digest[:4], byteorder="big")


def get_ist_now() -> datetime:
    """Get current time in Asia/Kolkata (IST)."""
    return datetime.now(IST)


def get_daily_info(target_date: str | None = None):
    """
    Compute daily puzzle metadata for a given date in Asia/Kolkata (default: today).
    Returns (date_str, tier, seconds_until_midnight, seed).
    Pattern:
    - Mon (0), Tue (1): Easy
    - Wed (2), Thu (3), Fri (4): Medium
    - Sat (5), Sun (6): Hard
    """
    now = get_ist_now()
    if target_date:
        dt = datetime.strptime(target_date, "%Y-%m-%d").replace(tzinfo=IST)
        date_str = target_date
    else:
        dt = now
        date_str = dt.strftime("%Y-%m-%d")

    weekday = dt.weekday()
    if weekday in (0, 1):
        tier = "easy"
    elif weekday in (2, 3, 4):
        tier = "medium"
    else:
        tier = "hard"

    # Seconds until midnight IST of today
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_remaining = int((tomorrow - now).total_seconds())
    if seconds_remaining < 0:
        seconds_remaining = 0

    seed = derive_seed(f"daily_{date_str}")
    return date_str, tier, seconds_remaining, seed
