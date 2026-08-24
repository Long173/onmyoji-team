"""Chi tiết một đội hình — endpoint GET /api/team/detail.

Cần đăng nhập (không cần hội viên): route `/query/team/detail` khai
`accessTier: "free"`, nhưng API trả 401 nếu thiếu token.

Phản hồi gồm:
  summary        — win_rate / pick_rate / total / duration của đội hình
  order          — thứ tự chọn (bp order) của từng 式神
  yys            — số liệu theo âm dương sư (nhân vật dẫn dắt)
  counter        — đội hình khắc chế / bị khắc chế
  ban_stats      — thống kê ban trong các trận có đội hình này
  ban_conditions — thống kê ban theo điều kiện
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .http import ApiError, get_json

TEAM_DETAIL_PATH = "/api/team/detail"

SECTION_LABELS: Mapping[str, str] = {
    "summary": "tổng quan",
    "order": "选取顺序 — thứ tự chọn",
    "yys": "阴阳师 — âm dương sư",
    "counter": "克制 — khắc chế",
    "ban_stats": "禁用统计 — thống kê ban",
    "ban_conditions": "禁用条件 — ban theo điều kiện",
}


def team_param(shishen_ids: Sequence[int]) -> str:
    """Dạng `team` mà API đòi: [{shishen_id, count}], count là lần xuất hiện thứ n."""
    seen: dict[int, int] = {}
    entries = []
    for shishen_id in shishen_ids:
        seen[shishen_id] = seen.get(shishen_id, 0) + 1
        entries.append({"shishen_id": int(shishen_id), "count": seen[shishen_id]})
    return json.dumps(entries, separators=(",", ":"))


@dataclass(frozen=True)
class TeamDetailQuery:
    """Bộ filter + đội hình cần xem chi tiết. Immutable."""

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

    def params_for(self, shishen_ids: Sequence[int]) -> Mapping[str, Any]:
        if not shishen_ids:
            raise ValueError("đội hình rỗng")
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "min_level": self.min_level,
            "max_level": self.max_level,
            "team": team_param(shishen_ids),
            "first_n": len(shishen_ids),
            "ban": json.dumps(list(self.ban), separators=(",", ":")),
        }


def fetch_detail(
    query: TeamDetailQuery,
    shishen_ids: Sequence[int],
    token: str,
) -> Mapping[str, Any]:
    """Lấy chi tiết một đội hình. Ném AuthRequiredError nếu token không đủ quyền."""
    payload = get_json(TEAM_DETAIL_PATH, query.params_for(shishen_ids), token=token)
    if not isinstance(payload, dict):
        raise ApiError(f"{TEAM_DETAIL_PATH}: 'data' phải là object")
    return payload


def section_sizes(detail: Mapping[str, Any]) -> Mapping[str, int]:
    """Số phần tử của từng mục — dùng để biết mục nào có dữ liệu thật."""
    sizes: dict[str, int] = {}
    for key in SECTION_LABELS:
        value = detail.get(key)
        if isinstance(value, list):
            sizes[key] = len(value)
        elif isinstance(value, dict):
            sizes[key] = len(value)
        else:
            sizes[key] = 0
    return sizes
