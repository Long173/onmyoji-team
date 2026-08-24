"""Tầng HTTP tối thiểu: GET JSON + retry + validate envelope trả về.

Chỉ dùng stdlib để crawler chạy được mà không cần cài thêm gì.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping

from . import BASE_URL

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE_URL}/",
    "User-Agent": USER_AGENT,
}

DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2.0


class ApiError(RuntimeError):
    """Server trả về lỗi, hoặc payload không đúng dạng mong đợi."""


def _build_url(path: str, params: Mapping[str, Any] | None) -> str:
    if not path.startswith("/"):
        raise ValueError(f"path phải bắt đầu bằng '/': {path!r}")
    query = ""
    if params:
        cleaned = {k: v for k, v in params.items() if v is not None}
        query = "?" + urllib.parse.urlencode(cleaned, doseq=False)
    return f"{BASE_URL}{path}{query}"


def get_json(
    path: str,
    params: Mapping[str, Any] | None = None,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> Any:
    """GET một endpoint và trả về phần `data` của envelope.

    Envelope của site: {"success": bool, "data": ..., "error": str}.
    """
    url = _build_url(path, params)
    last_error: Exception | None = None

    for attempt in range(1, max(1, retries) + 1):
        request = urllib.request.Request(url, headers=DEFAULT_HEADERS, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
        else:
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ApiError(f"{path}: phản hồi không phải JSON hợp lệ") from exc

            if not isinstance(payload, dict):
                raise ApiError(f"{path}: envelope không phải object JSON")
            if not payload.get("success"):
                raise ApiError(f"{path}: server báo lỗi — {payload.get('error')!r}")
            if "data" not in payload:
                raise ApiError(f"{path}: envelope thiếu field 'data'")
            return payload["data"]

        if attempt < retries:
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise ApiError(f"{path}: thất bại sau {retries} lần thử — {last_error}") from last_error
