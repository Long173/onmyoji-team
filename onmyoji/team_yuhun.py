"""Ngự hồn theo đội hình — endpoint GET /api/team/yuhun (cần hội viên `basic`).

Endpoint trả về tối đa 50 **tổ hợp ngự hồn hoàn chỉnh** cho cả đội (mỗi Thức thần một
bộ), kèm `win_rate` và `total`. Vì là tổ hợp 5 chiều nên cực kỳ phân mảnh:
median 3 trận/tổ hợp, và 50 tổ hợp đó chỉ phủ khoảng 4-5% số trận của đội.

Do đó KHÔNG dùng từng tổ hợp làm số liệu. Cách dùng được là **gộp theo cặp
(Thức thần, ngự hồn)**: cộng dồn `total` và tính tỉ lệ thắng gia quyền. Khi gộp, các
lựa chọn phổ biến đạt 100-230 trận — đủ để nói "trong đội này con X hay mang bộ Y".

Hai giới hạn phải nêu kèm khi trình bày:
  1. Chỉ phủ ~4-5% số trận của đội (API cắt ở top 50 tổ hợp).
  2. Mẫu bị lệch: đây là các tổ hợp PHỔ BIẾN, nên một bộ hay dùng trong nhiều
     tổ hợp hiếm sẽ bị đếm thiếu. Tần suất là chỉ dấu, không phải con số tuyệt đối.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .http import ApiError, get_json
from .team_detail import team_param

TEAM_YUHUN_PATH = "/api/team/yuhun"

# Ngưỡng khi gộp. Dưới 30 trận thì tỉ lệ thắng dao động vô nghĩa; tỉ lệ thắng
# chỉ được hiển thị từ 50 trận trở lên.
MIN_USAGE_MATCHES = 30
MIN_WIN_RATE_MATCHES = 50
TOP_OPTIONS_PER_SHISHEN = 4


@dataclass(frozen=True)
class TeamYuhunQuery:
    """Bộ filter cho /api/team/yuhun. Immutable."""

    start_date: str
    end_date: str
    min_level: int = 10
    max_level: int = 9999
    all_suits: bool = False

    def params_for(self, shishen_ids: Sequence[int]) -> Mapping[str, Any]:
        if not shishen_ids:
            raise ValueError("đội hình rỗng")
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "min_level": self.min_level,
            "max_level": self.max_level,
            "team1": team_param(shishen_ids),
            # team2 rỗng = không giới hạn đối thủ. Có team2 cụ thể thì gần như
            # luôn trả 0 dòng vì cặp đối đầu + tổ hợp ngự hồn quá phân mảnh.
            "team2": "[]",
            "all_suits": "true" if self.all_suits else "false",
        }


@dataclass(frozen=True)
class YuhunOption:
    """Một lựa chọn ngự hồn của một Thức thần trong đội, sau khi gộp."""

    shishen_id: int
    yuhun_id: int
    total: int
    win_rate: float
    share: float

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "shishen_id": self.shishen_id,
            "yuhun_id": self.yuhun_id,
            "total": self.total,
            "share": self.share,
            # None = mẫu chưa đủ để nói về tỉ lệ thắng.
            "win_rate": self.win_rate if self.total >= MIN_WIN_RATE_MATCHES else None,
        }


@dataclass(frozen=True)
class TeamYuhun:
    """Kết quả gộp cho một đội hình."""

    team_ids: tuple[int, ...]
    combos: int
    covered_matches: int
    options: tuple[YuhunOption, ...] = field(default_factory=tuple)

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "team_ids": list(self.team_ids),
            "combos": self.combos,
            "covered_matches": self.covered_matches,
            "options": [dict(o.as_dict()) for o in self.options],
        }


def fetch_team_yuhun(
    query: TeamYuhunQuery,
    shishen_ids: Sequence[int],
    token: str,
) -> TeamYuhun:
    """Lấy rồi gộp ngay — dữ liệu thô từng tổ hợp không dùng được nên không giữ."""
    rows = get_json(TEAM_YUHUN_PATH, query.params_for(shishen_ids), token=token)
    if not isinstance(rows, list):
        raise ApiError(f"{TEAM_YUHUN_PATH}: 'data' phải là list")

    buckets: dict[tuple[int, int], dict[str, float]] = defaultdict(
        lambda: {"total": 0.0, "weighted": 0.0}
    )
    covered = 0

    for row in rows:
        if not isinstance(row, dict):
            continue
        total = int(row.get("total") or 0)
        win_rate = float(row.get("win_rate") or 0.0)
        covered += total
        for slot in row.get("team1") or ():
            if not isinstance(slot, dict):
                continue
            key = (int(slot.get("shishen_id") or 0), int(slot.get("yuhun_id") or 0))
            if key[0] == 0:
                continue
            buckets[key]["total"] += total
            buckets[key]["weighted"] += win_rate * total

    per_shishen: dict[int, list[YuhunOption]] = defaultdict(list)
    for (shishen_id, yuhun_id), bucket in buckets.items():
        total = int(bucket["total"])
        if total < MIN_USAGE_MATCHES:
            continue
        per_shishen[shishen_id].append(
            YuhunOption(
                shishen_id=shishen_id,
                yuhun_id=yuhun_id,
                total=total,
                win_rate=bucket["weighted"] / total if total else 0.0,
                share=total / covered if covered else 0.0,
            )
        )

    options: list[YuhunOption] = []
    for shishen_id in shishen_ids:
        picked = sorted(per_shishen.get(int(shishen_id), ()), key=lambda o: -o.total)
        options.extend(picked[:TOP_OPTIONS_PER_SHISHEN])

    return TeamYuhun(
        team_ids=tuple(int(i) for i in shishen_ids),
        combos=len(rows),
        covered_matches=covered,
        options=tuple(options),
    )
