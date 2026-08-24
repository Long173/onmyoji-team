"""Đọc access token của yysrank.win để gọi các endpoint cần đăng nhập.

Token KHÔNG bao giờ được ghi vào log, in ra stdout, hay commit. Nguồn đọc, theo
thứ tự ưu tiên:

1. biến môi trường `ONMYOJI_TOKEN`
2. file `.token` ở gốc repo (đã nằm trong .gitignore)

Cách lấy token: đăng nhập yysrank.win, mở DevTools → Console, chạy
`JSON.parse(localStorage.getItem('user-info')).accessToken`
"""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Mapping

TOKEN_ENV_VAR = "ONMYOJI_TOKEN"
REFRESH_ENV_VAR = "ONMYOJI_REFRESH_TOKEN"
TOKEN_FILE = Path(".token")
REFRESH_FILE = Path(".refresh-token")
MIN_TOKEN_LENGTH = 20
REFRESH_PATH = "/api/auth/refresh-token"


class AuthError(RuntimeError):
    """Không có token, hoặc token không đúng dạng."""


def load_token(token_file: Path = TOKEN_FILE) -> str:
    """Trả về access token. Ném AuthError kèm hướng dẫn nếu không tìm thấy."""
    from_env = (os.environ.get(TOKEN_ENV_VAR) or "").strip()
    if from_env:
        return _validated(from_env)

    if token_file.is_file():
        return _validated(token_file.read_text(encoding="utf-8").strip())

    raise AuthError(
        f"Không tìm thấy token. Đặt biến môi trường {TOKEN_ENV_VAR}, "
        f"hoặc lưu token vào file {token_file}.\n"
        "Lấy token: đăng nhập yysrank.win → DevTools → Console → "
        "JSON.parse(localStorage.getItem('user-info')).accessToken"
    )


def _validated(token: str) -> str:
    if len(token) < MIN_TOKEN_LENGTH:
        raise AuthError(f"token quá ngắn ({len(token)} ký tự) — chắc bị copy thiếu")
    if any(char.isspace() for char in token):
        raise AuthError("token chứa khoảng trắng — kiểm tra lại nội dung copy")
    return token


def auth_headers(token: str) -> Mapping[str, str]:
    """Header xác thực mà site dùng: `Authorization: Bearer <token>`."""
    return {"Authorization": f"Bearer {token}"}


def has_token(token_file: Path = TOKEN_FILE) -> bool:
    """Có token khả dụng hay không — không ném lỗi, không đọc nội dung."""
    return bool((os.environ.get(TOKEN_ENV_VAR) or "").strip()) or token_file.is_file()


def load_refresh_token(refresh_file: Path = REFRESH_FILE) -> str:
    """Refresh token — sống lâu hơn access token, dùng để lấy access token mới.

    Nguồn: biến môi trường `ONMYOJI_REFRESH_TOKEN`, hoặc file `.refresh-token`.
    Lấy: DevTools → Console → JSON.parse(localStorage.getItem('user-info')).refreshToken
    """
    from_env = (os.environ.get(REFRESH_ENV_VAR) or "").strip()
    if from_env:
        return _validated(from_env)
    if refresh_file.is_file():
        return _validated(refresh_file.read_text(encoding="utf-8").strip())
    raise AuthError(
        f"Không tìm thấy refresh token. Đặt {REFRESH_ENV_VAR} hoặc lưu vào {refresh_file}.\n"
        "Lấy: DevTools → Console → "
        "JSON.parse(localStorage.getItem('user-info')).refreshToken"
    )


def refresh_access_token(refresh_token: str) -> str:
    """Đổi refresh token thành access token mới."""
    from .http import post_json

    data = post_json(REFRESH_PATH, {"refreshToken": refresh_token})
    if not isinstance(data, dict) or not data.get("accessToken"):
        raise AuthError(f"{REFRESH_PATH}: phản hồi không có accessToken")
    return _validated(str(data["accessToken"]))


def token_expiry(token: str) -> int | None:
    """Giây epoch ở claim `exp` của JWT, hoặc None nếu không đọc được."""
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        claims = json.loads(base64.urlsafe_b64decode(part))
    except (IndexError, ValueError, json.JSONDecodeError):
        return None
    exp = claims.get("exp")
    return int(exp) if isinstance(exp, (int, float)) else None


def token_is_fresh(token: str, *, margin_seconds: int = 120) -> bool:
    """Access token còn hạn hay không. Không đọc được `exp` thì coi là còn."""
    exp = token_expiry(token)
    return True if exp is None else exp - margin_seconds > time.time()


def resolve_token(token_file: Path = TOKEN_FILE, refresh_file: Path = REFRESH_FILE) -> str:
    """Access token dùng được, **ưu tiên cái đang có**.

    QUAN TRỌNG: refresh token của yysrank.win là **dùng một lần** — mỗi lần gọi
    /api/auth/refresh-token nó rotate và vô hiệu hoá session cũ, kể cả session
    đang mở trên browser. Vì vậy chỉ refresh khi access token đã hết hạn thật,
    và ghi lại cặp token mới ngay.
    """
    if has_token(token_file):
        token = load_token(token_file)
        if token_is_fresh(token):
            return token

    refresh_token = load_refresh_token(refresh_file)
    data = _refresh_pair(refresh_token)
    _persist_pair(data, token_file, refresh_file)
    return _validated(str(data["accessToken"]))


def _refresh_pair(refresh_token: str) -> Mapping[str, object]:
    from .http import post_json

    data = post_json(REFRESH_PATH, {"refreshToken": refresh_token})
    if not isinstance(data, dict) or not data.get("accessToken"):
        raise AuthError(f"{REFRESH_PATH}: phản hồi không có accessToken")
    return data


def _persist_pair(data: Mapping[str, object], token_file: Path, refresh_file: Path) -> None:
    """Lưu cặp token mới. Bỏ qua khi token đến từ biến môi trường (CI read-only)."""
    access = str(data.get("accessToken") or "")
    rotated = str(data.get("refreshToken") or "")
    try:
        if access and not (os.environ.get(TOKEN_ENV_VAR) or "").strip():
            token_file.write_text(access, encoding="utf-8")
            token_file.chmod(0o600)
        if rotated and not (os.environ.get(REFRESH_ENV_VAR) or "").strip():
            refresh_file.write_text(rotated, encoding="utf-8")
            refresh_file.chmod(0o600)
    except OSError:
        pass  # không ghi được thì vẫn dùng được token trong phiên này


def has_any_credential(token_file: Path = TOKEN_FILE, refresh_file: Path = REFRESH_FILE) -> bool:
    if (os.environ.get(REFRESH_ENV_VAR) or "").strip() or refresh_file.is_file():
        return True
    return has_token(token_file)
