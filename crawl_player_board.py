#!/usr/bin/env python3
"""CLI crawl BXH 100 người chơi (`/api/user-report/rank-top-100`) — CẦN đăng nhập.

Endpoint trả `401 请登录后使用本功能` cho khách, nên CI không lấy được; dữ liệu này
đi cùng khối token qua export_paid.py.

    ./save-token.sh && python3 crawl_player_board.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from onmyoji.auth import AuthError, resolve_token
from onmyoji.http import ApiError, AuthRequiredError
from onmyoji.site_stats import fetch_player_top100, player_shishen_ids

DEFAULT_OUTPUT = Path("out/player-board-current.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="file JSON xuất ra")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        token = resolve_token()
    except AuthError as exc:
        print(f"Chưa có token:\n{exc}", file=sys.stderr)
        return 2

    try:
        board = fetch_player_top100_with(token)
    except AuthRequiredError as exc:
        print(f"Token không đủ quyền hoặc session bị vô hiệu:\n  {exc}", file=sys.stderr)
        return 1
    except ApiError as exc:
        print(f"Lỗi API: {exc}", file=sys.stderr)
        return 1

    document = {
        "metadata": {
            "endpoint": "/api/user-report/rank-top-100",
            "access_tier": "cần đăng nhập (tài khoản free là đủ)",
            "window": f"{board.start_time} → {board.end_time}",
            "rows": len(board.rows),
        },
        "board": dict(board.as_dict()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Xong: {len(board.rows)} người chơi ({board.start_time} → {board.end_time}), "
        f"{len(player_shishen_ids(board))} 式神 được nhắc -> {args.output}",
        file=sys.stderr,
    )
    return 0


def fetch_player_top100_with(token: str):
    """`fetch_player_top100` không nhận token nên bọc lại ở đây."""
    from onmyoji.http import get_json
    from onmyoji.site_stats import PLAYER_TOP_PATH, PlayerBoard

    data = get_json(PLAYER_TOP_PATH, {}, token=token)
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


if __name__ == "__main__":
    raise SystemExit(main())
