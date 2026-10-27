import hashlib
import hmac
import secrets
import time
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from .models import AuthSession


def digest(value: str):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password: str):
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
    return f"pbkdf2_sha256$600000${salt}${key}"


def verify_password(password: str, stored: str):
    _, rounds, salt, expected = stored.split("$")
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
    return hmac.compare_digest(actual, expected)


def new_session(db, user_id, hours):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=digest(token), user_id=user_id, csrf=csrf,
                       expires_at=(datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()))
    db.commit()
    return token, csrf


class RateLimiter:
    """Single-process sliding window; replace with shared storage for multi-instance deployment."""
    def __init__(self):
        self.events = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key, limit=120, seconds=60):
        with self.lock:
            self._check(key, limit, seconds)

    def _check(self, key, limit, seconds):
        current = time.monotonic()
        events = self.events[key]
        while events and events[0] <= current - seconds:
            events.popleft()
        if len(events) >= limit:
            raise HTTPException(429, detail={"code": "RATE_LIMITED", "message": "Too many requests; try again later"},
                                headers={"Retry-After": str(seconds)})
        events.append(current)
        if len(self.events) > 10000:
            for old in list(self.events):
                if not self.events[old] or self.events[old][-1] < current - 3600:
                    self.events.pop(old, None)
