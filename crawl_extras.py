#!/usr/bin/env python3
"""CLI crawl các endpoint MỞ còn lại: nhãn vai trò, thống kê site, độ nóng.

Không cần token — CI chạy được, dữ liệu tự cập nhật hằng ngày.

BXH người chơi (`/api/user-report/rank-top-100`) KHÔNG mở — nó trả
`401 请登录后使用本功能`, nên nằm ở crawl_player_board.py (cần token).

    python3 crawl_extras.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from onmyoji.http import ApiError, get_json
from onmyoji.site_stats import fetch_heat, fetch_site_statistic
from onmyoji.tags import TAG_ALL_PATH, dropped_tag_names, fetch_shishen_tags

DEFAULT_OUTPUT = Path("out/extras-current.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="file JSON xuất ra")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        tags = fetch_shishen_tags()
        raw_tags = get_json(TAG_ALL_PATH)
        stats = fetch_site_statistic()
        heat = fetch_heat()
    except ApiError as exc:
        print(f"Lỗi API: {exc}", file=sys.stderr)
        return 1

    dropped = dropped_tag_names(raw_tags if isinstance(raw_tags, list) else [])
    if dropped:
        print(
            f"{len(dropped)} nhãn chưa có bản dịch nên bị bỏ (meme/từ tục hoặc cần bổ sung): "
            + ", ".join(dropped[:12])
            + ("…" if len(dropped) > 12 else ""),
            file=sys.stderr,
        )

    document = {
        "metadata": {
            "endpoints": [
                "/api/shishen/tag/all",
                "/api/asset/tag",
                "/api/statistic",
                "/api/asset/heat",
            ],
            "access_tier": "mở — không cần đăng nhập",
            "note": (
                "Nhãn chỉ giữ nhóm system (từ vựng chức năng do site chuẩn hoá) cộng ba "
                "nhãn cơ chế của người dùng; nhóm còn lại là meme/từ tục nên bỏ."
            ),
            "dropped_tags": list(dropped),
        },
        "tags": {str(k): [dict(x) for x in v] for k, v in sorted(tags.items())},
        "statistic": dict(stats.as_dict()),
        "heat": {str(k): dict(v) for k, v in sorted(heat.items())},
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    size_kb = args.output.stat().st_size / 1024
    print(
        f"Xong: {len(tags)} Thức thần có nhãn, {len(heat)} độ nóng, "
        f"tổng {stats.total_matches:,} trận -> {args.output} ({size_kb:.0f} KB)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
