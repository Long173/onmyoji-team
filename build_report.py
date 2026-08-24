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

from onmyoji.assets import fetch_shishen_map, fetch_yuhun_map
from onmyoji.avatars import download_avatars, download_yuhun_icons
from onmyoji.http import ApiError
from onmyoji.report import (
    ReportError,
    aggregate_shishen,
    build_avatar_css,
    build_payload,
    build_yuhun_css,
    now_stamp,
    paid_yuhun_ids,
    render_report,
)
from onmyoji.shishen_rank import referenced_shishen_ids, referenced_yuhun_ids
from onmyoji.translate import build_name_table, unmapped_chars

DEFAULT_INPUT = Path("out/team-rank-current.json")
DEFAULT_OUTPUT = Path("report/meta-dau-ky.html")
DEFAULT_AVATAR_DIR = Path("assets/avatars")
DEFAULT_YUHUN_DIR = Path("assets/yuhun")
DEFAULT_UNIT_INPUT = Path("out/shishen-rank-current.json")
DEFAULT_DETAIL_INPUT = Path("out/shishen-detail-current.json")
DATA_LINKS = (
    {"label": "đội hình JSON", "href": "team-rank-current.json"},
    {"label": "đội hình CSV", "href": "team-rank-current.csv"},
    {"label": "式神 JSON", "href": "shishen-rank-current.json"},
    {"label": "trend JSON", "href": "shishen-detail-current.json"},
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="file JSON do crawler sinh ra")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="file HTML xuất ra")
    parser.add_argument("--avatar-dir", type=Path, default=DEFAULT_AVATAR_DIR, help="thư mục cache avatar 式神")
    parser.add_argument("--yuhun-dir", type=Path, default=DEFAULT_YUHUN_DIR, help="thư mục cache icon ngự hồn")
    parser.add_argument(
        "--unit-input",
        type=Path,
        default=DEFAULT_UNIT_INPUT,
        help="file JSON của crawl_shishen_rank.py; thiếu thì báo cáo bỏ tab 式神",
    )
    parser.add_argument(
        "--detail-input",
        type=Path,
        default=DEFAULT_DETAIL_INPUT,
        help="file JSON của crawl_shishen_detail.py; thiếu thì bỏ sparkline và đội hình dưới ngưỡng",
    )
    parser.add_argument("--version-label", default="Phiên bản hiện hành", help="nhãn phiên bản trên masthead")
    parser.add_argument("--version-cn", default="", help="tên phiên bản tiếng Trung")
    parser.add_argument("--skip-download", action="store_true", help="không tải avatar còn thiếu")
    parser.add_argument(
        "--include-paid",
        action="store_true",
        help=(
            "đưa dữ liệu hội viên basic (ngự hồn chi tiết, đi cùng/đối đầu, vị trí BP) "
            "vào báo cáo. Đây là nội dung sau tường phí của yysrank.win — chỉ dùng cho "
            "bản xem tại máy, KHÔNG bật khi build bản publish công khai."
        ),
    )
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

    unit_rank: dict | None = None
    if args.unit_input.is_file():
        try:
            unit_rank = json.loads(args.unit_input.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Bỏ qua tab 式神 — không đọc được {args.unit_input}: {exc}", file=sys.stderr)
            unit_rank = None
    else:
        print(f"Không thấy {args.unit_input} — báo cáo sẽ không có tab 式神.", file=sys.stderr)

    unit_detail: dict | None = None
    if args.detail_input.is_file():
        try:
            unit_detail = json.loads(args.detail_input.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Bỏ qua sparkline — không đọc được {args.detail_input}: {exc}", file=sys.stderr)
            unit_detail = None
    else:
        print(f"Không thấy {args.detail_input} — bỏ sparkline và đội hình dưới ngưỡng.", file=sys.stderr)

    unit_rows = (unit_rank or {}).get("shishen") or []
    hidden_ids = {
        int(sid)
        for entry in ((unit_detail or {}).get("details") or [])
        for team in (entry.get("teams") or [])
        for sid in (team.get("team") or [])
    }
    shishen_ids = tuple(
        sorted(
            {stat.shishen_id for stat in stats}
            | set(referenced_shishen_ids(unit_rows))
            | hidden_ids
        )
    )
    yuhun_ids = referenced_yuhun_ids(unit_rows)
    if args.include_paid:
        paid_ids = {
            int(row["yuhun_id"])
            for entry in ((unit_detail or {}).get("details") or [])
            for row in (entry.get("yuhuns") or [])
        }
        yuhun_ids = tuple(sorted(set(yuhun_ids) | paid_ids))

    try:
        shishen_map = fetch_shishen_map()
        if not args.skip_download:
            fetched, missing = download_avatars(shishen_ids, args.avatar_dir)
            print(f"Avatar 式神: {fetched} tải mới, {len(shishen_ids) - len(missing)} sẵn sàng.", file=sys.stderr)
            if missing:
                print(f"  thiếu: {sorted(missing)}", file=sys.stderr)
            if yuhun_ids:
                fetched_y, missing_y = download_yuhun_icons(yuhun_ids, fetch_yuhun_map(), args.yuhun_dir)
                print(
                    f"Icon ngự hồn: {fetched_y} tải mới, {len(yuhun_ids) - len(missing_y)} sẵn sàng.",
                    file=sys.stderr,
                )
                if missing_y:
                    print(f"  thiếu: {sorted(missing_y)}", file=sys.stderr)
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
            unit_rank=unit_rank,
            unit_detail=unit_detail,
            include_paid=args.include_paid,
        )
        avatar_css = build_avatar_css(shishen_ids, args.avatar_dir)
        yuhun_css = build_yuhun_css(yuhun_ids, args.yuhun_dir)
        html = render_report(payload, "\n".join(filter(None, (avatar_css, yuhun_css))))
    except ReportError as exc:
        print(f"Lỗi dựng báo cáo: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    size_mb = args.output.stat().st_size / 1_048_576
    paid_note = ""
    if args.include_paid:
        paid_units = len(((payload.get("paid") or {}).get("units")) or {})
        paid_note = f", {paid_units} 式神 có dữ liệu hội viên (BẢN NÀY KHÔNG ĐỂ PUBLISH)"
    print(
        f"Xong: {args.output} ({size_mb:.2f} MB, {len(teams)} đội hình, "
        f"{len(stats)} 式神 trong meta, {len(unit_rows)} 式神 xếp hạng, "
        f"{len(yuhun_ids)} ngự hồn{paid_note})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
