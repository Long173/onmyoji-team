"""Crawl bảng xếp hạng阵容 (team rank) — endpoint GET /api/team/rank.

Tham số được suy ra từ bundle của trang https://yysrank.win/#/query/team:
filter component sinh start_date/end_date/min_level/max_level/include/
exclude/ban/thres/first_n, còn bảng sinh page/page_size/order/desc.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any, Iterator, Mapping, Sequence

from .http import ApiError, get_json

TEAM_RANK_PATH = "/api/team/rank"

ORDER_FIELDS = ("win_rate", "total", "duration")
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class TeamRankQuery:
    """Bộ filter cho một lần crawl. Immutable — đổi giá trị bằng `replace()`."""

    start_date: str
    end_date: str
    min_level: int = 10
    max_level: int = 9999
    thres: int = 100
    first_n: int = 5
    order: str = "win_rate"
    desc: bool = True
    page_size: int = 50
    include: Sequence[int] = field(default_factory=tuple)
    exclude: Sequence[int] = field(default_factory=tuple)
    ban: Sequence[int] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.order not in ORDER_FIELDS:
            raise ValueError(f"order phải thuộc {ORDER_FIELDS}, nhận {self.order!r}")
        if not 1 <= self.page_size <= MAX_PAGE_SIZE:
            raise ValueError(f"page_size phải trong [1, {MAX_PAGE_SIZE}]")
        if self.min_level > self.max_level:
            raise ValueError("min_level không được lớn hơn max_level")
        if self.thres < 0:
            raise ValueError("thres không được âm")
        if len(self.ban) > 2:
            raise ValueError("ban tối đa 2 Thức thần (giới hạn của site)")

    def params_for_page(self, page: int) -> Mapping[str, Any]:
        if page < 1:
            raise ValueError("page bắt đầu từ 1")
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "min_level": self.min_level,
            "max_level": self.max_level,
            "include": json.dumps(list(self.include), separators=(",", ":")),
            "exclude": json.dumps(list(self.exclude), separators=(",", ":")),
            "ban": json.dumps(list(self.ban), separators=(",", ":")),
            "thres": self.thres,
            "first_n": self.first_n,
            "page": page,
            "page_size": self.page_size,
            "order": self.order,
            "desc": 1 if self.desc else 0,
        }


@dataclass(frozen=True)
class TeamRankPage:
    """Một trang kết quả."""

    page: int
    total: int
    last_update: str
    rows: tuple[Mapping[str, Any], ...]


def fetch_page(query: TeamRankQuery, page: int) -> TeamRankPage:
    payload = get_json(TEAM_RANK_PATH, query.params_for_page(page))
    if not isinstance(payload, dict):
        raise ApiError(f"{TEAM_RANK_PATH}: 'data' phải là object")

    rows = payload.get("data") or []
    if not isinstance(rows, list):
        raise ApiError(f"{TEAM_RANK_PATH}: 'data.data' phải là list")

    return TeamRankPage(
        page=page,
        total=int(payload.get("total") or 0),
        last_update=str(payload.get("last_update") or ""),
        rows=tuple(row for row in rows if isinstance(row, dict)),
    )


def iter_pages(query: TeamRankQuery, *, max_pages: int | None = None) -> Iterator[TeamRankPage]:
    """Lặp qua từng trang tới khi hết dữ liệu (hoặc đủ `max_pages`)."""
    page = 1
    while max_pages is None or page <= max_pages:
        current = fetch_page(query, page)
        if not current.rows:
            return
        yield current
        if page * query.page_size >= current.total:
            return
        page += 1


def with_order(query: TeamRankQuery, order: str, *, desc: bool = True) -> TeamRankQuery:
    """Bản copy của query với sắp xếp khác — không sửa query gốc."""
    return replace(query, order=order, desc=desc)
