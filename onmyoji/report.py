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
from .yys import yys_table

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "report.html"
DATA_PLACEHOLDER = "__DATA__"
AVATAR_PLACEHOLDER = "__AVATAR_CSS__"

MIME_BY_SUFFIX = {".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg"}


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


def _image_rule(selector: str, path: Path) -> str:
    mime = MIME_BY_SUFFIX.get(path.suffix.lower())
    if mime is None:
        raise ReportError(f"không rõ kiểu ảnh: {path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'{selector}{{background-image:url("data:{mime};base64,{encoded}")}}'


def build_avatar_css(shishen_ids: Sequence[int], avatar_dir: Path) -> str:
    """Nhúng mỗi avatar 式神 đúng một lần thành class CSS `.a<id>`."""
    rules = [
        _image_rule(f".a{shishen_id}", avatar_dir / f"{shishen_id}.webp")
        for shishen_id in shishen_ids
        if (avatar_dir / f"{shishen_id}.webp").is_file()
    ]
    if not rules:
        raise ReportError(f"không tìm thấy avatar nào trong {avatar_dir}")
    return "\n".join(rules)


def build_yuhun_css(yuhun_ids: Sequence[int], yuhun_dir: Path) -> str:
    """Nhúng icon 御魂 thành class CSS `.y<id>`. Icon có thể là .webp hoặc .png."""
    rules: list[str] = []
    for yuhun_id in yuhun_ids:
        for suffix in (".webp", ".png"):
            path = yuhun_dir / f"{yuhun_id}{suffix}"
            if path.is_file():
                rules.append(_image_rule(f".y{yuhun_id}", path))
                break
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
    unit_rank: Mapping[str, Any] | None = None,
    unit_detail: Mapping[str, Any] | None = None,
    team_detail: Mapping[str, Any] | None = None,
    include_paid: bool = False,
    paid_payload: Mapping[str, Any] | None = None,
    sibling_link: Mapping[str, str] | None = None,
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
            "sibling": dict(sibling_link) if sibling_link else None,
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
        **_unit_section(unit_rank),
        **_detail_section(unit_detail, teams),
        **(
            dict(paid_payload)
            if paid_payload
            else {
                **_paid_section(unit_detail, unit_rank, include_paid),
                **_team_paid_section(team_detail, include_paid),
            }
        ),
    }


