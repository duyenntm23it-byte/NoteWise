from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from app.core.config import settings
from app.core.errors import ApiError


class AuthRateLimiter:
    def __init__(
        self,
        register_limit: int = settings.auth_register_rate_limit,
        login_limit: int = settings.auth_login_rate_limit,
        window_seconds: int = settings.auth_rate_limit_window_seconds,
    ) -> None:
        self._limits = {
            "register": register_limit,
            "login": login_limit,
        }
        self._window_seconds = window_seconds
        self._attempts: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def reset(self) -> None:
        with self._lock:
            self._attempts.clear()

    def check(self, operation: str, client_host: str) -> None:
        now = monotonic()
        cutoff = now - self._window_seconds
        key = (operation, client_host)
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            limit = self._limits[operation]
            if len(attempts) >= limit:
                raise ApiError(
                    429,
                    "RATE_LIMITED",
                    "Too many authentication attempts. Please try again later.",
                )
            attempts.append(now)
            if len(self._attempts) > 10_000:
                expired_keys = [
                    entry_key
                    for entry_key, timestamps in self._attempts.items()
                    if not timestamps or timestamps[-1] <= cutoff
                ]
                for entry_key in expired_keys:
                    self._attempts.pop(entry_key, None)


class DocumentRateLimiter:
    def __init__(
        self,
        upload_limit: int = settings.document_upload_rate_limit,
        window_seconds: int = settings.auth_rate_limit_window_seconds,
    ) -> None:
        self._upload_limit = upload_limit
        self._window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check_upload(self, client_host: str) -> None:
        now = monotonic()
        cutoff = now - self._window_seconds
        with self._lock:
            attempts = self._attempts[client_host]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= self._upload_limit:
                raise ApiError(
                    429,
                    "RATE_LIMITED",
                    "Too many document uploads. Please try again later.",
                )
            attempts.append(now)

    def check_ai(self, client_host: str) -> None:
        now = monotonic()
        cutoff = now - self._window_seconds
        key = f"ai:{client_host}"
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= settings.ai_request_rate_limit:
                raise ApiError(
                    429,
                    "RATE_LIMITED",
                    "Too many AI requests. Please try again later.",
                )
            attempts.append(now)
