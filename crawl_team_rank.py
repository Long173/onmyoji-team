#!/usr/bin/env python3
"""CLI crawl bảng阵容 của https://yysrank.win/#/query/team.

Ví dụ:
    python3 crawl_team_rank.py --start 2026-07-22 --end 2026-08-24
    python3 crawl_team_rank.py --thres 30 --order total --max-pages 5
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

from onmyoji.assets import fetch_shishen_map
from onmyoji.http import ApiError
from onmyoji.output import normalize_row, write_csv, write_json
from onmyoji.team_rank import ORDER_FIELDS, TeamRankQuery, iter_pages

DEFAULT_OUTPUT_DIR = Path("out")
POLITE_DELAY_SECONDS = 0.4


def _parse_date(value: str) -> str:
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"ngày phải theo dạng YYYY-MM-DD: {value!r}") from exc


def _parse_ids(value: str) -> tuple[int, ...]:
    if not value.strip():
        return ()
    try:
        return tuple(int(part) for part in value.replace(",", " ").split())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"danh sách id không hợp lệ: {value!r}") from exc


def build_parser() -> argparse.ArgumentParser:
    today = dt.date.today()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", type=_parse_date, default="2026-07-22", help="ngày bắt đầu (mặc định: đầu version hiện tại)")
    parser.add_argument("--end", type=_parse_date, default=today.isoformat(), help="ngày kết thúc")
    parser.add_argument("--min-level", type=int, default=10, help="mốc điểm/đoạn dưới (10 = 名仕)")
    parser.add_argument("--max-level", type=int, default=9999, help="mốc điểm/đoạn trên")
    parser.add_argument("--thres", type=int, default=100, help="số trận tối thiểu của một阵容")
    parser.add_argument("--first-n", type=int, default=5, help="độ dài阵容 (số Thức thần)")
    parser.add_argument("--order", choices=ORDER_FIELDS, default="win_rate", help="cột sắp xếp")
    parser.add_argument("--asc", action="store_true", help="sắp xếp tăng dần")
    parser.add_argument("--page-size", type=int, default=50, help="số dòng mỗi request (tối đa 100)")
    parser.add_argument("--max-pages", type=int, default=None, help="giới hạn số trang crawl")
    parser.add_argument("--include", type=_parse_ids, default=(), help="id Thức thần buộc phải có, cách nhau bởi dấu phẩy")
    parser.add_argument("--exclude", type=_parse_ids, default=(), help="id Thức thần loại trừ")
    parser.add_argument("--ban", type=_parse_ids, default=(), help="id Thức thần ở ô ban (tối đa 2)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="thư mục xuất kết quả")
    parser.add_argument("--slug", default="team-rank", help="tiền tố tên file xuất")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        query = TeamRankQuery(
            start_date=args.start,
            end_date=args.end,
            min_level=args.min_level,
            max_level=args.max_level,
            thres=args.thres,
            first_n=args.first_n,
            order=args.order,
            desc=not args.asc,
            page_size=args.page_size,
            include=args.include,
            exclude=args.exclude,
            ban=args.ban,
        )
    except ValueError as exc:
        print(f"Tham số không hợp lệ: {exc}", file=sys.stderr)
        return 2

    try:
        shishen_names = fetch_shishen_map()
        print(f"Đã tải {len(shishen_names)} Thức thần.", file=sys.stderr)

        rows: list[dict] = []
        last_update = ""
        total = 0

        for page in iter_pages(query, max_pages=args.max_pages):
            last_update, total = page.last_update, page.total
            for offset, raw in enumerate(page.rows):
                rank = (page.page - 1) * query.page_size + offset + 1
                rows.append(dict(normalize_row(raw, rank, shishen_names)))
            print(f"  trang {page.page}: +{len(page.rows)} dòng ({len(rows)}/{total})", file=sys.stderr)
            time.sleep(POLITE_DELAY_SECONDS)
    except ApiError as exc:
        print(f"Lỗi API: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Đã dừng theo yêu cầu.", file=sys.stderr)
        return 130

    if not rows:
        print("Không có dữ liệu khớp filter.", file=sys.stderr)
        return 1

    metadata = {
        "source": "https://yysrank.win/#/query/team",
        "endpoint": "/api/team/rank",
        "params": dict(query.params_for_page(1)),
        "server_last_update": last_update,
        "total_matching_teams": total,
    }

    json_path = args.out_dir / f"{args.slug}.json"
    csv_path = args.out_dir / f"{args.slug}.csv"
    write_json(json_path, metadata, rows)
    write_csv(csv_path, rows)

    print(f"Xong: {len(rows)} 阵容 -> {json_path} và {csv_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
