"""Bảng xếp hạng Thức thần — endpoint GET /api/shishen/rank.

Endpoint này **không phân trang**: nó trả về toàn bộ Thức thần đạt ngưỡng dữ liệu
trong một lần gọi. Field `total` là *số trận* được phân tích, không phải số dòng.
Nhãn cột lấy đúng theo UI của site (xem NHÃN bên dưới).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .http import ApiError, get_json

SHISHEN_RANK_PATH = "/api/shishen/rank"

# Nhãn gốc trên site, giữ lại để đối chiếu khi API đổi.
FIELD_LABELS: Mapping[str, str] = {
    "tier_score": "Tier",
    "win_rate": "外战胜率 — tỉ lệ thắng ngoại chiến",
    "pick_rate": "选用率 — tỉ lệ chọn",
    "ban_rate": "禁用率 — tỉ lệ bị ban",
    "external_rate": "外战比例 — tỉ lệ ngoại chiến",
    "duration": "平均时长 — thời lượng trung bình (giây)",
    "avg_position": "选取次序 — thứ tự chọn trung bình",
    "most_used_yuhuns": "常用御魂 — ngự hồn thường dùng",
    "counter": "克制 — khắc chế",
    "countered_by": "受制于 — bị khắc chế bởi",
}

# tier 0 là tốt nhất; màu lấy theo UI của site (blue / green / yellow / gray).
TIER_LABELS: Mapping[int, str] = {0: "T0", 1: "T1", 2: "T2", 3: "T3"}

SUIT_TYPE_LABELS: Mapping[str, str] = {
    "": "không có hiệu ứng bộ",
    "AttackRate": "Tấn công",
    "DefenseRate": "Phòng ngự",
    "HpRate": "Sinh mệnh",
    "CritRate": "Bạo kích",
    "CritPower": "Bạo sát",
    "EffectHitRate": "Hiệu quả mệnh trúng",
    "EffectResistRate": "Hiệu quả kháng",
}

STAT_LABELS: Mapping[str, str] = {
    "Attack": "Công",
    "Defense": "Phòng",
    "Hp": "HP",
    "Speed": "Tốc",
    "CritRate": "Bạo kích",
    "CritPower": "Bạo sát",
    "EffectHitRate": "Mệnh trúng",
    "EffectResistRate": "Kháng",
}


@dataclass(frozen=True)
class ShishenRankQuery:
    """Bộ filter cho /api/shishen/rank. Immutable."""

    start_date: str
    end_date: str
    min_level: int = 10
    max_level: int = 9999
    tag: str = ""
    ban: Sequence[int] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.min_level > self.max_level:
            raise ValueError("min_level không được lớn hơn max_level")
        if len(self.ban) > 2:
            raise ValueError("ban tối đa 2 Thức thần (giới hạn của site)")

    def as_params(self) -> Mapping[str, Any]:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "min_level": self.min_level,
            "max_level": self.max_level,
            "tag": self.tag,
            "ban": json.dumps(list(self.ban), separators=(",", ":")),
        }


@dataclass(frozen=True)
class ShishenRank:
    """Toàn bộ bảng xếp hạng trong một lần gọi."""

    last_update: str
    matches_analysed: int
    rows: tuple[Mapping[str, Any], ...]


def fetch_rank(query: ShishenRankQuery) -> ShishenRank:
    payload = get_json(SHISHEN_RANK_PATH, query.as_params())
    if not isinstance(payload, dict):
        raise ApiError(f"{SHISHEN_RANK_PATH}: 'data' phải là object")

    rows = payload.get("data") or []
    if not isinstance(rows, list):
        raise ApiError(f"{SHISHEN_RANK_PATH}: 'data.data' phải là list")

    return ShishenRank(
        last_update=str(payload.get("last_update") or ""),
        matches_analysed=int(payload.get("total") or 0),
        rows=tuple(row for row in rows if isinstance(row, dict)),
    )


def referenced_yuhun_ids(rows: Sequence[Mapping[str, Any]]) -> tuple[int, ...]:
    """Các yuhun_id được nhắc tới trong `most_used_yuhuns`, đã sắp xếp."""
    found: set[int] = set()
    for row in rows:
        for yuhun_id in row.get("most_used_yuhuns") or ():
            found.add(int(yuhun_id))
    return tuple(sorted(found))


def referenced_shishen_ids(rows: Sequence[Mapping[str, Any]]) -> tuple[int, ...]:
    """Các shishen_id cần avatar: chính nó + counter + countered_by."""
    found: set[int] = set()
    for row in rows:
        if row.get("shishen_id") is not None:
            found.add(int(row["shishen_id"]))
        for key in ("counter", "countered_by"):
            for shishen_id in row.get(key) or ():
                found.add(int(shishen_id))
    return tuple(sorted(found))
