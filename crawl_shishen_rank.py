#!/usr/bin/env python3
"""CLI crawl bảng xếp hạng 式神 của https://yysrank.win/#/query/shishen.

Gộp 3 endpoint mở: /api/shishen/rank (meta), /api/asset/shishen_stats (chỉ số gốc),
/api/asset/yuhun (tên + icon ngự hồn).

Ví dụ:
    python3 crawl_shishen_rank.py
    python3 crawl_shishen_rank.py --start 2026-06-24 --end 2026-07-21 --slug shishen-bishamon
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from onmyoji.assets import fetch_shishen_map, fetch_shishen_stats, fetch_yuhun_map
from onmyoji.http import ApiError
from onmyoji.shishen_rank import (
    SUIT_TYPE_LABELS,
    ShishenRankQuery,
    fetch_rank,
    referenced_shishen_ids,
    referenced_yuhun_ids,
)
from onmyoji.translate import build_name_table, to_hanviet, unmapped_chars

DEFAULT_OUTPUT_DIR = Path("out")


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
    parser.add_argument("--start", type=_parse_date, default="2026-07-22", help="ngày bắt đầu")
    parser.add_argument("--end", type=_parse_date, default=today.isoformat(), help="ngày kết thúc")
    parser.add_argument("--min-level", type=int, default=10, help="mốc điểm/đoạn dưới")
    parser.add_argument("--max-level", type=int, default=9999, help="mốc điểm/đoạn trên")
    parser.add_argument("--tag", default="", help="lọc theo tag của site")
    parser.add_argument("--ban", type=_parse_ids, default=(), help="id 式神 ở ô ban (tối đa 2)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="thư mục xuất")
    parser.add_argument("--slug", default="shishen-rank", help="tiền tố tên file xuất")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        query = ShishenRankQuery(
            start_date=args.start,
            end_date=args.end,
            min_level=args.min_level,
            max_level=args.max_level,
            tag=args.tag,
            ban=args.ban,
        )
    except ValueError as exc:
        print(f"Tham số không hợp lệ: {exc}", file=sys.stderr)
        return 2

    try:
        rank = fetch_rank(query)
        print(f"Bảng 式神: {len(rank.rows)} dòng, phân tích {rank.matches_analysed:,} trận.", file=sys.stderr)
        shishen_map = fetch_shishen_map()
        stats = fetch_shishen_stats()
        yuhun_map = fetch_yuhun_map()
        print(f"Asset: {len(shishen_map)} 式神, {len(stats)} bộ chỉ số, {len(yuhun_map)} ngự hồn.", file=sys.stderr)
    except ApiError as exc:
        print(f"Lỗi API: {exc}", file=sys.stderr)
        return 1

    if not rank.rows:
        print("Bảng xếp hạng rỗng — kiểm tra lại khoảng thời gian.", file=sys.stderr)
        return 1

    names = build_name_table(shishen_map)
    unknown = {n.chinese: unmapped_chars(n.chinese) for n in names.values() if unmapped_chars(n.chinese)}
    unknown.update({y["name"]: unmapped_chars(y["name"]) for y in yuhun_map.values() if unmapped_chars(y["name"])})
    if unknown:
        print(f"Cảnh báo: {len(unknown)} tên có ký tự chưa có âm Hán-Việt: {unknown}", file=sys.stderr)

    document = {
        "metadata": {
            "source": "https://yysrank.win/#/query/shishen",
            "endpoints": [
                "/api/shishen/rank",
                "/api/asset/shishen_stats",
                "/api/asset/yuhun",
                "/api/asset/shishen",
            ],
            "params": dict(query.as_params()),
            "server_last_update": rank.last_update,
            "matches_analysed": rank.matches_analysed,
        },
        "shishen": [dict(row) for row in rank.rows],
        "stats": {str(k): v for k, v in stats.items() if k in referenced_shishen_ids(rank.rows)},
        "names": {
            str(sid): {"vn": n.hanviet, "cn": n.chinese, "common": n.common}
            for sid, n in names.items()
            if sid in referenced_shishen_ids(rank.rows)
        },
        # Xuất TẤT CẢ ngự hồn (chỉ ~79 dòng text) chứ không riêng cái được tham chiếu:
        # /api/shishen/detail của hội viên basic nhắc tới nhiều bộ hơn most_used_yuhuns.
        "yuhun": {
            str(yid): {
                "vn": to_hanviet(meta["name"]),
                "cn": meta["name"],
                "suit_type": SUIT_TYPE_LABELS.get(meta["suit_type"], meta["suit_type"]),
                "suit_type_raw": meta["suit_type"],
                "icon": meta["icon"],
            }
            for yid, meta in sorted(yuhun_map.items())
        },
        "yuhun_most_used": list(referenced_yuhun_ids(rank.rows)),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    path = args.out_dir / f"{args.slug}.json"
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Xong: {len(document['shishen'])} 式神, {len(document['yuhun'])} ngự hồn -> {path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
