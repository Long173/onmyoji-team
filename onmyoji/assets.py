"""Bảng tra tĩnh: shishen (Thức thần) và server, dùng để dịch id sang tên."""

from __future__ import annotations

from typing import Mapping

from .http import ApiError, get_json

SHISHEN_PATH = "/api/asset/shishen"
SERVER_PATH = "/api/asset/server"
YUHUN_PATH = "/api/asset/yuhun"
SHISHEN_STATS_PATH = "/api/asset/shishen_stats"


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


def fetch_yuhun_map() -> Mapping[int, Mapping[str, str]]:
    """Trả về {yuhun_id: {name, icon, suit_type}} cho 御魂 (ngự hồn).

    `icon` có thể là đường dẫn tương đối trên yysrank.win, URL tuyệt đối trên
    CDN của NetEase, hoặc rỗng (các bộ 2 món không có ảnh riêng).
    """
    rows = get_json(YUHUN_PATH)
    if not isinstance(rows, list):
        raise ApiError(f"{YUHUN_PATH}: 'data' phải là list")

    return {
        int(row["id"]): {
            "name": str(row.get("name") or ""),
            "icon": str(row.get("icon") or ""),
            "suit_type": str(row.get("suit_type") or ""),
        }
        for row in rows
        if isinstance(row, dict) and row.get("id") is not None and row.get("name")
    }


def fetch_shishen_stats() -> Mapping[int, Mapping[str, float]]:
    """Trả về {shishen_id: {Attack, Defense, Hp, Speed, CritRate, ...}}."""
    rows = get_json(SHISHEN_STATS_PATH)
    if not isinstance(rows, list):
        raise ApiError(f"{SHISHEN_STATS_PATH}: 'data' phải là list")

    return {
        int(row["id"]): {str(k): float(v) for k, v in (row.get("stats") or {}).items()}
        for row in rows
        if isinstance(row, dict) and row.get("id") is not None and row.get("stats")
    }
