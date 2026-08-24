#!/usr/bin/env python3
"""CLI crawl `trend` và `summary.teams` cho từng 式神 (`/api/shishen/detail`).

Endpoint mở, không cần token. Lấy danh sách 式神 từ file của crawl_shishen_rank.py.

Ví dụ:
    python3 crawl_shishen_detail.py
    python3 crawl_shishen_detail.py --delay 1.5 --limit 10
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from onmyoji.http import ApiError
from onmyoji.shishen_detail import ShishenDetailQuery, fetch_detail

DEFAULT_INPUT = Path("out/shishen-rank-current.json")
DEFAULT_OUTPUT = Path("out/shishen-detail-current.json")
DEFAULT_DELAY = 0.8


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="file JSON của crawl_shishen_rank.py")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="file JSON xuất ra")
    parser.add_argument("--limit", type=int, default=None, help="chỉ lấy N 式神 đầu (mặc định: hết)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help=f"giây nghỉ giữa request (mặc định {DEFAULT_DELAY})")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.delay < 0:
        print("--delay không được âm", file=sys.stderr)
        return 2
    if not args.input.is_file():
        print(f"Không thấy {args.input}. Chạy `python3 crawl_shishen_rank.py` trước.", file=sys.stderr)
        return 2

    try:
        rank = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Không đọc được {args.input}: {exc}", file=sys.stderr)
        return 2

    params = dict((rank.get("metadata") or {}).get("params") or {})
    query = ShishenDetailQuery(
        start_date=str(params.get("start_date") or ""),
        end_date=str(params.get("end_date") or ""),
        min_level=int(params.get("min_level") or 10),
        max_level=int(params.get("max_level") or 9999),
    )
    if not query.start_date or not query.end_date:
        print("File đầu vào thiếu start_date/end_date trong metadata.", file=sys.stderr)
        return 2

    ids = [int(row["shishen_id"]) for row in (rank.get("shishen") or []) if row.get("shishen_id") is not None]
    if args.limit is not None:
        ids = ids[: args.limit]
    if not ids:
        print("Không có 式神 nào trong file đầu vào.", file=sys.stderr)
        return 1

    print(f"Lấy chi tiết {len(ids)} 式神, nghỉ {args.delay}s mỗi request.", file=sys.stderr)

    results: list[dict] = []
    failures: list[dict] = []

    for index, shishen_id in enumerate(ids, start=1):
        try:
            detail = fetch_detail(query, shishen_id)
        except ApiError as exc:
            failures.append({"shishen_id": shishen_id, "error": str(exc)})
            print(f"  [{index}/{len(ids)}] {shishen_id} lỗi: {exc}", file=sys.stderr)
            continue

        results.append(dict(detail.as_dict()))
        print(
            f"  [{index}/{len(ids)}] {shishen_id} → trend={len(detail.trend)} teams={len(detail.teams)}",
            file=sys.stderr,
        )
        if index < len(ids):
            time.sleep(args.delay)

    if not results:
        print("Không lấy được gì.", file=sys.stderr)
        return 1

    document = {
        "metadata": {
            "source": "https://yysrank.win/#/query/shishen/detail",
            "endpoint": "/api/shishen/detail",
            "note": (
                "summary.teams KHÔNG áp ngưỡng số trận nên có cả đội hình ít gặp. "
                "Các mục yuhuns/positions/counters/synergies bị site khoá sau hội viên basic."
            ),
            "params": dict(query.params_for(ids[0])),
            "requested": len(ids),
            "fetched": len(results),
            "failed": len(failures),
        },
        "details": results,
        "failures": failures,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    size_kb = args.output.stat().st_size / 1024
    print(f"Xong: {len(results)}/{len(ids)} 式神 -> {args.output} ({size_kb:.0f} KB)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
