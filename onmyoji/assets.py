"""Bảng tra tĩnh: shishen (式神) và server, dùng để dịch id sang tên."""

from __future__ import annotations

from typing import Mapping

from .http import ApiError, get_json

SHISHEN_PATH = "/api/asset/shishen"
SERVER_PATH = "/api/asset/server"


def fetch_shishen_map() -> Mapping[int, str]:
    """Trả về {shishen_id: tên}. Bỏ qua bản ghi thiếu id/tên."""
    rows = get_json(SHISHEN_PATH)
    if not isinstance(rows, list):
        raise ApiError(f"{SHISHEN_PATH}: 'data' phải là list")

    return {
        int(row["id"]): str(row["name"])
        for row in rows
        if isinstance(row, dict) and row.get("id") is not None and row.get("name")
    }


def fetch_server_map() -> Mapping[int, str]:
    """Trả về {server_id: tên server}."""
    rows = get_json(SERVER_PATH)
    if not isinstance(rows, list):
        raise ApiError(f"{SERVER_PATH}: 'data' phải là list")

    return {
        int(row["id"]): str(row["name"])
        for row in rows
        if isinstance(row, dict) and row.get("id") is not None and row.get("name")
    }
