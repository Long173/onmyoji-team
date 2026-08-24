#!/usr/bin/env python3
"""CLI crawl chi tiết đội hình (`/api/team/detail`) — cần token đăng nhập.

Endpoint này ở mức `free`: chỉ cần tài khoản đã đăng ký, không cần hội viên.
Mặc định chỉ lấy TOP 30 đội hình để không nã request vào site.

Ví dụ:
    python3 crawl_team_detail.py                       # top 30 theo tỉ lệ thắng
    python3 crawl_team_detail.py --top 100 --delay 1.5
    python3 crawl_team_detail.py --team 330,390,575,578,585
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

from onmyoji.auth import AuthError, resolve_token
from onmyoji.http import ApiError, AuthRequiredError
from onmyoji.team_detail import (
    SECTION_LABELS,
    TeamDetailQuery,
    fetch_detail,
    section_sizes,
)

DEFAULT_INPUT = Path("out/team-rank-current.json")
DEFAULT_OUTPUT = Path("out/team-detail-current.json")
DEFAULT_TOP = 30
DEFAULT_DELAY = 1.0


def _parse_ids(value: str) -> tuple[int, ...]:
    try:
        ids = tuple(int(part) for part in value.replace(",", " ").split())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"danh sách id không hợp lệ: {value!r}") from exc
    if not ids:
        raise argparse.ArgumentTypeError("đội hình rỗng")
    return ids


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="file JSON của crawl_team_rank.py")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="file JSON xuất ra")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP, help=f"số đội hình lấy chi tiết (mặc định {DEFAULT_TOP})")
    parser.add_argument("--team", type=_parse_ids, default=None, help="chỉ lấy một đội hình cụ thể, vd 330,390,575,578,585")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help=f"giây nghỉ giữa các request (mặc định {DEFAULT_DELAY})")
    parser.add_argument(
        "--by",
        choices=("total", "win_rate"),
        default="total",
        help=(
            "chọn đội hình theo tiêu chí nào. `total` (mặc định) lấy đội nhiều trận nhất — "
            "thứ tự BP / âm dương sư / counter mới đủ mẫu; `win_rate` lấy đội thắng cao nhất "
            "nhưng dữ liệu con thường rất mỏng."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.top < 1:
        print("--top phải >= 1", file=sys.stderr)
        return 2
    if args.delay < 0:
        print("--delay không được âm", file=sys.stderr)
        return 2

    try:
        token = resolve_token()
    except AuthError as exc:
        print(f"Chưa có token:\n{exc}", file=sys.stderr)
        return 2

    if not args.input.is_file():
        print(f"Không thấy {args.input}. Chạy `python3 crawl_team_rank.py` trước.", file=sys.stderr)
        return 2

    try:
        crawl = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Không đọc được {args.input}: {exc}", file=sys.stderr)
        return 2

    params = dict((crawl.get("metadata") or {}).get("params") or {})
    query = TeamDetailQuery(
        start_date=str(params.get("start_date") or dt.date.today().isoformat()),
        end_date=str(params.get("end_date") or dt.date.today().isoformat()),
        min_level=int(params.get("min_level") or 10),
        max_level=int(params.get("max_level") or 9999),
    )

    if args.team:
        targets = [{"team_ids": list(args.team), "rank": None, "total": None}]
    else:
        pool = sorted(
            crawl.get("teams") or (),
            key=lambda t: -float(t.get(args.by) or 0),
        )
        targets = [
            {"team_ids": list(t["team_ids"]), "rank": t.get("rank"), "total": t.get("total")}
            for t in pool[: args.top]
        ]

    if not targets:
        print("Không có đội hình nào để lấy chi tiết.", file=sys.stderr)
        return 1

    print(f"Lấy chi tiết {len(targets)} đội hình, nghỉ {args.delay}s mỗi request.", file=sys.stderr)

    details: list[dict] = []
    failures: list[dict] = []

    for index, target in enumerate(targets, start=1):
        ids = target["team_ids"]
        try:
            detail = fetch_detail(query, ids, token)
        except AuthRequiredError as exc:
            print(f"\nDừng lại — token không đủ quyền hoặc đã hết hạn:\n  {exc}", file=sys.stderr)
            break
        except ApiError as exc:
            failures.append({"team_ids": ids, "error": str(exc)})
            print(f"  [{index}/{len(targets)}] lỗi: {exc}", file=sys.stderr)
            continue

        sizes = section_sizes(detail)
        details.append(
            {"team_ids": ids, "rank": target["rank"], "total": target.get("total"), "detail": detail}
        )
        filled = ", ".join(f"{k}={v}" for k, v in sizes.items() if v)
        print(f"  [{index}/{len(targets)}] {ids} → {filled or 'rỗng'}", file=sys.stderr)

        if index < len(targets):
            time.sleep(args.delay)

    if not details:
        print("Không lấy được chi tiết nào.", file=sys.stderr)
        return 1

    document = {
        "metadata": {
            "source": "https://yysrank.win/#/query/team/detail",
            "endpoint": "/api/team/detail",
            "access_tier": "free (cần đăng nhập)",
            "params": dict(query.params_for(details[0]["team_ids"])),
            "section_labels": dict(SECTION_LABELS),
            "selected_by": args.by,
            "requested": len(targets),
            "fetched": len(details),
            "failed": len(failures),
        },
        "details": details,
        "failures": failures,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Xong: {len(details)}/{len(targets)} đội hình -> {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
