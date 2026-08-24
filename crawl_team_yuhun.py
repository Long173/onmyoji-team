#!/usr/bin/env python3
"""CLI crawl ngự hồn theo đội hình (`/api/team/yuhun`) — cần hội viên `basic`.

Dữ liệu thô từng tổ hợp quá phân mảnh (median 3 trận) nên module gộp ngay theo
cặp (Thức thần, ngự hồn) và chỉ giữ lựa chọn từ 30 trận trở lên. Xem onmyoji/team_yuhun.py.

Ví dụ:
    python3 crawl_team_yuhun.py                    # 40 đội nhiều trận nhất
    python3 crawl_team_yuhun.py --top 10 --delay 1
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from onmyoji.auth import AuthError, resolve_token
from onmyoji.http import ApiError, AuthRequiredError
from onmyoji.team_yuhun import (
    MIN_USAGE_MATCHES,
    MIN_WIN_RATE_MATCHES,
    TeamYuhunQuery,
    fetch_team_yuhun,
)

DEFAULT_INPUT = Path("out/team-rank-current.json")
DEFAULT_OUTPUT = Path("out/team-yuhun-current.json")
DEFAULT_TOP = 40
DEFAULT_DELAY = 0.8


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="file của crawl_team_rank.py")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="file JSON xuất ra")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP, help=f"số đội hình (mặc định {DEFAULT_TOP})")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help=f"giây nghỉ giữa request (mặc định {DEFAULT_DELAY})")
    parser.add_argument(
        "--by",
        choices=("total", "win_rate"),
        default="total",
        help="chọn đội hình theo số trận (mặc định) hay tỉ lệ thắng",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.top < 1 or args.delay < 0:
        print("--top phải >= 1 và --delay không được âm", file=sys.stderr)
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
    query = TeamYuhunQuery(
        start_date=str(params.get("start_date") or ""),
        end_date=str(params.get("end_date") or ""),
        min_level=int(params.get("min_level") or 10),
        max_level=int(params.get("max_level") or 9999),
    )
    if not query.start_date or not query.end_date:
        print("File đầu vào thiếu start_date/end_date.", file=sys.stderr)
        return 2

    pool = sorted(crawl.get("teams") or (), key=lambda t: -float(t.get(args.by) or 0))
    targets = [
        {"team_ids": list(t["team_ids"]), "total": t.get("total")}
        for t in pool[: args.top]
    ]
    if not targets:
        print("Không có đội hình nào.", file=sys.stderr)
        return 1

    print(
        f"Lấy ngự hồn của {len(targets)} đội hình, nghỉ {args.delay}s mỗi request. "
        f"Ngưỡng gộp: {MIN_USAGE_MATCHES} trận (tỉ lệ thắng từ {MIN_WIN_RATE_MATCHES}).",
        file=sys.stderr,
    )

    results: list[dict] = []
    failures: list[dict] = []

    for index, target in enumerate(targets, start=1):
        ids = target["team_ids"]
        try:
            picked = fetch_team_yuhun(query, ids, token)
        except AuthRequiredError as exc:
            print(f"\nDừng — token không đủ quyền hoặc session bị vô hiệu:\n  {exc}", file=sys.stderr)
            break
        except ApiError as exc:
            failures.append({"team_ids": ids, "error": str(exc)})
            print(f"  [{index}/{len(targets)}] lỗi: {exc}", file=sys.stderr)
            continue

        record = dict(picked.as_dict())
        record["team_total"] = target.get("total")
        results.append(record)
        share = (
            f"{100 * picked.covered_matches / target['total']:.1f}%"
            if target.get("total")
            else "?"
        )
        print(
            f"  [{index}/{len(targets)}] {ids} → {picked.combos} tổ hợp, "
            f"{len(picked.options)} lựa chọn đạt ngưỡng, phủ {share} số trận của đội",
            file=sys.stderr,
        )
        if index < len(targets):
            time.sleep(args.delay)

    if not results:
        print("Không lấy được gì.", file=sys.stderr)
        return 1

    document = {
        "metadata": {
            "source": "https://yysrank.win/#/query/team-counter/detail",
            "endpoint": TEAM_YUHUN_PATH_LABEL,
            "access_tier": "basic",
            "note": (
                "API chỉ trả top 50 tổ hợp ngự hồn của cả đội nên chỉ phủ ~4-5% số trận "
                "và mẫu lệch về các tổ hợp phổ biến. Số liệu đã gộp theo cặp "
                f"(Thức thần, ngự hồn), lọc từ {MIN_USAGE_MATCHES} trận; tỉ lệ thắng chỉ hiện "
                f"từ {MIN_WIN_RATE_MATCHES} trận trở lên."
            ),
            "params": dict(query.params_for(results[0]["team_ids"])),
            "selected_by": args.by,
            "requested": len(targets),
            "fetched": len(results),
            "failed": len(failures),
            "min_usage_matches": MIN_USAGE_MATCHES,
            "min_win_rate_matches": MIN_WIN_RATE_MATCHES,
        },
        "teams": results,
        "failures": failures,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Xong: {len(results)}/{len(targets)} đội hình -> {args.output}", file=sys.stderr)
    return 0


TEAM_YUHUN_PATH_LABEL = "/api/team/yuhun"


if __name__ == "__main__":
    raise SystemExit(main())
