"""阴阳师 (âm dương sư) — nhân vật dẫn dắt đội hình.

`/api/team/detail` trả `yys` với field `yys_id`. Site dùng hai dải id cho cùng
6 nhân vật: 1–6 và 10–16 (xem `index-BmPXGley.js`).
"""

from __future__ import annotations

from typing import Mapping

from .translate import to_hanviet

YYS_CHINESE: Mapping[int, str] = {
    1: "晴明", 2: "神乐", 3: "八百比丘尼", 4: "源博雅", 5: "源赖光", 6: "藤原道长",
    10: "晴明", 11: "神乐", 12: "八百比丘尼", 13: "源博雅", 15: "源赖光", 16: "藤原道长",
}

# Tên romaji quen dùng.
YYS_COMMON: Mapping[str, str] = {
    "晴明": "Seimei",
    "神乐": "Kagura",
    "八百比丘尼": "Hakubikuni",
    "源博雅": "Hiromasa",
    "源赖光": "Raiko",
    "藤原道长": "Michinaga",
}


def yys_name(yys_id: int) -> Mapping[str, str]:
    """Trả về {cn, vn, common} cho một yys_id; rỗng nếu id lạ."""
    chinese = YYS_CHINESE.get(int(yys_id), "")
    if not chinese:
        return {"cn": "", "vn": f"#{yys_id}", "common": ""}
    return {
        "cn": chinese,
        "vn": to_hanviet(chinese),
        "common": YYS_COMMON.get(chinese, ""),
    }


def yys_table() -> Mapping[int, Mapping[str, str]]:
    return {yys_id: yys_name(yys_id) for yys_id in sorted(YYS_CHINESE)}
