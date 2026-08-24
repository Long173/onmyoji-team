"""Dựng báo cáo HTML từ dữ liệu đã crawl."""

from __future__ import annotations

import base64
import datetime as dt
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .translate import ShishenName

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "report.html"
DATA_PLACEHOLDER = "__DATA__"
AVATAR_PLACEHOLDER = "__AVATAR_CSS__"


class ReportError(RuntimeError):
    """Không dựng được báo cáo."""


@dataclass(frozen=True)
class ShishenStat:
    """Thống kê gộp của một 式神 trong tập đội hình."""

    shishen_id: int
    teams: int
    matches: int
    win_rate: float

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "id": self.shishen_id,
            "teams": self.teams,
            "matches": self.matches,
            "win_rate": self.win_rate,
        }


def aggregate_shishen(teams: Sequence[Mapping[str, Any]]) -> tuple[ShishenStat, ...]:
    """Gộp số liệu theo 式神: số đội hình, tổng trận, tỉ lệ thắng gia quyền."""
    buckets: dict[int, dict[str, float]] = defaultdict(
        lambda: {"teams": 0.0, "matches": 0.0, "weighted": 0.0}
    )

    for team in teams:
        matches = int(team.get("total") or 0)
        win_rate = float(team.get("win_rate") or 0.0)
        for shishen_id in team.get("team_ids") or ():
            bucket = buckets[int(shishen_id)]
            bucket["teams"] += 1
            bucket["matches"] += matches
            bucket["weighted"] += win_rate * matches

    stats = tuple(
        ShishenStat(
            shishen_id=shishen_id,
            teams=int(bucket["teams"]),
            matches=int(bucket["matches"]),
            win_rate=bucket["weighted"] / bucket["matches"] if bucket["matches"] else 0.0,
        )
        for shishen_id, bucket in buckets.items()
    )
    return tuple(sorted(stats, key=lambda s: (-s.matches, s.shishen_id)))


def build_avatar_css(shishen_ids: Sequence[int], avatar_dir: Path) -> str:
    """Nhúng mỗi avatar đúng một lần thành class CSS `.a<id>`."""
    rules: list[str] = []
    for shishen_id in shishen_ids:
        path = avatar_dir / f"{shishen_id}.webp"
        if not path.is_file():
            continue
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        rules.append(f'.a{shishen_id}{{background-image:url("data:image/webp;base64,{encoded}")}}')

    if not rules:
        raise ReportError(f"không tìm thấy avatar nào trong {avatar_dir}")
    return "\n".join(rules)


def build_payload(
    crawl: Mapping[str, Any],
    names: Mapping[int, ShishenName],
    stats: Sequence[ShishenStat],
    *,
    version_label: str,
    version_cn: str,
    generated_at: str,
    data_links: Sequence[Mapping[str, str]] = (),
) -> Mapping[str, Any]:
    """Gói dữ liệu mà template cần — thuần dữ liệu, không HTML."""
    teams = list(crawl.get("teams") or ())
    if not teams:
        raise ReportError("dữ liệu crawl không có đội hình nào")

    params = dict((crawl.get("metadata") or {}).get("params") or {})
    win_rates = [float(t["win_rate"]) for t in teams]

    return {
        "meta": {
            "version_label": version_label,
            "version_cn": version_cn,
            "start_date": params.get("start_date", ""),
            "end_date": params.get("end_date", ""),
            "thres": params.get("thres", 0),
            "last_update": str((crawl.get("metadata") or {}).get("server_last_update", ""))[:19].replace("T", " "),
            "generated_at": generated_at,
            "total_matches": sum(int(t["total"]) for t in teams),
            "pick_coverage": sum(float(t["pick_rate"]) for t in teams),
            "median_win_rate": statistics.median(win_rates),
            "max_win_rate": max(win_rates),
            "min_win_rate": min(win_rates),
            "median_duration": statistics.median(float(t["duration"]) for t in teams),
            "data_links": [dict(link) for link in data_links],
        },
        "names": {
            str(stat.shishen_id): {
                "vn": names[stat.shishen_id].hanviet if stat.shishen_id in names else f"#{stat.shishen_id}",
                "cn": names[stat.shishen_id].chinese if stat.shishen_id in names else "",
                "common": names[stat.shishen_id].common if stat.shishen_id in names else "",
            }
            for stat in stats
        },
        "teams": [
            {
                "team_ids": list(t["team_ids"]),
                "win_rate": float(t["win_rate"]),
                "pick_rate": float(t["pick_rate"]),
                "total": int(t["total"]),
                "duration": float(t["duration"]),
            }
            for t in teams
        ],
        "shishen": [stat.as_dict() for stat in stats],
    }


def render_report(payload: Mapping[str, Any], avatar_css: str) -> str:
    """Chèn dữ liệu + CSS avatar vào template."""
    if not TEMPLATE_PATH.is_file():
        raise ReportError(f"thiếu template: {TEMPLATE_PATH}")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    for placeholder in (DATA_PLACEHOLDER, AVATAR_PLACEHOLDER):
        if placeholder not in template:
            raise ReportError(f"template thiếu placeholder {placeholder}")

    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if "</script" in serialized:
        raise ReportError("dữ liệu chứa '</script' — sẽ phá cấu trúc HTML")

    return template.replace(AVATAR_PLACEHOLDER, avatar_css).replace(DATA_PLACEHOLDER, serialized)


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")
