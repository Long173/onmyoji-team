"""Nhãn vai trò của 式神 — /api/shishen/tag/all và /api/asset/tag (đều mở).

Site chia hai loại nhãn:

* `system: true`  — bộ từ vựng chức năng do site chuẩn hoá (输出, 拉条, 护盾…).
  Đây là phần dùng được: nó nói 式神 làm gì trong đội.
* `system: false` — nhãn người dùng tự thêm. Phần lớn là meme, và có cả từ tục
  (畜生, 死妈, 涩图, 恶心). Bỏ, trừ vài nhãn chỉ cơ chế thật trong ALLOWED_USER_TAGS.

Dịch theo NGHĨA chứ không theo âm Hán-Việt: 拉条 → "Kéo thanh" mới hiểu được,
"Lạp Điều" thì vô nghĩa với người chơi.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .http import ApiError, get_json

TAG_ALL_PATH = "/api/shishen/tag/all"
TAG_ASSET_PATH = "/api/asset/tag"

# Nhãn hệ thống → nghĩa tiếng Việt.
TAG_LABELS: Mapping[str, str] = {
    "输出": "Sát thương",
    "增伤": "Tăng sát thương",
    "减伤": "Giảm sát thương nhận",
    "反伤": "Phản sát thương",
    "生存": "Sinh tồn",
    "护盾": "Khiên",
    "破盾": "Phá khiên",
    "回血": "Hồi máu",
    "复活": "Hồi sinh",
    "免死": "Miễn tử",
    "拉条": "Kéo thanh",
    "推条": "Đẩy thanh",
    "锁条": "Khoá thanh",
    "防推条": "Chống đẩy thanh",
    "抢速": "Tranh tốc",
    "反抢速": "Chống tranh tốc",
    "单控": "Khống chế đơn",
    "群控": "Khống chế nhóm",
    "解控": "Giải khống chế",
    "免控": "Miễn khống chế",
    "反控": "Phản khống chế",
    "抵挡控制": "Chặn khống chế",
    "打火": "Đốt lửa",
    "扣火": "Trừ lửa",
    "反击": "Phản kích",
    "防反击": "Chống phản kích",
    "协战": "Hiệp trợ",
    "召唤物": "Triệu hồi vật",
    "增抵抗": "Tăng kháng",
    "减抵抗": "Giảm kháng",
    "增命中": "Tăng mệnh trúng",
    "减命中": "Giảm mệnh trúng",
    "减疗": "Giảm hồi phục",
    "封御魂": "Phong ngự hồn",
    "封被动": "Phong bị động",
    "封普攻": "Phong đánh thường",
    "无视御魂": "Bỏ qua ngự hồn",
    "无视被动": "Bỏ qua bị động",
    "配合普攻式神": "Hợp 式神 đánh thường",
    "单体": "Đơn mục tiêu",
    # Nhãn người dùng nhưng chỉ cơ chế rõ ràng, giữ lại.
    "治疗或恢复": "Trị liệu / hồi phục",
    "自拉条": "Tự kéo thanh",
    "回合外特攻": "Đánh ngoài lượt",
}

ALLOWED_USER_TAGS = frozenset({"治疗或恢复", "自拉条", "回合外特攻"})


def fetch_tag_dictionary() -> Mapping[int, Mapping[str, Any]]:
    """Từ điển nhãn: {tag_id: {name, system}}."""
    rows = get_json(TAG_ASSET_PATH)
    if not isinstance(rows, list):
        raise ApiError(f"{TAG_ASSET_PATH}: 'data' phải là list")
    return {
        int(row["id"]): {"name": str(row.get("name") or ""), "system": bool(row.get("system"))}
        for row in rows
        if isinstance(row, dict) and row.get("id") is not None
    }


def _keep(tag: Mapping[str, Any]) -> bool:
    name = str(tag.get("name") or "")
    if tag.get("blocked"):
        return False
    if name not in TAG_LABELS:
        return False
    return bool(tag.get("system")) or name in ALLOWED_USER_TAGS


def fetch_shishen_tags() -> Mapping[int, tuple[Mapping[str, str], ...]]:
    """{shishen_id: (nhãn đã lọc và dịch, …)} — giữ thứ tự site trả về."""
    rows = get_json(TAG_ALL_PATH)
    if not isinstance(rows, list):
        raise ApiError(f"{TAG_ALL_PATH}: 'data' phải là list")

    result: dict[int, tuple[Mapping[str, str], ...]] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("shishen_id") is None:
            continue
        kept = tuple(
            {"cn": str(tag["name"]), "vn": TAG_LABELS[str(tag["name"])]}
            for tag in (row.get("tags") or ())
            if isinstance(tag, dict) and _keep(tag)
        )
        if kept:
            result[int(row["shishen_id"])] = kept
    return result


def dropped_tag_names(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Nhãn bị bỏ vì chưa có bản dịch — để biết cần bổ sung gì."""
    seen: set[str] = set()
    for row in rows:
        for tag in row.get("tags") or ():
            name = str((tag or {}).get("name") or "")
            if name and name not in TAG_LABELS:
                seen.add(name)
    return tuple(sorted(seen))