def _unit_section(unit_rank: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Phần dữ liệu cho tab 式神. Rỗng nếu chưa crawl bảng xếp hạng 式神."""
    if not unit_rank:
        return {"units": [], "unit_names": {}, "stats": {}, "yuhun": {}}

    return {
        "units": list(unit_rank.get("shishen") or ()),
        "unit_names": dict(unit_rank.get("names") or {}),
        "stats": dict(unit_rank.get("stats") or {}),
        "yuhun": dict(unit_rank.get("yuhun") or {}),
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


MIN_HIDDEN_MATCHES = 30
MAX_HIDDEN_TEAMS = 400


def derive_pick_base(teams: Sequence[Mapping[str, Any]]) -> float:
    """Tổng lượt chọn trong khoảng lọc, suy ra từ `total / pick_rate`.

    Tỉ số này bằng nhau ở mọi đội hình (đã kiểm: lệch 0.00% trên 676 dòng), nên
    nó cho phép quy đổi `pick_rate` của các đội hình KHÔNG có field `total`
    (`/api/shishen/detail` → `summary.teams`) về số trận thật.
    """
    ratios = [
        float(t["total"]) / float(t["pick_rate"])
        for t in teams
        if float(t.get("pick_rate") or 0) > 0 and t.get("total")
    ]
    return statistics.median(ratios) if ratios else 0.0


def _trend_payload(details: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Chuỗi win_rate 33 ngày cho từng 式神, dùng chung một thang y để so sánh được."""
    dates: tuple[str, ...] = ()
    series: dict[str, list[float]] = {}

    for entry in details:
        points = entry.get("trend") or []
        if not points:
            continue
        if not dates:
            dates = tuple(str(p["date"])[:10] for p in points)
        series[str(entry["shishen_id"])] = [float(p.get("win_rate") or 0.0) for p in points]

    values = [v for row in series.values() for v in row]
    if values:
        low, high = min(values), max(values)
        pad = max(0.005, (high - low) * 0.06)
        domain = [round(low - pad, 4), round(high + pad, 4)]
    else:
        domain = [0.4, 0.6]

    return {"dates": list(dates), "domain": domain, "series": series}


def _hidden_teams(
    details: Sequence[Mapping[str, Any]],
    ranked_teams: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Đội hình có trong `summary.teams` nhưng KHÔNG có trong bảng xếp hạng.

    Bảng xếp hạng áp ngưỡng số trận, còn `summary.teams` thì không — nên đây là
    các đội hình dưới ngưỡng. Số trận được quy đổi từ `pick_rate`.
    """
    pick_base = derive_pick_base(ranked_teams)
    ranked = {tuple(sorted(int(i) for i in t["team_ids"])) for t in ranked_teams}

    best: dict[tuple[int, ...], Mapping[str, Any]] = {}
    for entry in details:
        for team in entry.get("teams") or ():
            ids = tuple(sorted(int(i) for i in (team.get("team") or ())))
            if not ids or ids in ranked or ids in best:
                continue
            matches = round(float(team.get("pick_rate") or 0.0) * pick_base)
            if matches < MIN_HIDDEN_MATCHES:
                continue
            best[ids] = {
                "team_ids": list(ids),
                "win_rate": float(team.get("win_rate") or 0.0),
                "pick_rate": float(team.get("pick_rate") or 0.0),
                "matches": matches,
            }

    rows = sorted(best.values(), key=lambda r: -r["win_rate"])[:MAX_HIDDEN_TEAMS]
    return {
        "pick_base": round(pick_base),
        "min_matches": MIN_HIDDEN_MATCHES,
        "total_found": len(best),
        "teams": rows,
    }


def _detail_section(
    unit_detail: Mapping[str, Any] | None,
    ranked_teams: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Phần trend + đội hình ẩn. Rỗng nếu chưa crawl /api/shishen/detail."""
    details = (unit_detail or {}).get("details") or []
    if not details:
        return {"trend": {"dates": [], "domain": [0.4, 0.6], "series": {}}, "hidden": {}}

    return {
        "trend": _trend_payload(details),
        "hidden": _hidden_teams(details, ranked_teams),
    }


# Ngưỡng số trận để một dòng ngự hồn / ghép cặp được coi là có ý nghĩa.
# Median toàn bộ chỉ 7 trận nên phần lớn dòng là nhiễu.
MIN_YUHUN_MATCHES = 100
MIN_PAIR_MATCHES = 300
TOP_PAIRS = 6
MIN_POSITION_MATCHES = 50


def _paid_rows(
    entry: Mapping[str, Any],
    baseline: float,
) -> Mapping[str, Any]:
    """Lọc nhiễu và tính chênh lệch so với tỉ lệ thắng chung của 式神 đó."""

    def keep(rows, key, floor):
        picked = [r for r in rows if int(r.get("total") or 0) >= floor]
        return sorted(picked, key=lambda r: -float(r.get("win_rate") or 0.0))

    yuhuns = [
        {
            "yuhun_id": int(r["yuhun_id"]),
            "total": int(r["total"]),
            "win_rate": float(r["win_rate"]),
            "delta": float(r["win_rate"]) - baseline,
        }
        for r in keep(entry.get("yuhuns") or (), "yuhun_id", MIN_YUHUN_MATCHES)
    ]

    def pair(key):
        return [
            {
                "shishen_id": int(r["shishen_id"]),
                "total": int(r["total"]),
                "win_rate": float(r["win_rate"]),
                "delta": float(r["win_rate"]) - baseline,
            }
            for r in keep(entry.get(key) or (), "shishen_id", MIN_PAIR_MATCHES)[:TOP_PAIRS]
        ]

    positions = sorted(
        (
            {
                "position": int(r["position"]),
                "total": int(r["total"]),
                "win_rate": float(r["win_rate"]),
            }
            for r in (entry.get("positions") or ())
            if int(r.get("total") or 0) >= MIN_POSITION_MATCHES
        ),
        key=lambda r: r["position"],
    )

    return {
        "baseline": baseline,
        "yuhuns": yuhuns,
        "synergies": pair("synergies"),
        "counters": pair("counters"),
        "positions": positions,
    }


def _paid_section(
    unit_detail: Mapping[str, Any] | None,
    unit_rank: Mapping[str, Any] | None,
    include_paid: bool,
) -> Mapping[str, Any]:
    """Dữ liệu chỉ hội viên `basic` mới có. Rỗng khi không bật `include_paid`.

    Đây là nội dung sau tường phí của yysrank.win — mặc định KHÔNG đưa vào bản
    build để publish công khai.
    """
    details = (unit_detail or {}).get("details") or []
    if not include_paid or not details:
        return {"paid": {}, "yuhun_all": {}}

    baselines = {
        int(row["shishen_id"]): float(row.get("win_rate") or 0.0)
        for row in ((unit_rank or {}).get("shishen") or ())
    }

    paid = {}
    for entry in details:
        shishen_id = int(entry["shishen_id"])
        rows = _paid_rows(entry, baselines.get(shishen_id, 0.0))
        if rows["yuhuns"] or rows["synergies"] or rows["counters"]:
            paid[str(shishen_id)] = rows

    return {
        "paid": {
            "units": paid,
            "min_yuhun_matches": MIN_YUHUN_MATCHES,
            "min_pair_matches": MIN_PAIR_MATCHES,
        },
        "yuhun_all": dict((unit_rank or {}).get("yuhun") or {}),
    }


def paid_yuhun_ids(payload: Mapping[str, Any]) -> tuple[int, ...]:
    """Các yuhun_id cần icon cho phần dữ liệu hội viên."""
    units = ((payload.get("paid") or {}).get("units")) or {}
    found = {int(row["yuhun_id"]) for unit in units.values() for row in unit.get("yuhuns") or ()}
    return tuple(sorted(found))


# Ngưỡng cho dữ liệu theo đội hình. counter bị phân mảnh nhiều nhất nên khắt khe hơn.
MIN_ORDER_MATCHES = 100
MIN_YYS_MATCHES = 50
MIN_COUNTER_MATCHES = 100
TOP_ORDERS = 5
TOP_COUNTERS = 5


def team_key(shishen_ids: Sequence[int]) -> str:
    """Khoá ổn định cho một đội hình, không phụ thuộc thứ tự đầu vào."""
    return "-".join(str(int(i)) for i in sorted(shishen_ids))


def _team_paid_rows(detail: Mapping[str, Any]) -> Mapping[str, Any]:
    """Lọc theo số trận rồi sắp xếp. Trả về mục rỗng nếu không dòng nào đủ mẫu."""
    orders = sorted(
        (
            {
                "sequence": [int(i) for i in (r.get("team") or ())],
                "total": int(r["total"]),
                "win_rate": float(r["win_rate"]),
                "pick_rate": float(r.get("pick_rate") or 0.0),
            }
            for r in (detail.get("order") or ())
            if int(r.get("total") or 0) >= MIN_ORDER_MATCHES
        ),
        key=lambda r: -r["win_rate"],
    )[:TOP_ORDERS]

    yys = sorted(
        (
            {
                "yys_id": int(r["yys_id"]),
                "total": int(r["total"]),
                "win_rate": float(r["win_rate"]),
                "pick_rate": float(r.get("pick_rate") or 0.0),
            }
            for r in (detail.get("yys") or ())
            if int(r.get("total") or 0) >= MIN_YYS_MATCHES
        ),
        key=lambda r: -r["total"],
    )

    # Sắp TĂNG dần: đội hình mình thắng thấp nhất mới là cái đáng đề phòng.
    counters = sorted(
        (
            {
                "team_ids": [int(i) for i in (r.get("team") or ())],
                "total": int(r["total"]),
                "win_rate": float(r["win_rate"]),
            }
            for r in (detail.get("counter") or ())
            if int(r.get("total") or 0) >= MIN_COUNTER_MATCHES
        ),
        key=lambda r: r["win_rate"],
    )[:TOP_COUNTERS]

    return {"orders": orders, "yys": yys, "counters": counters}


def _team_paid_section(
    team_detail: Mapping[str, Any] | None,
    include_paid: bool,
) -> Mapping[str, Any]:
    """Thứ tự BP / âm dương sư / đội hình đối đầu — chỉ hội viên `basic` mới có."""
    entries = (team_detail or {}).get("details") or []
    if not include_paid or not entries:
        return {"team_paid": {}, "yys": {}}

    rows = {}
    for entry in entries:
        detail = entry.get("detail") or {}
        picked = _team_paid_rows(detail)
        if picked["orders"] or picked["yys"] or picked["counters"]:
            rows[team_key(entry.get("team_ids") or ())] = picked

    if not rows:
        return {"team_paid": {}, "yys": {}}

    return {
        "team_paid": {
            "teams": rows,
            "min_order_matches": MIN_ORDER_MATCHES,
            "min_yys_matches": MIN_YYS_MATCHES,
            "min_counter_matches": MIN_COUNTER_MATCHES,
        },
        "yys": {str(k): dict(v) for k, v in yys_table().items()},
    }


def team_paid_shishen_ids(payload: Mapping[str, Any]) -> tuple[int, ...]:
    """式神 cần avatar cho phần counter theo đội hình."""
    teams = ((payload.get("team_paid") or {}).get("teams")) or {}
    found: set[int] = set()
    for row in teams.values():
        for counter in row.get("counters") or ():
            found.update(int(i) for i in counter.get("team_ids") or ())
    return tuple(sorted(found))


PAID_PAYLOAD_KEYS = ("paid", "team_paid", "yuhun_all", "yys")


def build_paid_payload(
    unit_detail: Mapping[str, Any] | None,
    unit_rank: Mapping[str, Any] | None,
    team_detail: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    """Gom toàn bộ phần dữ liệu hội viên thành một khối để commit rồi trộn lại sau.

    CI không lấy được dữ liệu này (refresh token dùng một lần, site chỉ cho một
    session), nên nó được build tại máy, commit dạng JSON, và CI chỉ trộn vào.
    """
    return {
        **_paid_section(unit_detail, unit_rank, include_paid=True),
        **_team_paid_section(team_detail, include_paid=True),
    }


def paid_payload_is_empty(paid_payload: Mapping[str, Any] | None) -> bool:
    if not paid_payload:
        return True
    units = ((paid_payload.get("paid") or {}).get("units")) or {}
    teams = ((paid_payload.get("team_paid") or {}).get("teams")) or {}
    return not units and not teams


def paid_payload_shishen_ids(paid_payload: Mapping[str, Any]) -> tuple[int, ...]:
    """式神 cần avatar cho phần dữ liệu hội viên (ghép cặp + counter + thứ tự pick)."""
    found: set[int] = set()
    for unit in (((paid_payload.get("paid") or {}).get("units")) or {}).values():
        for key in ("synergies", "counters"):
            for row in unit.get(key) or ():
                found.add(int(row["shishen_id"]))
    for team in (((paid_payload.get("team_paid") or {}).get("teams")) or {}).values():
        for row in team.get("counters") or ():
            found.update(int(i) for i in row.get("team_ids") or ())
        for row in team.get("orders") or ():
            found.update(int(i) for i in row.get("sequence") or ())
    return tuple(sorted(found))
