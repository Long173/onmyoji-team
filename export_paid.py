#!/usr/bin/env python3
"""Xuất phần dữ liệu hội viên ra `prebuilt/paid.json` để commit.

CI không lấy được dữ liệu này: refresh token của yysrank.win dùng một lần và site
chỉ cho một session, nên CI refresh sẽ đăng xuất bạn khỏi browser. Cách làm là
build tại máy, commit khối JSON đã lọc sẵn, rồi CI trộn vào bản build hằng ngày.

Chạy sau khi đã crawl:
    ./save-token.sh
    python3 crawl_shishen_detail.py
    python3 crawl_team_detail.py --top 40 --by total
    python3 export_paid.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from onmyoji.report import build_paid_payload, paid_payload_is_empty

DEFAULT_RANK = Path("out/shishen-rank-current.json")
DEFAULT_UNIT_DETAIL = Path("out/shishen-detail-current.json")
DEFAULT_TEAM_DETAIL = Path("out/team-detail-current.json")
DEFAULT_TEAM_YUHUN = Path("out/team-yuhun-current.json")
DEFAULT_OUTPUT = Path("prebuilt/paid.json")


def _load(path: Path, label: str) -> dict | None:
    if not path.is_file():
        print(f"Không thấy {label}: {path}", file=sys.stderr)
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Không đọc được {path}: {exc}", file=sys.stderr)
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rank", type=Path, default=DEFAULT_RANK, help="file của crawl_shishen_rank.py")
    parser.add_argument("--unit-detail", type=Path, default=DEFAULT_UNIT_DETAIL, help="file của crawl_shishen_detail.py")
    parser.add_argument("--team-detail", type=Path, default=DEFAULT_TEAM_DETAIL, help="file của crawl_team_detail.py")
    parser.add_argument("--team-yuhun", type=Path, default=DEFAULT_TEAM_YUHUN, help="file của crawl_team_yuhun.py")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="file JSON xuất ra để commit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    rank = _load(args.rank, "bảng xếp hạng 式神")
    unit_detail = _load(args.unit_detail, "chi tiết 式神")
    team_detail = _load(args.team_detail, "chi tiết đội hình")
    team_yuhun = _load(args.team_yuhun, "ngự hồn theo đội hình")

    if rank is None or unit_detail is None:
        print("Thiếu dữ liệu bắt buộc — chạy crawl trước.", file=sys.stderr)
        return 2

    paid = build_paid_payload(unit_detail, rank, team_detail, team_yuhun)
    if paid_payload_is_empty(paid):
        print(
            "Khối dữ liệu hội viên rỗng. Token có thuộc hội viên basic không? "
            "Đăng nhập lại rồi ./save-token.sh, sau đó crawl lại.",
            file=sys.stderr,
        )
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(paid, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    units = len(((paid.get("paid") or {}).get("units")) or {})
    teams = len(((paid.get("team_paid") or {}).get("teams")) or {})
    yuhun_teams = len(((paid.get("team_yuhun") or {}).get("teams")) or {})
    size_kb = args.output.stat().st_size / 1024
    print(
        f"Xong: {units} 式神 + {teams} đội hình (+{yuhun_teams} có ngự hồn) "
        f"-> {args.output} ({size_kb:.0f} KB). "
        "Commit file này để CI trộn vào bản build hằng ngày.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
