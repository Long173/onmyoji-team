"""Đọc access token của yysrank.win để gọi các endpoint cần đăng nhập.

Token KHÔNG bao giờ được ghi vào log, in ra stdout, hay commit. Nguồn đọc, theo
thứ tự ưu tiên:

1. biến môi trường `ONMYOJI_TOKEN`
2. file `.token` ở gốc repo (đã nằm trong .gitignore)

Cách lấy token: đăng nhập yysrank.win, mở DevTools → Console, chạy
`JSON.parse(localStorage.getItem('user-info')).accessToken`
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

TOKEN_ENV_VAR = "ONMYOJI_TOKEN"
TOKEN_FILE = Path(".token")
MIN_TOKEN_LENGTH = 20


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
