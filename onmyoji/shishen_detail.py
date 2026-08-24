"""Chi tiết một 式神 — endpoint GET /api/shishen/detail.

Endpoint mở (không cần đăng nhập), nhưng chỉ **một phần** dữ liệu được trả:

  ĐƯỢC   summary.win_rate / pick_rate / ban_rate / external_rate / duration
         summary.teams   — tối đa 100 đội hình chứa 式神 này, KHÔNG áp ngưỡng số trận
         trend           — mỗi ngày một điểm win_rate / pick_rate / ban_rate
  RỖNG   summary.yuhuns / positions / counters / synergies, ban_stats,
         ban_conditions — site khoá sau hội viên `basic`; đã kiểm tra bằng token
         free và kết quả giống hệt lúc không token.

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
            raise ValueError("ban tối đa 2 式神")

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
    """Phần dữ liệu dùng được của một 式神."""

    shishen_id: int
    trend: tuple[Mapping[str, Any], ...]
    teams: tuple[Mapping[str, Any], ...]

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "shishen_id": self.shishen_id,
            "trend": [dict(point) for point in self.trend],
            "teams": [dict(team) for team in self.teams],
        }


def fetch_detail(query: ShishenDetailQuery, shishen_id: int) -> ShishenDetail:
    payload = get_json(SHISHEN_DETAIL_PATH, query.params_for(shishen_id))
    if not isinstance(payload, dict):
        raise ApiError(f"{SHISHEN_DETAIL_PATH}: 'data' phải là object")

    inner = payload.get("data")
    if not isinstance(inner, dict):
        raise ApiError(f"{SHISHEN_DETAIL_PATH}: 'data.data' phải là object")

    summary = inner.get("summary") or {}
    trend = inner.get("trend") or []
    teams = summary.get("teams") or []

    return ShishenDetail(
        shishen_id=int(shishen_id),
        trend=tuple(p for p in trend if isinstance(p, dict) and p.get("date")),
        teams=tuple(t for t in teams if isinstance(t, dict) and t.get("team")),
    )


def gated_sections_present(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Các mục bị khoá mà lần này lại CÓ dữ liệu — dùng để phát hiện khi lên hạng."""
    summary = ((payload.get("data") or {}).get("summary")) or {}
    return tuple(key for key in GATED_SECTIONS if summary.get(key))
