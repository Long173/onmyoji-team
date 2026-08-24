#!/usr/bin/env python3
"""Dựng báo cáo HTML (kèm avatar) từ file JSON do crawl_team_rank.py sinh ra.

Ví dụ:
    python3 build_report.py
    python3 build_report.py --input out/team-rank-current.json --output report/meta.html
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from onmyoji.assets import fetch_shishen_map
from onmyoji.avatars import download_avatars
from onmyoji.http import ApiError
from onmyoji.report import (
    ReportError,
    aggregate_shishen,
    build_avatar_css,
    build_payload,
    now_stamp,
    render_report,
)
from onmyoji.translate import build_name_table, unmapped_chars

DEFAULT_INPUT = Path("out/team-rank-current.json")
DEFAULT_OUTPUT = Path("report/meta-dau-ky.html")
DEFAULT_AVATAR_DIR = Path("assets/avatars")
DATA_LINKS = (
    {"label": "JSON", "href": "team-rank-current.json"},
    {"label": "CSV", "href": "team-rank-current.csv"},
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="file JSON do crawler sinh ra")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="file HTML xuất ra")
    parser.add_argument("--avatar-dir", type=Path, default=DEFAULT_AVATAR_DIR, help="thư mục cache avatar")
    parser.add_argument("--version-label", default="Phiên bản hiện hành", help="nhãn phiên bản trên masthead")
    parser.add_argument("--version-cn", default="", help="tên phiên bản tiếng Trung")
    parser.add_argument("--skip-download", action="store_true", help="không tải avatar còn thiếu")
    parser.add_argument(
        "--data-links",
        action="store_true",
        help="thêm link tải JSON/CSV vào footer (dùng khi deploy web, file phải nằm cùng thư mục)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.input.is_file():
        print(f"Không thấy file dữ liệu: {args.input}", file=sys.stderr)
        print("Chạy `python3 crawl_team_rank.py` trước.", file=sys.stderr)
        return 2

    try:
        crawl = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Không đọc được {args.input}: {exc}", file=sys.stderr)
        return 2

    teams = crawl.get("teams") or []
    stats = aggregate_shishen(teams)
    shishen_ids = tuple(stat.shishen_id for stat in stats)

    try:
        shishen_map = fetch_shishen_map()
        if not args.skip_download:
            fetched, missing = download_avatars(shishen_ids, args.avatar_dir)
            print(f"Avatar: {fetched} tải mới, {len(shishen_ids) - len(missing)} sẵn sàng.", file=sys.stderr)
            if missing:
                print(f"  thiếu: {sorted(missing)}", file=sys.stderr)
    except ApiError as exc:
        print(f"Lỗi API: {exc}", file=sys.stderr)
        return 1

    names = build_name_table(shishen_map)
    unknown = {
        name.chinese: unmapped_chars(name.chinese)
        for name in names.values()
        if unmapped_chars(name.chinese)
    }
    if unknown:
        print(f"Cảnh báo: {len(unknown)} tên có ký tự chưa có âm Hán-Việt: {unknown}", file=sys.stderr)

    try:
        payload = build_payload(
            crawl,
            names,
            stats,
            version_label=args.version_label,
            version_cn=args.version_cn,
            generated_at=now_stamp(),
            data_links=DATA_LINKS if args.data_links else (),
        )
        html = render_report(payload, build_avatar_css(shishen_ids, args.avatar_dir))
    except ReportError as exc:
        print(f"Lỗi dựng báo cáo: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    size_mb = args.output.stat().st_size / 1_048_576
    print(f"Xong: {args.output} ({size_mb:.2f} MB, {len(teams)} đội hình, {len(stats)} 式神)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
