"""Ba endpoint mở còn lại: thống kê site, độ nóng thô, và BXH người chơi.

Cả ba đều KHÔNG cần đăng nhập, nên CI crawl được — khác với dữ liệu hội viên.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .http import ApiError, get_json

STATISTIC_PATH = "/api/statistic"
HEAT_PATH = "/api/asset/heat"
PLAYER_TOP_PATH = "/api/user-report/rank-top-100"


@dataclass(frozen=True)
class SiteStatistic:
    """Số liệu toàn site. `score_brackets` là phân bố người chơi theo đoạn điểm."""

    total_matches: int
    last_days: tuple[int, ...]
    score_brackets: tuple[Mapping[str, Any], ...]
    most_picked: Mapping[str, Any]
    highest_win_rate: Mapping[str, Any]

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "total_matches": self.total_matches,
            "last_days": list(self.last_days),
            "score_brackets": [dict(b) for b in self.score_brackets],
            "most_picked": dict(self.most_picked),
            "highest_win_rate": dict(self.highest_win_rate),
        }


# Nhãn đoạn điểm do site trả về là tiếng Trung; dịch sang tiếng Việt.
BRACKET_LABELS: Mapping[str, str] = {
    "名仕以下(小于3000分)": "Dưới Danh sĩ (<3000)",
    "0-30星(3000-3900分)": "0–30★ (3000–3900)",
    "30-60星(3900-4800分)": "30–60★ (3900–4800)",
    "60-100星(4800-6000分)": "60–100★ (4800–6000)",
    "100星及以上(大于等于6000分)": "Từ 100★ (≥6000)",
}


def fetch_site_statistic() -> SiteStatistic:
    data = get_json(STATISTIC_PATH)
    if not isinstance(data, dict):
        raise ApiError(f"{STATISTIC_PATH}: 'data' phải là object")

    brackets = tuple(
        {
            "cn": str(b.get("name") or ""),
            "vn": BRACKET_LABELS.get(str(b.get("name") or ""), str(b.get("name") or "")),
            "value": int(b.get("value") or 0),
        }
        for b in (data.get("scoreRatio") or ())
        if isinstance(b, dict)
    )
    return SiteStatistic(
        total_matches=int(data.get("total") or 0),
        last_days=tuple(int(x) for x in (data.get("yesterday") or ())),
        score_brackets=brackets,
        most_picked=dict(data.get("mostPickedShishen") or {}),
        highest_win_rate=dict(data.get("highestWinRateShishen") or {}),
    )


def fetch_heat() -> Mapping[int, Mapping[str, int]]:
    """{shishen_id: {picks, bans}} — số tuyệt đối, không phải tỉ lệ."""
    rows = get_json(HEAT_PATH)
    if not isinstance(rows, list):
        raise ApiError(f"{HEAT_PATH}: 'data' phải là list")
    return {
        int(row["id"]): {"picks": int(row.get("picks") or 0), "bans": int(row.get("bans") or 0)}
        for row in rows
        if isinstance(row, dict) and row.get("id") is not None
    }


@dataclass(frozen=True)
class PlayerBoard:
    """BXH 100 người chơi trong tuần. Endpoint này mở, site tự công khai."""

    start_time: str
    end_time: str
    rows: tuple[Mapping[str, Any], ...]

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "rows": [dict(r) for r in self.rows],
        }


def fetch_player_top100() -> PlayerBoard:
    data = get_json(PLAYER_TOP_PATH)
    if not isinstance(data, dict):
        raise ApiError(f"{PLAYER_TOP_PATH}: 'data' phải là object")

    rows = tuple(
        {
            "name": str(r.get("account_name") or ""),
            "score": float(r.get("score") or 0.0),
            "settlement_score": int(r.get("settlement_score") or 0),
            "win_rate": float(r.get("win_rate") or 0.0),
            "total": int(r.get("total") or 0),
            "common_shishens": [int(s) for s in (r.get("common_shishens") or ())],
            "verified": bool(r.get("is_verified")),
        }
        for r in (data.get("data") or ())
        if isinstance(r, dict)
    )
    return PlayerBoard(
        start_time=str(data.get("start_time") or "")[:10],
        end_time=str(data.get("end_time") or "")[:10],
        rows=rows,
    )


def player_shishen_ids(board: PlayerBoard) -> tuple[int, ...]:
    found: set[int] = set()
    for row in board.rows:
        found.update(row.get("common_shishens") or ())
    return tuple(sorted(found))
