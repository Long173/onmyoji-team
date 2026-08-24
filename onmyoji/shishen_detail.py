"""Chi tiết một Thức thần — endpoint GET /api/shishen/detail.

Endpoint mở (không cần đăng nhập), nhưng chỉ **một phần** dữ liệu được trả:

  KHÔNG CẦN LOGIN
         summary.win_rate / pick_rate / ban_rate / external_rate / duration
         summary.teams   — tối đa 100 đội hình chứa Thức thần này, KHÔNG áp ngưỡng số trận
         trend           — mỗi ngày một điểm win_rate / pick_rate / ban_rate

  CẦN HỘI VIÊN `basic`  (tài khoản free trả về array rỗng, đã kiểm chứng)
         summary.yuhuns    — mỗi bộ ngự hồn: yuhun_id, total, win_rate
         summary.positions — mỗi vị trí BP: position, total, win_rate
         summary.counters  — Thức thần đối đầu: shishen_id, total, win_rate
         summary.synergies — Thức thần đi cùng: shishen_id, total, win_rate

  CẦN `pro`
         ban_stats / ban_conditions — vẫn rỗng ở hội viên basic.

Tham số `id` (không phải `shishen_id`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .http import ApiError, get_json

SHISHEN_DETAIL_PATH = "/api/shishen/detail"

GATED_SECTIONS = ("yuhuns", "positions", "counters", "synergies")


@dataclass(frozen=True)
class ShishenDetailQuery:
    """Bộ filter cho /api/shishen/detail. Immutable."""

    start_date: str
    end_date: str
    min_level: int = 10
    max_level: int = 9999
    ban: Sequence[int] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.min_level > self.max_level:
            raise ValueError("min_level không được lớn hơn max_level")
        if len(self.ban) > 2:
            raise ValueError("ban tối đa 2 Thức thần")

    def params_for(self, shishen_id: int) -> Mapping[str, Any]:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "min_level": self.min_level,
            "max_level": self.max_level,
            "id": int(shishen_id),
            "ban": json.dumps(list(self.ban), separators=(",", ":")),
        }


@dataclass(frozen=True)
class ShishenDetail:
    """Phần dữ liệu dùng được của một Thức thần.

    Bốn mục cuối chỉ có dữ liệu khi token thuộc hội viên `basic` trở lên.
    """

    shishen_id: int
    trend: tuple[Mapping[str, Any], ...]
    teams: tuple[Mapping[str, Any], ...]
    yuhuns: tuple[Mapping[str, Any], ...] = ()
    positions: tuple[Mapping[str, Any], ...] = ()
    counters: tuple[Mapping[str, Any], ...] = ()
    synergies: tuple[Mapping[str, Any], ...] = ()

    @property
    def has_paid_data(self) -> bool:
        return bool(self.yuhuns or self.positions or self.counters or self.synergies)

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "shishen_id": self.shishen_id,
            "trend": [dict(point) for point in self.trend],
            "teams": [dict(team) for team in self.teams],
            "yuhuns": [dict(row) for row in self.yuhuns],
            "positions": [dict(row) for row in self.positions],
            "counters": [dict(row) for row in self.counters],
            "synergies": [dict(row) for row in self.synergies],
        }


def _rows(container: Mapping[str, Any], key: str, required: str) -> tuple[Mapping[str, Any], ...]:
    value = container.get(key) or []
    if not isinstance(value, list):
        return ()
    return tuple(row for row in value if isinstance(row, dict) and row.get(required) is not None)


def fetch_detail(
    query: ShishenDetailQuery,
    shishen_id: int,
    token: str | None = None,
) -> ShishenDetail:
    """Lấy chi tiết một Thức thần. Truyền `token` của hội viên basic để có thêm 4 mục trả phí."""
    payload = get_json(SHISHEN_DETAIL_PATH, query.params_for(shishen_id), token=token)
    if not isinstance(payload, dict):
        raise ApiError(f"{SHISHEN_DETAIL_PATH}: 'data' phải là object")

    inner = payload.get("data")
    if not isinstance(inner, dict):
        raise ApiError(f"{SHISHEN_DETAIL_PATH}: 'data.data' phải là object")

    summary = inner.get("summary") or {}
    trend = inner.get("trend") or []

    return ShishenDetail(
        shishen_id=int(shishen_id),
        trend=tuple(p for p in trend if isinstance(p, dict) and p.get("date")),
        teams=tuple(t for t in (summary.get("teams") or []) if isinstance(t, dict) and t.get("team")),
        yuhuns=_rows(summary, "yuhuns", "yuhun_id"),
        positions=_rows(summary, "positions", "position"),
        counters=_rows(summary, "counters", "shishen_id"),
        synergies=_rows(summary, "synergies", "shishen_id"),
    )


def gated_sections_present(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Các mục bị khoá mà lần này lại CÓ dữ liệu — dùng để phát hiện khi lên hạng."""
    summary = ((payload.get("data") or {}).get("summary")) or {}
    return tuple(key for key in GATED_SECTIONS if summary.get(key))
