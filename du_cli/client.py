"""Single httpx wrapper: auth headers, error hints, timeout."""
from __future__ import annotations
import contextlib
import httpx

TIMEOUT = 300.0
MAX_UPLOAD_BYTES = 30 * 1024 * 1024

class CliError(Exception):
    def __init__(self, status: int, detail: str, hint: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.hint = hint

def make_client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT)

@contextlib.contextmanager
def api_client():
    """Yield an httpx client; transport failures become CliError (no tracebacks)."""
    try:
        with make_client() as c:
            yield c
    except httpx.RequestError as e:
        raise CliError(
            502,
            f"cannot reach server: {e}",
            "check base URL and try `du health --detailed`",
        ) from e

def auth_headers(api_key: str, idempotency_key: str | None = None) -> dict[str, str]:
    h = {"X-API-Key": api_key}
    if idempotency_key:
        h["Idempotency-Key"] = idempotency_key
    return h

def error_hint(status: int, detail: str, path: str = "") -> str:
    d = (detail or "").lower()
    if status == 401:
        return "invalid key — run `du configure`, copy from dashboard API Keys"
    if status == 402 or "insufficient_balance" in d:
        return "insufficient balance — top-up via dashboard Wallet"
    if status == 403:
        return "organization pending review — contact org admin"
    if status == 413:
        return "file exceeds 30 MB limit — compress or split audio"
    if status == 503:
        return "server busy (saturated) — retry after Retry-After seconds"
    if status == 502:
        return "backend unreachable — try `du health --detailed`"
    if status == 404 and path == "/diarize":
        return "gateway /diarize not deployed yet (spec 2026-09-28), backend is standalone"
    if status == 404:
        return "not found — check base URL and gateway version"
    return detail or f"HTTP {status}"

def raise_for_api(status: int, body: str, path: str = "") -> None:
    if 200 <= status < 300:
        return
    detail = body[:500] if body else f"HTTP {status}"
    # try to keep gateway JSON detail readable
    raise CliError(status, detail, error_hint(status, detail, path))
